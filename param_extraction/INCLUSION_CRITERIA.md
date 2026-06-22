<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# Parameter Inclusion Criteria

The rules the pipeline uses to decide whether a spec excerpt is a real,
certifiable architectural **parameter**. This is a living document: each rule
cites its source, and new rules are added as expert review surfaces them.

## What a parameter is

An architectural parameter is an **implementation choice with a finite,
enumerable, verifiable set of legal values**, left to the implementer by the
spec, supported by an extension, and **not already captured** elsewhere in UDB.

The key test (from the certification purpose of UDB and the schema's
requirement that a description "include a list of valid values"): **if you
cannot list the legal values, or cannot verify an implementation against them,
it is not a certifiable parameter.**

A choice-word ("may", "optional", "implementation-defined") is **necessary but
not sufficient** — many sentences contain one and are still not parameters.

## Inclusion signals (necessary, not sufficient)

Optionality language that indicates a genuine implementer choice:
`may` (as optionality), `optional`/`optionally`, `implementation-defined`,
`implementation-specific`/`-dependent`, `can choose`/`can be configured`,
`is/are not required to`, `need not`, `may be zero/one`, and
"the implementation chooses/defines/selects/sets a value/width".

A value, width, or number that is *unspecified* but chosen by the
implementation (e.g. `ASID_WIDTH`) **is** a parameter — see exclusion rule 5.

## Exclusion rules (what disqualifies an excerpt)

| # | Rule | Why | Source | Pipeline action |
|---|---|---|---|---|
| 1 | Text inside `[NOTE]`/`[TIP]`/`[WARNING]`/`[IMPORTANT]` blocks | Non-normative | Phase 2 design | `REJECT_NOTE` (matched by text, not line number) |
| 2 | Fixed requirement (`must`, `shall`, `required`, `mandatory`, `always`) with no optionality | No implementer choice | Phase 2 + mentor review | `REJECT_REQUIRED` |
| 3 | Reserved / hardwired statement of fact (`reserved`, `hardwired`, `WPRI`) | Fixed, not chosen | Pre-send audit | `REJECT_RESERVED` |
| 4 | Model classified it non-architectural (`NON_ISA`/`NON_NORM`/`DOC_RULE`/`UNKNOWN`) | Out of ISA scope | Taxonomy | `DROP_NONARCH` |
| 5 | **Unspecified *behavior*/result/outcome, or "misconfigured"** | No verifiable value set — "we never certify unspecified behavior" | Mentor review 1; spec §"UNSPECIFIED Behaviors and Values" | `REJECT_UNCERTIFIABLE` (exempts unspecified *values/widths*, which are real value params) |
| 6 | **Generic WARL / read-only-vs-read-write field restatement** | Already captured by the CSR field model | Mentor review 1 (lines 11,12); manager review 2 (line 28) | `refers_to_warl=yes` column + "likely duplicate" flag |
| 7 | **From an introduction / overview section** | Intro text is essentially non-normative | Manager review 2 (line 17) | `in_intro_section=yes` column + flag |
| 8 | **Untagged text near `software`/`firmware`/`note`/`will`** | Usually a clarification or software requirement, not a parameter | Manager review 2 | `sw_keywords` column + "likely clarification" flag |
| 9 | "implementation-defined" but **no enumerable/testable options** (e.g. "bounded time limit", unknown units) | Cannot test or even emulate | Manager review 2 (lines 35,36) | flag for human review |
| 10 | A clarification that **references an already-defined parameter** | Points at an existing param, not new | Manager review 2 (line 34) | flag (duplicate check) |
| 11 | **Duplicate** — same concept is already a named UDB param or a WARL-modeled field | Not new | Mentor review 1 (line 16); manager review 2 (priority) | duplicate check vs named params + CSR-field model |

## Diagnostic columns (manager review 2)

Added to the spreadsheet so a reviewer can triage quickly:
- **`tagged`** — is the excerpt already covered by a spec tag (`[#...]`)? Tagged text is genuine normative content; untagged text near software-requirement words is usually a clarification. (If a tagged excerpt *is* a parameter, the existing `[#norm:]` tag should be upgraded to also mark it a parameter.)
- **`refers_to_warl`** — does it describe a WARL / RO-vs-RW field already covered by the CSR field model?
- **`in_intro_section`** — is the source an introduction/overview file?
- **`sw_keywords`** — which clarification/SW-requirement words appear.

## Residual human-judgment cases

Some excerpts are genuine normative **rules** but not parameters, and cannot be
labelled correctly without the design rationale — e.g. "an invalid address must
remain identifiable as invalid" (`MNEPC_INVALID_ADDRESS_CONVERSION`). These are
**flagged for human review, never auto-labelled**. (Manager review 2, line 18.)

## What is automated vs pending

- **Automated now:** rules 1–8 (rejections + diagnostic columns + WARL/RW and intro/SW flags), plus value-parameter protection for rule 5.
- **Partially automated:** rule 6/11 — the WARL/RW *phrasing* is flagged, but a full cross-reference of each candidate against the CSR-field WARL definitions (to catch duplicates that don't use the word "WARL") is the next build.
- **Human-judgment:** rules 9, 10, 12 are surfaced as flags for a reviewer.

## Sources
- **Mentor review 1**: unspecified ≠ parameter; WARL restatements already modeled; duplicate concern.
- **Manager review 2**: tagged/untagged signal; `refers_to_warl` and `tagged` columns; intro = non-normative; software/firmware/note/will keywords; "implementation-defined" with no testable options; clarifications referencing real params; rationale-dependent rules.
- **Spec**: `ext/riscv-isa-manual/src/intro.adoc` §"UNSPECIFIED Behaviors and Values".
- **Schema**: `spec/schemas/param_schema.json` (description must include a list of valid values).
- **Certification models**: `spec/std/isa/proc_cert_model/*.yaml` `param_constraints` (the parameters certification actually tracks).
