# Newspaper acquisition and transition evidence: coordinator review

Reviewed on 6 October 2026. Publication interval: **1988-01-01 through 2026-09-21**; September is partial. The acquisition snapshot is 5 October 2026, not the review date. This review covers package 23 only; earlier government and media freezes retain their original scope.

The outcome is useful source/interface preparation, a working real retrieval/staging chain for two newspaper frames, and a substantive literature package. It does **not** meet the full-period, geographically diverse newspaper objective. The next change should address queue selection and historical source access rather than add more articles from an already dense source-month.

## Actual deliveries and their boundaries

The original newspaper worker delivered 20 candidate source entries, a 465-month pooled ledger, 2,325 geographic-month planning cells and 25 passing targeted offline tests. Its frozen result is **zero newly acquired newspaper articles**: the then-enforced inherited reserve caused a resource stop. Its saved Texas parser diagnostic is not newspaper acquisition. The parser repair, metadata/source registry and staging prototype remain useful; a registry entry is not a working article route.

In the parallel research chat, Dai subsequently directly instructed actual collection and live capacity calculation, without the inherited combined reserve. The coordinator verified those human instructions in the thread history. The successor acquisition is therefore authorised, even though the original research-only launch and coordination snapshot predate that change. Neither the zero-result newspaper report nor the earlier resource stop is rewritten.

The successor retained **1,216 native publication units/versions**, of which **1,214 have readable saved text** and two remain pending for body/date accounting. These are publisher-native pages and one traced OCR article, not 1,214 established independent original stories. Tables, briefs, letters, composites and syndicated material retain their native identities and unresolved relationships.

| Newspaper stratum | Readable native units | Months with readable native units | Months with dated presence, including whole issues | Calendar denominator |
|---|---:|---:|---:|---:|
| EU/Europe excluding UK | 0 | 0 | 0 | 465 |
| UK | 0 | 0 | 0 | 465 |
| AU | 10 | 10 | 10 | 465 |
| US | 1,204 | 44 | 47 | 465 |
| NZ | 0 | 0 | 0 | 465 |
| Pooled union | 1,214 | **51** | **54** | **465** |

The pooled readable-unit calendar presence is **51/465 (10.97%)**; **414 months lack an acquired readable native unit in this package**. This is a lower bound for the collected frames, not archive completeness, verified independent-article coverage or zero publication in missing months. The geographic ledger has readable units in 54/2,325 cells; overlapping AU/US months reduce the pooled union to 51.

Four publisher PDF issues contain 118 pages. One 1988-02-02 article is separately traced across seven segments, with OCR uncertainty preserved. February 1989, February 1990 and February 1991 have a dated issue container but no article mapping yet. They explain the difference between 54 dated-presence months and 51 readable-unit months. Pages, issue containers and segments are not additional article parents.

## Distribution and implementation findings

- **The Tech contributes 1,204/1,214 readable units (99.18%)**. It is an MIT student newspaper supplement; it does not establish national US newspaper representativeness. The ten AU units come from InDaily, whose Independent Weekly print/digital transition remains part of its source frame. Two working carriers do not represent five geographic strata.
- **2007 contributes 647 readable units (53.29%)**. This concentration is consistent with the saved batch-selection rules: `plan_next_round.py` limits its catalogue to volumes 127–146, chooses the next unattempted issue in volume/issue order and takes up to 40 native URLs per issue. It has no geographic or missing-month queue. Continued execution of that planner would prioritise more dense The Tech issues over the study's largest gaps. This is an acquisition-design finding, not evidence of a climate event or a reason to remove legitimate 2007 records.
- January 1988 through December 2006 contains 228 months. Only February 1988 has a separately mapped readable unit here; **227 early-period months remain without one**. The three issue-only months remain useful saved inputs for segmentation. The HTML-era planner does not address the early-period objective.
- Two distinct 2007-04-24 URLs, *Editor's Note* and *Energy Special*, have identical saved text. Record an equal-text relationship pending wrapper/component/original-work reconciliation; preserve both raw responses and do not automatically delete either. Thirty table-bearing units and native brief/letter carriers also need explicit component/genre/author-role accounting before independent-story totals or comparative discourse measures are reported.
- Nine sampled units confirm the retained boundaries and bytes. One AU sample explicitly says it was first published on The Lead; that origin remains separate from InDaily's publication identity. Native brief text includes publication recruitment/contact notices, and the traced 1988 article retains OCR line-break/hyphen noise. These are named later structural issues, not grounds for delaying otherwise permitted raw acquisition or imposing a length/topic gate.
- Cached download replay generated zero new requests/raw bytes. A saved staging rerun retained 954 parents/954 versions and created zero new versions or metadata revisions. This demonstrates observed restartability/idempotence, not a universally stable API. Later changed-tranche staging reached 1,216 units.

