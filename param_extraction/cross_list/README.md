<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# Cross-list parameter comparison — working brief

Everything needed to pick this up cold. Read this before touching anything in
`param_extraction/cross_list/`.

Background on the wider effort is in `param_extraction/CLAUDE.md`; the
authoritative ruleset is `param_extraction/INCLUSION_CRITERIA.md`. **Read that
ruleset properly before adjudicating anything** — working from a summary of it
caused real mistakes here (see §8).

---

## 1. What this is

Three independent people have catalogued RISC-V architectural parameters:

| List | What it is | Standing |
|---|---|---|
| **UDB** | 229 parameter YAMLs already in the database | The existing baseline |
| **Ours** | 38 candidates believed *missing* from UDB, mined from spec prose | Every entry individually reviewed by Allen Baum and Umer |
| **James Ball's** | 179 entries re-derived from normative-rule tags | Not reviewed by Allen or Umer; he describes it as an initial individual effort, explicitly not SIG consensus |

The task from the mentor was two AsciiDoc deliverables:

1. `out/parameter_lists.adoc` — each list normalised to **Name / Domain / Source**
2. `out/list_comparison.adoc` — the two candidate lists compared

Both exist and are current. A third piece of the original ask, a Sail-style
naming hierarchy, is **not done** — see §9.

A third deliverable was added later:

3. `out/master_list.csv` + `out/master_list.xlsx` (+ `out/master_list.adoc` for
   reading) — the **master list**: one row per distinct parameter concept
   across both lists, with the UDB name where one partially overlaps, both
   sides' names and domains, and an empty `confidence` column for reviewers to
   fill in. The xlsx is the circulating copy: frozen header, filters, the
   confidence column highlighted, and a `how_to_use` sheet.

   **29 columns.** Every field of James' schema is carried verbatim as its own
   `james_*` column — `long-name`, `description`, `type`, `width`, `range`,
   `array`, `note`, `func-of-field-name`, `reg-name`, `field-name`, chapter,
   section, granularity — rather than folded into a derived value.
   `james_domain` is the single normalised column, kept only so there is a
   like-for-like comparison against `ishaan_domain`. A cell containing ` | `
   means the row cites more than one of his entries.

**126 rows** = 30 on both lists + 8 only ours + 88 only his. The 56 entries of
his that UDB already defines outright are excluded; the 30 that only *partially*
overlap a UDB parameter are kept, because a granularity or aspect mismatch is
not coverage. Defects landing on an excluded row are listed separately in the
`.adoc` rather than dropped.

---

## 2. The inputs

Everything is vendored in the repo, so nothing has to be fetched to read or
rerun the comparison. The upstream sources are listed so a newer revision can
be pulled deliberately.

| Input | Path in repo | Upstream |
|---|---|---|
| Our list (raw) | `data/confirmed_parameters_v2.xlsx` | the mentor-reviewed workbook, 44 rows |
| Our list (built) | `data/ours_canonical.json` | generated from the xlsx, 38 params |
| James' list | `data/james_param_defs/*.yaml` | https://github.com/james-ball-qualcomm/riscv-arch-test/tree/prep-for-crd-generators/docs/crd/param_defs |
| UDB baseline | `../data/ground_truth.json` | 223 params, with `csr_references` |
| UDB baseline (2nd) | `data/sail_udb_config_mapping.md` | Jordan's Sail↔UDB map, names 228 UDB params |
| ISA manual | `ext/riscv-isa-manual` submodule | `git submodule update --init ext/riscv-isa-manual` |
| Ruleset | `../INCLUSION_CRITERIA.md` | rules 0–15 |

Other references, not needed to run anything but cited in discussion:

- James' schema and Python tooling —
  https://github.com/riscv/docs-resources/blob/main/tools/README.md
- Sail parameter declarations (the naming pattern under discussion) —
  https://github.com/riscv/sail-riscv/blob/master/model/core/platform_config.sail
- Sail config template the hierarchy is substituted from —
  https://github.com/riscv/sail-riscv/blob/master/config/config.json.in

