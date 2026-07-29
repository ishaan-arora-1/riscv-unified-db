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


# ------------------------------------------------------- adjudication ------
# The tag join alone is not sufficient. 44 of James' entries carry an
# ``impl-def`` that does not resolve against the pinned manual, and his
# ``csr_definitions`` are hand-authored per register, so wherever he covers a
# concept through an unresolved name the tag join wrongly reports it as ours
# alone. These were found by checking all of our unmatched parameters against
# his full file set by register, field and concept, then confirming each by
# hand. Recorded as a table so every one can be re-checked individually.
MANUAL_MATCHES = {
    "CTR_CCE_WIDTH": (
        ["CTR_CCOUNTER_IMPL"], "Exact",
        "Same 0..4 exponent-bit choice in CCE. Missed only because his "
        "impl-def is `CTR_CCOUNTER_IMPL` while the rule is named "
        "`ccounter_impl`.",
    ),
    "DELEGATABLE_EXCEPTIONS": (
        ["medeleg", "mideleg"], "Partial (1-to-2)",
        "He records the delegatable-bit mask once per register "
        "(`MEDELEG_WARL`, `MIDELEG_WARL`, both unresolved); ours is the "
        "single statement covering both.",
    ),
    "HIP_BIT_WRITABLE": (
        ["hip"], "Partial (register-level)",
        "His `hip` entry is a register-level WARL umbrella (`HIP_WARL`, "
        "unresolved); ours is the per-bit rule conditioned on `sie` bit i "
        "being read-only zero.",
    ),
    "MNEPC_INVALID_ADDRESS_CONVERSION": (
        ["mnepc"], "Partial (register-level)",
        "His `mnepc` entry is register-level WARL (`MNEPC_WARL`, "
        "unresolved); ours is specifically the invalid-address conversion.",
    ),
    "SIP_BITS_ACCESS": (
        ["sip"], "Partial (register-level)",
        "His `sip` entry is register-level WARL (`SIP_WARL`, unresolved); "
        "ours is the per-bit writable-or-read-only rule.",
    ),
    "STANDARD_INTERRUPT_SUPPORT": (
        ["SEI_INTR_IMPL", "STI_INTR_IMPL", "SSI_INTR_IMPL", "LCOFI_INTR_IMPL"],
        "Partial (1-to-4)",
        "He enumerates one parameter per standard interrupt type; ours is "
        "the single umbrella sentence naming all four.",
    ),
    "XRET_CLEARS_LR_RESERVATION": (
        ["MRET_CLR_LR_RESV", "SRET_CLR_LR_RESV"], "Partial (1-to-2)",
        "He splits the `__x__RET` rule into MRET and SRET variants.",
    ),
}

# Concepts that overlap but where calling it a match is a judgement, not a
# fact. Reported in their own section rather than silently resolved either way.
ARGUABLE_MATCHES = {
    "CTRTARGET_MISP_IMPLEMENTED": (
        ["ctrtarget"],
        "MISP is verified to be a field of `ctrtarget` (section at "
        "smctr.adoc:314, bitfield at :331), so the register is right. But his "
        "entry is a register-level WARL umbrella and says nothing about the "
        "optional MISP bit being read-only 0 when unimplemented.",
    ),
    "MSTATEEN_BIT63_TYPE": (
        ["mstateen0/mstateen1/mstateen2/mstateen3"],
        "He has one `ConstMask` entry covering all four `mstateen` "
        "registers, which arguably subsumes bit 63; it does not carry the "
        "condition (hypervisor absent and matching `sstateen` all "
        "read-only zero) that makes ours specific.",
    ),
    "HPM_MISCONFIGURED_BEHAVIOR": (
        ["HPM_READ_BEHAVIOR"],
        "His `HPM_READ_BEHAVIOR` draws on `HPM_PLATFORM_SPECIFIC_IMPL` and "
        "`HPM_UNIMPLEMENTED_COUNTER_ACCESS`. Ours is misconfigured *event "
        "selection*, which is a different axis from counter read access; "
        "whether his entry is meant to span it is unclear.",
    ),
    "ZALASR_MISALIGNED_ATOMICITY_GRANULE": (
        ["PMA_MAG_OP_LDST", "PMA_MAG_EXC"],
        "He has misaligned-atomicity-granule PMA parameters in "
        "`machine.yaml`. Ours is the Zalasr-specific relaxation referring to "
        "that same PMA. Already flagged separately as overlapping UDB's "
        "`MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE`.",
    ),
}

