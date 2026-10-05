# December 2015 media frame and published-petition date contract

**UTC cutoff:** 27 September 2026, 14:19 UTC. **Execution window:** 13:43–14:19 UTC, within the one-hour ceiling. The [counting contract](COUNTING_CONTRACT.md) was frozen before the new archive audit; the [three-body selection](BODY_SAMPLE_SCOPE.md) was frozen after metadata closure and before those body checks. This brief updates source readiness, not RQ1/RQ2 estimates.

## Result at the fixed source rules

| Role and rule | November 2015 | December 2015 | January 2016 | What the count means |
|---|---:|---:|---:|---|
| Guardian environment nonvideo archive **candidate parent** with checked original UTC month | one day only | **396** from 31/31 days | one day only | December current archive frame only; all 396 article URLs returned HTTP 200 and had original publication metadata in December UTC. |
| Guardian distinct articles with body HTML checked | 2 | **4** | 1 | Verified lower bounds, including the previous December spot check; other candidate bodies were not audited. |
| UK Parliament `q=climate`, **published only by `opened_at`** | **0** | **8** | **5** | Main public/civic query frame, not all eligible petitions. November zero is only within this keyword query. |
| Same petition query, **all submitted by `created_at`** | 4 | 14 | 3 | Sensitivity frame includes rejected submissions and cannot be treated as public expression at creation. |
| Rejected submissions by `created_at` | 2 | 6 | 0 | Excluded from the main published role. |

The [new 49×3 table](paris_month_role_readiness_49x3_round2.csv) preserves 49/49 government readable-source months; it updates December media and uses published/opened dates for the 22 months in the petition query's active source interval. The [round-2 dictionary](FIELD_DICTIONARY_ROUND2.md) explains the changed fields and blank/zero rules. The original matrix remains an earlier snapshot, not a competing count contract.

## Guardian: a bounded December candidate denominator

The fixed `environment/2015/dec/DD/all` paths for all 31 days returned HTTP 200. Their pagination controls went to adjacent days; no within-day page-number link was exposed. After excluding video cards and deduplicating canonical Guardian-host article URLs, the pages had **396 distinct nonvideo title cards**. The metadata-only check read the first 64 KiB of each linked article response and found 396/396 HTTP 200, 396/396 canonical URL matches, 396/396 `article:published_time` values in December 2015 UTC, and no unresolved metadata record. [Daily audit](guardian_dec2015_archive_days.csv), [card frame](guardian_dec2015_archive_cards.csv), [article metadata](guardian_dec2015_article_metadata.csv) and [access notes](SOURCE_ACCESS_AUDIT.md) make the denominator reproducible.

Three further hash-selected article bodies, dated 10, 12 and 14 December, were readable in current HTML ([spot checks](guardian_dec2015_body_spot_checks.csv)); together with one distinct body checked in round 1, the verified readable **lower bound is four**. Only short excerpts were saved. Original publication time differs conceptually from the current modification time; archived title cards and today's HTML do not prove historical body fidelity. The 396 are current archive **candidates**, not 396 climate or fear articles, all Guardian articles, or 396 verified bodies. The Guardian Open Platform test key previously returned HTTP 401; no key workaround was used. Full-text rights and any future systematic body use remain an explicit source-access step.

**Guardian go/no-go:** **Go** for a source-aware, monthly *candidate inventory* at least for December 2015. **No-go** for using the four body checks or the 396 candidate count as a monthly fear measure. Before a longer series, reproduce archive/day coverage in adjacent months, check all eligible body access/version and permitted use, and monitor genre/archive composition. This is a bounded next stage, not a claim that the 49-month media panel is ready.

## Public: publication replaces submission as the main clock

The official UK Parliament 2015–2017 archived `parliament=1&q=climate` search contains 179 result positions but **177 distinct petition IDs** after two cross-page duplicates. Of these, **77 have `opened_at` and published/closed state**; **100 are rejected and have no `opened_at`**. The [ID mapping](petition_177_id_date_mapping.csv) and [three-month comparison](petition_nov2015_jan2016_month_mapping.csv) retain both clocks and statuses. Government response text and signature totals do not enter the public authorial text.

The date choice changes the event-side interpretation. Two petitions created in November (IDs **114128**, **113997**) opened in December. Two created in December (IDs **117267**, **117357**) opened in January. Therefore the earlier “November–January three-role overlap” is **withdrawn for the published-only main public series**: there is no November published `q=climate` petition in this finite frame. December and January contain eight and five, respectively. These 13 were already within the bounded manual review: the December group includes five climate-topic and two anticipated-harm-cue parents; January includes three and one. No explicit fear expression was verified in these 13 reviewed texts. The three labels remain distinct, and the result cannot establish that climate fear was absent outside this frame.

The [official archive](https://petition.parliament.uk/archived/petitions?parliament=1) lists a larger published petition population. A targeted [CSV export](https://petition.parliament.uk/archived/petitions.csv?parliament=1&state=published) exposes petition, URL, state and signature count, **without dates**. The [published JSON list](https://petition.parliament.uk/archived/petitions.json?parliament=1&state=published) exposes `opened_at` but has 25 records per page and a last link at page 438; two large-page parameters did not change that cap. The site's search form showed `q` and `state`, no date filter. An all-eligible **monthly** published-petition denominator therefore was **not** obtained in this hour. It could be derived in a separately scoped, deduplicated traversal of the official published JSON pages, with explicit storage and acceptance limits. The current 77-ID count remains a keyword-query denominator only. The [access audit](SOURCE_ACCESS_AUDIT.md) records the probes.

**Petition go/no-go:** **Conditional go** as a dated, published **civic petition** channel under `opened_at`. **No-go** as a representative general-public series or as a monthly population rate from `q=climate` alone. A verified query-zero in November is not a verified zero of public discourse. Published-only and all-submitted may be compared as a source-selection sensitivity, but rejected drafts must never be pooled with published utterances for the main role.

## Next minimum action and stopping point

The next decision is whether to fund a short, bounded Guardian rights/body check around November 2015–January 2016 and a separate official petition all-published JSON denominator tranche. Only after those frames are reproducible should cleaning/relevance review scale beyond the diagnostic parents. No CCF, ITS, role lead/lag, emotion prevalence, or causal claim is supported here. RQ3 remains deferred.

If Guardian access or rights prevent that monthly media route, **Carbon Brief** is a minimal specialist-media *candidate* because its dated December 2015 article pages are accessible ([example](https://www.carbonbrief.org/carbon-briefs-15-numbers-for-2015/)); a one-record WordPress API probe returned HTTP 403, so it is **not yet a validated replacement or denominator**. A bounded archive/rights check would be necessary before any switch. The archived Obama White House petition API was also probed and was inaccessible (HTTP 404 on the archive path; TLS failure on the old API host); it was not substituted for the UK civic frame.

The formal government databases, source supervisors, proposal and pre-existing uncommitted files were not changed. The new files are limited to this round-2 directory, and only direct new-output checks were run.
