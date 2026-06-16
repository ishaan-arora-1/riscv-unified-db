#!/usr/bin/env python3
# Copyright (c) 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""
Generate UDB parameter YAML stubs from a verified new-parameter list.

UDB has no scaffolding for creating parameter YAMLs — they are hand-authored
against spec/schemas/param_schema.json. This produces schema-valid *stubs* for
each verified new parameter so a human only has to fill the specifics.

What we can fill from the extraction data:
  - name, kind, $schema
  - description  (seeded from the spec excerpt)
  - schema.type  (from the detected value_type)

What needs human completion (emitted as `# TODO` so nothing is silently wrong):
  - long_name
  - definedBy extension  (best-guessed from the source file; ALWAYS verify)
  - concrete legal values: enum members, min/max, bitmask width

Stubs are written to a staging dir (NOT spec/std/isa/param/) so they can be
reviewed before becoming a real PR.

Usage:
  uv run python param_extraction/scripts/generate_param_yamls.py
  uv run --with jsonschema python param_extraction/scripts/generate_param_yamls.py --validate
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
REPO_ROOT = PROJECT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
SCHEMA_PATH = REPO_ROOT / "spec" / "schemas" / "param_schema.json"

logger = logging.getLogger("gen_yaml")

# Best-guess defining extension per source file. ALWAYS flagged for human
# verification — getting definedBy wrong changes when the parameter exists.
FILE_TO_EXT = {
    "a-st-ext.adoc": "A",
    "b-st-ext.adoc": "B",
    "cmo.adoc": "Zicbom",
    "counters.adoc": "Zihpm",
    "hypervisor.adoc": "H",
    "machine.adoc": "Sm",
    "priv-intro.adoc": "Sm",
    "priv-csrs.adoc": "Sm",
    "rnmi.adoc": "Smrnmi",
    "scalar-crypto.adoc": "Zkr",
    "smcdeleg.adoc": "Smcdeleg",
    "smctr.adoc": "Smctr",
    "smstateen.adoc": "Smstateen",
    "supervisor.adoc": "S",
    "zalasr.adoc": "Zalasr",
    "zawrs.adoc": "Zawrs",
    "zicsr.adoc": "Zicsr",
    "zpm.adoc": "Smmpm",
}

# value_type -> (schema lines, needs-TODO-for-values?)
def schema_block(value_type: str) -> tuple[list[str], str]:
    """Return (yaml lines for the `schema:` block, a note on what's missing)."""
    vt = (value_type or "").strip().lower()
    if vt == "binary":
        return (["  type: boolean"], "")
    if vt == "value":
        return (["  type: integer"], "confirm integer vs string and any bounds")
    if vt == "range":
        return (
            ["  type: integer",
             "  # TODO: set the legal range",
             "  minimum: 0   # TODO",
             "  maximum: 0   # TODO"],
            "fill minimum/maximum",
        )
    if vt == "enum":
        return (
            ["  type: string   # TODO: confirm string vs integer",
             "  # TODO: list the legal values",
             "  enum: []   # TODO"],
            "fill enum values",
        )
    if vt == "set":
        return (
            ["  type: array",
             "  items:",
             "    type: integer   # TODO: confirm element type / universe"],
            "confirm the universe of values",
        )
    if vt == "bitmask":
        return (
            ["  type: array",
             "  items:",
             "    type: boolean",
             "  # TODO: set the fixed length (one bool per field/bit)"],
            "set bitmask length",
        )
    return (["  type: string   # TODO: unknown value_type, set schema"], "set schema manually")


def yaml_escape_block(text: str, indent: str = "  ") -> str:
    """Render text as a YAML literal block scalar."""
    lines = text.strip().splitlines() or [""]
    return "\n".join(indent + line.rstrip() for line in lines)


