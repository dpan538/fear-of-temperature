# US/Australia government acquisition: coverage and data quality

Generated 2026-09-27T00:02:50.420368+00:00 from ledger snapshot 2026-09-27T00:02:39.226199+00:00. Study window **1988-01-01 to 2026-09-21**. US supervisor state: `blocked_access_or_no_progress`. This report reflects the last committed database reconciliation and hash-verified files; the selected US series is complete only if that state is `us_selected_series_complete` and the audit passes.

## Source-specific progress

| Source period | Enumerated unique US parents | Verified downloaded texts | Parents with cleaned text in DB | Interpretation |
|---|---:|---:|---:|---|
| 1988–1993 | unknown | 0 | 0 | FederalRegister.gov API route unsupported; GovInfo annual indexes and scanned issues exist, but agency/genre document denominator is not enumerated |
| 1994–2002 | 10,237 | 10,218 | 10,218 | Fixed EPA/DOE final/proposed-rule series; historically prioritised |
| 2003–2026-09-21 | 23,307 | 56 | 56 | Same selected US series; September 2026 is a partial calendar bin |

The 132 reconciled agency × genre × year partitions contain **33,560 stratum hits** and **33,544 unique canonical document URLs**. The 16 cross-agency hits remain one parent with two associations. These are administrative rule/proposed-rule Works, not a US climate-policy denominator. No climate keyword filter was applied. The database has 33,544 US metadata parents, 10,274 saved US content versions and 10,274 locally hash-verified downloaded text files. Downloaded files awaiting insertion remain separately visible.

The Australian 83-page snapshot has **823 cards / 821 unique landing URL candidates**. All 821 candidates are stored as catalogue records with CMS time separate from original issue date. Four independently reviewed originals have verified landing/PDF pairs (8 content versions): two have an evidenced issue month or day and two only an issue year. 817 candidates still lack an original issue date. Catalogue candidates are not automatically distinct policy Works or exact-month observations. Ordinary current-host requests to both a recent and the oldest CMS-listed candidate timed out; the National Library predecessor route returned an access challenge. Neither outcome is a zero month.

## Parent-based monthly acceptance

The [monthly ledger](monthly_progress.csv) gives source, jurisdiction, agency, genre, date basis, enumerated target, unique parent, text-available parent, usable parent, unassessed relevant-parent and segment counts for all 465 study months. For the selected US agency/genre series, 107 months currently have resolved usable-or-verified-zero acquisition states, 98 have usable parent observations, and 9 are verified zero across all four US strata. The longest unresolved run is 285 months. These are **series-processing states**, not historical population coverage. The AU original-date monthly denominator is unknown; 817 undated candidates and two year-only originals cannot be assigned exact months. No country or genre fills another's missing observation.

The [49-bin event-window ledger](event_window_2015_paris_coverage.csv) uses the independently dated 12 December 2015 Paris Agreement adoption as a *coverage candidate*: 24 complete pre-event months, December 2015 separately, and 24 complete post-event months. It reports government-only source states; media and public roles have not been audited here. No RQ1 shared three-role window or RQ2 effect estimate is claimed. Relevance to warming/fear remains `not_yet_assessed` for every parent.

## Version, extraction and integrity

Only actual saved 2xx bytes that match SHA-256 create content versions. AU landing, primary PDF and alternative roles remain linked to one candidate parent; PDF files are not new parent documents. Source extraction and initial structural cleaning use separate runs, with raw bytes and clean-to-source mappings retained. The current DB contains 328,092 source segments and 1,131,839 cleaned segments in this tranche; **neither count is an independent sample size**. US extraction v1 used printed lines for its first blocks; v2 stores one complete source-text segment per later document to control storage growth. The cleaned paragraphs retain source line-range locators. The source-specific rules remove Federal Register page boilerplate, repair broken line wraps/hyphens, and discard short fragments; they do not normalise sentiment or run models.

The [content-status manifest](content_status.csv) distinguishes downloaded/cleaned, no-text or OCR candidates and not-requested content objects. [Successful extractions](success_records.csv), [extraction/OCR exceptions](extraction_exceptions.csv), [pending records](pending_records.csv), [request failures](exceptions.csv) and [route exceptions](../route_exceptions.csv) are separate, machine-readable lists. Current targeted audit: UK baseline unchanged = `True`; verified new version hashes = `10282`; hash mismatches = `0`; orphan segments = `0`; unmapped cleaned segments = `0`. Source language is presumed from the English official entrances and verified for retrieved texts; uncollected catalogue candidates are not represented as confirmed English bodies.

## Remaining work and use boundary

US body retrieval/insertion remains 23,270 parents short of the selected denominator. The 1988–1993 GovInfo annual indexes are an official finding aid, and their EPA/DOE rule and proposed-rule entries still need document-level enumeration and issue matching. AU needs original-date, publisher and primary-file review across the remaining catalogue candidates and a separately enumerated predecessor archive. The current DCCEEW and National Library access failures are documented without bypass. Source-specific US and AU raw counts must not be summed into a single global policy time series. Project authorisation for collection is recorded separately from institutional ethics status; no UQ approval or exemption is asserted. Raw full text is held for internal research, with public redistribution unassessed.

See [filter contract](../FILTER_CONTRACT.md), [runbook](../RUNBOOK.md), [object status](object_status.csv), [monthly progress](monthly_progress.csv), [identity spot checks](identity_spot_checks.csv), [integrity audit](integrity_audit.json), and [Figure 5](figure_5_us_au_coverage.pdf). The UK 06 database is a frozen comparator; the US/AU working copy is the only write target for this tranche.
