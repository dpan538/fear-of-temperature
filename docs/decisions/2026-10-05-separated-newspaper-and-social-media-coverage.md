# 5 October 2026 — separate newspaper and social-media acquisition; restore full-period coverage

## Decision and correction

Dai clarified that newspaper and social-media material must be acquired separately, and that the initial corpus-building objective is content coverage across the study period rather than a few demonstration months. Dai then clarified the purpose of a pilot: identify the proposal-aligned parent acquisition entries (websites, public archives and APIs), check interface stability and prepare for large-scale ingestion. These govern subsequent design. The fixed publication interval remains **1988-01-01 through 2026-09-21**; September 2026 is partial.

The coordinator incorrectly carried the three pilot months (1995-07, 2015-12 and 2025-07) and their 150 target coordinates forward as the operational media acquisition objective, then prioritised article counts over historical source and interface readiness. Round22 produced useful access/extraction evidence, but that scope could not deliver the full-period objective even if every target succeeded. This was a coordinator scope-design error, distinct from the worker's recorded execution defects. The correction does not demand that a pilot itself download a complete 38-year archive.

The submitted proposal already distinguishes editorial media from public/community expression (Sections 3.3–3.4), gives the collection a January 1988 start (Section 1.3), and warns against concatenating historical newspapers, letters/forums and contemporary platforms as interchangeable populations. Do not revise the submitted proposal or rewrite frozen rounds 19–22 evidence to conceal the scope error.

## Separate streams and units

| Acquisition stream | Unit and source frame | Treatment |
|---|---|---|
| Newspaper | Independently dated article in an identified newspaper title/edition or an evidenced archival reproduction | Register title, edition, publication date, article/issue identity, saved body or OCR, body boundaries, provenance and archive extent. An issue container is not an article. |
| Social media | Native post and separately identified comment/reply in an eligible platform/community | Register platform/community, native identity, parent/thread relationship, date, saved text and access route. Keep posts and comments distinct. |
| Other editorial media | Broadcaster, digital news outlet, commentary publication or news network outside the established newspaper frame | Retain existing evidence under its actual source type; do not silently count it as newspaper coverage. |
| Historical public expression | Letters to editors, forums or other evidenced public channels | Preserve a separate source-era subframe. These may extend public-expression evidence but do not manufacture pre-foundation social-platform records. |

Acquisition channel and discourse role are separate. A government account on a social platform remains institutional discourse; an editorial account remains media discourse. A carrier alone does not establish a public author. A letter printed in a newspaper is not automatically an editorial article. English language, publisher country and the place discussed do not establish an author's location.

Newspaper and social-media inventories, selections, manifests, coverage denominators and closeout totals must be separate, even when coordinated in one complete work package. Government transport work must not replace either acquisition objective.

## Full-period coverage ledger

Use the project's existing monthly reporting unit: **465 calendar months**, from January 1988 to September 2026. This is a continuous target calendar, not three demonstration dates. It is not an instruction to acquire every article ever published or a claim of daily completeness.

For newspaper acquisition, retain five disjoint geographic strata: EU/Europe excluding UK, UK, AU, US and NZ. Preserve concrete European countries and title/edition identities. Maintain 465 monthly cells per stratum (2,325 planned geographic-month cells), with a separate pooled 465-month view. A filled UK cell cannot conceal an EU gap; pooled temporal presence does not certify each stratum. Apply the same declared planned quota to comparable eligible cells; do not transfer an inaccessible stratum's allocation elsewhere. Exhaustive recovery of every country or every title is not a prerequisite for reporting usable pooled evidence.

For social media, retain the same target calendar but record each platform/community's actual existence and recoverable archive interval. Pre-foundation months are structurally inapplicable for that platform, not observed zeros and not recovered content. Existing-era access or archive gaps remain missing. Report both the full-calendar limitation and the applicable-period denominator; do not improve a score by silently removing inconvenient months. Modern platforms cannot be declared continuously covered back to 1988 without an evidenced historical source frame. The public-role historical extension remains a separate channel, with comparability unassessed until validated.

Each calendar/source cell distinguishes at least:

- **Readable parent present:** saved text, verified identity/date evidence and inspected article/post boundaries support the count.
- **Metadata only:** catalogue/search/index evidence exists but a readable parent is not yet saved.
- **Access or recovery gap:** source exists but the specified historical body is unavailable or blocked through the recorded route.
- **Unassessed:** no adequate observation has been made; absence of a query hit is not zero publication.
- **Structurally inapplicable:** the specific source/platform did not exist in that period, with supporting era evidence.
- **Verified empty eligible frame:** use only when a sufficiently enumerated eligible source frame supports zero records.

A basic monthly-presence claim requires at least one qualified independent readable parent in every claimed month. That minimum is not sufficient sampling density, complete archive recovery, comparable source composition or an analytical time series. A stronger completeness claim requires the observed source/edition/date frame and its enumeration limits, eligible count and retained count; an unknown denominator stays unknown. Full prose boundaries do not establish completeness of every embedded media component or equality to the historical content version.

## Pilot purpose: acquisition parents and ingestion readiness

Here, an **acquisition parent** means a source entry: a website, archive collection or API endpoint family. Register it separately from an **independent corpus parent**, which is an article, post or other native document. Websites are not document counts, and extracted passages are not additional source parents.

