# Python/NLP workspace validation

Validation date: 16 September 2026. Host: Apple M1 MacBook Pro, 16 GB memory, macOS 26.5.2 (arm64). Free disk before installation was approximately 44 GiB.

## Environment

- Python 3.12.13 in root `.venv`
- uv-managed Python 3.12.14 cached under the project for future clean rebuilds
- uv 0.12.13
- lock: 208 resolved packages; full profile: 189 installed packages
- selected core versions: PyTorch 2.14.0, Transformers 4.57.6, Sentence-Transformers 5.7.0, spaCy 3.8.16, `en_core_web_sm` 3.8.0, BERTopic 0.17.4, pandas 2.3.3, PyArrow 23.0.1, DuckDB 1.5.5, scikit-learn 1.9.1, statsmodels 0.15.0, JupyterLab 4.6.3
- `.venv`: approximately 1.7 GB; project cache after dependencies/models: approximately 2.5 GB

## Acceptance results

| Check | Result | Evidence |
|---|---|---|
| Lock and full installation | PASS | `uv sync --locked --all-extras --group dev` completed |
| One-command bootstrap | PASS | dependency sync, fixed model snapshots, kernel registration, offline demo and full doctor completed with exit code 0 |
| Independent clean rebuild | PASS | offline locked sync to `/private/tmp/fear-temperature-clean-venv`, 189 packages |
| Editable import outside repository | PASS | imported version 0.2.0 from `/private/tmp` using the clean environment |
| Unit/data-contract tests | PASS | 10 tests; duplicate lineage, missing/zero, S/E/B, lag direction, chronological holdout, schema and reproducibility |
| Ruff | PASS | package, model script and tests |
| Model download and inference | PASS | fixed sentence/emotion revisions plus spaCy model; remote custom code disabled |
| Apple MPS | PASS | backend built/available, real tensor probe, both Transformer models inferred on MPS without fallback |
| Synthetic end-to-end demo | PASS | completed offline with real cached models |
| DuckDB/Parquet storage | PASS | source/document/passage/lineage plus 13 analysis tables |
| Vector persistence | PASS | 36 × 384 float32 embedding array plus passage IDs/model metadata |
| Static and interactive figures | PASS | PNG, PDF, SVG and self-contained HTML; PNG visually inspected |
| Registered Jupyter kernel | PASS | `fear-of-temperature`, display `Python (Fear of Temperature)`, `argv[0]` points to root `.venv` |
| Notebook 01 | PASS | non-interactive execution; kernel process reported root `.venv/bin/python`, Python 3.12.13 and MPS |
| Notebook 02 | PASS | full offline pipeline executed from the registered kernel |
| VS Code extensions | PASS | Python/Jupyter/Pylance already present; Ruff 2026.80.0 installed |
| Legacy quantitative validator | PASS | 11 checks and 21 existing figures |

The local ipykernel emitted its general warning that a local TCP kernel connection was not encrypted. The process remained local, used the correct registered interpreter, and completed; no remote Jupyter server was configured.

## Demo outputs

- Input: 37 invented JSONL rows
- Canonical passages after exact deduplication: 36
- Preserved exact-duplicate lineage rows: 1
- Relation candidates: 29, all labelled `spacy_dependency_rule_baseline_not_srl`
- BERTopic assignments: 28 relevant synthetic passages across 3 deterministic demo topics
- TF-IDF and Sentence-Transformer top-10 results: both interfaces completed against identical texts
- Synthetic temporal series: 96 monthly observations
- VAR: chronological split at index 72; own-history and conditional models evaluated only on held-out observations
- Channel diagnostic: aggregate series shows the injected composition shift while the fixed-source series does not show the same level jump; this is a software check, not causal evidence

The detailed generated manifest with hashes is `outputs/demo/manifest.json` (ignored and reproducible). The executed notebooks are under `outputs/demo/notebooks/`.

## Honest limitations and next gates

- No historical/policy/media/platform corpus was collected by this rebuild.
- Synthetic expected labels are not human gold labels; retrieval counts are not empirical precision/recall estimates.
- GoEmotions is only an unvalidated transfer candidate.
- The implemented relation extractor is a dependency/entity rule baseline, not SRL.
- BERTopic, CCF, ITS and VAR outputs validate interfaces on synthetic data only.
- Existing PostgreSQL migrations were not applied to or tested against a user database; local DuckDB was selected to avoid state changes.
- Data access, annotation, human evaluation, ethics determination, permissions and publication remain governed by the proposal and supervisor/UQ process.
