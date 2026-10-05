# Project development log

This is the ongoing record of implementation progress, decisions and weekly plans. The proposal remains the planning baseline; development findings are recorded here rather than repeatedly incorporated into the proposal.

## 2026-09-21 — Government acquisition and text quality review

### Confirmed decisions / 已确认决定

- Dai confirmed that the project is in development, not proposal revision. Do not update proposal text, figures or exports as part of routine progress reporting.
- Follow the existing proposal plan with weekly progress records. The current proposal specifies 10–20 hours/week and completion of analysis and robustness checks by 28 February 2027; these are planning commitments, not recorded hours or achieved milestones.
- This conversation handles decisions, review, logs and instructions. Collection and implementation run in the designated execution conversation.
- Jev is deferred. No new model or external classification service is introduced.
- Government acquisition remains bounded to the frozen DEFRA/GOV.UK query set. No further source expansion is implied by completion of this batch.

### Completed work and evidence

Acquisition results below are from the execution conversation's completion report. Text-quality findings were checked against the saved review report; this log entry did not independently rerun database validation.

| Item | Recorded result |
|---|---:|
| Publication records | 1,020 |
| Unique attachment targets | 2,005 |
| Content objects attempted | 3,025 / 3,025 |
| Successfully downloaded objects | 3,016 |
| Successfully extracted objects | 2,995 |
| Stored extraction segments | 2,853,343 |
| Extracted characters | 143,725,193 |
| Needs OCR | 14 |
| Unsupported format | 5 |
| Extraction failures after successful download | 2 |
| Unavailable/error-page objects | 9 |

The execution report records successful recovery and provenance checks and preservation of the frozen 04/05 databases. Project collection authorization is recorded separately from institutional ethics status; this entry does not declare UQ HREC approval or exemption.

Evidence:

- [Acquisition report and recovery commands](../work_packages/M1_source_access/06_government_content_acquisition/README.md)
- [Authorization and use record](../work_packages/M1_source_access/06_government_content_acquisition/AUTHORIZATION_AND_USE.md)
- [Text quality review for Dai](../work_packages/M1_source_access/06_government_content_acquisition/text_quality_review/text_quality_report_for_dai.md)
- [Verification record](../work_packages/M1_source_access/06_government_content_acquisition/verification.json)

### Findings affecting the next implementation step

- PDF accounts for 96.22% of segments. Median segment length is 39 characters; 30.83% are at most 20 characters. Current PDF segments are largely newline-based extraction units, not reconstructed natural-language paragraphs.
- The largest 20 objects contribute 29.32% of segments. Volume is concentrated in long reports, legislation and tabular material; segment count is not a count of independent observations or usable retrieval passages.
- A text-volume heuristic identifies 984/1,020 publication records as attachment-dominant. This is a review aid, not proof of full-text completeness.
- There are 43 possible exact-overlap candidates between landing pages and attachments, including one near-complete overlap. These are candidates, not instructions to delete records.
- Web extraction retains some service text. Structured tables and PDF reading-order problems need separate treatment before retrieval inputs are constructed.
- Current acquisition demonstrates bounded download/storage feasibility. It does not yet establish historical completeness, historical version fidelity, cross-role comparability or analysis readiness.

### Updated execution decision — single ingestion and final acceptance

Dai superseded the earlier proposed 07 sample/derived-passage workflow. The approved decision is [single ingestion and stage boundaries](decisions/2026-09-21-single-ingestion-and-stage-boundaries.md).

- Continue in the existing 06 working database. Do not ingest the same sources again or create another parallel corpus.
- Inspect and repair actual extraction defects using saved files; retain source identities, content versions and valid locators. Record repair operations without duplicating sources or current text.
- Keep paragraph reconstruction, general cleaning and retrieval preparation for the dedicated cleaning stage. No vector validation, Jev or repeated sample approval cycle.
- Report fixed acquisition target and actual progress separately from repair progress. Baseline: 3,025 expected/attempted, 3,016 downloaded, 2,995 extracted; 9 download exceptions and 21 extraction exceptions.
- Perform one consolidated final acceptance after necessary repairs, reusing existing evidence for unchanged components. Report exceptions and a cleaning backlog, then close the bounded acquisition stage.

This conversation records the decision only. Database repairs have not been executed here. Weekly work remains aligned with the proposal's 10–20 hour budget; actual effort is recorded only when known.

### 2026-09-21 — Pre-2010 source discovery (read-only research)

Dai requested source discovery before deciding a historical backfill task. The review confirms 55 publication records before 2010 in the current batch and identifies actual GOV.UK DTI/DECC policy examples absent from its canonical-URL manifest. Hansard 1988 ministerial-answer text and UNFCCC historical reports are readable candidates. UK Government Web Archive offers official discovery/export routes, but archive replay/bulk retrieval remains unverified here; ProQuest access remains conditional. Full findings, direct sources and scope choices are in [the pre-2010 source review](research/2026-09-21-pre2010-government-source-review.md).

No collection, corpus/database changes or proposal changes were made. No new source has been approved merely by appearing in this review. Next discussion: related-department policy expansion and whether ministerial answers/statements should form a separate series.

### Weekly logging convention (ongoing)

Each subsequent entry should record:

- week/date and corresponding proposal milestone;
- planned work versus completed work;
- evidence and deliverable paths;
- actual effort when known (never substitute estimates);
- decisions, unresolved issues and effects on schedule;
- next week's bounded deliverables.

中文摘要：proposal 作为既定计划保留，后续按周记录项目实施。同批来源不重复入库；当前只做必要提取修理与统一最终验收，专门的数据清洗和段落重建留待后续阶段。取消此前反复样本确认流程，暂不引入 Jev。

## 2026-09-21 — Download-exception retry and government-corpus coverage analysis

### Completed work

- Continued in the existing 06 working database and retained the frozen 1,020 publication records, 1,020 webpage objects, 2,005 unique attachment objects and 3,025 total content objects. No source re-enumeration or parallel corpus was created.
- Added a bounded `retry-download-exceptions` path that selects only current download exceptions. It does not select successful objects or the 21 successfully downloaded extraction exceptions.
- Performed one actual-network retry of the nine original URLs. The result remained eight HTTP 403 responses and one HTTP 200 error page.
- Checked only the corresponding publication or official institutional sites for the same files. Nine identity-reviewed replacement addresses were recorded using title, organisation, reporting round, year, DOI or report number as applicable. Five objects were recovered and extracted; four remained inaccessible and were stopped without bypassing access controls.
- Preserved stable `content_object_id` values, current one-row-per-object status, acquisition events, saved hashes and content-version evidence. Address changes are recorded in the retry evidence rather than creating new source objects.
- Generated complete 1988–2026 annual rows, specified decade groups, year-by-month counts, three figures, explicit coverage-rate denominators, a proposal-gap assessment and a concise HTML page under `06_government_content_acquisition/coverage_analysis/`.
- Ran source preflight, PDF glyph checks and rendered collision audits for all three figures. Final collision audits pass; minimum PDF text size is 7 pt. Single-panel alignment checks are not applicable.

### Before/after acquisition status

| Item | Before | After | Change |
|---|---:|---:|---:|
| Expected / attempted content objects | 3,025 / 3,025 | 3,025 / 3,025 | 0 |
| Successful downloads | 3,016 | 3,021 | +5 |
| Successful extractions | 2,995 | 3,000 | +5 |
| Download exceptions | 9 | 4 | -5 |
| Downloaded extraction exceptions | 21 | 21 | 0 |
| Source-extraction segments | 2,853,343 | 2,865,202 | +11,859 |

Recovered objects: National Grid Gas, OECD biodiversity/natural-capital report, OECD ghost-fishing-gear report, Thames Water, and Historic England / English Heritage Trust. All five recovered files were detected as PDFs and extracted successfully.

Remaining download exceptions:

- National Grid Electricity Transmission — reviewed official replacement still HTTP 403.
- Portsmouth Water — reviewed official PDF still HTTP 403.
- Anglian Water — reviewed official PDF still HTTP 403.
- Birmingham Airport — reviewed official media URL could not be resolved in the acquisition runtime.

The separate downloaded extraction backlog remains 14 `needs_ocr`, 5 unsupported formats and 2 extraction failures. It was not reprocessed in this task.

The acquisition-run history also contains one restricted-runtime DNS attempt that did not reach remote hosts and one interrupted implementation run with `attempted_count=0`. They are retained for audit but are not counted as the finite remote retry. Final database verification restored and confirmed one current status/fetch per object.

### Distribution and coverage findings

- All 1,020 publication records have `first_published_at`; missing dates are 0. The first observed year is 1997. Zero rows for 1988–1996 and other years mean no record was observed in this frozen query, not that government policy did not exist.
- Decade groups contain 0 records for 1988–1989, 3 for 1990–1999, 52 for 2000–2009, 488 for 2010–2019 and 477 for 2020–21 September 2026. The opening and closing groups are incomplete by design.
- One attachment is shared across parent publication years 2019, 2024 and 2025. Annual attachment text totals use a parent-year association count, so cross-year sums are not unique attachment totals.
- Final calculable rates are: frozen-list attempt completion 3,025/3,025; download success 3,021/3,025; extraction success among downloads 3,000/3,021; target-object text availability 3,000/3,025. Webpage and attachment denominators are reported separately.
- Among 1,016 publication records with attachments, 998 have all linked attachments extracted, 10 have some but not all extracted, and 8 have none extracted. These are mutually exclusive record-level states, not a claim of policy full-text completeness.
- The frozen Search API type is `policy_paper`; current Content API metadata contains 1,019 `policy_paper` records and one `guidance` record. The drift is retained.
- `updated_at` is later than `first_published_at` for 275 records; the longest gap is 4,952 days. Dates remain binned by first publication, but the downloaded current version need not reproduce the first-published text.
- Current scope is limited to the frozen GOV.UK query under the current DEFRA organisation label. It does not support UK-government-wide, DEFRA-historical, cross-country, climate-policy-share or fear-expression coverage rates.

### Evidence

- [Government corpus coverage report](../work_packages/M1_source_access/06_government_content_acquisition/coverage_analysis/government_corpus_coverage_report.md)
- [HTML summary](../work_packages/M1_source_access/06_government_content_acquisition/coverage_analysis/index.html)
- [Annual distribution](../work_packages/M1_source_access/06_government_content_acquisition/coverage_analysis/annual_distribution.csv)
- [Decade distribution](../work_packages/M1_source_access/06_government_content_acquisition/coverage_analysis/decade_distribution.csv)
- [Coverage metrics](../work_packages/M1_source_access/06_government_content_acquisition/coverage_analysis/coverage_metrics.csv)
- [Retry results](../work_packages/M1_source_access/06_government_content_acquisition/coverage_analysis/retry_results.csv)
- [Final checks](../work_packages/M1_source_access/06_government_content_acquisition/coverage_analysis/final_checks.json)

Final checks pass: frozen 04 database, frozen manifest and 05 database hashes remain unchanged; object and current-status counts align; annual, decade and year-month totals reconcile; attachment availability states are exhaustive; chart source rows match the CSVs.

### Next bounded recommendations

- Retain all observed 1997–2026 records as the government source archive. Treat 1997–2010 mainly as sparse historical context and 2011–2025 as a candidate interval for a later monthly/quarterly stability assessment; keep 2026 partial.
- Do not start cross-role temporal analysis until Guardian and public-source availability, denominators and a common window are frozen.
- In the dedicated cleaning stage, reconstruct or aggregate PDF line/block units and table row/cell units within their parent objects. Do not interpret the 2,865,202 current segments as natural paragraphs or independent observations.
- Keep the four download exceptions and 21 extraction exceptions as explicit retained states; do not delete them or silently treat landing-page extraction as attachment/full-policy completeness.

Actual effort was not supplied and is therefore not recorded.


## 2026-09-21 — Historical expansion approved; execution handoff prepared

Dai approved an independent ministerial-answer/statement series following the historical-source review and requested collection instructions. The [approved decision](decisions/2026-09-21-historical-policy-and-ministerial-series.md) and [execution handoff](handoffs/2026-09-21-historical-government-acquisition.md) define related-department pre-2010 policy backfill plus a separate Commons written-answer/statement tranche. The ministerial discovery interval continues through the existing 2026-09-21 cutoff to avoid a source-channel break at 2010; process the historical years first. Other Houses, oral debate and additional countries are deferred implementation choices.

Expected additions must be established through source/year/genre enumeration and deduplication; no target count has been invented. Continue in the 06 working database, preserve existing identities and frozen snapshots, and report each genre separately. No collection, database mutation, proposal revision or dispatch to another task was performed by this decision window.


## 2026-09-22 — Historical policies and Commons ministerial series acquired and accepted

### Execution boundary and recovery

- Continued in the sole 06 working database and retained the pre-expansion recovery snapshot at `work_packages/M1_source_access/07_historical_government_acquisition/recovery/fear_temperature_government_content.before_historical.8d26ec74c222.duckdb` (SHA-256 prefix `8d26ec74c222`). No parallel corpus was created.
- Stopped the redundant full temporary smoke path. Its two diagnostic databases and `reports/smoke_test_stop_record.json` are retained but never count as formal progress.
- Changed Parliament ingestion to source-internal blocks of 1,000 records, written in foreign-key dependency order. Each block commits before its checkpoint and progress message; a failed block rolls back without undoing earlier committed blocks.
- A single 1,000-record gap validation transaction initially failed because the heterogeneous combined manifest had discarded archive-parent columns. The transaction rolled back with no formal additions. The manifest writer was corrected to preserve the field union, 626 already-downloaded official HTML parents were reparsed locally with zero network requests, and the bounded validation then committed successfully before the remainder resumed.
- No proposal, cleaning, vectorisation, semantic model, model validation or extra approval stage was added.

### Final source progress

| Source tranche | Frozen / enumerated target | Already in 06 | Original acquired and parsed | Formally committed | Remaining exceptions |
|---|---:|---:|---:|---:|---|
| GOV.UK historical policy | 35 records | 1 | 34 net-new records; 84/84 objects downloaded | 34 | 4 downloaded PDFs are `needs_ocr`; UK DoE/MAFF searchable policy routes remain unresolved |
| Historic Hansard bulk XML, 1988–2004 | 135,761 records | 0 | 135,761 | 135,761 | 319/320 ZIP targets valid; volume 200 is an HTTP-200 error page |
| Hansard API, 2005–2010-04-30 | 24,833 records | 0 | 24,748 | 24,748 | 85 frozen answer targets failed; 7 additional candidate-level failures are retained separately |
| Commons archive/API gap, 2010-05-01–2014-09-11 | 11,628 parsed record targets | 0 | 11,628 | 11,628 | Partial channel coverage: 20 failed indexes, 225 failed page requests, 212 frozen pages unrequested after throttle stop and 2 unresolved statement candidates |
| Questions/Statements API, 2014-09-12–2026-09-21 | 65,988 records | 0 | 65,988 | 65,988 | 0 record failures; records derive from 174 verified complete-text list responses |

The policy series added 34 records. The ministerial series added 235,420 written answers and 2,705 written statements across the database when combined with no pre-existing ministerial records. The final database contains 239,179 documents and 3,622,039 text segments. The three analytical series remain separate: 1,054 policy-source publication records, 235,420 ministerial written answers and 2,705 ministerial written statements.

Historic Hansard contains 135,368 answers and 393 statements. The 2005–2010 tranche contains 23,905 acquired answers and 843 statements. The gap tranche contains 11,135 archive-derived answers and 493 statements. The modern tranche contains 65,012 answers and 976 statements. Question/context segments are retained for evidence but are not counted as government responses.

### Provenance and rate-limit findings

- Historic per-record JSON is a derived record linked to its downloaded official ZIP/XML volume and source locator. Gap answer JSON is linked to the downloaded official archive HTML and question anchor. Modern per-record JSON is linked by official ID to one of 174 downloaded API list responses.
- Real request URL, final URL, HTTP status, MIME type and retrieval time come from the parent request evidence. Formal ingestion time is separate. No derived record is represented as an unmade per-record HTTP 200/XML request.
- The 2010–2014 archive phase froze 1,063 unique target pages. After 851 attempted pages produced 626 successes and 225 failures, repeated 403 responses triggered the documented dynamic stop; 212 pages remained unrequested. No login, captcha or WAF bypass was attempted.
- The 2010-05-01–2014-09-11 interval therefore remains explicitly partial. Zero observations and unprocessed pages are not interpreted as zero ministerial activity, and no continuous 1988–2026 claim is made.
- DTI, BERR and BEIS records are broad departmental material. They are not labelled as climate-specific answers without a later governed selection stage.