# Parameters confirmed absent from James' list, where he nonetheless has a
# *neighbouring* entry. Recorded so "only ours" is not read as "he has nothing
# nearby" -- the distinction matters when merging the lists.
ADJACENT = {
    "CTR_CTRDATA_TYPE_IMPLEMENTED":
        "He has `ctrsource` and `ctrtarget` as WARL registers but no "
        "`ctrdata` register entry at all; his only `ctrdata` reference is "
        "the cycle-count field. Gap in his own CSR coverage.",
    "MSECCFG_SEED_BITS_RW":
        "He has `MSECCFG_USEED_SSEED_RST`, which is the *reset value* of "
        "the seed bits. Ours is whether they are writable or a read-only "
        "constant zero -- a different axis. Sail treats these as two "
        "settings too (`Zkr.sseed_reset_value` vs `Zkr.sseed_read_only_zero`).",
    "SENVCFG_FIOM_ACCESS":
        "He has the M-mode sibling `MENVCFG_FIOM_RDONLY0_OK` but not the "
        "S-mode one; his only `senvcfg` entry is CBIE. Textbook per-CSR "
        "replication gap. Note Jordan's mapping shows UDB has no FIOM "
        "writability parameter either, while Sail does "
        "(`base.writable_fiom`), so this is a gap in two of the three lists.",
    "SISELECT_WIDTH":
        "He has the `miselect` sibling but not `siselect`.",
    "VSISELECT_WIDTH":
        "He has the `miselect` sibling but not `vsiselect`.",
}


