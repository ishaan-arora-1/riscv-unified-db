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
JDIR = REPO / "param_extraction/cross_list/data/james_param_defs"
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
                "impl_def": bool(e.get("impl-def-behavior")),
                "tags": tags,
            }
            for t in tags:
                by_tag.setdefault(t, []).append(name)
    return rules, by_tag


def load_james():
    """His entries, read straight from the vendored param_defs."""
    params, csrs = [], []
    for p in sorted(JDIR.glob("*.yaml")):
        doc = yaml.safe_load(p.read_text()) or {}
        for e in doc.get("parameter_definitions") or []:
            params.append({"name": e.get("name"),
                           "impl": e.get("impl-def") or e.get("impl-defs")})
        for e in doc.get("csr_definitions") or []:
            reg = e.get("reg-name") or e.get("reg-names")
            reg = reg if isinstance(reg, str) else "/".join(reg)
            fld = e.get("field-name")
            csrs.append({"name": f"{reg}.{fld}" if fld else reg,
                         "reg": reg, "field": fld,
                         "impl": e.get("impl-def") or e.get("impl-defs")})
    return {"params": params, "csrs": csrs}


def main() -> int:
    rules, by_tag = load_rules()
    ours = json.loads(OURS.read_text())["parameters"]
    james = load_james()

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
                "impl_def_marked": any(
                    rules[nz(h)]["impl_def"] for h in hits
                ),
            }
        )
    o_anchor = sum(1 for r in ours_rows if r["anchor"])
    o_rule = sum(1 for r in ours_rows if r["rules"])
    o_marked = sum(1 for r in ours_rows if r["impl_def_marked"])

    print()
    print("OUR SIDE")
    print(f"  params                   : {len(ours_rows)}")
    print(f"  with a norm anchor       : {o_anchor}")
    print(f"  anchor -> a rule entry   : {o_rule}")
    print(f"  ...marked impl-def-behavior: {o_marked}")

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
    print("impl-def-behavior behind our anchors:",
          Counter(r["impl_def_marked"] for r in ours_rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