### Final acceptance

- All source/year/genre record manifests have unique external IDs and canonical URLs; cross-manifest external-ID overlap is zero.
- Database duplicate source/external IDs, duplicate canonical URLs, duplicate content-object URLs, orphan text segments and orphan voice attributions are all zero.
- Annual CSV totals match the database, quarterly totals reconcile to annual totals, and the 1988 and 2026 partial-year boundaries are explicit.
- Historic ZIP, archive-HTML and modern list-response provenance checks all pass. The 04 database, 04 manifest and 05 database hashes are unchanged.
- All three 183 mm figures passed text-boundary QA; PDF text is extractable with DejaVu Sans fonts and a 6.2 pt minimum. The six-sheet XLSX audit workbook passed its formula-error scan and visual preview check.

### Deliverables

- [Final Markdown report](../work_packages/M1_source_access/07_historical_government_acquisition/reports/historical_government_acquisition_report.md)
- [Concise HTML report](../work_packages/M1_source_access/07_historical_government_acquisition/reports/index.html)
- [Annual distribution CSV](../work_packages/M1_source_access/07_historical_government_acquisition/reports/annual_distribution.csv)
- [Quarterly distribution CSV](../work_packages/M1_source_access/07_historical_government_acquisition/reports/quarterly_distribution.csv)
- [Source progress CSV](../work_packages/M1_source_access/07_historical_government_acquisition/reports/source_progress.csv)
- [Source-by-year reconciliation](../work_packages/M1_source_access/07_historical_government_acquisition/reports/source_year_progress.csv)
- [Exceptions and gaps](../work_packages/M1_source_access/07_historical_government_acquisition/reports/exceptions_and_gaps.csv)
- [Final integrity checks](../work_packages/M1_source_access/07_historical_government_acquisition/reports/final_integrity_checks.json)
- [Audit workbook](../outputs/01a0c28b-466f-7a23-b28c-0d66628f6a28/historical_government_acquisition_audit.xlsx)

### Next bounded recommendations

- Use the three series independently and add source-regime indicators to any later time comparison. Do not infer a continuous census across the documented channel gaps.
- Preserve the four policy PDFs marked `needs_ocr`, volume 200, 85 failed answer targets, 20 failed indexes, 225 failed pages, 212 unrequested pages and two unresolved statement candidates as explicit states. Do not silently impute, delete or treat them as successful text.
- If Dai later approves a dedicated extraction stage, OCR only the four retained historical-policy PDFs and revisit the frozen unresolved page targets under the documented aggregate rate limit. This is not part of the completed acquisition task.

Actual effort was not supplied and is therefore not recorded.


## 2026-09-22 — Post-acquisition government-corpus distribution and coverage assessment

### Scope and snapshot

- Opened the existing 06 DuckDB in read-only mode and wrote only to a new report directory under `07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/`. No network request, collection, database mutation, cleaning, vectorisation, model run, proposal change, workbook or full-database hash rerun was performed.
- The database size and modification time were unchanged before and after the read transaction. The fixed baseline reconciles: 239,179 documents, 1,054 policy-source publication records, 235,420 ministerial written answers, 2,705 ministerial written statements and 3,622,039 text segments.
- The 1,054 policy-source records consist of 1,053 stored `policy_paper` rows plus the one retained original-batch `guidance` row created by the frozen Search/API type mismatch. The database type was not rewritten.

### Distribution and text-scale findings

- Annual, quarterly, year-by-month and decade tables all reconcile to the same three genre totals. Of the 465 study-month slots, policy records appear in 228, written answers in 409 and written statements in 254; absence in a database month is not automatically a completed-source zero.
- Unique text scale is 2,989,270 policy segments / 151,355,178 characters, 627,397 answer segments / 184,124,378 characters and 5,372 statement segments / 4,872,256 characters. These are text-scale measures, not independent observations.
- Median record lengths are 46,996 characters for policy-source records, 513 for answers and 1,019 for statements. The ten longest records account for 22.2%, 0.1% and 5.0% of each series' record-associated characters respectively, so long-policy concentration needs later cleaning-stage attention.
- Department composition changes with machinery of government and source regime. The written-answer share peaks for DTI in 2005 (1,940/3,919; 49.5%), BERR in 2008 (2,110/5,321; 39.7%) and BEIS in 2022 (4,917/7,698; 63.9%). These broad-department shares are not climate or fear measures.

### Coverage-state findings

- Record quantities and collection status are now separate. The source × month table distinguishes completed/processed, completed with failures, incomplete enumeration/index, known but unrequested targets, unsupported periods and verified zero records.
- Historic Hansard volume 200 covers 1991-12-02 to 1991-12-13 and remains an HTTP-200 invalid ZIP; the hidden record count is unknown.
- The Historic Hansard bulk-volume window actually runs from 1988-01-11 through 2004-10-04; its opening and closing calendar months are marked as partial source support rather than confirmed-zero/complete months.
- The 2005–2010 tranche retains 85 failed answer-section targets and 7 candidate-detail anomalies as different units.
- The 2010-05-01–2014-09-11 tranche remains partial: 20 failed dated indexes, 225 failed known page targets, 212 known page targets not requested after the throttle stop and 2 unresolved statement candidates. Index failures may hide an unknown number of targets, so none of these categories is added into one “missing documents” total.
- Modern coverage retains separate denominators: 174 acquired parent API responses and 65,988 derived records. Successful ingestion of all eligible derived records does not substitute for a per-record HTTP acquisition rate.
- Historical policy enumeration is complete only within visible DTI/DECC/BERR/DETR GOV.UK organisation-tag partitions. UK DoE/MAFF predecessor archive routes remain an incomplete-enumeration state, not zero policy.

### Use recommendation

- The three genres can proceed to source-aware cleaning as independent series, with explicit partial-coverage flags. The totals alone do not justify a continuous 1988–2026 time-series claim.
- Prefer comparisons within stable source regimes. Treat volume 200, the 85 answer targets and the whole 2010–2014 answer gap as partial coverage; treat early policy before reliable predecessor routes as incomplete coverage.
- The most consequential future gap work is the 2010–2014 failed date indexes and unrequested pages because they affect the denominator, followed by failed pages. Policy archive-route discovery and OCR of four known PDFs improve different aspects of coverage and should remain separate decisions.
- A common government/news/public analysis window remains pending the other layers' own distribution and coverage assessment. Dai will decide whether to reopen acquisition.

### Deliverables and checks

- [Distribution and coverage report](../work_packages/M1_source_access/07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/government_corpus_distribution_coverage_report.md)
- [Concise HTML page](../work_packages/M1_source_access/07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/index.html)
- [Coverage-state CSV](../work_packages/M1_source_access/07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/coverage_status_by_source_month.csv)
- [Layered coverage rates](../work_packages/M1_source_access/07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/coverage_rates.csv)
- [Annual distribution](../work_packages/M1_source_access/07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/annual_distribution.csv)
- [Quarterly distribution](../work_packages/M1_source_access/07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/quarterly_distribution.csv)
- [Year-month distribution](../work_packages/M1_source_access/07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/year_month_distribution.csv)
- [Department annual composition](../work_packages/M1_source_access/07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/department_annual_composition.csv)
- [Final checks](../work_packages/M1_source_access/07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/final_checks.json)

Annual/quarterly/monthly/decade totals reconcile, all coverage-rate denominators are positive and unit-labelled, and the source-month status grid has the expected 3,720 rows. All four figures passed strict source preflight, panel alignment (or single-panel not-applicable), the 5 pt PDF glyph floor, rendered collision checks and final visual inspection.

Actual effort was not supplied and is therefore not recorded.


## 2026-09-22 — Decision review: targeted government gap repair

- Reviewed the post-acquisition coverage report, saved failure manifests, selected raw Hansard payloads and the current parser. Performed limited official web lookups for alternative routes; no corpus collection, database access/mutation, ingestion, cleaning, vectorisation or proposal update was performed in this decision review.
- The 85 unsuccessful 2005–2010 answer targets are not 85 transport failures. Local payload inspection found 79 nested-department cases dated 2006-05-22 (41 DEFRA, 38 DTI) in which the parser selects the first department ancestor, plus four question-format boundary failures with locally visible questions/answers, one mixed question/correction payload (Asda), and one API error (Companies House). These are repair candidates, not yet verified additions.
- Identified a cross-route seam from 2004-10-05 through 2004-12-31: the bulk route ends October 4 and the next route starts in 2005. Official search results expose December 2004 Commons records; execution-time retrieval/target enumeration remains necessary. The January 1988 boundary needs a sitting-calendar check before being treated as missing material.
- Directly opened the official 1991-12-02 Historic Hansard sitting index, confirming Commons volume 200 and a potential daily-index fallback for the failed ZIP. Also located the official 2010-02-23 statement index supporting the Energy and Climate Change target 10022378000029.
- The 20 failed 2010–2014 indexes, 225 failed pages and 212 unrequested pages remain different units. Seven of nine unresolved statement candidates have potentially out-of-scope departmental attribution, one is an in-scope DECC target and one appears to be a container; scope/date/child identity verification must precede claims of missing records.
- Prepared an execution-window handoff with local parser repair, bounded date/page recovery, candidate resolution, four-file OCR recovery, incremental ingestion and one final coverage refresh. Historical policy-publication coverage remains distinct from ministerial answer/statement coverage. No repair or recovered-count claim has been made here.
- Handoff: [Targeted government gap repair](handoffs/2026-09-22-government-targeted-gap-repair.md).


## 2026-09-22 — Targeted government gap repair completed

### Bounded execution and results

- Continued in the formal 06 DuckDB and used one pre-write recovery checkpoint under `07_historical_government_acquisition/targeted_gap_repair/recovery/`. No full temporary ingestion, full smoke replay, successful-record re-download, global re-enumeration or full-database hash rerun was performed.
- Corrected nearest-department ancestor and structured-question parsing. Of 85 saved HTTP-200 Hansard answer anomalies, 83 were deterministically reparsed and committed from unchanged bytes. Asda (`06071282000011`) and Companies House (`07091719000037`) remain unresolved after their ordinary rendered routes returned HTTP 403.
- Resolved nine statement candidates from saved official search-parent evidence. Three in-scope child statements were committed under official `ContributionExtId`; five candidate containers were excluded as outside the approved department scope; one repeated cross-date header/container remains unresolved and was not inserted.
- Used the official Historic Hansard daily route for failed volume 200. The official calendar confirms 10 Commons sitting days from 1991-12-02 through 1991-12-13. All 322 approved-department item pages returned HTTP 200; 321 parsed records were committed. `Self-regulating Bodies` remains unresolved because the official page splices unrelated answer text into the questioner block without reliable minister attribution.
- Verified that the January 1988 official calendar begins on 1988-01-11, so 1–10 January is a recess boundary rather than a collection gap.
- Checked 43 Historic sitting indexes in the 2004-Q4 seam; their written-answer/statement material is Lords-only and was not substituted for Commons. The normal publications and modern Hansard hosts each returned three consecutive HTTP 403 responses and were stopped without challenge bypass. The Commons 2004-10-05..12-31 denominator remains unknown.
- Preserved the 2010–2014 repair queue as separate units: 20 failed date indexes, 225 previously failed known HTML pages and 212 previously unrequested known pages. One corrected index request and one failed-page request returned HTTP 403 before the shared publications-host stop threshold; no document total is inferred from these units.
- Recovered exactly four existing downloaded policy PDFs with local Apple Vision OCR. Original content versions are unchanged; the new extraction lineage contains 340 page segments from 350 pages and 832,193 characters. Twelve representative pages were visually checked.

### Formal database delta

| Metric | Before | Added | After |
|---|---:|---:|---:|
| All documents | 239,179 | 407 | 239,586 |
| Policy-source records | 1,054 | 0 | 1,054 |
| Ministerial written answers | 235,420 | 404 | 235,824 |
| Ministerial written statements | 2,705 | 3 | 2,708 |
| Text segments | 3,622,039 | 1,398 | 3,623,437 |

The 1,398 segments comprise 243 saved-payload repair segments, 340 OCR page segments and 815 segments from new records. The 407 manifest records all have formal enumeration and content linkage. Duplicate `(source_id, external_id)` groups remain zero. Segment semantics remain separate: 447 question-context segments, 608 answer government-response segments and 3 statement government-response segments; no question context was fabricated for statements.

### Distribution, coverage and QA

- Refreshed annual, quarterly, year-month, decade, department-composition and categorical source-month coverage outputs once against the final read-only snapshot. All time tables reconcile to the three genre totals and the database size/mtime remained unchanged during reporting.
- Coverage now records volume 200 as 321/322 recovered, January 1988 as an evidenced recess boundary, two unresolved 2005–2010 answer targets, the unresolved 2004-Q4 Commons seam, and the unchanged 2010–2014 index/page queue. Indexes, pages, candidates, items and files are never summed as missing documents.
- All four refreshed figures passed source-data preflight, panel alignment, 5.5 pt PDF text-floor checks, strict rendered-collision audit and final visual inspection.

### Deliverables

- [Concise targeted repair report](../work_packages/M1_source_access/07_historical_government_acquisition/targeted_gap_repair/reports/government_targeted_gap_repair_report.md)
- [HTML summary](../work_packages/M1_source_access/07_historical_government_acquisition/targeted_gap_repair/reports/index.html)
- [Repair ledger](../work_packages/M1_source_access/07_historical_government_acquisition/targeted_gap_repair/repair_ledger.csv)
- [Queue reconciliation](../work_packages/M1_source_access/07_historical_government_acquisition/targeted_gap_repair/reports/queue_summary.csv)
- [Final database delta](../work_packages/M1_source_access/07_historical_government_acquisition/targeted_gap_repair/reports/final_delta_check.csv)
- [Final verification](../work_packages/M1_source_access/07_historical_government_acquisition/targeted_gap_repair/reports/final_verification.json)
- [Refreshed distribution and coverage](../work_packages/M1_source_access/07_historical_government_acquisition/targeted_gap_repair/reports/final_distribution_coverage/government_corpus_distribution_coverage_report.md)

Residual blockers are external access restrictions or source-structure ambiguity and remain checkpointed. The repaired corpus still does not establish continuous 1988–2026 Commons coverage or complete historical UK government-policy coverage. Proposal, cleaning, vectorisation and model analysis were not changed or run. Actual effort was not supplied and is therefore not recorded.


## 2026-09-22 — Decision review: residual gaps after targeted repair

- Read the repair report, queue summary, refreshed coverage report/month table and original 06 failure export. No database writes, downloads, repairs or model work were performed in this review.
- The largest remaining acquisition gaps are the 2004-10-05..12-31 Commons seam (unknown denominator) and the 2010-05-01..2014-09-11 answer tranche (20 unresolved indexes; 225 failed and 212 unrequested known pages). The known-page acquisition rate is 626/1,063 = 58.89%, not population/document coverage. Unrequested pages cluster from November 2013 onward; other page/index failures are spread across the tranche.
- Small residual cases are Asda (2006-07-12), Companies House (2007-09-17), Self-regulating Bodies (1991-12-03), and one unresolved 2010 cross-date statement container. These have distinct attribution/availability/identity issues.
- Original 06 exports retain 25 content objects without usable text: 3 access denials, 1 HTTP/DNS failure, 14 needs_ocr, 2 extraction failures and 5 unsupported formats. These are distinct from the four historical PDFs successfully OCRed in the repair. Historical policy-population coverage remains unknown outside enumerated GOV.UK organisation tags.
- Official research finding: the Commons Hansard team's 1 May 2026 post describes migration gaps in October 2004–May 2006 and the availability of legacy Publications and TheyWorkForYou XML material. This supports evaluating a traceable alternative, not claiming every missing target is available: https://commonshansard.blog.parliament.uk/2026/05/01/historical-hansard-bridging-the-gaps/
- ParlParse documentation describes Commons written-answer XML from the 2001 parliament, separate question/reply elements, speaker IDs and original Parliament URLs, plus written-statement data and file-level/rsync access: https://parser.theyworkforyou.com/hansard.html . Exact required files, permissions and target coverage have not been tested in this review. Recommended next decision is a bounded mirror feasibility check against already held official records and missing dates before targeted ingestion; do not treat mirror copies as new independent documents.
- Reporting-only inconsistencies noted: the refreshed coverage narrative still refers to two gap statement candidate anomalies and later nine candidate details as future work, although current tables resolve these to one outstanding container. These sentences should follow the current repair ledger; no database recount is implied.


