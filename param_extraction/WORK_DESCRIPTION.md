<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# Our RISC-V architectural-parameter work — a description for comparison

**Read this to understand what our parameter list is, how it was produced, and
what each entry means.** You are **not** taking over this project and you will
not run our pipeline. Your job is to understand our work well enough to compare
our parameter list against another person's list and produce new combined /
differential lists.

The single most important thing to absorb: **§5 (status tiers)** and **§6 (how to
compare without generating false matches and false differences)**. Naive
name-matching between the two lists will produce badly wrong results.

---

## 1. What we were doing

The RISC-V ISA specification (`riscv-isa-manual`, ~53k lines across 74 AsciiDoc
files) describes **architectural parameters**: implementation choices the spec
deliberately leaves to the chip designer. Examples: how wide a field is, which
values a WARL CSR field legally accepts, whether a CSR bit is read-write or
hardwired read-only-zero, whether an optional behaviour is supported.

The RISC-V Unified Database (UDB) already catalogs **223** such parameters. Our
project mined the spec text to find **parameters that UDB does not yet have**,
classify them, validate them, and prepare them for inclusion in UDB.

**Therefore: our lists contain CANDIDATE NEW parameters — things we believe are
missing from UDB.** They are, by construction, *not* the 223 that UDB already
has. If the other list you are comparing against includes already-in-UDB
parameters, that is a scope difference, not a disagreement (see §6.4).

A human **mentor** (a RISC-V domain expert) reviews our candidates and is the
**final authority**. Our automation only generates candidates; his verdict
decides what is real.

---

## 2. What we mean by "architectural parameter"

This definition governs every entry in our lists. If the other list uses a
different definition, most apparent disagreements will trace back to here.

> A parameter is **an implementation choice whose outcome can be observed and
> verified** — the implementer selects from a defined set, a bounded range, or
> commits to a single fixed declared value — left to the implementer by the
> spec, supported by an extension, and not already captured elsewhere in UDB.

**Master test:** *if an implementation's choice cannot be observed and tested, it
is not a certifiable parameter.*

Consequences of that test:
- It **admits** value/ID/width parameters whose value space is unconstrained but
  whose chosen value is declared and readable (e.g. an architecture-ID register's
  value, a field width).
- It **excludes** unspecified *behaviours*, which cannot be tested.

The full authoritative ruleset lives in
`param_extraction/INCLUSION_CRITERIA.md` — read it if you need to adjudicate a
borderline case.

### Inclusion signal
The spec text normally must carry genuine optionality language: *may* (as
optionality), *optional/optionally*, *implementation-defined*,
*implementation-specific/-dependent*, *can choose / can be configured*,
*is/are not required to*, *need not*, or "the implementation
**chooses/defines/selects/sets** a value/width/number".

A choice-word is **necessary but not sufficient** — the text must also survive
every exclusion. One deliberate exception: a **declared implementation-chosen
value, width, size, or ID** counts even without a modal word, because the choice
is inherent in the register being implementation-defined.

### ⚠️ WARL is a parameter, not a duplicate
A **WARL** (Write Any, Read Legal) field behaviour — or a read-only-vs-read-write
field behaviour — **IS a parameter** in our taxonomy. This is the single biggest
category in our findings. We classify the WARL behaviour (which legal values; RW
vs read-only-zero; conditional on privilege mode; read-only-mirroring-another-bit)
rather than discarding it. We drop a WARL finding only when that *specific field*
is already a defined UDB parameter.

We also treat **implicit WARL** as in scope: a bit documented as an ordinary RW
CSR bit may in practice be always/optionally read-only-0, read-only-1, or a copy
of another state bit. Those count **even when the word "WARL" never appears.**

If the other list treats WARL behaviour as "not a parameter" or as a duplicate,
that alone will explain a large block of differences.

---

## 3. What we deliberately EXCLUDE

If the other list contains these, it is a **definition difference, not a gap in
their work or ours.** Flag them as such rather than as missing parameters.

