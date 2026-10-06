# Newspaper coverage review and acquisition correction

The accepted register is a useful structural correction, but **the acquisition objective is substantially unmet**. Only **43 of 465 pooled months (9.25%)** meet Dai's lower bound of two complete distinct articles. The register confirms 142 articles in 76 months; it is a bounded inspected-evidence lower bound, not a final count of every saved candidate. The fixed interval remains **1988-01-01 through 2026-09-21**, with partial September.

## What the evidence establishes

| Frame | Months with zero confirmed | Months with one | Months with two or more | Confirmed articles |
| --- | ---: | ---: | ---: | ---: |
| Pooled | 389 | 33 | 43 | 142 |
| EU/Europe excluding UK | 457 | 8 | 0 | 8 |
| UK | 458 | 7 | 0 | 7 |
| AU | 444 | 21 | 0 | 21 |
| US | 416 | 12 | 37 | 100 |
| NZ | 459 | 6 | 0 | 6 |

Pooled passing months do not certify any regional completeness. US concentration is visible in the inspected selection; this convenience selection cannot estimate whole-corpus source proportions or entropy. Student and advocacy newspapers remain explicit supplements, and cannot establish representative national newspaper discourse merely by supplying dates.

| Publication period | Calendar months | Months meeting two-article minimum | Confirmed articles |
| --- | ---: | ---: | ---: |
| 1988–1990 | 36 | 0 | 0 |
| 1991–2006 | 192 | 0 | 11 |
| 2007–2016 | 120 | 24 | 82 |
| 2017–September 2026 | 117 | 19 | 49 |

The absence of confirmed 1988–1990 articles in this register does not erase four saved historical issues or assert historical publication absence. Those issue/article mappings remain pending where transcription is incomplete or column joins are corrupted.

## Separate recovery from missing acquisition

[GAP_QUEUE.csv](GAP_QUEUE.csv) reconciles the frozen readable-unit ledger with the current complete-article ledger for all 465 months:

| Queue state | Months | Next necessary action |
| --- | ---: | --- |
| Meets the minimum | 43 | Retain all qualified surplus and provenance |
| One confirmed, other readable native candidates saved | 4 | Inspect a bounded additional cached selection; resolve named candidates where feasible |
| One confirmed, only one readable native unit saved | 29 | Obtain a second distinct complete article |
| Zero confirmed, readable native candidates saved | 10 | Resolve/select cached articles or use another evidenced article route |
| Zero confirmed, no readable native unit saved | 379 | Real historical/monthly acquisition is necessary |

The four one-article cache opportunities are February 1991, May 2007, August 2013 and August 2014. The ten zero-confirmed cache months are February 1988, February 1989, February 1990, February 2007, September 2007, October 2007, December 2007, April 2008, June 2009 and February 2020. A cached table, component or corrupted transcript is not automatically another article. February 2007 has 182 readable native units in the earlier ledger, while the correction inspected at most three prior candidates per observed month without refill; this is a concrete unsampled-cache opportunity.

The current ledger deficit is **811 article slots**: 33 single-article months need one each and 389 zero-confirmed months need two each. It is not `930 - 142 = 788`, because 23 surplus articles cannot be moved to another month. This deficit describes the inspected register; some slots may be filled from already saved but uninspected articles, so it is not a requirement to download exactly 811 new bodies.

## Why progress remained insufficient

The coordination design continued to use pilot-scale execution limits after the objective had become a full-calendar acquisition task. The last tranche allowed 12 article-body transfers per stratum; the implementation charged individual HTTP hops, redirects and failures against that allowance. All five counters reached 12 and the worker closed about 45 minutes before its network deadline. Consequently, a request-hop limit served as the completion condition without delivering two complete articles per target month. Preserve that historical stop; revise the counters prospectively, rather than erase failures or silently resume the same scope.

The planner also pursued one first native page per missing month. That strategy can produce many new one-article months and table/component pages while barely improving the two-article criterion. The successor must use month-level article pairs, preserve unused candidates and progress to another native article when a component fails. It must retain already qualified surplus and must not filter by topic, fear, length or a desired distribution score.

The 128 MiB cumulative allocation was inherited from a pilot. At coordinator review it held 129,353,564 bytes, leaving 4,864,164 bytes (4.64 MiB) before the new small review files. This is a genuine allocation limit, separate from physical free space. The dispatcher's usual 2 MiB raw plus three-times-raw derivative reservation requires more remaining allocation than that. A large continuation cannot honestly be released under the unchanged pilot allowance.

