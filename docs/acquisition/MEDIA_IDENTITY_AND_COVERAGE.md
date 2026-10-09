# Media identity, coverage evaluation and acquisition specification

Version: `media-planning-3`, 9 October 2026. This specification replaces count-floor completion as the prospective planning method. Frozen reports and the historical two-work field remain unchanged. No data deletion, topic/fear filter, population-representativeness claim or extraction release follows from this document.

## 1. Identity hierarchy and non-destructive deduplication

Keep the following identities separate:

1. **Acquisition interface:** a URL/API/archive route and its access evidence. Multiple interfaces may expose one source.
2. **Source:** a newspaper title/edition, forum community or platform instance under its documented frame. A website hostname is not a universal source identifier.
3. **Source parent/platform:** publisher or acquisition family, platform software and host operator are different relations. Shared software does not imply a shared publisher; shared ownership does not collapse distinct titles.
4. **Native publication entity:** a complete article or typed native post/reply/comment, keyed by source + namespace + native ID. Bodyless/context/repost entities remain their actual units.
5. **Known publication/work membership:** existing evidenced work-family or native original-publication URI links, distinct from transport identity.
6. **Version and observation:** immutable content/state versions and observations of those versions in individual responses. Repeated observations never become additional publications.

Stable source, article/entity and version IDs survive every derived deduplication view. The current implementation creates memberships and candidate groups; it never updates an original ID or deletes a row/file. A previously accepted work-family relationship is carried as *known*, not re-certified as universal work independence.

### Source resolution

An explicit `same_source` assertion requires a registered canonical target, `confirmed` status and an evidence reference. The assertion set belongs to a dated registry version. Candidate relationships, common publisher/platform/hostname and similar names cannot change source counts. Cross-stream aliases, cycles, missing endpoints and conflicting canonical assignments fail validation. Revocation produces a new assertion-set version; it does not rewrite old snapshots.

The conservative URL comparison key lowercases scheme/host, removes default HTTP(S) ports and fragments, and preserves scheme, path case, query parameters/order and trailing slash. It is only a candidate generator. HTTP/HTTPS equivalence, feed/API/page aliases, changed domains and tracking-parameter removal require source-specific evidence before confirmation. No regex strips identity-bearing parameters globally. No fuzzy-name or embedding merge is executed.

### Publication and content relationships

Group matching accepted publication keys into a counting view while preserving every original entity and observation. A native original URI can identify a federated copy's publication; missing URI mapping remains unresolved. Distinct source-native publications can have identical text. Body SHA-256 equality therefore generates an `exact_body_overlap_candidate`, not an automatic work merge, deletion or retention decision. Short conventional expressions are especially unsuitable for hash-based work identity. A source edition, attributed wire reproduction and independently published article can require separate publication and work views.

The current run found 41 multi-member known publication groups, all newspaper, containing 92 article IDs (51 additional memberships beyond one per group). Those relationships were inherited from accepted metadata. It also found 539 exact-body candidate groups: 41 newspaper and 498 social. The latter are **not 539 proven duplicate works**. Multiple body hashes across versions are listed separately; the script does not select an arbitrary last version. Ambiguous publication membership remains explicit.

## 2. Coverage is a set of evidence dimensions

The calendar remains 465 months, ending 21 September 2026. Partial September is not extrapolated to a full month. Source-era inapplicability, unknown era, access restriction and applicable-but-unobserved are separate states. The earliest acquired record never establishes a founding date or the start of a complete archive.

For source `s`, publication month `m`, and declared snapshot/frame `f`, retain:

| Symbol/field | Definition |
|---|---|
| `R(s,m)` | Distinct retained dated native entities in the supplied accepted entity snapshot |
| `B(s,m)` | Entities with readable independently authored bodies and usable publication-date mapping |
| `W(s,m)` | Distinct nonempty accepted publication/work keys among those bodies |
| `D(s,m)` | Distinct observed publication days; evidence of temporal spread, not a daily-production target |
| `E(s,m,f)` | Unique native candidate IDs from a declared inventory snapshot, when evidenced |
| `Q(s,m,f)` | Candidates resolved as eligible complete-body acquisition units |
| `X(s,m,f)` | Candidates with explicit structural/date/access disposition under the declared frame |
| `L(s,m,f)` | Eligible inventory IDs actually loaded, intersected with `Q`; bodies outside this inventory cannot inflate it |

