<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# Master brief — taking over the LFX Architectural Parameter Extraction project

You are taking over an in-flight LFX project on the RISC-V Unified Database (UDB).
Read this whole brief, then read the on-branch docs before you touch anything.
Think critically throughout — the previous agent was as capable as you are, so do
not follow steps mechanically. Question whether each step is the right thing to
do, and say so when you think it isn't.

---

## 0. Orientation — do this FIRST, every session

- **Repo:** `/Users/ashish/lfx/riscv-unified-db` (fork of riscv/riscv-unified-db,
  remote `https://github.com/ishaan-arora-1/riscv-unified-db.git`)
- **Our work lives ONLY on branch `lfx-v3-param-rework`.**

> ⚠️ **The working copy repeatedly drifts onto an unrelated upstream branch
> `fix/issue-1618-vmv-vi`.** This happened twice in the last session. When it
> does, `param_extraction/` looks half-empty and scripts "disappear." Do not
> panic and do not re-create anything. Just run:

```bash
git -C /Users/ashish/lfx/riscv-unified-db branch --show-current
```

If it is not `lfx-v3-param-rework`, run `git checkout lfx-v3-param-rework`.
HEAD should be **`842dc7ad`** ("feat(v5): raise param-extraction recall
0.805 -> 0.851") or later.

**Another gotcha:** `cd` inside a Bash tool call does not always persist between
calls in this environment. Use absolute paths, or re-`cd` in the same command.

### Read these, in order, before acting
| File | What it is |
|---|---|
| `param_extraction/CLAUDE.md` | How any agent should work in this project |
| `param_extraction/INCLUSION_CRITERIA.md` | **The authoritative ruleset** (rules 0–15) |
| `param_extraction/README.md` | Phase-by-phase pipeline run guide |
| `param_extraction/RECALL_IMPROVEMENT.md` | What the last session changed and measured |
| `param_extraction/taxonomy.md` | Parameter class definitions |
| `param_extraction/WORK_DESCRIPTION.md` | Describes our work + lists for an *external* agent comparing our params against someone else's (no pipeline commands) |

**The single most important rule: WARL behavior IS a parameter, not a duplicate.**
A whole version's WARL findings were once wrongly discarded. Do not repeat that.
Drop a WARL finding only if that *specific field* is already a defined UDB
parameter (a true field-level duplicate).

---

## 1. What this project is

The RISC-V spec (`ext/riscv-isa-manual/src/*.adoc` — 74 files, ~53k lines)
describes **architectural parameters**: implementation choices the spec leaves to
the chip designer (a value, a WARL legal-value set, whether a CSR field is RW vs
RO, etc.). UDB catalogs **223** of them today.

We run an LLM pipeline to (a) find parameters not yet catalogued, (b) classify
them, (c) validate them, and (d) prepare them for UDB. **A mentor reviews our
candidate lists in Excel and is the final authority. Our automation only
generates candidates.**

### The 4-layer funnel — none is trusted alone
1. **Prompt** (`prompts/v5/system_prompt.txt`) — exclusions baked into extraction.
2. **Script filters** (`scripts/validate_findings.py`, `scripts/generate_spreadsheet.py`) — mechanical rules + reviewer flag columns.
3. **LLM adjudication** (`scripts/adjudicate.py`) — dedup + certifiability, grounded in all 223 existing params.
4. **Human (mentor)** — final authority.

### Parameter classes
`NORM_DIRECT` (implementation picks a value directly) · `NORM_CSR_WARL` (legal-value
set of a WARL field) · `NORM_CSR_RW` (field RW vs read-only, incl.
implemented-else-RO0) · `SW_RULE` (hardware choice that is deterministic if
software follows the spec).

---

## 2. How the pipeline actually works

### Phase map (each phase is one script)

| Phase | Script | What it does | Costs API? |
|---|---|---|---|
| 1 | `export_udb_params.py`, `map_params_to_spec.py`, `generate_report.py` | Builds the answer key: `data/ground_truth.json` (223 params), `data/spec_mappings.json` (param → file/line), `data/udb_param_names.txt` | No |
| 2 | `validate_prompt.py`, `run_prompt.py estimate` | Prompt consistency checks + token budget | No |
| 3 | `chunker.py` | Splits the spec into **79 chunks** without breaking CSR sections | No |
| 3.3 | `structured_fields.py build` | Parses register **bytefield diagrams** (`images/bytefield/*.edn`) into a per-file CSR-field checklist appended to the prompt → `data/structured_fields.json` | No |
| 4 | `extract.py run` | **The LLM step.** Reads each chunk, extracts candidate parameters | **Yes** |
| 5 | `analyze.py all` | Dedup, align findings to ground truth, compute recall/precision metrics | No |
| 5.1 | `validate_findings.py` | Stamps each finding KEEP / REVIEW / FRAGMENT / REJECT_* | No |
| 7 | `generate_spreadsheet.py` | Builds the reviewable deliverable | No |
| 8 | `insert_tags.py` | Inserts `[#param:NAME]` anchors into the spec, captured as a patch | No |
| — | `generate_param_yamls.py` | Drafts UDB param YAMLs (see §7) | No |

### How extraction works, concretely
Each of the 79 chunks becomes one LLM call. The **user message** is assembled in
`extract.py:build_user_message()` from three parts:
1. **Few-shot examples** (`prompts/v5/examples.json`)
2. **The list of all 223 known UDB parameter names** (see the integrity note in §6)
3. **The spec chunk itself**, plus (when `INCLUDE_STRUCTURED_FIELDS=1`) the
   bytefield-diagram field checklist for that file/line window.

The **system prompt** (`prompts/v5/system_prompt.txt`) carries the definition,
the inclusion signals, the hard exclusions, the class taxonomy, the
"commonly missed patterns" list, and the required JSON output schema. The model
must return `parameters[]` (each with `excerpt`, `line_number`,
`parameter_name`, `existing_udb_name`, `class`, `value_type`, `modal_signal`,
`confidence`, `reasoning`) plus `skipped_non_parameters[]`.

19 source files are skipped as boilerplate/non-normative
(`SKIP_SOURCE_FILES` in `extract.py`), so **60 chunks** actually run.

### Running it (the exact commands that work today)

```bash
set -a && . /Users/ashish/.lfx_v3.env && set +a
COMMON="PROMPT_VERSION=v5 INCLUDE_STRUCTURED_FIELDS=1 MODEL_ID=claude-sonnet-4-6 MAX_OUTPUT_TOKENS=16384 RATE_LIMIT_TPM=200000"

env $COMMON uv run --with anthropic python param_extraction/scripts/extract.py run --model claude --force
PROMPT_VERSION=v5 uv run python param_extraction/scripts/extract.py merge --model claude
PROMPT_VERSION=v5 uv run python param_extraction/scripts/analyze.py all
```

- A full run is ~60 calls, ~1.2M input tokens, **~22 minutes**. Run it in the background.
- `--force` is required to re-extract; without it, chunks with existing results are skipped.
- **`MODEL_ID` is mandatory.** The pinned `claude-sonnet-4-20250514` is **EOL/dead**.
  Use `claude-sonnet-4-6`. Note the *display name* in output filenames stays
  `claude-sonnet-4` regardless — do not be confused by that.
- Use `--source <file>.adoc` to re-run just one file's chunks (cheap iteration).
- Always `uvx ruff@0.15.1 check` any script you edit; keep SPDX `.license`
  sidecars on new data files (REUSE compliance).

---

## 3. Current state — measured numbers

Committed run (HEAD `842dc7ad`), scored against the 223 known params. "Adjusted"
recall excludes 8 debug-spec params that live in files we deliberately do not process.

| Run | raw recall | adj. recall | matched | candidates | precision proxy |
|---|---|---|---|---|---|
| Old baseline (frozen, EOL model, old prompt) | 0.776 | 0.805 | 173 | 210 | 82.4% |
| Model upgrade only | 0.821 | 0.851 | 183 | 212 | 86.3% |
| **Committed single run** (upgrade + prompt fix) | **0.821** | **0.851** | **183** | **213** | **85.9%** |
| 3-run ensemble (union) | 0.879 | **0.912** | 196 | 292 | 67.1% |

Classification accuracy: **0.881**. Precision proxy = matched / total candidates.

**The committed run improves recall AND precision over baseline — no tradeoff.**
The ensemble is an available lever, not the default (see §6).

---

## 4. What the last session did (and what it did NOT do)

The pipeline was recovering only ~80% of *known* params, so it was certainly
missing unknown ones. Diagnosis of the 42 non-debug misses found three real
blind spots:

1. **Per-bit register fields collapsed into one finding** (~10 params).
   The STATEEN registers state a general rule ("each bit is WARL, may be
   read-only zero or one") and then name individual bits (ENVCFG, IMSIC, AIA,
   CONTEXT, CSRIND, JVT) in prose. UDB catalogs **one param per named bit**; the
   old model emitted a single umbrella finding.
   **Fix: the model upgrade alone solved this** — no code change.
   ⚠️ The original hypothesis was "these are trapped in register *diagrams*."
   **That was wrong** — `smstateen.adoc` has no bytefield diagram; the bits are
   pure prose. The diagram tooling (`structured_fields.py`) was already enabled
   and did not need changing. Do not repeat that misdiagnosis.

2. **Declared values/IDs/widths with no choice-word** (~4–6 params).
   `MXLEN`, `ARCH_ID_VALUE`, `IMP_ID_VALUE`, `VENDOR_ID_OFFSET` are stated as
   flat facts ("The `misa` CSR is MXLEN bits wide") with no *may/optional*, so
   the choice-word requirement skipped them. The model found the neighbouring
   `*_IMPLEMENTED` boolean but never the chosen **value**.
   **Fix: a tightly-gated addition to `prompts/v5/system_prompt.txt`** — a
   declared, implementation-chosen value/width/ID read back from a register is a
   `NORM_DIRECT` parameter even without a modal word.
   **Guardrail that proves it isn't gaming:** it explicitly must not emit a width
   that is merely derived/aliased. Verified: it correctly **skips** `STVAL_WIDTH`
   (because `stval` is just "SXLEN-bit").

3. **Run-to-run randomness dropping real params** (~8 params).
   **Fix: union multiple runs** (ensemble) → 0.912.

---

## 5. The deliverables and the Excel files

### `/Users/ashish/Downloads/params_for_review (1) (1) (1).xlsx` — the current review sheet
One sheet, `params_for_review`, **51 data rows**, **16** columns (read **by header
name, never by position** — we once shifted columns by reading positionally):

`section, parameter_name, class, value_type, modal_signal, adoc_file,
line_number, tagged, norm_tag, refers_to_csr_field_value, refers_to_warl,
in_intro_section, cross_chapter_dup, excerpt, mentor_comment, our assessment`

Sections, newest on top:
| Section | Rows | Status |
|---|---|---|
| `V5 - for review (improved-recall pipeline)` | 8 | **Still awaiting mentor verdicts** |
| `0. NEW - likely duplicate/replication` | 5 | **Still awaiting mentor verdicts** |
| `1. V4 - for review` | 14 | Mentor reviewed (9 confirmed, 3 hedged, 2 rejected) |
| `2. Mentor-confirmed (V3)` | 24 | Mentor reviewed — all confirmed |

Changes in this revision vs the earlier `(1) (1).xlsx`: a dedicated
**`our assessment`** column was added and our "OUR ASSESSMENT:" text moved into
it; the three `0. NEW - genuinely new` rows were merged into the V5 section
(V5 is now 8 rows); and `ZCMP_PUSH_BUS_FAULT_HANDLING` was removed.

> 🚩 **CRITICAL — the two voices are now in two separate columns.**
> - **`mentor_comment`** = the mentor's own verdict (*"parameter !"*,
>   *"duplicate"*, *"WARL behavior"*, *"possibly a parameter; depends…"*).
> - **`our assessment`** = **our** opinion, prefixed "OUR ASSESSMENT:".
>
> **Verified as of this revision: all 8 V5 rows and all 5 "0. NEW" rows have an
> EMPTY `mentor_comment`.** Despite the file being circulated as "reviewed", the
> mentor has **not** recorded verdicts on V5. Never present an
> `our assessment` row as mentor-confirmed.

