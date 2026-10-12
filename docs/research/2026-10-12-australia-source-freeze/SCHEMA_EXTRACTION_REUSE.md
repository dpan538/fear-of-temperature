# Schema and extraction preservation map

12 October 2026. Reviewed published repository code, schema documents and frozen implementation files only. No old SQLite/DuckDB store, raw body, evaluator, credential or collector control was opened; no module was imported/executed. No file was moved/deleted and no database or corpus was changed. This maps preservation and prospective reuse; it does not perform the archive/cutover.

All paths below are exact repository-relative paths under `/Users/jarlgiovanni/Desktop/fear_of_temperature`.

## Schema contracts to preserve

| Exact path | Role and reuse caveat |
|---|---|
| `src/fear_temperature/database_pilot.py` | `SCHEMA_SQL` supplies supporting sources, batches, documents, metadata versions and extraction-run structures. Preserve the historical pilot; its original document-linked segment interface is superseded by the version-linked core below. |
| `src/fear_temperature/government_collection.py` | `CORE_STORAGE_SQL` and `CORE_TEXT_STORAGE_SQL` define immutable successful-byte versions and version/extraction-run-linked segments. Logical core: documents → content objects via many-to-many links → content versions → text segments. GOV.UK enumeration and legacy migration commands are source-specific and must not be launched for the new Australian view. |
| `work_packages/M1_source_access/05_core_content_storage/schema_mapping.md` | Explains the approved five-table logical core and supporting tables. Keep metadata/document versions distinct from fetched body versions. |
| `work_packages/M1_source_access/09_us_au_government_acquisition/au_browser_stage.py` | `setup()` defines `au_browser_works`, `au_browser_versions`, `au_browser_pages`; keeps original-date precision/evidence, attachment role and page lineage. A page is not an independent policy work or analytical paragraph. Its stage/main routines point to historical inputs/stores. |
| `work_packages/M1_source_access/25_newspaper_calendar_acquisition_20261006/worker/elt.py` | `init()` contains newspaper DDL: `articles`, `article_versions`, `evidence`, `transport`, `baseline`; `ensure_dispositions()` adds `article_dispositions`. Stable complete article and immutable body-version concepts are reusable; historical schedules/baselines/limits are not the new scope. |
| `work_packages/M1_source_access/27_newspaper_context_recovery_20261008/social_public_api/code/schema.sql` | Complete social core: `posts`, typed `native_identities`, URL aliases, parent context, body versions, raw-response mappings and observations. Preserve original/native HTML separately from structurally derived text. |
| `work_packages/M1_source_access/27_newspaper_context_recovery_20261008/social_public_api/continuations/20261009_public_native_expansion/worker/schema_v2.sql` | Adds acquisition sources/interfaces/frames, typed entities, immutable entity versions/observations, native edges/attachments and structural corrections. Context containers, reposts, previews and bodyless evidence must not inflate authored-body counts. Preserve alongside `NATIVE_SCHEMA_V2.md` in the same directory. |
| `work_packages/M1_source_access/34_media_four_hour_review_20261011/closed/social/B/implementation/schema_v2.sql` | Later frozen SQL adds the `entity_version_lookup` index to the earlier v2 schema. Preserve this version and sibling `schema_legacy.sql`; the latter matches the first-wave core hash. |
| `work_packages/M1_source_access/36_media_current_routes_closeout_20261011/SOURCE_AND_SCHEMA.md` | Finalized native-unit, date/version, source/geography, rights and changed-tranche contract. Preserve as the interpretation of the closed snapshot. |

The early media SQL at `work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/02_media_precollection/schema.sql` and `work_packages/M1_source_access/20_media_original150_validation_20261005/candidate/schema.sql` also stays preserved as historical pilot design; it is not silently promoted to the current production schema.

## Extractors worth retaining, with boundaries

`src/fear_temperature/government_collection.py` contains `_extract_html`, `_extract_pdf`, `_extract_office_zip`, `_extract_csv`, `_extract_source_text` and format validation. Reuse format/locator ideas through a new declared adapter; do not inherit old database paths, source identity assumptions or acquisition commands. `work_packages/M1_source_access/09_us_au_government_acquisition/au_generic.py` additionally handles AU landing, PDF, DOCX and RTF extraction. Its historical 15/25-character cleaned-text thresholds need explicit reconsideration; preserve source extraction and do not use those thresholds as new native-unit inclusion rules.

Preserve `work_packages/M1_source_access/25_newspaper_calendar_acquisition_20261006/worker/extract_load.py` for original article-boundary parsers. The finalized overlay is `work_packages/M1_source_access/36_media_current_routes_closeout_20261011/code/newspaper/extract_load.py`; retain its full sibling code tree and `IMPLEMENTATION_MANIFEST.json`. Its `elt.py` dynamically executes the donor `work_packages/M1_source_access/27_newspaper_context_recovery_20261008/worker/elt.py`, which executes the package25 ELT. The parser overlay uses the package25 parser prefix through `elt.PREVIOUS`. The published manifest explicitly says this is not a standalone runnable snapshot. Reuse tested parser logic after separating runtime controls and binding new Australian sources; do not run the old wrapper against the archive.

