# Parent-source statistics and auxiliary live view

Version: `parent-source-monitor-1`, 9 October 2026. Implemented and tested against metadata fixtures and the closed collection manifests. The existing collectors have not been connected or started.

The parent-source view supports source-quality investigation and future visualization. **It never changes acquisition priority, source inclusion, article quotas, requests, budget decisions or stopping rules.** It is separate from the weighted coverage calculation. A large or small parent count is not automatically good or bad; different source frames legitimately have different structures. Government's institutional hierarchy is not a diversity target for newspapers or social media.

## Relation model

| Relation dimension | Example | Interpretation limit |
|---|---|---|
| `acquisition_family` | A recorded newspaper publisher/source/interface family | Existing mixed family evidence is not automatically verified publisher independence |
| `publisher_organization` | An evidenced title's publishing organization, with validity dates where known | Separate ownership changes, editions and independent editorial units; unknown remains unknown |
| `platform_network` | Stack Exchange or Bluesky | A platform network is neither a single speaker nor proof of independent publishers |
| `software_family` | Discourse, Mastodon or Lemmy | Shared software is a technical relation, not shared ownership |
| `instance` | A named Mastodon/Lemmy server | Hosting location does not establish author country or role |
| `community` | A Stack Exchange community or forum | Community identity does not make every member's voice interchangeable |

Keep these dimensions separate; there is no universal cross-stream parent total. Source-native entities, original-publication/work memberships and versions remain separate levels below the source registry. Future account or speaker relations need their own documented typed dimension; this module does not infer them across platforms.

A source can have several parent assertions in one dimension. Each assertion has a stable parent ID, status (`confirmed`, `recorded`, `candidate`, `unresolved`), evidence reference and optional inclusive publication-date validity interval. Only confirmed/recorded mappings enter the corresponding observed counting view. Candidate relationships remain unresolved. A recorded registry classification is not upgraded to independently verified ownership.

Mappings without validity dates are labelled **snapshot classifications**. Their historical body counts show grouping under that registry snapshot, not proof that the same owner existed throughout 1988–2026. A bounded historical assertion applies only when the entity's usable publication date falls within its interval. Unknown dates cannot be allocated through a historical ownership interval.

The current bootstrap carries nine recorded newspaper acquisition families, while leaving verified publishing-organization mappings unresolved. Social bootstrap separates documented network families from shared software, server instances and communities. Unmapped relations may be unknown or genuinely inapplicable; missing applicability evidence cannot distinguish those cases. Do not interpret every unmapped software/instance field on a newspaper as a quality failure.

## Counts and denominators

For each stream × relation dimension × parent, and each publication month plus the full snapshot, publish:

- Distinct retained native entity IDs.
- Readable body entity IDs and, separately, readable bodies with usable in-interval dates.
- Distinct accepted publication/work keys among the usable dated bodies.
- Contributing canonical/source registry IDs, retaining the assertion-view scope.

Publication-date corrections move the current derived count between months; the event history and original corpus are preserved. Unknown or outside-interval dates have an explicit separate bin and cannot inflate the fixed study calendar. Versions/replays of one entity do not add another entity. A known work shared by two entities counts once in that parent's work view, while both native entities remain counted as entities.

For each stream × dimension, publish registered versus observed parent count, parents with bodies, unmapped entity/body count and body share, multi-parent entity count and the largest mapped parent's share of **all usable dated bodies in that stream**. The denominator is visible; no adjustment hides unmapped bodies. Known parent counts of zero mean no supported mapping in the current view, not zero real-world parents.

Membership counts are distinct **within each parent** and can overlap across parents. Consequently, parent shares may sum above 100% under multiple mappings, and different dimensions must never be added. Show the multi-parent count and unknown proportion beside any composition chart. No entropy/HHI target, uniform distribution, publishing-independence proxy or source-quality threshold is computed.

## Incremental metadata event contract

Input is an append-only UTF-8 JSONL metadata feed. Each complete newline-terminated event is one of:

