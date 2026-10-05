# Fixed cutoff, distribution and source-quality preparation

Date: 4 October 2026. Status: accepted from Dai's instruction. Scope: current development priorities and reporting; no retrospective relabelling of pilot evidence or revision of the submitted proposal.

## Fixed time boundary

Retain the existing study publication-date interval, **1988-01-01 through 2026-09-21**. The endpoint is anchored to the initial extraction period, not to the current date. The 04 collection scope already records 21 September as the inclusive UTC calendar-day query limit, with its actual first observation ending at 01:10:54 UTC; the 06 collection-authorisation record is also dated 21 September. These are distinct events, not evidence of one exact shared extraction-start timestamp. Preserve their actual timestamps and date precision rather than inventing a second-level global cutoff. September is partial and a source may have a narrower observed boundary.

Later collection may recover older eligible records. Store publication date, retrieval/extraction time, version/modification time and report snapshot time separately. Reports produced in October still display the fixed September endpoint. Later retrieval of a changed webpage does not establish its exact historical wording. Flag out-of-interval or uncertain-date records separately; do not silently alter dates, delete originals or extend the interval. A future endpoint extension requires Dai's explicit decision and a new corpus version.

## What is complete and what comes next

The recorded pooled government corpus has source text in all 465 study months. This meets its basic temporal-presence target. It does not assert three-role or topical coverage, and those later questions must not invalidate the completed acquisition milestone.

Current work has two objectives:

1. **Distribution:** explain the shape of the collected records. Inspect source × month × genre counts at independent-parent level, together with text length and extraction segment counts. For peaks, check duplicate IDs/canonical URLs, mirrored or syndicated works, repeated versions, attachments counted as works, record splitting, pagination, batch filter changes and wrong date fields. Then distinguish a supported collection artefact, legitimate publication concentration, independently evidenced candidate event/checkpoint, and an unresolved anomaly. A high count alone proves neither accidental overcollection nor substantive event importance. Do not cap, downsample or equalise peaks merely to make distributions smooth.
2. **Source quality:** establish which texts are original utterances, archival reproductions, secondary reports, mixed or unresolved, and which identity/date/content relationships can be verified. Identify specific missing original routes, broken mappings or conflicting metadata that justify supplementation. Do not resume global enumeration solely because every provenance issue cannot be resolved.

## Source assessment fields

Use a transparent review ledger before any schema change. The following are recommended review dimensions, not a claim that these columns already exist in the database:

| Dimension | Suggested values / evidence |
|---|---|
| Evidence unit | Source ID, stable parent ID, object/version ID and source role |
| Directness | Original utterance; archival reproduction; indirect/secondary report; mixed; unknown |
| Original/reproduction link | Issuer, canonical/original URL, archive URL, document number and relationship basis |
| Verification | Verified; partly verified; pending; conflicting; inaccessible, with the specific field or content checked |
| Conflict type | Identity/date/version/content mismatch; attribution ambiguity; or a substantive claim disputed in the source—do not conflate these |
| Review evidence | Supporting URL/local reference, check date, original date precision and reviewer/rule |
| Follow-up | Targeted original retrieval, metadata reconciliation, extraction repair, contextual note, or no action |

Directness is relative to the evidence question: an original newspaper article is direct evidence of media discourse, even if it is secondary reporting about a policy. A petition is direct evidence of its author's expression. An authentic archived copy can preserve a primary document. Verification of provenance does not verify every factual claim. A contested claim may itself be research evidence; record the dispute rather than automatically discarding it. Do not impose a single unexplained confidence score or a fixed government-above-public credibility ranking.

## Cleaning versus analysis

Current cleaning concerns identity, dates, missingness, duplicate/version relationships, segmentation artefacts, text lengths, storage mappings and reproducibility. Preserve raw files and stable IDs; record every derived repair, duplicate grouping or exclusion reason. Near-duplicate or outlier detection nominates review candidates and does not itself authorise deletion.

Climate relevance, topic membership, affective association, fear classification and causal attribution belong to the later analysis stage. Algorithm specifications, evaluation designs and synthetic software checks may be prepared, but a corpus cleaning task must not run substantive climate/emotion filtering, label unreviewed records irrelevant, or assume every text/peak is caused by climate change. Preserve broad source frames and neutral material. Existing pilot labels remain frozen diagnostics.

This clarification supersedes the coordinator's 4 October suggestion to make climate-topic validation an immediate data-quality priority, and refines the earlier [staged construct decision](2026-09-27-staged-climate-affect-and-fear-interpretation.md). It updates project instructions and logs only; no corpus repair or semantic reclassification was executed by recording this decision.