Report `L/Q` only when the inventory scope, immutable manifest, snapshot time and native namespace exist, and `Q` is nonempty. Also report unresolved eligibility `|E − (Q ∪ X)|`. `Q` and `X` must be disjoint subsets of `E`; duplicated inventory IDs are an error. A zero or unknown denominator returns **null**, not zero completion or 100%. `X` is a disposition, not an instruction to delete retained evidence or semantically exclude material.

`declared_frontier_complete` requires: evidenced native index exhaustion, all candidate eligibility resolved, all eligible IDs loaded, and no access block preventing the claimed completion. An empty inventory can be complete only with the same explicit scoped terminal evidence; its recovery fraction remains null. HTTP timeout, page cap, date boundary, robots denial, exhausted metadata pagination and exhausted article-body queue are different states. None alone proves historical population completeness.

The current finalized inputs do **not** supply verified source-month ID inventory denominators. The script consequently emits null completion fractions for every such cell, even when hundreds of bodies are present. Source-wide API totals cannot substitute for month-specific eligible-article counts. This is a missing measurement contract, not an accusation that the collected text is invalid.

### Pooled and regional reporting

Keep readable-body IDs, known publication keys, distinct canonical sources, recorded acquisition-parent families, unresolved parent mappings and largest-source share side by side. Acquisition-parent count is not verified independent publisher count. A later evidence-based publishing-parent table may support that additional statistic; do not invent it from domains or platform software.

The exactly-two-work field is an explicitly labelled **legacy diagnostic**, never a completion condition or article eligibility rule. Compare it with the prior snapshot to identify persistent floor-shaped input. Current evidence is 157 exactly-two months, 154 already at two before the latest tranche. The 365 historical floor months include 298 single-source months. These quantities do not become a new scalar quality score.

Maintain regional views without requiring every country to be exhaustive before useful descriptive analysis. A pooled presence month cannot be presented as all-stratum coverage. Unknown source/author location remains unknown. Campus publications retain their separate frame and cannot fill newspaper gaps.

## 3. Explain month-to-month source composition

Let `S0` and `S1` be sources with acquired bodies in adjacent publication months. Decompose exactly:

`total_change = sum_common_sources(B1 − B0) + sum_appearing_sources(B1) − sum_disappearing_sources(B0)`.

This is an accounting identity, not causal attribution. Appearing/disappearing means presence in the acquired view, not platform founding, source closure or real population entry. Report observed-source Jaccard overlap `|S0 ∩ S1| / |S0 ∪ S1|` as a diagnostic; return null for an empty union. It is not a score to optimize and never controls inclusion or retention. Common-source change can still contain cursor, frame, historical-version and date artefacts.

For August→September 2026 social input, the exact decomposition is **+7,488 = +921 common-source change +6,567 appearing-source bodies −0**. The four Mastodon instances contribute 6,565 of the appearing-source bodies; OSM contributes two. This explains why the pooled jump cannot directly measure public attention. January–August 2026 is 99.1% Bluesky in the current dated view.

For later longitudinal work, define a source/cohort panel in advance with evidenced applicable eras, frame versions and complete or explicitly censored inventories. Do not construct a supposedly balanced panel merely by retaining high-count sources or treating absent cells as zero. Publish both the broad pool and declared panel view. No inverse-probability weights can be estimated from these opportunity samples without identified inclusion probabilities.

## 4. Replace the count-floor weight with explicit coverage dimensions

**Weights concern the coverage evaluation previously dominated by `count >= 2`, not allocation of working hours**. No fixed work-time allocation applies. The historical two-work test has **zero weight in the new evaluation**, and remains visible only to diagnose legacy acquisition truncation. One, two or three hundred articles alone cannot certify completion.

The initial configurable reporting profile is a **design proposal**, not a fitted model or validated research measure:

