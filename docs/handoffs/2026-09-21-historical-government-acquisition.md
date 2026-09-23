# Execute: historical government policy and ministerial discourse acquisition

## 1. Authorization and objective

Work in `/Users/jarlgiovanni/Desktop/fear_of_temperature`.

Dai has approved collecting related-department historical policies and a separate ministerial-answer/statement series. This is an execution instruction, not another feasibility-only exercise. Read:

- `docs/decisions/2026-09-21-historical-policy-and-ministerial-series.md`
- `docs/decisions/2026-09-21-single-ingestion-and-stage-boundaries.md`
- `docs/research/2026-09-21-pre2010-government-source-review.md`
- `docs/PROJECT_LOG.md`

Create a goal if available: enumerate and acquire the bounded historical-policy and Commons ministerial written-answer/statement tranches below, ingest genuinely new records once into the existing database, extract supported text, and report source-specific progress and coverage with final acceptance. If an old goal prevents creation, record that condition and continue substantive work. No token budget is requested.

Do not modify the proposal, run embeddings or models, introduce Jev, expand cleaning, or create repeated sample-approval gates. Do not alter unrelated notebook/code work from other tasks. This instruction authorizes acquisition within the scope below; proceed without another routine approval request.

## 2. Fixed scope and order

### A. Formal policy backfill: 1988-01-01 through 2009-12-31

Keep the existing DEFRA batch. First enumerate available GOV.UK policy-paper records for DTI and DECC, then verified UK DoE/DETR/MAFF/BERR records within this period. Confirm official organisation identifiers and jurisdiction before adding filters; UK DoE and Northern Ireland DoE are not interchangeable. If a former body lacks a searchable current identifier, record the missing route instead of inventing a slug or treating a zero return as historical absence.

Use topic-independent enumeration within the stated source/type/date boundaries where supported. Preserve original publication date, current hosting organisation, original issuing body when evidenced, document number/ISBN, and type drift.

Known discovery checks (not the whole corpus):

- 2003 DTI: https://www.gov.uk/government/publications/our-energy-future-creating-a-low-carbon-economy
- 2009 DECC: https://www.gov.uk/government/publications/the-uk-low-carbon-transition-plan-national-strategy-for-climate-and-energy
- 2006 DEFRA, already present: https://www.gov.uk/government/publications/climate-change-the-uk-programme-2006

For historical files absent from GOV.UK, use the official UK Government Web Archive index to identify available Defra/predecessor sites. Only enumerate policy/publication index routes within verified departmental sites, not an unbounded whole-web crawl. Define the selected URLs, date bounds and accessible index partitions in the manifest before downloading their contents. Archive capture dates are not publication dates; 2010+ captures may contain pre-2010 documents. Preserve both dates and evidence. Missing dates remain unknown, not guessed.

UKGWA export is capped at 10,000 search results per query. Partition and deduplicate where supported; truncated/search-only results are not a complete denominator. If replay/export is inaccessible, log that route's failure and continue with accessible official collections. Do not let one archive endpoint block the whole task.

UKGWA references:

- https://www.nationalarchives.gov.uk/webarchive/find-a-website/atoz/
- https://www.nationalarchives.gov.uk/webarchive/find-a-website/how-to-find-an-archived-website/

Do not add UNFCCC reports, ProQuest, other countries or every government document type to this first tranche. They remain identified follow-on candidates.

### B. Independent ministerial series: 1988-01-01 through 2026-09-21

First implementation scope: **House of Commons ministerial written answers and written ministerial statements**, concerning the environmental/climate/energy departmental responsibilities followed over time. Process 1988–2009 first, then the later interval so the channel does not abruptly end at 2010. Oral debates, Lords and general MP speeches are outside this tranche.

Use official department/section labels and dated ministerial office evidence. For the later period, follow documented transfers of the climate/energy remit, including DECC and its verified successors, rather than dropping records simply because the department name changes. Record any broader-business-department mixture; do not silently claim a constant remit.

Official starting points:

- https://www.parliament.uk/commons-hansard/
- https://api.parliament.uk/historic-hansard/sittings/1988/index.html
- https://api.parliament.uk/historic-hansard/written-answers/1988/jul/20/greenhouse-effect

Follow official date indexes, departmental sections and officially documented APIs/downloads when available. Do not assume the historic `api.parliament.uk` hostname guarantees a supported REST interface. Historic Hansard (1803–2005), the 1988–2016 archives and modern services overlap; deduplicate by stable official IDs and date/chamber/column/question/contribution identity, not merely URL.

