# Pooled month × discourse-role coverage snapshot

> **Later source-text correction (11:56 UTC):** This checkpoint's 458/465 “readable” count was gated by the older UK parent `body_status` field. A read-only content-version/segment check found nonempty saved UK source text in five more months despite stale parent status. The corrected **stored-text presence is 463/465**, with only **2015-04 and 2015-05** lacking government text at that audit. See [the corrected source-text snapshot](../../../../docs/research/coverage_snapshot_2026-09-27/README.md) and the targeted bridge scope in [`targeted_2015_bridge/SCOPE.md`](targeted_2015_bridge/SCOPE.md). The historical 458 figure below remains the stricter status-gated operational count for this frozen checkpoint, not the current missing-text target list.

Checkpoint: 2026-09-27 10:53 UTC. Study bins: 1988-01 through 2026-09; the last bin ends on 21 September. This is **acquisition coverage**, not a climate/fear relevance finding or a source-completion claim. The [465-month × three-role ledger](pooled_month_role_coverage_2026-09-27.csv) is generated from committed UK 06, US/AU 09 and EU 10 databases by the [read-only builder](../build_pooled_month_role_snapshot.py).

| Discourse role | Months with dated source parents | Months with readable source parents | Validated warming/fear-relevant parents |
|---|---:|---:|---|
| Government | 465/465 | 458/465 | Not yet assessed |
| Media | Not acquired/audited in these databases | Not acquired/audited | Not yet assessed |
| Public | Not acquired/audited in these databases | Not acquired/audited | Not yet assessed |

Government totals below count **independent parents within each source**; they are source-parent sums, not cross-source deduplicated people, events, passages, or time-series observations. Metadata-only Works/records enter the dated column but not the readable column. A readable source text is still subject to relevance and, where needed, layout review.

| Source and date basis | Dated source parents | Readable source parents | Months with readable parent | Current boundary |
|---|---:|---:|---:|---|
| UK 06 parliamentary/policy records; official publication date | 248,035 | 246,981 | 423 | 1,054 UK records have no accepted extracted-body status |
| EU Commission CELLAR `act_preparatory` Works; official Work month | 50,578 | 15,299 | 198 | Work enumeration complete; Item stage through 2004-06 only |
| US EPA/DOE Federal Register selected rule/proposed-rule series; official day | 33,544 | 17,805 | 195 | Further selected-series bodies still being acquired |
| AU DCCEEW catalogue; independently evidenced original day/month | 5 | 5 | 5 | 821 catalogue candidates are **not** 821 dated policy Works; one precise-month issuer case is excluded pending scope review, two originals are year-only, most candidates have no original month |

The EU stage has 15,455 saved Item versions at this checkpoint: 15,326 with text extraction, 100 OCR candidates pending layout review and 29 scan-only Items pending OCR. Twenty-seven extracted HTML Works with table placeholders are withheld from the readable count, leaving 15,299 source-text parents. EU official Work enumeration includes one verified zero in its frozen `act_preparatory` class at 2024-08; other sources support that month. Source composition changes must be retained in later measurement.

## Newly supported pooled months and checkpoints

- Relative to 423 UK readable months, EU source text adds **28** government-readable months, concentrated in August/September 1988–2003 plus 1997-04 and 2000-09. The US selected series adds **seven** further months after UK+EU: **2004-08, 2005-08, 2006-08, 2007-08, 2008-08, 2009-08, 2010-08**. AU adds five dated original Works but no new pooled month. Thus the current government-readable union is 458 months. These are presence gains, not evidence of topical relevance.
- The 1997-12 Kyoto adoption *candidate* has government source text in all 49 calendar bins of a provisional 1995-12–1999-12 window; EU and US each contribute readable parents in all 49. Its exact event definition/date and eligible discourse responses still require an independent event register and relevance work. Media/public availability is not established.
- The independently dated 2015-12-12 Paris Agreement adoption candidate has government source text in **46/49** bins from 2013-12 through 2017-12. The uncovered bins are **2014-08, 2015-04 and 2015-05**. Official US/EU metadata lists potential parents in each, but no retrieved readable body from those sources is committed for those months. All 49 media/public bins remain unacquired or unaudited here. Mere calendar coincidence is not an event response.

## Specific unresolved evidence windows

| Month | UK dated / readable | EU dated / readable | US dated / readable | Priority and reason |
|---|---:|---:|---:|---|
| 2012-08 | 3 / 0 | 115 / 0 | 120 / 0 | Government pooled source-text gap; selected bodies pending |
| **2014-08** | 4 / 0 | 82 / 0 | 85 / 0 | Paris 49-bin gap; target bounded retrieval |
| **2015-04** | 0 / 0 | 71 / 0 | 129 / 0 | Paris 49-bin gap; target bounded retrieval |
| **2015-05** | 0 / 0 | 92 / 0 | 81 / 0 | Paris 49-bin gap; target bounded retrieval |
| 2020-08 | 1 / 0 | 89 / 0 | 67 / 0 | Government pooled source-text gap; selected bodies pending |
| 2023-08 | 5 / 0 | 16 / 0 | 82 / 0 | Government pooled source-text gap; selected bodies pending |
| 2024-06 | 1 / 0 | 57 / 0 | 40 / 0 | Government pooled source-text gap; selected bodies pending |

For **every** proposed RQ1 shared-role month and RQ2 event window, media and public parents and relevance judgements remain unassessed. The 1988 IPCC institutional anchor is a historical collection boundary: a 24-month pre-window falls outside this study start, and its exact event date has not been fixed in the event ledger. Keep it descriptive unless a separately justified scope change supplies earlier observations. The Paris event and Kyoto candidate require independently selected event-linked passages; routine and low-attention bins stay in the denominator.

## Checkpoint acceptance and remaining scope

The latest US 500-parent ingestion committed at 10:52 UTC: **17,805/33,544** selected-series parents have one committed version each. A read-only changed-tranche reconciliation found 17,805 unique linked US parents, zero orphan versions and zero downloaded US versions whose parent lacks the extracted/cleaned status. The EU stage query reports one version per 15,455 staged Works. This checkpoint reused earlier full byte audits; it did not rehash the entire corpus or rebuild figures. The UK 06 database was opened read-only.

The US and EU single-writer supervisors continue under their 15 GB free-space floors and ordinary rate limits. The blocked AU host route and 1988–1993 US full-issue archive remain documented source-specific limitations. The roughly 140 GB historical issue route is deferred unless a selected pooled event/window requires bounded retrieval. No former exhaustive country-archive goal is claimed complete. Next research preparation can start with dated/readable government intervals while relevance, media/public acquisition, event identity and source-composition sensitivity are developed explicitly.
