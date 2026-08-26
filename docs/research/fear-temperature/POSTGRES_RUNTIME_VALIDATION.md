# PostgreSQL Runtime Validation

Status: **PASS**

Server: PostgreSQL 16.13 (Homebrew)

Validation environment: isolated temporary cluster and disposable database, removed after the test

Applied in order:

1. `db/migrations/001_fear_temperature_fast_pilot.sql`
2. `db/seeds/001_reference_data.sql`
3. `db/seeds/002_provisional_lexicon.sql`
4. `db/seeds/003_quantitative_query_inventory.sql`
5. `db/seeds/004_ngram_quantitative.sql`
6. `db/validation/quantitative_v01_integrity.sql`

The final SQL assertions returned:

| PostgreSQL | Anchors | Seed records | Query rules | Annual observations | Bounded-search observations |
| --- | ---: | ---: | ---: | ---: | ---: |
| 16.13 | 6 | 396 | 143 | 23,892 | 0 |

The zero bounded-search observation count is intentional: no document-level corpus connector was run, so search quantity was not fabricated. The integrity script also verifies controlled-dimension counts, anchor containment, reconstruction flags, ambiguity controls, query execution outcomes, year range, zero retrieval smoothing, and frequency-observation uniqueness.
