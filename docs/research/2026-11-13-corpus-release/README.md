# Australian Corpus: Acquisition Closeout and Research Progress

**Release date: 13 November 2026. Study window: 1 January 2003–31 December 2025. Acquisition: complete.**

The government/official acquisition inventory supplied the activity-based temporal reference for selecting this window. The public-expression window was subsequently fixed to the complete 2003–2025 interval. This is an explicit research scope, not a fitted historical change point or evidence that fear began in 2003. The older official inventory retains its separate 1988–2026 reference scope and recorded access gaps.

## Final accounting

| Unit | Count | Interpretation |
|---|---:|---|
| Frozen formal baseline | 776,559 | Preserved before the final targeted phase |
| Gross new-document receipts in round31 | 26,383 | Before current-phase reversible holds |
| Current-phase reversible holds | 1,383 | Retained outside formal increment credit; include confirmed and unresolved cases |
| Actual net new formal records in round31 | 25,000 | 26,383 minus 1,383 |
| Final formal union across stores | **801,559** | 776,559 plus 25,000; not a physical SQLite row count |
| Dated formal records in 2003–2025 | 801,516 | All 23 publication years represented |
| Baseline records with unresolved dates | 43 | Retained separately; not assigned an invented year |
| Final-phase source domains | 530 | Descriptive domain count, not independent people or source owners |

The selected hard cap of 810,000 was respected. The source processor, saved-input processor and sole writer finished naturally, with the last writer batch complete at 00:40:36 AEST on 13 November. No manual threshold termination was used. No further collection is launched by this publication.

The final phase has 21,576 native authored-article fields, 3,142 personal-blog fields, 196 forum posts and 86 public blog comments. These are native acquisition categories, not verified personal experience, Australian residence or emotion labels. Stored extraction projections include 9,715 records at least 1,000 tokens long and 15,285 complete shorter fields; retained quotation and interface context mean these lengths are not universally pure narrator utterance lengths.

## What this package publishes

- [Acquisition process](ACQUISITION_PROCESS.md): discovery, native-body capture, identity/version handling, durable writing and final verification.
- [Decision history](DECISION_HISTORY.md): scope, matrix expansion, effort weights, source preferences and closure.
- [Accepted research questions](RESEARCH_QUESTIONS.md): longitudinal learning-compatible development, validated ML/DL measurement and event-centred change.
- [Next-stage design](NEXT_STEPS.md): derived text views, leakage control, annotation and model evaluation.
- [Complete query matrix](../../methodology/search/QUERY_MATRIX.md), [version index](../../../config/search/versions.json) and [search registers](../../methodology/search/README.md).
- [Machine-readable closeout](collection_summary.json), [annual accounting](annual_counts.csv) and [final-phase domain counts](round31_domains.csv).
- [Seven figures](FIGURES.md) and the [fully coded, executed notebook](query_matrix_visualizations.ipynb).
- [Publication manifest](PUBLICATION_MANIFEST.json): exact public artifact hashes and original local source references.

This is a methods-and-results documentation release. It is not a newly created raw-data snapshot, restore-tested backup, deposit of original text or complete archive of every historical runtime artifact.

## Verification and limits

The inherited final current-phase verification replayed the 25,000 retained bodies against their native responses, identities, date/byline evidence and sealed receipts. Preservation checks retained the baseline and available historical metadata/version relations. Pre-round29 does not have a complete old per-observation and version-edge snapshot; no universal historical preservation or frozen-body replay claim follows.

An additional generic 410-row metadata check had 406 strict matches and four explicitly documented chronology qualifications: one omitted native modification value and three same-value metadata-path aliases. The original omissions and strict failures remain preserved. First publication, CMS modification, rendered update, capture time and narrative/event time remain different clocks. Original bodies and metadata were not rewritten to erase qualifications.

A subsequent bounded review of 36 records, 31 sources, 23 years and 33 raw responses found no new hard defects and two medium derived segmentation annotations. This is not a corpus-wide semantic clearance or estimated error rate. Early 2003–2005 records remain concentrated in a few domains; source/time sensitivities belong in later analysis, not destructive pruning.

Query membership is an acquisition association. Neither the 801,559 total nor the 25,000 final increment establishes negative-affect prevalence, Fear intensity, population representativeness or learned cultural transmission. No validated corpus-wide emotion labels or empirical trend findings are released here.

## Data access and preservation

Original text, raw API/HTML/PDF evidence, database files, body versions, detailed receipts, identifiers and holding tracks remain in protected local storage. A repository clone supplies code, definitions and aggregate evidence, not the raw corpus. Source-specific redistribution and privacy review must precede any text release. No repository-wide licence or data DOI has yet been assigned.

Existing SQLite primary/recovery files remain at their original locations; DuckDB increments have not been represented as a completed physical migration. Formal counts reconcile across stores and eligibility tracks. Preserve original publication dates, voices, quotations, work/version links and reversible holds during all derived work.
