<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# CLAUDE.md — LFX Parameter Extraction

Instructions for any Claude agent working on the `param_extraction/` effort.
Read `INCLUSION_CRITERIA.md` and `README.md` here before acting.

## What this is
An LFX project contributing to UDB. The RISC-V spec (`ext/riscv-isa-manual`,
~53k lines) describes **architectural parameters** — implementation choices left
to the chip designer. UDB catalogs 223 today. This pipeline uses an LLM to find
parameters not yet catalogued, classify them, validate them, and prepare them
for UDB. A **mentor reviews candidate lists** (in Excel) and gives feedback; we
refine the pipeline and the rules from his feedback. **He is the final
authority; our automation only generates candidates.**

Work happens on branch **`lfx-v3-param-rework`** (fork
`ishaan-arora-1/riscv-unified-db`). Commit + push after each meaningful change.

## The rules (authoritative source: `INCLUSION_CRITERIA.md`)
A parameter is **an implementation choice whose outcome can be observed and
tested**. A choice-word (`may`/`optional`/`implementation-defined`/`can choose`)
is necessary but NOT sufficient. Key exclusions: NOTE blocks; fixed `must`/`shall`
requirements; reserved/hardwired facts; **unspecified behavior** ("the result is
unspecified", "may or may not [happen/fail]") — but an unspecified *value/width*
IS a param, and "may or may not *support* a feature" IS a param; intro/overview
text; untagged software/firmware clarifications; duplicates; describing an
existing mechanism; extension/whole-register presence; derived-from-another-choice.

**CRITICAL — WARL is a parameter, NOT a duplicate.** A WARL / read-only-vs-read-
write field behavior IS a parameter — classify it (RW or RO0; which legal values;
conditional-on-mode). Drop it ONLY if that *specific field* is already a defined
UDB parameter (a true field-level duplicate). We once wrongly discarded all WARL
findings for a whole version; don't repeat that. WARL is the biggest category of
real params here. A notable WARL shape: a read-only field whose value **mirrors
another state bit**.

**Classes:** `NORM_DIRECT`, `NORM_CSR_WARL`, `NORM_CSR_RW` (incl. implemented-
else-read-only-zero), `SW_RULE`.

## The 4-layer process (none trusted alone)
1. **Prompt** (`prompts/v4/`): exclusions baked into extraction.
2. **Script filters** (`scripts/validate_findings.py`, `generate_spreadsheet.py`):
   mechanical rules + columns `tagged`, `refers_to_warl`, `in_intro_section`,
   `sw_keywords`.
3. **LLM adjudication** (`scripts/adjudicate.py`): semantic rules (duplicates,
   existing-mechanism, certifiability) grounded in all 223 existing params.
4. **Human (mentor):** final authority.

## Handling new mentor feedback on his Excel sheet (do exactly this)
1. **Read the `.xlsx` BY HEADER name, not by column position** (his order:
   `parameter_name,class,value_type,confidence,modal_signal,adoc_file,line_number,
   excerpt`; his comments ~col 9-10). Use `uv run --with openpyxl python`. We once
   shifted columns by reading positionally — never do that.
2. Tally his per-row verdicts (parameter / not-a-parameter / duplicate / WARL /
   unclear / conditionally-unspecified).
3. Interpret any email alongside it; verify specific claims against
   `data/ground_truth.json` (e.g. confirm a duplicate maps to a real existing param).
4. If he reveals a new/corrected rule, update `INCLUSION_CRITERIA.md` AND the
   scripts/prompt; commit each.
5. Rebuild the affected list by **re-filtering** existing data (an LLM re-run is
   only needed to find *new* params; re-filtering only removes/keeps). Verify the
   relevant params are present in the data before promising re-filter suffices.
6. Report back honestly.

## Behavioral guidance
- **Be honest about quality — never inflate counts.** If a list is thin/shaky, say so.
- **Be extremely cautious about what to add as a parameter.** Include only what's
  defensible; flag the rest for human review rather than asserting.
- **Verify before claiming** — read files, grep data, hand-review final lists.
  Don't blindly trust the LLM adjudicator (it has shown inconsistencies).
- **Mentor emails:** human tone, NO em dashes, light punctuation, ask for further
  review, note he can edit the sheet directly (he has access).
- Keep SPDX `.license` sidecars on new data files (REUSE); run
  `uvx ruff@0.15.1 check` on scripts before committing.

## Environment
- API keys: `/Users/ashish/.lfx_v3.env` (source it for LLM runs).
- Model: `claude-sonnet-4-20250514` is **dead (EOL)** — use `MODEL_ID=claude-sonnet-4-6`.
- Run scripts with `uv run` (`--with anthropic`/`--with openpyxl` as needed).

## Current state
Latest sheet: `data/params_for_review.csv`/`.xlsx` (14 V4 candidates + 24 mentor-
confirmed). Confirmed-but-deduplicated list and concrete per-param details
(`definedBy` extension, legal values, `long_name`) are NOT yet ready, so **YAMLs
are a later milestone** (start with a 1-2 param format pilot). Next work: a
field-level duplicate check (for each "optional"/WARL finding, verify it isn't
just a value of an existing CSR-field parameter — e.g. the misaligned-trap
finding maps to existing `MISALIGNED_LDST_EXCEPTION_PRIORITY`). Pending: mentor's
choice of depth (resolve duplicates on current set) vs breadth (run full
candidate set for one larger review batch).
