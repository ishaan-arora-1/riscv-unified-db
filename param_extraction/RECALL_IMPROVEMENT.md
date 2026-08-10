<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# Recall improvement: closing the extraction's known-param blind spots

## Problem

Scored against the 223 known UDB parameters, the v5 pipeline recovered only
~80% of them (`raw_recall 0.776`, `adjusted_recall 0.805`, excluding 8
debug-spec params in files we do not process). If we cannot reliably find params
we *know* exist, we are certainly missing unknown ones too. Goal: raise recall
toward 100% by making the extractor genuinely *see* params it was blind to —
without gaming the metric (loosening filters until every sentence is a
"parameter").

## Diagnosis of the 42 non-debug misses

The dominant failure was **not** blindness to a region. It was **granularity
mismatch**: UDB decomposes one spec rule into many per-bit / per-mode / per-value
parameters, and the extractor emitted the umbrella statement once.

| Bucket | Count | What happened |
|---|---|---|
| **A1** STATEEN per-bit (`MSTATEEN_/HSTATEEN_/SSTATEEN_*_TYPE`) | 10 | Extractor captured the *generic* rule `STATEEN_BIT_ACCESS` ("each bit is WARL, may be RO0") once; UDB models each named feature bit (ENVCFG, IMSIC, AIA, CONTEXT, JVT) separately. No bytefield diagram exists — the bits are prose, each `[#norm:...]` tagged. |
| **A2/A3** tvec + Sv mode enumeration (`STVEC_/VSTVEC_MODE_*`, `SV*X4`, `SV*_VSMODE`) | ~12 | Extractor found the machine-mode / one variant; UDB splits "which modes are legal" into per-mode booleans across supervisor/virtual/G-stage. |
| **B** declared value/ID/width (`MXLEN`, `ARCH_ID_VALUE`, `IMP_ID_VALUE`, `VENDOR_ID_OFFSET`, `STVAL_WIDTH`, `SEW_MIN`, `PHYS_ADDR_WIDTH`) | 7 | Stated as bare facts ("`marchid` is an MXLEN-bit read-only register encoding …") with no `may`/`optional` word, so the choice-word requirement skipped them. Extractor found the `*_IMPLEMENTED` boolean but not the chosen *value*. |
| **C** individual prose behaviors (misaligned/atomic/vector/trap) | ~13 | Genuine prose params; a few are truly blind, a few sit in tension with our exclusion rules. |

## What changed

Two levers, measured separately to keep them honest.

### 1. Model upgrade (the dominant lever)

The frozen baseline used `claude-sonnet-4-20250514` (now EOL). Re-running with
`claude-sonnet-4-6` — **no code change** — recovered Bucket A1 on its own: the
newer model reads the prose per-bit enumeration + the general WARL rule and
decomposes into per-bit params correctly. This is not gaming: the model *sees*
fields it was blind to.

### 2. Bucket-B prompt change (`prompts/v5/system_prompt.txt`)

Even the new model still missed the declared value/ID params (it emits
`MARCHID_IMPLEMENTED` but not `ARCH_ID_VALUE`). Added a **tightly-gated** signal:
a declared, implementation-chosen **value / width / ID** read back from a
register is a `NORM_DIRECT` value parameter *even without* a classic choice-word,
because the choice is inherent in the register being implementation-defined.
Guardrail baked in: do **not** emit a width that the spec fixes for all
implementations, and do **not** re-emit a width that is merely an alias of one
already emitted (e.g. `stval` being "SXLEN-bit" — correctly suppressed, so
`STVAL_WIDTH` is *not* forced as noise).

## Results (measured, not asserted)

All recall numbers are adjusted recall (debug-spec excluded). Precision proxy =
matched UDB params / total deduped candidates (higher = less noise per row the
mentor reviews).

| Run | raw recall | adj. recall | matched | candidates | precision proxy |
|---|---|---|---|---|---|
| **Baseline** (frozen, old model, old prompt) | 0.776 | 0.805 | 173 | 210 | 82.4% |
| **+ model upgrade only** (new model, old prompt) | 0.821 | 0.851 | 183 | 212 | 86.3% |
| **+ Bucket-B prompt** (single reproducible run) | 0.821 | **0.851** | 183 | 213 | **85.9%** |
| **3-run ensemble** (union of runs) | 0.879 | **0.912** | 196 | 292 | 67.1% |