| We exclude | Rationale |
|---|---|
| Text inside `[NOTE]` / `[TIP]` / `[WARNING]` / `[IMPORTANT]` blocks | Non-normative |
| Fixed requirements (*must*, *shall*, *required*, *always*) with no optionality | No choice exists |
| Reserved / hardwired statements of fact (*reserved*, *hardwired*, *WPRI*) | Fixed, not chosen |
| **Unspecified behaviour/result** ("the result is unspecified", "may or may not [happen/fail/update]" describing a runtime *outcome*) | Intentionally unconstrained; untestable |
| Implementation-defined things with **no testable units or enumerable options** (e.g. "a bounded time limit" with no units) | Cannot certify |
| Introduction / overview sections | Non-normative |
| Untagged software/firmware requirements and clarifications | A requirement *on software*, not an implementer choice |
| Clarifications that reference a parameter defined elsewhere | Points at an existing param |
| **Duplicates** — same concept as an existing UDB param, or the same normative text repeated in another chapter | Not new |
| Text describing how an **existing mechanism** already works | Not a new knob |
| **Extension or whole-register presence** — whether a complete extension/register exists | That is extension membership. *But* whether an **optional field within a register** is implemented (read-only-zero if not) IS a parameter |
| **Derived** values — fully determined by another choice | Not independent |

Two important carve-outs that often cause cross-list disagreement:
- An unspecified **value/width/number** the implementation picks **IS** a
  parameter (unlike unspecified *behaviour*).
- "May or may not **support/implement** a feature" **IS** a binary support
  parameter (testable), and is *not* treated as unspecified behaviour.

---

## 4. How the list was produced (provenance & reliability)

An LLM pipeline reads the spec in chunks and proposes candidates, filtered
through four layers, **none of which is trusted alone**:

1. **Extraction prompt** — the exclusions above are baked in, so candidates are
   comparatively clean by construction.
2. **Mechanical script filters** — rule checks plus reviewer flag columns.
3. **LLM adjudication** — duplicate detection against all 223 existing UDB
   parameters, "describes an existing mechanism", certifiability.
4. **Human mentor review** — the final authority.

Practical implications for you:
- Entries are **grounded in a verbatim spec excerpt** with a file name and line
  number. Every claim is traceable to spec text — use the **excerpt**, not the
  name, as the source of truth when comparing.
- Line numbers are from our pinned copy of the spec submodule and can drift by a
  few lines against a different checkout. **Match on excerpt text, not line
  number.**
- The pipeline is **not exhaustive** (see §7).

---

## 5. The deliverables and their status tiers — READ THIS

Our entries are **not all equally certain.** Treat these as distinct tiers.

### File A — `params_for_review (1) (1) (1).xlsx` (the working review sheet)
One sheet, `params_for_review`, **51 data rows**, 16 columns.

| Section | Rows | Status |
|---|---|---|
| `V5 - for review (improved-recall pipeline)` | 8 | **Candidate — NOT yet mentor-reviewed** |
| `0. NEW - likely duplicate/replication` | 5 | **Candidate — flagged by us as probably duplicates; not mentor-reviewed** |
| `1. V4 - for review` | 14 | Mentor reviewed (9 confirmed, 3 hedged, 2 rejected) |
| `2. Mentor-confirmed (V3)` | 24 | Mentor reviewed — all confirmed |

> 🚩 **Two voices live in this sheet, in two separate columns:**
> - **`mentor_comment`** — the mentor's own verdict. Terse and opinionated:
>   *"parameter !"*, *"duplicate"*, *"WARL behavior"*, *"possibly a parameter;
>   depends…"*. **Only the V3 and V4 sections have these.**
> - **`our assessment`** — **our** analysis, prefixed "OUR ASSESSMENT:". This is
>   the project team's opinion, **not** expert confirmation.
>
> **All 8 V5 rows and all 5 "0. NEW" rows currently have an EMPTY
> `mentor_comment`.** They carry only our assessment. Do **not** treat them as
> confirmed parameters.

### File B — `parameter list.xlsx` / `confirmed_parameters.xlsx` (the clean output)
Sheet `confirmed_parameters`, **32 parameters** — the mentor-confirmed set
(24 from V3 + 9 from V4, minus one that appears in both). Columns:
`parameter_name, class, value_type, adoc_file, line_number, excerpt,
mentor_verdict, review_batch`.

