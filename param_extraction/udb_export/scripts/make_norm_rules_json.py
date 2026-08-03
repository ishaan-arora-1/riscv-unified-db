#!/usr/bin/env python3
# Copyright (c) 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""
Produce the ``norm-rules.json`` that ``create_params.py`` consumes, directly
from the manual's ``normative_rule_defs/*.yaml``.

This stands in for ``create_normative_rules.py``, which additionally wants tag
JSON emitted by the manual's asciidoctor build. That build is not needed here:
``create_params.py`` only indexes the rules by name and reads ``kind``,
``instance`` and ``impl-def-category`` off them (see ``rules_by_name`` and
``resolve_impldef_entries`` in that file). Everything it touches is already in
the YAML.

What this deliberately does NOT do is verify that each rule's tag actually
appears in the rendered manual. That check is the real job of
``create_normative_rules.py``, so run the genuine tool before anything ships.
This is a local shortcut for driving the rest of the chain, nothing more.

One subtlety worth keeping: a rule may name several behaviours under ``names``
rather than one under ``name``, and ``rules_by_name`` only ever reads ``name``.
Plural entries are therefore expanded into one entry per name, which is what
lets ``MEDELEG_WARL``/``MIDELEG_WARL`` and the four ``*_INTR_IMPL`` rules
resolve at all.

Usage:
  uv run --python 3.13 --with pyyaml python scripts/make_norm_rules_json.py -o build/norm-rules.json
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
WORK_DIR = SCRIPT_DIR.parent
REPO_ROOT = WORK_DIR.parent.parent
NORM_RULE_DEFS = REPO_ROOT / "ext" / "riscv-isa-manual" / "normative_rule_defs"

# Carried through to the output; anything else in the YAML is for the manual's
# own tooling and would only be noise here. ``instance``/``instances`` are
# handled separately because they need normalising -- see below.
PASSTHROUGH = ("kind", "impl-def-behavior", "impl-def-category",
               "summary", "description")

logger = logging.getLogger("make_norm_rules")


def build(rule_dir: Path) -> list[dict]:
    rules: list[dict] = []
    seen: dict[str, str] = {}
    for path in sorted(rule_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for rule in doc.get("normative_rule_definitions") or []:
            names = ([rule["name"]] if rule.get("name") else []) + list(rule.get("names") or [])
            tags = rule.get("tags") or ([rule["tag"]] if "tag" in rule else [])
            for name in names:
                if name in seen:
                    # create_params.py treats a duplicate name as fatal, so drop
                    # the later one and say so rather than emitting a file that
                    # cannot be consumed.
                    logger.warning(
                        "duplicate rule name %s (%s and %s) -- keeping the first",
                        name, seen[name], path.name,
                    )
                    continue
                seen[name] = path.name
                entry = {"name": name, "tags": [t for t in tags if isinstance(t, str)]}
                for key in PASSTHROUGH:
                    if key in rule:
                        entry[key] = rule[key]
                # The rule defs write a single extension as ``instance: Sm``,
                # but norm-rules-schema.json only has ``instances``, and
                # export_params_to_udb.py reads nothing else -- a singular
                # ``instance`` passed through raw makes every parameter fall
                # through to its ``extension: I`` default. The real
                # create_normative_rules.py folds one into the other
                # (lines 183-192); do the same.
                instances = []
                if rule.get("instance") is not None:
                    instances.append(rule["instance"])
                if rule.get("instances") is not None:
                    instances.extend(rule["instances"])
                if instances:
                    entry["instances"] = instances
                rules.append(entry)
    return rules


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rule-defs", type=Path, default=NORM_RULE_DEFS)
    ap.add_argument("-o", "--output", type=Path, default=WORK_DIR / "build" / "norm-rules.json")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    rules = build(args.rule_defs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"normative_rules": rules}, indent=2) + "\n", encoding="utf-8"
    )
    marked = sum(1 for r in rules if r.get("impl-def-behavior"))
    logger.info("wrote %s", args.output)
    logger.info("  rules: %d   marked impl-def-behavior: %d", len(rules), marked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
