# Fear of temperature

**Fear of temperature: Computational analysis of policy, media and public climate emotions** is a computational social science / climate communication thesis project. It studies how warming-related attention, fear, worry, anticipated harm, causes, blame and response duties are expressed across policy, news media and public discourse.

The current repository provides a reproducible Python/NLP research workspace and a fully executed synthetic demonstration. It does **not** yet report thesis findings, validate population mental-health claims, establish a new model architecture, or treat cultural heritage as a core conclusion.

**第一次在 VS Code 中使用？请从 [`00_START_HERE.md`](00_START_HERE.md) 开始。**

The authoritative proposal is maintained in the local `proposal/` tree. Because that pre-existing tree also contains private working material and generated runtimes, it is not included in this public workspace snapshot. The implemented boundary is recorded in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/WORKSPACE_VALIDATION.md`](docs/WORKSPACE_VALIDATION.md).

## Research scope

- Core language and regions: English-language material associated with the United States, European settings, Australia and New Zealand. Chinese and additional regions remain extension candidates.
- Target collection period: 1988–2026. Recoverable material from 1938 onward may provide historical context; statistical comparisons use only sufficiently dense common coverage.
- Primary discourse roles: government/policy, news media and public expression. Scientific material remains a source subtype rather than a fourth interchangeable denominator.
- Attribution is explicit: publisher, quoted speaker and emotion holder are separate fields. A scientist quoted by a newspaper and a resident quoted by a journalist are not recoded as the publisher's own emotion.
- Direct heat danger and longer-term warming concern are collected together but labelled separately by emotion, target, holder, horizon, quotation scope and negation.
- Required NLP directions: event/relation candidates, aspect-specific emotion candidates, and diachronic topic/semantic analysis. Relevance retrieval is their shared entry point.

The main temporal questions concern leading, lagging, synchrony and possible feedback among the three roles. CCF, conditional small VAR and segmented regression/ITS are bounded diagnostics: prediction or a discontinuity is not causal proof.

## Implemented now

- An installable `src/fear_temperature` package with shared configuration and deterministic seeds.
- CSV, JSONL and Parquet input; Unicode/whitespace normalisation; deterministic IDs; exact deduplication; raw-to-derived lineage.
- Local DuckDB plus Parquet storage for sources, documents, passages, lineage and analysis tables. Existing PostgreSQL migrations remain untouched and available for the production route.
- TF-IDF retrieval and a real pinned Sentence-Transformer comparison, with persistent 384-dimensional vectors and model metadata.
- A pinned GoEmotions RoBERTa candidate plus interpretable emotion/horizon/negation cues. GoEmotions `nervousness` is explicitly **not** treated as climate anxiety.
- spaCy NER/dependency relation candidates labelled as a rule baseline, not SRL.
- A real BERTopic interface check using the shared sentence embeddings and deterministic K-means clustering.
- Role/time aggregation with separate attention `S`, conditional emotion `E`, derived joint share `B = S × E`, coverage counts, and distinct missing versus observed-zero states.
- Reproducible synthetic CCF, ITS, conditional VAR and channel-transition diagnostics, including a fixed-source comparison.
- PNG, PDF, SVG and self-contained interactive HTML exports.
- Pytest, Ruff, an environment doctor, registered Jupyter kernel, executable notebooks and VS Code tasks/debug settings.

The fixture under [`data/fixtures/`](data/fixtures/) is invented test text. Its expected fields are neither historical evidence nor human gold labels.

## Quick start: fresh clone to VS Code

Prerequisites are macOS or Linux, [uv](https://docs.astral.sh/uv/) and VS Code. This workspace is pinned to Python 3.12. The bootstrap installs the full research profile, downloads the three configured public model artefacts, registers the kernel, runs the offline synthetic demo, and finishes with the full doctor.

```bash
cd fear_of_temperature
./scripts/bootstrap.sh
code .
```

On first open, accept VS Code workspace trust if you trust this repository. The interpreter is configured as `.venv/bin/python`. For a notebook, select **Python (Fear of Temperature)** if VS Code does not select it automatically; workspace settings cannot bypass the trust or kernel-confirmation UI.

Run the verified workflow from the terminal or the matching VS Code tasks:

```bash
.venv/bin/fear-temperature-doctor --full-models
.venv/bin/pytest
.venv/bin/fear-temperature-demo --offline
./scripts/run_notebooks.sh
```

The main notebooks are:

1. [`notebooks/01_workspace_check.ipynb`](notebooks/01_workspace_check.ipynb)
2. [`notebooks/02_synthetic_end_to_end.ipynb`](notebooks/02_synthetic_end_to_end.ipynb)

Executed copies, model/device manifests, DuckDB/Parquet tables, vectors and figures are written to `outputs/demo/` and are intentionally not tracked.

## Environment and reproducibility

`pyproject.toml` is the single dependency declaration and `uv.lock` is the exact cross-platform lock. `requirements.txt` is only a compatibility entry point for old `pip install -r requirements.txt` commands; it delegates to the `legacy` extra in `pyproject.toml`.

```bash
# Recreate exactly from the checked-in lock
UV_CACHE_DIR="$PWD/.cache/uv" uv sync --locked --all-extras --group dev --python 3.12

