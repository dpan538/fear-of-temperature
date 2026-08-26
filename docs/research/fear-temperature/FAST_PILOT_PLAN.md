# Fast Pilot Plan

- Sources found: three mandatory narrative research reports plus four supporting reports in the repository root.
- Structured artifacts: original workbook/CSV/JSON bundle not found; report-visible records are reconstructed with new stable IDs and `RECONSTRUCTED_FROM_REPORT` provenance.
- Database: PostgreSQL 16 relational schema, SQL seeds, and isolated-cluster integrity validation.
- Analysis stack: Python standard library, `pdfplumber` for source-table extraction, Pillow for figures, and `@oai/artifact-tool` for the supervisor workbook.
- Ngram approach: verify the live public English interface, cache raw JSON, request unsmoothed annual values, retain zero/failure/not-run outcomes, and calculate descriptive anchor statistics without causal inference.
- Outputs: `data/fear-temperature/`, `figures/fear-temperature/`, `docs/research/fear-temperature/`, and `outputs/quantitative-v01/`.
- Network: live retrieval depends on the public Google Books endpoint; the completed cache permits deterministic `--reuse-raw` analysis without new requests.

The implementation proceeded directly to quantitative outputs; the more detailed current plan is in `QUANTITATIVE_BASELINE_PLAN.md`.