Pinned revisions are in `data/SOURCES.md`. All three lists move independently,
so a comparison is only meaningful against a stated revision of each — James'
files last changed 2026-04-03, the manual is pinned at 2026-07-29.

---

## 3. Running it

```bash
git submodule update --init ext/riscv-isa-manual
cd param_extraction/cross_list

uv run --python 3.13 --with openpyxl python scripts/build_canonical_list.py
uv run --python 3.13 --with pyyaml  python scripts/generate_asciidoc.py
uv run --python 3.13 --with pyyaml  python scripts/segment_james_vs_udb.py
uv run --python 3.13 --with pyyaml  python scripts/audit_james_vs_criteria.py
uv run --python 3.13 --with pyyaml  python scripts/generate_asciidoc.py   # again
uv run --python 3.13 --with pyyaml --with openpyxl python scripts/generate_master_list.py
```

`generate_asciidoc.py` runs twice because it emits `data/only_james.json`,
which `segment_james_vs_udb.py` consumes, and then renders the segmentation.

`generate_master_list.py` runs last and **imports `generate_asciidoc.py` as a
module** to reuse its loaders and its match tables, so the master list cannot
drift from the comparison document. Change a match there, not here.

Always `uvx ruff@0.15.1 check scripts/` before committing. Keep SPDX
`.license` sidecars on new data files.

**The `.adoc` files are generated. Do not hand-edit them** — the next run
wipes the change. Edit `scripts/generate_asciidoc.py` instead. (This has
already happened once; the edits were recovered and ported.)

Verify a render with:

```bash
ruby -e "require 'asciidoctor'; Asciidoctor::LoggerManager.logger = Asciidoctor::MemoryLogger.new; h=Asciidoctor.load_file('out/list_comparison.adoc', safe: :safe).convert; puts Asciidoctor::LoggerManager.logger.messages.size"
```

---

## 4. The central design decision: join on the normative tag, not the name

Names are useless as a key. Both sides invented their own, so measured against
his 179 entries **exactly one of our 38 names matches his** (`MCYCLE_SHARED`);
a lenient match stripping our `_PARAM`/`_ACCESS` suffixes reaches five. Tag and
concept matching finds **26**. A name join would report the two efforts as
almost entirely disjoint, which is an artefact of naming, not a finding.

The join is the normative tag in the ISA manual:

```
ours   : excerpt -> enclosing [#norm:...] anchor -> normative rule
James' : impl-def -> normative rule -> its tag(s)
```

**The tag join alone is not sufficient**, and trusting it caused a wrong first
draft. 23 of his entries cite an `impl-def` with no matching rule, and his
`csr_definitions` are authored per register, so wherever he covers a concept
through one of those, a tag-only join reports it as ours alone. Every unmatched
parameter must also be checked by hand against his full file set by register,
field and concept. Doing that recovered seven matches.

For **James vs UDB** the key is different again: UDB's `csr_references` carry
the (CSR, field) each parameter controls — 111 params, 978 pairs. That resolved
20 entries no name match would find (`mstatus.MBE` → `M_MODE_ENDIANNESS`,
`vsstatus.UXL` → `VUXLEN`, `hstatus.VSBE` → `VS_MODE_ENDIANNESS`).

---

## 5. Current numbers

Ours vs James':

| | |
|---|---|
| Our parameters | 38 (37 confirmed, 1 flagged) |
| His entries | 179 (93 `parameter_definitions` + 86 `csr_definitions`) |
| On both lists | 26 (19 by tag, 7 by concept) |
| Arguable — a judgement call | 4 |
| Only ours | 8 |
| Only his | 144 |

His 144 segmented against UDB:

| Segment | Count |
|---|---|
| Already in UDB | 56 |
| Overlaps UDB, not one-to-one | 30 |
| **No UDB counterpart** | **52** |
| Outside the ISA parameter space | 5 |
| Same field in both his sections | 1 |

His list against our inclusion criteria: 156 of 179 checkable, **8 flagged**,
so his new candidates go 52 → **45 surviving**, of which 2 cannot be verified
against spec text. That low flag rate is the headline result — his list is
largely consistent with our criteria despite never having been built to them.