## 2026-09-22 — Dai decision: historical coverage first; mandatory fifth figure

- Dai prioritised historical coverage over distribution and modern corpus growth. Early policy publications require alternative-source work; recovering ministerial answers does not replace policy-publication coverage. Stop expanding modern data in this tranche.
- Records with inseparable mixed text or unreliable attribution should be excluded from the usable corpus, retaining raw evidence and the exclusion reason. Access failures remain alternative-retrieval targets rather than ambiguity exclusions. No database dispositions were changed in this decision window.
- Added the approved decision in `docs/decisions/2026-09-22-coverage-first-historical-gap-recovery.md` and the revised execution handoff in `docs/handoffs/2026-09-22-coverage-first-historical-recovery.md`.
- Dai additionally requires Figure 5 in future summaries: full-study-period monthly/quarterly coverage from the study start to the actual acquisition endpoint. Show three genres separately, preserve unknown/partial/blocked/zero states, and distinguish coverage from record-count distribution. Quarterly display must not conceal unresolved months; numeric rates require explicit known denominators. Include monthly source data and render a readable final chart once at the end of the recovery tranche.
- Only decision, handoff and project-log files were changed. No collection, database changes, chart generation, proposal revision or model work was performed.


## 2026-09-22 — Historical coverage recovery completed

### Bounded acquisition and identity results

- Continued from the targeted-repair baseline in the sole formal 06 DuckDB. A single pre-write recovery copy is retained at `07_historical_government_acquisition/historical_coverage_recovery/recovery/fear_temperature_government_content.before_commons_parlparse_targeted_gap_recovery_20260922_v1.duckdb`. No modern expansion, full smoke replay, full-database hash rerun, proposal change, cleaning, vectorisation or model analysis was performed.
- Froze 388 distinct target dates from the 2004-Q4 Commons seam, the 2010–2014 failed-index/page/unrequested queues and the named Companies House access failure. A bounded rsync listing found 816 relevant `wrans`/`wms` XML files on 373 dates; 15 dates had no file of either requested kind and were kept as unknown rather than zero.
- Downloaded exactly the 816 enumerated XML files through ordinary HTTPS. All returned HTTP 200 parseable XML; per-file request URL, final URL, timestamp, MIME, hash and fetch metadata are retained. There were no 403/429 responses, failed files or host-stop leftovers, and no mirror-wide clone was made.
- Parsed 10,853 in-scope derived records after correcting one pre-ingestion department-normalisation mismatch (`ENVIRONMENT FOOD AND RURAL AFFAIRS`). Of these, 2,405 mapped to records already in 06, 8,448 were genuinely new stable identities and zero were duplicate mirror representations. A second bounded check prevented the named 2007 Companies House date from expanding into unrelated same-day DEFRA targets.
- Companies House was recovered as the exact BERR record. Asda remains excluded because its saved text and department attribution cannot be separated reliably. `Self-regulating Bodies` remains excluded for mixed attribution, and the unresolved cross-date statement container is not inserted as a statement. Four evidence rows represent these three substantive exclusion cases; none was inserted by this recovery.
- Recovered one exact early policy publication absent from 06: *Biodiversity: the UK action plan* (25 January 1994, Cm 2428, ISBN 0101242824). The official GOV.UK Content API record, landing page and 194-page PDF were saved. Text extraction yielded 12,822 source-line segments across 188 text-bearing pages; the six no-text pages were visually verified as two blanks and four image-only globe separators. This single item does not establish a predecessor-policy population denominator.

### Formal database delta and provenance

| Metric | Before | Added | After |
|---|---:|---:|---:|
| All documents | 239,586 | 8,449 | 248,035 |
| Policy-source records | 1,054 | 1 | 1,055 |
| Ministerial written answers | 235,824 | 8,405 | 244,229 |
| Ministerial written statements | 2,708 | 43 | 2,751 |
| Text segments | 3,623,437 | 44,838 | 3,668,275 |

- Parliament records were committed in 17 source-internal chunks (sixteen × 500 and one × 448); the policy record was a separate eighteenth commit. Every progress line was printed after successful `COMMIT`. Each chunk added exactly its source-row count; no `ON CONFLICT DO NOTHING` skip was counted as new.
- The 8,448 Parliament records link to 398 acquired XML parent files used by at least one new identity. Their per-record JSON is explicitly marked as derived and retains the original Parliament URL and source locator. The database does not fabricate per-record HTTP/XML requests. The policy record links to its real landing-page and PDF fetches.
- New Parliament text contains 8,439 question/context segments, 23,097 answer-government-response segments and 480 statement segments. Question/context is retained for evidence but excluded from government-response counts.
- Formal reconciliation found all 8,448 expected mirror IDs and the policy ID present, zero duplicate `(source_id, external_id)` groups, zero duplicate canonical URLs, zero orphan text segments and zero orphan voice attributions. All 8,448 mirror records retain original Parliament URLs.

### What the recovery closes — and what remains open

- In the 2004-10-05..12-31 seam, `wrans` files exist for 39/43 target dates and `wms` files for 39/43. The recovery added 1,930 answers and 43 statements. Eight date × genre units across five distinct dates have no matching file and remain unknown; they are not eight missing documents.
- In the 2010-05-01..2014-09-11 answer gap, eight of the 20 failed date indexes now have matching XML and 12 remain without a matching file. Every date represented by the original 225 failed page targets and 212 unrequested page targets has matching alternative XML and was parsed for the approved departments; the original page units are preserved and are not equated with recovered record counts. This tranche added 6,474 answers.
- Across all bounded mirror targets there are 431 date × genre units: 411 complete and 20 unknown (16 answer units and 4 statement units). Download failure, parse failure and unrequested-after-stop counts are all zero. These units remain distinct from the 816 files and 10,853 parsed records.
- Early policy coverage for 1988–2009 remains population-incomplete. The normal UK Government Web Archive route was access-blocked, catalogue evidence is not full text, and the exact 1994 recovery does not justify a historical completeness rate.

### Distribution, coverage and figure QA

- Refreshed distribution and coverage exactly once after the final commit. Annual, quarterly, monthly and decade totals reconcile to 1,055 policy records, 244,229 answers and 2,751 statements. The report read the database in read-only mode and its size/mtime stayed unchanged during generation.
- Added monthly and quarterly coverage tables for every period from 1988-01 through the 2026-09-21 cutoff. Unknown, blocked, partial, unrequested and confirmed-zero states remain categorically separate; document counts are not used as coverage percentages.
- Added Figure 5, `Government corpus coverage over time`, with separate policy/answer/statement quarterly and monthly panels. The final 182.9 mm figure passed strict source preflight (21/21), five panel-alignment comparisons, the 5 pt PDF floor (minimum 6.2 pt), strict rendered-collision QA and final visual inspection.

### Deliverables

- [Final Markdown report](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/historical_coverage_recovery_report.md)
- [Concise HTML report](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/index.html)
- [Historical gap register](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/historical_gap_register.csv)
- [Alternative-source register](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/alternative_source_register.csv)
- [Exclusion ledger](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/exclusion_ledger.csv)
- [Recovery progress by source and unit](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/recovery_progress_by_source.csv)
- [Monthly coverage status](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/monthly_coverage_status.csv)
- [Quarterly coverage status](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/quarterly_coverage_status.csv)
- [Target-date coverage outcomes](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/target_date_coverage_outcomes.csv)
- [Incremental ingestion reconciliation](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/incremental_reconciliation.json)
- [Refreshed distribution and coverage](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/final_distribution_coverage/government_corpus_distribution_coverage_report.md)
- [Figure 5](../work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/figures/05_government_corpus_coverage_over_time.png)

The usable corpus has materially improved historical coverage but still does not establish a continuous or complete UK-government series from 1988 to 2026. The next decision should focus on the 20 unknown date × genre units and independent predecessor-policy catalogues rather than additional modern volume. Actual effort was not supplied and is therefore not recorded.


## 2026-09-23 — Read-only temporal reference availability

- Dai requested a direct answer to whether every month/quarter has reference material. Read the authoritative 06 database in read-only mode and joined actual non-empty text linkage to the latest coverage tables. No collection, database mutation or chart redesign was performed.
- All 248,035 records have some linked non-empty extracted text; this is not full-document completeness, cleaned usability or climate relevance. Policy records used content-object/version/segment links; ministerial records used voice-attribution/segment links, without a new attribution audit.
- At least one series has text in 434/465 months and 155/155 quarters. Policy: 229 months/98 quarters; answers: 421/155; statements: 257/96. All three series coexist in 198 months and 88 quarters. Listed all 31 wholly empty months in the new report. Quarterly presence does not imply all constituent months are populated.
- Early policy remains sparse: 0 records in 1988–1992, 7 records across 7 months in 1993–1999, and 83 records across 44 months in 2000–2009. Unknown enumeration can coexist with actual texts (e.g. November 2004 answers: 882).
- Delivered README and monthly/quarterly/annual/empty-month CSVs under `work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/temporal_reference_availability/`. Figure 5's acquisition-evidence status must be explained separately from this reference-presence measure.


## 2026-09-23 — Three-period monthly stacked chart and early-policy plan

- Dai requested all records stacked by month in three chronological rows, then specified an English-only landscape PNG matching project figures. Delivered 1988–2000 / 2001–2013 / 2014–2026-cutoff panels, shared linear y scale, explicit zero-month shading and all 465 months. Counts sum to 248,035; period totals are 108,510 / 70,609 / 68,916 and empty-month counts 23 / 6 / 2.
- Final PNG: `work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/temporal_reference_availability/figures/monthly_government_records_landscape.png`. Source CSV/script and editable PDF/SVG retained. All-English labels, 5400×3000 pixels, 300 dpi. Alignment/text/collision checks passed and visual inspection completed; no data mutation.
- Prepared `docs/handoffs/2026-09-23-early-policy-catalogue-and-originals.md`: prioritise 1988–1999 policy catalogues/originals, then 2000–2009, with verified bibliographic seed titles and alternative full-text routes; keyword seed examples do not define an exhaustive denominator.
- Found a material date-basis caveat: the existing policy record Securing the future is dated 2011-03-25 using GOV.UK first_published_at, but its attached pb10589-securing-the-future-050307.pdf is the 2005 strategy. The plan now starts with original-date versus webpage-date review, preserving both and their evidence. Current figures retain the stored date and disclose the limitation. No dates, records, raw metadata or proposal were changed.


## 2026-09-23 — Dispatched zero-month recovery task

- Dai explicitly asked this decision window to send the execution task. Sent the bounded instructions to the existing task “采集政府正文与附件” (01a0c28b-466f-7a23-b28c-0d66628f6a28).
- Prioritise the 31 wholly empty months identified in the latest monthly stacked chart, with per-genre calendar/catalogue verification, original-policy versus webpage-date checks, alternative early-policy originals and incremental recovery. Preserve evidenced zeros/unknown denominators instead of forcing every month to have records.
- Preserve ambiguous-record exclusions, original metadata and stable identities; distinguish date reassignment from genuinely new documents. No modern volume expansion. Required final output is a per-month before/after ledger, date evidence, coverage updates and one refreshed English landscape chart. No acquisition or database mutation was executed in this decision window.


## 2026-09-23 — Corrected execution routing after Dai review

- Dai reported that the zero-month follow-up had not been correctly executed. The target task's previous turn was completed/idle; the screenshot showed a forwarding acknowledgement and the project log contained no zero-month execution outcome. The previously reported +8,449 documents belongs to the older recovery tranche, not this follow-up.
- Sent corrective instructions to the existing acquisition task (01a0c28b-466f-7a23-b28c-0d66628f6a28): execute locally rather than re-dispatching; first create the 31-month, three-genre ledger in `07_historical_government_acquisition/zero_month_policy_recovery/`; then perform date-evidence review and bounded policy recovery under the already authorised scope.
- Completion evidence must be actual new ledger/results, per-month before/after, separately counted date corrections and new records, and explicit unresolved months. An active thread or successful message delivery is not proof of work completed. No new corpus recovery is claimed by this log entry.


## 2026-09-23 — Zero-month and early-policy recovery audit completed

### Execution and formal-database state

- Executed the corrected follow-up locally in the collection task under `07_historical_government_acquisition/zero_month_policy_recovery/`. The formal 06 DuckDB was opened read-only; its modification time did not change. Counts remain 248,035 documents, 1,055 policy records, 244,229 written answers, 2,751 written statements and 3,668,275 text segments.
- No evidence-sufficient new policy original was acquired, so the current tranche made zero database writes and added zero documents or text segments. Catalogue records, bibliographic previews, excerpts, physical-holding records and shorter summaries were not represented as recovered full text.
- Created the required 93-row ledger (31 completely blank months × 3 genres). Every before/after record count is zero. All 62 answer/statement genre-month rows remain confirmed zero within the already enumerated Commons scope; calendar evidence supplies recess/dissolution context but does not replace enumeration.
- Within the 31 all-series-zero months, 29 policy months retain an unknown predecessor-department denominator and April–May 2015 are confirmed zero only within the frozen current-DEFRA GOV.UK route. The known Cm 1200 policy target is in September 1990, which is outside the 31 completely blank months because seven written answers exist that month.

### Original-date review and bounded source outcomes

- Reviewed five already stored official policy PDFs while preserving their stable document/content/version IDs and GOV.UK stored dates. Three have independently visible month evidence and enter the versioned research-date view: *Securing the Future* → 2005-03, *Working with the Grain of Nature* → 2002-10, and *Conserving Biodiversity: the UK Approach* → 2007-10.
- Two further originals support only a year: *England Biodiversity Strategy: Climate Change Adaptation Principles* → 2008 and *United Kingdom Overseas Territories Biodiversity Strategy* → 2009. They are deliberately withheld from exact-month reassignment; asset filenames and PDF creation metadata were not used to invent months or days.
- Verified catalogue/date evidence for six bounded command-paper targets. *This Common Inheritance* (Cm 1200) is a known September 1990 policy gap, but the checked Internet Archive scan is access-restricted. Cm 2426, Cm 2427 and Cm 4345 remain catalogued but not acquired. The Cm 4913 UK Government Web Archive route returned an HTTP 405 WAF/captcha page and was stopped without bypass or repeated pressure. The 17-page UNFCCC item and a third-party Cm 4913 transcript were excluded as substitutes for the full command papers.
- The three exact-month corrections land in months that already held other records; therefore 0 of the 31 completely blank months became non-zero. The research-date chart contains 248,033 exact-month records, with the two year-only policy records explicitly withheld rather than silently assigned.

### Deliverables and checks

- [Recovery report](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/reports/historical_coverage_recovery_report.md)
- [Concise HTML report](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/reports/historical_coverage_recovery_report.html)
- [31-month × three-genre ledger](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/month_recovery_ledger.csv)
- [Versioned research-date mapping](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/research_publication_date_mapping_v1.csv)
- [Early-policy target register](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/early_policy_target_register.csv)
- [Source evidence log](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/source_evidence_log.csv)
- [Actual acquisition manifest](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/actual_acquisition_manifest.csv)
- [Incremental reconciliation](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/incremental_reconciliation.csv)
- [Corrected monthly record view](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/reports/monthly_reference_availability_corrected.csv)
- [Updated monthly coverage state](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/reports/coverage_status_by_series_month_updated.csv)
- [English landscape monthly chart](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/reports/figures/monthly_government_records_research_date_landscape.png)
- [Updated Figure 5](../work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/reports/figures/05_government_corpus_coverage_over_time_updated.png)

