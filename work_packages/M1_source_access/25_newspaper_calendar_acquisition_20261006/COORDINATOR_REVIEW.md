# Package25 closeout: usable ELT delivery with a physical-capacity stop

The existing owner is **completed and idle**. The bounded task delivered useful regular newspaper ELT inputs, but **the full-calendar objective is incomplete**. Acquisition ended at 19:01:45 CST on 6 October; final delivery completed at approximately 19:22, before the unchanged 21:52:36 deadline. No successor collection has been dispatched by this review.

## Reconcile the three article totals

- **391 additional qualified IDs** are disjoint from the accepted 142-ID baseline. Seventeen use previously acquired raw inputs; 374 use this tranche's newly acquired raw inputs. An article ID is not one HTTP download: two complete original articles may come from one dated print issue.
- **392 currently qualified articles** have actual whole TEXT in the new persistent newspaper database. One overlaps the accepted baseline. The database retains 400 article rows, 402 whole-text versions and eight preserved/reclassified article rows; pending/component evidence has 75 separate records. Versions and reclassified rows are not extra qualified articles.
- **533 complete IDs** appear in the combined selected register: 142 accepted baseline IDs plus 391 additional IDs. Of these, 141 accepted old articles remain referenced through their earlier body files and are not whole-TEXT rows in this new database. The combined register is not a claim that all 533 articles have been loaded into this database or that every old saved candidate has been assessed.

The source register, new-ID set and six monthly ledgers reconcile exactly. Persistent identities and body references survive corrections; source-link fields are present. This coordinator review reused the worker's saved database/reference checks and verified 33 delivery artifact hashes. It did not rerun SQLite integrity, query the database, sweep raw/body hashes or reopen a full-corpus audit. Recorded evidence is in [control/COORDINATOR_CLOSEOUT_REVIEW.json](control/COORDINATOR_CLOSEOUT_REVIEW.json).

## Coverage improvement and remaining deficit

Pooled months meeting the lower bound rose **43 → 176 of 465**, from 9.25% to **37.85%**, with **133 newly passing months**. Here, passing means **minimum monthly coverage only**, not adequate density or completed newspaper acquisition. Twelve months have one article and 277 have none confirmed. Therefore **289 months remain below minimum**, requiring **566 article slots** under the present register: `12 + 2 × 277`. It is not `930 − 533`: 169 surplus articles cannot transfer across months. Preserve that surplus, which may provide useful source diversity even when it does not close another pooled monthly gap. The production objective extends substantially beyond these floor slots.

| Frame | Before passing months | After passing months | One article | Zero confirmed articles | Combined qualified articles |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pooled | 43 | 176 | 12 | 277 | 533 |
| EU/Europe excluding UK | 0 | 80 | 7 | 378 | 167 |
| UK | 0 | 33 | 16 | 416 | 82 |
| AU | 0 | 39 | 10 | 416 | 88 |
| US | 37 | 62 | 9 | 394 | 159 |
| NZ | 0 | 15 | 7 | 443 | 37 |

| Publication period | Calendar months | Passing before | Passing after | Zero confirmed after |
| --- | ---: | ---: | ---: | ---: |
| 1988–1990 | 36 | 0 | 4 | 32 |
| 1991–2006 | 192 | 0 | 39 | 153 |
| 2007–2016 | 120 | 24 | 94 | 15 |
| 2017–September 2026 | 117 | 19 | 39 | 77 |

The longest remaining below-minimum interval is **May 1994–January 2007, 153 consecutive months**. This is an unfinished acquisition interval, not evidence of absent newspaper discourse. The Green Left frame already produced paired monthly articles through April 1994; its continuing observed native issue queue is a concrete next route. Its pre-foundation era still requires another newspaper frame.

Density is insufficient for a production corpus: 101/176 covered months contain exactly two articles, the median among those months is two, and the observed monthly maximum is seven. These are selected-register counts, not the newspapers' actual output. The [density table](MONTHLY_DENSITY_REVIEW.csv) and [volume plan](COLLECTION_VOLUME_PLAN.md) address Dai's clarification that two is only the coverage lower bound.

The early print route supplied eight whole original articles, two each in April 1988, October 1988, May 1989 and April 1990. They are not eight arbitrary PDF pieces. Original titles, dates, article boundaries and continuations are preserved in source scans/sidecars. A severely corrupted May1989 continuation remains outside the complete count, with another complete reporting article used instead. The other 32 months in 1988–1990 remain missing from the qualified register.