**The committed run is the single reproducible run: recall AND precision both
improve over baseline — no tradeoff.** The 4 Bucket-B value params (`MXLEN`,
`ARCH_ID_VALUE`, `IMP_ID_VALUE`, `VENDOR_ID_OFFSET`) are recovered reliably
(verified excerpts, correct classes) and are cleanly attributable to the prompt
change.

### Non-determinism caveat (important)

Single-run recall has a **±3–4 point noise band** — re-rolling all 60 chunks at
temperature 0 finds a slightly different subset each time. Two independent full
runs both landed at exactly 0.851, so the *model* gain is robust, but individual
mode-enumeration params (SvXX, tvec modes) flip in and out between runs. This is
why the ensemble helps and why chasing those specific params in a single run is
fragile.

### Ensemble lever (recall vs precision — a mentor decision)

Unioning runs (a legitimate technique — every finding is a real extraction, not
a lowered bar) reaches **0.912 adjusted recall, 19 misses**, but grows the
candidate pile 210 → 292 (+39%). That is a real review-burden cost. Whether to
adopt it is the **depth-vs-breadth call already pending with the mentor**, not
something baked in unilaterally.

## What I deliberately did NOT chase, and why

- **Mode-enumeration params** (`SV*X4`, `SV*_VSMODE`, `STVEC/VSTVEC_MODE_*`):
  real UDB params, but they are UDB *decomposing* one rule into N rows. Forcing
  "one param per mode" in a single run risks overfitting to UDB's convention and
  flip-flops under non-determinism. The ensemble recovers most; otherwise this is
  a granularity call for the mentor.
- **`STVAL_WIDTH`**: correctly suppressed — it is `stval` = "SXLEN-bit", i.e.
  derived from `SXLEN` (exclusion rule 14). Forcing it would be noise.
- **`TRAP_ON_UNIMPLEMENTED_CSR`**: the spec says an unimplemented counter access
  "may cause an illegal-instruction exception or may [not]" — phrasing that our
  rule 5 treats as *unspecified behavior*, yet UDB catalogs it as a binary
  behavior choice. Genuine rule tension → **flag for the mentor**, do not force.
- **`TRAP_ON_EBREAK`, `TIME_CSR_IMPLEMENTED`**: defined only obliquely (debug
  environment / emulation prose); low-confidence to assert mechanically.

## Side effect: genuinely-new candidates

Closing the blind spots did surface new candidate params of the same shapes —
84 high-confidence candidates in the current run map to no existing UDB param,
concentrated in newer extensions (`smctr.adoc` control-transfer-records family,
`CBO_ZERO_*` atomicity, hypervisor `*_WRITABLE`/`*_RO` fields). These are the
mentor-review prize and support the hypothesis that fixing recall blind spots
also finds new params.

## Honest read on where we are

We were **not** at the spec's real limit at 0.805 — a third of the gap was our
own extractor being blind to declared values and to per-bit decomposition, both
now largely fixed. We are likely still slightly under-counting: the ensemble's
0.912 and the 84 new candidates show there is more to find. The remaining ~10%
is a mix of (a) UDB granularity conventions we should not overfit to, and (b) a
handful of prose params that need a mentor rule decision. Recommendation: adopt
the model upgrade + Bucket-B prompt as the new floor; put the ensemble and the
rule-tension params to the mentor.

## Reproduce

```bash
set -a && . /path/to/keys.env && set +a
PROMPT_VERSION=v5 INCLUDE_STRUCTURED_FIELDS=1 MODEL_ID=claude-sonnet-4-6 MAX_OUTPUT_TOKENS=16384 RATE_LIMIT_TPM=200000 uv run --with anthropic python param_extraction/scripts/extract.py run --model claude --force
PROMPT_VERSION=v5 uv run python param_extraction/scripts/extract.py merge   --model claude
PROMPT_VERSION=v5 uv run python param_extraction/scripts/analyze.py all
```
