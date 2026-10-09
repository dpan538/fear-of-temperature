# Non-destructive media identity, coverage evaluation and lakehouse delivery

9 October 2026. Implemented algorithm version: `media-planning-3`. Final metadata run: [`results_v4`](results_v4/summary.json). Status: tested offline implementation and complete architecture plan; no collector dispatch, new acquisition, corpus-store mutation or server migration.

This delivery replaces count-floor completion with explicit source-aware coverage evidence, preserves existing identities and raw data, and adds auxiliary parent-source monitoring. Coverage-evaluation weights are separate from demand-driven acquisition scheduling. The next collection window has no fixed time shares. Earlier closed reports retain their original scopes.

## Findings from the accepted closed metadata

| Evidence | Reconciled result | Meaning |
|---|---:|---|
| Registry entries / canonical sources in current assertion view | 41 / 41 | Nine newspaper titles and 32 social opportunity entries; only 14 social sources have core bodies |
| Confirmed source aliases applied | 0 | No supplied evidence justifies collapsing current registry entries; shared platform is insufficient |
| Newspaper dated article identities | 9,538 | Same accepted non-campus count; no deletion or identity rewrite |
| Newspaper historical two-work months | 365 / 465 | Preserved diagnostic, not completion |
| Exactly-two-work months / unchanged since earlier snapshot | 157 / 154 | Persistent legacy-floor pattern warrants continued native inventory acquisition |
| One-source months among historical floor months | 298 / 365 | Pooled temporal presence does not establish broad media-source coverage |
| Opening newspaper gap | 37 months | January 1988 through January 1991 remains unobserved |
| Social usable dated independent bodies / observed months | 42,478 / 165 | Same accepted date/body view; other native entities remain retained |
| Known multi-member publication groups | 41 | Existing newspaper work memberships, preserving all 92 member article IDs |
| Exact-body overlap candidate groups | 539 | 41 newspaper and 498 social groups; hash equality is not proof of duplicate publication |
| Verified source-month inventory denominators in these inputs | 0 | Unknown coverage fractions remain unknown, even in high-volume cells |

The CLI reads metadata for 61,164 native entities: 9,538 newspaper articles plus 51,626 social typed entities. Campus's 9,249 article IDs remain separate and outside this calculation. Bodyless/context entities, versions, missing/contested dates and multiple-version hashes are not deleted to simplify a count. The source-month table contains 19,065 cells; the two pooled calendars contain 930 cells.

All acquired February–September 2026 newspaper bodies in this snapshot come from Devonport Flagstaff. The social August-to-September increase is exactly **7,488 = 921 within common sources + 6,567 from sources appearing in the collected month view − 0 from disappearing sources**. Four Mastodon instances contribute 6,565 of that appearing-source count, and OpenStreetMap Discourse contributes two. This establishes a collection-composition change, not a real-world event, founding date or population trend. Peaks remain retained and nonblocking.

## Coverage evaluation and scripts

[The algorithm specification](../../../docs/acquisition/MEDIA_IDENTITY_AND_COVERAGE.md) defines source/interface/parent/publication/version identities, conservative alias assertions, immutable source-month inventory denominators, evidence states, exact composition decomposition and the prospective selection contract.

The initial reporting profile in [`configs/media_planning.json`](../../../configs/media_planning.json) assigns **40% inventory recovery, 25% declared source-frame breadth, 20% native publication-period recovery and 15% identity/date resolution**. These are provisional design parameters, not estimated scientific weights or user-prescribed exact numbers. The old `>= 2` test has **zero evaluation weight** and never stops acquisition. Counts and individual dimensions remain primary; the weighted summary has no pass/fail or retention threshold.

Each component needs an evidenced declared target and covered-ID set. Unknown components keep their weight in a reported lower/upper range; they are not normalized away. For example, 100% identity/date resolution alone produces a 15–100 range, with only 15% of the weight resolved. These are missing-evidence bounds, not confidence intervals. Even 100 across a complete declared scope does not prove population coverage, a complete archive or later analytical readiness. Source-era inapplicability and genuine empty inventories require separate evidence.

The current 930 monthly assessment rows all lack the complete new denominator contract, so they retain unknown components. This is deliberate: accepted structural mapping checks do not supply a new monthly source-frame or inventory denominator. The implementation does not manufacture one from the observed sources, earliest record or current body count. New source adapters should record the needed lightweight manifests while collecting normally.

[The pure implementation](../../../src/fear_temperature/media_planning/core.py) separates this evaluation from demand-driven scheduling. The selector uses a named source/range need, readiness/block state, bounded-batch waiting age and stable tie-breaks. It does not receive the coverage score, acquired article count, peak flag, time-share target or semantic score. Necessary historical-route work may outrank routine expansion; equal-priority/equal-wait acquisition takes precedence over unrelated preparation. No fixed work-time allocation remains.

