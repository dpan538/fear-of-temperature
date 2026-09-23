# Execution handoff: recover historical gaps, prioritising coverage

Read `docs/decisions/2026-09-22-coverage-first-historical-gap-recovery.md` first. This handoff changes priority after the completed targeted-gap-repair tranche; do not rerun the old handoff in full.

## Objective

Identify and use traceable alternative sources to fill missing early government policy publications and the specific parliamentary time gaps. Modern data volume is sufficient for the current acquisition stage. Coverage takes priority over distribution, charts, corpus expansion and speculative engineering.

Project: `/Users/jarlgiovanni/Desktop/fear_of_temperature`.

Reuse the authoritative 06 database, the 07 manifests and `07/targeted_gap_repair/` before-state. The latest reported baseline is 239,586 documents and 3,623,437 segments; check for concurrent changes before using it. Write this tranche's new evidence under `07/historical_coverage_recovery/`. Do not overwrite previous frozen evidence or rebuild the whole database.

## Track A — early policy publications: required alternative-source work

Target the missing early part of the existing study scope, especially 1988–2009 and the already approved DoE/MAFF/DETR/DTI/BERR/DECC/DEFRA predecessor routes. Retain the approved department-remit boundaries; record organisational succession rather than projecting current department names backward.

1. Build a compact gap register by department, historical interval and document genre from existing evidence. Identify whether the missing element is a catalogue/index, a known publication or its text. Do not manufacture an expected publication count.
2. Investigate the normal UK Government Web Archive/departmental archive routes, official publication catalogues, Parliament deposited-paper or official scanned-publication holdings, and other institutional repositories holding copies of the same official documents. These are candidate routes to verify, not claims that their required holdings are present. Search/catalogue access can establish a target even when the content is not downloadable.
3. Prioritise routes that can enumerate publications over keyword search hits alone. For each route record the actual years, departments, included publication types, catalogue completeness limits, access method and reusable original identifiers.
4. For an actual alternative copy, verify issuing department, title, publication date, document/series number and completeness against available official evidence. Record both original publisher identity and actual retrieval provider/URL/version. Check applicable access/reuse conditions without reopening project permission already recorded.
5. Preserve policy-publication inclusion rules. Do not relabel annual accounts, operational reports, parliamentary answers, statements or third-party commentary as policy papers merely to fill a year. If an important early policy type does not fit the stored genre vocabulary, document the exact example and mapping needed; do not silently broaden the corpus.
6. Once a route and document identities are supported, proceed with bounded enumeration and retrieval within the existing authorised scope. Use local OCR for official scanned copies where needed. Do not pause for repeated general confirmations. Escalate only a concrete scope choice or external access requirement that the current instruction cannot resolve.
7. If a route is blocked, keep its catalogue/target evidence and move to an alternative. Do not conclude the historical-policy problem is solved by the existing ministerial-answer corpus. If alternatives are exhausted, report exactly which archive, date interval and access step remain unavailable and the specific request Dai could make to a library/archive. Do not send messages to third parties without an explicit instruction.

## Track B — parliamentary date gaps

1. **2004-10-05 to 2004-12-31 Commons**: enumerate the missing window's approved departments and written genres. The denominator is currently unknown; Lords material is not a replacement.
2. **2010-05-01 to 2014-09-11 answers**: restore the 20 unresolved date indexes and recover the 225 failed + 212 unrequested known pages, using original record identities. Pages/indexes/items remain separate units. Do not re-download the successful subset.
3. Evaluate ParlParse/TheyWorkForYou XML as a traceable alternative: its documentation describes Commons written answers, separate question/reply fields, speakers and original Parliament URLs. First inspect representative existing-overlap and missing-date files; if identity and provenance are sound, retrieve only the relevant missing dates/items. No full mirror clone or modern-data expansion.
4. Match by date, chamber, department, original question/record ID, column or original URL as available. Different provider IDs alone do not make a new document. Preserve provider-specific transformations and unresolved mappings; do not silently replace original text with a processed mirror version.
5. Named Companies House access failure can be addressed within this route. Do not spend another work package trying to infer the speakers of excluded mixed records.

Verified route documentation from the decision review (individual target availability still requires checking):

- <https://commonshansard.blog.parliament.uk/2026/05/01/historical-hansard-bridging-the-gaps/>
- <https://parser.theyworkforyou.com/hansard.html>
- <https://data.mysociety.org/datasets/theyworkforyou-api/>

