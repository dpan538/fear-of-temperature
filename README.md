# Fear of temperature

**Fear of temperature: Computational analysis of policy, media and public climate emotions**
is a computational social science and climate communication project. It investigates how
warming-related attention, fear, worry, anticipated harm, causal explanation, blame and
response duties are expressed across policy, news media and public discourse.

This repository contains the project's reproducible Python/NLP research infrastructure and a
fully executed synthetic demonstration. It does not yet contain the final research corpus or
report empirical thesis findings.

## Project context

Rising temperature is simultaneously a physical process, a policy problem and an object of
social anticipation. A heatwave warning, anxiety about children's futures, a newspaper's risk
frame and a government duty statement may concern the same climate issue while expressing
different emotions, time horizons and responsibilities.

The project therefore treats discourse roles and attribution explicitly:

- **policy/government**, **news media** and **public expression** are the primary comparison
  roles;
- scientific material is retained as a source subtype, not treated as an interchangeable
  fourth public agenda;
- publisher, quoted speaker and emotion holder remain separate;
- direct heat danger and longer-term warming concern are collected together but labelled
  separately;
- textual emotion is not interpreted as population prevalence or a mental-health diagnosis.

The core planned corpus covers English-language material associated with the United States,
European settings, Australia and New Zealand, with a target collection window of 1988–2026.
Recoverable material from 1938 onward may provide historical context, but statistical
comparisons will use only sufficiently dense common coverage windows.

## Research questions

1. **Temporal ordering:** when do policy, media and public climate attention or emotion lead,
   lag, move together or appear to feed back on one another?
2. **Emotional meaning:** how do fear, worry and anticipated harm vary by target, holder,
   horizon, quotation scope, negation, source role and period?
3. **Explanation and responsibility:** how are warming-related causes, threatened outcomes,
   blame and response duties attributed, and how do those narratives change around physical,
   institutional or communication events?

Channel and source transitions are analysed as possible composition changes. A discontinuity
after a platform, archive or coverage change is a bias warning, not by itself a causal effect.

## Contributions

### Intended research contribution

- A source-role-aware account of how climate emotions and responsibility narratives develop
  across policy, media and public discourse.
- A longitudinal comparison of attention, emotion and framing that states temporal and causal
  limits instead of treating correlation, prediction or discontinuity as proof of influence.
- Contextual evidence for distinguishing future-oriented concern from immediate bodily heat
  danger, and discourse expression from population mental health.

These are research objectives, not completed findings. They depend on corpus access,
permission review, human annotation, model evaluation and adequate temporal coverage.

### Implemented methodological and engineering contribution

- An auditable ingestion and provenance model linking raw records, sources, documents,
  canonical passages and exact-duplicate lineage.
- A modular NLP workflow joining lexical/TF-IDF baselines, semantic retrieval, emotion
  candidates, relation candidates and diachronic topic candidates without claiming a new
  model architecture.
- Explicit measurement denominators: attention `S`, emotion conditional on relevant text
  `E`, and joint share `B = S × E`, with observed zero distinguished from missing coverage.
- Reproducible temporal diagnostics for CCF, conditional small VAR, segmented regression/ITS
  and fixed-source channel-transition checks.
- A locked Python environment, model revision register, device/fallback reporting, executable
  notebooks, tests and machine-readable output manifests.

## What the repository contains

| Layer | Contents | Current status |
|---|---|---|
| Ingestion | CSV, JSONL and Parquet readers; normalisation, dates, stable IDs and exact deduplication | Implemented and tested |
| Evidence storage | Source/document/passage/lineage tables, DuckDB and Parquet exports | Implemented locally; PostgreSQL route preserved |
| Relevance | TF-IDF and pinned Sentence-Transformer retrieval on identical passages | Executed on synthetic fixtures |
| Emotion | Interpretable cues plus a pinned GoEmotions RoBERTa transfer candidate | Implemented candidate; climate validity not yet established |
| Relations | spaCy dependency/entity rules with actor, predicate, object and scope fields | Implemented baseline; explicitly not SRL |
| Topics | BERTopic interface using shared sentence embeddings and deterministic clustering | Implemented interface; stability validation remains planned |
| Measurement | Role/time aggregation with `S`, `E`, `B`, denominators and coverage states | Implemented and unit tested |
| Temporal analysis | Synthetic CCF, ITS, conditional VAR and channel-transition diagnostics | Implemented interface; not empirical evidence |
| Outputs | DuckDB, Parquet/CSV, NumPy vectors, PNG/PDF/SVG and self-contained HTML | Generated by the verified demo |
| Research workspace | Jupyter notebooks, registered kernel, environment doctor, Pytest, Ruff and Mypy | Installed and validated on Apple Silicon |

The tracked fixture in [`data/fixtures/`](data/fixtures/) is invented test material. Its
expected fields are software checks, not historical evidence or human gold labels.

## Method overview

