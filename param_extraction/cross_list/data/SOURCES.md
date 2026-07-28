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
| RISC-V ISA manual (`ext/riscv-isa-manual` submodule) | `7fc198f13ad89e9608e9404be1c7a8119c14c13b` | 2026-02-15 |
| Our expert-confirmed list | `confirmed_parameters_v2.xlsx` (Allen Baum + Umer review) | 2026-07-28 |

**Consequence worth carrying:** James' definitions are ~7 weeks newer than the
manual we resolve tags against. 44 of his 179 entries reference `impl-def`
names with no matching normative rule in the pinned manual (mostly `*_WARL`
names such as `MIP_WARL`, `SIE_WARL`, `STVEC_MODE_WARL`). Those are most
likely tags he is proposing be created, but some may simply exist upstream
already. Confirm with him before treating an unresolved tag as missing.
