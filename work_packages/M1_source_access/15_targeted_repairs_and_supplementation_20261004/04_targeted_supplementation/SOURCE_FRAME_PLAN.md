# Targeted source supplementation plan

Study publication interval: **1988-01-01–2026-09-21 inclusive**, with September 2026 partial. Plan snapshot: 4 October 2026. This folder contains a frozen acquisition plan, **zero acquired bodies**, and no formal database changes. Publication, metadata retrieval, future body retrieval/content version, and report times remain separate.

## Evidence and purpose

The saved 13 distribution audit records 235,824 UK written-answer parents across Historic Hansard, the archive and Questions API, before adding the targeted ParlParse mirror. These are source-specific parents; shared answers and mirrors prevent treating their sum as independent utterances. No peak is deleted or interpreted as a climate event. Pooled government dated text presence is already 465/465 months at its recorded checkpoint.

For **2015**, the saved monthly composition gives 2,674 UK Questions API answers, 64 statements, 32 DEFRA policy parents, 1,244 US EPA/DOE rule parents (648 final, 596 proposed), and 1,009 EU COM preparatory Works. The audit has operational extraction status for 2,674 answers, 64 statements, 107 US final rules and zero EU Works in that year. DEFRA's zero parent status is known to be stale relative to its saved bodies; it does **not** show that there are no policy texts. The catalogue and verified AU original frames overlap and are not added together. See `source_composition_2015.csv`; it is a copy of saved audit rows, not a live census or a cross-source deduplicated denominator.

The unresolved need is executive-publication/source depth alongside parliamentary answers in a specified shared research window. Additional EU bodies would supply another institutional publication process and genre. They would not automatically remove source bias or add 979 globally new parents: these Works already exist in the metadata frame. A mirror of an existing UK answer strengthens provenance but does not supply another independent utterance.

## Tranche A: exact missing originals

`potential_requests.csv` contains **three provisional ID routes** from Task 1's insufficient-evidence list-linked Hansard parents:

| Parent | Existing external ID | Candidate official detail route |
|---|---|---|
| `doc_5b740259ea5cdcdbdbdf` | `07051786000046` | Hansard API `/debates/debate/07051786000046.json` |
| `doc_6fe9e11be5ea65fab67e` | `09021291000017` | Hansard API `/debates/debate/09021291000017.json` |
| `doc_76b0ddb367df2c048a60` | `10022378000984` | Hansard API `/debates/debate/10022378000984.json` |

The saved linked objects are search-result JSON, so Task 1 could not apply its detail-object validator (`Overview.ExtId absent`). This is a mapping uncertainty, not proof of a corrupt answer or that the detail has not been saved elsewhere. Publication dates are left blank; digits in identifiers are not used to invent source dates. The route comes from the existing Hansard collector, and has not been probed or fetched here.

After Task 3 emits its actual `missing_original_requests.csv`, join by stable parent/external ID, use its actual request paths and preconditions, and remove any locally resolved or redundant requests. Only that released exact manifest can become the A download queue. A planning scenario is 256 KiB per detail (768 KiB for these three), with at most 2,000,000 bytes per object; sizes are unmeasured. Any further request requires a named structural/provenance need and its own frozen scope. The 202 saved-ZIP omission candidates belong to local derivation, and the 56,271 uncheckable annotations are not an acquisition queue. Other saved-detail and ZIP insufficient cases remain Task 3 work, without automatic redownload.

Expected contribution: identity/date/question-reply evidence for existing utterances, **not** improved discourse independence. Stage returned originals in this folder; preserve the failed/list-linked evidence and provide exact ID/body-boundary findings to the coordinator.

## Tranche B: two routes assessed, one selected

| Route | Evidence and possible contribution | Decision |
|---|---|---|
| Existing EU CELLAR COM preparatory English Work frame, 2015 | 1,009 reconciled Works over all 12 months; 979 have candidate English digital Items, 30 have no saved Item link. No selected Item raw file or request checkpoint is present locally. Executive preparatory publications differ from the UK parliamentary-answer mechanism. | **Select this single first tranche.** Reuse the saved enumeration/WEMI relationships; no new provider or class enumeration. |
| Existing US EPA/DOE final/proposed-rule frame, 2015 | Saved audit: 1,244 parents, only 107 operationally extracted final-rule parents, zero proposed-rule parents. Rulemaking would also add executive genre depth. Official developer documentation supports document API routes since 1994. | Defer. Existing US supervisors/checkpoints include transport and rate-limit history; this plan creates no second US queue. Missing-body target count is not independently frozen here. |

