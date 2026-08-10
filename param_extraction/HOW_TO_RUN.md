<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# How to run the parameter extraction pipeline

Reads the RISC-V spec in 60 chunks, sends each to Claude, extracts candidate
architectural parameters, then scores them against the 223 parameters UDB
already has.

**~22 minutes, ~$4 in API credits per full run.**

## Setup (once)

```bash
git clone https://github.com/ishaan-arora-1/riscv-unified-db.git
cd riscv-unified-db
git checkout lfx-v3-param-rework
git submodule update --init ext/riscv-isa-manual
```

The submodule is the spec itself — skip it and the pipeline has nothing to read.

You also need [`uv`](https://astral.sh/uv) (`brew install uv`) and an Anthropic
API key. No pip installs; `uv` handles dependencies per command.

**No need to rebuild inputs.** The chunks, the ground-truth answer key, and the
prompt are already committed. Go straight to the run.

## Run

Run these from the **repository root**, one after the other:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

```bash
PROMPT_VERSION=v5 INCLUDE_STRUCTURED_FIELDS=1 MODEL_ID=claude-sonnet-4-6 MAX_OUTPUT_TOKENS=16384 RATE_LIMIT_TPM=200000 uv run --with anthropic python param_extraction/scripts/extract.py run --model claude --force
```

```bash
PROMPT_VERSION=v5 uv run python param_extraction/scripts/extract.py merge --model claude
```

```bash
PROMPT_VERSION=v5 uv run python param_extraction/scripts/analyze.py all
```

Extract → merge → analyze. The last step prints recall and classification accuracy.

Run the first one in the background; most output is buffered until it finishes.

> **Do not** shorten this by putting the env vars in a variable
> (`COMMON="PROMPT_VERSION=v5 ..."` then `env $COMMON ...`). That works in bash
> but **silently breaks in zsh** — the macOS default shell — because zsh does not
> word-split unquoted variables, so the whole string becomes the value of
> `PROMPT_VERSION`. You get a confusing
> `FileNotFoundError: System prompt not found: .../prompts/v5 INCLUDE_STRUCTURED_FIELDS=1 MODEL_ID=...`.
> Keep the variables inline as above; it is correct in both shells.

## Gotchas

1. **`MODEL_ID` is mandatory.** The model pinned in the code
   (`claude-sonnet-4-20250514`) is retired and the run will fail without the
   override.
2. **Output filenames always say `claude-sonnet-4`**, whatever model you use.
   That is just the display name — it does not mean the override was ignored.
3. **`--force` is required to re-run.** Without it every chunk with an existing
   result is skipped ("0 processed, 60 skipped").
4. **`--force` overwrites the committed results.** Copy
   `param_extraction/results/v5/` somewhere safe first if you want to compare
   against the current baseline.

## Results

All in `param_extraction/results/v5/`:

| File | Contents |
|---|---|
| `metrics_claude-sonnet-4.json` | **Start here** — recall, precision, classification accuracy |
| `deduped_claude-sonnet-4.json` | Deduplicated candidate parameters |
| `alignment_claude-sonnet-4.json` | Findings matched to known UDB params (`udb_coverage: null` = missed) |
| `discrepancies_claude-sonnet-4.csv` | Human-readable hit/miss report |
| `claude-sonnet-4/chunk_*.json` | Raw per-chunk output |

Current baseline: **82.1% raw / 85.1% adjusted recall** (183 of 223 known params).
Expect to land within a few points — the model is mildly non-deterministic, so no
two runs are identical.

## Cheaper iteration

Target a single spec file instead of paying for a full run:

```bash
PROMPT_VERSION=v5 INCLUDE_STRUCTURED_FIELDS=1 MODEL_ID=claude-sonnet-4-6 MAX_OUTPUT_TOKENS=16384 RATE_LIMIT_TPM=200000 uv run --with anthropic python param_extraction/scripts/extract.py run --model claude --source machine.adoc --force
```

---

More detail: `README.md` (full phase guide) and `AGENT_HANDOFF.md` (project context).
