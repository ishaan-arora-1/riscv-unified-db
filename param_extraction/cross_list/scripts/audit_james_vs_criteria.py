# SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""Audit James' entries against param_extraction/INCLUSION_CRITERIA.md.

Our list was filtered through that ruleset; his was never held to it. This
applies the mechanically checkable rules to his entries so the two lists can
be compared on the same footing.

His entries carry no excerpt, only an ``impl-def`` pointing at a normative
rule, so the spec text has to be recovered first:

    impl-def -> normative rule -> tag -> anchor text in the .adoc

Rules that can be checked mechanically once the text is in hand:

  inclusion signal (S1)  does the text carry any optionality language at all
  rule 1                 inside a NOTE/TIP/WARNING/IMPORTANT block
  rule 2                 fixed requirement (must/shall/required) and no choice
  rule 3                 reserved / hardwired / WPRI statement of fact
  rule 6                 "misconfigured", or a quantity with no testable units
  rule 8                 introduction / overview section

Rules 4, 10, 11, 12, 13, 14 and 15 need judgement or UDB context and are not
decided here; rule 11 (duplicates) is already covered by the UDB segmentation.

Output is an evidence file, not a verdict on his work: a rule hit means the
entry would need review under OUR criteria, which is a definition difference
until the mentor rules on it.
"""

import json
import re
import sys
from glob import glob
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
BASE = REPO / "param_extraction/cross_list"
SRC = REPO / "ext/riscv-isa-manual/src"
NRD = REPO / "ext/riscv-isa-manual/normative_rule_defs"
JDIR = BASE / "data/james_param_defs"
OUT = BASE / "data/james_criteria_audit.json"

CHOICE = re.compile(
    # the words INCLUSION_CRITERIA section 1 lists literally
    r"\bmay\b|\boptional(?:ly)?\b|implementation[- ]defined|implementation[- ]"
    r"specific|implementation[- ]dependent|can choose|can be configured|"
    r"is not required to|are not required to|need not|chooses|selects|"
    r"defines a|sets a"
    # plus equivalents the ruleset does not spell out but plainly means
    r"|an implementation can|implementations can|is permitted to|"
    r"are permitted to|is allowed to|are allowed to|\bmight\b|"
    r"unless the platform|either .{0,60}\bor\b",
    re.I)
# The mentor's standing rule: "IF it is WARL, it is automatically a parameter."
# A WARL/WLRL field therefore satisfies the inclusion signal on its own.
WARL = re.compile(r"\bWARL\b|\bWLRL\b", re.I)
# INCLUSION_CRITERIA rule 5a plus the v5 prompt exception: a declared,
# implementation-chosen value / width / size / ID counts even with no modal
# word, because the choice is inherent in the quantity being declared.
# The quantity must be what the sentence is ABOUT. A bare mention of "size"
# or "number of" is not enough -- "aligned to the size of the operand" is a
# requirement, not a declared value, and matching it here silently passed
# LRSC_ALIGNMENT on a sentence that does not describe its parameter at all.
DECLARED = re.compile(
    r"^\s*The (maximum |minimum )?(size|number|width|value|address)\b"
    r"|\bis an? [A-Za-z0-9]+-bit\b|\bnumber of bits\b|\bwidth of\b"
    r"|\beffective XLEN\b|\bvalue of\b|\bencodes?\b|\bencoding\b"
    r"|\bconstant termed\b|\bgranularity\b|\bproviding the\b|\bunique\b"
    r"|\bID\b|\bidentifier\b|reset value",
    re.I)
# rule 14 -- legal values defined as identical to ANOTHER register's, so the
# choice is not independent. Deliberately narrow: a read-only field mirroring
# another state bit is NOT derived, it is an explicitly blessed WARL shape
# (INCLUSION_CRITERIA section 3, "Read-only mirroring another state bit").
DERIVED = re.compile(
    r"same set of values that .{0,40} can hold", re.I)
# rule 1 also covers an inline "NOTE:" prefix, not just a [NOTE] block
INLINE_NOTE = re.compile(r"^\s*(NOTE|TIP|WARNING|IMPORTANT|CAUTION)\s*:", re.I)
FIXED = re.compile(r"\bmust\b|\bshall\b|\brequired\b|\bmandatory\b|\balways\b", re.I)
RESERVED = re.compile(r"\breserved\b|\bhardwired\b|\bWPRI\b", re.I)
NOUNITS = re.compile(r"misconfigured|bounded time|time limit|some time|"
                     r"reasonable|unspecified amount", re.I)
BLOCK = re.compile(r"^\[(NOTE|TIP|WARNING|IMPORTANT|CAUTION)\]", re.I)
INTRO = re.compile(r"introduction|overview|preface|rationale", re.I)


def nz(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def build_tag_index():
    """tag -> {file, line, text, in_block, section}"""
    idx = {}
    for p in sorted(SRC.glob("*.adoc")):
        lines = p.read_text().split("\n")
        # track NOTE-block spans (delimited by ==== after a [NOTE])
        in_block, block_depth = [False] * len(lines), False
        pending = False
        for i, ln in enumerate(lines):
            s = ln.strip()
            # a delimiter line is ONLY equals signs. "==== Title" is a level-4
            # section heading, not a block delimiter -- conflating the two
            # leaves the tracker stuck open for the rest of the file.
            delim = bool(re.fullmatch(r"={4,}", s))
            if BLOCK.match(s):
                pending = True
            elif pending and delim:
                block_depth, pending = True, False
            elif block_depth and delim:
                block_depth = False
            in_block[i] = block_depth
        # nearest preceding section heading
        section = [""] * len(lines)
        cur = ""
        for i, ln in enumerate(lines):
            if re.match(r"^=+\s+\S", ln):
                cur = ln
            section[i] = cur
        text = p.read_text()
        for m in re.finditer(r"\[#(norm:[^\]]+)\]#(.*?)#", text, re.S):
            line = text[: m.start()].count("\n")
            idx[m.group(1)] = {
                "file": p.name, "line": line + 1, "text": " ".join(m.group(2).split()),
                "in_block": in_block[min(line, len(lines) - 1)],
                "section": section[min(line, len(lines) - 1)],
            }
        for i, ln in enumerate(lines):
            m = re.match(r"^\[\[(norm:[^\]]+)\]\]\s*$", ln.strip())
            if not m:
                continue
            para = []
            for nxt in lines[i + 1:]:
                if not nxt.strip():
                    break
                para.append(nxt)
            idx[m.group(1)] = {
                "file": p.name, "line": i + 1, "text": " ".join(" ".join(para).split()),
                "in_block": in_block[i], "section": section[i],
            }
    return idx


def load_rules():
    rules = {}
    for p in sorted(NRD.glob("*.yaml")):
        doc = yaml.safe_load(p.read_text()) or {}
        for e in doc.get("normative_rule_definitions") or []:
            if not e.get("name"):
                continue
            raw = e.get("tags") or ([e["tag"]] if e.get("tag") else [])
            rules[nz(e["name"])] = [
                t["name"] if isinstance(t, dict) else t for t in raw]
    return rules


def load_james():
    out = []
    for p in sorted(glob(str(JDIR / "*.yaml"))):
        doc = yaml.safe_load(Path(p).read_text()) or {}
        for e in doc.get("parameter_definitions") or []:
            out.append({"name": e.get("name"), "section": "param",
                        "impl": e.get("impl-def") or e.get("impl-defs"),
                        "file": Path(p).name})
        for e in doc.get("csr_definitions") or []:
            reg = e.get("reg-name") or e.get("reg-names")
            reg = reg if isinstance(reg, str) else "/".join(reg)
            fld = e.get("field-name")
            out.append({"name": f"{reg}.{fld}" if fld else reg, "section": "csr",
                        "impl": e.get("impl-def") or e.get("impl-defs"),
                        "file": Path(p).name})
    return out


def main() -> int:
    idx, rules, james = build_tag_index(), load_rules(), load_james()
    print(f"norm anchors indexed in the spec : {len(idx)}")

    rows = []
    for j in james:
        impl = j["impl"]
        impl = impl if isinstance(impl, list) else ([impl] if impl else [])
        tags, texts = [], []
        for i in impl:
            for t in rules.get(nz(i), []):
                tags.append(t)
                if t in idx:
                    texts.append(idx[t])
        if not texts:
            rows.append({**j, "resolved": False, "tags": tags, "hits": [],
                         "note": "no spec text reachable -- cannot apply "
                                 "text-based rules"})
            continue
        blob = " ".join(t["text"] for t in texts)
        # a WARL/WLRL field, or a declared value/width/ID, satisfies the
        # inclusion signal without a modal word
        signal = bool(CHOICE.search(blob) or WARL.search(blob)
                      or DECLARED.search(blob))
        hits = []
        if not signal:
            hits.append(("S1", "no optionality language, no WARL/WLRL and no "
                               "declared value or width in the tagged text"))
        if any(t["in_block"] for t in texts) or INLINE_NOTE.match(blob):
            hits.append(("1", "tagged text sits in a NOTE/TIP/WARNING block"))
        if FIXED.search(blob) and not signal:
            hits.append(("2", "fixed requirement with no optionality"))
        if RESERVED.search(blob) and not signal:
            hits.append(("3", "reserved/hardwired/WPRI statement of fact"))
        if NOUNITS.search(blob):
            hits.append(("6", "no testable units / 'misconfigured'"))
        if any(INTRO.search(t["section"]) for t in texts):
            hits.append(("8", "introduction or overview section"))
        if DERIVED.search(blob):
            hits.append(("14", "legal values stated as identical to another "
                               "register's -- possibly derived, not independent"))
        rows.append({**j, "resolved": True, "tags": tags,
                     "hits": [{"rule": r, "why": w} for r, w in hits],
                     "evidence": [{"file": t["file"], "line": t["line"],
                                   "text": t["text"][:240]} for t in texts[:2]]})

    res = [r for r in rows if r["resolved"]]
    flagged = [r for r in res if r["hits"]]
    OUT.write_text(json.dumps({"rows": rows}, indent=1) + "\n")
    print(f"his entries                     : {len(rows)}")
    print(f"  spec text recoverable         : {len(res)}")
    print(f"  NOT recoverable (no check)    : {len(rows) - len(res)}")
    print(f"  flagged by >=1 rule           : {len(flagged)}")
    print()
    from collections import Counter
    c = Counter(h["rule"] for r in flagged for h in r["hits"])
    for rule, n in sorted(c.items()):
        print(f"    rule {rule:3} {n}")
    print(f"\nwrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