# Where both lists agree the parameter exists but disagree on its domain.
TYPE_CONFLICTS = {
    "PMA_IDEMPOTENT_IMPLICIT_READ_SIZE":
        "Domain disagreement: ours is a power-of-2 byte size, his is typed "
        "`boolean`.",
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
    j_by_name = {}
    for r in james:
        j_by_name[r["name"]] = r
        for t in r["tags"]:
            j_by_tag.setdefault(t, []).append(r)

    matched, arguable, only_ours = [], [], []
    for r in sorted(ours, key=lambda x: x["name"]):
        tag = r["tags"][0] if r["tags"] else None
        hits = j_by_tag.get(tag, []) if tag else []
        name = r["name"]

        if hits:
            rel = "Exact" if len(hits) == 1 else f"Partial (1-to-{len(hits)})"
            note = TYPE_CONFLICTS.get(name, "")
            matched.append((r, hits, rel, "normative tag", note))
            continue

        if name in MANUAL_MATCHES:
            jnames, rel, why = MANUAL_MATCHES[name]
            hits = [j_by_name.get(n, {"name": n}) for n in jnames]
            matched.append((r, hits, rel, "concept (hand-verified)", why))
            continue

        if name in ARGUABLE_MATCHES:
            jnames, why = ARGUABLE_MATCHES[name]
            arguable.append((r, jnames, why))
            continue

        only_ours.append(r)

    ours_tags = {r["tags"][0] for r in ours if r["tags"]}
    claimed = {h["name"] for _, hits, _, _, _ in matched for h in hits}
    claimed |= {n for _, jn, _ in arguable for n in jn}
    only_james = [r for r in james
                  if not (set(r["tags"]) & ours_tags)
                  and r["name"] not in claimed]

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
        "The primary join is therefore the *normative tag* in the ISA manual:",
        "",
        "* ours -- excerpt -> enclosing `[#norm:...]` anchor -> normative rule",
        "* James' -- `impl-def` -> normative rule -> its tag(s)",
        "",
        "Coverage of that chain: 37 of our 38 sit in a norm anchor and 35 reach a",
        "rule entry; 135 of James' 179 entries resolve to a tag. Name equality is",
        "reported below as corroboration where it happens, never as the join.",
        "",
        "IMPORTANT: The tag join alone is *not* sufficient, and an earlier draft of",
        "this document was wrong because of it. 44 of James' entries carry an",
        "`impl-def` that does not resolve against the pinned manual, and his",
        "`csr_definitions` are hand-authored per register, so wherever he covers a",
        "concept through an unresolved name a tag-only join reports it as ours",
        "alone. Every parameter the tag join left unmatched was therefore checked",
        "by hand against his full file set, by register, field and concept. That",
        "recovered seven further matches, listed with their evidence below.",
        "",
        "Relationship vocabulary follows Jordan's `sail_udb_config_mapping.md`:",
        "*Exact* (one-to-one), *Partial* (concepts overlap but not one-to-one --",
        "one umbrella entry against several fine-grained ones, or a register-level",
        "entry against a specific field rule).",
        "",
        "== Summary",
        "",
        '[cols="60,40",options="header"]',
        "|===",
        "| Measure | Count",
        f"| Our parameters (expert-confirmed, de-duplicated) | {len(ours)}",
        f"| James' entries | {len(james)}",
        f"| On both lists | {len(matched)}",
        f"| ...matched by normative tag | "
        f"{sum(1 for m in matched if m[3] == 'normative tag')}",
        f"| ...matched by concept, hand-verified | "
        f"{sum(1 for m in matched if m[3] != 'normative tag')}",
        f"| Arguable -- overlap is a judgement call | {len(arguable)}",
        f"| Only on our list | {len(only_ours)}",
        f"| Only on James' list | {len(only_james)}",
        "|===",
        "",
    ]

    L += ["== Parameters on both lists", "",
          '[cols="20,22,16,14,28",options="header"]', "|===",
          "| Our name | James' name(s) | Relationship | Matched by | Evidence"]
    for r, hits, rel, how, note in matched:
        jn = ", ".join(f"`{h['name']}`" for h in hits)
        ev = f"`{r['tags'][0]}`" if how == "normative tag" else ""
        if note:
            ev = f"{ev} +\n{note}" if ev else note
        same = [h for h in hits if nz(h["name"]) == nz(r["name"])]
        if same:
            ev += " +\nname also matches"
        L.append(f"| `{esc(r['name'])}` | {jn} | {rel} | {how} | {ev}")
    L += ["|===", ""]

    L += ["== Arguable overlaps", "",
          "Concepts that overlap, where calling it a match is a judgement rather",
          "than a fact. Left unresolved deliberately.",
          "",
          '[cols="24,24,52",options="header"]', "|===",
          "| Our name | James' nearest | Why it is unresolved"]
    for r, jn, why in arguable:
        L.append(f"| `{esc(r['name'])}` | "
                 f"{', '.join('`' + n + '`' for n in jn)} | {esc(why)}")
    L += ["|===", ""]

    L += ["== Only on our list", "",
          "Each of these was verified individually against James' complete file",
          "set: by normative tag, by register name, by field name and by keyword",
          "sweep across all fifteen of his YAML files. None is covered by any",
          "entry of his.",
          "",
          "The *Nearest entry he has* column matters when merging: most of these",
          "are not blank areas of his list but a missing sibling or a missing",
          "axis next to something he does have.",
          "",
          '[cols="20,22,18,40",options="header"]', "|===",
          "| Name | Domain | Tag status | Nearest entry he has"]
    for r in only_ours:
        if not r["tags"]:
            why = "no anchor"
        elif not r["rules"]:
            why = "anchor, no rule entry"
        elif "parameter" not in r["rule_kinds"]:
            why = "rule not marked `kind: parameter`"
        else:
            why = "rule marked `kind: parameter`"
        adj = ADJACENT.get(r["name"], "Nothing adjacent in his files.")
        L.append(f"| `{esc(r['name'])}` | {esc(r['domain'])} | {why} "
                 f"| {esc(adj)}")
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

    # findings that are useful to the manual maintainers.
    # NOTE: scoped over ALL our parameters, not only the unmatched ones. The
    # missing-kind claim is about the manual's metadata and is independent of
    # whether James happens to have the parameter.
    nokind = [r for r in ours if r["rules"]
              and "parameter" not in r["rule_kinds"]]
    norule = [r for r in ours if r["tags"] and not r["rules"]]
    untag = [r for r in ours if not r["tags"]]
    unres = [r for r in james if not r["tags"]]
    matched_names = {m[0]["name"] for m in matched}

    L += ["== Findings for the ISA manual", "",
          "Fallout from the comparison that is directly actionable in the manual",
          "repo. These are independent factual claims about the manual's",
          "metadata; they are deliberately *not* offered as an explanation of why",
          "the two lists differ (see <<why-not-causal>>).",
          "",
          f"=== {len(nokind)} rules that are parameters but are not marked as such",
          "",
          "Each carries a normative tag and has a rule entry in",
          "`normative_rule_defs/`, but the rule is not marked `kind: parameter`.",
          "Each was individually confirmed as a real parameter by Allen Baum and",
          "Umer, so the marking is missing. One-line fix per rule.",
          ""]
    for r in nokind:
        also = " (James has this too)" if r["name"] in matched_names else ""
        L.append(f"* `{r['tags'][0]}` -- our `{r['name']}` "
                 f"({r['file']}:{r['line']}){also}")

    n_have = sum(1 for r in nokind if r["name"] in matched_names)
    L += ["", "[[why-not-causal]]",
          "==== Why this is not the reason the lists differ", "",
          "An earlier draft of this document claimed the missing `kind: parameter`",
          "marking explained why James' list lacks these. The data does not",
          f"support that: he has {n_have} of the {len(nokind)} anyway. His method is",
          "not purely a selection on that marking -- he also hand-authors",
          "`csr_definitions` per register, which routes around it. The metadata",
          "gap is real and worth fixing on its own merits; it is not a causal",
          "account of the difference between the lists.",
          ""]

    L += ["", f"=== {len(norule)} anchors with no normative rule entry", ""]
    for r in norule:
        L.append(f"* `{r['tags'][0]}` -- our `{r['name']}` ({r['file']}:{r['line']})")

    plural = "s" if len(untag) != 1 else ""
    L += ["", f"=== {len(untag)} confirmed parameter{plural} with no tag at all", ""]
    for r in untag:
        L.append(f"* our `{r['name']}` ({r['file']}:{r['line']}) -- "
                 "normative text carrying no anchor")

    L += ["", "=== Two defects noticed in James' files while verifying", "",
          "Both found while confirming the *only on our list* section, and both",
          "worth passing back to him.",
          "",
          "* `hypervisor.yaml:106` declares `reg-name: hgainp`, but its own",
          "  `impl-def` is `HGATP_MODE_WARL`. `hgainp` is not a RISC-V CSR;",
          "  this is a typo for `hgatp`.",
          "* `smctr.yaml` covers `ctrsource` and `ctrtarget` as WARL registers",
          "  but has no entry for `ctrdata`, even though the spec makes every",
          "  field within `ctrdata` optional and read-only 0 when unimplemented.",
          ""]

    L += ["", f"=== {len(unres)} of James' entries reference an unresolved tag", "",
          "These `impl-def` names have no matching normative rule in the pinned",
          f"manual ({MANUAL_SHA[:8]}, 2026-02-15). His definitions are about seven",
          "weeks newer, so some may already exist upstream and others are likely",
          "tags he is proposing. Worth confirming with him rather than assuming.",
          "",
          "This is not only a documentation gap. It is what made a tag-only join",
          "unsafe: seven of the matches above are invisible to the tag join purely",
          "because the counterpart entry resolves through one of these names.",
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
