# SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""Build the canonical de-duplicated list of our expert-confirmed parameters.

Input : confirmed_parameters_v2.xlsx (44 rows, as reviewed by Allen Baum + Umer)
Output: cross_list/data/ours_canonical.json

Three corrections are applied, each recorded in the output so the change is
auditable rather than silent:

1. MERGE -- five V3/V4 row pairs carry byte-identical excerpts. Each of those
   sentences occurs exactly once in the spec, so they are the same parameter
   catalogued twice under two invented names, not the m/s/vs replication
   pattern. Merged; the discarded name is kept as an alias.
2. DROP  -- a parameter that is already a defined UDB parameter. Per the
   project rule, a WARL finding is dropped only when that specific field is
   already in UDB; this is that case.
3. FLAG  -- entries that need a ruling before publication; kept, but marked.

Line numbers in the sheet drift by up to ~75 lines (two pipeline vintages were
merged), so every row's location is re-resolved by searching the spec for the
excerpt. The enclosing [#norm:...] anchor is captured at the same time, since
that anchor is the join key for the cross-list comparison.
"""

import json
import re
import sys
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "ext/riscv-isa-manual/src"
# The mentor-reviewed workbook is vendored so the pipeline runs from a clean
# clone. The Downloads copy is only a fallback for whoever has the original.
XLSX = REPO / "param_extraction/cross_list/data/confirmed_parameters_v2.xlsx"
if not XLSX.exists():  # pragma: no cover
    XLSX = Path("/Users/ashish/Downloads/confirmed_parameters_v2.xlsx")
OUT = REPO / "param_extraction/cross_list/data/ours_canonical.json"

# --- decision table -------------------------------------------------------
# Same spec sentence, two names. keep -> alias.
MERGES = {
    "SCTRDEPTH_SUPPORTED_VALUES": "CTR_SUPPORTED_DEPTHS",
    "HINT_SXLEN_DEST_REG_BEHAVIOR": "HINT_SXLEN_BEHAVIOR",
    "MSECCFG_SEED_BITS_RW": "SSEED_USEED_WRITABLE",
    # keep the name that also appears on James' list -- free corroboration
    "VTW_VIRTINSTR_PARAM": "VTW_WFI_ALWAYS_TRAP",
}

DROPS = {
    "CTR_RASEMU_SUPPORTED": "Already in UDB as MCTRCTL_RASEMU_IMPLEMENTED "
    "('Whether or not mctrctl.RASEMU is implemented. When not implemented "
    "mctrctl.RASEMU will be read-only-zero'), whose csr_references cover "
    "sctrctl and vsctrctl. True field-level duplicate.",
    "CTR_RASEMU_IMPLEMENTED": "Duplicate of CTR_RASEMU_SUPPORTED (identical "
    "excerpt, one spec sentence) AND already in UDB as "
    "MCTRCTL_RASEMU_IMPLEMENTED.",
}

# Genuinely open -- the entry is kept but its status is unresolved.
FLAGS = {
    "ZALASR_MISALIGNED_ATOMICITY_GRANULE": "Overlaps existing UDB "
    "MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE. The Zalasr sentence points at the "
    "misaligned-atomicity-granule PMA rather than defining it, which reads "
    "like the 'clarification referencing a parameter defined elsewhere' "
    "exclusion. Needs a ruling.",
}

# A question that was asked and has since been ANSWERED. These stay confirmed;
# marking them "needs a ruling" would overstate the uncertainty.
RESOLVED = {
    "MSTATEEN_BIT63_TYPE": "The mentor asked whether this is genuinely new "
    "('seems to have a tag -- not in UDB?'). Answered: it is new. The spec "
    "tag does exist ([#norm:mstateen-bit-63_roz], smstateen.adoc:175), but "
    "UDB defines only six MSTATEEN_*_TYPE parameters "
    "(ENVCFG/IMSIC/AIA/CONTEXT/CSRIND/JVT) and none for bit 63. Tagged in "
    "the spec does not mean present in UDB.",
}


def adoc_files(src: Path):
    """Every chapter .adoc under src/, for both manual layouts.

    Before 2026-03 the chapters were flat in src/*.adoc. They then moved to
    src/priv/, src/unpriv/ and src/profiles/. The Antora tree under modules/
    is a byte-identical duplicate of src/ and is excluded so nothing is
    counted or matched twice.
    """
    return sorted(p for p in src.rglob("*.adoc") if "modules" not in p.parts)


def find_adoc(src: Path, basename: str):
    """Locate a chapter by bare file name in either layout."""
    for p in adoc_files(src):
        if p.name == basename:
            return p
    return None


def probes(excerpt: str, name: str = ""):
    """Search phrases for an excerpt, longest first.

    A short prefix is not always unique. The machine-mode TW rule and the
    hypervisor VTW rule both begin "An implementation may have WFI always
    raise", so a seven-word probe collapses them onto one anchor. Trying the
    longest prefix first and only shortening on failure keeps distinct
    sentences distinct while still tolerating light rewording.
    """
    if name in REWORDED:
        return [demarkup(REWORDED[name])]
    words = demarkup(excerpt).split()
    lens = [n for n in (len(words), 25, 18, 12, 7) if n <= len(words)]
    seen, out = set(), []
    for n in lens:
        p = " ".join(words[:n])
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def find_by_excerpt(src: Path, excerpt: str, hint: str = "", name: str = ""):
    """Locate the chapter that actually contains this excerpt.

    File names are not stable across manual revisions -- the 2026-07 rework
    split counters.adoc into zihpm/zicntr, renamed rnmi.adoc to smrnmi.adoc,
    scalar-crypto.adoc to zk.adoc and indirect-csr.adoc to smcsrind.adoc, and
    moved everything under src/priv and src/unpriv. The excerpt is the stable
    identity, so search on that and fall back to the recorded name only to
    break ties.
    """
    for probe in probes(excerpt, name):
        hits = [p for p in adoc_files(src) if probe in flatten(p)[0]]
        if not hits:
            continue
        for p in hits:                  # prefer the recorded file if still valid
            if p.name == hint:
                return p
        return hits[0]
    return None


def squash(s: str) -> str:
    return " ".join((s or "").split())


# Excerpts the 2026-07 manual reworded, so the recorded text no longer occurs
# verbatim. Each maps to a distinctive phrase that IS present in the new text,
# checked by hand. Kept explicit rather than fuzzy-matched so a wrong match
# cannot creep in silently.
REWORDED = {
    # "the A extension" became "the Zalrsc extension" -- LR/SC was split out
    # of A. Substantive spec change; the parameter itself is unchanged.
    "XRET_CLEARS_LR_RESERVATION":
        "clear any outstanding LR address reservation but is not required to",
    # "[s,u]seed" became "csr::[sseed] and csr::[useed]"
    "MSECCFG_SEED_BITS_RW":
        "is a read-only constant value",
}

# Any AsciiDoc cross-reference macro: csr:, ext:, insn:, and whatever else the
# manual adds later. Matching the shape rather than a fixed list means a new
# macro cannot silently break excerpt lookup the way insn: did.
XREF_MACRO = re.compile(r"\b[a-z][a-z0-9]*:([A-Za-z0-9_]*)\[([^\]\n]*)\]")


def demarkup(s: str) -> str:
    """Normalise AsciiDoc markup so text matches across manual revisions.

    The 2026-07 manual introduced cross-reference macros, so the same
    sentence is now written differently:
        `mcycle`           -> csr:mcycle[]
        `mcountinhibit.CY` -> csr:mcountinhibit[cy]
        `WFI`              -> insn:wfi[]
        `[s,u]seed`        -> csr::[sseed] and csr::[useed]
    Unfolding these to bare names, and comparing case-insensitively, lets an
    excerpt captured against the old manual still be found in the new one.
    """
    s = s or ""
    s = XREF_MACRO.sub(
        lambda m: m.group(1) + ("." + m.group(2) if m.group(2) else ""), s)
    s = re.sub(r"[`#*_]", "", s)
    return squash(s).lower()


def load_anchors(path: Path):
    """Return [(anchor_name, demarkup'd span text)] for the file.

    The spec uses two anchor syntaxes and both must be handled:
      [#norm:NAME]#text#   inline anchor, span is the delimited text
      [[norm:NAME]]        block anchor on its own line, span is the
                           paragraph that follows (up to the next blank line)
    """
    text = path.read_text()
    out = [
        (m.group(1), demarkup(m.group(2)))
        for m in re.finditer(r"\[#(norm:[^\]]+)\]#(.*?)#", text, re.S)
    ]
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        m = re.match(r"^\[\[(norm:[^\]]+)\]\]\s*$", ln.strip())
        if not m:
            continue
        para = []
        for nxt in lines[i + 1 :]:
            if not nxt.strip():
                break
            para.append(nxt)
        out.append((m.group(1), demarkup(" ".join(para))))
    return out


def flatten(path: Path):
    """Return (flat_text, offsets) where offsets[k] starts line k+1."""
    lines = path.read_text().split("\n")
    flat, offsets = [], []
    pos = 0
    for ln in lines:
        d = demarkup(ln)
        offsets.append(pos)
        flat.append(d)
        pos += len(d) + 1
    return " ".join(flat), offsets


def locate(path: Path, excerpt: str, name: str = ""):
    """Re-resolve (line_number, enclosing_norm_anchor) for an excerpt."""
    flat, offsets = flatten(path)
    probe, idx = None, -1
    for cand in probes(excerpt, name):
        if cand in flat:
            probe, idx = cand, flat.find(cand)
            break
    if probe is None:
        return None, None
    line = None
    if idx >= 0:
        # map the match offset back to the line that contains it
        lo, hi = 0, len(offsets) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if offsets[mid] <= idx:
                lo = mid
            else:
                hi = mid - 1
        line = lo + 1
    # The anchor span is often SHORTER than the recorded excerpt -- the
    # siselect rule tags only "The siselect register will support the value
    # range 0..0xFFF at a minimum." while our excerpt runs on past the closing
    # delimiter. So walk the probe ladder again here rather than reusing the
    # long probe that matched the file body.
    anchor = None
    spans = load_anchors(path)
    for cand in probes(excerpt, name):
        for anchor_name, span in spans:
            if cand in span:
                anchor = anchor_name
                break
        if anchor:
            break
    return line, anchor


def main() -> int:
    if not XLSX.exists():
        print(f"missing input: {XLSX}", file=sys.stderr)
        return 1

    ws = openpyxl.load_workbook(XLSX)["confirmed_parameters"]
    raw = list(ws.iter_rows(values_only=True))
    hdr = raw[0]
    rows = [dict(zip(hdr, r, strict=True)) for r in raw[1:]]

    alias_of = {v: k for k, v in MERGES.items()}
    by_name = {r["parameter_name"]: r for r in rows}

    out, dropped, merged = [], [], []
    for r in rows:
        name = r["parameter_name"]

        if name in DROPS:
            dropped.append({"parameter_name": name, "reason": DROPS[name]})
            continue

        if name in alias_of:  # discarded half of a merge pair
            merged.append({"discarded": name, "merged_into": alias_of[name]})
            continue

        path = find_by_excerpt(SRC, r["excerpt"], r["adoc_file"], name)
        if path is None:
            print(f"  !! excerpt not found anywhere: {name}", file=sys.stderr)
            continue
        line, anchor = locate(path, r["excerpt"], name)

        rec = {
            "parameter_name": name,
            "aliases": [MERGES[name]] if name in MERGES else [],
            "class": r["class"],
            "value_type": r["value_type"],
            "adoc_file": r["adoc_file"],
            "adoc_path_now": str(path.relative_to(SRC)),
            "reworded_in_new_manual": name in REWORDED,
            "line_number_sheet": int(r["line_number"]),
            "line_number_resolved": line,
            "norm_anchor": anchor,
            "excerpt": squash(r["excerpt"]),
            "mentor_verdict": squash(r["mentor_verdict"]),
            "review_batch": r["review_batch"],
            "status": "flagged" if name in FLAGS else "confirmed",
        }
        if name in MERGES:
            twin = by_name[MERGES[name]]
            rec["merged_verdict"] = squash(twin["mentor_verdict"])
        if name in FLAGS:
            rec["flag"] = FLAGS[name]
        if name in RESOLVED:
            rec["resolved_note"] = RESOLVED[name]
        out.append(rec)

    out.sort(key=lambda r: r["parameter_name"])
    doc = {
        "source": XLSX.name,
        "input_rows": len(rows),
        "canonical_count": len(out),
        "confirmed": sum(1 for r in out if r["status"] == "confirmed"),
        "flagged": sum(1 for r in out if r["status"] == "flagged"),
        "merged_pairs": merged,
        "dropped": dropped,
        "parameters": out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1) + "\n")

    unloc = [r["parameter_name"] for r in out if r["line_number_resolved"] is None]
    noanchor = [r["parameter_name"] for r in out if r["norm_anchor"] is None]
    drift = [
        (r["parameter_name"], r["line_number_sheet"], r["line_number_resolved"])
        for r in out
        if r["line_number_resolved"]
        and abs(r["line_number_sheet"] - r["line_number_resolved"]) > 5
    ]

    print(f"input rows          : {len(rows)}")
    print(f"merged away         : {len(merged)}")
    print(f"dropped (in UDB)    : {len(dropped)}")
    print(f"canonical           : {len(out)}  "
          f"({doc['confirmed']} confirmed, {doc['flagged']} flagged)")
    print(f"excerpt not located : {len(unloc)} {unloc}")
    print(f"no enclosing anchor : {len(noanchor)} {noanchor}")
    print(f"line drift >5       : {len(drift)}")
    for n, a, b in drift:
        print(f"    {n:38} sheet={a:5} actual={b}")
    print(f"\nwrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
