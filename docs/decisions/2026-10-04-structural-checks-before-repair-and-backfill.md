# Independent structural checks before repair and backfill

Date: 4 October 2026. Status: Execute Tasks 1–2 now. Dai confirmed the distinction between existing-data repair/evidence completion (Task 3) and supplementary acquisition (Task 4), then clarified that their exact scopes must be adjusted by the coordinator after Tasks 1–2 return. Do not dispatch Tasks 3–4 yet.

Dai requested two independent checks before further supplementation: (1) whether splitting a shared meeting/archive container into individual replies is justified and nonduplicative; (2) corpus-wide provenance/date logic and explicit annotations. These precede repair and supplementary collection to reduce conflicting I/O.

## Task 1 — archive reply-split validator

Produce an independently runnable, read-only script. Validate imported reply parents against saved source structure rather than merely reusing the importer's output. Use original question/answer IDs, source nodes, speakers, dates, boundaries and answer spans where available. Count containers, independent replies, joint-answer groups, questions, versions and segments separately.

Detect repeated source units, overlapping or duplicated substantive answer spans, header/footer leakage, truncated or missed replies and multiple imported copies. Repeated procedural wording, shared questions or one answer addressing several questions do not by themselves prove duplication. Different genuine replies may have identical wording. Distinguish proven duplicate imports, plausible legitimate sharing and unresolved identity. Cross-source mirror identity must remain separate from within-container split correctness.

Where original boundary evidence is absent, report the check as unresolved or unsupported. Passing means no violation detected under named checks, not mathematical proof of every historical boundary. Do not delete, merge, re-import or rechunk during validation.

## Task 2 — provenance and date logic annotations

Run applicable structural rules across all available registered source frames, with explicit denominators for checked, uncheckable, not applicable and unassessed records. Work from saved metadata and content evidence; no semantic truth or climate/emotion classification.

Check identity and original-host/archive relationships; publication, update, retrieval, answer and event date meanings; date precision and timezone; fixed cutoff; issuer versus host; content/version/status and parent/attachment consistency. Local and UTC date differences are not automatically errors. Recess calendars, future events and an event mentioned after publication are not universal rejection rules. Distinguish genuine contradictions from permitted chronology and uncertainty. Source authenticity does not establish the truth of every statement.

Write non-destructive companion annotations containing target ID/unit, rule ID/version, observed/expected values, outcome, severity, evidence path/locator, input checkpoint and check time. Allowed outcomes include supported, conflict, needs_review, uncheckable and not_applicable. Preserve original fields and separate provenance dimension results; do not produce an opaque aggregate credibility score or infer population reliability from a purposive sample.

## Execution sequence and I/O

Tasks 1 and 2 may develop and process small saved manifests concurrently in isolated directories. Large database scans and raw-container reads must share one advisory exclusive I/O lock; stream required columns once, reuse snapshots and do not duplicate full-corpus hashing or database copies. Formal data and shared collector code remain read-only during these tasks.

After both scripts, actual-run coverage, exceptions and limits are reviewed by the coordinator, release the next stage. Successful completion means an honest auditable result, not that every record passed. Unresolved records receive annotations and a bounded action; they do not demand another unlimited audit.

Confirmed Task 3: repair/complete existing mappings, dates, status and evidence annotations. Task 4 planning scope: acquire identified missing originals/attachments or add a justified source frame into a separate staging directory. Dai explicitly permits considering additional sources to address evidenced source/genre/period concentration. Do not reduce supplementation to failed-download retries, and do not equalise monthly counts by collecting or deleting records just to flatten the distribution. Define an independent source frame, date interval, counting unit and stopping rule for any proposed addition. Start neither downstream task now. The coordinator first reviews Tasks 1–2 and revises the concrete scopes. Their eventual repair preparation and acquisition staging may run concurrently; commit to each formal database through a single writer. No overlapping parent/version may be patched and imported concurrently. Preserve historical raw data and record changes. Existing resource/rate limits remain in force.

The study publication interval remains 1988-01-01–2026-09-21. Current work does not gate inclusion on climate, affect or fear, modify the proposal or reopen exhaustive national coverage.

## Later 4 October — coordinator acceptance and downstream release scope

Tasks 1 and 2 completed and were accepted with named exceptions. Their earlier no-dispatch gate is superseded by [the accepted downstream scope](../../work_packages/M1_source_access/15_targeted_repairs_and_supplementation_20261004/ACCEPTANCE_AND_SCOPE.md): Task 3 prepares/executes evidence-supported repair; Task 4 may plan source supplementation but downloads wait for the checked repair release and disk guard. Dai specifies GPT-6.1 Sol / Extra High for subsequent tasks. Existing source composition may justify an additional source, not only retries of missing originals.
