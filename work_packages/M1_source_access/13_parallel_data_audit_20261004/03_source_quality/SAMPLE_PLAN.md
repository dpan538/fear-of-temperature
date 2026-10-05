# Prespecified provenance check (4 October 2026)

Unit: one independent parent or EU Work, not an attachment, segment, query hit, or version. The check has **30** purposive cases and is not an estimator of source-wide error rates. Selection is fixed by the strata below and `build_source_quality.py`; within a stratum without a named exception, choose the lexicographically smallest SHA-256 of its stable parent ID. Existing local source files, database links and committed audit ledgers are checked before any source page. No new source-page access is required for this review.

| Frame | Prespecified strata | Cases |
|---|---|---:|
| UK | two Historic Hansard, two Parliament Questions/Statements API, one Parliament Hansard/publications archive, one ParlParse/TWFY mirror, one DEFRA GOV.UK, one historical GOV.UK | 8 |
| US Federal Register | one ordinary downloaded raw text, one govinfo fallback, both distinct dated 95-24211 records, one 95-14725 cross-agency record | 5 |
| EU CELLAR | two extracted items, one OCR candidate, one HTML placeholder, one Work without an English digital item | 5 |
| AU DCCEEW catalogue | 2015 NCRAS, 2008 EPBC policy, CSIRO issuer-review exception, one files-verified/date-pending record, one raw-pending September 2026 plan | 5 |
| Guardian | the one December 2015 previously body-reviewed article, plus three December article URLs selected by parent-ID hash from the 396-URL archive frame | 4 |
| UK petitions | two published and one rejected submission from the pre-existing 21-parent reviewed pilot, chosen by parent-ID hash | 3 |

Checks are limited to source/parent identity, publication-date evidence and precision, local saved version/raw route, content-object or body mapping, issuer attribution, and access. A current saved body does not establish its historical wording. A dispute about a substantive claim is recorded separately from a provenance conflict. The resulting checked statuses apply only to these 30 parents.