# Update intentionally, then review uv.lock
UV_CACHE_DIR="$PWD/.cache/uv" uv lock --upgrade
```

Local non-secret defaults live in ignored `.env`; the tracked template is [`.env.example`](.env.example). Paths, model cache, seed, device and optional database URL are shared by scripts and notebooks. No API key is supplied or expected by the synthetic demo.

See [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) for kernel maintenance, first-download/offline use, CPU/MPS selection and troubleshooting. Model IDs, exact revisions, licences and measured cache size are documented in [`docs/DATA_MODELS_AND_GOVERNANCE.md`](docs/DATA_MODELS_AND_GOVERNANCE.md).

## Project layout

```text
src/fear_temperature/  installable ingestion, NLP, temporal and visualisation code
configs/               model and run configuration
notebooks/             numbered, kernel-bound research notebooks
scripts/               bootstrap, model, kernel, notebook and legacy entry points
tests/                 data-contract and temporal-analysis tests
data/fixtures/         tracked synthetic inputs only
data/raw|interim|processed|exports/
                       local research data stages; raw/interim outputs are ignored
outputs/demo/          regenerable demo artefacts and manifests; ignored
db/                    preserved PostgreSQL migrations, seeds and validations
proposal/              local authoritative proposal and working records; publication reviewed separately
docs/                  environment, architecture, migration and validation records
.vscode/               portable interpreter, test, task and debug configuration
```

The incremental migration and protection inventory is in [`docs/MIGRATION_INVENTORY.md`](docs/MIGRATION_INVENTORY.md). No existing data, old script, database migration, proposal file, figure or uncommitted user artefact was moved or deleted.

## Planned research work

The next phase is the access- and ethics-governed pilot described by the proposal. It will verify source permissions and common windows; freeze source roles, denominators and sampling weights; create role/period-stratified human-reviewed labels; evaluate retrieval and the three NLP components; and only then fit real temporal/event models. Production SRL/contextual relation extraction, topic stability analysis and climate-specific emotion validation remain planned, not claimed as completed here.

Restricted originals, quotations, identifiers, features and embeddings require source-specific permission and release review. Public visibility is not blanket consent. Only permitted data and derivatives may be published. The repository currently assigns no blanket open-source licence to the code and no licence to third-party corpora.

## Legacy baseline

The earlier 1842–2022 lexical/Google Books Ngram work remains a preserved, provisional baseline under `scripts/fear-temperature/`, `data/fear-temperature/`, `db/`, `figures/fear-temperature/` and `outputs/quantitative-v01/`. It is background and a comparison baseline, not the current thesis scope or a gold semantic corpus.

Validate it without writing raw data:

```bash
.venv/bin/python scripts/fear-temperature/validate_quantitative_baseline.py
```

The current run passes 11 checks and confirms 21 legacy figures. See [`docs/research/fear-temperature/VALIDATION_REPORT.md`](docs/research/fear-temperature/VALIDATION_REPORT.md).

## Repository metadata

GitHub description:

> Computational study of warming-related fear and anxiety across policy, news media and public discourse, using a reproducible NLP pipeline and temporal analysis.

Suggested topics: `computational-social-science`, `climate-communication`, `nlp`, `climate-emotions`, `sentence-transformers`, `bertopic`, `time-series`, `jupyter`, `duckdb`, `postgresql`, `research-data`, `data-provenance`.