The [official CELLAR publication documentation](https://op.europa.eu/en/web/cellar/cellar-data/publications) describes language/format REST retrieval and a content-stream size limit. The [metadata documentation](https://op.europa.eu/en/web/cellar/cellar-data/metadata) explains grouped formats/languages and unique publication identification. Saved metadata supplies the actual Item URIs; documentation availability does not establish that every Item will return a readable complete body.

The [Federal Register API documentation](https://www.federalregister.gov/reader-aids/developer-resources/rest-api) describes public CSV/JSON access without an API key, documents since 1994, and a 2,000-result pagination limit. Its [developer page](https://www.federalregister.gov/reader-aids/developer-resources) distinguishes its XML rendition from the official GovInfo edition. This is route assessment only; no US document request or pagination was run.

## Frozen B contract

- **Dates and months:** every saved Work dated 2015-01-01–2015-12-31 in the existing frozen frame; all 12 consecutive months, including routine and low-volume periods. No climate, emotion, fear or headline selection.
- **Source/genre/language:** `COM` issuer, `cdm:act_preparatory`, an English (`ENG`) Expression, using the exact existing `eu_cellar_com_preparatory_en_v1` contract. No adjacent document classes are added or frozen denominators revised.
- **Parent:** distinct CELLAR Work URI. Item formats, languages, annexes, pages and versions are not additional parents.
- **Body route:** one candidate Item per Work, using the existing deterministic format preference and URI tie-break, including existing declared overrides where applicable. Preserve all saved alternatives in `selected_work_item_relationships.csv`. There are **973 selected Works with multiple distinct Item alternatives**; selecting one PDF does not prove that it includes all annexes or the complete Work.
- **Manifest:** `frozen_acquisition_manifest.csv` has **979 unique Work/selected-Item targets**. `source_frame_population.csv` accounts for all **1,009 Works**, including the **30 no-link outcomes**, without inventing their bodies. All selected formats are PDF variants: PDF 435, PDF1X 361, PDF/A-1A 179 and PDF/A-1B 4.
- **Date support:** saved official `work_date_document` and Work-query locators, with the metadata checkpoint timestamp retained. Printed Item issue date, title/issuer and full-body boundary remain pending. Retrieval in October 2026 will not prove that the body equals its 2015 version; ETag/Last-Modified, corrections and observed version evidence must remain separate.
- **Bytes:** the per-target 1 MiB value is an explicit planning scenario, **not observed Content-Length**. Total scenario: 979 MiB (0.956 GiB). Enforce an aggregate new-raw cap of **2 GiB**, a 100,000,000-byte per-Item cap, a 100,000,000-byte in-flight reserve, 64 MiB for checkpoints/error evidence, and an additional 1 GiB for concurrent repair/other activity. No extraction/OCR or formal ingestion occurs inside this download tranche. A cap/access stop yields a partial ordered tranche with exact observed counts; it does not permit a wider or replacement selection.

The interval is nested within the already documented Paris preparation window (2013-12–2017-12). The independently dated event is the **12 December 2015** Paris adoption, documented by [UNFCCC](https://unfccc.int/process-and-meetings/the-paris-agreement). The event justifies choosing a shared study year; it does not classify these Works as climate responses. A single year has little post-adoption time and cannot by itself support an ITS or comparable role series. Adjacent years require a later scoped decision after this first tranche's structural accounting; no automatic extension is authorised by this manifest.

## Access, provenance and identity checks

The [EUR-Lex legal notice](https://eur-lex.europa.eu/content/legal-notice/legal-notice.html) permits reuse of legal documents subject to specified exceptions and additional rights for third-party content. Keep document/annex-specific conditions and attribution; do not assign a blanket CC-BY licence to every downloaded Item. Project collection permission already stands. No new account, payment or authentication bypass is planned. The data-reuse help-page probe returned a robot/JavaScript challenge; it was recorded and not bypassed. Other official documentation was readable.

Expected directness is an official archival reproduction of the Commission's own publication. Identity/date/content mapping, body completeness, substantive claim truth and access conditions are separate dimensions. At planning time only the metadata/route mapping is established; body directness and any conflicting provenance require the original. Do not replace these dimensions with a trust score.

Dedup before every request: (1) join Work URI against the existing month frame; (2) check the selected Item URI's deterministic local/external storage path and checkpoint; (3) reuse verified existing bytes instead of redownloading; (4) flag any changed/shared Item-to-Work relationship. The current 979 targets have no selected local raw file/checkpoint; no full-corpus hash scan was run. After retrieval, Item URI plus SHA-256 identifies versions, and a changed-byte version never overwrites prior evidence. Preserve exact Work namespace and original parent IDs for integration. Check known cross-source work identifiers/title-date candidates against the coordinator's saved identity evidence and newly extracted headers; equal policy references or similar titles do not prove duplicate utterances. Corpus-wide semantic matching remains deferred. Cross-source independence is **expected, not verified**, until this accounting is complete.

## Execution and stopping instructions

1. Read Task 3's `control/REPAIR_READY.json`. Confirm every targeted issue is accounted for, supported repairs are actually committed and checked, unresolved cases annotated, and before/after checkpoint and **actual request paths** present. `staged_only` or storage-blocked repair is not a release. This task never creates or changes the marker.
2. Finalise A only from the released missing-original request manifest. Resolve/reuse locally available originals first, then attempt the exact remaining originals before the B queue; record an unavailable route without unbounded retries. Keep each A outcome and ingestion request local.
3. Re-measure free bytes on the actual project/staging volume. Require remaining space after the bounded download and transient/concurrent budget to be **strictly above 15 × 2^30 bytes**. The 21.13 GiB refresh supersedes the earlier ~14 GiB dispatch reading; it is not a budget to consume. The local `PREFLIGHT.json` records a fresh measurement and footprint calculation. Reserve figures are planning bounds, not a guarantee against concurrent disk changes; check again before each object.
4. Verify the frozen manifest SHA-256 against `ACQUISITION_CONTRACT.json`. Use `stage_frozen_items.py --repair-ready-sha256 <SHA256 of reviewed Task3 release> --execute` from this folder after A accounting. The hash binds the execution to the reviewed release; it does not replace the committed-checkpoint review. The runner fails closed if it cannot identify the marker's committed/checked evidence and actual request manifest. Its default invocation performs preflight only.
5. One request at a time, at least two seconds apart. Use public HTTPS Item URIs, source-size headers and streamed byte cap. Save per-object request/final URL, headers, retrieval time, bytes, SHA-256, attempts and structural signature. This tranche uses one attempt per object per invocation; transport/non-200/signature failure stops it. A 403, 429, challenge or source cooldown stops the run and is preserved. Honour Retry-After; existing bounded retry rules may be applied only to the same named object after the stated cooldown, without an automatic wrapper or alternate access route.
6. Acquire the shared `14_structural_validation_20261004/control/heavy_io.lock` for substantial raw reads/writes and a local downloader lock; fail promptly if busy. Do not hold it for documentation browsing or small plan writes, unlink it, or acquire a formal database writer lease. All outputs remain here. No invocation of old supervisors/stagers that would write elsewhere.
7. At the bounded stop, export `ingestion_manifest.csv` for the coordinator/single writer, with raw hashes, Work/Expression/Manifestation/Item IDs, source dates, retrieval/version evidence and verification-pending fields. Structural acceptance must check readable text and Work/header/attachment boundaries before describing an acquired candidate as a complete body. Keep bytes-without-readable-text, OCR/layout candidates, identity/date conflicts and missing-body outcomes separate. No formal database writes by Task 4.

Concrete invocation from the repository root, after reviewing the actual release and completing A accounting:

```sh
.venv/bin/python work_packages/M1_source_access/15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation/stage_frozen_items.py --repair-ready-sha256 REVIEWED_TASK3_RELEASE_SHA256 --execute
```

Replace the digest with the hash of the actual checked release, never a fabricated readiness file. Omit `--execute` for a no-download preflight. The release parser accepts explicit committed/checked assertions, before/after checkpoint fields and existing Task 3 request paths; an unrecognised schema stops for content review. Network-stream execution remains untested while this gate is closed. Text extraction and Work/date/annex acceptance are coordinator follow-through after byte staging, so the runner deliberately reports candidate originals rather than verified full bodies.

## Research boundary and exact next action

**Level 1:** saved dated Work metadata and candidate routes established; newly downloaded/readable originals **zero**. **Level 2:** climate/warming relevance and similarity unassessed. **Level 3:** affect/risk/future-harm/responsibility associations unassessed. **Level 4:** fear-specific interpretation unassessed. No fear or relevance measure gates inclusion, source success or progress.

At this delivery the repair marker and Task 3 request manifest are absent. Result: **`waiting_on_repair`**, with the storage gate passing at this plan snapshot. Exact next action: the coordinator retrieves this plan, accepts Task 3's committed checked checkpoint, reads its actual missing-original requests, finalises/executes A, then runs a fresh guarded B preflight against this same 979-row manifest. No polling loop or automatic collection restart is left running.