## What stopped the task

At the observed stop, free disk space was **16,173,236,224 bytes**: exactly **64 MiB above the 15 GiB floor**. The 48 MiB recovery allowance plus 32 MiB owner reservation and 64 KiB receipt allowance required 80.0625 MiB. The result was **−16.0625 MiB physical headroom**. This matches the released protection rule; the machine did not need to reach zero free bytes before the collector stopped.

Cumulative retained media was approximately **256 MiB**; after reserved writes, roughly **735 MiB** of the 1 GiB allocation remained available. The allocation and all regional attempt ceilings were unexhausted. Increasing the 1 GiB allowance would not address this observed stop.

Free space fell by about 1.34 GiB between dispatch and the collection stop, while cumulative accounted media grew by approximately 132 MiB. These two quantities are different: file allocation, temporary/shared activity and other disk changes are not measured by the media retention counter. The evidence does **not** establish which outside activity caused the remainder, and does not justify blaming the newspaper dataset for the entire decline or deleting raw evidence. Later capacity improved sufficiently for consolidating saved/prepared input, without reopening acquisition. The coordinator releases the completed owner's 32 MiB logical lease; this does not itself free 32 MiB of physical storage or clear the historical stop.

## Execution quality and source limits

The ELT chain produced actual durable article TEXT and preserved raw references; this is more than an interface-only pilot. Tenets of the whole-article, stable-ID/link and fixed-cutoff requirements remain. The worker retained eight component/compilation reclassifications rather than deleting the source content. Two intermediate title-field/variable errors occurred at 18:28 and 18:51 and the collector restarted. Four interrupted transport receipts and seven missing raw/partial references were reconciled at close, with originals/stops/counters preserved. Successful closing checks establish terminal consistency; they do not mean the execution had no faults or that every source claim is true.

The combined 533-ID register includes **408 student-press articles (76.55%)**, 78 Green Left advocacy-newspaper articles, 37 Otago Daily Times articles and ten InDaily articles. All 167 European entries here are Trinity News, an Irish student newspaper. The geographic strata are present, but source diversity/national representativeness is limited. These genuine newspaper sources need not be discarded; preserve their frames and treat source changes explicitly in later comparisons. National/European media conclusions require broader evidenced source frames.

Genre is unrecorded for 386 of 392 currently qualified database articles. The combined export also has incomplete inherited raw-reference/country fields for 141 baseline representations, while their accepted source/body evidence remains elsewhere. These are metadata-consolidation limits for later transformation; they do not invalidate the whole input or require relaunching a semantic audit. Reproduced statements, wire material and quotations require original-speaker attribution before a later measure is interpreted as the newspaper's own discourse/emotion. Coverage and Load status do not establish climate relevance or fear prevalence.

## Recommended continuation

1. Address **actual available write capacity**, preserving the existing 15 GiB floor and recovery rule. The unused 1 GiB allowance did not cause this stop; a production-scale allocation should be estimated from source inventories and actual storage, not increased as a substitute for disk capacity. Resume only under a new bounded release and fresh capacity snapshot, preserving this stop.
2. Correct the successor scheduler so articles and issues remain eligible after a regional month reaches two. The old `perform_pair` filter/break and floor-based issue selection made the coverage lower bound the operational acquisition target. Preserve that frozen code; implement gap recovery plus continuing native-index production in one ELT task under the [volume plan](COLLECTION_VOLUME_PLAN.md).
3. In the gap-recovery lane, prioritise the **12 single-article pooled months**, **May1994–January2007 long gap**, remaining **1988–1990** and **2017–2026** gaps. In the production lane, retain all eligible additional articles through declared source-year frontiers, with substantive daily/regional/general-interest newspaper opportunities and five-stratum source identities. Already covered months remain eligible; minimum coverage does not establish adequate volume or frame completeness.
4. Keep Extract → coarse structural cleanup → immediate durable Load. Consolidate the 141 accepted external-body baseline records and inherited metadata into the same store in a separately recorded Load step when authorised; reuse accepted evidence, without rereading all historical raw inputs. Later systematic transformation and source-attribution work stay separate. Report production article volume, source-index progress and source diversity alongside the two-article coverage floor.

No new source contact, social-media collection, government reopening, hidden evaluator access, further network request or automatic next round was performed. The publication endpoint stays 2026-09-21 and the prior heartbeat remains paused. New outer records and commit descriptions are English; frozen worker reports and raw evidence remain unchanged.
