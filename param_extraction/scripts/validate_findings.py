#!/usr/bin/env python3
# Copyright (c) 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""
V3 Stage 1: Validate LLM parameter findings against the spec's own rules.

The extraction prompt *asks* the model to avoid non-parameters (NOTE blocks,
fixed must/shall requirements, reserved-encoding facts, permission-"may").
Nothing previously *checked* that it did — findings flowed straight into the
final spreadsheet. This module is the missing quality-control gate: it labels
every finding with a verdict and a reason, so the deliverable can be filtered
to the defensible subset and every rejection is auditable.

A real architectural parameter is a choice the spec *explicitly leaves to the
implementer*. The strongest textual signal for that is RFC-2119-style
optionality language ("may", "optional", "implementation-defined", ...). The
gates below are ordered; the first matching gate wins.

Verdicts
  KEEP             — has clear optionality language; confirmed parameter
  REVIEW_NO_MODAL  — no optionality and no hard-rule language; needs human eyes
  FRAGMENT         — excerpt too short / not a sentence; needs human eyes
  REJECT_NOTE      — excerpt lives inside a NOTE/TIP/WARNING/IMPORTANT block
  REJECT_RESERVED  — reserved/hardwired fact, not an implementation choice
  REJECT_REQUIRED  — fixed must/shall requirement, no optionality
  DROP_NONARCH     — model itself classified it non-architectural

Usage
  uv run python param_extraction/scripts/validate_findings.py \
      --deduped param_extraction/results/v2/deduped_claude-sonnet-4.json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
REPO_ROOT = PROJECT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
RESULTS_DIR = PROJECT_DIR / "results"
SPEC_DIR = REPO_ROOT / "ext" / "riscv-isa-manual" / "src"

logger = logging.getLogger("v3.validate")

# Verdicts that still make it into the reviewable deliverable.
KEPT_VERDICTS = {"KEEP", "REVIEW_NO_MODAL", "FRAGMENT"}
NON_ARCH_CLASSES = {"NON_ISA", "NON_NORM", "DOC_RULE", "UNKNOWN"}

MIN_SENTENCE_CHARS = 80

# ── Signal patterns ─────────────────────────────────────────────────────────

