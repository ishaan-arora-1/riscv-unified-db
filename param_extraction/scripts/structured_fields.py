#!/usr/bin/env python3
# Copyright (c) 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""
V3 Stage 3.3: Structured pre-extraction of CSR fields from bytefield diagrams.

The extraction LLM reads register layouts as raw prose and is genuinely bad at
parsing them, so bit-level parameters (e.g. which `mcountinhibit` bits are
writable, the AIA bit in `mstateen0`) get missed — they're defined in a
diagram, not a sentence.

RISC-V bytefield diagrams live in `images/bytefield/*.edn` (and some
`images/wavedrom/*.edn`) files, included into the `.adoc` via
`include::images/.../NAME.edn[]`. Each diagram declares its fields with
`(draw-box "FIELD" ...)` and marks WARL fields with `(text "(WARL)" ...)`.

This module parses those diagrams and, for any `.adoc` file (or chunk line
range), produces a structured summary listing every named field and whether it
is WARL. That summary is appended to the extraction prompt so the model gets an
explicit checklist of fields to reason about, rather than having to notice them
in the text.

Usage:
  uv run python param_extraction/scripts/structured_fields.py build   # data/structured_fields.json
  uv run python param_extraction/scripts/structured_fields.py summary machine.adoc
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
REPO_ROOT = PROJECT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
SPEC_DIR = REPO_ROOT / "ext" / "riscv-isa-manual" / "src"

logger = logging.getLogger("v3.structured")

INCLUDE_RE = re.compile(r"include::(images/(?:bytefield|wavedrom)/[^\[]+\.edn)\[\]")
DRAW_BOX_RE = re.compile(r'\(draw-box\s+(?:\(text\s+)?"([^"]+)"')
WARL_RE = re.compile(r'"\(WARL\)"')

# Box labels that are decorations or bit-width annotations, not field names.
_DECORATION = {"(WARL)", "(WLRL)", "(WPRI)", "...", "", "0", "1"}
_WIDTH_LABEL = re.compile(r"^(MXLEN[-\d]*|XLEN[-\d]*|\d+|[-\d]+)$")


def _is_field_name(label: str) -> bool:
    s = label.strip()
    if s in _DECORATION:
        return False
    if _WIDTH_LABEL.match(s):
        return False
    # Must contain at least one letter to be a field name.
    return bool(re.search(r"[A-Za-z]", s))


def parse_edn(path: Path) -> dict:
    """Return {'fields': [...], 'warl': bool} for one bytefield .edn file."""
    if not path.exists():
        return {"fields": [], "warl": False}
    text = path.read_text(encoding="utf-8", errors="replace")
    fields: list[str] = []
    seen: set[str] = set()
    for m in DRAW_BOX_RE.finditer(text):
        label = m.group(1).strip()
        if _is_field_name(label) and label not in seen:
            seen.add(label)
            fields.append(label)
    return {"fields": fields, "warl": bool(WARL_RE.search(text))}


def build_index() -> dict:
    """Map each .adoc file -> list of {register, edn, fields, warl} entries.

    `register` is derived from the .edn filename (best-effort handle).
    """
    index: dict[str, list[dict]] = {}
    for adoc in sorted(SPEC_DIR.glob("*.adoc")):
        lines = adoc.read_text(encoding="utf-8", errors="replace").splitlines()
        entries: list[dict] = []
        for lineno, line in enumerate(lines, start=1):
            m = INCLUDE_RE.search(line)
            if not m:
                continue
            edn_rel = m.group(1)
            edn_path = SPEC_DIR / edn_rel
            parsed = parse_edn(edn_path)
            if not parsed["fields"]:
                continue
            register = Path(edn_rel).stem
            entries.append(
                {
                    "register": register,
                    "edn": edn_rel,
                    "line_number": lineno,
                    "fields": parsed["fields"],
                    "warl": parsed["warl"],
                }
            )
        if entries:
            index[adoc.name] = entries
    return index


def summary_for_file(adoc_name: str, index: dict, start_line: int = 0, end_line: int = 10**9) -> str:
    """Render a compact field checklist for the given file / line window."""
    entries = [
        e for e in index.get(adoc_name, [])
        if start_line <= e["line_number"] <= end_line
    ]
    if not entries:
        return ""
    out = ["## Register fields present in this section (from bytefield diagrams)",
           "Consider each field below: is it optional / implementation-defined / WARL? If so it may be a parameter.\n"]
    seen: set[tuple] = set()
    for e in entries:
        key = (e["register"], tuple(e["fields"]))
        if key in seen:
            continue
        seen.add(key)
        warl = " [WARL]" if e["warl"] else ""
        fields = ", ".join(e["fields"])
        out.append(f"- `{e['register']}`{warl}: {fields}")
    return "\n".join(out)


def cmd_build(_args) -> int:
    index = build_index()
    out = DATA_DIR / "structured_fields.json"
    out.write_text(json.dumps(index, indent=2), encoding="utf-8")
    (out.parent / (out.name + ".license")).write_text(
        "# SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB "
        "<https://github.com/riscv/riscv-unified-db>\n"
        "# SPDX-License-Identifier: BSD-3-Clause-Clear\n",
        encoding="utf-8",
    )
    n_files = len(index)
    n_regs = sum(len(v) for v in index.values())
    n_fields = sum(len(e["fields"]) for v in index.values() for e in v)
    n_warl = sum(1 for v in index.values() for e in v if e["warl"])
    logger.info(
        "Indexed %d files, %d register diagrams, %d named fields (%d WARL diagrams). Wrote %s",
        n_files, n_regs, n_fields, n_warl, out,
    )
    return 0


def cmd_summary(args) -> int:
    index = build_index()
    print(summary_for_file(args.adoc, index))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="Build data/structured_fields.json")
    s = sub.add_parser("summary", help="Print the field checklist for one .adoc file")
    s.add_argument("adoc")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    return {"build": cmd_build, "summary": cmd_summary}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
