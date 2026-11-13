# Current Research Architecture — 13 November 2026

The current frame is Australian **2003–2025** text, with completed acquisition, preserved raw/identity/version layers and separately derived preprocessing. The prospective route is structural text views → work/version/thread/context grouping → frozen parent splits → train-only learned transformations → model-compatible chunks → validated affect/Fear measurement → longitudinal and event analysis. The old numerical-inventory-first question order is superseded; see [current RQs](research/2026-11-13-corpus-release/RESEARCH_QUESTIONS.md) and [next-stage design](research/2026-11-13-corpus-release/NEXT_STEPS.md). Infrastructure and historical stage descriptions below are not completed empirical findings.

---

# NLP workspace architecture

Current research priorities and acquisition stopping rules are set by
[PROJECT_DIRECTION.md](PROJECT_DIRECTION.md). This document inventories implemented
infrastructure; available modules do not establish additional compulsory research tasks.

## Current planned research flow, updated 21 October 2026

**21 October closeout:** Official Voice acquisition is closed by Dai. All 9 executable routes
are exhausted; 8 named routes remain pending, with `all_sources_complete:false` unchanged.
The full official 1988-01-01–2026-09-21 inventory and frozen evidence remain preserved.
Dai selects approximately **2003–2024/2025** as the priority dense-collection window for Australian
Social Media and Personal Discourse, with 1988–2002 as historical/background reference.
The exact endpoint awaits a separately instructed new window; this decision launches no collector,
new chat, corpus cleaning, model or migration. See the
[scope decision](research/2026-10-20-australia-official-voice/CLOSEOUT_SCOPE_DECISION.json).
Observed official counts/reference events do not establish statistical power, causal exogeneity,
complete social coverage or an event match for every proposed window.

**20 October amendment, official-voice workstream:** the search-led event pipeline is retired.
The [replacement](research/2026-10-20-australia-official-voice/README.md) uses documented public
source interfaces or frozen ready-made Hansard exports, the four-dimensional query matrix,
and two research tables: `source_documents` and `event_claims`. Only compact metadata and
at most 500-character excerpts persist; complete original bodies are transient. PostgreSQL DDL
and JSON validation accompany a local SQLite acquisition store, without production warehouse
migration. Operational page/cursor receipts are separate from the two research tables. Claims
default to draft, missing/coarse dates remain explicit, and a source-native record count does
not imply independently authored speech or institutional endorsement. Dai removed the fixed
15 GiB floor for this task; actual-operation capacity checks remain. The text stream is unchanged.

## Implemented demonstration flow

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