The final numerical checks reconcile 93 ledger rows, 31 distinct blank months, five reviewed stable documents/content versions, three exact-month mappings, two year-only mappings, 248,035 stored records and 248,033 research-exact-month records. Both figures passed panel-alignment, rendered-collision and 5.5 pt PDF text-floor checks and were visually inspected. The next bounded route is institutional or official-library access by command number/ISBN; the remaining early-policy zeros cannot be labelled complete without an independent population denominator. Proposal, cleaning, vectorisation and model analysis were not changed or run. Actual effort was not supplied and is therefore not recorded.


## 2026-09-23 — Early-policy catalogue/originals continuation

- Continued the approved historical-policy tranche without repeating the zero-month parliamentary work or expanding modern material. The formal 06 DuckDB was read-only. Counts remain 248,035 documents, 1,055 policy-source records and 3,668,275 text segments; size/mtime and 264 stored monthly policy counts match the prior state. **New complete originals, database documents, and text segments: 0 each.**
- Bounded catalogue work added five named missing or scope-review policy candidates to the five prior command-paper seeds: Cm 2429 (1994 forestry), Cm 3040 (1995 waste), the 1997 UK second climate report, Cm 3587 (1997 air quality), and Cm 4548 (2000 air quality). This is not a complete historical denominator. The 1991 Forestry Commission statement remains separately scope-pending. Existing Cm 2235 and Cm 6467 identities were checked, not reimported.
- Official UK Parliament guidance establishes TNA copy requests and authorised ProQuest library access for older numbered Command Papers. NBS supplies catalogue identity, not a universe count or open original. The indexed UNFCCC 1997 PDF was readable to the search renderer, but its direct response was HTTP 200 HTML rather than PDF; the official Forestry Research annual-report URL returned HTTP 403. Previous archive WAF and restricted Internet Archive routes were not retried or bypassed. None was counted as acquired.
- Delivered [report](../work_packages/M1_source_access/07_historical_government_acquisition/early_policy_originals_20260923/REPORT.md), [target register](../work_packages/M1_source_access/07_historical_government_acquisition/early_policy_originals_20260923/catalogue_target_register.csv), [source-route register](../work_packages/M1_source_access/07_historical_government_acquisition/early_policy_originals_20260923/source_route_register.csv), [acquisition/exception ledger](../work_packages/M1_source_access/07_historical_government_acquisition/early_policy_originals_20260923/acquisition_and_exception_ledger.csv), [monthly before/after and gap states](../work_packages/M1_source_access/07_historical_government_acquisition/early_policy_originals_20260923/policy_month_before_after.csv), [period comparison](../work_packages/M1_source_access/07_historical_government_acquisition/early_policy_originals_20260923/policy_period_before_after.csv) and [precise library request list](../work_packages/M1_source_access/07_historical_government_acquisition/early_policy_originals_20260923/library_request_list.csv). No request was sent to a library; the next recovery step requires a lawful complete copy and edition verification. The 1988–2009 policy population denominator remains unknown.


## 2026-09-23 — Cross-region government-source coverage reconnaissance

- Opened a separate `08_cross_region_government_coverage` work package; the formal UK 06 database was read only and remained at 248,035 documents and 3,668,275 segments. No foreign records were added to it, and no proposal, cleaning, vectorisation or model work was undertaken.
- Systematically enumerated bounded official metadata rather than climate-keyword hits: US Federal Register EPA/Energy Department × final/proposed rule × 1994–2026-cutoff (132/132 partitions; 33,560 stratum hits; 33,544 unique canonical document URLs), Australian DCCEEW current all-publications listing (83/83 pages; 823 cards, 821 unique landing URLs; two cards after the fixed cutoff), and the Irish Oireachtas all-department written-question monthly index (171/171 months from July 2012; 684,809 indexed questions; 19 verified-zero index months). These are **different units**, not a combined government-document count. Irish index counts are not ministerial answers or an environment-department subset; Australian landing pages are not verified original policy files.
- Preserved request URL/final URL/status/MIME/time/hash and raw response for bounded official requests. The Australian page-0 cached response time was corrected to the saved HTTP Date header and labelled approximate; script reuse time is separate. Federal Register `document_number` alone collides in two dated cases, so URL+date remains the record boundary; 16 cross-agency duplicate hits are not 16 new documents.
- EU CELLAR and EP API entrances were checked, but institution/genre-filtered denominators were not enumerated. Ireland gov.ie and NZ Parliament remain entrance-only. Current NZ MfE publications returned a challenge page and Australian Parliament questions entry returned 403; neither was bypassed or called a zero. The chosen US API does not cover 1988–1993, and the current Australian department listing does not prove predecessor-period completeness.
- Recorded four identity relationship classes separately: 18 exact repeated metadata-URL groups (16 US cross-stratum + two AU repeated cards), zero verified cross-host mirrors, two near-duplicate relationship candidates with distinct dated US URLs, and zero **verified** cross-jurisdiction same-event/distinct-voice pairs in this metadata tranche. No publication-file hashes were obtained; response-body hashes do not prove publication identity. Shared events, titles or months are not deduplication grounds.
- Delivered [English report](../work_packages/M1_source_access/08_cross_region_government_coverage/reports/coverage_report.md), [HTML](../work_packages/M1_source_access/08_cross_region_government_coverage/reports/coverage_report.html), [source register](../work_packages/M1_source_access/08_cross_region_government_coverage/reports/source_register.csv), [monthly status](../work_packages/M1_source_access/08_cross_region_government_coverage/reports/monthly_source_coverage_status.csv), [identity ledger](../work_packages/M1_source_access/08_cross_region_government_coverage/reports/identity_relationship_status.csv), [record examples](../work_packages/M1_source_access/08_cross_region_government_coverage/reports/record_identity_examples.csv), and [coverage matrix](../work_packages/M1_source_access/08_cross_region_government_coverage/reports/cross_region_coverage_matrix.png). The next tranche must freeze EU/NZ/Irish-government institutional series and document boundaries before claiming common-window coverage. Actual effort was not supplied and is therefore not recorded.


## 2026-09-26 — Ireland/EU/NZ source opportunity and sufficiency review

- Recomputed existing 08 evidence: EU has 50,578 summed month-level DISTINCT-Work counts (465 months; 464 positive); Ireland has 684,809 all-department question-index records (171 months; 152 positive); NZ has 536 currently answered Climate Change question-index records in 2025. These units are not downloadable unique answer/full-text counts.
- The Irish September 2012 departmental pilot has 357 question-linked answers but 280 distinct full answer strings. Repeated strings were flagged as relationship/weighting candidates; no records were deleted or altered.
- Verified official API/data-model documentation and NZ early-policy/ministerial archive routes. NZ first national communication has a September 1994 cover and a 1995 inserted summary; retrospective reference to 1988 does not establish a 1988 publication.
- Proposed source-specific collection priorities and explicit pilot sufficiency gates, distinguishing retrieved paragraphs, independent parent records, relevant parents per bin and comparable time points. Numerical planning targets are provisional, not confirmed power calculations or approved changes to the analysis plan.
- Saved [English research memo](research/2026-09-26-ie-eu-nz-source-sufficiency-review.md). No bulk acquisition, database changes, proposal changes, model analysis or Git operations in this review.


## 2026-09-26 — Approved RQ1/RQ2 priorities and EU early coverage

- Dai prioritised RQ1/RQ2, principal monthly coverage and two-year pre/post-event coverage. EU institutional texts are approved as the next early-coverage priority; further Ireland/NZ acquisition is deferred. Current US/Australia work continues.
- Recorded [decision and reporting rules](decisions/2026-09-26-rq1-rq2-eu-coverage-and-record-units.md): EU stays an independent supranational series; source/country substitutions do not fill national gaps. Every month needs an explicit evidence state; true zeros, unknown coverage and insufficient observations remain distinguishable.
- The event coverage audit uses 24 full months before, the event month separately, and 24 full months after. This is a coverage convention, not a power guarantee or a final model specification. Cutoff remains 2026-09-21, with September partial.
- Final usable-record reporting must count unique parent publications/replies/statements separately from metadata targets, file versions, attachments and extracted segments. Relevant-parent counts remain unassessed until relevance validation; excessive segmentation cannot increase the independent sample size.
- This turn records a scope decision and execution alignment only; no additional EU bulk collection, database mutation, proposal edits or Git operations occurred.


## 2026-09-26 — US/Australia government-source acquisition (ongoing)

- Created the source-specific US/AU acquisition package with a machine-readable filter contract, ordinary-access fetch checkpoints, a versioned DuckDB working copy, parent-based monthly ledgers and a 49-bin Paris Agreement coverage candidate. The UK 06 baseline was not written; its SHA-256 remained `d6c285649048f7910810630dc3da8479efcca7c38e35f903a5d20eae20e90465` in the 12:46 UTC audit.
- Imported exactly 33,544 deduplicated US Federal Register rule/proposed-rule metadata parents and 821 Australian DCCEEW catalogue landing candidates. The 16 US cross-agency overlaps are two associations on one parent. AU catalogue CMS times were not promoted to original dates.
- As of the 12:46 UTC committed reconciliation, 1,136 US raw-text files were downloaded and hash-verified, 600 were versioned and source-extracted/cleaned in the working database, and four previously saved AU landing/PDF pairs contributed eight hash-verified versions. AU has two originals with month/day precision, two with year-only precision and 817 catalogue candidates with unknown original dates. Subsequent bounded US retrieval remains in progress; current counts are in the package's regenerated report rather than fixed by this log entry.
- Captured ordinary DCCEEW request timeouts on both a recent and the oldest CMS-listed candidate; the official predecessor archive link returned an access challenge. These gaps remain unknown, not zero. The US 1988–1993 scanned-print route has no frozen agency/genre denominator and is separate from the 1994+ API series.
- Initial quality audit verified 608 new content-version hashes, zero canonical duplicates, zero orphan segments, zero unmapped cleaned segments, 11 AU attachment associations and unchanged UK baseline. US source extraction changed from line segments (v1) to a whole-document source segment (v2) for later batches to control storage growth; original bytes and clean-to-source line-range maps remain preserved. Segments are not independent parent records.
- Figure 5, monthly source-specific coverage and the 49-bin event audit were generated for RQ1/RQ2 preparation. Relevant-parent classification, model inference, EU acquisition and proposal changes were outside this tranche. No Git commit or push was made. Actual effort was not supplied and is not estimated.
- A supervised 500-request acceptance block finished at 13:19 UTC: 1,849 US texts hash-verified, 1,610 US parents with versioned and cleaned text, and eight AU versions. The audit verified all 1,618 new content versions, with zero hash/size mismatches, orphan segments, unmapped clean segments, or CMS-imputed AU months; the UK baseline SHA-256 remained unchanged. The 1994–2002 target remains 10,237 parents, and the full 1994–cutoff target remains 33,544, so this is partial acquisition.
- GovInfo's official annual cumulative Federal Register indexes for 1988–1993 were added as the pre-1994 finding-aid route. They have not yet been enumerated by EPA/DOE and rule/proposed-rule at document level; those years stay `unknown`, never zero. A separate single-writer supervisor resumed the remaining fixed US series at 13:22 UTC with per-block reports and access/storage stop conditions. Its current state is in `09_us_au_government_acquisition/checkpoints/supervisor_state.json`.


## 2026-09-26 — Continue US/AU and activate EU acquisition before overall coverage analysis

- Dai requested completion of real US, AU and EU acquisition before another overall coverage analysis. Reviewed the 09 snapshot: 33,544 US metadata parents, 1,849 downloaded bodies, 1,610 inserted US parents, 821 AU candidates and four verified AU originals; these are intermediate results.
- Inspection found full audit/figure/report generation inside every US 500-record supervisor cycle and an AU ingestion path restricted to four existing originals. The execution handoff requires batch-level checks during continuation, one final consolidated coverage pass, and a general AU landing-to-original ingestion path. The log showed subsequent US download progress; process health must be checked before restarting, not inferred solely from the running checkpoint.
- Prepared [US/AU/EU completion handoff](handoffs/2026-09-26-us-au-eu-acquisition-completion.md), activating EU Work enumeration and English content acquisition, keeping source-specific scope and counts, and retaining explicit historical/access gaps. Ireland/NZ remain deferred. No collection completion is claimed by this coordination entry.

## 2026-09-27 — Real-source acquisition checkpoint (in progress)

- The 33,544-parent US EPA/DOE final/proposed-rule metadata queue remains frozen. All 10,237 selected 1994–2002 bodies are now verified and ingested, including 19 raw-text 404/410 objects recovered from official GovInfo HTML with their original failed checkpoints retained. The 2003–cutoff route returned HTTP 429 after 56 new bodies; after an approximately one-hour cooldown it resumed with ordinary HTTP 200 responses. At 01:49 UTC two additional 500-parent blocks had equal new-download and new-ingestion counts, bringing the later-year committed subtotal to 1,056 and the full selected-series subtotal to 11,293. Collection continues; no full-series completion is claimed.
- The EU CELLAR frozen `COM`/`cdm:act_preparatory`/English Work enumeration reconciled all 465 months and 50,578 globally unique Works. All 465 English WEMI months were audited, with 47,472 Works having an Item link and 3,106 without one. At 01:59 UTC, 6,522 original Item streams passed the independent byte/derivative audit with zero issues; 67 scan-only PDFs had page-aligned OCR candidate sidecars. The independent EU stage had 6,498 versions through 1996; downloaded Items in the current month may temporarily precede stage insertion. OCR remains subject to layout review.
- The exact frozen EU query returns zero Works for 2024-08. A saved official CELLAR diagnostic for the 2024-08-09 COM proposal CELEX 52024PC0999 found the adjacent type `cdm:proposal_decision_implementing_ec`. This confirms a class boundary in the frozen denominator, not a zero across all Commission proposals. The denominator was not silently expanded.
- The Australian current catalogue still has 821 landing candidates. Four earlier official pairs and five newly saved official landings account for 17 saved AU content versions in the 09 DB; 807 catalogue candidates remain individually unvisited. A later bounded current-host HTTP/1.1 HEAD check again timed out, while one predecessor-domain PDF returned HTTP 200. The predecessor route remains a separate unenumerated source. No unvisited candidate is treated as absent.
- The 1988–1993 US GovInfo annual indexes and seven full issue originals remain separate from the 1994+ API series. The 4,844 index locator tokens are page clues, not a rule-document denominator; six EPA/DOE rule samples have independent source boundaries. Further scans need substantially more storage. The current [cross-source acquisition snapshot](../work_packages/M1_source_access/09_us_au_government_acquisition/reports/acquisition_progress_snapshot.md) and source-specific ledgers distinguish committed bodies, pending requests and access exceptions. No proposal/model edits, commit or push were made in this run.

### Later 27 September checkpoint (still in progress)

- By 03:46 UTC, 12,399/33,544 US selected parents had verified, inserted bodies: 10,237 in 1994–2002 and 2,162 in 2003 onward. All 21 observed raw-text 404/410 objects had separately verified GovInfo HTML originals. A 2005-03 raw-text HTTP 429 stopped one batch; after roughly one hour, the same object returned HTTP 200 and the saved failure was retained in its request-attempt history. The 2005 continuation is running, so these counts are a committed checkpoint, not a terminal total. The latest full 09 integrity audit found 12,416 US/AU content versions with no hash or size mismatch and the UK baseline unchanged.
- By 03:44 UTC, the EU Item-byte audit checked 8,222 downloaded originals, 75 scan-only PDFs and 72 OCR sidecars with zero integrity issues. Three newer scans subsequently received page-aligned OCR sidecars. The 50,578-Work denominator, 3,106 no-English-Item cases and frozen class boundary remain unchanged. EU monthly downloads and staging continue.
- All 807 previously unvisited Australian catalogue landings received one read-only official-page query and the 68 initial reader errors/omissions received one smaller-batch retry. The reconciled observations show 778 opened official pages, 21 reader errors and eight omitted results, with 417 newly identified first-PDF URLs. The [Australian outcome ledger](../work_packages/M1_source_access/09_us_au_government_acquisition/reports/au_candidate_outcomes.csv) now has one state for each of 821 frozen candidates; the read-only URL observations add no verified raw original, date or independent Work. The [web-observation audit](../work_packages/M1_source_access/09_us_au_government_acquisition/reports/au_web_observations_audit.json) found zero URL or route mismatches. Nine parent landings still account for the 17 saved AU content versions.
- Internal free space was roughly 20–21 GiB and the optional T7 Shield volume was not mounted at this checkpoint. EU downloads have a 5 GB source-supervisor floor; no external-disk writes or historical full-issue expansion occurred. No proposal/model edits, commit or push were made.

