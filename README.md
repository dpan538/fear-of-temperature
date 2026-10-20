# Fear of temperature

### Computational analysis of policy, media and public climate emotions

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Status: corpus acquisition](https://img.shields.io/badge/status-corpus%20acquisition-2ea44f)](docs/PROJECT_LOG.md)
![Platform: macOS Apple Silicon](https://img.shields.io/badge/validated-macOS%20Apple%20Silicon-555555?logo=apple)
![License: not yet assigned](https://img.shields.io/badge/license-not%20yet%20assigned-lightgrey)

## 30-second overview

**Latest government/institutional status, 21 October:** [Official Voice](docs/research/2026-10-20-australia-official-voice/README.md)
acquisition is **closed by Dai**. Nine available routes are exhausted; eight named routes remain
pending, so full-registry completeness remains false. Preserve the metadata/excerpt inventory,
frozen reports and 1988-01-01–2026-09-21 official reference interval. See the
[closeout and selected scope](docs/research/2026-10-20-australia-official-voice/CLOSEOUT_SCOPE_DECISION.json).

**Selected next collection scope:** approximately **2003–2024/2025** for dense Australian social
media and personal discourse; retain **1988–2002** as historical/background reference. The exact
endpoint awaits Dai's separate instructions in a new window. This is a research priority, not proof
of exponential discourse growth, statistical power, exogenous stimuli or complete social coverage.
No new acquisition or automatic official follow-up is launched by this closeout.

**Current stage:** the completed official inventory provides descriptive source/time context for the next Australian public-expression collection. Native social posts, forum discussion, reader comments and personal/community blogs remain distinct from editorial news. The next task and exact endpoint await the user's separate instructions; this closeout does not launch collection or models.

| Question | Answer |
|---|---|
| **What is this?** | A computational social science project studying how warming-related attention, fear, worry, harm, blame and response duties appear across policy, news media and public discourse. |
| **What works now?** | A reproducible Python/NLP workspace, real local model inference, provenance-aware ingestion, retrieval, candidate emotion/relation/topic analysis, temporal diagnostics, notebooks, tests and exportable figures. |
| **Can I use it?** | Yes, for the verified synthetic demonstration and as research infrastructure. It does not yet contain the final corpus or empirical thesis findings. |
| **What should I run first?** | `./scripts/bootstrap.sh`, then `.venv/bin/fear-temperature-doctor --full-models`. |
| **Where are the results?** | Real acquisition evidence is in `work_packages/M1_source_access/` and [`docs/PROJECT_LOG.md`](docs/PROJECT_LOG.md); the synthetic demo and its validation remain separately documented. |

## Contents

- [Quickstart](#quickstart)
- [Project context and research questions](#project-context-and-research-questions)
- [Contributions](#contributions)
- [What is included](#what-is-included)
- [Terminology](#terminology)
- [Technical stack](#technical-stack)
- [Documentation](#documentation)
- [Status and research boundaries](#status-and-research-boundaries)
- [Citation](#citation)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Quickstart

### Requirements

- Python 3.12, managed by [uv](https://docs.astral.sh/uv/)
- macOS or Linux
- network access for the first model download

The complete workflow was validated on macOS 26.5.2, Apple M1, using Python 3.12.13,
uv 0.12.13 and PyTorch MPS. The lock is also configured for Linux x86_64, but this rebuild
did not claim a hardware-level Linux validation. CPU fallback is supported; no CUDA-specific
build is installed by default.

```bash
git clone https://github.com/dpan538/fear-of-temperature.git
cd fear-of-temperature

# Create the locked environment, download fixed model snapshots,
# register the kernel, run the demo and finish with the full doctor.
./scripts/bootstrap.sh

# Re-run individual acceptance commands.
.venv/bin/fear-temperature-doctor --full-models
.venv/bin/fear-temperature-demo --offline
.venv/bin/pytest
```

The demo writes DuckDB/Parquet tables, embeddings, retrieval artefacts, figures and a manifest
to `outputs/demo/`. The main notebooks are
[`01_workspace_check.ipynb`](notebooks/01_workspace_check.ipynb) and
[`02_synthetic_end_to_end.ipynb`](notebooks/02_synthetic_end_to_end.ipynb).

## Project context and research questions

The empirical scope is Australian institutions, media and sources with evidenced Australian
public/community context, within the fixed 1988-01-01–2026-09-21 publication interval.
International holdings and the submitted proposal retain their historical scope.

The current operational design for RQ1/RQ2 uses events/checkpoints grounded in dated data,
statements or reporting to define periods and compare social-data activity distributions before
and after events. Government original articles provide event/context evidence. Social datasets
provide the main analysis material, with text paragraphs converted to vectors for analysis and
prediction. Paragraph counts and native post/activity counts remain distinct.

The exact question wording, activity unit, period boundaries, vector algorithm, prediction target
and horizon still need specification. The phrase paragraph-to-vector does not select the literal
Word2Vec algorithm. RQ3 remains a later return to traceable passages to interpret fear, its
targets and attributed causes. Available experimental modules do not add compulsory tasks,
and before/after associations or successful prediction do not establish causal influence.

Publisher, quoted speaker and emotion holder remain separate; direct heat danger and
longer-term concern are separately labelled. Textual emotion is not a population diagnosis.

## Contributions

### Research objective

- A source-role-aware longitudinal account of climate emotions and responsibility narratives.
- A comparison of attention, emotion and framing with explicit temporal and causal limits.
- Contextual evidence distinguishing future-oriented concern, immediate heat danger and
  population-level psychological claims.

These are objectives, not completed findings; they require permission-reviewed corpora,
human annotation, model evaluation and adequate common coverage.

### Implemented contribution

- Traceable raw-to-derived provenance across sources, documents, passages and duplicates.
- Modular lexical/TF-IDF, embedding, emotion, relation and topic candidate workflows.
- Explicit measures for attention `S`, conditional emotion `E` and joint share
  `B = S × E`, including missing-versus-zero handling.
- Reproducible temporal diagnostics, locked dependencies, pinned models, device/fallback
  reporting, tests and machine-readable manifests.

## What is included

| Component | Implementation |
|---|---|
| Data and provenance | CSV/JSONL/Parquet input, normalisation, stable IDs, exact deduplication and lineage |
| Storage | Local DuckDB and Parquet; existing PostgreSQL migrations preserved for a production route |
| NLP | TF-IDF, Sentence-Transformers, GoEmotions candidate, spaCy dependency/entity baseline and BERTopic interface |
| Measurement | Role/time aggregation, denominators, coverage states and `S/E/B` outputs |
| Temporal analysis | Synthetic CCF, ITS, conditional VAR and fixed-source channel-transition checks |
| Outputs | CSV/Parquet, DuckDB, NumPy vectors, PNG/PDF/SVG and self-contained Plotly HTML |
| Reproducibility | uv lock, model register, Jupyter notebooks, environment doctor, Pytest, Ruff and Mypy |
| Legacy baseline | Preserved 1842–2022 lexical/Google Books Ngram workflow, 11 validation checks and 21 figures |

The tracked [synthetic fixture](data/fixtures/) is invented test material. Its expected fields
are software checks, not historical evidence or human gold labels.

## Terminology

| Term | Meaning in this project |
|---|---|
| **S** | Attention share: relevant weighted units divided by eligible weighted units |
| **E** | Conditional emotion share: future-worry units divided by relevant units |
| **B** | Joint share: future-worry units divided by eligible units; where defined, `B = S × E` |
| **CCF** | Cross-correlation function used as a lead/lag diagnostic after appropriate time-series processing |
| **ITS** | Interrupted time series / segmented regression used to estimate level or slope discontinuities |
| **VAR** | Vector autoregression used here as a small conditional predictive model, not causal proof |
| **SRL** | Semantic role labelling; planned for production relations, not claimed by the current spaCy rule baseline |
| **MPS** | Apple's Metal Performance Shaders backend used for verified local PyTorch inference |
| **Lineage** | The recorded link from each raw input row to its document and canonical passage |

## Technical stack

| Area | Technologies |
|---|---|
| Runtime and configuration | Python 3.12, uv, `pyproject.toml`, `uv.lock`, dotenv, YAML |
| Data processing | pandas, NumPy, PyArrow, SciPy |
| Storage | DuckDB, Parquet and preserved PostgreSQL migrations |
| Retrieval and NLP | scikit-learn, PyTorch, Transformers, Sentence-Transformers, spaCy, GoEmotions candidate, BERTopic |
| Statistical analysis | statsmodels, CCF, segmented regression/ITS and conditional VAR |
| Visualisation | Matplotlib, Seaborn and Plotly |
| Research workflow | JupyterLab, ipykernel and nbformat/nbconvert |
| Quality controls | Pytest, Ruff, Mypy, deterministic seeds, model/output manifests and SHA-256 records |

Exact versions are locked in [`uv.lock`](uv.lock). Model IDs, revisions, licences and
interpretation limits are recorded in
[`docs/DATA_MODELS_AND_GOVERNANCE.md`](docs/DATA_MODELS_AND_GOVERNANCE.md).

## Documentation

| Document | Purpose |
|---|---|
| [Current project direction](docs/PROJECT_DIRECTION.md) | Global temporal objective, gap-recovery priorities and stopping rules |
| [Project log](docs/PROJECT_LOG.md) | Real acquisition progress, decisions and remaining work |
| [Architecture](docs/ARCHITECTURE.md) | Pipeline, modules, provenance, denominators and storage boundaries |
| [Environment](docs/ENVIRONMENT.md) | Installation, model cache, CPU/MPS selection and troubleshooting |
| [Data, models and governance](docs/DATA_MODELS_AND_GOVERNANCE.md) | Model register, licences, data access and interpretation limits |
| [Workspace validation](docs/WORKSPACE_VALIDATION.md) | Executed acceptance checks, versions and known limitations |
| [Migration inventory](docs/MIGRATION_INVENTORY.md) | Protected pre-existing assets and additive rebuild record |
| [Legacy validation](docs/research/fear-temperature/VALIDATION_REPORT.md) | Validation of the preserved lexical/Ngram baseline |

## Status and research boundaries

The synthetic end-to-end workflow is operational and verified with real downloaded models.
It does **not** claim a completed research corpus, empirical emotion trends, a validated
climate-anxiety classifier, production SRL, stable historical topics, causal influence or a
novel neural architecture.

Public availability is not permission to collect or redistribute source material. Restricted
text, identifiers, features and embeddings require source-specific review; human annotation
remains subject to supervisory and UQ ethics processes. See
[`docs/DATA_MODELS_AND_GOVERNANCE.md`](docs/DATA_MODELS_AND_GOVERNANCE.md).

## Citation

No DOI or archival release has been assigned yet. Until one exists, cite the repository and
the specific commit used:

> Pan, D. (2026). *Fear of temperature: Computational analysis of policy, media and public
> climate emotions* [Computer software]. GitHub.
> https://github.com/dpan538/fear-of-temperature

```bibtex
@software{pan_fear_of_temperature_2026,
  author = {Pan, Dai},
  title = {Fear of temperature: Computational analysis of policy, media and public climate emotions},
  year = {2026},
  url = {https://github.com/dpan538/fear-of-temperature},
  note = {Research infrastructure; cite the specific commit used}
}
```

## Contributing

Contributions are reviewed case by case. Open an issue before a substantial code, data-source
or methodological change. Do not submit restricted text, personal data, credentials or
unlicensed corpora. Changes should preserve provenance and evidence boundaries and pass:

```bash
.venv/bin/ruff check src tests
.venv/bin/mypy src
.venv/bin/pytest
```

## License

No repository-wide open-source licence has been assigned. Do not assume permission to copy,
modify or redistribute the code or research materials. Third-party packages, models and data
remain governed by their own licences and terms. See the model register for recorded model
licences.

## Contact

Project owner: **Dai Pan** ([@dpan538](https://github.com/dpan538)).

Use [GitHub Issues](https://github.com/dpan538/fear-of-temperature/issues) for public code or
documentation questions. Do not post restricted data, credentials or sensitive access details
in a public issue.
