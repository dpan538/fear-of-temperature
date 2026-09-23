# Government corpus: targeted gap repair

Prepared for Dai on 22 September 2026. This is an execution-window instruction, not a record of completed repairs. Investigation used existing files/code and a few official web lookups; no corpus download, database change or ingestion was performed in the decision window.

## Objective and boundaries

Repair the identified government-corpus gaps, incrementally ingest verified additions into the existing 06 database, and update distribution/coverage evidence once. Follow this bounded task rather than restarting the previous full acquisition goal. If Dai instructs you to establish a goal, use this objective; do not reopen an unbounded “complete all historical government discourse” goal.

Project: `/Users/jarlgiovanni/Desktop/fear_of_temperature`.

Authoritative database: `work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb`.

Inputs are under `work_packages/M1_source_access/07_historical_government_acquisition/` (abbreviated **07** below). Put new repair manifests, evidence and reports in `07/targeted_gap_repair/`; preserve the old manifests/reports as the before-state. Reuse existing acquisition and ingestion code with minimal targeted changes, not a second database architecture.

Baseline reported and reconciled by the previous task: 239,179 documents; 1,054 policy-source records (1,053 policy_paper plus one retained guidance mismatch); 235,420 written answers; 2,705 written statements; 3,622,039 text segments. Check for concurrent changes before using these as the before-counts. Preserve other windows' work.

Retain the approved Commons department and genre boundaries, the existing study endpoint and all-topic departmental sampling. No climate-keyword selection, new countries, Lords, oral debates, embeddings, models, broad cleaning or proposal revision. Do not reopen project collection permission already recorded or represent it as formal institutional ethics approval. Previously blocked archive access remains blocked unless the normal official route becomes accessible; do not bypass access controls.

## 1. Repair existing Hansard answer payloads first

Input: `07/manifests/hansard_answer_acquisition_status.csv`. Its 85 unsuccessful answer targets all recorded HTTP 200; they are not 85 transport failures.

### A. 79 nested-department failures, all dated 2006-05-22

The current `_hansard_department()` takes the FIRST `hs_6bDepartment` in Navigator. The saved payloads contain two department nodes:

- 41: International Development → Environment, Food and Rural Affairs.
- 38: International Development → Trade and Industry.

Example: external ID `003e54c5-1ee7-4ef0-8aaa-8217304cdb86`, Dairy Calves. The saved JSON Navigator has the question under DEFRA, while the parser returns International Development. The question and answer are present.

Resolve the nearest valid department ancestor of the actual item by IDs/ParentId where available; check it against the saved daily tree and speaker/office evidence. Do not merely substitute “last department” without checking hierarchy. Retain ambiguous cases as unresolved. Reparse the existing local JSON and create a versioned repair decision for each target. No network request is needed where the saved evidence is sufficient. Preserve raw bytes and previous failure history.

### B. Four question-boundary failures with locally visible question and answer

| External ID | Date | Title | Observed issue |
|---|---|---|---|
| 06101841000010 | 2006-10-18 | Ragwort | Numbered question `(1) To ask…`, followed by continuation `(2)…` |
| 07031215000029 | 2007-03-12 | River Thames: Environment Protection | Speaker prefix inside text before `To ask…` |
| 07031943000036 | 2007-03-19 | Employment: Regulation | Numbered multipart question and continuations |
| 07101133000055 | 2007-10-11 | Pirbright Laboratory: Inspections | Speaker prefix inside text before `To ask…` |

Use structured question tags and contribution order/attribution where supported. Keep question continuations as question context, not ministerial speech. Preserve precise original offsets/IDs and text. Repair only deterministic boundaries; do not manufacture missing attribution.

### C. Two cases needing separate resolution

- `06071282000011`, 2006-07-12, Asda: one saved Contribution attributed to the questioner contains a QuestionText followed by apparent correction/answer prose inside a Question wrapper. Do not attribute all of it to the questioner or invent the minister. Check the official rendered Hansard record to resolve structure and attribution; otherwise retain an explicit unresolved-attribution status.
- `07091719000037`, 2007-09-17, Companies House: actual API error payload. Try the ordinary official rendered/archive entry as fallback, verifying publication date, department and item identity.

The first 83 cases are **repair candidates**, not guaranteed new documents. Match against existing identities before insertion. Add a few focused regression fixtures for the actual parser defects. Check affected same-shape records using existing metadata/payloads if needed; do not reprocess the entire corpus or silently rewrite accepted records. If a repair exposes a wider material attribution problem, report its measured scope before a broader correction.

## 2. Close the known 2010–2014 answer acquisition queue