1. `source`: `{kind, revision, source: {source_id, stream, ...}}`.
2. `entity`: `{kind, revision, unit: {stream, source, entity_id, publication_key, publication_day, countable_body, date_usable, body_hash?, acquisition_parent?}}`.
3. `parent_assertions`: `{kind, revision, source_id, dimension, assertions: [...]}` replacing that source/dimension's current assertion set.

`revision` is a positive monotonically increasing integer **per object**: source ID, stream/entity ID, or source/dimension. It is not inferred from publication/retrieval timestamps. Source registration precedes dependent events. The entity body is never sent in this diagnostic feed; only identity, mapping, date and hash metadata are needed. A source event must not change an established source's stream silently.

Identical same-revision replay is idempotent; lower revisions are stale and ignored. Different payloads at the same revision are rejected as conflicts. Higher revisions update the materialized view without altering the input journal or original entities. Malformed/conflicting events remain in the unchanged input, increase a visible rejection counter and do not mutate the accepted view. Incomplete trailing lines wait for the next append. File replacement/truncation stops this monitor and requires an explicit new feed/replay rather than silently resetting identities.

A collector adapter should expose **already committed** metadata through its existing durable outbox/checkpoint mechanism. The diagnostic reader neither opens corpus databases nor holds their writer/resource locks. Failure or absence of the monitor must not fail a body transaction, pause a source or change a scheduler result. Integrate this feed only as part of an authorized changed-chain update; no collector message or integration occurred here.

## Run and refresh behavior

One-shot replay:

```sh
.venv/bin/python -m fear_temperature.media_planning.parent_monitor \
  --events /path/to/committed_metadata_events.jsonl \
  --output /path/to/local_parent_monitor
```

Optional live mode adds `--follow --poll-seconds 5`; `--duration-seconds` bounds its lifetime. This delivery ran only a short temporary-fixture follow test, not a production daemon. A separate output-directory lock prevents two monitors from writing the same diagnostic view. It is not a collector lock.

The view updates only after changed input. Events update in-memory accepted metadata incrementally; snapshot refresh groups that metadata without scanning the source body/raw stores. Replaying a feed reconstructs the view after restart. Current memory/snapshot work scales with retained entity metadata; substantially larger corpora may later need persisted per-source aggregates, without changing this auxiliary boundary.

Outputs are:

- `latest.json`: atomically refreshed disposable parent/month snapshot, with report time, publication interval, feed byte position, mapping assertions and diagnostic counters.
- `history.jsonl`: compact append-only changes to parent totals and diagnostics, with report IDs and timestamps. Removed keys describe a changed **view**, not deletion of source data.

The input feed retains the evidence needed to reproduce earlier views; closed research snapshots are saved separately and remain immutable. The monitor does not save another complete snapshot every five seconds. Its default 64 MiB output guard includes the additional temporary snapshot and history write. Reaching it stops **only this diagnostic writer**, without deleting its history or stopping collection. The output capacity is a local guard, not a new shared-budget allocation: future production integration must reserve its measured metadata/event/output footprint within the existing resource envelope before enabling it. A crash can leave history ahead of the latest disposable snapshot; matching report IDs expose that mismatch and replay regenerates the view. This is not a cross-file atomicity claim.

## Visualization contract

The finalized [`parent_source_statistics.json`](../../work_packages/M1_source_access/28_media_identity_coverage_and_lakehouse_20261009/results_v4/parent_source_statistics.json) provides a baseline for:

- Parent → child source composition, with separate relation-dimension and stream selectors.
- Publication-month contributions by parent, retaining irregular peaks and partial September.
- Acquisition-time changes in observed parents, resolved/unknown mappings and membership corrections from the compact history.
- Coverage/source-quality inspection cards that distinguish registered opportunities from parents actually contributing bodies.

Show the metric unit, denominator, mapping status/version, latest feed position and unresolved share. Avoid a single green/red quality score or an automatic crawl-control callback. The baseline alone is one observation-time snapshot, not a historical time series of how parent mappings were learned.
