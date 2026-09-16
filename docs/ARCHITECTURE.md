# NLP workspace architecture

## Execution flow

```text
CSV / JSONL / Parquet
        ↓
normalise + validate + deterministic IDs + duplicate lineage
        ↓
sources / documents / passages / lineage
        ↓
DuckDB + Parquet evidence store
        ↓
TF-IDF ───────────────┐
Sentence embeddings ─┼─ relevance comparison + persistent vectors
                     │
                     ├─ GoEmotions + interpretable emotion cues
                     ├─ spaCy dependency/entity relation baseline
                     └─ BERTopic candidate topics
        ↓
role/time aggregation: S attention, E conditional emotion, B = S × E
        ↓
CCF / conditional VAR / ITS / channel-transition diagnostic
        ↓
Parquet/CSV tables + DuckDB tables + PNG/PDF/SVG/HTML + manifest
```

Terminal scripts and notebooks import the same installed `fear_temperature` package. They do not patch `sys.path`.

## Module responsibilities

| Module | Responsibility | Boundary |
|---|---|---|
| `config` | project-root paths, `.env`, YAML, seeds, CPU/MPS probe | no fabricated credentials or remote services |
| `io` | CSV/JSONL/Parquet readers and JSON manifests | explicit supported formats |
| `cleaning` | conservative text normalisation, validation, stable IDs, exact deduplication and lineage | raw text hash remains auditable |
| `corpus` | DuckDB/Parquet source, document, passage and analysis tables | does not touch existing PostgreSQL databases |
| `embeddings` | pinned Sentence-Transformer load, MPS fallback, vector persistence | relevance representation, not an emotion measure |
| `retrieval` | TF-IDF and semantic ranking on identical texts | synthetic diagnostics are not empirical precision claims |
| `emotions` | lexical/horizon/negation rules and GoEmotions probabilities | unvalidated transfer candidate; no clinical inference |
| `relations` | dependency/entity candidate relations with spans and scope fields | explicitly not SRL or culpability inference |
| `topics` | BERTopic interface using shared embeddings and deterministic clustering | synthetic topics are not thesis findings |
| `temporal` | S/E/B, coverage, CCF, ITS, VAR and channel diagnostics | prediction/discontinuity is not causality |
| `visualization` | static and self-contained interactive exports | synthetic label always visible |
| `pipeline` | reproducible end-to-end orchestration and manifest | default demo uses only synthetic fixture data |
| `doctor` | Python, imports, paths, MPS, parser, models, kernel and demo status | failures are non-zero and individually reported |

## Provenance model

Each imported row receives a `raw_id`; source and external ID determine `document_id`; normalised text determines the canonical `passage_id`. Exact duplicates retain distinct lineage rows pointing to one canonical passage. The demo evidence view joins raw lineage to canonical text, its document and source. Generated files receive SHA-256 values in `outputs/demo/manifest.json`.

The production corpus will require additional source-specific fields, permissions, versions and restricted storage, but the demo does not invent those access decisions.

## Denominators and missingness

For a source role and time bin:

- `S = relevant weighted units / eligible weighted units`;
- `E = future-worry weighted units / relevant weighted units`;
- `B = future-worry weighted units / eligible weighted units = S × E`.

No eligible units means missing `S/E/B`. Eligible units with zero relevant units means `S=0`, `B=0`, and `E` missing because its denominator is zero. Tests assert these distinctions and the identity only where `E` is defined.

## Production versus demo storage

DuckDB is the verified local, service-free demonstration store. Existing PostgreSQL migrations, seeds and validations under `db/` remain the production lineage and were not rebuilt, cleared or applied to an existing instance. A future adapter can map the package tables to a new versioned PostgreSQL schema after source and permissions review.