Window: **2010-05-01 to 2014-09-11**.

Inputs:

- `07/manifests/hansard_gap_archive_index_status.csv`: 20 failed date indexes (9 HTTP 403; 11 HTTP-200 unexpected HTML).
- `07/manifests/hansard_gap_archive_page_target_manifest.csv`: 1,063 known page targets.
- `07/manifests/hansard_gap_archive_page_acquisition_status.csv`: 851 attempted, comprising 626 successful and 225 HTTP-403 failures.
- Derive the 212 not-yet-requested pages by target/status anti-join; reconcile with the existing unprocessed list.

First resolve the 20 indexes using the existing attempt history and actual official links/session identifiers. Distinguish wrong URLs/error pages, a verified sitting with no written answers, non-sitting dates, access failure and genuine unavailable content. A 200 or 404 alone does not establish an empty day. Do not retry a large permutation of guessed session URLs.

Freeze any newly discovered page targets as a separate manifest revision. Then fetch only the union of the **225 failed + 212 unrequested known pages + genuinely new targets**, deduplicated by canonical source identity. Do not re-fetch the 626 successful pages. The initial 437-page queue is not a count of missing answers. Failed indexes can conceal an unknown additional number of pages/items.

Use one worker, initially at least 3 seconds between requests, and respect a longer Retry-After. Allow at most one later retry for a transient failure per route in this repair pass. Repeated 403 is not proof of throttling: inspect the response. On three consecutive access-denied/throttled responses, stop that host queue and preserve a checkpoint; continue independent local tasks. Do not rotate proxies, bypass challenges, loop overnight or poll through a long cooldown. An ordinary alternative official representation can be used if accessible, with its real URL and evidence recorded.

For every page, extract all in-scope records, preserve question/answer separation and cross-page continuation. Record actual request counts separately from extracted record counts. Recoverable work should continue without repeatedly asking Dai to approve the already specified scope.

## 3. Repair historical date gaps using bounded official alternatives

### A. Volume 200: 1991-12-02 to 1991-12-13

The existing `S6CV0200P0.zip` is an HTTP-200 error page, not a usable ZIP. Preserve the failure evidence. Prefer the official daily Historic Hansard index and follow only Commons written-answer items for the approved departments within this date window:

<https://api.parliament.uk/historic-hansard/sittings/1991/dec/02>

This index was directly verified in the decision review: it identifies Commons volume 200 and includes Trade and Industry, Agriculture/Fisheries/Food and other department headings. Individual item retrieval still needs execution-time verification. Do not substitute Lords or oral answers. Enumerate actual sitting days; check against existing identities before adding records. No need to re-download 319 good ZIPs or repeatedly request the known error ZIP.

### B. Newly identified source seam: 2004-10-05 to 2004-12-31

The bulk-volume route stops at 2004-10-04 and the next route begins in 2005. In the coverage table, November and December 2004 are unsupported by either route. This is a cross-route acquisition gap, not evidence of absent government speech.

Official Hansard search results list Commons written answers for 2004-12-01 and 2004-12-15, including DEFRA records:

- <https://hansard.parliament.uk/commons/2004-12-01>
- <https://hansard.parliament.uk/commons/2004-12-15>

These two modern pages were discoverable in search but not successfully opened by the review browser; do not claim their API or full-text availability has already been verified. An official Publications archive statement page for the same period is also discoverable:

<https://publications.parliament.uk/pa/cm200405/cmhansrd/vo041201/wmstext/41201m01.htm>

Enumerate the actual Commons sitting calendar/index within the bounded seam and retrieve the approved departments' written answers/statements via the existing Hansard API or linked official Publications archive. Verify format on one real item before running the small bounded tranche. Freeze targets, then ingest only missing identities. Do not extend into all of 2004 or re-fetch 2005 onward. Mark recess/non-sitting days only with calendar evidence.

### C. January 1988 boundary

Before calling 1988-01-01 to 1988-01-10 a collection gap, check the official sitting calendar. The first bulk date of January 11 may reflect recess. Correct the coverage explanation if supported; absence of a sitting is not missing documentation. No speculative daily scraping.

## 4. Resolve the nine statement candidates without assuming nine missing statements

Inputs: the 7 failures in `hansard_candidate_acquisition_status.csv` and the 2 failures in `hansard_gap_written_acquisition_status.csv`.

- Priority in-scope target: `10022378000029`, 2010-02-23, Energy and Climate Change, Departmental Expenditure Limits, Edward Miliband. The official statement index lists this item and minister:
  <https://publications.parliament.uk/pa/cm200910/cmhansrd/cm100223/wmsindx/100223-x.htm>
  Follow its real link/anchor, then deduplicate against existing statements.