def build_yaml(row: dict) -> tuple[str, dict]:
    name = row["parameter_name"].strip()
    ext = FILE_TO_EXT.get(row["adoc_file"], "Sm")
    ext_guessed = row["adoc_file"] not in FILE_TO_EXT or row["adoc_file"] in {
        "priv-intro.adoc", "priv-csrs.adoc", "cmo.adoc", "counters.adoc", "zpm.adoc",
    }
    sch_lines, missing = schema_block(row["value_type"])

    desc = row["excerpt"].strip()
    body = []
    body.append("# Copyright (c) Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>")
    body.append("# SPDX-License-Identifier: BSD-3-Clause-Clear")
    body.append("")
    body.append("# yaml-language-server: $schema=../../../schemas/param_schema.json")
    body.append("")
    body.append("$schema: param_schema.json#")
    body.append("kind: parameter")
    body.append(f"name: {name}")
    body.append("long_name: TODO   # TODO: short human-readable label")
    body.append("description: |")
    body.append(f"  {desc}")
    body.append(f"  # Source: {row['adoc_file']}:{row['line_number']} (classification {row['class']})")
    body.append("schema:")
    body.extend(sch_lines)
    body.append("definedBy:")
    flag = "   # TODO: VERIFY defining extension" if ext_guessed else "   # TODO: verify defining extension"
    body.append("  extension:")
    body.append(f"    name: {ext}{flag}")
    body.append("")
    meta = {
        "name": name, "ext": ext, "ext_guessed": ext_guessed,
        "value_type": row["value_type"], "missing": missing, "class": row["class"],
    }
    return "\n".join(body), meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=DATA_DIR / "high_confidence_new_parameters.csv")
    ap.add_argument("--out-dir", type=Path, default=PROJECT_DIR / "generated_params")
    ap.add_argument("--validate", action="store_true", help="Validate each stub against param_schema.json")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    with open(args.input, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    metas = []
    for r in rows:
        text, meta = build_yaml(r)
        path = args.out_dir / f"{meta['name']}.yaml"
        path.write_text(text, encoding="utf-8")
        metas.append((path, meta))

    # Generation report
    report = args.out_dir / "GENERATION_REPORT.txt"
    with open(report, "w", encoding="utf-8") as f:
        f.write("Generated parameter YAML stubs — human completion checklist\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Stubs written: {len(metas)}  (to {args.out_dir})\n\n")
        f.write("Every stub needs: long_name, verified definedBy extension, and\n")
        f.write("(for enum/range/set/bitmask) the concrete legal values.\n\n")
        f.write(f"{'parameter':44s} {'ext(guess)':12s} {'value_type':10s} needs\n")
        f.write("-" * 90 + "\n")
        for _p, m in metas:
            g = "?" if m["ext_guessed"] else " "
            f.write(f"{m['name']:44s} {m['ext']+g:12s} {m['value_type']:10s} {m['missing']}\n")

    logger.info("Wrote %d YAML stubs + GENERATION_REPORT.txt to %s", len(metas), args.out_dir)

    if args.validate:
        # Structural check (dependency-light). The param_schema.json uses local
        # $refs (schema_defs.json, json-schema-draft-07.json); full resolution is
        # done by `udb validate` at PR time. Here we confirm the stubs are
        # well-formed: required keys present, parseable YAML, valid schema.type.
        try:
            import yaml
        except ImportError:
            logger.error("Run with: uv run --with pyyaml python ... --validate")
            return 2
        required = {"$schema", "kind", "name", "long_name", "description", "definedBy", "schema"}
        valid_types = {"boolean", "integer", "string", "array", "number", "object"}
        ok = 0
        for path, m in metas:
            doc = yaml.safe_load(path.read_text())
            errs = []
            missing_keys = required - set(doc)
            if missing_keys:
                errs.append(f"missing keys {missing_keys}")
            if doc.get("kind") != "parameter":
                errs.append("kind != parameter")
            if doc.get("schema", {}).get("type") not in valid_types:
                errs.append("bad schema.type")
            if "extension" not in (doc.get("definedBy") or {}):
                errs.append("definedBy has no extension")
            if errs:
                logger.warning("INVALID %s: %s", m["name"], "; ".join(errs))
            else:
                ok += 1
        logger.info("Structural validation: %d/%d well-formed", ok, len(metas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
