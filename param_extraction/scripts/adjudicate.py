#!/usr/bin/env python3
# Copyright (c) 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""
LLM adjudication layer: apply the inclusion rules that cannot be scripted.

Script filters (validate_findings.py + generate_spreadsheet.py) catch the
mechanical rules (unspecified behavior, reserved facts, WARL phrasing, intro
sections, SW keywords). But several reviewer rules need *semantic judgment*:

  - Duplicate: is this candidate the same concept as an existing UDB
    parameter, even under a different name or described in a different place?
    (e.g. GEILEN vs NUM_EXTERNAL_GUEST_INTERRUPTS — no shared tokens.)
  - Describes-existing-mechanism: is it just restating how an existing
    feature/lock-bit/WARL field already works?
  - Certifiable: does it have a finite, verifiable value set?
  - Needs-rationale: is it a normative rule that can't be labelled a parameter
    without the design intent?

This runs an LLM reviewer over each candidate, grounded in the FULL list of
existing UDB parameters (names + descriptions), and returns a verdict with the
rule that fired and, for duplicates, which UDB parameter it duplicates.

Output (results/<version>/adjudication_<model>.json) + three lists:
KEEP (real new params), DROP (with reason), NEEDS_HUMAN.

Usage:
  uv run --with anthropic python param_extraction/scripts/adjudicate.py \
      --candidates param_extraction/data/parameters.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
RESULTS_DIR = PROJECT_DIR / "results"
PROMPT_VERSION = os.environ.get("PROMPT_VERSION", "v4")
MODEL_ID = os.environ.get("MODEL_ID", "claude-sonnet-4-6")
BATCH_SIZE = int(os.environ.get("ADJ_BATCH", "8"))

logger = logging.getLogger("adjudicate")

SYSTEM_RULES = """\
You are a RISC-V certification reviewer for the Unified Database (UDB). You decide whether a \
candidate is a real, NEW, certifiable architectural *parameter*, applying the rules below exactly \
as a maintainer would. Be strict: when in doubt, do not keep.

A parameter is an implementation choice with a FINITE, ENUMERABLE, VERIFIABLE set of legal values, \
not already captured elsewhere in UDB.

Reject (verdict DROP) if the candidate is any of:
- UNSPECIFIED behavior/result/outcome (intentionally unconstrained — cannot certify). Note: an
  unspecified VALUE/width/number that the implementation picks IS a parameter.
- "misconfigured" outcomes, or implementation-defined things with no testable units/options.
- a plain WARL or read-only-vs-read-write field restatement already covered by the CSR field model.
- introduction/overview (non-normative) text.
- a software/firmware requirement or a clarification (not an implementer hardware choice).
- a clarification that merely references a parameter defined elsewhere.
- a DUPLICATE: the same architectural concept as an existing UDB parameter (listed below), even if
  the name differs or it's described in a different place. Set duplicate_of to that UDB name.
- just describing how an existing mechanism/lock-bit/feature already works.

Use verdict NEEDS_HUMAN for a genuine normative rule whose parameter-ness can't be decided without
the design rationale.

Use verdict KEEP only for a genuine new certifiable parameter not covered above.

Return ONLY a JSON array, one object per candidate, in the same order:
[{"name": "...", "verdict": "KEEP|DROP|NEEDS_HUMAN", "rule": "duplicate|unspecified|warl_covered|\
misconfigured|sw_or_clarification|intro|references_existing|existing_mechanism|needs_rationale|\
certifiable", "duplicate_of": "UDB_NAME or null", "reasoning": "one sentence"}]
"""


def load_existing_params() -> str:
    gt = json.loads((DATA_DIR / "ground_truth.json").read_text())["parameters"]
    lines = [f"- {p['name']} [{p.get('classification','')}]: {(p.get('description') or '').strip()[:120]}"
             for p in gt]
    return "Existing UDB parameters (do not re-discover these):\n" + "\n".join(lines)


def load_candidates(path: Path, only_new: bool) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if only_new:
        rows = [r for r in rows if r.get("named", "no") == "no"]
    return rows


def call_anthropic(system_blocks: list[dict], user_text: str) -> str:
    import anthropic
    client = anthropic.Anthropic(max_retries=0)
    for attempt in range(6):
        try:
            resp = client.messages.create(
                model=MODEL_ID,
                max_tokens=4096,
                temperature=0,
                system=system_blocks,
                messages=[{"role": "user", "content": user_text}],
            )
            return resp.content[0].text
        except Exception as e:
            if "429" in str(e) or "overloaded" in str(e).lower():
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError("repeated API failures")


def parse_array(text: str) -> list[dict]:
    s = text.find("[")
    e = text.rfind("]")
    if s < 0 or e < 0:
        return []
    try:
        return json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return []


def adjudicate(candidates: list[dict], existing: str) -> list[dict]:
    # Existing-params block is large and constant -> mark it cacheable.
    system_blocks = [
        {"type": "text", "text": SYSTEM_RULES},
        {"type": "text", "text": existing, "cache_control": {"type": "ephemeral"}},
    ]
    out: list[dict] = []
    for i in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[i : i + BATCH_SIZE]
        user = "Adjudicate these candidates:\n\n" + "\n\n".join(
            f"{j+1}. name: {c['parameter_name']}\n   class: {c.get('class','')}\n"
            f"   excerpt: {c['excerpt']}\n   modal_signal: {c.get('modal_signal','')}"
            for j, c in enumerate(batch)
        )
        verdicts = parse_array(call_anthropic(system_blocks, user))
        by_name = {v.get("name", ""): v for v in verdicts}
        for c in batch:
            v = by_name.get(c["parameter_name"], {})
            out.append({
                "parameter_name": c["parameter_name"],
                "verdict": v.get("verdict", "NEEDS_HUMAN"),
                "rule": v.get("rule", "unparsed"),
                "duplicate_of": v.get("duplicate_of"),
                "reasoning": v.get("reasoning", ""),
                "class": c.get("class", ""),
                "excerpt": c.get("excerpt", ""),
            })
        logger.info("adjudicated %d/%d", min(i + BATCH_SIZE, len(candidates)), len(candidates))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidates", type=Path, default=DATA_DIR / "parameters.csv")
    ap.add_argument("--all", action="store_true", help="Adjudicate all rows, not just new (named=no)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    candidates = load_candidates(args.candidates, only_new=not args.all)
    existing = load_existing_params()
    logger.info("Adjudicating %d candidates against %d existing params (model=%s)",
                len(candidates), existing.count("\n- "), MODEL_ID)

    results = adjudicate(candidates, existing)

    out = args.out or (RESULTS_DIR / PROMPT_VERSION / "adjudication_claude.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    from collections import Counter
    counts = Counter(r["verdict"] for r in results)
    logger.info("Verdicts: %s", dict(counts))
    logger.info("Wrote %s", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
