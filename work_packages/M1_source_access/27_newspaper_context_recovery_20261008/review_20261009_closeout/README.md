# Media acquisition closeout and eight-hour planning review

Both 9 October collector tasks are closed and idle. Newspaper reached its fixed 16:41:51 AEST deadline; social reached its additional 50,000-object boundary at 14:27:56 AEST. This review issues no messages, resumes no collector and creates no successor release. Dai requested an eight-hour next-round design, not dispatch during this review.

The study publication interval remains **1988-01-01 through 2026-09-21**, with partial September. Collection, native edit/version, publication and review timestamps have separate meanings. This is a metadata reconciliation of the closed tranche, reusing accepted body/raw/database checks.

## What changed

| Measure | Previous accepted view | Closed current view |
|---|---:|---:|
| Current non-campus newspaper articles | 3,085 | 9,538 (+6,453) |
| Newspaper pooled months with two known independent works | 262/465 | 365/465 |
| Newspaper one-work / zero-work months | 18 / 185 | 15 / 85 |
| Preserved campus-publication articles, separate frame | 9,249 | 9,249 |
| Social retained core text identities | 1,566 | 42,488 (+40,922) |
| Social dated independent bodies | Not retrospectively recomputed | 42,478 |
| Social usable observed months | 85/465 | 165/465 |
| Body-producing social sources | 8 | 14 |

Social separately contains 51,626 typed entities, 54,789 state versions, 88,091 relations and 17,213 attachment metadata records. There are 42,487 independently authored body entities; one legacy Python action is excluded, and nine named date conflicts are additionally withheld from dated coverage. Raw bytes and all affected identities remain retained. Native entities, wrappers, versions and observations must not be added together as independent voices. Binary attachments were not downloaded.

See the frozen [newspaper report](../continuations/20261009_newspaper_open_production/worker/DELIVERY_REPORT.md), [social report and storage assessment](../social_public_api/continuations/20261009_public_native_expansion/worker/summaries/COLLECTION_REPORT.md), [schema](../social_public_api/continuations/20261009_public_native_expansion/worker/NATIVE_SCHEMA_V2.md), and the consolidated tables in this directory.

## Distribution and analytical limits

Newspaper's 365 pooled floor months mask regional gaps: EU/Europe excluding UK 12, UK 11, AU 184, US 90 and NZ 118, each against 465. The current view has nine newspaper sources. The Bridge contributes 27.2% and Northern Rivers Times 20.6%; neither share is a population weight. Of the 365 floor months, **157 have exactly two known works**, so minimum presence is still often thin. The largest article month is September 2025 with 486 article IDs but 453 known work families. Those are different measures, and retained copies are not deleted.

The longest newspaper gap is **January 1988–January 1991 (37 months)**. Other long gaps occur in 2005–2006, 2007–2008 and 2009–2012. The 2017–partial-2026 interval has 116/117 newspaper floor months; January 2023 remains missing. The raw count in a gap means not yet acquired, not absent historical discourse. Current newspaper and dated social evidence coincide in 161 months; that overlap alone does not establish matched national frames or a comparable role/emotion time series.

Social has 36,383/42,478 dated bodies (85.7%) in 2017–partial-2026. September 2026 alone supplies 10,194 (24.0%), despite being partial. Bluesky supplies 23,542/42,488 core texts (55.4%) from a contemporary account-graph frame, not random public sampling or historical graph membership. Four Mastodon instances each still cover only one month. Public access does not establish public-role authorship: 156 institutional records and 42,332 unknown-role records are reported, with author country unknown.

The 165/465 social figure is a full-calendar limitation, not a claim that all 465 months were applicable to each platform. The separate source-era table retains known inapplicability and unknown era. Only sources with a sufficiently evidenced full era have interpretable applicable denominators here: Sustainable Living 147/165, Earth Science 121/150 and Python 23/97. For sources with unknown-era months, observed/(observed + known missing) is **not** a complete historical coverage rate. No source is labelled 100% covered merely because only acquired months are dated.

Of the social reply edges, 12,242 are resolved and 11,114 unresolved; linked context is therefore incomplete even when an individual body is complete. Relation counts can reflect multiple observed relations per entity and include exact-overlap edges. They do not count people or independent posts. Future context recovery should be tracked separately from new independent bodies.

The pooled exploratory adjacent-month screen flags six newspaper and seven social months using count >=20 and >=3 times the largest available count in the preceding/following three months. September 2026 has only three observed neighbors. These are transparent, nonblocking review flags, not event labels, statistical anomaly tests, exclusion rules or targets. Unsmoothed data remain available. There is no entropy/HHI optimization, topic/fear filtering or inferred causal event explanation.

## Acceptance and unresolved issues

The coordinator verified hashes for 89 selected finalized metadata/code artifacts (about 260 MB uncompressed), reconciled current newspaper IDs/months and the social dated-month union, and reused 22 passed newspaper checks and the social terminal mapping/integrity checks. No database was opened and no raw/body corpus was swept. `acceptance.json` and `input_artifact_manifest.json` preserve the exact verification scope. Runtime controls, owner state, original close receipts, queues, raw/full bodies and stores stay local.

