<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# Getting our 38 parameters into UDB — working brief

Everything needed to pick this up cold. Background on the wider effort is in
`param_extraction/CLAUDE.md`; the ruleset is `INCLUSION_CRITERIA.md`; the
three-way list comparison is in `cross_list/`.

---

## 1. The decision this encodes

Our 38 expert-confirmed parameters are authored in **James Ball's
parameter-definition format** rather than written straight to UDB YAML, so that
his existing toolchain carries them the rest of the way.

Why, in one line: his chain already solves the two hard mechanical steps
(resolving a normative rule to its defining extension, and turning a declared
domain into JSON Schema), and it is the format he proposed as the shared one,
so authoring into it is the merge path rather than a third parallel track.

The alternative — extending our own `../scripts/generate_param_yamls.py` — is
faster and depends on nobody, but becomes throwaway the moment the SIG adopts
his format.

---

## 2. The pipeline

```
ext/riscv-isa-manual/normative_rule_defs/*.yaml
        │
        ├── (real) docs-resources create_normative_rules.py ─┐
        └── (local) ../scripts/make_norm_rules_json.py ─────────┤
                                                             ▼
        ../scripts/build_param_defs.py ──► param_defs/*.yaml    │
                                              │              │
                                              ▼              ▼
                              docs-resources create_params.py
                                              │
                                              ▼   build/params.json
                              docs-resources export_params_to_udb.py
                                              │
                                              ▼   build/udb_params/*.yaml
```

Only the two `../scripts/` entries are ours. Everything else is his, run unmodified.

`make_norm_rules_json.py` stands in for `create_normative_rules.py`, which also
wants tag JSON from the manual's asciidoctor build. That build is not needed to
drive the rest of the chain — `create_params.py` only indexes rules by name and
reads `kind`/`instance`/`impl-def-category`, all of which are already in the
YAML. **It does not verify that each rule's tag appears in the rendered manual,
which is the real tool's actual job. Run the genuine tool before anything
ships.**

---

## 3. Running it

Needs `riscv/docs-resources` checked out somewhere (`$DR` below); the
`ext/docs-resources` submodule in this repo is registered but not initialised.

```bash
cd param_extraction/udb_export
uv run --python 3.13 --with pyyaml python ../scripts/make_norm_rules_json.py
uv run --python 3.13 --with pyyaml python ../scripts/build_param_defs.py
uv run --python 3.13 --with pyyaml --with jsonschema python $DR/tools/create_params.py \
    -n build/norm-rules.json $(for f in param_defs/*.yaml; do echo -n "-d $f "; done) \
    --output build/params.json
uv run --python 3.13 --with pyyaml python $DR/tools/export_params_to_udb.py \
    -i build/params.json -o build/udb_params
```

Validate the authored files against his schema:

```bash
uv run --python 3.13 --with pyyaml --with jsonschema python ../scripts/build_param_defs.py \
    --validate --schema-dir $DR/schemas
```

`uvx ruff@0.15.1 check ../scripts/` before committing. `param_defs/` is generated —
edit `../scripts/authoring_table.py`, never the YAML.

---

## 4. Current state

| | |
|---|---|
| Parameters authored | 38 |
| Validate against his `param-defs-schema.json` | 38 / 38 |
| Accepted by his `create_params.py` | 38 / 38 |
| Exported UDB YAMLs valid against `spec/schemas/param_schema.json` | 38 / 38 |
| **`definedBy` correct** | **22 / 38** |
| `definedBy` wrongly `extension: I` | 16 |
| Domain shape is an approximation | 8 |

`build/` is not committed; regenerate it.

---

## 5. The 16 with a wrong `definedBy`

His schema constrains `impl-def` names to `^[A-Z][A-Z0-9_]+$`. The manual gives
a rule an upper-case name only when it is also marked `impl-def-behavior: true`
— across all 2,822 rules, **185 carry the marking and every one of them also has
the upper-case name and a `kind`/`instance`; none has the marking without
them.** Our remaining 16 point at rules that were never marked, whose names are
lower case, so there is no valid `impl-def` to write for them.

Those entries still validate and still compile (his schema allows omitting
`impl-def` when a `description` is present). But `export_params_to_udb.py`
line 86 then falls back to `extension: {name: I}` **silently**, which is wrong
for all 16. `param_defs/build_report.json` lists exactly which, so the fallback
is never mistaken for a result.

