#!/usr/bin/env python3
# Copyright (c) 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""
Express our 38 expert-confirmed parameters in James Ball's parameter-definition
format, so his existing toolchain can carry them the rest of the way to UDB.

Why this shape rather than a bespoke converter of our own: his chain already
solves the two hard mechanical steps, and it is the format he proposed as the
shared one, so authoring into it is the merge path rather than a third parallel
track.

    normative_rule_defs/*.yaml ->  create_normative_rules.py -> norm-rules.json
    THIS SCRIPT                ->  param_defs/*.yaml                 |
                                            +-------------------------+
                                   create_params.py     -> params.json
                                   export_params_to_udb.py -> UDB param YAMLs

The one field we cannot always supply is ``impl-def``. His schema constrains
those names to ``^[A-Z][A-Z0-9_]+$``, and the manual only gives a rule an
upper-case name when it is also marked ``impl-def-behavior: true`` -- 185 rules
carry the marking and every one of them has both the upper-case name and a
``kind``/``instance``. Our remaining parameters point at rules that were never
marked, whose names are lower case, so there is no valid ``impl-def`` to write.

His schema permits omitting ``impl-def`` when a ``description`` is present, so
those entries still validate and still compile. But ``export_params_to_udb.py``
then falls back to ``extension: {name: I}`` silently (line 86 of that script),
which is wrong for every one of ours. This script therefore records exactly
which parameters are affected, so the fallback is never mistaken for a result.

Judgement calls (long_name, and how each domain maps onto his type system) live
in ``authoring_table.py``, not here.

Usage:
  uv run --python 3.13 --with pyyaml python scripts/build_param_defs.py
  ... --validate --schema-dir /path/to/docs-resources/schemas   # needs jsonschema
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from authoring_table import AUTHORING, CHAPTER_FILES

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
WORK_DIR = PROJECT_DIR / "udb_export"
REPO_ROOT = PROJECT_DIR.parent

CANONICAL = PROJECT_DIR / "cross_list" / "data" / "ours_canonical.json"
NORM_RULE_DEFS = REPO_ROOT / "ext" / "riscv-isa-manual" / "normative_rule_defs"

# Split so `reuse lint` does not read this literal as a tag on this file and
# fail to parse the trailing newline as a license expression.
SPDX = (
    "SPDX" "-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB "
    "<https://github.com/riscv/riscv-unified-db>\n"
    "SPDX" "-License-Identifier: BSD-3-Clause-Clear\n"
)

# His schemas/param-common-schema.json, #/implDefNamePattern.
IMPL_DEF_NAME = re.compile(r"^[A-Z][A-Z0-9_]+$")

logger = logging.getLogger("build_param_defs")


def load_norm_rules(rule_dir: Path) -> dict[str, list[dict]]:
    """Index every normative rule by each tag it carries.

    A list per tag, not a single rule: several tags carry two entries, one
    naming the implementation-defined behaviour and one naming the ordinary
    normative rules on the same sentence. Keeping only the last silently drops
    the useful one -- that cost us ``SSTATUS_UBE_ACCESS`` on the first pass.
    """
    by_tag: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(rule_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for rule in doc.get("normative_rule_definitions") or []:
            tags = rule.get("tags") or ([rule["tag"]] if "tag" in rule else [])
            for tag in tags:
                if isinstance(tag, str):
                    by_tag[tag].append(rule)
    return by_tag


def resolve_impl_defs(anchor: str | None, by_tag: dict[str, list[dict]]) -> tuple[list[str], str | None]:
    """Return (usable impl-def names, extension instance) for a norm anchor.

    Rules record one name under ``name`` or several under ``names``; both are
    valid impl-def targets. A rule marked ``impl-def-behavior`` wins outright,
    since that marking is what guarantees the upper-case name and the
    ``kind``/``instance`` his exporter needs.
    """
    if not anchor:
        return [], None
    best: tuple[list[str], str | None] = ([], None)
    for rule in by_tag.get(anchor, []):
        candidates = ([rule["name"]] if rule.get("name") else []) + list(rule.get("names") or [])
        usable = [c for c in candidates if IMPL_DEF_NAME.match(c)]
        if not usable:
            continue
        instance = rule.get("instance") or rule.get("instances")
        if rule.get("impl-def-behavior"):
            return usable, instance
        if not best[0]:
            best = (usable, instance)
    return best


def build_entry(param: dict, impl_defs: list[str], authoring: dict) -> dict:
    """One parameter_definitions entry, key order matching his own files."""
    entry: dict = {
        "name": param["parameter_name"],
        "long-name": authoring["long_name"],
    }
    if impl_defs:
        # His schema forbids carrying both keys; singular when there is one.
        if len(impl_defs) == 1:
            entry["impl-def"] = impl_defs[0]
        else:
            entry["impl-defs"] = impl_defs
    entry.update(authoring["shape"])

    # Provenance. His schema is additionalProperties:false, so the spec excerpt,
    # the mentor's verdict and the source line have no field of their own. The
    # description is the only place they can travel, and losing them would cost
    # this list the thing that gives it standing.
    description = [
        param["excerpt"].strip(),
        "",
        f"Source: {param['adoc_path_now']}:{param['line_number_resolved']}"
        + (f" ({param['norm_anchor']})" if param.get("norm_anchor") else " (untagged)"),
        "Confirmed by Allen Baum and Umer."
        if param.get("status") == "confirmed"
        else "Flagged, awaiting a ruling.",
    ]
    entry["description"] = "\n".join(description) + "\n"

    note = authoring.get("note")
    approx = authoring.get("approx")
    if approx:
        note = f"{note} " if note else ""
        note += f"Domain shape is an approximation: {approx}"
    if note:
        entry["note"] = note
    return entry


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--canonical", type=Path, default=CANONICAL)
    ap.add_argument("--rule-defs", type=Path, default=NORM_RULE_DEFS)
    ap.add_argument("--out-dir", type=Path, default=WORK_DIR / "param_defs")
    ap.add_argument("--validate", action="store_true", help="validate against his schema")
    ap.add_argument("--schema-dir", type=Path, help="docs-resources/schemas, for --validate")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    params = json.loads(args.canonical.read_text(encoding="utf-8"))["parameters"]
    by_tag = load_norm_rules(args.rule_defs)

    missing = {p["parameter_name"] for p in params} - set(AUTHORING)
    if missing:
        logger.error("no authoring entry for: %s", ", ".join(sorted(missing)))
        return 2

    chapters: dict[str, list[dict]] = defaultdict(list)
    report: list[dict] = []
    for param in params:
        name = param["parameter_name"]
        authoring = AUTHORING[name]
        impl_defs, instance = resolve_impl_defs(param.get("norm_anchor"), by_tag)
        adoc = param["adoc_file"]
        if adoc not in CHAPTER_FILES:
            logger.error("%s: no chapter file mapped for %s", name, adoc)
            return 2
        chapters[adoc].append(build_entry(param, impl_defs, authoring))
        report.append(
            dict(
                name=name,
                chapter=CHAPTER_FILES[adoc][0],
                impl_defs=impl_defs,
                extension=instance,
                approx=bool(authoring.get("approx")),
                anchor=param.get("norm_anchor"),
            )
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for adoc, entries in sorted(chapters.items()):
        filename, chapter_name = CHAPTER_FILES[adoc]
        doc = {
            "$schema": "../../docs-resources/schemas/param-defs-schema.json#",
            "chapter_name": chapter_name,
            "parameter_definitions": sorted(entries, key=lambda e: e["name"]),
        }
        path = args.out_dir / filename
        header = (
            "# yaml-language-server: "
            "$schema=../../docs-resources/schemas/param-defs-schema.json\n\n"
        )
        path.write_text(
            header + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=88),
            encoding="utf-8",
        )
        # REUSE: his vendored files carry sidecars rather than in-file headers.
        (args.out_dir / f"{filename}.license").write_text(SPDX, encoding="utf-8")
        logger.info("wrote %s (%d parameters)", path.name, len(entries))

    (args.out_dir / "build_report.json").write_text(
        json.dumps(report, indent=1) + "\n", encoding="utf-8"
    )
    (args.out_dir / "build_report.json.license").write_text(SPDX, encoding="utf-8")

    resolved = [r for r in report if r["impl_defs"]]
    blocked = [r for r in report if not r["impl_defs"]]
    approx = [r for r in report if r["approx"]]
    logger.info("")
    logger.info("parameters authored          : %d", len(report))
    logger.info("  usable impl-def            : %d  (definedBy will be correct)", len(resolved))
    logger.info("  no impl-def available      : %d  (exporter will emit extension: I)", len(blocked))
    logger.info("  domain shape approximated  : %d  (needs a human ruling)", len(approx))
    if blocked:
        logger.info("")
        logger.info("blocked -- the rule behind each is not marked impl-def-behavior:")
        for r in sorted(blocked, key=lambda x: x["name"]):
            logger.info("    %-38s %s", r["name"], r["anchor"] or "(no tag at all)")

    if args.validate:
        return validate(args.out_dir, args.schema_dir)
    return 0


def validate(out_dir: Path, schema_dir: Path | None) -> int:
    """Validate each generated file against his param-defs-schema.json."""
    if not schema_dir:
        logger.error("--validate needs --schema-dir pointing at docs-resources/schemas")
        return 2
    try:
        from jsonschema import Draft7Validator, RefResolver
    except ImportError:
        logger.error("run with: uv run --with pyyaml --with jsonschema python ...")
        return 2

    schema = json.loads((schema_dir / "param-defs-schema.json").read_text())
    store = {}
    for path in schema_dir.glob("*.json"):
        store[path.name] = json.loads(path.read_text())
    resolver = RefResolver(base_uri="", referrer=schema, store=store)
    validator = Draft7Validator(schema, resolver=resolver)

    failed = 0
    for path in sorted(out_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
        if errors:
            failed += 1
            for err in errors[:4]:
                logger.error("%s: %s at %s", path.name, err.message, list(err.path))
        else:
            logger.info("valid: %s", path.name)
    if failed:
        logger.error("%d file(s) failed validation", failed)
        return 1
    logger.info("all files validate against param-defs-schema.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