The coordinator owns these scope and scheduling choices. There is no evidenced industry-average productivity comparator; assessment is against the declared calendar and article standard.

## Accepted evidence and limits

One changed-tranche review passed **22 checks**, recorded in [control/COORDINATOR_ACCEPTANCE.json](control/COORDINATOR_ACCEPTANCE.json). It reconciled 27 acquisition delivery hashes, 30 local-correction artifact hashes, six frozen tranche inputs, 110 new raw/partial receipts, 51 effective new body hashes, unique article IDs and traceable source-link fields, fixed dates, body references, six 465-month ledgers, six corrected derivatives and changed Python syntax. The selected HTML paragraph-presence and original-boundary inspection, the 10 targeted offline checks and the worker's own staging/idempotence checks were reused. Link-field acceptance is not a new live-link or publisher-permission verification. No formal database was opened, old raw collection rescanned, sealed evaluator accessed or frozen file rewritten.

Of 185 selected candidates, 142 are confirmed complete, 17 pending and 26 non-article components. Selected prior candidates contribute 101 confirmed articles; the successor contributes 41. Three mapped PDF candidates remain pending despite correctly traced named article identities and marker removal. Minor OCR noise alone is not a universal failure criterion: named missing/corrupted lines and column joins remain specific transcription limits. Native grouped briefs/editorial collections need original-item evidence; arbitrary splitting cannot create another observation. Exact-day/version conflicts remain distinct from supported month mapping, and current renditions do not prove unchanged historical bodies.

The raw bodies, scans, OCR payloads, databases and full-text-bearing frozen metadata remain local. The compact article CSV, ledgers, provenance receipts, operational code and reports are suitable for the project evidence delivery. Public metadata summaries do not replace the local original hashes/references.

## Actionable successor

[CALENDAR_ACQUISITION_PLAN.md](CALENDAR_ACQUISITION_PLAN.md) defines one complete continuation in the existing acquisition window: bounded cached recovery, paired monthly collection through observed native source indexes, specific early-period routes, resumable staging and one consolidated delivery. The proposed cumulative allocation is 1 GiB with 128 MiB checkpoints and an absolute four-hour runtime. This allocation is **proposed, not released**. The old 128 MiB scope and all source stops remain in force until Dai decides the allocation.

A finite primary-source route review found useful boundaries, without adding acquired articles:

- Green Left identifies its early archive and first issue in February 1991; the existing local archive chain already supplies 11 complete 1991 articles. Expanding that native issue/month route is evidenced, but does not prove every month is available or represent all Australian newspapers. [Publisher archive account](https://www.greenleft.org.au/node/50356), [publisher first-issue account](https://www.greenleft.org.au/2011/868/news/green-left-weekly-celebrates-20-years).
- The Harvard Crimson exposes a [1988 dated archive index](https://www.thecrimson.com/sitemap/1988/) and historical article HTML, so scan-only recovery is not the only possible US historical route. The observed index's issue-query links returned web-tool cache misses, so interface stability is unverified. Its [rights page](https://www.thecrimson.com/about/permissions/) does not clear retained corpus copying; keep this as an access/retention-pending candidate, not a released bulk route. No publisher contact was made.
- The Guardian's public-site guide reports availability from September 1998; its licensing page states after February 1999. Neither proves 1988 public full text. Preserve this boundary discrepancy and the separate API/key/retention limits. [Public archive guide](https://www.theguardian.com/info/2017/jun/26/how-to-access-guardian-and-observer-digital-archive), [licensing archive page](https://licensing.theguardian.com/products/archive).
- Victoria University's [official digitisation description](https://www.wgtn.ac.nz/library/about-us/heritage-collections-and-archives/more-about-the-collections) lists digitised Salient through 1979. This does not establish an eligible 1988 route. Do not substitute a pre-study archive for missing NZ months.

These observations make source-era and access limits more concrete; they do not guarantee full public-only recovery in all five strata. The priority remains actual newspaper acquisition. Social-media collection is not a remedy for newspaper gaps and remains separate. Climate/warming retrieval, association measurement and fear interpretation are later stages; this register does not yet support a comparable full-period newspaper time series.
