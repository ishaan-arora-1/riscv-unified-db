<!--
SPDX-FileCopyrightText: 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
SPDX-License-Identifier: BSD-3-Clause-Clear
-->

# Scripts Directory

Every command-line tool and helper module used by the LFX architectural
parameter work. Three workstreams share this directory:

1. **Extraction** — mine the ISA manual for parameters UDB does not have.
   Outputs the mentor's review spreadsheet. See `../README.md`.
2. **Cross-list comparison** — compare our list against James Ball's and
   against UDB, and build the master list. See `../cross_list/README.md`.
3. **UDB export** — author our confirmed parameters in James' schema so his
   toolchain can emit UDB YAML. See `../udb_export/README.md`.

Rules that apply to all of them: run with `uv run` (no global installs), keep
SPDX `.license` sidecars on new data files, and `uvx ruff@0.15.1 check scripts/`
before committing. Paths inside every script resolve from the repository root,
so they can be invoked from anywhere.

**Generated files are generated.** `cross_list/out/*.adoc`, `master_list.*` and
`udb_export/param_defs/*.yaml` are all script output. Edit the generator, never
the artefact — a rerun wipes hand edits, and this has already happened once.

---

## Python Scripts At A Glance

| Script | Workstream | Type | Purpose |
|---|---|---|---|
| `chunker.py` | Extraction | Helper module | Splits spec `.adoc` files into semantically coherent chunks that keep CSR sections intact and fit the LLM context window. |
| `run_prompt.py` | Extraction | Helper module | Assembles system prompt + few-shot examples + UDB parameter names + spec chunk into one complete prompt. |
| `structured_fields.py` | Extraction | Helper module | Pre-extracts CSR fields from bytefield diagrams, which the extraction LLM reads badly as raw prose. |
| `export_udb_params.py` | Extraction | CLI tool | Exports all UDB `spec/std/isa/param/*.yaml` to structured JSON, deriving value types from JSON Schema. The ground-truth baseline. |
| `map_params_to_spec.py` | Extraction | CLI tool | Locates each UDB parameter's source sentence in the spec `.adoc` files. |
| `generate_report.py` | Extraction | CLI tool | Human-readable report and CSV over the ground truth and spec mapping. |
| `validate_prompt.py` | Extraction | CLI tool | Checks the prompt deliverables: taxonomy completeness, example structure, output schema. |
| `extract.py` | Extraction | CLI tool | Runs the LLM extraction over the chunks and stores structured results per chunk. |
| `validate_findings.py` | Extraction | CLI tool | Mechanical filter layer: applies the inclusion rules a script *can* decide (NOTE blocks, fixed `must`/`shall`, reserved, unspecified behaviour). |
| `adjudicate.py` | Extraction | CLI tool | LLM adjudication layer: the semantic rules a script cannot decide (duplicates against all UDB params, existing-mechanism, certifiability). |
| `analyze.py` | Extraction | CLI tool | Deduplicates and aligns extraction results against ground truth; produces recall/precision metrics and discrepancy reports. |
| `generate_spreadsheet.py` | Extraction | CLI tool | Builds the mentor's review spreadsheet from the deduplicated results, ground truth and alignment. |
| `insert_tags.py` | Extraction | CLI tool | Inserts `[#param:NAME]` tags into the ISA manual for confirmed parameters. |
| `generate_param_yamls.py` | Extraction | CLI tool | **Superseded.** Earlier direct-to-UDB YAML stub generator; reads a stale V3 input. Kept for reference — use the UDB-export chain instead. |
| `build_canonical_list.py` | Cross-list | CLI tool | Reduces the 44 reviewed rows to the canonical 38 de-duplicated parameters. |
| `measure_tag_join.py` | Cross-list | CLI tool | Measures whether the normative tag works as a join key between the two lists. Diagnostic; not part of the build. |
| `segment_james_vs_udb.py` | Cross-list | CLI tool | Segments James' "only on his list" entries against UDB: already present, partial overlap, genuinely new, out of scope. |
| `audit_james_vs_criteria.py` | Cross-list | CLI tool | Applies our `INCLUSION_CRITERIA.md` to his entries, so both lists are judged on one standard. |
| `generate_asciidoc.py` | Cross-list | CLI tool | Emits the two SIG deliverables: `parameter_lists.adoc` and `list_comparison.adoc`. |
| `generate_master_list.py` | Cross-list | CLI tool | Builds the master list, one row per distinct parameter concept, as CSV, XLSX and AsciiDoc. |
| `make_norm_rules_json.py` | UDB export | CLI tool | Builds the `norm-rules.json` James' `create_params.py` consumes, straight from the manual's rule definitions. Stands in for his `create_normative_rules.py`. |
| `authoring_table.py` | UDB export | Helper module | Every non-mechanical decision for the 38: `long_name`, how each domain maps onto his type system, and the mentor's conditions. **Judgement lives here, not in code.** |
| `build_param_defs.py` | UDB export | CLI tool | Writes our 38 parameters as `udb_export/param_defs/*.yaml` in James' `param-defs-schema.json` format. |