The standalone [CLI](../../../src/fear_temperature/media_planning/__main__.py) reads only named finalized metadata. It refuses an existing output directory and emits input, implementation and output digests. Confirmed aliases change only a derived counting view; hash matches remain candidates. Optional supplied coverage evidence is structurally validated and bound to the named closed snapshot; external source completeness is not automatically re-certified.

```sh
.venv/bin/python -m pytest tests/test_media_planning.py tests/test_parent_source_monitor.py -q
.venv/bin/python -m fear_temperature.media_planning \
  --snapshot work_packages/M1_source_access/27_newspaper_context_recovery_20261008 \
  --config configs/media_planning.json \
  --output /path/to/new/output-directory
```

Validation: **35 targeted tests passed**, Ruff formatting/lint passed, and all final run input/code/output hashes matched. Tests cover non-destructive identities, source alias conflicts, repeated observations, date correction across months, body/version boundaries, exact source-composition changes, unknown/empty/scoped inventory states, weight uncertainty, demand/age scheduling and resource/release guards. The closed newspaper/social counts reconcile unchanged. No old raw/body audit or sealed reviewer access was performed.

## Auxiliary parent-source monitor

The [parent-source module](../../../src/fear_temperature/media_planning/parent_monitor.py) and [full contract](../../../docs/acquisition/PARENT_SOURCE_MONITOR.md) add revision-aware statistics over committed metadata events. Six separate relations cover acquisition families, publishing organizations, platform networks, software families, instances and communities. Source registration, entity corrections and mapping replacements refresh the view; replay is idempotent and conflicting revisions remain explicit. Counts distinguish all native entities, readable bodies, usable dated bodies and known works. Unknown and multiple-parent memberships remain visible.

The finalized [parent-source statistics](results_v4/parent_source_statistics.json) support parent-child composition and publication-month visualization.

| Relation | Registered parents | Parents observed in retained entities |
|---|---:|---:|
| Newspaper acquisition family | 9 | 9 |
| Social platform network | 5 | 2 |
| Social software family | 3 | 3 |
| Social instance | 10 | 8 |
| Social community | 18 | 5 |

These rows are separate, non-additive relations. Publishing-organization mappings are unresolved in both streams, not evidence of zero real publishers. The 3,767 parent/period rows preserve native counts and mapping limitations.
 The live mode exposes an atomically refreshed view and compact append-only change history, with feed position and rejected-event counters. Storage is bounded; a diagnostic failure stops only the monitor, never acquisition. Parent metrics do not enter coverage weights, crawl sorting, quotas or stopping rules. No collector adapter has been connected. A temporary-fixture live test verified new appends, incomplete-line waiting and duplicate-event replay.

## Complete lakehouse design and next implementation boundary

[The full lakehouse plan](../../../docs/acquisition/MEDIA_LAKEHOUSE_DESIGN.md) covers:

- Immutable permitted source payloads and minimal evidence envelopes; separate typed catalog and versioned Parquet analytical views.
- Source/frame/native identity, publication memberships, versions, observations, relations, attachment metadata and unresolved/noisy entities.
- Operation charging, durable raw save, catalog/cursor commits, interrupted-request accounting, replay and snapshot publication.
- Current SQLite writers, targeted index repair, DuckDB/Parquet querying, conditional PostgreSQL catalog migration and later remote storage/compute.
- Schema evolution, partitioning, actual peak-footprint accounting, fixed cutoff, source permissions, backup/restore and reversible cutover.
- Demand-driven eight-hour acquisition, incremental checkpointing, evidence-linked forecasting and explicit implementation exit criteria.

Preparation should be completed offline where possible; the future collection window should be used mainly for real acquisition. Live checks and changed-chain verification are necessary, but repeated pilots, whole-store audits, full exports and speculative server migration should not consume fixed blocks of that window. Estimate the final closeout reserve from actual in-flight and export/reconciliation work. No new deadline or byte/request/source release is issued here.

The modules are **not yet connected to either closed collector**. Integrating the selector/inventory contract and validating the changed writer chain are the next concrete implementation steps before a future dispatch. Journal/Parquet/server migration phases remain explicitly unimplemented. User instructions still prohibit messaging the collector windows during this review; none were sent.

Raw bodies, SQLite stores, request queues, per-object receipts and controls remain local. Earlier intermediate algorithm runs are retained locally and ignored. This delivery publishes implementation/tests, schemas/design, final consolidated metadata, manifests and this report together.