**This is the authoritative "these are real" list.** It deliberately excludes:
- **3 hedged** entries where the mentor said "possibly"/"arguably" rather than
  confirming: `CTR_MISP_IMPLEMENTED`, `CTR_CYCLE_COUNT_IMPLEMENTED`,
  `CTR_RASEMU_IMPLEMENTED`.
- **2 rejected as duplicates:** `WFI_U_MODE`, and the V4 copy of
  `SENVCFG_FIOM_ACCESS`.
- **All V5 and "0. NEW" rows** — not yet reviewed.

### Status summary
| Tier | Count | How to treat it |
|---|---|---|
| **Mentor-confirmed** | **32** | High confidence. Real parameters. |
| Hedged by mentor | 3 | Plausible, unresolved |
| Awaiting mentor review (V5 + flagged-duplicate) | 13 | Our candidates only |
| Rejected as duplicate | 2 | Not new |

---

## 6. How to compare our list against another list — the traps

These are the specific ways a naive comparison will go wrong.

### 6.1 Our parameter NAMES are our own inventions — match by concept
Our `parameter_name` values (e.g. `SSTATUS_UBE_ACCESS`, `MIP_WRITABLE_BITS`) are
**suggested UPPER_SNAKE_CASE names our pipeline generated**, not canonical RISC-V
or UDB identifiers. Another person analysing the exact same spec sentence will
almost certainly have chosen a different name.

**Match on the underlying concept**, identified by:
`(CSR or mechanism) + (field/bit) + (the kind of choice)` — e.g.
"`sstatus`.UBE, read-only vs writable" — and corroborate with the **excerpt** and
`adoc_file`. Only use names as a weak hint.

### 6.2 Granularity mismatch — expect 1-to-N mappings
The same spec statement can legitimately be catalogued as **one umbrella
parameter** or as **many fine-grained ones**. Real example from our work: the
`stateen` CSRs carry one general rule ("each bit is WARL and may be read-only
zero or one") plus separately named feature bits (ENVCFG, IMSIC, AIA, CONTEXT,
CSRIND, JVT). UDB models **one parameter per named bit**; a single extraction
pass naturally emits **one** umbrella finding.

The same applies to MODE fields: UDB splits one WARL MODE field (e.g. `satp` /
`hgatp` / `stvec`) into **one boolean per legal mode value**, where the spec
states them as a single list.

**So: an entry on one side may correspond to several on the other.** Record these
as *granularity differences*, not as matches or misses. Do not silently collapse
or explode them.

### 6.3 Per-CSR replication — the m/s/vs/h family problem
RISC-V repeats the same mechanism across privilege levels: `mstateen`/`hstateen`/
`sstateen`, `mepc`/`sepc`/`vsepc`, `miselect`/`siselect`/`vsiselect`,
`htval`/`mtval2`. The spec often uses **near-identical wording** for each.

We flag these in a `cross_chapter_dup` column and sometimes count them as **one
concept**, while another list may enumerate **all variants separately**. Check
explicitly whether an apparent "missing" parameter on our side is just the
sibling CSR of one we listed.

### 6.4 Our list is "NEW parameters only" — the 223 UDB baseline is separate
Our candidates exclude anything already in UDB **by design**. If the other list
mixes existing UDB parameters with new discoveries, you must segment their list
into "already in UDB" vs "genuinely new" before comparing, or our list will look
falsely incomplete. The 223-parameter baseline is available in
`param_extraction/data/ground_truth.json`.

### 6.5 Scope limits — absence here does not mean "we disagree"
- **The RISC-V debug specification is out of scope for us.** Debug-related
  parameters (trigger/`tdata`/`dcsr`/`*context` families) are not mined by our
  pipeline. If they appear on the other list, it is a scope gap, not a conflict.
- 19 spec files are skipped as boilerplate/non-normative (bibliography, formal
  memory-model proofs, worked examples, preface/rationale/history, include
  wrappers). Findings sourced there are out of our scope.

### 6.6 Status tier must travel with every comparison
When you report an overlap or a difference, always carry **which tier** our entry
came from (§5). "The other list has X and we don't" means something very
different from "the other list has X and we have it as a mentor-confirmed
parameter."

---

