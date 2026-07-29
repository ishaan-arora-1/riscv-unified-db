# SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""Generate the two AsciiDoc deliverables for the Parameter SIG.

  out/parameter_lists.adoc  -- each list normalised to Name / Domain / Source
  out/list_comparison.adoc  -- the two lists compared

Design decisions worth knowing before reading the code:

* The comparison joins on the **normative tag**, not on parameter name. Both
  sides invented their own names; only 3 of our 38 collide with James' names,
  while 19 share a normative tag. Name equality is reported as corroborating
  evidence, never as the join.

* James' ``csr_definitions`` are treated as parameters. The mentor's rule is
  "IF it is WARL, it is automatically a parameter", and that section is a
  catalogue of WARL fields; 11 of the 19 tag matches come from it and every one
  lands on a mentor-confirmed row of ours. Granularity (field-level vs
  register-level) is carried as a column instead of being flattened away.

* Relationship vocabulary follows Jordan's sail_udb_config_mapping.md so the
  three documents read as one family: Exact / Partial / Transform needed.

* Domains are emitted only where they are actually known. Our list carries a
  coarse ``value_type`` (a shape, not a domain), so a domain is derived only
  where the class makes it unambiguous and is otherwise printed as TBD rather
  than invented. James' TBD placeholders are likewise passed through as TBD.
