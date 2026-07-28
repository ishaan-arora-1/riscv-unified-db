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

FLAGS = {
    "ZALASR_MISALIGNED_ATOMICITY_GRANULE": "Overlaps existing UDB "
    "MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE. The Zalasr sentence points at the "
    "misaligned-atomicity-granule PMA rather than defining it, which reads "
    "like the 'clarification referencing a parameter defined elsewhere' "
    "exclusion. Needs a ruling.",
    "MSTATEEN_BIT63_TYPE": "Mentor asked whether this is genuinely new. "
    "Verified: it IS new. The spec tag exists "
    "([#norm:mstateen-bit-63_roz]) but UDB has only six MSTATEEN_*_TYPE "
    "params (ENVCFG/IMSIC/AIA/CONTEXT/CSRIND/JVT) and none for bit 63.",
}


def squash(s: str) -> str:
    return " ".join((s or "").split())


def demarkup(s: str) -> str:
    return squash(re.sub(r"[`#*_]", "", s or ""))


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


def locate(path: Path, excerpt: str):
    """Re-resolve (line_number, enclosing_norm_anchor) for an excerpt."""
    probe = " ".join(demarkup(excerpt).split()[:7])
    flat, offsets = flatten(path)
    line = None
    idx = flat.find(probe)
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
    anchor = None
    for name, span in load_anchors(path):
        if probe in span:
            anchor = name
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

        path = SRC / r["adoc_file"]
        line, anchor = locate(path, r["excerpt"])

        rec = {
            "parameter_name": name,
            "aliases": [MERGES[name]] if name in MERGES else [],
            "class": r["class"],
            "value_type": r["value_type"],
            "adoc_file": r["adoc_file"],
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