### 05:28 UTC source checkpoint (still in progress)

- A new official FederalRegister.gov raw-text HTTP 429 at 05:18 UTC stopped the 2007-02 batch after 407 successful bodies. All 407 were ingested before the supervisor stopped. The committed US total is **14,306/33,544** parents with body (10,237 early and 4,069 later); the 09 audit verified **14,323 US/AU content versions**, zero hash/size or segment-mapping problems, and the unchanged UK baseline. The 429 checkpoint has no `Retry-After`. A bounded one-hour polite resume is scheduled from the failed response time through `us_polite_resume.py`; this is not completion evidence.
- The independent EU byte audit at 05:28 UTC rehashed **10,483 downloaded Item originals**, found 77 scan-only PDFs with 77 page-aligned OCR sidecars, and reported zero integrity issues. One failed checkpoint is for a nonselected >100 MB PDF/A; its selected official ordinary-PDF alternative is saved. The Work disposition ledger still has 50,578 unique Works, including 3,106 without English Item links; text extraction and OCR candidate status do not establish relevance or final body usability. EU Item acquisition and staging continue into late 2001.
- One published Federal Register 1988 archive slice returned a valid 3.8 MB PDF `HEAD`, but a guessed arbitrary page-range key returned S3 403. The separate pre-1994 rule-document denominator and article boundaries remain unresolved; the seven saved full issues and six bounded rule samples are not inflated into a complete series.

### 06:52 UTC source checkpoint (still in progress)

- The first scheduled US retry was mistakenly launched inside the restricted local sandbox and produced three `NameResolutionError` checkpoints without reaching FederalRegister.gov. The wrapper stopped correctly on a non-429 failure. A network-enabled restart retrieved the original 2007-02-27 `E7-3311.txt` as verified HTTP 200 and completed a full 500-download/500-ingestion block. The committed US total rose to **14,806/33,544**. The independent 09 audit verified **14,823 US/AU content versions**, zero hash/size mismatches and orphan/unmapped segments, and unchanged UK baseline SHA-256. The earlier 429 and local DNS failure remain in the object's attempt history. A further US block is running; no full-series completion is claimed.
- EU moved through 2002-09 and into 2002-10. The 06:45 UTC independent Item audit rehashed **12,129 downloaded originals** and 96 scan-only PDFs with 96 page-aligned OCR candidate sidecars, reporting zero issues. OCR sidecars added during live collection will be restaged only after the Item supervisor stops; source-layout and relevance review remain pending.
- A cooled, single HTTP/1.1 IPv4 `HEAD` retry of one official DCCEEW 2014 PDF at 06:38 UTC again timed out with zero response bytes. The apex host also redirects to that same unavailable current-host path. The 821-candidate outcome ledger remains complete, but most catalogue originals remain raw-file pending. No bulk current-host retry or external-disk write occurred.


## 2026-09-27 — Acquisition health check at approximately 07:10–07:15 UTC

- Dai requested a health check of the long-running US/AU/EU acquisition task. Read-only process, log, checkpoint and capacity checks show real progress: US checkpoint total 14,806 committed parents, with a subsequent 500-body fetch completed and ingestion progressing from 25 to 50 records during observation; one US supervisor and one child writer observed. EU had saved/inserted 12,470 versions by its 2002-11 checkpoint; after one read timeout it was performing OCR backfill in its separate staging DB before a bounded retry. No same-DB duplicate writer was observed in the sampled process snapshots.
- The US loop now uses incremental checkpoints and has removed full figures/audits from every batch, as previously requested. These observations establish activity, not a new whole-corpus correctness audit. System memory-pressure query reported 39% system-wide free memory; observed US writer RSS was approximately 1.1 GiB and CPU use reflected multiple active cores. No full DB hash or acquisition restart was performed.
- Main operational risk: filesystem reported about 19 GiB available at 98% capacity. Work packages 09 and 10 occupied approximately 7.3G and 13G; EU raw Items alone approximately 11G. The historical US full-issue route's existing estimate (~140 GB) does not fit current capacity. AU remains an acquisition bottleneck: most candidates have web-reader evidence rather than saved original bytes.
- Sent execution alignment to the active collection task: preserve at least 10 GiB plus expected transaction/OCR working space before new blocks, apply checks to active supervisor entry points, safely finish transactions and checkpoint if capacity is insufficient; estimate remaining storage before large historical scans, preserve originals, and avoid duplicate restarts or unapproved storage moves. This log records the request, not confirmation that the mitigation is already implemented.

### 07:23 UTC continuation checkpoint (still in progress)

- The in-flight US 500-parent block completed and committed in 25-parent DuckDB transactions at 07:20 UTC. The checkpoint now records 5,069/23,307 later-year bodies and 10,237/10,237 early-year bodies, or **15,306/33,544** selected US parents with ingested text. A watcher stopped the old supervisor only after the committed batch and before its next fetch. A single replacement supervisor started at 07:22 UTC with the revised **15,000,000,000-byte** pre-block floor; its first later-year fetch is running. No active transaction was interrupted. A full post-block integrity audit is still due.
- The EU Item supervisor resumed at 07:17 UTC with the same 15 GB floor and recovered the selected 2002-11 timeout object by an official HTTP 200 retry. The prior independent audit had verified 12,470 originals, 100 scan PDFs and 100 OCR sidecars with zero integrity issues; newer EU downloads are still being staged. The frozen 50,578-Work identity denominator and 3,106 no-English-Item cases are unchanged. This is a progress checkpoint, not an EU completion count.
- The actual shared-volume free space at 07:23 UTC was 20,534,692 KiB (about 19.6 GiB), despite the user's report of clearing close to 40 GB. The 15 GB floor leaves about 5 GB for additional bytes before both supervisors pause. Measured 2002 EU Items average roughly 91 KiB (1,699 Items), while sampled 1994–1998 Items average roughly 1.6 MiB; projecting the approximately 35,000 not-yet-requested English Items from those period-specific samples gives a very broad roughly 3–55 GiB raw-only range, not a storage forecast. Stage growth and OCR working space are additional. The separate 1988–1993 US full-issue route remains roughly 140 GB by its size sample, so it was not launched. No raw originals were deleted or moved, and no external volume was mounted or written.

### 07:52 UTC committed-batch audit (still in progress)

- The first US block under the restarted 15 GB floor downloaded and committed 500 more parents, bringing the selected-series total to **15,806/33,544** (10,237 early; 5,569 later). A read-only audit after the writer closed and before its following fetch finished verified **15,823 US/AU content versions**, zero file hash/size mismatches, zero orphan or unmapped new clean segments, zero duplicated canonical documents, and the unchanged UK baseline SHA-256. The next US fetch is running; these are committed snapshot values, not a completion claim.
- EU finished 2002-12 and proceeded through 2003-03 into 2003-04; the 2002-12 stage checkpoint was 12,760 versions, and 2003-01 was 12,874. The 114 verified 2003-01 Items averaged 214 KiB; this digital-period sample does not predict later PDF/A storage. A new 2003-03 scan without a text layer remains an OCR candidate pending a later safe sidecar pass. The frozen Work total is unchanged.
- A further 07:25 UTC single official DCCEEW 2014 PDF `HEAD` attempt timed out with zero bytes after 20 seconds; no bulk retry followed. The Australian candidate outcome ledger was regenerated after guarding against an empty attachment list being called verified: all 821 outcomes retained their prior counts, and the web-observation audit reported zero issues. The current-host raw-file route remains blocked for most candidates.
- A separate 07:53 UTC EU byte audit, safe during the downloader's next month, checked 13,141 saved originals, 121 scan-only PDFs and 100 existing OCR candidate sidecars with **zero integrity issues**. The 21 newly identified scans still need OCR sidecars and layout review in a later supervisor pause; one retained failed checkpoint is the nonselected oversized PDF/A with a selected ordinary-PDF alternative.

### 08:12 UTC transient local-proxy recovery (still in progress)

- EU stopped in 2003-05 after 41/150 selected Items because the local HTTPS proxy connection failed before any source response (`ProxyError`, HTTP status 0). It staged the 41 verified files and left the failed object as a retryable checkpoint. After a short pause, the stopped supervisor was restarted alone from 2003-05 with the 15 GB guard; the exact failed Item then returned HTTP 200 and its previous failure was retained in `.attempts.jsonl`. The queue is again moving. This was a transport interruption, not source refusal or a missing Work.
- The US fetch block spanning late 2008 to May 2009 logged one similar HTTP-0 proxy failure on 2009-02-04 `E9-2373.txt`, then continued to 500 attempts with subsequent HTTP 200 responses. Its verified downloads are being ingested; the one failed URL remains eligible for the next bounded fetch. No failed response is counted as a body.

### 08:34 UTC rate-limit and proxy checkpoint (still in progress)

- That US block committed **499** new parents, bringing the selected-series total to **16,305/33,544** (10,237 early; 6,068 later). Its next fetch retried the lone proxy-failed `2009-02-04/E9-2373.txt` and received an actual FederalRegister.gov **HTTP 429**. The supervisor stopped after a zero-ingestion reconciliation block; it did not count the failed object. `us_polite_resume.py --dry-run` set the earliest ordinary retry to **2026-09-27 09:23:47.965745 UTC** (one hour after the source response, no earlier `Retry-After` override), and the single network-enabled wrapper is waiting for that time. Its source supervisor retains the 15 GB floor.
- EU retried another 2003-05 HTTP-0 local-proxy failure after the stopped supervisor had staged 109/150 verified Items. The same selected Item returned HTTP 200 on restart, with its failed attempt retained. The restarted EU supervisor uses a 2-second request gap and the 15 GB guard. Repeated proxy failures are transport interruptions, not a source 403/429 or a completed Work; the latest state remains running. Shared-volume free space was about 19.5 million KiB at this checkpoint; no external volume was mounted.
- While the US queue waits on the official 429 cooldown, `report.py` reconciled 16,305 downloaded/inserted US parents and 17 AU content versions; 21 US raw-text 404/410s have separately verified GovInfo HTML fallback originals. The current per-parent exception CSV has the one US 429 and two Australian direct-host timeouts; other historical attempts remain in request histories. The post-block 09 audit independently checked **16,322 US/AU content versions**, zero hash/size mismatches, zero orphan/unmapped clean segments, zero canonical duplicates, and the unchanged UK baseline. This remains a partial snapshot.

### 09:14 UTC EU continuation and byte audit (still in progress)

- EU continued with a 2-second request gap through 2003-09 and staged **13,990** Item versions, then entered 2003-10. The bounded `eu_transport_resume.py` monitor was added to watch the single active Item supervisor; its dry run recognised `running` and it has not launched another writer. It may retry only a selected Item's checkpointed HTTP-0 transport error after ten minutes, at most five total restarts and fewer than three same-object transport failures; source HTTP responses, stage errors and storage stops terminate this wrapper. `manifests/transport_resume.jsonl` records decisions.
- The 09:13 UTC independent byte audit checked **14,000** downloaded originals, 127 scan-only PDFs and 100 existing OCR sidecars with zero integrity issues. Thus 27 saved scans still need sidecar OCR and layout review at a safe pause; extraction/OCR status is not a usable-body or relevance claim. One failed nonselected oversized PDF/A checkpoint remains retained with its alternate ordinary PDF saved.

### 09:25 UTC source-cooldown recovery (still in progress)

- The US polite-resume wrapper waited through the exact 09:23:47.965745 UTC eligibility time, rechecked the unchanged stopped supervisor state, and launched one network-enabled source supervisor. The first formerly limited `2009-02-04/E9-2373.txt` returned **HTTP 200**; its 55,101 saved bytes passed SHA-256 verification, and both earlier HTTP-0 local-proxy and source HTTP-429 attempts remain in `.attempts.jsonl`. The following requests reached at least 25/500 in the new block. The last *committed* US count remains 16,305 until this block is ingested.
- EU completed and staged through 2003-10, reaching **14,172** Item versions, and entered 2003-11. The 15 GB floor remains active for both source supervisors. The Australian raw-file barrier and pre-1994 US issue-storage barrier are unchanged.

### 09:54 UTC committed recovery block (still in progress)

- The US post-cooldown block downloaded and committed **500/500** parents, raising the selected-series total to **16,805/33,544** (10,237 early; 6,568 later). The next fetch has started under the same single-writer supervisor. A read-only audit after that block checked **16,822 US/AU content versions**, zero hash/size mismatches, zero orphan/unmapped clean segments, zero canonical duplicates, and unchanged UK baseline SHA-256. The formerly limited object is included only after its verified 200 response and committed insertion.
- EU completed every 2003 Item month and staged **14,541** Item versions through 2003-12, then continued into 2004-01 at a 2-second request gap. The latest independent EU byte audit at 09:13 had checked 14,000 originals with zero issues; OCR candidates and source relevance are still pending. The separate bounded transport monitor has not launched a duplicate writer.
- A further single exact-file `HEAD` on the official Australian 2014 PDF at 09:40 UTC, after more than two hours of cooldown, again timed out in 20 seconds with zero bytes. No bulk DCCEEW retry followed. The user was asked for a usable official-file route or saved original; the 821 candidate outcomes remain metadata/observation dispositions rather than full raw acquisition. `df` at 09:53 showed about 19.0 million KiB free (roughly 18.1 GiB); the 15 GB source guards remain active, and additional writable space was requested separately. No raw originals were deleted or moved, no UK/proposal edits, commit or push occurred.


### 27 September — clarify global temporal coverage objective

Dai clarified that the primary goal is cross-regional macro feedback to climate and warming, with contemporaneous international records contributing to pooled monthly coverage. The coordinator's prior framing of US acquisition mainly as enrichment relative to UK gap recovery was too narrow. US/EU/AU observations may close pooled temporal gaps while source-specific gaps remain documented. Country is a provenance and adjustment attribute, not a predetermined limit on the primary conclusions. RQ1 still requires separate government/media/public series; source composition, independent parent counts and event identity remain necessary to interpret pooled change. Continuous monthly presence supports an international-corpus coverage statement, with relevance, weighting and robustness assessed later. The decision is recorded in [global temporal coverage and macro feedback](decisions/2026-09-27-global-temporal-coverage-and-macro-feedback.md), and the previous coverage decision now links to this clarification.


### 27 September — prioritise authentic temporal and event evidence

Dai further clarified the shared collective knowledge/memory/culture perspective: collection priorities should ensure real event and primary-text evidence across study intervals and checkpoints, rather than exhaustive single-jurisdiction recovery. The [global temporal coverage decision](decisions/2026-09-27-global-temporal-coverage-and-macro-feedback.md) now records this criterion. Reporting should distinguish documented events, available primary texts and observed role-specific responses. Routine/low-attention periods and eligible-document denominators remain necessary; event-guided recovery does not authorise selecting only emotionally salient periods. Shared memory/culture remains a research perspective rather than a finding established by corpus aggregation.


### 27 September — project-wide scope correction and bounded verification

Dai identified repeated completeness/validation work as displacing the research objective. Updated the root README (including stale RQ2/RQ3), methodology, architecture entry point, decision index, US/AU/EU handoff and both active runbooks to follow [PROJECT_DIRECTION.md](PROJECT_DIRECTION.md). The primary completion question is pooled temporal/event evidence for macro feedback. Exhaustive national recovery, blocked Australian PDFs and the roughly 140 GB US historical full-issue route no longer gate pooled reporting or all downstream work. Keep new-record checks and one changed-tranche acceptance; repeat broad checks only for a concrete changed assumption or failure. Current source filters and historical evidence retain their meaning. This is a documentation/priority update; proposal and acquisition data were not rewritten.