| Dimension | Proposed weight | Numerator / evidenced denominator |
|---|---:|---|
| Native inventory recovery | 40% | Loaded eligible native publication IDs / all enumerated eligible IDs in the declared source-range inventory |
| Declared source-frame breadth | 25% | Canonical source cells with usable evidence / applicable source cells in a versioned source/edition/stratum frame |
| Publication-period recovery | 20% | Native issue/day/period cells represented by usable bodies / evidenced expected publication cells within the declared source range |
| Identity/date resolution | 15% | Retained target publication entities with resolved identity, readable-body mapping and usable publication date / all retained target publication entities in that declared snapshot |
| Historical `articles >= 2` flag | **0%** | Diagnostic only; no pass/fail, stop, retention or reward effect |

These dimensions answer different questions and are not statistically independent. Source breadth is not equal-volume balancing and does not prove publisher independence or public representativeness. Never define its target frame retrospectively as only the sources already collected. Archive mirrors/interfaces of one source count once after confirmed resolution; separate newspaper editions and social communities retain their documented identities. Report evidenced publishing-parent breadth and unresolved parent mapping separately. Do not invent author-country or independence labels.

The publication-period denominator respects actual publication cadence or a declared observable API range. It is **not automatically every calendar day**: a weekly newspaper need not publish daily, and a social account need not post every day. No known cadence/inventory means an unknown denominator. Natural silent periods and peaks are not penalties. Partial September ends on the existing cutoff; inapplicable pre-foundation periods require evidence. A source-range denominator must not be extended to a whole-platform population.

Identity/date resolution uses the target publication entities, not previews, wrappers, attachments or all returned objects. An unresolved-date entity remains in that denominator and the retained pool; it cannot be allocated to a month by retrieval time. Compute that dimension at a broader source/snapshot scope when its month is unknown. Do not silently drop unresolved dates to obtain 100% within a dated-only view. Native text mappings do not establish truth, climate relevance or emotion.

### Calculation and uncertainty

For each evidenced dimension, the script requires `scope_ref`, immutable `manifest_ref`, `unit_namespace`, unique `target_ids` and unique `covered_ids`. Covered IDs must be a subset of the target. A semantic or climate filter is not a permitted target definition. A manifest reference is an evidence contract, not automated verification of the external inventory's completeness.

Let `v_j = |covered_j| / |target_j|`, with `w = (0.40, 0.25, 0.20, 0.15)`. For known applicable dimensions `K` and unknown applicable dimensions `U`, publish:

`lower = 100 × sum(K, w_j × v_j) / sum(K ∪ U, w_j)`

`upper = lower + 100 × sum(U, w_j) / sum(K ∪ U, w_j)`

Also publish every component's counts, ratio, evidence/status and the resolved weight fraction. Unknown dimensions keep their weight; they are **never reweighted away**. A proven inapplicable dimension can be excluded, with its evidence and changed applicable-weight denominator explicit. Empty denominator is null, not success. All-inapplicable scopes have no numeric result. These are logical bounds from missing evidence, **not statistical confidence intervals**. Do not compare different frame/weight versions as if they were a common measure.

For example, complete identity/date resolution alone gives a **15–100 range with 15% of weight resolved**, not 100% coverage. Four evidenced 50% components give 50, but this remains fulfillment of a declared bounded scope. Even four 100% components cannot establish historical population completeness or analytical readiness; native-frontier closure still requires its own exhaustion evidence. No aggregate threshold admits/removes data, stops acquisition or releases later analysis. Use the component table as the primary report; any aggregate is secondary and must retain the uncertainty interval.

The closed metadata do not establish the required denominators for these four-dimensional monthly assessments. The current CLI therefore leaves those dimensions unknown, alongside the actual entity/source/month counts. It does not retrofit a target frame from observed data. New adapters should emit compact inventory/issue/frame manifests during ordinary acquisition so this evidence grows without a separate full-corpus audit. Sensitivity to alternative declared weights can be reported later on the same evidence; changing weights cannot fill an unknown denominator.

## 5. Demand-driven scheduling with collection as the main activity

**There are no fixed time shares.** Historical recovery, old-prefix continuation, source/context recovery and ordinary production are need labels. Advance existing viable native inventories beyond two articles and handle specific unresolved needs when their routes are actionable. Prefer real acquisition over unrelated preparation at equal priority; a necessary historical-route repair may outrank routine expansion. Do not optimize the coverage index, entropy, HHI, counts per second or a desired histogram.

