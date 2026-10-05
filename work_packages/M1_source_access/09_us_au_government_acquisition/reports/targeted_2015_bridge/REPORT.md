# Targeted government source-text bridge: April–May 2015

**Acquisition checkpoint:** 27 September 2026, 12:36 UTC. **Scope:** existing US Federal Register EPA `final_rule` parents; original publication day; no climate keyword prefilter. This report concerns source coverage and comparability, not climate relevance, fear, media/public response or an RQ2 effect.

## Result

The 11:56 UTC saved-text audit had government text in **463/465** study months, with only **2015-04 and 2015-05** absent. All 125 prespecified official Federal Register originals in this bounded tranche returned HTTP 200, were saved with SHA-256 request evidence, and were committed as 125 distinct canonical parents and 125 content versions with nonempty source text. The two gap-month denominators were fully processed:

| Month / role in this tranche | Frozen eligible EPA final-rule parents | Verified original bytes | Committed versions | Nonempty source-text parents | Outcome |
|---|---:|---:|---:|---:|---|
| 2015-04, complete gap-month selection | 63 | 63 | 63 | 63 | Complete within the frozen source rule |
| 2015-05, complete gap-month selection | 38 | 38 | 38 | 38 | Complete within the frozen source rule |
| Eight prespecified surrounding/window months, three parents each | 389 eligible across those eight months | 24 | 24 | 24 | Bounded continuity-validation sample |

The [updated all-month government ledger](updated_monthly_government_presence.csv) therefore records **465/465** months with at least one saved government source text, versus 463/465 before this tranche. The 49-bin Paris candidate window changes from **47/49 to 49/49 government-text months**. These are pooled presence counts; they are not 465 observations of warming-related fear. The previous 458/465 parent-status count was lower because five UK policy months had saved source text with stale parent status. Those five were not downloaded again.

## Fixed source and continuity evidence

The [prespecified rule and sample](SCOPE.md) use the already frozen FederalRegister.gov enumeration (SHA-256 `0bf7e771bbba01785975942e8744c7542338079a3d18b415109ea3836176c46b`). Each parent is one canonical URL whose official agency strata include EPA and whose API genre is `final_rule`; the month is the original publication day. Cross-agency hits remain one parent. The [selection manifest](selected_parents.csv) was fixed before requests.

The [2012–2019 month table](monthly_source_coverage_2012_2019.csv) preserves the eligible denominator and separately records verified downloads, versions, extractable source text and metadata-only or zero months. The source has **4,407** eligible parents in **95/96** months of that wider frame; 2019-01 is a verified zero only under this exact EPA/final-rule rule. The Paris window, 2013-12–2017-12, has **2,304** eligible parents and at least one in **49/49** metadata months.

Actual text was checked beyond the gap months. Three deterministic parents in each of 2013-12, 2014-04, 2014-05, 2015-03, 2015-06, 2016-04, 2016-05 and 2017-12 yielded **24/24** verified, extractable originals. This tests adjacent months, matching calendar months in surrounding years, and the ends of the Paris window. Across all 125 acquired parents, the original Federal Register issue date, FR document number, EPA heading and “Rules and Regulations” section matched the frozen parent metadata; none required a source-identity exception. All 125 source representations had nonempty text and at least one cleaned segment. Their 24,313 cleaned segments had **zero** missing source mappings or cross-version mappings in the changed-tranche check. The [parent acceptance ledger](parent_acceptance.csv) records the exact URLs, dates, raw hashes, version IDs, source routes, text lengths and outcomes.

The API's `final_rule` genre includes distinct original-text subtypes. A bounded header/action reading of the 101 gap-month parents found 61 final rules or amendments, 29 direct final rules, five CFR corrections, four withdrawals and two other actions within the official rules section. The 24 validation parents contained 16, four, one, one and two respectively in those same categories. These are descriptive source-composition tags, not relevance labels. Source-text lengths ranged from 623 to 3,309,003 characters across the tranche; the median was 23,042. Later role/time measures should retain subtype and text-length/source-mix indicators.

## Boundary and next minimum

The selected EPA rule has continuous **metadata eligibility** in the 49-bin Paris window, and verified comparable source structure in the two full gap months plus eight prespecified check months. Its own saved-body series currently spans **10/49** Paris months and **125/2,304** eligible parents. It is therefore **not** a complete 49-month EPA full-text series, a trend estimate or a sample of event-linked climate responses. The other 39 months remain metadata-only for this US source at this checkpoint, even though UK government text supplies pooled coverage there.

If a self-contained EPA text-presence series is required, the smallest prespecifiable extension is a fixed small sample in each of those 39 months, with the same parent/date/genre and original-header checks; such sparse sampling would still be insufficient to assert population attention trends. If the EPA route becomes inaccessible or fails a later comparability check, the smallest already enumerated alternative is the EU Commission `COM`/`cdm:act_preparatory`/English Work series: it has positive Work and English Item-link metadata in all 49 Paris months, including 71 Works/69 links in 2015-04 and 92 Works/91 links in 2015-05. Its active Item writer must reach a safe checkpoint before any targeted EU body collection. No alternative metadata is counted as text here.

The US sequential supervisor stayed stopped after its earlier HTTP 429; its automatic resume wrapper was stopped at the committed checkpoint before this targeted run. The bounded target waited until the one-hour cooldown expired, held the existing US writer/resume locks, used ordinary requests, and encountered no new access failure. The EU Item supervisor continued in its separate stage database. The 15 GB floor remained active; no proposal, model, full-corpus audit or chart was changed.
