# Coordinator acceptance and next-stage scope

4 October 2026. Subsequent tasks use **GPT-6.1 Sol / Extra High (gpt-6.1-sol / xhigh)**, superseding the earlier GPT-6 Sol preference.

## Acceptance of Tasks 1 and 2

Accepted as completed diagnostic deliverables, with unresolved evidence retained; no claim that all records are correct. Coordinator re-read methods, result manifests and exception ledgers and reran the 10 split-validator and 9 provenance-validator fixtures; all passed. No full scan was repeated.

Task 1: 246,980 parent links; 239,546 supported, 6,044 legitimate shared-answer parents, 1,381 conflicts and 9 insufficient cases. Another 202 original groups are candidate omissions, not approved inserts. Historic text-inferred matches and mirror-internal checks retain their stated limits. Task 2: 110 frame-rule coverage rows; 1,488 needs-review and 56,271 uncheckable emitted annotations. Its zero demonstrated metadata conflicts does not override Task 1's original-span conflicts. These are different checks, not inconsistent pass/fail decisions.

The coordinator triage has 3,080 issue rows (1,592 Task 1 rows plus 1,488 Task 2 review rows), NOT 3,080 unique bad documents. Multiple findings on a parent must be joined before repair. The 56,271 uncheckable annotations are NOT a bulk acquisition queue.

## Handling order

1. Verify and repair question/reply roles, continuation boundaries and missing blocks from already saved originals. The 1,113 Hansard and 135 Historic item conflict labels are not interchangeable with duplicate imports; confirm each actual defect before mutation.
2. Resolve the 124 range-heading date conflicts conservatively. A range alone supports an interval, not an invented exact day. Preserve 119 local/UTC differences as convention-sensitive; do not move monthly bins in this tranche. Record source calendar date and UTC timestamp separately for a later documented bin decision.
3. Reconcile the 1,054 GOV.UK body-status relationships without overwriting ethics status or historical attempts. Separate current technical content status from institutional approval and source licensing. Persist derived review evidence, not a new opaque trust score.
4. Review 202 saved original groups against eligibility and prior overlap/exclusion. Existing saved source text needs local derivation, not another download. Preserve legitimate joint answers and mirrored original identities.
5. Export specific missing-original requests and optional source-composition needs. Acquisition is driven by these needs, not by every uncheckable record or a desire for equal monthly counts.

## Task 3 — existing-data repair and evidence completion

Exclusive folder `03_existing_data_repair/`. Develop deterministic, idempotent bounded repairs with preconditions, before/after values, evidence locators, rule versions and inverse/rollback records. Preserve raw objects, stable document IDs and prior extraction runs; repairs to derived segments should be versioned. First inspect the actual schema and existing migration/ingestion entry points; do not assume a storage column exists or mutate historical raw data.

Use the issue ledger, not a full rebuild. Annotate unresolved cases and maintain a per-issue disposition. Shared parser fixes may be proposed as a patch in this folder; avoid editing shared collection modules while another task runs. Check only changed objects plus meaningful regression fixtures. Do not mark simulated/staged repairs as committed.

Given the current low disk space, prepare a compact patch/change set first. Formal database mutation requires an estimated bounded transaction/WAL footprint, sufficient free space for that footprint and rollback, and a single-writer lease. Avoid table-wide rewrites. If safe capacity cannot be established, deliver the staged patch and explicit blocked-commit state; do not loop or invent a successful repair.

## Task 4 — targeted originals and justified source additions

Exclusive folder `04_targeted_supplementation/`. Source research and a concrete acquisition manifest may proceed alongside Task 3. Actual download/ingestion waits for the anomaly-handling release described below and storage availability. Use already saved route metadata first. Small lawful web documentation/catalogue probes may establish routes; do not begin bulk enumeration or bulk raw storage.

Prioritise named originals Task 3 cannot reconstruct locally. In addition, use existing source×genre×month composition tables to identify a specific source dependence (e.g. parliamentary answer dominance) and consider at most two alternative frames; select at most one coherent first tranche. Existing EU/US sources with unacquired bodies may fill the need without a new provider. Do not quietly switch source filters to climate keywords, select individual dramatic documents, or equate more volume with less bias. Preserve role and genre labels and show how the added series would contribute independently.

Write a predeclared source/date/genre/unit rule, actual route/license evidence, dedup keys, expected bytes, bounded target count and stop conditions before requests. Retain published source dates within 1988-01-01–2026-09-21. The Paris 49-month window or a documented early-period gap is a candidate scope, not a mandate to complete every queue. Do not redownload originals already present. If new access/account/payment permissions are needed, identify the specific missing requirement rather than bypass it.

## Release and resource gates

- Tasks 1/2 evidence acceptance is complete. Both downstream windows may start their scoped preparation now; actual supplementary acquisition must wait for Task 3's anomaly disposition/checkpoint.
- Task 3 writes `control/REPAIR_READY.json` only after every targeted issue is accounted for and all supported committed changes are checked, with remaining uncertain records annotated and explicit before/after checkpoint. `staged_only` or storage-blocked results are not a collection release. No requirement that every issue pass.
- Task 4 must not create/override that marker or self-release. It may finish a useful source/manifest plan while the gate is closed. No spinning wait or automatic resumption is required; report the waiting state.
- At coordination time this volume has approximately **14 GiB free**, below the existing **15 GiB** collector floor. Preserve that existing floor for bulk acquisition. For the small local repair tranche, assess its actual transaction/WAL and rollback footprint before mutation; do not automatically treat a collector-only floor as a prohibition on every small metadata repair. Respect any existing repair-tool guard and retain safe rollback capacity. Do not delete user files, lower the guard, copy full databases or install large packages. Compact code/manifests/patch evidence may be produced while bulk acquisition is blocked.
- Reuse `14_structural_validation_20261004/control/heavy_io.lock` for substantial scans/raw reads and additionally `15_targeted_repairs_and_supplementation_20261004/control/formal_database_writer.lock` for formal writes; acquire heavy I/O before writer consistently. Never unlink lock files. One formal writer across all databases. Task 4 stages downloads separately and submits an ingestion manifest to the writer, not a competing importer.
- No proposal edits, semantic filtering, all-corpus hashes/reimports, commits or pushes. Workers write LOG_ENTRY.md locally; the coordinator appends the central log. Completion uses local RESULT.json and thread status, without cross-thread messaging.
