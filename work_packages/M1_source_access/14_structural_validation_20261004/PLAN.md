# Structural validation and staged follow-through

Fixed publication scope: 1988-01-01–2026-09-21. Model preference: GPT-6 Sol, Extra High.

| Task | Output directory | Execution boundary |
|---|---|---|
| 1. Independent archive reply-split validator | `01_archive_split/` | Read-only source-boundary and duplicate diagnostics |
| 2. Provenance/date logic validator and annotations | `02_provenance_logic/` | All registered frames inventoried; per-rule applicability and actual coverage recorded |
| 3. Existing-data repair and evidence completion | Not started | Wait for 1+2 results and coordinator scope revision |
| 4. Targeted originals and justified additional-source acquisition | Not started | Wait for 1+2 results and coordinator scope revision |

## Shared rules

Read root AGENTS.md, PROJECT_DIRECTION and latest PROJECT_LOG. Also read the new structural-check decision and the integrated audit under `13_parallel_data_audit_20261004`, including COORDINATOR_CORRECTIONS.md. Frozen reports are historical evidence, not current instructions.

Tasks 1/2 use separate output folders and do not edit shared code, project log, formal databases, raw data, proposal or each other's outputs. The coordinator integrates their LOG_ENTRY.md files. No network acquisition. Scripts must have a reproducible CLI, rule dictionary, input checkpoint, actual-run results and targeted meaningful fixtures. Tests must cover both real defects and legitimate shared/repeated structures; passing the importer twice is not independent validation.

Each task writes REPORT.md, SUMMARY_zh.md, RESULT.json, INPUT_MANIFEST.json, RULES.md and LOG_ENTRY.md, plus executable script, annotations/exceptions and execution coverage. Reports distinguish inventory counts from actual original-level verification. Do not promise universal correctness or truth. Finish once the specified run and bounded checks are accounted for; report unsupported cases rather than looping indefinitely.

## Heavy I/O mutex

Both workers must use the same advisory `fcntl.flock(..., LOCK_EX)` file at `control/heavy_io.lock` before a substantial database scan or batch of raw-container reads. Retain the handle through the heavy phase, release in `finally`, and never unlink/recreate the lock file. Wait with nonblocking attempts and progress updates; there is no shared database writer. Do not hold the lock during coding, small-manifest reads, report writing or waiting for user input. Record acquisition/release times in each worker's own run log. Reuse previous evidence where sufficient, stream records, and do not hash all saved bytes or copy databases.

Downstream work has not been dispatched. Completion of 1+2 is an evidence gate, not an all-records-must-pass gate. Dai confirmed the repair-versus-acquisition distinction, then instructed the coordinator to revise Tasks 3/4 after Tasks 1/2 return. Additional source frames may be justified by actual source/genre/period concentration; no automatic launch or numerical equalisation. Formal database integration remains serial even if repair preparation and network staging run concurrently.

## Active workers

- Task 1: existing thread `01a1054d-a23c-7c90-adc9-03b3988c15db`, GPT-6 Sol / xhigh.
- Task 2: existing thread `01a1054d-bde4-7f72-a9c5-c882b926edaa`, GPT-6 Sol / xhigh.
- Both follow-up tasks were dispatched successfully. The coordinator retrieves local result files and thread completion; workers need not send cross-thread messages.
- Tasks 3 and 4 have not been dispatched.