---

## 6. Findings worth carrying forward

**UDB has no parameter for any interrupt-pending, interrupt-enable or
delegation register.** Not `mip`, `sip`, `mie`, `sie`, `hie`, `hip`, `hvip`,
`hgeie`, `vsip`, `vsie`, `medeleg`, `mideleg`, `hedeleg`, `hideleg`. Verified
by name and by `csr_references` across the full 229-parameter union; the only
near neighbour is `NUM_EXTERNAL_GUEST_INTERRUPTS`, a count. Our list adds five
here and his adds nine, so the two candidate lists between them fill a category
UDB lacks entirely. **This is the strongest joint result and the best argument
for merging the lists rather than picking one.**

**15 rules are parameters but carry no `impl-def-behavior` marking.** Each has
a normative tag and a rule entry, and each was confirmed as a real parameter by
Allen and Umer. One-line fix per rule in the manual repo. Re-verified 15/15.

Do **not** present that as the reason the lists differ — he has 4 of the 15
anyway, because he also authors `csr_definitions` per register, which routes
around the marking.

**Defects to pass back to James:** `hgainp` is a typo for `hgatp`
(`hypervisor.yaml`); `MIPMPID` should be `MIMPID`; two parameters are spelled
`MISSALIGNED` with a doubled S; `ctrdata` has no entry although every field in
it is optional; and `MTVEC_RDONLY`, `LRSC_ALIGNMENT` and `PMA_MM_IFETCH` cite
tags whose sentence does not describe the parameter (`MTVEC_RDONLY` points at
"The mtvec register must always be implemented", which says nothing about
read-only).

**Asymmetry in UDB:** it defines `MSTATUS_TVM_IMPLEMENTED` but nothing for
`mstatus.TSR` or `mstatus.TW`, which are the same shape of choice.

**His naming has been upstreamed.** 160 of his 190 `impl-def` names are now
rule names in the manual, all carrying `impl-def-behavior: true`.

---

## 7. How the manual represents parameters

`ext/riscv-isa-manual/normative_rule_defs/*.yaml` holds 2,544 normative rules.
Implementation-defined behaviour is marked **`impl-def-behavior: true`**, with
an optional **`impl-def-category`** of `WARL` or `WLRL`; 171 rules carry it.

That marking is the manual's own machine-readable assertion and is a better
inclusion signal than pattern-matching prose — **many such rules tag a
register's bytefield *diagram* rather than a sentence**, so there is no
optionality wording to find. Using it as a signal is what took the criteria
audit from 27 flags to 8.

An older `kind: parameter` marking no longer exists. If you find code or notes
referring to it, they are stale.

---

## 8. Traps — every one of these caused a real error here

**Text-matching traps**

- **A short probe is not unique.** The machine-mode TW rule and the hypervisor
  VTW rule both open "An implementation may have WFI always raise", so a
  seven-word probe collapsed two of our parameters onto one anchor. Probes run
  longest-prefix-first. Always assert no anchor is claimed twice.
- **The anchor span is often shorter than the excerpt.** The `siselect` rule
  tags one clause while our excerpt runs past the closing delimiter, so the
  anchor search needs its own probe ladder.
- **Chapter file names are not stable.** `counters.adoc` split into
  `zihpm`/`zicntr`, `rnmi.adoc` → `smrnmi.adoc`, `scalar-crypto.adoc` →
  `zk.adoc`, `indirect-csr.adoc` → `smcsrind.adoc`. Locate by **excerpt**, never
  by file name.
- **Prose carries cross-reference macros** (`csr:mcycle[]`,
  `csr:mcountinhibit[cy]`, `insn:wfi[]`, `ext:zalrsc[]`). `demarkup` unfolds any
  `name:target[args]` shape rather than a fixed list — handling `csr:` and
  `ext:` but not `insn:` silently broke lookup once.
- **`modules/` duplicates `src/` byte-for-byte.** Read `src/` recursively and
  skip `modules/`, or everything is counted twice.