# Optionality: the spec explicitly leaves a choice to the implementer.
# Deliberately anchored to "implementation"/feature verbs so that bare
# permission-"may" ("software may read ...") does NOT count.
OPTIONALITY = re.compile(
    r"""
    implementation[-\ ]defined        | implementation[-\ ]dependent          |
    \boptional(ly)?\b                  | \bunspecified\b                       |
    may\ or\ may\ not                  | \bneed\ not\b                         |
    (is|are|is\ not|are\ not)\ not\ required\ to                              |
    not\ required\ to\ (support|implement|provide|have)                       |
    may\ (optionally\ )?(be\ (implemented|read-only|supported|present|absent|configured)
        | implement | support | choose | contain | hold | return | vary
        | provide | omit | not\ support | not\ be | not\ implement)            |
    can\ (be\ (implemented|read-only|configured)
        | choose | contain | vary | be\ omitted)                              |
    \b(is|are)\ allowed\ to\b          |
    (vary|varies|depend|depends|differ|differs)\ (by|on|across|between).{0,30}implementation |
    implementation.{0,20}(may|can|chooses?|decides?|selects?|defines?|provides?|sets?) |
    (implementer|implementation)\ (chooses?|defines?|selects?|provides?|sets?)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Hard requirement language (no implementer choice).
REQUIREMENT = re.compile(r"\b(must|shall|required|mandatory|always)\b", re.IGNORECASE)

# Reserved / hardwired statements of fact (not a knob).
RESERVED = re.compile(
    r"\b(reserved|hardwired|hard-wired|tied\ to|fixed\ to|wpri)\b", re.IGNORECASE
)

# Admonition openers, both the block form ([NOTE]\n====) and the inline form (NOTE:).
ADMONITION_BLOCK = re.compile(r"^\[(NOTE|TIP|WARNING|IMPORTANT|CAUTION)\]\s*$")
ADMONITION_INLINE = re.compile(r"^(NOTE|TIP|WARNING|IMPORTANT|CAUTION):\s")
BLOCK_DELIM = re.compile(r"^(={4,}|-{2,}|\*{4,}|_{4,})\s*$")


# ── NOTE-block index (built per spec file, line-number based) ───────────────


def build_note_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """Return 1-based inclusive line ranges that fall inside admonition blocks."""
    ranges: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip("\n")
        if ADMONITION_BLOCK.match(line.strip()):
            # Next non-empty line should be a delimiter; block runs to the
            # matching delimiter.
            j = i + 1
            while j < n and lines[j].strip() == "":
                j += 1
            if j < n and BLOCK_DELIM.match(lines[j].strip()):
                delim = lines[j].strip()
                k = j + 1
                while k < n and lines[k].strip() != delim:
                    k += 1
                # 1-based inclusive, covering opener..closing delimiter
                ranges.append((i + 1, min(k + 1, n)))
                i = k + 1
                continue
        if ADMONITION_INLINE.match(line):
            ranges.append((i + 1, i + 1))
        i += 1
    return ranges


def _norm(text: str) -> str:
    """Whitespace-normalized, lowercased text for robust substring matching."""
    return re.sub(r"\s+", " ", text).strip().lower()


def load_note_index(source_files: set[str]) -> dict[str, str]:
    """Per-file, the normalized concatenation of all admonition-block text.

    We match findings against this by TEXT, never by the LLM-reported line
    number — LLMs miscount lines, so line-based NOTE detection produces mostly
    false positives (verified: 44/54 mislabeled on the V2 set).
    """
    index: dict[str, str] = {}
    for fname in source_files:
        path = SPEC_DIR / fname
        if not path.exists():
            index[fname] = ""
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        note_text_parts: list[str] = []
        for lo, hi in build_note_ranges(lines):
            # build_note_ranges returns 1-based inclusive; slice accordingly
            note_text_parts.append("".join(lines[lo - 1 : hi]))
        index[fname] = _norm(" ".join(note_text_parts))
    return index


# Excerpt prefix length used as the search key when testing NOTE membership.
_NOTE_KEY_LEN = 60


def in_note_block(fname: str, excerpt: str, note_index: dict) -> bool:
    note_text = note_index.get(fname, "")
    if not note_text:
        return False
    key = _norm(excerpt)[:_NOTE_KEY_LEN]
    return bool(key) and key in note_text


# ── Per-finding classification ──────────────────────────────────────────────


def classify(finding: dict, note_index: dict) -> tuple[str, str]:
    """Return (verdict, reason) for a single LLM finding."""
    cls = (finding.get("class") or "").upper()
    excerpt = (finding.get("excerpt") or "").strip()
    fname = finding.get("_source_file") or finding.get("adoc_file") or ""

    # 1. Model self-classified as non-architectural.
    if cls in NON_ARCH_CLASSES:
        return "DROP_NONARCH", f"class={cls} is non-architectural"

    # 2. Origin inside a NOTE/TIP/WARNING block (non-normative). Matched by
    #    text, not by the unreliable LLM line number.
    if excerpt and in_note_block(fname, excerpt, note_index):
        return "REJECT_NOTE", f"excerpt text found inside an admonition block in {fname}"

    has_opt = bool(OPTIONALITY.search(excerpt))

    # 3. Fragment / not a sentence (only if it isn't a clear optionality hit).
    if not has_opt and (len(excerpt) < MIN_SENTENCE_CHARS or " " not in excerpt.strip()):
        return "FRAGMENT", f"excerpt is {len(excerpt)} chars, likely a fragment"

    # 4. Clear optionality language → confirmed.
    if has_opt:
        return "KEEP", "optionality language present"

    # 5. Reserved / hardwired fact, no optionality.
    if RESERVED.search(excerpt):
        return "REJECT_RESERVED", "reserved/hardwired statement of fact, no optionality"

    # 6. Hard requirement, no optionality.
    if REQUIREMENT.search(excerpt):
        return "REJECT_REQUIRED", "must/shall requirement with no optionality language"

    # 7. Neither signal — genuinely ambiguous.
    return "REVIEW_NO_MODAL", "no optionality and no hard-rule language"


# ── Final dedup on resolved identity ────────────────────────────────────────


def dedup_kept(findings: list[dict]) -> tuple[list[dict], int]:
    """Collapse kept findings sharing (parameter_name, source_file).

    Runs on the resolved name so post-alignment collisions (e.g. SXLEN x2)
    that the early name-only dedup missed are caught here.
    """
    rank = {"high": 3, "medium": 2, "low": 1}
    best: dict[tuple[str, str], dict] = {}
    dropped = 0
    for f in findings:
        key = ((f.get("parameter_name") or "").upper(), f.get("_source_file") or "")
        cur = best.get(key)
        if cur is None:
            best[key] = f
        else:
            dropped += 1
            if rank.get(f.get("confidence"), 0) > rank.get(cur.get("confidence"), 0):
                best[key] = f
    return list(best.values()), dropped


# ── Driver ──────────────────────────────────────────────────────────────────


def validate(deduped: dict) -> tuple[list[dict], dict]:
    params = deduped.get("parameters", [])
    source_files = {p.get("_source_file") or "" for p in params if p.get("_source_file")}
    note_index = load_note_index(source_files)

    annotated: list[dict] = []
    for p in params:
        verdict, reason = classify(p, note_index)
        annotated.append({**p, "_verdict": verdict, "_verdict_reason": reason})

    kept = [a for a in annotated if a["_verdict"] in KEPT_VERDICTS]
    kept_deduped, collisions = dedup_kept(kept)

    stats = {
        "total": len(params),
        "verdicts": dict(Counter(a["_verdict"] for a in annotated)),
        "kept_before_dedup": len(kept),
        "kept_after_dedup": len(kept_deduped),
        "final_dedup_collisions": collisions,
    }
    return annotated, stats


def write_report(annotated: list[dict], path: Path) -> None:
    cols = [
        "parameter_name", "class", "confidence", "_verdict", "_verdict_reason",
        "_source_file", "line_number", "excerpt",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([c.lstrip("_") for c in cols])
        for a in sorted(annotated, key=lambda x: (x["_verdict"], x.get("_source_file", ""))):
            w.writerow([a.get(c, "") for c in cols])
    logger.info("Wrote %s", path)


def write_stats(stats: dict, path: Path) -> None:
    order = [
        "KEEP", "REVIEW_NO_MODAL", "FRAGMENT",
        "REJECT_NOTE", "REJECT_RESERVED", "REJECT_REQUIRED", "DROP_NONARCH",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("V3 Stage 1 — Finding Validation — Statistics\n")
        f.write("=" * 56 + "\n\n")
        f.write(f"Total findings examined : {stats['total']}\n\n")
        f.write("Verdict breakdown:\n")
        for v in order:
            n = stats["verdicts"].get(v, 0)
            pct = 100 * n / stats["total"] if stats["total"] else 0
            f.write(f"  {v:18s} {n:4d}  ({pct:4.1f}%)\n")
        for v, n in stats["verdicts"].items():
            if v not in order:
                f.write(f"  {v:18s} {n:4d}\n")
        f.write("\n")
        f.write(f"Reviewable (KEEP+REVIEW+FRAGMENT) before final dedup : {stats['kept_before_dedup']}\n")
        f.write(f"Final-dedup collisions collapsed                     : {stats['final_dedup_collisions']}\n")
        f.write(f"Confirmed/reviewable after final dedup               : {stats['kept_after_dedup']}\n")
    logger.info("Wrote %s", path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--deduped", type=Path, default=RESULTS_DIR / "v2" / "deduped_claude-sonnet-4.json")
    p.add_argument("--out-report", type=Path, default=DATA_DIR / "validation_report.csv")
    p.add_argument("--out-stats", type=Path, default=DATA_DIR / "validation_stats.txt")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    if not args.deduped.exists():
        logger.error("Missing deduped results: %s", args.deduped)
        return 2

    deduped = load_json(args.deduped)
    annotated, stats = validate(deduped)
    write_report(annotated, args.out_report)
    write_stats(stats, args.out_stats)

    logger.info(
        "Validation: %d findings -> %d confirmed/reviewable (%d rejected, %d dedup collisions)",
        stats["total"],
        stats["kept_after_dedup"],
        stats["total"] - stats["kept_before_dedup"],
        stats["final_dedup_collisions"],
    )
    return 0


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    sys.exit(main())