- Six old candidates have search attribution to Prime Minister, Cabinet Office, DCMS, FCO, Justice or Scotland: `06121471000030`, `07051786000018`, `09021274000015`, `09021291000008`, `10022416000013`, `10022416000014`. Verify department scope against official index/detail evidence. If out of scope, record exclusion and evidence rather than counting them as unrecovered government records in our target series. Do not infer publication date from ID digits: the two `100224…` IDs are listed under February 23 by the search and the official February 23 statement index includes those ministries/items.
- `11021758000013`, 2011-02-17, Supplementary Estimates, is search-attributed to Defence/Liam Fox; verify and exclude if outside the approved department scope.
- `1009068000001`, search date 2010-09-07, is titled Written Ministerial Statements with 29 contributions and no first speaker. It may be a container rather than a single statement. Check September 6–7 official daily indexes, resolve the actual date, enumerate any in-scope child statements and deduplicate them. Never insert the whole container as one ministerial statement or count already held children again.

Keep `out_of_scope`, `already_present`, `recovered`, `unresolved` distinct. A failed API request alone does not prove either eligibility or absence.

## 5. Four downloaded historical policy PDFs: bounded OCR recovery

These are extraction gaps, not missing downloads. Locate their saved bytes/content versions and attempt OCR only for these four, reusing an available local tool:

- `https://assets.publishing.service.gov.uk/media/5a74b991e5274a3cb2866ade/2235.pdf`
- `https://assets.publishing.service.gov.uk/media/5a75978be5274a436829873f/0545.pdf`
- `https://assets.publishing.service.gov.uk/media/5a7c182740f0b61a825d66b2/2614.pdf`
- `https://assets.publishing.service.gov.uk/media/5a7c1f5940f0b645ba3c6d4f/5761.pdf`

Keep original content versions unchanged and record the OCR extraction run/tool/version/page mapping. Inspect representative pages for legibility before treating the output as usable text. Do not retransmit PDFs to a new external service or start a corpus-wide OCR/cleaning project. If local OCR is unavailable or output unusable, retain needs_ocr and state the concrete blocker. Do not create duplicate documents/content objects for OCR output.

## 6. Incremental storage, reporting and stopping rules

1. Create one repair ledger with gap ID, source, original ID/URL/date, original failure, local repair or fallback route, target unit, attempted result, disposition and resulting database identity. Preserve actual requests, timestamps, source bytes/hashes and extraction provenance. Keep expected quantities separate by unit: dates, pages, items, files.
2. Use the existing five-table storage and bounded transactional ingestion. Reuse stable IDs/content versions. Add only genuinely new material; changed extraction of existing bytes is a new extraction lineage, not a duplicate source. Take the normal recoverable checkpoint once before writes; do not run a full temporary ingestion followed by a full replay.
3. Do not run `all`, `--no-resume`, global re-enumeration, complete database rebuild, all-file hashing, or another full ingestion smoke test. Run only targeted parser checks and one final delta/count/linkage reconciliation. If an existing CLI cannot restrict itself to the repair manifest, add a minimal filter instead of invoking the broad command.
4. At completion, report each queue's expected/attempted/recovered/excluded/already-present/unresolved counts with units; show genuinely new document counts separately from extraction/attribution repairs. Reconcile before + additions (and explicitly justified corrections, if any) = after by genre.
5. Refresh the existing annual, quarterly, source-by-month coverage tables and the affected figures once. No additional workbook or redesigned report suite. Show before/after coverage of 1991-12, 2004-Q4, 2005–2010 parser failures and 2010–2014 page gaps.
6. Coverage remains conditional on route/department/genre. Verified zero, non-sitting, unsupported, failed, unrequested and unknown denominator must remain distinguishable. Full retrieval of enumerated targets does not demonstrate complete UK government coverage. Ministerial answers/statements do not fill missing historical policy-publication coverage by substitution. Keep TNA/predecessor policy archive discovery as a separate unresolved scope item.
7. Deliver a concise Markdown + HTML repair report, repair ledger/target manifests, updated distribution/coverage CSVs, changed relevant figures, final delta check, and an append-only PROJECT_LOG entry. Do not modify proposal or unrelated files; no commit/push in this task unless Dai separately instructs it.

Completion means this bounded pass and its reporting are finished, with residual external blockers explicit. It does not require every remote archive to become accessible. Do not turn remaining 403/WAF cases into endless engineering work or label the entire 1988–2026 corpus complete.
