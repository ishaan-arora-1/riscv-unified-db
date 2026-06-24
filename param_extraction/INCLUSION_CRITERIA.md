<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# Parameter Inclusion Criteria — Final Ruleset (V1–V4)

The complete set of rules for deciding whether a spec excerpt is a real,
certifiable architectural **parameter**. Consolidated from the whole project:
the original taxonomy, both expert reviews, and the V4 LLM-adjudication pass.

## 0. Definition

A parameter is **an implementation choice whose outcome can be observed and
verified** — the implementer selects from a defined set, a bounded range, or
commits to a single fixed declared value — left to the implementer by the spec,
supported by an extension, and **not already captured** elsewhere in UDB.

Master test: *if an implementation's choice cannot be observed and tested, it is
not a certifiable parameter.* This deliberately admits value/ID/reset
parameters (e.g. `ARCH_ID_VALUE`) whose value space is unconstrained but whose
chosen value is declared and readable; it excludes unspecified *behaviors*,
which cannot be tested.

## 1. Inclusion signals (necessary)

The excerpt must contain genuine optionality language:
`may` (as optionality), `optional`/`optionally`, `implementation-defined`,
`implementation-specific`/`-dependent`, `can choose`/`can be configured`,
`is/are not required to`, `need not`, `may be zero/one`, or
"the implementation **chooses / defines / selects / sets** a value/width/number".

A choice-word is **necessary but not sufficient** — it must also survive every
exclusion below.

Note on weaker words: `should` (a recommendation) and a bare `can`/`will` are
NOT by themselves optionality — untagged uses of these alongside the keywords in
rule 9 are usually clarifications, not parameters. Whether the excerpt is
**tagged** in the spec is a useful positive signal: tagged text is genuine
normative content (and if it is a parameter, its `[#norm:]` tag should be
upgraded to `[#param:]`); untagged text is more likely a clarification.

## 2. Exclusion rules (each one disqualifies)

| # | Rule — NOT a parameter if it is… | Why | First learned |
|---|---|---|---|
| 1 | Inside a `[NOTE]`/`[TIP]`/`[WARNING]`/`[IMPORTANT]` block | Non-normative | V2 |
| 2 | A fixed requirement (`must`, `shall`, `required`, `mandatory`, `always`) with no optionality | No choice | V2 / mentor |
| 3 | A reserved / hardwired statement of fact (`reserved`, `hardwired`, `WPRI`) | Fixed, not chosen | V3 audit |
| 4 | Model-classified non-architectural (`NON_ISA`/`NON_NORM`/`DOC_RULE`/`UNKNOWN`) | Out of ISA scope | Taxonomy |
| 5 | **Unspecified behavior/result/outcome** — e.g. "the result is unspecified", or "may or may not [happen/fail/update]" describing a runtime *outcome* | Intentionally unconstrained; cannot test | Mentor + V4 adjudication |
| 5a | *Exception:* an unspecified **value/width/number** the implementation picks | That IS a value parameter (e.g. ASID_WIDTH) | V3 |
| 5b | *Distinguish:* "may or may not **support / implement** a feature" is a binary **support parameter** (yes/no, testable) — keep it; it is NOT unspecified behavior | A feature-support choice is observable | Domain review |
| 6 | "Misconfigured", or implementation-defined with **no testable units / enumerable options** (e.g. "bounded time limit", unknown units), **or a value that cannot be observed/tested at all** (line 17: "kind of invisible") | Cannot test or certify | Mentor + manager |
| 7 | A plain **WARL / read-only-vs-read-write field restatement** ("field X is WARL", "each bit may be writable or read-only") | Already covered by the CSR field model | Both reviews |
| 7a | *Exception:* a **specific legal-value choice** of a WARL field (which MODE/DEPTH values are supported) | That IS a parameter | — |
| 8 | From an **introduction / overview** section | Non-normative | Manager |
| 9 | **Untagged** text that is a software/firmware requirement or clarification (keywords `software`/`firmware`/`note`/`will`). NOTE: *tagged* text is a positive signal — do not exclude it on this basis | Clarification / SW requirement, not an implementer choice | Manager |
| 10 | A clarification that **references a parameter defined elsewhere** | Points at an existing param | Manager |
| 11 | A **duplicate** — same concept as an existing UDB parameter, even under a different name or in a different location | Not new | Both reviews |
| 12 | **Describing how an existing mechanism** (lock bit, feature) already works | Not a new knob | Manager (lock bit) |
| 13 | **Extension / whole-register presence** — whether a complete extension or register exists | That's extension membership, not a parameter. *But:* whether an **optional field within a register** is implemented (read-only-zero if not) IS a `NORM_CSR_RW` parameter | V4 review |
| 14 | **Derived** — fully determined by another choice, not a free independent one | Not an independent parameter | V4 review |
| 15 | A genuine normative **rule** whose parameter-ness needs the design rationale | Cannot be decided mechanically | Manager → flag for human, never assert |

## 3. Classification (for the parameters that pass)

| Class | Meaning |
|---|---|
| `NORM_DIRECT` | Implementation picks a value directly; no CSR field controls it |
| `NORM_CSR_WARL` | The legal-value set of a WARL CSR field |
| `NORM_CSR_RW` | Whether a CSR field is read-only vs read-write (incl. field implemented-else-read-only-zero) |
| `SW_RULE` | A *hardware* choice that looks impl-defined but is deterministic if software follows the spec (e.g. `HW_MSTATUS_FS_DIRTY_UPDATE`). Distinct from rule 9: SW_RULE is still a hardware parameter; rule 9 excludes a requirement placed *on* software |

Note: a "field implemented, else read-only-zero" param is `NORM_CSR_RW`, **not**
`NORM_DIRECT` (corrected ground-truth heuristic, V3).

**Value-type accuracy:** the `value_type` must match the actual field — e.g. a
field with a numeric width is a `range`, not a `bitmask` (manager, line 15). A
mis-typed value is also a clue it may be a WARL duplicate (rule 7/11), so verify
value_type and WARL coverage together.

## 4. How the rules are enforced (defense in depth)

No single layer is trusted; a parameter must survive all four:

1. **Prompt (V4):** the exclusions are baked into extraction, so the model produces clean candidates by construction.
2. **Script filter** (`validate_findings.py` + `generate_spreadsheet.py`): mechanical rules (1–9) + diagnostic columns `tagged`, `refers_to_warl`, `in_intro_section`, `sw_keywords`.
3. **LLM adjudication** (`adjudicate.py`): the semantic rules (10–14) — duplicate detection against all existing UDB params, "describes existing mechanism", certifiability — that scripts cannot do.
4. **Human review:** the final authority. Rule 15 and any layer-disagreements go here. The automated layers are a strong *candidate generator*, not the final word.

## 5. Tagging follow-on
Where a confirmed parameter's excerpt already carries a `[#norm:NAME]` tag, the
tag should be upgraded to also indicate a parameter (`[#param:NAME]`).