## Disposition of ambiguous records

- Mark documented inseparable mixed text / unreliable attribution as `excluded_ambiguous_text_or_attribution` (or the equivalent existing status); retain raw evidence and a reason.
- Apply this to the documented Asda and Self-regulating Bodies cases. Do not fabricate speakers or keep retrying merely to reach 100%.
- Mark the cross-date statement container as a non-includable container unless individual children can be independently identified. Do not count a container as one statement; do not discard already verified children.
- Do not delete historical evidence or mutate a shared content object to remove other documents' text. Reflect exclusions in eligibility/decision records using existing schema facilities.
- Keep exclusion separate from missing/unavailable. An excluded item remains visible in the target-accounting table but is not a recovered usable item. Do not improve a completion percentage by silently shrinking its denominator.

## Storage and working limits

- Follow existing source/document/content-object/version/segment provenance and stable IDs; one incremental insertion per genuinely new identity, preserving source and extraction history. No duplicate database or repeated imports of the same batch.
- Reuse ordinary recovery checkpoints and small transactions. Run checks specific to new mappings and actual ingestion changes, not another full ingestion rehearsal or全库哈希.
- Respect published rate limits/Retry-After and access denials. Stop repeated denied requests to the same route and investigate alternatives; no proxy rotation, challenge bypass or endless retries.
- No new embeddings, semantic analysis, distribution experiments, proposal edits or unrelated software work. No commit/push unless separately instructed.

## Deliverables and acceptance

1. **Historical gap register**: department/genre/time interval, expected-target evidence, known or unknown denominator, missing index versus missing document versus missing text, and priority.
2. **Alternative-source register**: actual route, holdings evidence, access/rights conditions, canonical identity mapping, selected/rejected/unavailable reason. Include early policy sources, not just parliamentary mirrors.
3. **Recovery ledger**: expected, attempted, acquired, usable-text recovered, already present, excluded and unresolved counts with units; actual requests/timestamps and retained evidence.
4. **Incremental database reconciliation**: baseline, genuine additions, extraction changes, exclusions and final counts separately by genre. Source-level exclusions must not be misreported as deleted source evidence.
5. **Coverage-first report**: which historical intervals are now supported, which remain partial, and which specific route/action remains required. Refresh only the necessary coverage CSV during the work. At tranche completion, update affected distribution outputs once; do not redesign charts or create another audit workbook.
6. Append decisions and progress to `docs/PROJECT_LOG.md`, including unresolved external barriers. The tranche may finish with clearly documented unavailable targets, but do not call the historical coverage objective complete merely because modern volume is large or one retrieval route failed.

Start with source discovery and the gap register, then continue directly into supported, bounded recovery. Keep progress reports centred on coverage gained and remaining unknown denominators.

## Required Figure 5 in this and future summaries

Add **Figure 5. Government corpus coverage over time** to the final summary, following the new reporting requirement in the decision file. This is required alongside the existing four figures.

- Cover the entire study interval, currently 1988-01-01 through the actual frozen acquisition cutoff, with continuous monthly/quarterly time bins and visible year ticks. Use quarters for the readable whole-period overview and monthly detail/CSV where appropriate; do not omit years with no records.
- Show three separate genre lanes and source/department sublanes where required. Clearly distinguish complete within the enumerated scope, partial, unknown/incomplete enumeration, blocked, not requested, unsupported and verified zero. Non-sitting periods are not missing data. Label the last incomplete quarter/month.
- An unknown denominator receives an unknown/partial visual state, not a percentage or zero. If rates are shown, label whether they concern records, pages, indexes or content objects; do not pool these units or equate volume with coverage.
- Carry unresolved monthly components into quarterly status. Retain exclusions in accounting, avoid duplicate counting of overlapping sources, and do not display a completed quarter merely because one month has data.
- Export the underlying monthly coverage table and the quarterly aggregation rule, plus SVG/PNG/PDF for the figure. Integrate the figure into HTML/Markdown summaries. Check legibility, legend meaning, labels and clipping at normal viewing size once before delivery.
- Reuse the current coverage CSV and plotting infrastructure. Generate this final figure after the recovery tranche; it must not displace the priority work of recovering historical coverage or trigger another full database audit.
