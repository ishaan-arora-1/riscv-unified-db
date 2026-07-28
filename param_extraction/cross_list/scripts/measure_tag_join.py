# SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""Measure whether the normative tag works as a join key between the lists.

The cross-list comparison cannot use parameter names -- both sides invented
their own. The proposed join key is the normative tag in the ISA manual:

    ours   : excerpt -> enclosing [#norm:...] anchor -> normative rule
    James' : impl-def -> normative rule -> its tag(s)

This script reports, without asserting anything about overlap yet, whether
that chain actually connects on both sides. If coverage is poor the cross-list
document needs a different design, so this runs before either generator.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
NRD = REPO / "ext/riscv-isa-manual/normative_rule_defs"
OURS = REPO / "param_extraction/cross_list/data/ours_canonical.json"
JAMES = Path(
    "/private/tmp/claude-501/-Users-ashish-lfx-riscv-unified-db/"
    "c9469cd6-0086-4537-af44-4c6ac9e12f2f/scratchpad/james/inventory.json"
)
OUT = REPO / "param_extraction/cross_list/data/tag_join_report.json"


def nz(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def load_rules():
    """name -> {tags, file, kind}; plus tag -> [rule names]."""
    rules, by_tag = {}, {}
    for p in sorted(NRD.glob("*.yaml")):
        doc = yaml.safe_load(p.read_text()) or {}
        for e in doc.get("normative_rule_definitions") or []:
            name = e.get("name")
            if not name:
                continue
            raw = e.get("tags") or ([e["tag"]] if e.get("tag") else [])
            # a tag is normally a string, but 21 of them are
            # {name: ..., context: true} -- take the name either way
            tags = [t["name"] if isinstance(t, dict) else t for t in raw]
            rules[nz(name)] = {
                "name": name,
                "file": p.name,
                "kind": e.get("kind"),
                "tags": tags,
            }
            for t in tags:
                by_tag.setdefault(t, []).append(name)
    return rules, by_tag


def main() -> int:
    rules, by_tag = load_rules()
    ours = json.loads(OURS.read_text())["parameters"]
    james = json.loads(JAMES.read_text())

    print(f"normative rules            : {len(rules)}")
    print(f"distinct tags referenced   : {len(by_tag)}")

    # --- our side: anchor -> rule ---------------------------------------
    ours_rows = []
    for r in ours:
        anchor = r.get("norm_anchor")
        hits = by_tag.get(anchor, []) if anchor else []
        ours_rows.append(
            {
                "parameter_name": r["parameter_name"],
                "anchor": anchor,
                "rules": hits,
                "rule_kinds": sorted(
                    {rules[nz(h)]["kind"] or "(none)" for h in hits}
                ),
            }
        )
    o_anchor = sum(1 for r in ours_rows if r["anchor"])
    o_rule = sum(1 for r in ours_rows if r["rules"])
    o_kindparam = sum(1 for r in ours_rows if "parameter" in r["rule_kinds"])

    print()
    print("OUR SIDE")
    print(f"  params                   : {len(ours_rows)}")
    print(f"  with a norm anchor       : {o_anchor}")
    print(f"  anchor -> a rule entry   : {o_rule}")
    print(f"  ...rule is kind:parameter: {o_kindparam}")

    # --- James' side: impl-def -> rule -> tags ---------------------------
    j_rows = []
    for r in james["params"] + james["csrs"]:
        impl = r["impl"]
        impl = impl if isinstance(impl, list) else ([impl] if impl else [])
        tags = []
        for i in impl:
            hit = rules.get(nz(i))
            if hit:
                tags += hit["tags"]
        j_rows.append(
            {
                "name": r.get("name") or f"{r.get('reg')}.{r.get('field')}",
                "kind": "param" if "name" in r and r.get("name") else "csr",
                "impl": impl,
                "tags": sorted(set(tags)),
            }
        )
    j_res = sum(1 for r in j_rows if r["tags"])
    print()
    print("JAMES' SIDE")
    print(f"  entries                  : {len(j_rows)}")
    print(f"  impl-def -> rule -> tag  : {j_res}")
    print(f"  no resolvable tag        : {len(j_rows) - j_res}")

    # --- the join --------------------------------------------------------
    j_by_tag = {}
    for r in j_rows:
        for t in r["tags"]:
            j_by_tag.setdefault(t, []).append(r["name"])

    joined, only_ours = [], []
    for r in ours_rows:
        hit = j_by_tag.get(r["anchor"], []) if r["anchor"] else []
        (joined if hit else only_ours).append(
            {"ours": r["parameter_name"], "anchor": r["anchor"], "james": hit}
        )

    print()
    print("JOIN RESULT (tag-matched)")
    print(f"  our params sharing a tag with James : {len(joined)}")
    print(f"  our params with no James counterpart: {len(only_ours)}")
    for j in joined:
        print(f"    {j['ours']:38} {j['anchor']:34} -> {j['james']}")

    OUT.write_text(
        json.dumps(
            {
                "ours": ours_rows,
                "james": j_rows,
                "joined": joined,
                "only_ours": only_ours,
                "stats": {
                    "ours_total": len(ours_rows),
                    "ours_with_anchor": o_anchor,
                    "ours_anchor_to_rule": o_rule,
                    "james_total": len(j_rows),
                    "james_tag_resolved": j_res,
                    "joined": len(joined),
                },
            },
            indent=1,
        )
        + "\n"
    )
    print(f"\nwrote {OUT.relative_to(REPO)}")

    print()
    print("our anchors that hit NO rule entry:")
    for r in ours_rows:
        if r["anchor"] and not r["rules"]:
            print(f"    {r['parameter_name']:38} {r['anchor']}")
    print()
    print("rule kinds behind our anchors:",
          Counter(k for r in ours_rows for k in r["rule_kinds"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