## Transition evidence and its appropriate use

The research delivery contains 16 source entries, 12 core evidence families, 25 claim rows, 53 country-wave comparisons, nine era recommendations and five verified journal references. Its DOI/chart/read-scope validation contains 35 passing checks. Full-text readings, abstract-only readings and unresolved findings are explicitly distinguished. Bibliographic verification is not evidence that every paper was fully read.

There is **no supported universal newspaper-to-social-media switch year**. Country, population and metric must accompany any timing claim:

| Evidence frame | Supported timing | Interpretation limit |
|---|---|---|
| US, Reuters weekly use among online-panel news consumers | 2013–2015 observed-wave crossover bracket; 2014 inversion uses estimated values | Overlapping weekly categories; not all adults or a monthly switch |
| US, Pew adults often getting news | 2017 approximate parity; 2018 social 20%, print 16%, first exceedance in its question series | Print newspapers, not all newspaper-brand digital use |
| UK, Reuters weekly use among online-panel respondents | Rounded parity in 2016–2017; 2018 first displayed strict exceedance, social 39%, print 36% | Does not establish a whole-population or newspaper-brand crossover |
| Germany, Reuters weekly use | 2019 parity and 2020 first displayed strict exceedance in the retained report vintage | One European country and one survey metric |
| AU | Social already above print as a main source in the earliest retained 2015 comparison; earlier crossing unresolved | The 2025 social/online-news comparison uses a different comparator |
| NZ | National newspaper/social crossover unresolved | Overlapping outlet/brand/social categories cannot be added into deduplicated shares |

Primary examples are [Pew's 2018 report](https://www.pewresearch.org/short-reads/2018/12/10/social-media-outpaces-print-newspapers-in-the-u-s-as-a-news-source/), [Reuters UK 2018](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/archive/survey/2018/united-kingdom-2018/index.html) and [Reuters Germany 2020](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/archive/survey/2020/germany-2020/index.html). Exact chart values and their retained source references are in `transition_research/LONGITUDINAL_VALUES.csv` and `EVIDENCE_TABLE.csv`.

The five verified journal references concern cross-format complementarity/displacement, incidental social exposure, a newspaper's print cessation and traditional/social issue attention. They support preserving overlapping media eras and distinct units; none licenses cutting newspaper collection off in a universal year. Audience shares are not article/post sampling weights. Editorial social accounts remain media-role evidence where appropriate, rather than automatically public expression.

## Acceptance, resource status and remaining work

The [coordinator receipt](control/COORDINATOR_REVIEW_RECEIPT_20261006.json) records **17 passing checks**: 77 frozen newspaper-package files and 60 frozen research-package files agree with their submitted receipts, native identities/date bounds and calendar counts reconcile, all 2,519 raw/body file fingerprints match the owner's cached sizes/mtimes, and nine bounded body/raw samples agree. The owner's 3,747 acquisition checks and 35 research checks are reused with their scope stated. No formal database, government input, new acquisition, corpus model or sealed independent evaluator was accessed. The publication calendar was reconciled from metadata, not by another full raw/text scan.

The original 3,335,940,580-byte combined reserve is removed **for the directly authorised media successor**. Physical free space, the 15 GiB floor, 48 MiB recovery allowance and cumulative media budget remain distinct. The closing saved allocation is **107,575,001 / 134,217,728 bytes**, leaving **26,642,727 bytes (25.41 MiB)** at that snapshot. A new disk observation is recorded in the coordinator receipt; it is not a fresh download release. The next request must remeasure real usage and live leases. A larger multi-decade rollout requires an explicitly versioned resource allocation; unchanged 128 MiB is a separate constraint even when disk space is sufficient.

The NZ Press calendar's HTTP403 and two US transport failures remain stopped/recorded. Alternative lawful sources need specific route evidence, not blind retries or bypassing access controls. Successful sources need not wait for a universal adapter, every country's completion or climate/fear validation. No recurring collector was created; both reviewed threads are idle and the earlier coordinator heartbeat remains paused.

The [revised plan](REVISED_ACQUISITION_PLAN_20261006.md) preserves the full newspaper objective and replaces the next-round selection rule with a coverage-oriented source/month queue. This review accepts useful inputs and names unresolved scope; it neither starts social-post collection nor claims newspaper completion.