"""

import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
BASE = REPO / "param_extraction/cross_list"
OURS = BASE / "data/ours_canonical.json"
JDIR = BASE / "data/james_param_defs"
NRD = REPO / "ext/riscv-isa-manual/normative_rule_defs"
OUTDIR = BASE / "out"

JAMES_SHA = "213450b8671a513ed94cd62fc87a836f8a839a10"
MANUAL_SHA = "7fc198f13ad89e9608e9404be1c7a8119c14c13b"


def nz(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def esc(s):
    """Escape a cell for an AsciiDoc table."""
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


# ---------------------------------------------------------------- rules ----
def load_rules():
    rules, by_tag = {}, {}
    for p in sorted(NRD.glob("*.yaml")):
        doc = yaml.safe_load(p.read_text()) or {}
        for e in doc.get("normative_rule_definitions") or []:
            name = e.get("name")
            if not name:
                continue
            raw = e.get("tags") or ([e["tag"]] if e.get("tag") else [])
            tags = [t["name"] if isinstance(t, dict) else t for t in raw]
            rules[nz(name)] = {"name": name, "kind": e.get("kind"), "tags": tags}
            for t in tags:
                by_tag.setdefault(t, []).append(name)
    return rules, by_tag


# ----------------------------------------------------------- our domains ----
# Domains that cannot be derived from class alone, read off the spec excerpt.
# Kept as an explicit table so each one can be checked against the sentence it
# came from rather than being buried in branching logic.
EXPLICIT_DOMAINS = {
    "CSR_STRONGLY_ORDERED":
        "subset of the implemented CSRs (possibly empty)",
    "CTR_CCE_WIDTH":
        "integer [0..4] exponent bits",
    "HPM_UNIMPLEMENTED_ACCESS_BEHAVIOR":
        "{raise illegal-instruction exception, return a constant value}",
    "HTVAL_LEGAL_VALUES":
        "{0} plus an implementation-chosen subset of "
        "2-bit-shifted guest physical addresses",
    "MTVAL2_LEGAL_VALUES":
        "{0} plus an implementation-chosen subset of "
        "2-bit-shifted guest physical addresses",
    "PMA_IDEMPOTENT_IMPLICIT_READ_SIZE":
        "power-of-2 bytes, not exceeding the smallest supported page size",
    # value table taken from James' smctr.yaml, which enumerates the encoding
    "SCTRDEPTH_SUPPORTED_VALUES":
        "non-empty subset of {0,1,2,3,4} = {16,32,64,128,256} entries",
    "SISELECT_WIDTH":
        "supported range 0..N, N >= 0xFFF",
    "VSISELECT_WIDTH":
        "supported range 0..N, N >= 0xFFF",
}


def our_domain(rec):
    """Derive a domain only where the class or the excerpt fixes it."""
    name, cls, vt = rec["parameter_name"], rec["class"], rec["value_type"]
    if name in EXPLICIT_DOMAINS:
        return EXPLICIT_DOMAINS[name], "read from excerpt"
    if cls == "NORM_CSR_RW" and vt == "binary":
        # the mentor's own repeated formulation for these rows
        return "{read-write, read-only-0}", "derived from class"
    if cls == "NORM_CSR_RW" and vt == "bitmask":
        return "per bit: {read-write, read-only-0}", "derived from class"
    if vt == "binary":
        return "{true, false}", "derived from value_type"
    if vt == "bitmask":
        return "per bit: {true, false}", "derived from value_type"
    return f"TBD (shape: {vt})", "TBD"


# --------------------------------------------------------- james domains ----
def james_domain(e):
    if "range" in e:
        lo, hi = e["range"]
        return f"[{lo}..{hi}]", "declared"
    t = e.get("type")
    if isinstance(t, list):
        return "{" + ", ".join(str(x) for x in t) + "}", "declared"
    if t == "boolean":
        return "{true, false}", "declared"
    if t == "ConstMask":
        return "per bit: constant mask", "declared"
    if t == "LegalEnum":
        return "TBD (legal enum)", "TBD"
    if t == "Other":
        return "TBD", "TBD"
    return "TBD", "TBD"


def load_james(rules):
    out = []
    for p in sorted(JDIR.glob("*.yaml")):
        doc = yaml.safe_load(p.read_text()) or {}
        chap = doc.get("chapter_name") or p.stem
        for e in doc.get("parameter_definitions") or []:
            dom, src = james_domain(e)
            out.append(_jrec(e, e.get("name"), "parameter_definitions",
                             "n/a", chap, p.name, dom, src, rules))
        for e in doc.get("csr_definitions") or []:
            reg = e.get("reg-name") or e.get("reg-names")
            reg = reg if isinstance(reg, str) else "/".join(reg)
            fld = e.get("field-name")
            name = f"{reg}.{fld}" if fld else reg
            dom, src = james_domain(e)
            out.append(_jrec(e, name, "csr_definitions",
                             "field-level" if fld else "register-level",
                             chap, p.name, dom, src, rules))
    return out


def _jrec(e, name, section, gran, chap, fname, dom, domsrc, rules):
    impl = e.get("impl-def") or e.get("impl-defs")
    impl = impl if isinstance(impl, list) else ([impl] if impl else [])
    tags, kinds = [], []
    for i in impl:
        hit = rules.get(nz(i))
        if hit:
            tags += hit["tags"]
            kinds.append(hit["kind"] or "(none)")
    return {
        "list": "james",
        "name": name,
        "section": section,
        "granularity": gran,
        "chapter": chap,
        "file": fname,
        "domain": dom,
        "domain_source": domsrc,
        "impl_defs": impl,
        "tags": sorted(set(tags)),
        "rule_kinds": sorted(set(kinds)),
        "status": "individual draft (not SIG consensus)",
    }


def load_ours(by_tag, rules):
    doc = json.loads(OURS.read_text())
    out = []
    for r in doc["parameters"]:
        dom, domsrc = our_domain(r)
        anchor = r.get("norm_anchor")
        hits = by_tag.get(anchor, []) if anchor else []
        out.append({
            "list": "ours",
            "name": r["parameter_name"],
            "aliases": r.get("aliases") or [],
            "section": "confirmed_parameters",
            "granularity": "field-level",
            "chapter": r["adoc_file"],
            "file": r["adoc_file"],
            "domain": dom,
            "domain_source": domsrc,
            "tags": [anchor] if anchor else [],
            "rules": hits,
            "rule_kinds": sorted({rules[nz(h)]["kind"] or "(none)" for h in hits}),
            "line": r["line_number_resolved"],
            "excerpt": r["excerpt"],
            "class": r["class"],
            "value_type": r["value_type"],
            "mentor_verdict": r["mentor_verdict"],
            "status": ("expert-confirmed (Allen Baum + Umer)"
                       if r["status"] == "confirmed" else "flagged, needs ruling"),
            "flag": r.get("flag"),
        })
    return out, doc


HDR = f"""//
// SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB
// SPDX-License-Identifier: BSD-3-Clause-Clear
//
// GENERATED FILE -- do not edit by hand.
// Regenerate: uv run --python 3.13 --with pyyaml python \\
//   param_extraction/cross_list/scripts/generate_asciidoc.py
//
// Pinned sources:
//   James' param_defs : {JAMES_SHA} (2026-04-03)
//   ISA manual        : {MANUAL_SHA} (2026-02-15)
//
"""


def write_lists(ours, james, meta):
    L = [HDR, "= Architectural Parameter Lists", ":toc:", ":toclevels: 2", ""]
    L += [
        "Two independently produced candidate parameter lists, normalised to a",
        "common shape: *Name*, *Domain* (the set of values an implementation may",
        "choose from) and *Source* (where the claim comes from in the ISA manual).",
        "",
        "IMPORTANT: The two lists have different scope and different standing.",
        "Ours contains only parameters believed *missing* from UDB, and every entry",
        "was reviewed individually by Allen Baum and Umer. James' list re-derives",
        "the parameter space from normative-rule tags and includes parameters UDB",
        "already has; he describes it as an initial individual effort, not SIG",
        "consensus. Counts are therefore not comparable head-to-head.",
        "",
        "A Domain of `TBD` means the source has not yet fixed the legal-value set.",
        "It is left blank rather than guessed.",
        "",
    ]

    L += ["== List A -- our pipeline (expert-reviewed)", ""]
    L += [
        f"{meta['input_rows']} reviewed rows reduce to *{meta['canonical_count']}*",
        f"distinct parameters ({meta['confirmed']} confirmed, {meta['flagged']} flagged):",
        f"{len(meta['merged_pairs'])} rows were the same spec sentence recorded twice",
        f"under two names, and {len(meta['dropped'])} were already defined in UDB.",
        "See <<corrections>>.",
        "",
        '[cols="26,24,26,24",options="header"]',
        "|===",
        "| Name | Domain | Source (normative tag) | Status",
    ]
    for r in sorted(ours, key=lambda x: x["name"]):
        tag = r["tags"][0] if r["tags"] else "(untagged)"
        src = f"`{tag}` +\n{r['file']}:{r['line']}"
        L.append(f"| `{esc(r['name'])}` | {esc(r['domain'])} | {src} "
                 f"| {esc(r['status'])}")
    L += ["|===", ""]

    L += ["== List B -- James Ball's list", ""]
    npar = sum(1 for r in james if r["section"] == "parameter_definitions")
    ncsr = len(james) - npar
    L += [
        f"*{len(james)}* entries: {npar} from `parameter_definitions` and",
        f"{ncsr} from `csr_definitions`. The latter are counted as parameters",
        "here (a WARL field behaviour is a parameter), with register-level and",
        "field-level entries distinguished in the Granularity column.",
        "",
        '[cols="24,20,22,16,18",options="header"]',
        "|===",
        "| Name | Domain | Source (normative rule) | Granularity | Chapter",
    ]
    for r in sorted(james, key=lambda x: (x["file"], x["name"] or "")):
        impl = ", ".join(f"`{i}`" for i in r["impl_defs"]) or "(none)"
        unres = "" if r["tags"] else " +\n[.small]#unresolved in pinned manual#"
        L.append(f"| `{esc(r['name'])}` | {esc(r['domain'])} | {impl}{unres} "
                 f"| {r['granularity']} | {esc(r['chapter'])}")
    L += ["|===", ""]

    L += ["[[corrections]]", "== Corrections applied to List A", ""]
    L += ["Recorded so the changes are auditable rather than silent.", ""]
    L += ["=== Merged (one spec sentence, two names)", ""]
    L += ["Each of these sentences occurs exactly once in the manual, so the pair",
          "is one parameter named twice, not the m/s/vs replication pattern.", ""]
    for m in meta["merged_pairs"]:
        L.append(f"* `{m['discarded']}` merged into `{m['merged_into']}`")
    L += ["", "=== Dropped (already defined in UDB)", ""]
    for d in meta["dropped"]:
        L.append(f"* `{d['parameter_name']}` -- {d['reason']}")
    L += ["", "=== Flagged (kept, needs a ruling)", ""]
    for r in ours:
        if r.get("flag"):
            L.append(f"* `{r['name']}` -- {r['flag']}")
    L.append("")
    return "\n".join(L)


def write_comparison(ours, james, meta):
    j_by_tag = {}
    for r in james:
        for t in r["tags"]:
            j_by_tag.setdefault(t, []).append(r)

    matched, only_ours = [], []
    for r in sorted(ours, key=lambda x: x["name"]):
        tag = r["tags"][0] if r["tags"] else None
        hits = j_by_tag.get(tag, []) if tag else []
        if hits:
            matched.append((r, hits))
        else:
            only_ours.append(r)

    ours_tags = {r["tags"][0] for r in ours if r["tags"]}
    only_james = [r for r in james
                  if not (set(r["tags"]) & ours_tags)]

    L = [HDR, "= Parameter List Comparison", ":toc:", ":toclevels: 2", ""]
    L += [
        "Comparison of our expert-reviewed parameter list against James Ball's.",
        "",
        "== Method, and why not by name",
        "",
        "Both lists invented their own parameter names, so name equality is not a",
        "usable join. Measured: only *3* of our 38 names collide with James',",
        "against *19* that share a normative tag. A name-based comparison would",
        "report the two efforts as ~97% disjoint, which is an artefact of naming,",
        "not a real finding.",
        "",
        "The join is therefore the *normative tag* in the ISA manual:",
        "",
        "* ours -- excerpt -> enclosing `[#norm:...]` anchor -> normative rule",
        "* James' -- `impl-def` -> normative rule -> its tag(s)",
        "",
        "Coverage of that chain: 37 of our 38 sit in a norm anchor and 35 reach a",
        "rule entry; 135 of James' 179 entries resolve to a tag. Name equality is",
        "reported below as corroboration where it happens, never as the join.",
        "",
        "Relationship vocabulary follows Jordan's `sail_udb_config_mapping.md`:",
        "*Exact* (one-to-one), *Partial* (concepts overlap but not one-to-one, for",
        "example one umbrella entry against several fine-grained ones).",
        "",
        "== Summary",
        "",
        '[cols="60,40",options="header"]',
        "|===",
        "| Measure | Count",
        f"| Our parameters (expert-confirmed, de-duplicated) | {len(ours)}",
        f"| James' entries | {len(james)}",
        f"| Shared a normative tag | {len(matched)}",
        f"| Only on our list | {len(only_ours)}",
        f"| Only on James' list | {len(only_james)}",
        "|===",
        "",
    ]

    L += ["== Parameters on both lists", "",
          '[cols="24,24,16,36",options="header"]', "|===",
          "| Our name | James' name(s) | Relationship | Shared tag / note"]
    for r, hits in matched:
        jn = ", ".join(f"`{h['name']}`" for h in hits)
        rel = "Exact" if len(hits) == 1 else "Partial (1-to-N)"
        note = f"`{r['tags'][0]}`"
        same = [h for h in hits if nz(h["name"]) == nz(r["name"])]
        if same:
            note += " +\nname also matches"
        L.append(f"| `{esc(r['name'])}` | {jn} | {rel} | {note}")
    L += ["|===", ""]

    L += ["== Only on our list", "",
          "Candidates for adding to James' list and to the ISA manual metadata.",
          "",
          '[cols="26,30,20,24",options="header"]', "|===",
          "| Name | Domain | Tag | Why James' method missed it"]
    for r in only_ours:
        tag = r["tags"][0] if r["tags"] else "(untagged)"
        if not r["tags"]:
            why = "text carries no normative tag at all"
        elif not r["rules"]:
            why = "tagged, but no normative rule entry exists"
        elif "parameter" not in r["rule_kinds"]:
            why = "rule exists but is not marked `kind: parameter`"
        else:
            why = "rule is marked `kind: parameter` -- genuine gap"
        L.append(f"| `{esc(r['name'])}` | {esc(r['domain'])} | `{tag}` | {why}")
    L += ["|===", ""]

    L += ["== Only on James' list", "",
          "Expected: his list re-derives the whole parameter space including",
          "parameters UDB already has, while ours is restricted to parameters",
          "believed missing from UDB. Most entries here are therefore a scope",
          "difference, not a gap in our work.",
          "",
          '[cols="26,24,20,30",options="header"]', "|===",
          "| Name | Domain | Granularity | Source"]
    for r in sorted(only_james, key=lambda x: (x["file"], x["name"] or "")):
        impl = ", ".join(f"`{i}`" for i in r["impl_defs"]) or "(none)"
        if not r["tags"]:
            impl += " +\n[.small]#unresolved in pinned manual#"
        L.append(f"| `{esc(r['name'])}` | {esc(r['domain'])} | {r['granularity']} "
                 f"| {impl}")
    L += ["|===", ""]

    # findings that are useful to the manual maintainers
    nokind = [r for r in only_ours if r["rules"]
              and "parameter" not in r["rule_kinds"]]
    norule = [r for r in only_ours if r["tags"] and not r["rules"]]
    untag = [r for r in only_ours if not r["tags"]]
    unres = [r for r in james if not r["tags"]]

    L += ["== Findings for the ISA manual", "",
          "Fallout from the join that is directly actionable in the manual repo.",
          "",
          f"=== {len(nokind)} tagged rules that are parameters but not marked as such",
          "",
          "These carry a normative tag and a rule entry, but the rule is not",
          "marked `kind: parameter`. Since James' method selects on exactly that",
          "marking, this is why his list does not have them -- a metadata gap, not",
          "a difference of judgement. Each was individually confirmed as a real",
          "parameter by Allen Baum and Umer.",
          ""]
    for r in nokind:
        L.append(f"* `{r['tags'][0]}` -- our `{r['name']}` ({r['file']}:{r['line']})")

    L += ["", f"=== {len(norule)} anchors with no normative rule entry", ""]
    for r in norule:
        L.append(f"* `{r['tags'][0]}` -- our `{r['name']}` ({r['file']}:{r['line']})")

    L += ["", f"=== {len(untag)} confirmed parameter with no tag at all", ""]
    for r in untag:
        L.append(f"* our `{r['name']}` ({r['file']}:{r['line']}) -- "
                 "normative text carrying no anchor")

    L += ["", f"=== {len(unres)} of James' entries reference an unresolved tag", "",
          "These `impl-def` names have no matching normative rule in the pinned",
          f"manual ({MANUAL_SHA[:8]}, 2026-02-15). His definitions are about seven",
          "weeks newer, so some may already exist upstream and others are likely",
          "tags he is proposing. Worth confirming with him rather than assuming.",
          ""]
    seen = set()
    for r in unres:
        for i in r["impl_defs"]:
            if i not in seen:
                seen.add(i)
    L.append("* " + ", ".join(f"`{i}`" for i in sorted(seen)))
    L.append("")
    return "\n".join(L)


def main() -> int:
    rules, by_tag = load_rules()
    ours, meta = load_ours(by_tag, rules)
    james = load_james(rules)
    OUTDIR.mkdir(parents=True, exist_ok=True)

    (OUTDIR / "parameter_lists.adoc").write_text(write_lists(ours, james, meta))
    (OUTDIR / "list_comparison.adoc").write_text(
        write_comparison(ours, james, meta))

    print(f"ours   : {len(ours)}")
    print(f"james  : {len(james)}")
    print(f"wrote  : {(OUTDIR / 'parameter_lists.adoc').relative_to(REPO)}")
    print(f"wrote  : {(OUTDIR / 'list_comparison.adoc').relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