All six 465-month newspaper ledgers additionally reconcile to their source-stratum native IDs and known work-family sets. Selected Python implementation files pass syntax parsing. The inline charts and model passed real-browser checks at 1,024 and 360 pixels, including the 2 GB/4 GB selector's numerical update, no horizontal overflow and no JavaScript errors; the full desktop rendering was visually inspected. These interface checks do not validate forecast accuracy. The inline response fragments remain outside the repository; their reproducible input tables and model code are published here.

Three Alice metadata fetches occurred after a cached robots denial because a metadata-job guard was missing. The owner retained those bytes as an explicit exception, added the guard and loaded no Alice article. This is a source-access implementation defect distinct from the successful article-mapping checks; the exception remains in the published register. It must not be described as an entirely exception-free run.

Social's six Bluesky pre-project timestamps and three pre-beta Earth Science timestamps remain pending source/date mapping. A source-specific `post_type` repair recovered 1,293 already-retained Stack Exchange comments into the core without HTTP or counter reset. A missing lookup index caused one metadata anti-join to exceed 160 seconds; this does not establish a SQLite engine limit. Raw-file save, SQLite commit and external JSON counters are not a single atomic transaction. These concrete issues motivate the incremental lake/catalog design.

## Conditional model: what an eight-hour round could deliver

This is a **capacity-and-yield scenario model**, not a trained generalization model, confidence interval or eventual corpus-size forecast. One heterogeneous acquisition round cannot identify the total accessible historical population or the probability of finding unseen archives. Model inputs and all scenarios are published in `model_parameters.json` and `eight_hour_scenarios.csv`.

Assume 8 hours elapsed, 6.5 hours productive acquisition and 1.5 hours combined startup/repair/closeout. Newspaper reference rate is 6,453/4 = 1,613 additions/hour; social reference rate is 40,922/1.768 acquisition hours = 23,145 core additions/hour, excluding its later closeout. This social rate benefits from efficient public API batches and may not transfer to older forums. Newspaper uses 0.5/1.0/1.5 rate multipliers; social uses 0.35/0.65/1.0, explicitly chosen sensitivity assumptions rather than fitted quantiles.

Plan 50 kB per newspaper addition and 25 kB per social core addition, including expected raw/catalog/version/export overhead. These rounded planning coefficients are not measured body sizes or guaranteed marginal costs. Social's observed envelope grew roughly 0.828 GB for 40,922 core additions; repeated full metadata exports can make later growth worse than linear. Use a conservative 3.0 GB physical growth envelope, reserving 0.5 GB within it for journals/closeout; initial review observed about 19.75 GB free before packaging against the unchanged 15 GiB floor and 48 MiB recovery. Git and output growth consume the same physical disk. Recheck actual capacity before any release.

| Planning case | Newspaper additions | Newspaper total | Social core additions | Social core total |
|---|---:|---:|---:|---:|
| Conservative, current 2 GB social envelope | 5,243 | 14,781 | 46,314 | 88,802 |
| Central, current 2 GB social envelope | 10,486 | 20,024 | 46,314 | 88,802 |
| Faster, current 2 GB social envelope | 15,729 | 25,267 | 46,314 | 88,802 |
| Conservative, proposed 4 GB social envelope | 5,243 | 14,781 | 52,654 | 95,142 |
| Central, proposed 4 GB social envelope | 10,486 | 20,024 | 79,028 | 121,516 |
| Faster, proposed 4 GB social envelope | 15,729 | 25,267 | 68,542 | 111,030 |

The proposed 4 GB social envelope remains inside the shared 15 GB cap and is **not released**. The model also assumes prospective allowances of 200,000 additional returned entities and 5,000 requests, preserving inherited counters. Those are planning ceilings, not output targets or current permissions. Physical space binds the larger-envelope central/faster cases. The faster case allocates more shared bytes to newspaper and consequently retains fewer social additions; this is a resource tradeoff, not a prediction of lower API speed. Disk and source availability can produce results below every scenario, including zero additions for a blocked source.

For coverage, an independent Poisson-arrival sensitivity calculation allocates hypothetical new independent newspaper works across months using this tranche's empirical publication-month shares. Existing months with >=2 works remain covered; a one-work month passes after >=1 arrival and a zero-work month after >=2. This intentionally assigns zero probability to months absent from the tranche. It yields roughly **367.8–369.6 floor months** at the modeled volumes, with an empirical-support ceiling of 370 months. Thus continued production from the same temporal mix cannot solve most residual gaps. These expected values are not validated forecasts, and they assume future returned works are distinct. Social reuse of the same temporal support cannot exceed the existing 165-month union. New-source/historical-route recovery must be reported as a separate evidence-driven process, not an invented linear coverage gain.

## Next step

The [eight-hour collection and lake/catalog design](NEXT_ROUND_DESIGN.md) proposes a bounded next round with continuous production, explicit historical recovery and incremental durability improvements. No start time, new deadline, writer lease, new collection authorization or collector message is created by this report. Finalized acquisition implementation, schema/source documentation, manifests and this review are published together on main; raw content and execution state remain local.

Evidence levels remain separate: (1) dated presence/readable text is reported here; (2) climate relevance/similarity is deferred; (3) affect/risk associations require later validation; (4) fear-specific interpretation requires traceable passages and validated attribution. None of the volume scenarios predicts climate relevance, emotion prevalence or final thesis effects.