### 27 September, 10:53 UTC — first committed pooled month × role snapshot

- After the next US 500-parent ingestion committed, the selected Federal Register series held **17,805/33,544** independently linked parent texts; the EU stage had **15,455** Item versions through 2004-06. Neither single-writer supervisor was restarted or duplicated. The 15 GB floors and ordinary request delays remain in force.
- Published one [pooled coverage snapshot](../work_packages/M1_source_access/09_us_au_government_acquisition/reports/pooled_month_role_snapshot_2026-09-27.md) and its [465-month × three-role ledger](../work_packages/M1_source_access/09_us_au_government_acquisition/reports/pooled_month_role_coverage_2026-09-27.csv), using a read-only builder against the committed UK/US-AU/EU databases. Government has dated source parents in 465/465 months and readable source parents in **458/465**; relevance is unassessed. UK alone has 423 readable months, EU adds 28, and US adds seven further months (2004–2010 August). Media and public corpus coverage has not been acquired or audited in these databases, so no three-role comparison is claimed.
- The independently dated Paris Agreement adoption candidate has government readable source text in **46/49** bins, with explicit gaps at **2014-08, 2015-04 and 2015-05**. Four additional government-readable month gaps are 2012-08, 2020-08, 2023-08 and 2024-06. The provisional 1997-12 Kyoto candidate has government text in all 49 bins, but event identity/response, relevance and media/public evidence remain unvalidated. The 1988 institutional anchor cannot have a full 24-month pre-window inside this study scope.
- Changed-tranche reconciliation found 17,805 US content versions mapped to 17,805 distinct US parents, zero orphan versions and zero acquired US bodies without extracted/cleaned parent status. EU source-text counting excluded 100 OCR review candidates, 29 scan-only Items and 27 HTML table-placeholder Works. No full-corpus rehash, all-source re-import, model run or figure rebuild was performed. This is a snapshot while the US/EU queues run; AU current-host access and the deferred US historical issue route remain source-specific limitations, not global reporting gates.


### 27 September — pooled temporal coverage and data-shape snapshot

A read-only calculation from the existing UK monthly ledger/06 database, the 08:34 UTC US monthly report, EU Work index and completed-month extracted-text dispositions gives **463/465** study months with government text across the included UK/US/EU sources. The two unobserved months in these snapshots are **2015-04 and 2015-05**. UK text alone covers 434 months; the cross-regional view supports 29 of its 31 absent months. Kyoto 1997 has 49/49 government text months in the 24+event+24 audit window; Paris 2015 has 47/49. This is source-text presence, not climate relevance, actual event response, media/public coverage or historical population completeness. The UK 06 database shape is 248,035 parents and 3,668,275 segments, with 244,229 ministerial answers. The EU and US queues remain live, so dated snapshots are preserved rather than declaring final coverage. See [report, plot and all-month CSV](research/coverage_snapshot_2026-09-27/README.md). No source data was downloaded, changed or re-imported for this calculation.

### 27 September — targeted 2015 source-text bridge

Dai selected the two remaining stored-text-absent government months, **2015-04 and 2015-05**, as the next bounded acquisition target. The 11:56 UTC read-only audit reconciled the broader **463/465** stored-text-presence count against the legacy parent-status-gated **458/465** count: five UK policy months have linked nonempty source text but stale acquisition status, so they are not additional missing-text targets. The next acquisition should use existing enumerated US/EU candidates and a predeclared source/genre definition that is traceable across months around the gap. Verify continuity and source composition over the existing 2013-12–2017-12 Paris window, with 2012–2019 as an extended metadata frame; do not cherry-pick two isolated documents or resume global enumeration solely to raise a month count. This is a coverage and comparability step, not relevance classification or an RQ1/RQ2 effect analysis. Preserve current US/EU single-writer, rate-limit and disk safeguards; report any source-series failure or unresolved month without substituting metadata for readable text.

### 27 September, 12:36 UTC — targeted EPA original-text bridge committed

- At the safe US checkpoint after the 11:27 FederalRegister.gov HTTP 429, stopped the waiting automatic-resume wrapper before it could compete for the 09 writer. Prespecified one frozen series: official Federal Register records whose agency strata include EPA and whose API genre is `final_rule`, with the original publication day as month. The existing 2012–2019 metadata frame contains 4,407 eligible parents in 95/96 months (2019-01 is zero only for this rule); the 2013-12–2017-12 Paris window has 2,304 eligible parents in all 49 bins. The [fixed scope and 125-parent manifest](../work_packages/M1_source_access/09_us_au_government_acquisition/reports/targeted_2015_bridge/SCOPE.md) were written before new requests.
- After the one-hour cooldown, all **125/125** bounded official requests returned HTTP 200, were saved with SHA-256 evidence and ingested under the existing US writer/resume locks: all **63/63** eligible 2015-04 parents, all **38/38** eligible 2015-05 parents, and a prespecified three-parent validation sample in each of eight adjacent, same-calendar-month and window-end months (**24/24**). No second US writer or EU stage writer was launched. EU's separate Item supervisor continued under the 15 GB storage guard.
- The [English source-text report](../work_packages/M1_source_access/09_us_au_government_acquisition/reports/targeted_2015_bridge/REPORT.md), [Chinese summary](../work_packages/M1_source_access/09_us_au_government_acquisition/reports/targeted_2015_bridge/REPORT_zh.md), [2012–2019 monthly source table](../work_packages/M1_source_access/09_us_au_government_acquisition/reports/targeted_2015_bridge/monthly_source_coverage_2012_2019.csv) and [updated 465-month government table](../work_packages/M1_source_access/09_us_au_government_acquisition/reports/targeted_2015_bridge/updated_monthly_government_presence.csv) record **463/465 → 465/465** pooled government stored-text presence, and **47/49 → 49/49** for the Paris candidate window. The source's own acquired-body months are still only **10/49**; 39 Paris months remain metadata-only for this US series, so no complete single-source full-text trend is claimed.
- Changed-tranche acceptance found 125 distinct parent IDs, 125 distinct verified originals and content versions, all with nonempty source text and matching original issue date, FR document number, EPA heading and official rules section. All 24,313 new cleaned segments had source mappings to the same version; zero selected-parent identity or mapping issues. The API `final_rule` class includes 6 CFR corrections and 5 withdrawals among the 125 originals, so subtype/source composition remains a later measurement consideration. The existing idempotent US importer traversed earlier saved checkpoints before inserting the selected 125; no separate all-source audit, global enumeration, model, causal run, figure rebuild, proposal edit, commit or push was performed for this bridge.

### 27 September, 13:20 UTC — Paris 49-month three-role readiness and bounded pilots

- Added an independent [Paris readiness pilot directory](../work_packages/M1_source_access/11_paris_readiness_pilot_20260927/REPORT.md) with a 49-month × three-role CSV, field dictionary, frozen sampling rule, source-aware government sample/review, Guardian article/day-frame check, official UK Parliament archived-petition query pilot, English report and Chinese summary. Existing source databases and proposal were not changed.
- Government stored text is present in 49/49 months, but full-month climate/fear relevance is unreviewed. The fixed EPA `final_rule` source has 2,304 eligible parents in all 49 months and 125 readable originals in only 10 months. The diagnostic 23-parent UK/EPA review found 5 climate-topic connections and no verified explicit fear expression; its deliberate title enrichment rules out any prevalence estimate.
- Guardian one-day archive frames in November 2015, December 2015 and January 2016 held 22, 17 and 7 distinct nonvideo title cards; four selected article parents had checked publication times and readable current HTML bodies. The test Open Platform key returned HTTP 401, so there is no monthly Guardian denominator. The official petition `q=climate` search had 179 result positions across eight pages, 177 distinct IDs after two cross-page duplicates; 21 created in the same three months were reviewed, with 13 published and eight rejected submissions. Fourteen were climate-topic relevant, six had anticipated climate-harm cues, and none had a verified explicit fear expression. Government responses embedded in the petition JSON were excluded from public text.
- The observed November 2015–January 2016 overlap is a source-feasibility interval, not a comparable monthly role panel or RQ1/RQ2 result. Next work is a defensible whole-month media frame, a published-versus-submitted petition rule with monthly eligible denominator, and further government passage/date/version review. RQ3 remains deferred. Actual effort was not supplied and is not recorded.

### 27 September, 14:19 UTC — bounded December media and published-petition correction

- Within a one-hour cap, froze the [round-2 counting contract](../work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/COUNTING_CONTRACT.md), audited Guardian December 2015 daily environment archives, and published an [English brief](../work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/BRIEF.md), [Chinese summary](../work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/SUMMARY_zh.md) and [updated 49×3 snapshot](../work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/paris_month_role_readiness_49x3_round2.csv). The original matrix remains a round-1 snapshot.
- All **31/31** Guardian December `/all` date pages returned HTTP 200 with only adjacent-date pagination observed. They yielded **396 distinct nonvideo article URLs**; **396/396** linked pages returned HTTP 200, a matching canonical URL and an original publication timestamp in December 2015 UTC. Three new hash-selected bodies were readable; with one distinct earlier body check, **four** have verified current HTML text. The 396 are a current archive candidate denominator, not a climate/fear numerator, historical immutable archive or 396 verified readable bodies. No Guardian API-key workaround or bulk copyrighted-body storage was used.
- The official petition `q=climate` frame has **177 distinct submitted IDs**: **77 published with `opened_at`** and **100 rejected without it**. Published/opened main counts for 2015-11, 2015-12 and 2016-01 are **0, 8, 5**; all-submitted/created sensitivity counts are **4, 14, 3**. Two November submissions opened in December; two December submissions opened in January. The prior November–January three-role overlap is withdrawn for the published public/civic main series. The zero in November applies only to this keyword-query frame. Existing manual labels remain separate for climate topic, anticipated harm and explicit fear.
- The official published-petition CSV omits dates, while its JSON list has `opened_at` but 25 records/page and a last link at page 438; large-page parameters did not alter the cap. No all-eligible monthly denominator was obtained, and no 438-page traversal was started. Guardian is a conditional go for monthly candidate inventory; published petitions are a conditional go for a civic channel, not general-public representation or a rate without the denominator. The [access audit](../work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/SOURCE_ACCESS_AUDIT.md) records the probes and fallback boundaries. No formal database, supervisor or proposal was modified, and no RQ1/RQ2 statistical run was made.

### 27 September — clarify staged climate, affect and fear interpretation

Dai clarified that the early project should not directly map fear. The thesis question remains fear of rising temperature, but source acquisition and first retrieval should establish climate/warming discourse and investigate its macro-level association with affective, risk and future-oriented language. Later passage-level review may interpret and attribute fear after checking speaker, quotation, negation, target and temporal horizon. Explicit-fear pilot labels are narrow diagnostics, not eligibility criteria or an early headline outcome. Government policy text may describe risk without expressing an emotion; the Paris pilot's zero explicit-fear observations neither invalidate the sources nor prove population absence. RQ1/RQ2 remain first; RQ3 is deferred. This is recorded in the [staged construct decision](decisions/2026-09-27-staged-climate-affect-and-fear-interpretation.md), with matching updates to project direction, methodology and root README. Frozen pilot data and reports, acquisition filters, formal databases and submitted proposal were not changed.

### 27 September — make the non-gating rule binding for future agents

Added root [AGENTS.md](../AGENTS.md) so new Codex tasks receive the same stage order. Its explicit rule forbids treating the ability to form a fear time series as a source-inclusion, acquisition, cleaning, data-quality, pilot-success or progression gate. A fear-specific measure can remain unavailable while climate-topic and validated macro-association work proceeds. The previous round-2 brief remains a frozen source-readiness record; its “no-go” applies only to using its four Guardian body checks or 396 candidate URLs as a monthly fear measure, not to the value or admissibility of that source. No data, proposal or pilot labels were changed.

### 27 September, 15:07 UTC — eight-figure project EDA atlas

- Created the [English EDA atlas](../work_packages/M1_source_access/12_project_eda_snapshot_20260927/INDEX.md) with eight distinct figures, each as 320 dpi PNG, PDF and SVG, plus a contact sheet, figure-specific CSV inputs, reproducible Python assembly/plot scripts, an input/checkpoint manifest and saved QA reports. It audits inventory stages, 465-month source-text presence, annual volume, issuer footprint, physical text shape, Paris 49-month readiness, manual label breadth and evidence-linked interpretation boundaries.
- Used the static UK database read-only and frozen US/EU/AU and Paris checkpoint ledgers. The corrected government stored-text union remains **465/465 months** after the 125-parent EPA bridge, with no claim of climate relevance. EU Item versions, government parents/Works, Guardian candidate URLs and petition IDs remain distinct units. The finite manual review is **23 government + 4 media + 21 petition parents** with 22 climate-topic, six anticipated-harm and zero narrow explicit-fear labels; these are diagnostic counts, not prevalence or a source gate.
- Visually inspected the final landscape renders. All eight PDF exports passed 5 pt font-floor and collision checks; the two multi-panel figures passed alignment checks, PNGs are ≥300 dpi, and figure-specific data invariants passed. The static source preflight passed with only nonblocking journal-template warnings. No formal acquisition database, supervisor communication, proposal or raw source record was changed.

### 4 October — freeze the endpoint and prioritise distribution and source quality

Dai clarified that the database's research endpoint must be anchored to the start of extraction and must not roll forward with later runs or reports. Retained the established publication interval **1988-01-01–2026-09-21**; September remains partial. The initial query observation, later retrieval/extraction times and report dates keep their separate meanings; no unsupported exact global extraction-start timestamp was invented. Historical backfill inside the interval can continue when justified without extending the endpoint.

The recorded **465/465 government source-text months** complete basic pooled temporal presence. The next preparation priorities are (1) distribution diagnostics that distinguish collection artefacts from legitimate concentration or independently evidenced candidate research checkpoints, and (2) source directness, verification, unresolved/conflicting provenance and targeted supplementation. Original, archived, indirect and mixed records require explicit evidence; directness is role-relative, and provenance verification does not prove the truth of every claim. High volume or disputed content alone does not justify deletion or flattening.

The coordinator's previous suggestion to prioritise climate-topic validation immediately was corrected. Current work is structural/numerical cleaning; climate relevance, emotion and attribution belong to later analysis. Algorithm/evaluation design can be prepared, but topic or fear labels must not gate current acceptance or cause semantic exclusions. Updated root AGENTS.md, project direction, methodology, README, the decision index and a dated clarification on the prior figure brief and staged-construct decision. See [fixed cutoff, distribution and source quality](decisions/2026-10-04-fixed-cutoff-distribution-and-source-quality.md). No database, acquisition program, source filter, frozen pilot labels or proposal was modified in this documentation update.

### 4 October — dispatch three parallel preparation tasks

At Dai's request, created three local project tasks using **GPT-6 Sol / Extra High**: fixed cutoff/date integrity, distribution/collection anomaly diagnosis, and source provenance/verification quality. Each has an exclusive output directory under [13_parallel_data_audit_20261004](../work_packages/M1_source_access/13_parallel_data_audit_20261004/COORDINATION.md), reads formal data without modifying it, records its input checkpoint, and prepares an individual log entry for central integration. Dai authorised each task to send its final evidence-linked report back to this coordinating task. Results will be reconciled before shared-code/database changes or supplementary acquisition are proposed. All three dispatches succeeded; findings are not yet complete.

### 4 October — integrate the three parallel structural audits

All three GPT-6 Sol / Extra High tasks completed, and their outputs were reconciled in the [integrated report](../work_packages/M1_source_access/13_parallel_data_audit_20261004/INTEGRATED_REPORT.md). The audited UK/US/EU publication dates have no observed out-of-scope record; 119 GOV.UK local-versus-UTC date differences include three month changes and remain a convention decision, not an automatic repair. Distribution flags (85, with 20 reviewed) are diagnostics, not grounds for flattening or climate attribution. Shared objects, attachments, versions and short PDF blocks remain separate from independent parent counts. Source quality uses route rules and a 30-case purposive review, not a population confidence score.