Two reviewer-flag columns are frequently misread — they map to exclusion rules:
- **`cross_chapter_dup`** → rule 11. The spec repeats normative statements across
  chapters; flags "same concept already stated elsewhere."
- **`in_intro_section`** → rule 8. Intro/overview sections are non-normative.

### `/Users/ashish/Downloads/confirmed_parameters.xlsx` — the shareable list
**32 mentor-confirmed parameters** (24 from V3, 8 from V4), deduplicated
(`CTR_CCE_WIDTH` appeared in both). Columns: `parameter_name, class, value_type,
adoc_file, line_number, excerpt, mentor_verdict, review_batch`.

Deliberately **excluded** from that list:
- **3 hedged** — mentor said "possibly"/"arguably", not firm:
  `CTR_MISP_IMPLEMENTED`, `CTR_CYCLE_COUNT_IMPLEMENTED`, `CTR_RASEMU_IMPLEMENTED`.
- **2 rejected as duplicates:** `WFI_U_MODE`, and the V4 copy of `SENVCFG_FIOM_ACCESS`.
- **All V5 + "0. NEW" rows** — not yet mentor-reviewed.

### The 5 V5 candidates awaiting mentor review
`HTVAL_LEGAL_VALUES`, `MTVAL2_LEGAL_VALUES` (flagged in-row as a per-CSR replica
of htval), `HGATP_PPN_LOWER_BITS_RO`, `MCYCLE_SHARED`, `MSTATEEN_BIT63_TYPE`.

