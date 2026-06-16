<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# Architectural Parameter Extraction — Pipeline & Run Guide

LLM-assisted discovery of architectural **parameters** (implementation choices the
spec leaves to the hardware designer) in the RISC-V ISA manual, evaluated against
the existing UDB parameter set.

This document is a phase-by-phase guide so the whole pipeline can be re-run and
inspected. Everything below is on the latest branch (`lfx-v3-param-rework`); the
"V3" prompt/results are the current version.

## Headline result (V3 vs the previous V2, both scored against the corrected 223-param ground truth)

| Metric | V2 | V3 |
|---|---|---|
| Findings in deliverable | 346 | **201** (validated) |
| Raw recall | 61.9% | **65.9%** |
| Adjusted recall | 64.2% | **68.4%** |
| Classification accuracy | 89.8% | **92.3%** |
| Precision (clear-optionality rate) | 27% | **35%** |

Final deliverables live in `data/`:
- `parameters.csv` / `.xlsx` — all 201 reviewed findings (69 already in UDB, 132 new), with a `validation` verdict, the `modal_signal` choice-word, and review flags.
- `high_confidence_new_parameters.csv` — the 37 hand-verified, high-confidence **new** parameters.
- `riscv-isa-manual-param-tags.patch` — `[#param:NAME]` tags for the spec (applies to the pinned `riscv-isa-manual` submodule).

---

## Prerequisites (once)

```bash
# 1. Clone and init the spec submodule (the pipeline reads ext/riscv-isa-manual/src)
git submodule update --init ext/riscv-isa-manual

# 2. Python deps are handled per-command by `uv run`. The LLM phase additionally
#    needs the provider SDK, supplied ephemerally with `--with`:
#       uv run --with anthropic python ...
#    (no global install required)

# 3. For the extraction phase only, set an API key:
export ANTHROPIC_API_KEY=sk-ant-...      # required for Phase 4
export OPENAI_API_KEY=sk-...             # optional, only for a GPT-4o ensemble
```

All commands are run from the repository root.

---

## The phases

Each phase is one script. Phases 1–3 and 7 are free (no API). Phase 4 calls the
LLM. `PROMPT_VERSION=v3` selects the current prompt and routes results to
`results/v3/`.

### Phase 1 — Ground truth (the answer key)
Catalogs every existing UDB parameter (currently **223**), classifies each, and
finds candidate spec locations. Outputs are the benchmark the LLM is scored against.
```bash
uv run python param_extraction/scripts/export_udb_params.py     # -> data/ground_truth.json
uv run python param_extraction/scripts/map_params_to_spec.py    # -> data/spec_mappings.json
uv run python param_extraction/scripts/generate_report.py       # -> data/parameters_catalog.csv, udb_param_names.txt
```

### Phase 2 — Taxonomy & prompt
The 8-class taxonomy (`taxonomy.md`) and the LLM prompt (`prompts/v3/`). Validate
internal consistency and check the token budget:
```bash
PROMPT_VERSION=v3 uv run python param_extraction/scripts/validate_prompt.py   # 176 checks
PROMPT_VERSION=v3 uv run python param_extraction/scripts/run_prompt.py estimate
```

### Phase 3 — Chunking
Splits the ~53k-line spec into 79 LLM-sized chunks without breaking CSR sections.
```bash
uv run python param_extraction/scripts/chunker.py run
uv run python param_extraction/scripts/chunker.py verify
```

### Phase 3.3 — Structured field index (V3 addition)
Parses register bytefield diagrams so the prompt can hand the model an explicit
list of CSR fields (helps it find bit-level parameters).
```bash
uv run python param_extraction/scripts/structured_fields.py build   # -> data/structured_fields.json
```

### Phase 4 — LLM extraction (needs ANTHROPIC_API_KEY)
Reads each chunk, extracts candidate parameters. Pilot on `machine.adoc` first,
then the full run, then merge. `INCLUDE_STRUCTURED_FIELDS=1` enables the Phase-3.3
checklist; the rate/token env vars speed the run up on a high-tier account.
```bash
COMMON="PROMPT_VERSION=v3 INCLUDE_STRUCTURED_FIELDS=1 RATE_LIMIT_TPM=200000 MAX_OUTPUT_TOKENS=16384"

env $COMMON uv run --with anthropic python param_extraction/scripts/extract.py pilot --model claude
env $COMMON uv run --with anthropic python param_extraction/scripts/extract.py run   --model claude
PROMPT_VERSION=v3 uv run python param_extraction/scripts/extract.py merge --model claude
```
Cost/time for the full run: ~$4, ~20 min. Results in `results/v3/claude-sonnet-4/`.

### Phase 5 — Analysis (recall, classification, alignment)
Deduplicates, aligns findings to UDB ground truth, and computes metrics.
```bash
PROMPT_VERSION=v3 uv run python param_extraction/scripts/analyze.py all
# -> results/v3/{deduped,alignment,metrics,discrepancies}_claude-sonnet-4.*
```

### Phase 5.1 — Validation gate (V3 addition)
Stamps every finding with a verdict (KEEP / REVIEW / FRAGMENT / REJECT_*), the
quality check that was missing before.
```bash
uv run python param_extraction/scripts/validate_findings.py \
  --deduped param_extraction/results/v3/deduped_claude-sonnet-4.json \
  --out-report param_extraction/data/validation_report_v3.csv \
  --out-stats  param_extraction/data/validation_stats_v3.txt
```

### Phase 7 — Final spreadsheet
Consolidates everything into the reviewable deliverable, runs the validation gate,
drops hard-rejects, and flags over-decomposition / non-verbatim rows.
```bash
uv run python param_extraction/scripts/generate_spreadsheet.py
# -> data/parameters.csv, data/parameters.xlsx, data/parameters_stats.txt
```

### Phase 8 — Spec tagging
Inserts `[#param:NAME]` anchors into the spec and captures the diff as a patch.
```bash
uv run python param_extraction/scripts/insert_tags.py dry-run    # preview match rate
uv run python param_extraction/scripts/insert_tags.py run        # write tags into the submodule
git -C ext/riscv-isa-manual diff > param_extraction/data/riscv-isa-manual-param-tags.patch
git -C ext/riscv-isa-manual checkout -- .                        # restore submodule working tree
```

---

## Two bugs this work found inside UDB itself
1. **Stale parameter set** — analysis assumed 185 params; UDB now has 223 (MOCK fixtures removed, 38 added). Fixed by regenerating Phase 1.
2. **Classification heuristic** — `export_udb_params.py` labeled every `_IMPLEMENTED` param `NORM_DIRECT`; the `MCTRCTL_*` family (read-only-zero when unimplemented) is actually `NORM_CSR_RW`. Fixed (21 params relabeled).

## Layout
```
param_extraction/
  scripts/     all phase scripts
  prompts/v3/  current system prompt + few-shot examples
  chunks/      Phase 3 output (79 chunk files + manifest)
  results/v3/  Phase 4/5 per-chunk + merged + analysis outputs
  data/        ground truth, spreadsheets, patch, validation reports
  taxonomy.md  parameter class definitions
```