The coordinator corrected one reporting omission: across both Guardian pilots four distinct December 2015 bodies were checked, not one; 392 of the 396 candidate URLs are outside that documented body-check set. Earlier US/EU status exports were kept separate from the later committed version inventory (18,590 US versions; 19,114 EU Items). The 09 UK copy and the EPA bridge were not added again. A [nine-item ordered action list](../work_packages/M1_source_access/13_parallel_data_audit_20261004/INTEGRATED_ACTIONS.csv) prioritises date rules, stale text-status fields and parent/mirror identity, then bounded date/issuer/content checks. No global enumeration restart is proposed.

Formal data, shared collection code, raw evidence and the proposal were unchanged; no acquisition, model run, full-corpus rehash, commit or push occurred in this integration. Local CSV checks confirmed exception counts, ledger dimensions and the four distinct Guardian checks. Worker figure collision automation was unavailable, so no full automated figure-QA pass is claimed. Automatic approval rejected some cross-task reporting/corrective messages; reading the shared local results and recording a coordinator addendum completed integration without a messaging workaround or further user approval.

### 4 October — independent split validation and provenance-logic checks before supplementation

Dai requested two executable checks: an independent saved-source validator for splitting meeting/archive containers into reply parents, and corpus-wide applicable provenance/date logic with explicit per-record annotations. These are structural checks, not content-truth, climate or fear tests. Record unsupported boundary evidence and uncertain dates rather than declaring all data correct. Preserve parent/container/question/answer-group distinctions and legitimate repeated wording. The [execution decision](decisions/2026-10-04-structural-checks-before-repair-and-backfill.md) and [task plan](../work_packages/M1_source_access/14_structural_validation_20261004/PLAN.md) specify separate outputs, shared heavy-read mutex and no formal data changes during Tasks 1–2.

Dai confirmed Task 3 means repair and evidence completion for existing dates, sources, states, mappings and annotations; Task 4 means downloading specifically missing originals/attachments. They must wait for both validation tasks and coordinator review, then may prepare repairs and stage acquisitions concurrently with serial formal database integration. A task can complete with named unresolved records; universal pass is not required. The fixed endpoint and analysis-stage semantic boundaries remain unchanged. No downstream collection or repair was started by this scheduling decision.

Dai's subsequent clarification: **only Tasks 1 and 2 start now**. The coordinator must review their results and adjust Tasks 3/4 before dispatch. Supplementary acquisition may include new source frames where existing source/genre/period concentration is a genuine research-data limitation, rather than only downloading failed originals. Such additions require a defined frame and stopping rule; unequal counts alone are not a mandate to equalise distribution. The two existing audit windows have now received the validator tasks using GPT-6 Sol / Extra High, with isolated outputs and a shared heavy-I/O lock. Tasks 3/4 remain undispatched.

### 4 October — accept validators, triage anomalies and update downstream model

Dai authorised anomaly handling followed by Tasks 3/4 and changed all subsequent task models to **GPT-6.1 Sol / Extra High**. Coordinator accepted the two completed diagnostic deliverables after reviewing exceptions and rerunning 10+9 focused fixtures (all passed). Task 1's original-span conflicts remain valid pending per-record source confirmation even though Task 2 found no conflict in its narrower metadata comparisons. [Accepted scope and staged execution](../work_packages/M1_source_access/15_targeted_repairs_and_supplementation_20261004/ACCEPTANCE_AND_SCOPE.md) and a 3,080-row issue ledger distinguish defects, uncertain dates/statuses and candidate omissions; the count is not unique erroneous documents.

Task 3 will first handle existing-original reply/role/boundary anomalies, date uncertainty and stale technical state, preserving ethics/rights status, raw text and prior extraction evidence. Task 4 will define named missing originals and a bounded additional-source tranche justified by source/genre/period composition. Actual supplementary acquisition waits for Task 3's checked repair checkpoint; metadata/source planning can proceed independently. Local/UTC month reassignment remains undecided and is not silently applied.

The volume currently has approximately 14 GiB free, below the existing 15 GiB safeguard. Do not lower it or delete user data. Compact repair patches and source plans can proceed. Bulk acquisition must retain the 15 GiB floor; small local repair commits require their own bounded transaction/WAL and rollback footprint assessment, without inventing a new blanket prohibition from the collector-only guard. No formal repairs or new acquisitions have yet been executed by the coordinator.

### 4 October, 09:23 UTC — Task 3/4 dispatched on GPT-6.1 and storage refreshed

Created Task 3 (`01a10638-e552-7313-a19d-88a0c672255d`) for bounded anomaly repair and Task 4 (`01a10639-811d-73a2-bacc-fcede2e06848`) for targeted missing-original/additional-source planning. Both use **gpt-6.1-sol / xhigh**. Actual supplementary acquisition remains behind Task 3's checked repair checkpoint; Task 4 cannot write formal databases.

Dai cleared Trash. At 09:23:34 UTC the project volume had **21.13 GiB free**, above the existing 15 GiB collector floor, leaving about 6.13 GiB before repair/transaction/download overhead. Both tasks were informed; the former ~14 GiB reading is not a current blocker. [Storage evidence](../work_packages/M1_source_access/15_targeted_repairs_and_supplementation_20261004/control/storage_status.json) records actual bytes and time. Recheck planned footprint and space before substantial writes; no automatic global acquisition restart.

### 4 October — review committed repairs and hand off analysis

Coordinator reviewed Tasks3/4 results and checked the final release against the current UK database file checkpoint; size/mtime match. Task3's additive layer exposes248,319 effective parents (legacy248,035), with1,256 existing-parent corrections,202 recovered ZIP groups and82 repartitioned HTML groups.124 date intervals and1,054 current technical states are recorded.318 issue instances across165 units remain unresolved, including named adapter limits; no universal pass is claimed. See [coordinator review](../work_packages/M1_source_access/15_targeted_repairs_and_supplementation_20261004/COORDINATOR_REVIEW.md).

Task4 ended before the repair release and acquired no bodies. Its979 EU2015 Item manifest remains a plan; final Task3 original-evidence requests are5, superseding3 provisional Hansard routes. The gate is now released but no collector was restarted. Free space measured~20.72GiB during this review. Earlier465/465 coverage remains a dated snapshot until recalculated using effective date views. Prepared [new analysis-window handoff](handoffs/2026-10-04-analysis-continuation.md), explicitly using GPT-6.1 Sol / Extra High. No database scan, raw hash audit, repair rerun, acquisition, commit or push was performed by this coordinator review.

The new local analysis conversation was created successfully: `01a10743-2e31-7541-9498-3254139e8b12` — **Continue post-repair corpus analysis and source planning**, model `gpt-6.1-sol`, effort `xhigh`. It owns the next read-only analysis/decision deliverable; former workers remain idle and no duplicate collector was dispatched.

### 4 October, 22:21 CST — post-repair analysis and supplementation readiness

Completed the initial analysis handoff in [16_post_repair_analysis_20261004](../work_packages/M1_source_access/16_post_repair_analysis_20261004/CURRENT_STATE.md), with an English current-state report, Chinese summary, concrete next-action list, bounded evidence manifest and saved delivery checks. The fixed publication interval remains **1988-01-01–2026-09-21**, September partial.

The actual UK06 file size/mtime match the committed repair release. One read-only effective-document metadata aggregate, under the shared heavy-I/O lock, confirmed **248,319** source-specific parents, **248,268** assignable to one month and **248,195** with exact-day metadata support. Nine Historic Hansard answer months changed: 284 locally derived additions, minus 51 transferred out of unsupported point-month allocation, give a calendar-bin net change of **233** plus **51** retained cross-month intervals. The 73 remaining interval cases support October 2003. No readable-text coverage refresh was performed; **465/465** remains its historical checkpoint. Source/genre totals retain mirror/shared-answer constraints.

Reconciled **318 remaining issue instances / 165 units**, the separate 37 HTML-adapter limits, and the final **five original-evidence requests** (three Hansard section originals and two AU issue-date/primary-file cases). The prior three contribution-ID routes are superseded; the withdrawn saved-EU request stays withdrawn. Confirmed **979 candidate Items / 1,009 EU2015 Works**, 30 no-link outcomes and 973 multi-Item Works; **253 Works have multiple Items within the selected PDF Manifestation**, requiring explicit component/completeness accounting.

Focused runner inspection and a side-effect-free preflight reproduced a release-schema incompatibility: the real release uses explicit status and pre/post checkpoints, while the script looks for separate committed/checked assertions and before/after keys. The release remains valid; the script is not ready to execute against it. A-before-B final-five accounting is also not programmatically enforced. Storage preflight passed at about **20.67 GiB free**, **17.51 GiB projected** after existing reserves. Recommended a scoped runner correction and five-request accounting, then the same frozen EU candidate-byte tranche with the unchanged 2 GiB cap/15 GiB floor and subsequent serial changed-tranche ingestion acceptance.

No HTTP body acquisition, formal data write, repair/validator rerun, text/raw hash audit, old-figure regeneration, semantic/emotion/fear classification, new chat, cross-chat message, proposal change, commit or push occurred. No collector was resumed. Delivery checks verified saved-input hashes, database checkpoint stability, source/month reconciliation, EU multiplicity and artifact links without a second aggregate.

### 5 October — independent distribution diagnostics and encrypted evaluator preservation

Dai requested methodological review of entropy, coverage, source concentration, text-length distributions and temporal-source quota sampling, followed by targeted executable checks kept away from extraction windows. Dai selected authenticated-encrypted preservation outside the extraction repository, with credentials delivered only in the coordinator conversation. Recorded the [independent review decision](decisions/2026-10-05-independent-distribution-audit-sealing.md) and added the extraction boundary to root AGENTS.md. Extraction windows receive only the [evidence issue list](../work_packages/M1_source_access/17_independent_audit_handoff_20261005/EXTRACTION_ISSUES.csv) and operating instructions, not evaluator code, fixtures, credentials or metric targets.

Completed six reviewer modules, 18 passing synthetic falsification/boundary tests and two diagnostic figures from the already saved post-repair UK metadata aggregate. Metrics describe declared source composition and evidence-specific presence; uniformity is not a data-quality target. Missing department mappings, applicability/completeness evidence and current parent-level lengths remain unassessed. Sparse census units retain design weight one; any optional certainty-selected and random components require their own inclusion probabilities. No production downsampling was performed. The fixed endpoint remains 1988-01-01–2026-09-21, with partial September and date uncertainty preserved.

Authenticated archive restoration and tamper rejection were verified, then only the task-created plaintext build directory was removed. Input/evaluator/output hashes and versioned review receipts are retained outside the extraction repository. Encryption protects direct code reading without a credential; shared OS accounts remain a stated limitation. This freezes a reviewed evaluator version and does not claim retrospective blinded preregistration.

No fresh formal-database query, raw/text scan, new body acquisition, repair, formal data write, live corpus sampling, semantic/emotion/fear classification, new chat, cross-chat message, proposal change, commit or push occurred. The evidence list does not release new acquisition or supersede the existing five-original/EU2015 scope.

### 5 October — resume bounded supplementation in the two existing windows

Dai explicitly authorised the original continuation order: downloader correction and offline verification → dispositions for the final five original requests → staging the unchanged 979 EU2015 selected Items. Resumed existing Task 3 (`01a10638-e552-7313-a19d-88a0c672255d`) and Task 4 (`01a10639-811d-73a2-bacc-fcede2e06848`) with **gpt-6.1-sol / xhigh**; both returned active status. The [execution coordination package](../work_packages/M1_source_access/18_bounded_supplementation_execution_20261005/COORDINATION.md) gives Task 3 exclusive downloader editing and bounded A request accounting, while Task 4 initially prepares only local reuse/manifest/component evidence. EU HTTP requests require coordinator acceptance and a new digest-bound execution release; neither worker may self-release B or make formal database writes.

The coordinator rechecked only saved manifests/release and database file size/mtime, without a database query. Five unique A requests, 979 unique B Item targets, the frozen B digest and committed post-checkpoint match. Fresh storage passed the existing reserve-aware 15 GiB floor. The aggregate 2 GiB new-raw cap includes both A and B and retained partial files; rate/access stops, source identity, uncertain dates and component-pending states remain binding. Audit code and credentials were not distributed. No new window was created and no HTTP acquisition was performed by the coordinator during dispatch.

### 5 October — accept downloader and A accounting, release the independent EU phase

Task 3 completed downloader V3 and the [five-request ledger](../work_packages/M1_source_access/18_bounded_supplementation_execution_20261005/01_downloader_and_originals/A_DISPOSITIONS.csv). The real repair-release schema, linked committed evidence, active run and current post-checkpoint are now checked explicitly. Shared A/B raw and retained-partial accounting, reserve-aware storage checks, bounded streams, reuse, request spacing and persistent stops remain enforced. All 32 network-denied fixtures passed in the worker and coordinator checks; V2 evidence remains preserved because A actually executed under that version.

A made one canonical Hansard HTML request, which returned HTTP403. The remaining four requests were not attempted after the stop; their availability is untested. No new original or raw/partial bytes were obtained. The five terminal dispositions and evidence hashes are accepted as complete accounting, **not** as completed original acquisition. AU publication dates remain unresolved and CMS dates were not substituted.

The initial shared halt would also block the separately authorised EU source. The reviewed V3 transition preserves A's stop unchanged, requires coordinator acceptance of its exact digest and checks inherited cooldowns, while giving B a separate persistent phase state. It does not retry A. B failure still halts B; global locks, spacing and the original budget/floor remain binding. The coordinator signed [EU_STAGING_RELEASE.json](../work_packages/M1_source_access/18_bounded_supplementation_execution_20261005/control/EU_STAGING_RELEASE.json), and a network-denied real preflight passed with one targeted read-only run-record query and no HTTP or formal write. Fresh free space was about 19.20 GiB; after the existing full reserve, about 16.04 GiB remained above the 15 GiB floor.

Task 4's 15 local preparation checks passed, with all 979 targets unrequested at that snapshot. Sent the explicit execution follow-up to the same existing Task 4 window using **gpt-6.1-sol / xhigh**; its new turn is active. It owns candidate-byte staging, all-target status accounting and the ingestion handoff. The manifest, 1,009 Work denominator, 30 no-link outcomes, component uncertainty and publication interval remain frozen. **EU download completion is not yet claimed.** No extraction or formal database integration is authorised in this continuation. The coordinator will use the worker's saved terminal result for any later changed-tranche integration decision.

### 5 October — consolidate government closeout and start equal-stratum media preparation

EU staging reached a bounded stop: 20 candidate Items saved (9,020,646 bytes), the 21st request returned HTTP406, and 958 targets were not attempted. These are candidate bytes, not verified complete Works or readable independent parents. The existing failed A request and four unattempted original requests retain their separate dispositions. No formal database integration occurred.

Dai requested government distribution/gap closure within one or two complete task rounds, followed by script execution, visualisation and next-round recommendations, while one window prepares media/newspaper acquisition, schema and the collection chain across all proposal geographies. Recorded the [two-work-line plan](../work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/PLAN_zh.md). Both existing windows received **gpt-6.1-sol / xhigh** continuation prompts: Task 4 combines evidence-based transport diagnosis, any reviewable bounded correction, changed-Item structural checks and the final government input checkpoint; the completed downloader Task 3 window now owns the media pilot and schema package. No new window or microtask was created. A new viable transport route requires one combined coordinator acceptance; existing stops cannot be silently cleared or retried.

The media pilot plans equal slots in EU/Europe, UK, AU, US and NZ: two independent editorial sources and three fixed months, five articles per source-month, at most 30 articles per stratum and 150 total. EU is a regional stratum with specific publisher countries/markets recorded; UK is not counted again within it. Unfilled slots and access/era limitations remain explicit, rather than being transferred to easier sources. The 128 MiB media raw cap remains within the shared reserve and 15 GiB floor. This is a route/schema pilot, not a nationally representative sample or a climate/fear-filtered frame. Publisher/library/licensed-access evidence, article/issue/version and wire-adoption identities, dates, rights, denominators and coverage states belong in the single media deliverable.

The coordinator retains independent government analysis and visualisation after the final input checkpoint. The encrypted evaluator and credentials stay outside extraction access; workers receive factual requests and output contracts only. Reuse earlier accepted aggregates and verify the changed tranche once. No production quota downsampling, semantic exclusion, proposal revision or universal source-completeness claim is authorised by this plan.

