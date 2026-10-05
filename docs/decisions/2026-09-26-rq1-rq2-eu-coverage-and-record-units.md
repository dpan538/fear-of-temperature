# Prioritise RQ1/RQ2 coverage and count independent records

Date: 26 September 2026
Status: user-approved priorities; operational reporting rules below implement that direction.

Scope clarification, 27 September: [Global temporal coverage and macro feedback](2026-09-27-global-temporal-coverage-and-macro-feedback.md) establishes a primary cross-regional research objective. The source-specific accounting below preserves provenance and measurement validity; it does not restrict the primary research question to individual countries. Observations from additional jurisdictions may contribute to pooled temporal coverage while jurisdiction-specific gaps remain recorded.

## User direction

Include EU material to extend early-year coverage; defer Ireland and New Zealand as current acquisition priorities; focus first on RQ1 and RQ2, coverage of the principal months and two years before/after selected events; establish the number of usable records without inflating it through excessive segmentation.

## Scope and priority

- Continue the authorised US/Australia acquisition work. EU/European Commission is the next priority for early institutional coverage, using the existing CELLAR reconnaissance as the starting point.
- Defer additional Ireland/New Zealand acquisition and RQ3 topology development for this phase. Preserve their reconnaissance evidence. Deferral reflects current priority and unverified systematic early coverage, not a finding that early material does not exist.
- EU remains identifiable while contributing to pooled international temporal coverage. It may close a pooled observation gap without changing the status of a missing national observation. Retain source-composition changes for later adjustment and sensitivity checks; they do not require national completeness before research can advance.
- Keep the study cutoff at 21 September 2026. This decision does not launch an additional bulk collection task, change the proposal or authorise a Git push.

## RQ1 coverage acceptance

Declare the actual jurisdiction/source/genre and government/media/public comparison window. Account for every calendar month in that window with both acquisition evidence and usable-record counts. Government-only coverage is preparation for RQ1; its completion alone does not establish a shared three-role window.

Monthly states must distinguish: enumerated and usable, partial recovery, verified zero in the defined scope, unknown enumeration/denominator, inaccessible known targets, unsupported source period, and partial observation at the study cutoff. One document in a month establishes presence, not completeness or sufficient precision. Zero observed documents does not establish historical zero. Retain verified source-specific zeros. Other jurisdictions may independently supply pooled monthly observations; never relabel them as records from the missing source or create observations by interpolation/duplicate passages.

Separate three quantities: months with resolved coverage status; months with usable observations; and recovered/usable targets divided by enumerated targets where that denominator is known. Do not label the first two quantities historical population coverage. Report longest unresolved gap and source-composition changes.

For monthly attention S, zero relevant documents with a valid positive eligible denominator yields zero; no eligible denominator yields missing. For conditional similarity Q, no relevant parent documents yields missing, not zero similarity. A quarterly summary must retain unresolved constituent-month coverage; aggregation cannot cure unknown acquisition coverage.

## RQ2 event windows

For each prespecified event, report 24 complete monthly bins before and 24 complete monthly bins after the event month; retain the event month separately. This produces 49 labelled monthly bins for the coverage audit. This audit convention does not dictate whether the event month is excluded or how an intra-month intervention is encoded in the later ITS model.

Report every bin by source/role, including eligible/usable/relevant parent counts and missing reasons. Select candidate events from independently documented dates and feasible coverage rather than observed effect size. Overlapping events, source transitions, unresolved gaps and incomplete endpoints remain visible.

The current September 2026 bin is partial. Events too near the study start/end cannot be described as having full two-year observation on both sides. Do not manufacture later observations or silently extend the 1988 study start. Mark such windows incomplete and retain them as descriptive candidates unless a separate scope change is approved.

Full temporal coverage is a collection objective, not proof of adequate statistical power. Actual variability, relevant-parent yield, measurement error and serial dependence still govern whether RQ1/RQ2 estimates can support the intended conclusions. Prior memo numeric planning gates remain provisional.

## Record accounting and segmentation

The analysis parent is a distinct publication Work or an independently identifiable governmental reply/statement. Keep jurisdiction, institution, source, genre and parent identity throughout. Metadata pages, language/format copies, mirrored files, attachments, repeated question-index hits and downloaded versions do not automatically create additional analysis parents.

Maintain the following separate counts per source and month:

1. `n_enumerated_targets`: deduplicated catalogue/index targets with the exact index unit stated.
2. `n_unique_parent_records`: distinct identified publication/answer/statement units.
3. `n_text_available_parents`: parents with actual extracted body content.
4. `n_usable_parents`: parents meeting the versioned minimum identity, issuer, date precision, body readability and boundary rules for the named use.
5. `n_relevant_usable_parents`: those passing the later validated warming/fear-reference relevance definition; unknown before relevance validation, never assumed equal to usable parents.
6. `n_segments`: extraction/cleaning scale only; never the independent sample size.

Year-only records can remain usable for historical reading while being excluded from exact-month counts. Define usability by the actual analysis rather than discarding their evidence. Preserve exclusions and uncertain boundaries with reasons.

Multiple questions answered jointly retain question relationships and a single identifiable reply parent where the source supports that identity. Exact-text repeats are candidates for relationship review, not permission to collapse distinct publication acts automatically. Split a container only at an evidenced independent document/speaker-response boundary. Repair line fragmentation without inventing documents. Model-sized passages can be derived later with exact parent/version mapping, and repeated/overlapping chunks cannot increase independent counts.

## Required reporting view

The next acquisition summary should prioritise a monthly table of source, jurisdiction, genre, date basis, enumerated target count, unique parent count, text-available parent count, usable parent count, relevant-parent count (or not yet assessed), segment count, coverage state and reason. Include an event-window table identifying the 24 pre / event / 24 post bins, shared-role availability and unresolved months. Reuse the established English coverage-figure style and retain Figure 5.

Lead with pooled monthly evidence and event-window availability across included regions, retaining source/role/genre breakdowns. Count independent parents separately from temporal bins and chunks; the raw record sum is not the number of independent time-series observations. Follow the 27 September project direction for acquisition stopping rules.

## Evidence and effect on prior decisions

The [26 September source/sufficiency review](../research/2026-09-26-ie-eu-nz-source-sufficiency-review.md) records 50,578 summed EU month-level DISTINCT-Work counts across 465 months, with 464 positive. These are reconnaissance counts, not a verified global unique or usable-full-text total.

This prioritisation supersedes that review's suggestion to advance Ireland and NZ alongside EU immediately. Existing raw preservation, single-ingestion, source-specific identity and coverage-first decisions remain applicable.