Preserve the finalized social tree `work_packages/M1_source_access/36_media_current_routes_closeout_20261011/code/social/` and its `IMPLEMENTATION_MANIFEST.json`. `transport.py` contains native Mastodon/Discourse/Q&A/Bluesky parsing and structural text handling; `entities.py` retains typed identity, version and relation handling. They still contain old absolute store paths and import-time owner/scope reads. `entities.py` expects `schema_v2.sql`, and `transport.py` expects `schema_legacy.sql`; those SQL files are not supplied alongside the package36 Python snapshot. Preserve the donor SQL/layout, but build a clean explicit import boundary before any future reuse.

`scripts/fear-temperature/extract_report_text.py` is a supplied-PDF inspection helper, not a corpus collector. `src/fear_temperature/corpus.py` is demo/derived storage infrastructure with create-or-replace tables; it is not an archive/cutover tool. Keep both without executing them against protected holdings.

Preserve retired `coverage >= 2`, source-count and old acquisition scheduler code as historical evidence. Do not reactivate its completion flags, quotas, dispatch, queues or expired releases. Schema/parser reuse adds no model, prediction, topic, emotion or fear execution. Ready Australian databases and small named gap fills should use the common identity/version/lineage contracts while keeping parliamentary utterances/paragraphs, newspaper works and public native bodies separate.

## Code integrity receipt

Read-only SHA-256 checks on **45 newspaper and 17 social Python files** matched every recorded byte count/hash in their package36 public implementation manifests. This validates published code bytes, not runtime dependency closure or corpus correctness. Selected additional fingerprints:

| File | SHA-256 |
|---|---|
| `src/fear_temperature/database_pilot.py` | `21b69aa79ed6f19fe12f3955ee04805d2893e9051d3a351fa34ed4bd56699ece` |
| `src/fear_temperature/government_collection.py` | `974a6ef6d169597539867785c070674032de85f980c78c83a6e784059d1d4072` |
| `work_packages/M1_source_access/09_us_au_government_acquisition/au_browser_stage.py` | `aec7461ed030db8fb5fe393b84fcd2339df70b0105c11b2116d0e217b0e73203` |
| `work_packages/M1_source_access/09_us_au_government_acquisition/au_generic.py` | `c7cb57e755efa3ba5daf40ef4af68e618d7d6ef5a1c3f5ed70ba41b4731439ca` |
| `work_packages/M1_source_access/25_newspaper_calendar_acquisition_20261006/worker/elt.py` | `a9dd8e707fe6593f9996028526de68943ebc003268345f3dbb1510cdef1d9e06` |
| `work_packages/M1_source_access/25_newspaper_calendar_acquisition_20261006/worker/extract_load.py` | `3aec113ac9313d72d38d2983fcd0e6cc9f150e975eb70092e73524aaa894b3ce` |
| `work_packages/M1_source_access/27_newspaper_context_recovery_20261008/social_public_api/code/schema.sql` | `daea9eafb3caee782b840c8a1694fd163d58c7230f83d96fd64e6b99cb04fd48` |
| `work_packages/M1_source_access/27_newspaper_context_recovery_20261008/social_public_api/continuations/20261009_public_native_expansion/worker/schema_v2.sql` | `34b75e12d1afb570cceda6303bf2599523c5ab0f9b86c27c08aa0fccd9c28d57` |
| `work_packages/M1_source_access/34_media_four_hour_review_20261011/closed/social/B/implementation/schema_v2.sql` | `513b36b771756ebc3cb8a0fc63375d6430cdb6dd57dace3983b60f319c9864c9` |
| `scripts/fear-temperature/extract_report_text.py` | `7e3441a773ade5b3e4af1c9a0bf59a9eeff414bf7553fcaac7406fcaf547c742` |

## Quarantine and selective carry-forward

Use a separate append-only quarantine/disposition ledger keyed by archive version, stream/source, original native/work ID and content version/hash. Record the specific structural anomaly, original date/precision and evidence locator, validation state, disposition, reviewer/time and any replacement/derived-view link. Existing hashes can be referenced; this review did not rehash old bodies. A candidate body-hash match alone is not authority to merge independent works.

Suspect rows remain archived and traceable while the **new active view** excludes their unresolved structural state. Selectively carried Australian records require explicit source/date/unit/rights and original-content evidence; copy or reference them with an archive-to-new-ID mapping, preserving original version lineage. Corrections create new derived versions or mappings rather than overwriting originals. An anomaly peak is a reason to inspect named records, not automatically to quarantine every record in that month. Neither neutral tone, absent fear words nor unvalidated climate relevance is a quarantine reason.

This lets the new active dataset start from verified inputs without destroying evidence, reviving legacy selection logic or misrepresenting optional carry-forward as a completed corpus transfer.