## 7. Honest limits of our list

- **It is not exhaustive.** Benchmarked against the 223 parameters UDB already
  has, our pipeline recovers about **85%** in a single run and about **91%** when
  several runs are combined. So on a like-for-like basis we would expect to miss
  roughly 10–15% of findable parameters. If the other list has entries we lack,
  that is entirely plausible and expected — **not** evidence their entry is wrong.
- **The LLM is mildly non-deterministic**, so a re-run finds a slightly different
  subset; individual borderline entries can appear or vanish between runs.
- **Known systematic gaps**, useful when explaining differences:
  - **Mode-field enumeration** (per-mode booleans for `satp`/`hgatp`/`stvec`/
    `vstvec` translation and vectoring modes) — we emit the umbrella, not the N
    split rows.
  - **Prose trap/exception behaviours** — several sit in genuine tension with our
    own exclusion rules (e.g. "may cause an illegal-instruction exception or may
    [not]" reads as unspecified behaviour under our rule set, yet UDB catalogs
    such a parameter). These are open questions for the mentor.
  - **Dense sentences with multiple aspects** — where one sentence contains
    several distinct choices, we may have captured a *different aspect* than
    another analyst did. Check the excerpt before calling it a mismatch.

---

## 8. Vocabulary reference

### Classes
| Class | Meaning |
|---|---|
| `NORM_DIRECT` | Implementation picks a value directly; no CSR field controls it |
| `NORM_CSR_WARL` | The legal-value set of a WARL CSR field |
| `NORM_CSR_RW` | Whether a CSR field is read-only vs read-write (incl. "implemented, else read-only-zero") |
| `SW_RULE` | A *hardware* choice that is deterministic if software follows the spec |

Non-parameter classes that may appear in raw data: `NON_ISA` (platform/EEI-level,
outside ISA scope), `NON_NORM` (non-normative text), `DOC_RULE` (documentation
requirement), `UNKNOWN`.

### Value types
`binary` (2 choices) · `enum` (3+ discrete values) · `range` (bounded integer) ·
`set` (subset of a fixed universe) · `bitmask` (per-bit booleans) · `value`
(single unconstrained declared value).

### Column meanings in the review sheet
| Column | Meaning |
|---|---|
| `section` | Which batch/tier the row belongs to (see §5) |
| `parameter_name` | **Our suggested name** — not canonical (see §6.1) |
| `class`, `value_type` | Taxonomy above |
| `modal_signal` | The exact optionality phrase found in the excerpt |
| `adoc_file`, `line_number` | Spec location (line may drift between checkouts) |
| `tagged`, `norm_tag` | Whether the spec text carries a `[#norm:NAME]` anchor. Tagged text is normative — a positive signal |
| `refers_to_csr_field_value` | Does the text describe a CSR field value? |
| `refers_to_warl` | Does it describe WARL behaviour (including implicit WARL)? |
| `in_intro_section` | Flag for the "introduction/overview is non-normative" exclusion |
| `cross_chapter_dup` | Flag for "same concept stated in another chapter / replicated per CSR" |
| `excerpt` | **The verbatim spec sentence — the ground truth for matching** |
| `mentor_comment` | **The expert's verdict.** Empty = not yet reviewed |
| `our assessment` | **Our own opinion.** Not expert confirmation |

---

## 9. Reference files

| Path | What it is |
|---|---|
| `/Users/ashish/Downloads/params_for_review (1) (1) (1).xlsx` | Working review sheet, 51 rows, all tiers |
| `/Users/ashish/Downloads/parameter list.xlsx` | The 32 mentor-confirmed parameters (clean output) |
| `param_extraction/INCLUSION_CRITERIA.md` | The authoritative ruleset (rules 0–15) |
| `param_extraction/data/ground_truth.json` | The 223 parameters UDB already has |
| `param_extraction/taxonomy.md` | Class definitions |
| `ext/riscv-isa-manual/src/*.adoc` | The spec being mined (74 files) |

Repo: `/Users/ashish/lfx/riscv-unified-db`, branch `lfx-v3-param-rework`.
(A separate document, `param_extraction/AGENT_HANDOFF.md`, covers running the
pipeline — you do not need it for a comparison task.)
