# Australian governmental sources: bounded interface and native-text confirmation

Recorded 12 October 2026. This completes public-source confirmation for the Australian rebuild; it does not import a production corpus or open a collector. The publication interval remains **1988-01-01–2026-09-21**, with September partial. Current retrieval, deposit creation/version and publication/sitting dates remain separate. The primary **100 GB decimal** peak envelope and **15 GiB** physical floor remain; approximately 35.96 GB free before this check does not establish local capacity for 100 GB.

**Choose the exact UQ RAPID-CDL deposit for parliamentary importer preparation and PM Transcripts' working single-ID XML route for named executive records.** Parliamentary complete-unit/role acceptance and PM catalogue/date discovery remain necessary before scale. Preserve the seven-original/821-candidate historical government checkpoint unchanged; neither these samples nor the ready-table metadata replace it with an imported corpus.

## Real access and bounded payload

The [RAPID deposit](https://zenodo.org/records/22868754) and its public record/file API respond successfully. README, `session.parquet` and `speaker_detail.parquet` were downloaded in full because they total only 125,482 bytes; all three sizes and deposited MD 5 checksums match. Paragraph trailer/footer and **two explicit byte ranges** return HTTP 206 with exact Content-Range and lengths. Those two ranges contain Parquet row groups 22 and 52, totaling **23,891,320 bytes**, rather than the 500,382,872-byte full paragraph file. Its full-file checksum is consequently still unverified. No production database, old source store, model, PDF or historical collector was touched. [Machine-readable finalized evidence](government_evidence.json).

All network checks combined transferred **24,160,712 bytes** across 16 requests under one **26,214,400-byte (25 MiB)** cap: ten HTTP 200, four 206 and two 403 responses. The default sandbox could not resolve Zenodo; the same authorized bounded public requests then ran with network access. Raw returns, request times, status/headers, bytes, hashes and scripts remain unpublished in package 38 `local_government/`. No challenge workaround or repeated failed-route loop was used.

## Parliamentary source, dates and units

The version is **2026-09-21**, DOI **10.5281/zenodo.22868754**, with four analytical tables plus README totaling **502,442,451 bytes**. It derives from official federal Parliament XML/SGML and retains original sitting URLs. Its **6,911,269 paragraphs** are recorded parliamentary/procedural text, not independent speeches or government speakers. A native record preserves `para_id`, `session_id`, order, speaker/detail keys, debate and procedural-unit keys/types, and text. These generated IDs must be qualified by the deposit version; sequence/ID order is not publication-date order. [Deposited schema documentation](https://zenodo.org/records/22868754/files/README.md?download=1).

The complete checksum-matched sitting table establishes **3,300 rows and distinct IDs**, **1,775 House /1,525 Senate**, with **1996-05-30–2026-09-08** nominal sitting-start dates. It has no missing dates or original URLs, four missing PDF links, and two repeated chamber/date combinations requiring the date checks below. The nominal day can cover proceedings continuing after midnight. Only three sittings occur in 1996 and none in 1997; the bounds do not establish a continuous 1996–2026 archive.

| Declared frame | House | Senate | Pooled | Interpretation |
|---|---:|---:|---:|---|
| Fixed January 1988–September 2026 calendar |247/465 observed months;1,775 sittings|248/465;1,525|249/465;3,300|Source presence, not complete Australian government coverage|
| June 2024–August 2026 |21/27;127 sittings|21/27;108|21/27;235|Both chambers share the same 21 observed months|
| September 2026 partial |2 sittings|2|4|Latest recorded sitting 8 September; no 21 September completeness claim|

The [chamber-by-month CSV](government_session_month_counts.csv) records all 930 chamber/calendar cells with explicit **sittings** units, unchanged source dates, latest observed date and unverified completeness. In the recent frame no rows occur in **December 2024–January 2025, April–June 2025 or December 2025**. Compare official calendars before deciding whether these are non-sitting periods or acquisition omissions. Adding September gives 22 observed parliamentary months within the 28-month media/community candidate window. Full zero-row and observed ranges are retained in the JSON; no imported international 465-month claim is used.

Two date/URL conflicts are specifically flagged: House `session_id=2146` is dated **2009-06-04** while the recorded original path identifies **2009-06-03**; Senate `4891` is dated **2010-03-09** while its path identifies **2010-02-23**. One original-page request for each returns 403. URL dates alone do not authorize a correction; these source records and aggregate dates stay unchanged pending original verification. They do not affect the recent frame. The four missing PDF links concern IDs 1384,1546,4353 and 4404; their ParlInfo URLs remain present.

## Text and length measurements

Two nonrandom file blocks were selected after joining session-statistic ranges to dates: **group 22 House** and **group 52 Senate**. They each decode 122,880 paragraphs. Their full decoded text is not saved as a second corpus; the downloaded compressed ranges and 72 fixed-position era/type examples remain local. This is a convenience/block check, biased by file order, chamber, dates and procedural mix; block edges can truncate sittings/procedural units. It neither validates complete speeches nor supplies a representative full-corpus length estimator.

| Measurement of decoded block | House group 22 | Senate group 52 |
|---|---:|---:|
| Measured UTF-8 text bytes |48,740,272|37,692,082|
| UTF-8 bytes/paragraph: mean; median;95 th percentile |396.65;318;1,065|306.74;162;1,000|
| Whitespace words/paragraph: mean; median;95 th percentile; maximum |66.31;53;179;562|51.07;26;169;486|
| Empty strings retained |3,000|3,694|
| Null speaker-detail keys retained |4,984|5,963|
| Paragraphs dated June 2024 or later in these blocks |50,257 across 11 months|31,318 across 13 months|

These are native whitespace word counts, **not model tokens**. Sampled date limits are 2011-05-24–2026-09-08 and 2011-06-15–2026-09-07. Every sampled non-null speaker-detail foreign key resolves and lies inside the exported validity interval; session keys resolve and paragraph IDs are unique within each block. That bounded result does not establish full-table validity. The export contains dated party/name attributes but **no ministerial-office or governing/opposition field**. Government, opposition, independents, parliamentary officers, procedural material and quoted/petition holders require separate dated evidence. Empty text or unresolved speaker context is a recorded structural issue, not evidence of absent emotion and not a semantic exclusion rule.

The ready data already contain paragraphs; the Canadian CCF article-to-unit multiplier must not be copied onto them. Plain UTF-8 text measured here differs from Parquet's encoded uncompressed-byte statistics. Before estimating embeddings, choose the eligible source/date/procedural view and any reconstruction/segmentation rule. Preserve all unit-to-sitting/speaker/original lineage; do not treat row groups as observation windows.

## Executive single-record API is operational; discovery is conditional

The [official developer page](https://pmtranscripts.pmc.gov.au/developers) documents full release XML by ID. **`/query?transcript=<id>` works** for four deliberately named records across older/current formats. The actual schema is `response/item` with `field_date` in DD/MM/YYYY and HTML in `content` CDATA, differing from the documentation's `transcripts/transcript/release-date` example. The HTML page for 46784 also contains readable original interview text; an Incapsula script marker within ordinary HTML is not itself an access challenge.

| Native release | Verified release date/type | Readable UTF-8 bytes | Whitespace words | Native-holder limit |
|---|---|---:|---:|---|
|[46220](https://pmtranscripts.pmc.gov.au/release/transcript-46220)|2024-09-06 Transcript: National Cabinet remarks|1,896|323|PM-labelled remarks|
|[46784](https://pmtranscripts.pmc.gov.au/release/transcript-46784)|2025-06-04 Transcript: Perth radio interview|6,101|1,123|PM and two distinct hosts, with quoted language|
|[47643](https://pmtranscripts.pmc.gov.au/release/transcript-47643)|2026-09-21 Transcript: UN press conference|22,490|3,886|PM and journalists; New York venue remains Australian institutional source|
|[7370](https://pmtranscripts.pmc.gov.au/release/transcript-7370)|1988-08-07 Media Release|2,641|431|UNKNOWN title and visible OCR artifacts; original scan not checked|

All four native dates are eligible. These are examples chosen by ID, not a probabilistic sample, inventory denominator or evidence of monthly completeness. Three modern `document` values are the site root, not an original-file link; preserve their canonical release URLs. The older record supplies a PDF URL, with no PDF fetched. Current retrieval does not prove historical-body equality. Formatting varies substantially: National Cabinet remarks occupy one HTML paragraph while the interview has 54; an HTML paragraph is not automatically an utterance or uniform analytical unit.

The earlier frozen XML-index 404 and date-filter Incapsula result remain preserved and were not retried. A working one-ID request proves neither catalogue pagination nor an executable native date-filter route. Exact eligible/recent/month totals stay **unknown**, not zero; the site's approximately 26,000 headline is not a study inventory. Use the one-ID interface for a small named executive supplement while resolving lawful reproducible date/ID discovery before any production tranche.

## Rights, admission and evidence boundaries

[RAPID metadata/README](https://zenodo.org/records/22868754) specify **CC BY-NC-ND 4.0** and link Parliament's terms; the APH copyright page is 403 to the browsing tool. Public access and an open-source parser do not establish unrestricted redistribution of transformed text. Retain source/version/attribution and check intended derivative distribution against the stated terms. PM transcript text has [CC BY 4.0 terms](https://pmtranscripts.pmc.gov.au/copyright), with Coat of Arms, photographs/graphics and item-specific exceptions. Their licensing and provenance are separate from the truth of any quoted claim.

Preparation can proceed with a version-qualified four-table importer and a tolerant single-ID PM XML parser. A real intake still needs full four-table checksums, complete-unit/debate/procedural lineage, named date/PDF issues, dated offices/governing roles, applicable-calendar comparison and a measured peak-operation plan. PM catalogue discovery and older OCR checks remain conditional. No climate relevance, affect/risk association or fear attribution was measured in this check. Readability and dated source presence are established only to the stated depth; no fear time series or representative three-role result follows from these counts.