---

## Running a workstream end to end

### Cross-list comparison

```bash
cd param_extraction
uv run --python 3.13 --with openpyxl python scripts/build_canonical_list.py
uv run --python 3.13 --with pyyaml  python scripts/generate_asciidoc.py
uv run --python 3.13 --with pyyaml  python scripts/segment_james_vs_udb.py
uv run --python 3.13 --with pyyaml  python scripts/audit_james_vs_criteria.py
uv run --python 3.13 --with pyyaml  python scripts/generate_asciidoc.py
uv run --python 3.13 --with pyyaml  python scripts/generate_master_list.py
```

`generate_asciidoc.py` runs twice on purpose: the first pass emits
`data/only_james.json`, which `segment_james_vs_udb.py` consumes, and the
second pass renders the resulting segmentation. Needs the ISA manual submodule
(`git submodule update --init ext/riscv-isa-manual`).

### UDB export

Needs `riscv/docs-resources` checked out somewhere — `$DR` below. The
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

### Extraction

The LLM stages cost money and take time; they are not part of a routine
rebuild. Source `~/.lfx_v3.env` for API keys first, and set
`MODEL_ID=claude-sonnet-4-6` — `claude-sonnet-4-20250514` is end-of-life.

```bash
cd param_extraction
uv run --with anthropic  python scripts/extract.py            # costs money
uv run                   python scripts/validate_findings.py
uv run --with anthropic  python scripts/adjudicate.py         # costs money
uv run --with openpyxl   python scripts/generate_spreadsheet.py
```

Re-filtering an existing result set only ever *removes* candidates. A full
LLM re-run is needed only to find genuinely new ones.

---

## Notes worth knowing before editing

- **Reviewable tables, not buried logic.** `generate_asciidoc.py`
  (`MANUAL_MATCHES`, `ARGUABLE_MATCHES`, `EXPLICIT_DOMAINS`),
  `build_canonical_list.py` (`MERGES`, `DROPS`, `FLAGS`) and
  `authoring_table.py` each hold their judgement calls as data so a reviewer
  can challenge one row without reading the code.
- **Read `INCLUSION_CRITERIA.md` itself** before adjudicating anything.
  Working from a summary has produced wrong rule citations here before.
- **Locate spec text by excerpt, never by file name.** Chapter files get
  renamed between manual revisions (`counters.adoc` split into
  `zihpm`/`zicntr`, `rnmi.adoc` became `smrnmi.adoc`).
- **`modules/` duplicates `src/` byte-for-byte** in the manual. Read `src/`
  recursively and skip `modules/`, or everything counts twice.
- **A normative tag can carry more than one rule**, and rules name behaviours
  under `names` as well as `name`. Index tags to a list and read both keys;
  doing otherwise silently drops real matches.

The full trap list for each workstream is in that workstream's own README.