- **Two anchor syntaxes exist:** `[#norm:X]#text#` and a bare `[[norm:X]]`
  above a paragraph. Parsing only the first undercounts badly.
- **A block delimiter is only equals signs.** `==== Title` is a level-4
  heading, not a delimiter; conflating them leaves a NOTE-block tracker stuck
  open for the rest of the file.

**Adjudication traps**

- **Read `INCLUSION_CRITERIA.md` itself.** Working from a summary produced rule
  citations that were never checked.
- **WARL/WLRL satisfies the inclusion signal on its own** (the mentor's
  standing rule), and so does a declared value/width/ID (rule 5a). Without
  both, `MXLEN` itself gets flagged.
- **Rule 14 must not fire on "read-only copy of another state bit"** —
  §3 of the criteria explicitly blesses that as a valid WARL shape, and our own
  confirmed `VSSTATUS_UBE_PARAM` is exactly it.
- **Watch false negatives after loosening a check.** `LRSC_ALIGNMENT` passed
  only because the word "size" appeared in "aligned to the size of the
  operand". Instrument *why* each entry passed, not just how many.
- **Our `value_type` is a shape, not a domain.** `binary` is not an answer to
  "which values are legal".
- **Verify the UDB baseline you are comparing against.** `ground_truth.json`
  has 223 params; Jordan's file names 228; the union is 229, which matches the
  count James reports. Four UDB names cited from Jordan's file did not exist
  locally and only an assertion caught it.

---

## 9. Open items

1. **The 30 `in_udb_partial` verdicts** are the softest judgements in the
   document and have not been re-audited at the depth of the other segments.
2. **Sail-style naming** is not done. Jordan's mapping shows 144 of 228 UDB
   parameters have no Sail equivalent, so adopting Sail's hierarchy means
   inventing paths for most of the catalogue — a SIG decision, not ours. The
   suggestion on the table is to adopt the *pattern* (dotted path, explicit
   type, `_exp` for log2) and propose paths for our 38 only, as a sample.
3. **Two entries need a mentor ruling, not a verdict:** `WFI_OPT_U_MODE` (he
   has it; the mentor rejected our equivalent as a duplicate) and
   `INTERRUPTS_ALLOWED_IN_PUSHPOP` (our pipeline held it back under rule 1
   because the sentence is in a `NOTE`, and he includes it).
4. **Rule tensions to put to the mentor.** Rule 1 excludes `NOTE` blocks
   outright, yet two flagged entries sit in a NOTE *while carrying a
   `[#norm:]` tag* the manual's own authors added. Rule 6 excludes the WFI
   bounded time limit, which he independently judged a parameter.
5. **23 of his entries cite an unresolved `impl-def`.** Most are probably rules
   he is proposing; worth confirming with him rather than assuming.
6. **Voice is inconsistent** in `list_comparison.adoc`: the summary says
   "Ishaan's parameters" while ~25 other references are first person ("Only on
   our list", "Our name").

---

## 10. Where judgement lives

Every non-mechanical decision is in a reviewable table, not buried in code, so
each can be challenged individually:

| Table | File | What it holds |
|---|---|---|
| `MERGES`, `DROPS`, `FLAGS`, `RESOLVED`, `REWORDED` | `scripts/build_canonical_list.py` | the 44 → 38 corrections |
| `MANUAL_MATCHES`, `ARGUABLE_MATCHES`, `TYPE_CONFLICTS`, `ADJACENT`, `EXPLICIT_DOMAINS` | `scripts/generate_asciidoc.py` | cross-list adjudication and domains |
| all 144 verdicts with reasons | `data/james_vs_udb_adjudication.json` | his entries vs UDB |
| per-entry rule hits with spec text | `data/james_criteria_audit.json` | his entries vs our criteria |
| `CONCEPTS`, `JAMES_CONCEPTS`, `DEFECTS` | `scripts/generate_master_list.py` | the master list's row labels and known defects |

The segmentation verdicts are a **proposed** classification, labelled as such
in the document. They have not been through mentor review.
