# SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""Segment James' 'only on his list' entries against the 223 UDB parameters.

"Only on James' list" mixes three very different things, and reporting them as
one number is misleading:

  * parameters UDB already has -- a scope difference, since our list is
    restricted to parameters believed MISSING from UDB;
  * things outside the ISA parameter space entirely (platform devices,
    memory-map regions, emulator knobs);
  * genuinely new candidates.

Name matching fails here for the same reason it failed between the two
candidate lists: James invented his names and UDB has its own. So this
gathers several independent signals per entry and writes an evidence file
for hand adjudication rather than deciding automatically.

Signals, strongest first:
  1. exact normalised name equality with a UDB parameter
  2. (csr, field) equality against UDB's csr_references, which carry the
     CSR and field each parameter controls
  3. (csr) equality, field unmatched
  4. token overlap between his name and UDB names/descriptions
"""

import json
import os
import re
import sys
from glob import glob
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
BASE = REPO / "param_extraction/cross_list"
GT = REPO / "param_extraction/data/ground_truth.json"
JDIR = BASE / "data/james_param_defs"
OURS = BASE / "data/ours_canonical.json"
OUT = BASE / "data/james_vs_udb_evidence.json"

STOP = {
    "the", "and", "are", "for", "not", "may", "can", "that", "this", "which",
    "when", "with", "all", "any", "other", "some", "from", "its", "has",
    "have", "implementation", "implementations", "register", "registers",
    "bit", "bits", "value", "values", "read", "only", "write", "field",
    "warl", "impl", "supported", "support", "param", "csr", "tbd",
}


def nz(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def toks(s):
    return {t for t in re.findall(r"[a-z][a-z0-9]{2,}", (s or "").lower())
            if t not in STOP}


def load_udb():
    gt = json.loads(GT.read_text())["parameters"]
    udb = gt if isinstance(gt, dict) else {p["name"]: p for p in gt}
    by_nz = {nz(k): k for k in udb}
    pair, csr_only = {}, {}
    for k, v in udb.items():
        for c in v.get("csr_references") or []:
            pair.setdefault((nz(c.get("csr")), nz(c.get("field"))), set()).add(k)
            csr_only.setdefault(nz(c.get("csr")), set()).add(k)
    return udb, by_nz, pair, csr_only


def load_james():
    out = []
    for p in sorted(glob(str(JDIR / "*.yaml"))):
        doc = yaml.safe_load(Path(p).read_text()) or {}
        f = os.path.basename(p)
        for e in doc.get("parameter_definitions") or []:
            out.append({
                "name": e.get("name"), "section": "parameter_definitions",
                "reg": None, "field": None, "file": f,
                "impl": e.get("impl-def") or e.get("impl-defs"),
                "desc": " ".join((e.get("description") or "").split())[:200],
            })
        for e in doc.get("csr_definitions") or []:
            reg = e.get("reg-name") or e.get("reg-names")
            reg = reg if isinstance(reg, str) else "/".join(reg)
            fld = e.get("field-name")
            out.append({
                "name": f"{reg}.{fld}" if fld else reg,
                "section": "csr_definitions", "reg": reg, "field": fld,
                "file": f, "impl": e.get("impl-def") or e.get("impl-defs"),
                "desc": "",
            })
    return out


def main() -> int:
    udb, by_nz, pair, csr_only = load_udb()
    james = load_james()

    # exactly the "only on James' list" set emitted by generate_asciidoc.py
    only = set(json.loads((BASE / "data/only_james.json").read_text()))

    rows = []
    for j in james:
        if j["name"] not in only:
            continue
        ev = {"exact": None, "csr_field": [], "csr_any": [], "tokens": []}

        hit = by_nz.get(nz(j["name"]))
        if hit:
            ev["exact"] = hit

        if j["section"] == "csr_definitions":
            reg = (j["reg"] or "").split("/")[0]
            k = (nz(reg), nz(j["field"]))
            ev["csr_field"] = sorted(pair.get(k, []))
            if not ev["csr_field"]:
                ev["csr_any"] = sorted(csr_only.get(nz(reg), []))[:8]

        jt = toks(j["name"]) | toks(j["desc"]) | toks(str(j["impl"]))
        scored = []
        for k, v in udb.items():
            sh = jt & (toks(k) | toks(v.get("description", "")))
            if len(sh) >= 2:
                scored.append((len(sh), k, sorted(sh)[:4]))
        scored.sort(reverse=True)
        ev["tokens"] = [{"udb": k, "shared": s} for _, k, s in scored[:5]]

        rows.append({**j, "evidence": ev})

    OUT.write_text(json.dumps({"count": len(rows), "rows": rows}, indent=1) + "\n")
    print(f"entries to segment : {len(rows)}")
    print(f"  exact name hit   : {sum(1 for r in rows if r['evidence']['exact'])}")
    print(f"  (csr,field) hit  : {sum(1 for r in rows if r['evidence']['csr_field'])}")
    print(f"  csr-only hit     : {sum(1 for r in rows if r['evidence']['csr_any'])}")
    print(f"  token hit only   : "
          f"{sum(1 for r in rows if not r['evidence']['exact'] and not r['evidence']['csr_field'] and not r['evidence']['csr_any'] and r['evidence']['tokens'])}")
    print(f"  no signal at all : "
          f"{sum(1 for r in rows if not any([r['evidence']['exact'], r['evidence']['csr_field'], r['evidence']['csr_any'], r['evidence']['tokens']]))}")
    print(f"\nwrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