The proposal names Guardian for editorial media and Reddit as the preferred public route, with Mastodon as a fallback and source-specific geographical/historical extensions. Use that source topology as the starting map, then document public-route availability and historical scope. Dai currently has public Internet access only; a proposal-listed API or licensed archive is not an available entitlement. Mark unavailable routes honestly and identify evidenced public alternatives, without reclassifying a recent commentary site as a historical newspaper archive.

One consolidated pilot should deliver two separate source registries and a runnable chain, with the following evidence:

1. **Source and era mapping:** newspaper title/edition or social platform/community, jurisdiction evidence, original/archive relationship, actual historical range, gaps, source transitions and permitted access/export route. Explain how the source portfolio could address the full study calendar; do not infer body availability from catalogue dates.
2. **Interface probes:** saved bounded requests/responses across the source's early, middle and latest eligible eras, including the fixed endpoint where applicable. Check date filters and conventions, article/native IDs, pagination or cursors, ordering, attachments, full-body versus metadata/preview, rate limits and failure responses. Repeat a small declared probe to observe interface behaviour; a single HTTP200 or an API's documented existence does not demonstrate stable collection. A few probes do not prove every intervening month is recoverable.
3. **Restart and write path:** demonstrate deterministic enumeration, a saved cursor/checkpoint, bounded retries, raw receipt/version capture, extraction, identity mapping and idempotent insertion into a temporary staging database. Verify duplicate reruns, post/comment or article/issue relationships and interrupted-write recovery using a small real sample plus separately labelled fixtures. Formal government data stays untouched; production ingestion retains single-writer/transaction rules.
4. **Scale preparation:** estimate record/byte ranges from the observed source frame, with unknown quantities explicit; specify request pacing, tranche order, storage reserves, write batches and resumability. Deliver an executable route and a concrete rollout plan, not a larger schema or test count without real chain evidence.
5. **Per-route readiness:** distinguish ready within a tested scope, provisional, blocked and unassessed. Report source-entry/interface readiness separately from actual content coverage. No route or full-period completeness is declared solely because the pilot deadline ended.

Small real payloads are chain checks, not the main pilot output or a proxy for 465-month coverage. Reuse qualified round22 bodies and saved evidence where applicable, repairing only evidenced changed paths rather than running another arbitrary 150-article pilot. Independent audit scripts remain sealed; source owners receive factual evidence issues only.

## Acquisition sequence and acceptance

1. Complete the consolidated source-entry/interface/ingestion pilot above. Prioritise historical route viability; recent-only sources may contribute within their era but cannot be the sole design for 1988-onward coverage. Interface readiness is distinct from already acquired content.
2. After the evidenced rollout scope and resource preflight, advance separate newspaper and social-media acquisition in resumable calendar blocks. Acquire actual dated parents against the monthly ledger, prioritising unresolved temporal gaps with equal planned effort across the five strata. Checkpoints report progress against all 465 months, rather than substitute a pilot quota for the study target.
3. Repair the evidenced inline-text defect in a versioned derivative path and retain raw/prior body evidence. Perform one changed-tranche structural acceptance covering dates, source roles, identity/duplicates, boundaries and provenance; no repeated full-corpus audit.
4. Close each stream with actual-content coverage, density/source-mix tables, explicit residual gaps and a resumable checkpoint. Partial acquisition is reported as partial. Do not declare full coverage merely because a network deadline, test suite or three-month pilot ended.

Coverage establishes dated source presence, not climate relevance, emotion prevalence or fear. No climate/fear query or classifier, entropy target, uniform observed counts or preferential long-text selection is a source-inclusion or acquisition-success gate. Distribution diagnosis and later analysis sampling follow the recorded source frame; do not discard raw evidence to flatten coverage.

## Current evidence and execution boundary

Round22's 30 qualified visible prose bodies occur in only two months: December 2015 (10) and July 2025 (20). Its other editorial/source-type mixtures require explicit newspaper classification before a newspaper-specific total can be stated. It acquired no social-media posts/comments. This statement concerns round 22 only; it does not reset earlier frozen Guardian/public evidence or claim a refreshed whole-corpus count.

The round 22 limited government 11/11 transport result and its residual queue retain their original scope. Accepted historical government 465/465 is not newspaper or social-media coverage. Preserve all prior stops, publisher restrictions and government seals. Public Internet access remains Dai's available route; do not request credentials, purchase access or bypass restrictions.

This correction updates future scope and acceptance, not a live bulk-download release. Existing storage floors, shared locks, raw caps and reserves remain until an explicit bounded successor scope provides its preflight and any authorised budget revision. The pilot's 150 targets are not the total study acquisition budget or a full-period completion criterion. No new window, automated collector, formal import, private evaluator access or resumed heartbeat follows from this documentation change.

Evidence: [submitted proposal](../../proposal/thesis_proposal.md), [round 22 plan](../../work_packages/M1_source_access/22_real_payload_acquisition_20261005/PLAN.md), [round 22 coordinator review](../../work_packages/M1_source_access/22_real_payload_acquisition_20261005/COORDINATOR_REVIEW.md). This decision supersedes reuse of the [round 22 decision](2026-10-05-real-payload-acquisition-round.md) as a future full-period acquisition plan; its historical permission and outcomes remain unchanged.
