# Government targeted gap repair — final report

Completed: **2026-09-22T06:28:35Z**. Scope is limited to the 2026-09-22 handoff: saved-payload parser repair, bounded named gaps, nine statement candidates and four downloaded PDFs. The proposal, cleaning, embeddings and model analysis were not changed or run.

## Outcome

| Metric | Before | Addition | After |
|---|---|---|---|
| documents | 239,179 | 407 | 239,586 |
| policy_document | 1,054 | 0 | 1,054 |
| ministerial_written_answer | 235,420 | 404 | 235,824 |
| ministerial_written_statement | 2,705 | 3 | 2,708 |
| text_segments | 3,622,039 | 1,398 | 3,623,437 |

- Genuine new documents: **407** = 404 written answers + 3 written statements. Policy record count is unchanged.
- Existing-text repairs: **83** saved Hansard answer payloads were deterministically reparsed; **4** existing PDF objects received a new local OCR extraction lineage.
- Text growth: **1,398 segments** = 243 local parser-repair segments + 340 OCR page segments + 815 segments from new records.
- January 1988 boundary: the official calendar's first sitting is **1988-01-11**; 1–10 January is not treated as a collection gap.

## Queue reconciliation

| Queue | Unit | Expected | Attempted | Recovered/resolved | Excluded | Unresolved | New documents |
|---|---|---|---|---|---|---|---|
| Saved Hansard answer payload parser repair | answer target | 85 | 85 | 83 | 0 | 2 | 83 |
| Failed written-statement candidates | candidate container | 9 | 9 | 3 | 5 | 1 | 3 |
| Historic Hansard volume 200 daily repair | written-answer item | 322 | 322 | 321 | 0 | 1 | 321 |
| Historic policy OCR | downloaded PDF file | 4 | 4 | 4 | 0 | 0 | 0 |
| 2010–2014 failed date indexes | date index | 20 | 1 | 0 | 0 | 20 | 0 |
| 2010–2014 known page repair queue | archive HTML page | 437 | 1 | 0 | 0 | 437 | 0 |
| 2004-Q4 Commons cross-route seam | date range with unknown target denominator | unknown | 2 | 0 | 0 | 1 | 0 |

Different units are intentionally not added into one “missing documents” total. In particular, 20 failed date indexes can hide an unknown record count, and 437 HTML pages are not 437 answer records.

## Important evidence decisions

- Volume 200: actual range **1991-12-02..1991-12-13**, 10 Commons sitting days, 322 approved-department item targets; 321 were parsed and committed. `Self-regulating Bodies` remains unresolved because the official HTML merges unrelated answer text into the questioner's block without reliable minister attribution.
- Statement candidates: official search parents contain section-ID collisions. Three in-scope children were stored by official `ContributionExtId`; five candidate containers were out of department scope; one cross-date header/container was not inserted.
- 2004-Q4 seam: 43 accessible Historic daily indexes expose Lords written material only. No Lords content was substituted. Both normal Commons hosts reached three consecutive HTTP 403 responses and were stopped; the Commons denominator remains unknown.
- 2010–2014: the frozen page queue remains 225 previously failed + 212 previously unrequested. The bounded repair made one corrected index request and one page request before the shared publications host reached its stop threshold across three scoped probes.
- OCR: all four saved PDFs were processed locally. **340/350 pages** yielded text, totalling **832,193 characters**; blank/image-only pages were retained as blank rather than fabricated. Representative pages were visually reviewed.

## Final checks

- All **407** repair-manifest records exist in the formal 06 database and have enumeration/content linkage.
- Repair segments preserve separate semantic roles: **447 question-context** segments, **608 answer government-response** segments and **3 statement government-response** segments; statements have no fabricated question context.
- Duplicate `(source_id, external_id)` groups: **0**.
- OCR targets marked extraction-success: **4/4**; OCR extraction segments: **340**.
- Annual, quarterly, monthly and decade totals reconcile to the same read-only snapshot; final counts match the expected repaired baseline.
- All four refreshed figures passed panel-alignment, PDF text-size, strict rendered-collision and visual review checks.
- No full database hash rerun, full ingestion smoke test or successful-record re-download was performed.

## Deliverables

- Repair ledger: `../repair_ledger.csv`
- Queue summary: `queue_summary.csv`
- Final delta: `final_delta_check.csv`
- Verification: `final_verification.json`
- OCR quality: `../evidence/policy_ocr_quality.csv`
- Distribution/coverage report and CSVs: `final_distribution_coverage/`

Residual access failures are preserved with actual request URLs, final URLs, timestamps, HTTP status, response bytes and host-stop checkpoints. They remain conditional source gaps, not evidence of absent government records and not a claim of continuous 1988–2026 coverage.
