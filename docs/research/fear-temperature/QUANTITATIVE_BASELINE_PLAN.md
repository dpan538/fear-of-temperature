# Quantitative Baseline v0.1 — Implementation Plan

## Inputs located

- `Fear of Temperature_ Historical Lexical Discovery and Anchor Validation.pdf`
- `Fear of Temperature_ Stratified Lexical Expansion, Voice Mapping, and Semantic-Relational Pre-Valida.pdf`
- `Fear of Temperature — Deep Research Round Two_ Historical Semantic Validation, Cross-Voice Relationa.pdf`
- Four supporting conceptual, database, feasibility, and communication reports

No original workbook, Priority CSV, Expansion table, source registry, or machine-readable artifact bundle was present. The reports refer to a structured bundle, but its embedded temporary download target is unavailable. The project therefore uses newly assigned stable IDs and `RECONSTRUCTED_FROM_REPORT` provenance throughout.

## Implementation choices

- Database: PostgreSQL relational schema and SQL seeds; JSONB only for raw/irregular collector metadata.
- Seed ledger: deterministic extraction of 180 initial, 180 Priority, and 36 Expansion report rows.
- Query inventory: 143 newly identified, anchor-specific provisional rules reconstructed from report-visible Priority terms and the methodological contract; unsupported rules remain in the audit export. The live July-2024 Ngram interface documentation permits up to seven ordinary words per query.
- Frequency source: public Google Books Ngram JSON interface, with corpus and maximum year verified at run time; annual unsmoothed observations are cached and checkpointed.
- Analysis: Python standard library plus Matplotlib/Pillow where available; CSV remains the canonical analysis output.
- Workbook: a formula-linked supervisor workbook built from the canonical exports.

## Expected outputs

- Schema and seeds: `db/migrations/`, `db/seeds/`
- Provenance ledger and query audit: `data/fear-temperature/seed/`
- Ngram cache, observations, and summaries: `data/fear-temperature/ngram/`, `data/fear-temperature/analysis/`, `data/fear-temperature/exports/`
- Figures: `figures/fear-temperature/`
- Presentation narrative: `docs/research/fear-temperature/PRESENTATION_SNAPSHOT.md`
- Supervisor workbook: `outputs/quantitative-v01/`

## Network/runtime limits

Ngram access depends on the live public endpoint and may be rate-limited. Individual failures are retried, recorded, and do not abort the run. PostgreSQL migrations are applied to an isolated temporary cluster when the local server binaries permit it; the SQL artifacts remain reproducible if runtime access is unavailable.
