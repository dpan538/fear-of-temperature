# Parallel corpus preparation audit — 4 October 2026

Dai authorised three separate tasks running concurrently, all on **gpt-6-sol / xhigh**, with results returned to the coordinating task for review. The publication interval remains **1988-01-01–2026-09-21**, regardless of retrieval or report date. Climate relevance and emotion attribution are deferred to analysis.

| Task | Thread ID | Exclusive output directory |
|---|---|---|
| Fixed corpus cutoff and date integrity | `01a1054d-7fba-7110-9e31-de2d73bf1189` | `01_fixed_cutoff/` |
| Corpus distribution and collection anomaly audit | `01a1054d-a23c-7c90-adc9-03b3988c15db` | `02_distribution/` |
| Source provenance quality and verification audit | `01a1054d-bde4-7f72-a9c5-c882b926edaa` | `03_source_quality/` |

Coordinator: `01a0a369-5516-7492-a412-adbbabfb032f`, host `local`.

## Shared execution contract

- Read root AGENTS.md and the 4 October decision first. Work in the saved project with independent output directories.
- Formal databases, raw files and shared code/configuration remain read-only during parallel work. No duplicate collectors, large database copies, whole-corpus rehash or shared log edits.
- Record source-specific checkpoints, input paths, count units and query/filter rules in each task's INPUT_MANIFEST.json. Historical atlas figures are baselines, not synchronized current counts.
- Produce REPORT.md, SUMMARY_zh.md, LOG_ENTRY.md, RESULT.json and task-specific evidence/scripts. Propose any shared-code changes for coordinator integration. Preserve raw records and unresolved states.
- On completion, each task sends an evidence-linked summary to the coordinator under Dai's explicit return-reporting authorisation. An incomplete task must report its actual blocker and completed evidence, not claim completion.

## Coordinator review after returns

1. Reconcile snapshot times, date rules and independent-record units before comparing totals across tasks.
2. Review cutoff integration proposals, numerical anomaly explanations and provenance classifications against their evidence. Check that uncertainty and sample findings have not become full-corpus assertions.
3. Combine overlapping exceptions once, with parent/source IDs and a concrete next action. Preserve legitimate high-volume periods and indirect/disputed discourse.
4. Publish a consolidated assessment and prioritised bounded repair/supplementation plan. Append accepted log entries centrally; do not automatically apply proposed deletions, live database changes or global acquisition restarts.

All three audits completed. The coordinator retrieved and reconciled their local outputs on 4 October. See [integrated report](INTEGRATED_REPORT.md), [prioritised actions](INTEGRATED_ACTIONS.csv) and [corrections/checkpoints](COORDINATOR_CORRECTIONS.md). Source-quality acceptance includes the Guardian body-check correction; original worker outputs remain preserved. No shared code or formal database repair has been applied. Some cross-task messages were rejected by automatic approval; local evidence retrieval completed the handoff without another messaging route.