Enumerate all eligible written answers/statements in each approved department/date stratum where feasible, not only hits for fear/climate keywords. If a period only permits topic search or partial discovery, preserve query rules and label the result as observed/topic-selected; do not invent a complete all-topic denominator.

Record separately:

- government respondent and role at the time;
- questioner and question/context;
- answer or statement text;
- parliamentary date, available publication/update dates and retrieval time;
- chamber, department, official IDs, volume/column where supplied;
- genre (`ministerial_written_answer` or `ministerial_written_statement`);
- attribution evidence/status.

Before standalone written-statement categories existed, retain the original archive category. Do not fabricate genre continuity. A minister's parliamentary membership or party alone does not establish that every utterance is an official government response. Unresolved attribution remains unknown and excluded from confirmed-government counts, while preserved as a candidate record.

## 3. Enumeration, expected counts and progress

For each source/year/genre partition, enumerate and freeze its deduplicated manifest, calculate genuinely new records after comparing with the database, then download automatically. Do not stop after a metadata feasibility report.

Report these quantities distinctly:

- discovered candidates (provisional while discovery continues);
- enumerated targets and completeness/truncation status;
- matches already in the database;
- net-new expected publication/answer/statement records;
- expected content objects (separate from records and parliamentary sittings);
- attempted, downloaded, extracted, failed/deferred and unattempted objects.

Expected targets remain unknown until their partition has been enumerated. Never prefill invented target counts. Freeze targets before processing each partition, and log any legitimate revision. Keep A and B progress separate; do not compare a policy document count directly with a speech-turn count.

## 4. Single ingestion and provenance

Authoritative working database:

`work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb`

Reuse the existing five core tables and provenance/batch/voice structures. Do not create another working corpus/database or reimport the original 1,020 records. Create a new acquisition batch record for genuinely new additions, not new identities for the old sources.

Use existing voice-attribution and segment relationships where suitable to distinguish questions from answers; do not place question text inside government-response text. Add only minimal fields/relations needed to preserve real source structure and document their mapping. Keep source HTML/PDF as evidence; cleaning belongs to its later stage.

Check for an active database writer before writing. Serialize writers rather than allowing two tasks to modify the same DuckDB concurrently. A recovery backup is acceptable; it is not a competing working database. Preserve 04/05 frozen snapshots and all stable existing identities.

Store alternate archive/live locations under the same confirmed identity where appropriate. New bytes can create a content version; new retrieval attempts alone must not create duplicate content. Record hashes, timestamps, original URLs, replay URLs/capture dates, response status, extractor version and truthful source locators. Do not assign an old publication date to a later revised text without recording the version limitation.

Use modest concurrency, rate limiting, finite retries and object/partition checkpoints. Never bypass authentication or access controls. Existing project authorization remains valid; do not fabricate institutional ethics determinations or publish raw copyrighted text.

## 5. Outputs and one final acceptance

Create a reports/scripts directory (not another database), for example `work_packages/M1_source_access/07_historical_government_acquisition/`, noting that this replaces the withdrawn 07 text-preparation proposal with a different task.

Deliver:

1. Collection scope and department/genre register, distinguishing verified lineage from unresolved mappings.
2. Frozen partition manifests, deduplication/net-new counts and collection/extraction statuses.
3. Real newly acquired files and text in the existing database, with reproducible resume commands.
4. Before/after annual and quarterly distributions, separately for policy papers, ministerial answers and ministerial statements. Mark partial 2026 and missing/unknown coverage.
5. A compact HTML report: what was added, what remains unavailable, and how much pre-2010 coverage improved. Do not force temporal balance by oversampling or duplicating records.
6. Final integrity checks: manifests/statuses reconcile, no duplicated existing records, valid version/segment links, correct voice separation, counts match plots and original frozen snapshots remain unchanged.
7. Updated `docs/PROJECT_LOG.md` with actual results and residual issues, not a proposal rewrite.

Reuse existing acceptance evidence for unchanged paths. Add/check only what actual source differences require; do not build a new testing project or repeat full-corpus rebuilds. Complete one consolidated final acceptance. Report observed coverage honestly; months with no observations are not evidence that no government speech existed.

Do not mark the acquisition goal complete merely because code or schema exists. Distinguish all targets attempted from all text successfully obtained. If a whole necessary source route remains inaccessible, report partial delivery and its concrete blocker while completing independent accessible routes.

No Git commit/push is requested here. Never stage raw files, database files or bulk text exports. Finish the bounded acquisition and report results directly without another routine confirmation round.