These came from a critical rule-by-rule pass over 84 high-confidence
non-matching candidates (130 in the ensemble). Held back deliberately, with
reasons: `ZCMP_INTERRUPTS_DURING_SEQUENCE` (inside a `NOTE:` block → rule 1),
`MISELECT_WIDTH` (the sheet already calls SISELECT/VSISELECT replicas of it),
`HTINST_LEGAL_VALUES` / `MTINST_LEGAL_VALUES` (lean rule 12), `EGSMAX`
(possibly derived, rule 14), `GEILEN`/VGEIN (framing ambiguous),
`MISA_COLLECTIVE_WARL_CONSTRAINTS` (overlaps UDB's `MUTABLE_MISA_*`).

---

## 6. Honest caveats you must carry forward

1. **Recall is measured under "assisted naming."** Every extraction prompt is fed
   the list of all 223 UDB parameter **names** (`data/udb_param_names.txt`, via
   `format_param_names_section()` in `run_prompt.py`), instructed: *"When a
   parameter you find matches one of these known names, use the exact name."*
   It is **not** given their definitions, excerpts, or locations, and is not told
   to go find them. Evidence it isn't just parroting: it still *misses* ~15–20%
   of names sitting in that list, and every hit requires a matching verbatim
   excerpt from the chunk. **But a fully blind recall check (name list removed,
   concept-matched afterwards) has NOT been run.** That is an open, worthwhile
   experiment and the number would likely be somewhat lower.

2. **Non-determinism: single-run recall has a ±3–4 point noise band.** Even at
   temperature 0, re-rolling all 60 chunks finds a slightly different subset.
   Two independent full runs both landed at exactly 0.851, so the *model* gain is
   robust — but individual mode-enumeration params flip in and out. **Never treat
   a single run's decimal as truth; re-run or ensemble before concluding.**

3. **The ensemble's cost is real.** 0.912 recall, but candidates 210 → 292 (+39%)
   and precision proxy drops to 67.1%. Whether to adopt it is a
   **depth-vs-breadth decision for the mentor**, not a unilateral one.

4. **The remaining ~15% is mostly not blindness.** Pattern analysis of the
   remaining misses:
   - **~40% MODE-field enumeration** (`SV32/39/48/57_VSMODE`, `SV*X4`,
     `STVEC_MODE_*`, `VSTVEC_MODE_*`, `VSSTAGE_MODE_BARE`). UDB splits one WARL
     MODE field into one boolean per legal mode. The model sees the field and
     emits one finding. **Chasing this teaches overfitting to UDB's row-splitting
     convention, not new sight.** Flagged as a granularity question for the mentor.
   - **~25% prose trap/exception behaviors** (`TRAP_ON_UNIMPLEMENTED_CSR`,
     `LRSC_MISALIGNED_BEHAVIOR`, `MTVEC_ILLEGAL_WRITE_BEHAVIOR`,
     `PRECISE_SYNCHRONOUS_EXCEPTIONS`, `TIME_CSR_IMPLEMENTED`…). Several are
     genuine **rule tensions** — e.g. `TRAP_ON_UNIMPLEMENTED_CSR` is spec'd as
     "may cause an illegal-instruction exception or may [not]", which our rule 5
     treats as unspecified behavior yet UDB catalogs. **Needs a mentor ruling,
     not a pipeline tweak.**
   - **~19% "one passage, multiple aspects"** vector semantics — the model
     extracts one aspect of a dense sentence, UDB catalogued a sibling aspect.
   - Remainder: run-to-run noise the ensemble already handles.

5. **Diminishing returns are visible.** Tripling the candidate pool (84 → 130)
   yielded only ~1 additional valid new parameter; ~50 of the 52 extras were
   duplicates or non-params. That is a real signal the genuinely-new well is
   getting shallow.

6. **Do NOT game recall.** The failure mode is loosening filters until every
   sentence is a "parameter." That lifts recall against the 223 but buries the
   mentor and destroys precision. A real fix makes the extractor **see** something
   it was blind to (a diagram field, a declared value) — it never lowers the bar.
   **If you are tempted to relax an inclusion rule, stop and ask. Rule changes go
   through the mentor.** Always track recall **and** candidate count together.

---

## 7. The YAML milestone (not started beyond drafts)

Goal: emit UDB-ready `spec/std/isa/param/NAME.yaml` files. `generate_param_yamls.py`
has produced **37 drafts** in `param_extraction/generated_params/`, but they are
full of `# TODO` and are **not submission-ready**.

The schema `spec/schemas/param_schema.json` **requires**: `$schema`, `kind`,
`description`, `long_name`, `definedBy`, `schema`.

| Field | Status |
|---|---|
| `$schema`, `kind`, `name` | ✅ Automatable (boilerplate) |
| `description` | ⚠️ We have the raw excerpt; UDB wants a clean semantic description |
| `long_name` | ❌ Generator writes `TODO` |
| `schema` | ⚠️ We have coarse `value_type`; UDB needs exact bounds (e.g. `ASID_WIDTH` = integer 0..16; a bitmask needs a fixed array length) |
| `definedBy` | ❌ **The real blocker** — which extension(s) enable it, plus conditions (e.g. `ARCH_ID_VALUE` is `allOf: [Sm, MARCHID_IMPLEMENTED==true]`). Not derivable from the spec sentence alone. Generator guesses `Sm` with a TODO. |

Optional `requirements: idl()` encodes machine-checkable constraints
(e.g. `MXLEN == 32 -> ASID_WIDTH <= 9`).

**Recommended approach:** do **not** mass-generate. Build **1–2 fully correct
pilot YAMLs** by hand for clean confirmed params (`HGATP_PPN_LOWER_BITS_RO` is a
good candidate — plain boolean, H extension), validate against the schema, show
the mentor to confirm the `definedBy`/`description` conventions, *then* decide
whether to scale.

---

## 8. Suggested next steps (in priority order)

1. **Get the mentor's verdict on the 5 V5 candidates** + the "0. NEW" rows.
2. **Put the two open rule questions to the mentor:**
   (a) the MODE-field granularity question — does he want one param per legal
   mode, or is the umbrella finding fine?
   (b) the rule-5 tension on "may X or may not X" behaviors that UDB nonetheless
   catalogs (`TRAP_ON_UNIMPLEMENTED_CSR`).
3. **Depth vs breadth:** ask whether to adopt the ensemble (0.912 recall, +39%
   candidates) or stay with the clean single run.
4. **Run the blind-recall experiment** (§6.1) to quantify the name-list assist.
5. **YAML pilot** (§7).

---

## 9. Behavioral rules (from the mentor's working agreement)

- **Be honest about quality. Never inflate counts.** If a result is thin or
  shaky, say so plainly. Do not claim something worked if it didn't. If a
  hypothesis turns out wrong (like the diagram theory), say so rather than
  claiming credit.
- **Be extremely cautious about what you call a parameter.** Include only the
  defensible; flag the rest for human review rather than asserting.
- **Verify before claiming** — read the files, grep the data, hand-check lists.
  Do not blindly trust the LLM adjudicator; it has been inconsistent.
- **Measure, don't assert.** Re-run metrics after every change and compare to the
  stored baseline. Keep baselines so you can diff.
- **Back up before re-extracting** — `extract.py --force` overwrites committed
  per-chunk results. Copy `results/v5/claude-sonnet-4/` somewhere outside the
  repo first.
- Commit and push after each meaningful, verified step, with honest messages.
- **Mentor emails:** human tone, no em dashes, light punctuation, ask for further
  review, note he can edit the sheet directly (he has access).
- Don't stop between phases to ask "should I continue" — continue. Come back only
  for keys, a mentor-level decision, or something you genuinely cannot resolve.

---

## 10. Environment

- **API keys:** `/Users/ashish/.lfx_v3.env` — **outside the repo; never commit it
  or paste its contents.** Defines `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`.
  Load with `set -a && . /Users/ashish/.lfx_v3.env && set +a`. If a call 401s,
  ask the user to refresh.
- **Python:** always `uv run --python 3.13` (the bare interpreter has glitched).
  Add `--with anthropic` / `--with openpyxl` as needed. If importing a sibling
  script fails, inline the logic instead.
- **Spec submodule:** `ext/riscv-isa-manual` must be initialised
  (`git submodule update --init ext/riscv-isa-manual`); 74 `.adoc` files in `src/`.

### Key paths quick reference
```
param_extraction/
  CLAUDE.md, INCLUSION_CRITERIA.md, README.md, RECALL_IMPROVEMENT.md, taxonomy.md
  prompts/v5/system_prompt.txt        # the live prompt (v1-v4 are history)
  prompts/v5/examples.json            # few-shot examples
  scripts/                            # 14 phase scripts
  chunks/                             # 79 chunk .txt files + manifest.json
  data/ground_truth.json              # the 223-param answer key
  data/spec_mappings.json             # param -> spec file/line
  data/udb_param_names.txt            # name list fed into the prompt
  data/structured_fields.json         # bytefield-diagram field index
  results/v5/claude-sonnet-4/         # per-chunk raw results (60 files)
  results/v5/all_results_*.json       # merged
  results/v5/deduped_*.json           # deduplicated candidates
  results/v5/alignment_*.json         # findings <-> ground truth ("udb_coverage": null = missed)
  results/v5/metrics_*.json           # recall / precision / classification
  results/v5/discrepancies_*.csv      # human-readable miss report
  generated_params/                   # 37 draft YAMLs (TODO-laden)
ext/riscv-isa-manual/src/*.adoc       # the spec being mined
spec/schemas/param_schema.json        # UDB param YAML schema
spec/std/isa/param/*.yaml             # real UDB params (reference examples)
```

**Useful one-liner — list the currently-missed known params:**
```bash
cd /Users/ashish/lfx/riscv-unified-db/param_extraction && uv run --python 3.13 python -c "
import json
DEBUG=('DBG_','DCSR_','TRIGGER_','TDATA_','MCONTEXT_','HCONTEXT_','SCONTEXT_')
cov=json.load(open('results/v5/alignment_claude-sonnet-4.json'))['udb_coverage']
missed=[k for k,v in cov.items() if v is None and not any(k.startswith(p) for p in DEBUG)]
print(len(missed)); [print(' ',n) for n in sorted(missed)]"
```
