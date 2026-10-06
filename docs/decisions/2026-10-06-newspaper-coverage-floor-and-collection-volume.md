# Newspaper coverage floor and production collection volume

Date: 6 October 2026. Authority: Dai clarified that two articles per month establish only the coverage lower bound. Newspaper acquisition should produce a substantial corpus rather than stop at this lower bound.

## Correct the operational interpretation

The two-article requirement remains: zero or one confirmed complete independent article is below the monthly minimum. Two or more establishes **minimum monthly coverage**, not sufficient density, complete source coverage or analytical readiness. It is neither a monthly acquisition target nor a stopping condition. All eligible additional articles in the declared source frame remain available for collection and Load.

Package25 preserved some surplus, but its scheduler operationalised the floor as a limit. In `worker/calendar_run.py`, `perform_pair` only groups targets where the regional count is below two and breaks once that count reaches two. Green Left issue discovery also excludes months already at two. This prevented systematic density acquisition even with unattempted native article links. The original code, scope, reports and receipts remain frozen evidence of that behaviour; apply the correction in a bounded successor rather than rewriting this delivery.

## Production collection objective

Use a single restartable ELT pipeline with two scheduling purposes: fill calendar gaps and ingest eligible articles from declared newspaper title/edition/era frames. The main acquisition frontier follows real native indexes, issue tables of contents, sitemaps or permitted APIs and continues past two articles in a month. Completion concerns exhaustion of the declared accessible frontier, or an explicitly recorded resource, access or deadline stop. It does not concern attainment of two articles, uniform monthly counts or a distribution score.

Prioritise additional viable daily, regional and general-interest newspaper frames alongside existing student and advocacy newspapers. Keep all accepted sources and their actual classifications. Equal prospective opportunity across EU/Europe excluding UK, UK, AU, US and NZ does not require equal output or justify moving an unused regional allocation to another region. European country identities and applicable eras remain explicit.

Plan production volume from observed source-index inventories, not from `465 × 2`. An initial delivery milestone on the order of ten thousand additional complete articles is a proposed scale checkpoint, followed by source-supported expansion toward hundreds of thousands. These are planning magnitudes, not approved download quantities, evidence of source availability, fixed monthly quotas or promises for one four-hour run. Do not stop an accessible source-month at an arbitrary article count or extend a deadline merely to hit a numerical milestone.

Comparison with government data must use comparable independent complete publication units and declared source frames. The government seal's 248,319 UK effective source-specific parent identities include a mirror; complete bodies and cross-route independence are unestablished. They are not a globally deduplicated complete government-publication total. Newspaper production should support much greater publication density where the chosen newspaper frames supply it, without manufacturing duplicates, fragments or a predetermined newspaper/government ratio.

## Reporting and execution

Report minimum coverage separately from article volume, title/edition diversity, source-era availability, index/cursor progress and extraction/Load outcomes. Existing frozen fields such as `passing_months` keep their historical names; explain that they measure only the two-article floor. Subsequent outer reports use `months_at_minimum_coverage` or an equally explicit label. Catalogue enumeration is discovery evidence, not confirmation of readable complete articles or exhaustive archive coverage.

Preserve Extract → coarse structural cleanup → immediate durable Load, whole-article IDs/links, the fixed 1988-01-01–2026-09-21 interval and the separate social-media stream. Reuse accepted operational checks and verify genuinely changed scheduler/storage behaviour once. No topic, fear, minimum-length, entropy/HHI or uniformity gate is added; systematic transformations and research sampling occur later on retained data.

The completed package25 owner remains idle. This clarification does not clear its physical-space stop, enlarge the 1 GiB allowance, lower the 15 GiB floor, delete evidence or start collection. A successor needs actual write capacity and one bounded release with the existing owner, shared lock and single database writer. The [production-volume plan](../../work_packages/M1_source_access/25_newspaper_calendar_acquisition_20261006/COLLECTION_VOLUME_PLAN.md) records the concrete adjustment. New outer reports and commit descriptions are English; frozen originals remain unchanged.