```text
source records
      ↓
normalisation + metadata + provenance + duplicate lineage
      ↓
relevance retrieval ── TF-IDF / sentence embeddings
      ↓
      ├── emotion and horizon candidates
      ├── event/relation candidates
      └── diachronic topic candidates
      ↓
role/time measures ── S attention / E conditional emotion / B joint share
      ↓
CCF / conditional VAR / ITS / channel-composition diagnostics
      ↓
traceable tables, figures and contextual interpretation
```

Detailed module boundaries are documented in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Technical stack

| Area | Technologies |
|---|---|
| Runtime and reproducibility | Python 3.12, uv, `pyproject.toml`, `uv.lock`, dotenv, YAML |
| Data processing | pandas, NumPy, PyArrow, SciPy |
| Storage | DuckDB and Parquet for the service-free workspace; preserved PostgreSQL migrations for the production route |
| Retrieval and NLP | scikit-learn TF-IDF, PyTorch, Transformers, Sentence-Transformers, spaCy, GoEmotions candidate, BERTopic |
| Statistical analysis | statsmodels, cross-correlation, segmented regression/ITS and conditional VAR |
| Visualisation | Matplotlib, Seaborn and Plotly |
| Research workflow | JupyterLab, ipykernel and nbformat/nbconvert |
| Quality controls | Pytest, Ruff, Mypy, deterministic seeds, model/output manifests and SHA-256 records |

Exact dependency versions are locked in [`uv.lock`](uv.lock). Model IDs, revisions, licences,
cache behaviour and interpretation limits are recorded in
[`docs/DATA_MODELS_AND_GOVERNANCE.md`](docs/DATA_MODELS_AND_GOVERNANCE.md).

## Current status and evidence boundary

The synthetic end-to-end run has verified real model download/inference, Apple MPS execution,
cleaning, provenance storage, embeddings, retrieval, emotion/relation/topic candidates,
aggregation, temporal diagnostics and figure export. The current acceptance record includes
10 unit/data-contract tests and the preserved legacy validator's 11 checks and 21 figures.

The repository does **not** currently claim:

- a completed historical, policy, media or platform corpus;
- empirical changes in public or institutional emotion;
- a validated climate-anxiety classifier;
- production semantic role labelling;
- stable historical topics or causal influence among discourse roles;
- a novel neural architecture.

See [`docs/WORKSPACE_VALIDATION.md`](docs/WORKSPACE_VALIDATION.md) for executed checks and
remaining research gates.

## Data and research governance

Public visibility is not blanket permission to collect, quote, infer from or redistribute
source material. Restricted originals, identifiers, text, features and embeddings require
source-specific permission and release review. Human annotation and later evaluation remain
subject to the project's supervisory and UQ ethics process.

The authoritative proposal is maintained in the local `proposal/` working tree. It is
reviewed separately for publication because it also contains private course material,
historical drafts and generated runtimes. This public snapshot applies no blanket licence to
the repository and asserts no licence over third-party corpora.

## Reproducibility

The complete verified environment can be rebuilt from a fresh clone with:

```bash
./scripts/bootstrap.sh
```

The two supplied notebooks separate environment verification from the synthetic end-to-end
demonstration:

1. [`notebooks/01_workspace_check.ipynb`](notebooks/01_workspace_check.ipynb)
2. [`notebooks/02_synthetic_end_to_end.ipynb`](notebooks/02_synthetic_end_to_end.ipynb)

The same workflows can be executed non-interactively:

```bash
.venv/bin/fear-temperature-doctor --full-models
.venv/bin/fear-temperature-demo --offline
.venv/bin/pytest
./scripts/run_notebooks.sh
```

Generated model/device manifests, tables, vectors, databases, notebook execution copies and
figures are written under ignored `outputs/demo/`.

## Repository structure

```text
src/fear_temperature/  installable ingestion, NLP, temporal and visualisation package
configs/               run and pinned-model configuration
notebooks/             environment check and synthetic end-to-end demonstration
scripts/               bootstrap, model, kernel, notebook and legacy entry points
tests/                 data-contract and temporal-analysis tests
data/fixtures/         tracked synthetic inputs only
data/raw/              ignored local source material
outputs/demo/          ignored, reproducible demonstration artefacts
db/                    preserved PostgreSQL migrations, seeds and validations
docs/                  architecture, environment, governance, migration and validation records
.vscode/               optional editor tasks, tests and debug configuration
```

The migration and protection inventory is in
[`docs/MIGRATION_INVENTORY.md`](docs/MIGRATION_INVENTORY.md).

## Legacy baseline

The earlier 1842–2022 lexical and Google Books Ngram work remains a preserved provisional
baseline under `scripts/fear-temperature/`, `data/fear-temperature/`, `db/`,
`figures/fear-temperature/` and `outputs/quantitative-v01/`. It provides historical
background and a comparison baseline; it is not the current thesis scope or a gold semantic
corpus.

```bash
.venv/bin/python scripts/fear-temperature/validate_quantitative_baseline.py
```

The current run passes 11 checks and confirms 21 legacy figures. See
[`docs/research/fear-temperature/VALIDATION_REPORT.md`](docs/research/fear-temperature/VALIDATION_REPORT.md).
