<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# Pinned sources for the cross-list comparison

Recorded so the generated documents can be regenerated and audited later.
All three inputs move independently, so a comparison is only meaningful
against a stated revision of each.

| Input | Revision | Date |
|---|---|---|
| James Ball's `param_defs` (`james-ball-qualcomm/riscv-arch-test`, branch `prep-for-crd-generators`, path `docs/crd/param_defs`) | `213450b8671a513ed94cd62fc87a836f8a839a10` | 2026-04-03 |
| RISC-V ISA manual (`ext/riscv-isa-manual` submodule) | `310a111489a0bad6e60ef4cbfba574417c6f825f` | 2026-07-29 |
| Our expert-confirmed list | `confirmed_parameters_v2.xlsx` (Allen Baum + Umer review) | 2026-07-28 |

## Notes on the manual revision

The manual organises chapters under `src/priv/`, `src/unpriv/` and
`src/profiles/`, with an Antora tree under `modules/` that duplicates `src/`
byte-for-byte. The tooling reads `src/` recursively and skips `modules/` so
nothing is counted twice.

Chapter file names are not a stable identifier. Between revisions
`counters.adoc` split into `zihpm.adoc` and `zicntr.adoc`, `rnmi.adoc` became
`smrnmi.adoc`, `scalar-crypto.adoc` became `zk.adoc`, and `indirect-csr.adoc`
became `smcsrind.adoc`. Our records therefore locate a parameter by searching
for its **excerpt**, not by file name, and record the resolved path in
`adoc_path_now`.

Prose carries cross-reference macros (`csr:mcycle[]`, `csr:mcountinhibit[cy]`,
`insn:wfi[]`, `ext:zalrsc[]`) rather than plain backticks. The tooling unfolds
any `name:target[args]` macro before matching so excerpts captured under an
older revision still resolve.

Two excerpts are reworded relative to the recorded text and are matched on an
explicit phrase instead, listed in `REWORDED` in `build_canonical_list.py`:
`XRET_CLEARS_LR_RESERVATION` (the rule now reads "If the Zalrsc extension is
supported", LR/SC having moved out of A) and `MSECCFG_SEED_BITS_RW`
(`[s,u]seed` is now written as two separate field references).

Implementation-defined behaviour is marked in `normative_rule_defs/` as
`impl-def-behavior: true`, with an optional `impl-def-category` of `WARL` or
`WLRL`. 171 rules carry the marking. All 2661 tags cited by rule definitions
resolve to an anchor in the manual.