These 16 are the same set already documented in
`cross_list/out/list_comparison.adoc` as "15 rules that are parameters but are
not marked as such", plus `MSECCFG_SEED_BITS_RW`, which carries no tag at all.
Fixing them in the manual repo is therefore not housekeeping — **it is the
precondition for this pipeline producing correct output**, and it is what James
asked for in his email. Deferred deliberately; not started.

---

## 6. Where judgement lives

`../scripts/authoring_table.py` holds every non-mechanical decision, one row per
parameter, so each can be challenged individually:

- **`long_name`** — written by us. Nothing to copy: 86 of James' 93 are the
  placeholder `NAME-TBD`, and 166 of UDB's own 223 are literally `TODO`.
- **`shape`** — how each domain maps onto his type system.
- **`note`** — the mentor's own condition, where he recorded one. His exporter
  appends it to the description, so it survives into the UDB YAML.

### The 8 approximations

His schema offers `type` (scalar token or enum list), `range` and `array`
(*fixed* index bounds). It has **no way to express a variable-length subset of
a set**, which is what several of our WARL findings actually are. Those are
modelled as a fixed-length per-element boolean mask — testable and close, but
our reading rather than his schema's intent. Each is marked `approx` in the
table, with the reason carried into the emitted `note`. **All 8 need a human
ruling before shipping.** The starkest is `CSR_STRONGLY_ORDERED`, a 4,096-entry
per-CSR-address mask.

---

## 7. Defects found in his tooling while doing this

Worth passing back, alongside those already listed in `cross_list/README.md`.

- **`export_params_to_udb.py` does not dedupe extension names.** It appends one
  per `impl-def`, so an entry citing several impl-defs that resolve to the same
  extension emits `anyOf: [Sm, Sm]`. Semantically harmless, but it looks wrong
  in a PR. Hits 3 of our 38 (`DELEGATABLE_EXCEPTIONS`,
  `XRET_CLEARS_LR_RESERVATION`, `STANDARD_INTERRUPT_SUPPORT`) and **18 entries
  in his own list**, including `HPM_READ_BEHAVIOR`. One-line fix.
- **The `extension: I` fallback is silent.** No warning, no error. Given the
  marking gap above this will mislabel real parameters, and nothing in the
  output says so. It should fail loudly instead.
- **Its output would fail REUSE lint in this repo.** No SPDX header and no
  `# yaml-language-server:` line; all 223 existing UDB param files carry both.
  Needs a post-step before any PR.
- **`long-name` is optional in his authoring schema but fatal in his exporter.**
  Masked today only because he fills `-TBD` on every entry.

---

## 8. Not done

1. **The CSR-field linkage.** 23 of our 38 are `NORM_CSR_RW`/`NORM_CSR_WARL`.
   For those the parameter YAML alone does nothing — the field in
   `spec/std/isa/csr/*.yaml` has to reference it back (`definedBy: param:`, or
   IDL in the field's behaviour). That is a hand edit to an existing file per
   parameter and no tool here touches it. It is the larger half of the
   remaining work.
2. **The manual PR** for the 16 unmarked rules (§5).
3. **`requirements`** — the mentor recorded real conditions ("true only if
   `exists(satp)`", "true only if `sie[i]` is read-only zero"). They currently
   ride along as prose in `note`; none is expressed as UDB IDL.
4. **Nothing has been proposed to UDB.** `build/udb_params/` is a staging area,
   not a PR.

---

## 9. Traps

- **A tag can carry more than one rule.** Several tags have both an
  implementation-defined-behaviour entry and an ordinary normative-rule entry.
  Index tags to a *list*; keeping only the last silently drops the useful one
  and cost us `SSTATUS_UBE_ACCESS` on the first pass.
- **Rules name behaviours under `names` as well as `name`.** `MEDELEG_WARL`,
  `MIDELEG_WARL`, the four `*_INTR_IMPL` rules and the `xRET` pair all live
  under the plural key. Reading only `name` loses them — and led us to state,
  wrongly, in `cross_list/out/list_comparison.adoc`, that three of our anchors
  have no normative rule entry. **That claim in the published document is
  incorrect and still needs correcting.**
- **`instance` versus `instances`.** The rule defs write a single extension as
  `instance: Sm`; `norm-rules-schema.json` has only `instances`, and
  `export_params_to_udb.py` reads nothing else. Pass the singular form through
  raw and *every* parameter silently falls through to `extension: I`. The real
  `create_normative_rules.py` folds one into the other (lines 183–192).