The tested pure selector accepts source/range evidence, `need_priority` (0–3), action kind, remaining-work/block state and waiting rounds. It selects the lowest `max(0, need_priority − floor(wait_rounds / 4))`, then the longest-waiting opportunity, then acquisition before route preparation and a stable ID. Waiting-age promotion prevents a viable older/harder route from being displaced forever. Priority 0 is a named severe gap or enabling repair, 1 an evidenced truncation/continuity issue, 2 ordinary native continuation and 3 optional expansion. Priorities are explicit coordinator decisions with evidence, not calculated from the aggregate coverage score.

Operations are bounded native batches/cursor continuations. After each batch, update the remaining frontier, failures/cooldowns and waiting states, then select again. Every attempt's actual duration is observable, but **no lane receives an assigned percentage of hours**. Blocked work cannot consume requests; preparation must resolve a concrete next step and end with a usable route or explicit blocker. Ready acquisition resumes immediately when an enabling repair finishes. No repeated pilot/audit cycle or speculative database migration should occupy the collection window.

Known access stops remain in candidate opportunities. Every actual operation still needs fresh source/release/deadline, request/object and live resource checks. No acquired article count, peak, sentiment, topic or desired distribution is an input to the selector. A high-volume month stays eligible. An offline opportunity is not permission to fetch it.

## 6. Runtime integration gate and regression cases

The modules in `src/fear_temperature/media_planning/` are an **offline implementation**, not yet imported into either closed collector. Before a future release, the collector adapter must:

1. Bind the source/alias/frame/config version; load declared inventory and persistent cursor state.
2. Call the demand-based selector at bounded operation boundaries, update need/cursor/cooldown states, and record elapsed time without enforcing time shares.
3. Under the shared lock, re-read both leases, actual free space, cumulative stream/shared bytes and source/request/object ceilings. Hold its one stream writer mutex. The pure `execution_guard` is an input validator, not a lock, resource reader or authorization authority.
4. Reserve the complete pending raw/decompression/journal/export footprint plus the 64 KiB receipt allowance, 48 MiB recovery and 15 GiB physical floor. Separately enforce shared and stream retained-byte limits, with other pending leases reserved conservatively.
5. Save/load permitted returned material, update the ingestion journal and cursor transactionally where possible, and emit source-month inventory progress. Body eligibility never depends on semantic relevance or a desired distribution.
6. Produce a changed-tranche manifest and one terminal reconciliation. Do not rerun old raw/body acceptance.

Required regressions cover source alias cycles/conflicts and cross-stream boundaries; identity-bearing URL queries; identical text with independent publications; federated publication memberships; repeated observations; conflicting version/date snapshots; unknown/empty/partial inventories; source-entry decomposition; partial September and pending dates; evidence-weight uncertainty; demand/age selection without time quotas; no count-based stop; expired releases, source blocks, byte limits and peak-operation capacity. See `tests/test_media_planning.py`.

## 7. Reproduction and publication

Run against the named closed metadata only:

```sh
.venv/bin/python -m fear_temperature.media_planning \
  --snapshot work_packages/M1_source_access/27_newspaper_context_recovery_20261008 \
  --config configs/media_planning.json \
  --output /path/to/a/new/output-directory
```

An existing output directory is rejected rather than overwritten. Outputs contain source and month metrics, publication/hash groups, source-composition decomposition, legacy-floor diagnostics, identity conflicts and input/code/output hashes. Candidate opportunity lists stay in an ignored `control/` subdirectory. An optional `--coverage-evidence` JSON file supplies `snapshot_ref` (the exact closed snapshot path) and unique `cells`, each with `stream`, `month` and `dimensions` using the evidence contract above. Inputs and code/output digests are recorded; supplied evidence is validated structurally, not externally re-certified. Published source/body metadata preserve provenance; original corpus databases, raw responses, full bodies and frozen reports are never opened or modified by this CLI. The independent sealed reviewer remains separate and unread.

## 8. Auxiliary parent-source statistics

The separate [parent-source monitor](PARENT_SOURCE_MONITOR.md) groups sources under distinct acquisition-family, publishing-organization, platform-network, software-family, instance and community relations. It supplies current and changing parent/source/entity/body/month metadata for auxiliary source-quality checks and visualization. It does not alter the coverage weights or provide input to the acquisition selector. Publisher independence remains unresolved without specific evidence. Current grouping under a snapshot must not be interpreted as proven historical ownership.