Created a 15-minute thread heartbeat to carry out the authorised follow-through after worker results: combined operational acceptance where justified, final government independent analysis/figures and integrated media recommendations. It remains quiet while unchanged, contains no credential, and will pause after both deliverables have been reviewed and reported. The heartbeat does not create additional tasks or authorise bulk media collection. Both existing worker turns were confirmed active after dispatch.

### 5 October, 19:37 UTC — accept one combined government continuation and review media design

Task 4 delivered 23 native source/genre frames and a frozen input package. Its once-checked 20 PDF Items have135 pages with nonempty text layers;20 first pages were visually checked. One CDM-versus-printed day conflict (2015-01-30 versus2015-01-31) and four first-page multi-notice boundaries remain explicit. No Item was certified as a complete parent-length observation. Source checkpoints and question/answer/Work/Item units are not pooled into a new independent total.

The coordinator reran all16 transport fixtures with real network denied, verified70 saved small evidence/request receipts and checked the real repair release with one targeted read-only run-record query under the heavy-I/O lock. Fresh free space was20,606,500,864 bytes; after3,379,313,690 bytes of remaining government raw and original reserves, the15 GiB floor passed. Official CELLAR documentation supports wildcard Accept when an exact URI determines the stream; that makes the proposed same-Item header change reviewable, not a proven explanation for406. Signed [one combined continuation release](../work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/control/GOV_CONTINUATION_RELEASE.json) and sent the execution follow-up to the same Task4 window on GPT-6.1 Sol / Extra High. It permits one corrected validation of the failed Item, the unchanged958 never-requested targets only after success, and at most four requests for the two unattempted AU landing/exact-PDF pairs in an independent phase. Prior403/406 stops remain bound and immutable; no database integration or complete-Work acceptance was released.

Task3 delivered the media design and bounded access findings: five equal strata,10 sources,150 unfilled slots; new articles/full bodies0. One saved212-byte HTTP200 object is an access challenge, not readable catalogue or article content. The coordinator reran31 network-denied prototype fixtures, all passed. The18-table schema and simulated structural checks do not establish a working real-body/OCR pipeline. Asked the same media window for one consolidated design revision: edition-scoped article identity and source/edition consistency constraints, preserved v1 receipts, and a compact existing-access readiness matrix. The suggested adjacent-month batch is deferred; access and article-level validation should first address the original150 slots. No new media HTTP batch, publisher substitution, account creation or bulk acquisition was dispatched.

### 5 October CST — bounded government closeout, independent figures and media V2 accepted

Both existing GPT-6.1 Sol / Extra High workers completed their combined turns and are idle. Government's released continuation added27 PDF Items (13,210,928bytes) to the20 reused candidates. Final actual staging is47 Item identities,45 distinct raw hashes,22,231,574bytes and partial0. The original failed Item returned200 in its one corrected request; its historical406 remains. The next new Item returned406 and stopped B. Of979 frozen targets,1 currently failed and931 are unattempted;30 no-link Works remain outside that target denominator. Every newly acquired Item is in January2015, not a year-wide completed corpus. AU made one landing request with a90-second ReadTimeout/no body; the other landing and both PDFs were unattempted. Original five-request new-original count stays0, with the prior Hansard403 and unattempted requests preserved.

The changed27 PDFs were checked once by their owner:257 nonempty text-layer pages and27 first-page visual checks; combined47 have392 pages,2 same-month CDM/printed-day conflicts,7 first-page multi-notice flags,10 selected multi-Item Manifestations and2 cross-Work identical-PDF groups. Complete parent/body ownership and component coverage are unestablished; all47 parent-length eligibility fields arefalse. Original identity/raw/date evidence is retained. No formal import, date rewrite, duplicate deletion or downsampling was performed. Final input frozen2026-10-04T19:57:43.784085 UTC has manifest SHA2564d60b7032ddbd200c7ee6cc6de8cb5c07e04830345a4b484c634cd4bf4b440c1. Coordinator accepted71 small evidence hashes and database file size/mtime; no post-freeze DB query or repeat raw/body scan. An earlier pre-completion receipt was explicitly preserved and superseded by this final receipt.

Ran the sealed six-module independent evaluator after the final input, with18 network-denied boundary tests passed and original source hashes unchanged. Reused the accepted UK248,319 effective source-parent aggregate (248,268 month-assignable,51 cross-month) and historical source-specific native units. UK metadata presence is155/155 quarters and434/465 months; these do not refresh the historical pooled readable-text465/465 snapshot. Official source-route K=5 entropy0.61324 and HHI0.42199 are descriptive; mirror inclusion lowers HHI to0.39492 without establishing independent diversity. A34-parent 2014Q3 trough and archival/API era changes limit dominance interpretation. Applicable-source completeness, verified department mapping, full parent lengths and tokenizer/passages remain unavailable.

Delivered [Chinese integrated closeout report](../work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/GOV_CLOSEOUT_REPORT_zh.md), native-frame/month state tables and four PDF/SVG/320dpi PNG figures. Grey unknown/date-unverified and declared metadata/index zero cells differ; source-specific parents, Works and question indexes are not pooled. EU Item lengths are explicitly file diagnostics, with shared raw identities retained, not a fabricated parent violin. Figure source preflights have0 failures with documented static/internal-contract warnings; rendered fonts are at least6pt, final collisions0, all four visually inspected. A saved-evidence plotting extension was created after final input, not claimed as blind preregistration.

Reviewer closeout V2 is authenticated-encrypted outside extraction: archive SHA25641fdfe40acbae44dc5922e62da7a429a0f74ad19ff9365aa17eacaeaef1c3e18,126 payload files. Round-trip all-file verification and tamper rejection passed. V1 ciphertext is unchanged. Task-created plaintext and isolated QA dependency were removed; credentials were not persisted or distributed. Public [seal receipt](../work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/control/INDEPENDENT_REVIEW_SEAL_RECEIPT.json) contains hashes/status only, no credential or evaluator location.

Accepted media V2 edition-scoped source/native identities, consistency constraints and preserved V1 receipts. All37 coordinator network-denied prototype fixtures, SQLite integrity and foreign-key checks passed. The150 original planned slots remain30 each inEU/Europe(excludingUK),UK,AU,US,NZ. Real new articles/full bodies0;1 saved212-byte challenge is not article/catalogue evidence. Ten-source existing-access readiness table lists title/year/edition, metadata/text/OCR, retention/export and missing entitlements. Real-body/OCR/republishing validation remains pending; product existence does not establish current user access. Recommend one complete next media task to confirm existing lawful access and validate the original150 slots, with fixed128 MiB/15 GiB/shared-lock bounds. Adjacent months are deferred; no new media HTTP batch or bulk collection was released.

Recorded [closeout/readiness decision](decisions/2026-10-05-gov-closeout-and-media-readiness.md). Government usable input advances with honest gaps; no exhaustive queue, uniformity, climate relevance or fear result gate. No fresh full-corpus audit, formal database write, semantic/emotion/fear model, proposal revision, new window, third-party message, commit or push occurred during independent analysis. The follow-up automation pauses after these deliverables; this conversation remains open.

### 5 October, 10:45 CST — start one bounded public-media validation task

Dai authorised the recommended media task and accurate repairs without an indefinitely extended cycle. Resumed the existing media window on GPT-6.1 Sol / Extra High; no new window or microtask. [Round20 scope](../work_packages/M1_source_access/20_media_original150_validation_20261005/PLAN_zh.md) preserves accepted19 media V2 evidence and government closeout. At most two owner turns and one consolidated operational acceptance; network operations stop by11:45:48 CST, preserving checkpoints and honest failures rather than claiming completion. The original five disjoint geographic strata, three months and150 planned slots remain. New scope explicitly allows up to five body checks per source-month; the prior route-only one-check limit could validate at most30 and its historical scope is unchanged.

Dai confirmed no institution/database/API access: public Internet crawler/search only. The one access-fact question is resolved; no credential discovery, registration, purchase or third-party contact. Permit one pre-body bounded candidate revision (at most two per stratum/ten total) for evidenced public access/reuse and editorial-era applicability, preserving original source/slot failures and distinct new-candidate identities. This is not a topic/length/availability-volume selection rule or permission to bypass known stops. Public challenge/robots/timeout states persist; new routes need specific viability evidence. All independent evaluator code and credentials remain sealed. No article/frame network execution release has yet been issued; the worker is preparing an exact candidate, targeted offline validation and a consolidated route/access/repair package. Government queues remain closed and the previous heartbeat remains paused.

### 5 October, 11:31 CST — one media operational acceptance and final bounded execution

The existing media owner froze round1 with0 real article/frame requests,4 saved policy/robots objects (201,722 new bytes;201,934 including prior challenge). Coordinator checked all9 accepted V2 input hashes and six actual execution digests; independently reran19 socket-disabled targeted checks and1 temporary whole-chain scenario, all passed. Synthetic5 parents stayed outside the real project database. Verified four policy raw hashes and read EDJNet's saved primary licence text: defaultCC BY4.0 with per-article exceptions; member attribution remains distinct. Fresh five-max-object budget preflight passed the fixed128 MiB,15 GiB floor and original government/other reserve.

Issued [one digest-bound execution release](../work_packages/M1_source_access/20_media_original150_validation_20261005/control/MEDIA_EXECUTION_RELEASE.json) to the same GPT-6.1 Sol / Extra High owner for its second and final turn. Only one domain/date-only public-search response and at most five preselected EDJNet European-English2025-07 article requests are authorised; no refill, retry, redirect, further candidates or months. EDJNet started2017, is a data-news network rather than a newspaper, and cannot count as DW or original-source success. The original150 five-layer slots and stops remain; known older-era and other-country gaps are honest terminal states, not zero publication. Search indexing is a partial observation frame; first publication and complete article boundary require retained-byte checks; monthly denominator andpi remainNULL.

Network deadline remains11:45:48 CST; no third turn, new window, adjacent-month collection, government database access or private evaluator access. Existing follow-up automation remainsPAUSED. Physical body completeness, per-article rights, historic-version equality and original/wire/member mappings are separate evidence dimensions. The final actual-body outcome and one changed-tranche local acceptance remain pending.

### 5 October, 11:39 CST — media repairs accepted; public discovery gap preserved

The media owner completed its second/final turn and is idle. Its single exact released EDJNet2025-07 domain/date search returned0 article URLs;0 body requests, actual article parents/versions/verified full bodies/issues/OCR. The empty response is a partial observation and does not establish zero monthly publication. No additional search, refill or deadline extension occurred. Five strata still plan30 each; all150 original-source slots remain unfilled.135 original stops,10 candidate pre2017 inapplicable coordinates and5 empty-search coordinates are separate; the EDJNet candidate is not DW success or newspaper evidence.

Coordinator accepted62 final output hashes,9 frozen inputs and6 execution-code hashes; all150 original CSV fields are unchanged. One read-only local media database check under the shared lock confirmed integrity, no foreign-key failures,150 unfilled old slots and5 persistent candidate terminal mappings. No additional test, network request, government database or sealed evaluator access was needed. Four policy raw files plus one68-byte search response total201,790 new bytes (202,002 including the historical212-byte challenge), no partial/body bytes. Earlier independent19 targeted and1 temporary-chain checks remain the repair evidence; simulated5 articles never entered real outputs.

[Final coordinator report](../work_packages/M1_source_access/20_media_original150_validation_20261005/COORDINATOR_FINAL_REVIEW_zh.md) and [machine acceptance](../work_packages/M1_source_access/20_media_original150_validation_20261005/control/COORDINATOR_FINAL_ACCEPTANCE.json) distinguish repaired code from unresolved real acquisition. The next need is an evidenced public publisher date/archive/index frame plus actual articles, preserving geographic quotas, source/edition/era and unknown denominator/pi; do not repeat the same empty query or split another task around fields/tests. Existing saved EDJNet robots advertises a sitemap index only as an untested next-route fact. No media distribution/length figure can be supported with0 actual articles; government report/four figures and all residual gaps are unchanged. Recorded [public-only validation decision](decisions/2026-10-05-public-media-validation-closeout.md). Previous heartbeat staysPAUSED, no automatic next round or bulk acquisition.

### 5 October CST — archive accumulated work in21 descriptive local commits

Dai requested a real commit history after an empty staging area and a last commit on23 September. Grouped the existing outcomes into21 substantive commits, with Chinese titles and multiline descriptions recording changes, existing evidence and unresolved limits. Current branch iscodex/coverage-gap-recovery; no prior commit was rewritten or backdated and no remote push was requested. The [commit index](git/COMMIT_BATCH_2026-10-05.md) records the first20 actual SHAs and this final history commit.

Preflight inspected158 Python files by AST,430 JSON/notebook files and1JSONL; syntax/format decoding errors0 and known credential-pattern matches0. Internal proposal aliases resolve to versioned targets. New ignore rules preserve local raw/API probes, databases, bulk repeated row snapshots, dependency runtimes and temporary files; they do not delete evidence. Kept a2706-byte public robots snapshot needed by the existing offline media chain. This Git task did not execute collectors, corpus repair, models, hidden evaluation or database writes. Frozen reports and source limits retain their original dates and meanings.

### 5 October, 15:02 CST — government phase1 qualitative seal and main integration checks

Dai authorised pushing the21 descriptive local commits; normal push and remote readback confirmed working-branch tip7bdcc8f07ae310a72f85c29ec958bbb2aea5fb8a. Dai subsequently specified direct integration into main with pre-merge checks. Remote main initially remains61db65e4a21748f5256bf885be30c1c05e789b4f; preserve all substantive commits and descriptions through an ancestry-checked fast-forward, with remote main readback after push. The working-branch push alone is not the requested main delivery.

Created a separate [government phase1 qualitative seal](../work_packages/M1_source_access/21_government_phase1_seal_20261005/GOV_PHASE1_SEAL.md), dedicated coordinator-only hash-chained government log and freeze manifest. This closes the bounded round with usable inputs while retaining47/979 candidate Items,1 current406,931 unattempted,30 no-link Works outside the target denominator and0/5 new originals. No collector, queue expansion, formal import or topic/emotion model was run. Logical log isolation/Git anchoring is explicitly distinct from OS permissions; any future authorised government change uses a new version and preserves this baseline.

Frozen government input is unchanged:71 small evidence hashes and24 accepted independent output hashes agree, current formal database size/mtime match without opening or hashing it. Reused four byte-identical independent PNG/PDF/SVG figures and prior18 evaluator tests/QA; all four also visually reviewed this round. New [35-row verification table](../work_packages/M1_source_access/21_government_phase1_seal_20261005/AUDIT_VERIFICATION_TABLE.csv) has30 receipt/arithmetic passes,1 prior-evaluator/QA reuse,1 historical-only reference and3 unavailable metrics. Monthly-source counts independently reproduce quarterly HHI and H/log(K) to below1e-12. The verifier initially encountered the existing empty official2004Q4 metric and was corrected to validate N=0/undefined, rather than coercing it to zero. No original input/output was changed.

The new report distinguishes239,820 quarter-assignable official parents from239,871 inventory parents and51 cross-month intervals; official2004Q4 hasno saved parents and undefined entropy/HHI, whereas mirror-inclusive metadata has155/155 quarterly presence. Department mapping, applicable-source/readable-parent completeness and complete-parent lengths/tokenizers remain unavailable. Historical pooled readable-text465/465 is not refreshed. No repeated raw scan, database query/write, reviewer-source access or decryption occurred. Existing follow-up automation staysPAUSED; media real articles remain0/150 and no new batch is released by this seal.


Dai clarified that conversation may remain Chinese, but this delivery, commit titles/descriptions and new logs must be English for supervisor/university review; frozen originals remain unchanged. Recreated the 21 commits with English messages, identical trees and preserved author/committer timestamps. The [English identifier map](git/ENGLISH_COMMIT_MAP_2026-10-05.json) records all 21 old/new pairs. The English chain tip is 106ca8caed77839415d379654ac4fbbddf5aa73f. Main integration will retain that chain plus one English government-seal commit, using a normal fast-forward from the original main baseline.
