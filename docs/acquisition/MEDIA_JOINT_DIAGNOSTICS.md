# Joint media distribution, amount and parent-source diagnostics

Version 2, 10 October 2026. This is an offline reporting method, not a collector
selector, quality rank, deletion rule or declaration of corpus completion.
The fixed publication interval remains 1988-01-01 to 2026-09-21.

## What the method changes

Two observed articles establish presence, not sufficient historical density.
The former `coverage >= 2` flag has zero prospective evaluation weight. There
is no replacement constant that makes an unknown archive complete. A single
large archive can increase volume while reducing the effective diversity of
the collected frame. Conversely, a real event can create a valid sharp peak.
Report these situations separately, then inspect their conjunction.

The implementation is [media_diagnostics.py](../../src/fear_temperature/media_diagnostics.py).
The [reproducible validation package](../../work_packages/M1_source_access/31_media_joint_validation_20261010/README.md)
contains closed-input results, simulations and literature evidence. No active
collector imports this module. No topic or emotion labels are computed.

## Units, denominators and parent identity

Use one eligible complete newspaper article or one independently authored,
usable dated social body. Do not count issue containers, segments, versions,
attachments or saved HTTP responses as additional publications. Retained IDs
are not necessarily independent works until known reprints/duplicates are
resolved. Preserve raw IDs and versions; apply confirmed aliases in a versioned
derived counting view. Identical text alone is not a confirmed alias.

Keep observed presence, enumerated inventory recovery, source-frame breadth and
statistical interval coverage distinct. Inventory recovery is `loaded eligible
IDs / enumerated eligible IDs` only within a matched source, interval, unit and
inventory snapshot. Unknown denominators yield **unknown**, not 0 or 1. A count
of observed sources has no completeness denominator without a declared source
universe. Pre-foundation social months are inapplicable only with evidence;
unknown historical access is not zero public expression.

Parent mappings must name a relation dimension and valid time. Publisher or
operator, acquisition archive, platform network, software, instance, community,
author and independent publication work are different relations. Shared
Discourse software does not prove shared ownership; two titles may share an
operator. A current ownership page does not prove historical ownership. The
consumer must resolve ambiguous multi-parent sources or leave them outside
the one-parent sensitivity contract. Report the excluded/unresolved mass.

## Interpretable output vector

| Output | Range | Meaning and limitation |
|---|---|---|
| Observed presence | 0 or 1 | Dated text exists in this snapshot; not completeness |
| Inventory recovery | [0,1] or unknown | Scoped enumerated recovery, only with a verified denominator |
| Parent mapping fraction | [0,1] or unknown | Fraction assigned to evidenced parents in one dimension |
| Effective parent count, P | [1,K] for nonempty data | Concentration-adjusted number, not population representativeness |
| Parent diversity, B | [0,1) | Probability two draws from the observed distribution have different parents |
| Amount index, A | [0,1] | Precision scenario for a future binary estimand; not achieved accuracy |
| Source-mixture JS | [0,1] or unknown | Composition change between two collected source distributions |
| Signed distribution contrast, D | [-1,1] or unknown | Within a fixed observed source panel, below/above nearby rate |
| Joint sensitivity, J | [-1,1] or unknown | D scaled by amount under parent-dependence scenarios |

Always expose N, raw K, mapping coverage, panel share and all components next to
J. Never sort retention or acquisition by J, B, P or A. Small J may mean small
contrast **or inadequate information**; these are not interchangeable. Neither
a positive nor a negative value means positive/negative emotion. No value is a
probability that a record is wrong, and no significance test is performed.

## Parent concentration and dependence

For parent shares p_g = n_g/N, use P = 1/sum(p_g²), the order-2 Hill effective
number, and B = 1-sum(p_g²). Ten equally represented parents give P=10; one
dominant parent plus nine tiny contributors gives much less. This application
uses the mathematical diversity measure; it does not transfer an ecological
population model to media. [Hill (1973)](https://esajournals.onlinelibrary.wiley.com/doi/10.2307/1934352)

For sensitivity only, assume equal marginal variance, common nonnegative
within-parent correlation rho and zero between-parent covariance. Directly
expanding the variance of the mean gives:

```
Var(mean) = variance_per_unit * [N + rho*(sum(n_g²)-N)] / N²
design_effect = 1 + rho*(N/P - 1)
N_eff = N / design_effect
```

Report rho = 0, .01, .05, .10 and 1 as scenarios, never fitted estimates. Unequal
cluster sizes and within-cluster correlation matter for information, as shown
in cluster-sampling research; media ownership does not itself identify an ICC.
Cross-parent syndication, common events and serial dependence can violate the
zero-between-parent assumption. [Eldridge, Ashby & Kerry (2006)](https://pubmed.ncbi.nlm.nih.gov/16943232/)

For unknown parents, retain logical bounds: merge all unresolved source-month
mass with the largest confirmed parent for the lower P bound; treat unresolved
source-month blocks as distinct for the upper bound. This assumes one parent
per block and evidenced distinctness among confirmed groups. These are
conditional mapping bounds, not confidence intervals. The current empirical
run has no verified historical publisher mapping in its selected tables, so
it reports bounds and separately labels source-ID concentration as a proxy.

## Replace a fixed minimum with explicit precision scenarios

For planning a **future binary proportion**, the maximum Wilson half-width at
nominal 95% confidence occurs at p-hat=.5. Write z=1.959964 and:

```
h(N_eff) = z / [2*sqrt(N_eff + z²)]
A = e / (e + h)
```

For N=0, A=0 and h is unknown. With fractional effective N this is a sensitivity
surrogate, not an actual binomial interval. A=.5 means h equals the selected
margin e; it is not a pass threshold. Wilson avoids some problems of the
ordinary Wald interval, but neither interval repairs a nonprobability source
sample. [Brown, Cai & DasGupta (2001)](https://doi.org/10.1214/ss/1009213286),
[NIST formula and implementation documentation](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/propconf.htm)

| Nominal 95% planning margin | Independent-N reference, rounded up |
|---|---:|
| ±10 percentage points | 93 |
| ±7.5 percentage points | 167 |
| ±5 percentage points | 381 |

These values solve the stated Wilson benchmark; they are **not new monthly
minimums, required source counts, representativeness claims or acquisition
stops**. Different outcomes, rare events, continuous affect scores, dependence,
annotation error and comparisons require different designs. For N=2 the
worst-case half-width is about .405 even under independence.

Example: 1,000 texts from one parent at rho=.05 give N_eff≈19.63; 1,000 equally
distributed across ten independent parents give N_eff≈168.07. For fixed P and
rho>0, N_eff approaches P/rho as N grows. Increasing one archive indefinitely
can therefore fail to reach a chosen precision scenario. This is an algebraic
sensitivity result, not an estimate of this corpus's effective sample size.

## Distribution without flattening real peaks

Show pooled monthly and yearly counts first. Then compare source composition
using equal-mixture Jensen–Shannon divergence with log base 2; it is 0 for
identical distributions and 1 for disjoint support. It describes a change in
collection mix, not an error. [Lin (1991)](https://doi.org/10.1109/18.61115)

For each month, inspect the preceding and following three months. Construct a
fixed panel of sources positively observed in the target and **every available
nonempty neighbor**; require at least two such neighbors. Calculate the panel's
target count per calendar day x and the median neighboring rate b. Then:

```
D = (x-b)/(x+b)
J(rho,e) = D * A(N_eff(panel, parent mapping, rho), e)
```

Sort the two mapping endpoints of J so negative contrasts still have ordered
bounds. Keep a real event peak positive; never cap or downsample it. New-source
appearance is visible in pooled counts/JS and panel share rather than silently
attributed to within-source growth. This positive-presence panel selects
persistent observed sources and is not a population estimator. Missing cells
are not zero expression. Calendar-day normalization is only a descriptive
exposure convention; it does not prove full archive capture. September 2026
has 21 in-scope calendar days and incomplete forward context, with no assertion
of end-of-day completeness. Irregular publication schedules remain a limitation.

J and A are **new project constructions**, not validated scores from the cited
papers. A monotone bounded scale improves display but does not supply empirical
calibration. Avoid an arbitrary weighted average of counts, diversity and
distribution. Preserve the component vector and scenario range.

## Validation and future evidence

Current validation covers algebra, independent Wilson implementation, 41 edge
and regression tests, 20 seeded beta-binomial variance simulations and 6,975
monthly scenario rows from three closed stream/snapshot combinations. It tests
behavior under a model; it does not prove archive completeness or classify
2026 records as erroneous.

The next empirical calibration should freeze independently adjudicated
source-month cases: verified date/identity errors, genuine peaks, source
appearance, archive horizon limits and unresolved cases. Keep unresolved cases
out of truth labels. Use source/parent-held-out and forward-time partitions;
do not split versions of one work across partitions. Compare the components
against simple count-only and source-mix baselines; report precision/recall and
false flags on known valid peaks only once adequate reviewed cases exist.
Bootstrap parents or time blocks after defining the estimand, rather than
treating every text as independent. No performance numbers are claimed now.

Problem-specific validation is central to text-as-data work; selection and
platform/pipeline bias cannot be solved by size alone.
[Grimmer & Stewart (2013)](https://doi.org/10.1093/pan/mps028),
[Olteanu et al. (2019)](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2019.00013/full)

Chao–Jost sample coverage standardizes biodiversity samples by an explicit
completeness concept. Its random-sampling assumptions do not justify inferring
an unseen media universe from purposively collected API/archive returns; do
not apply singleton/doubleton extrapolation or its stopping suggestions here.
[Chao & Jost (2012)](https://pubmed.ncbi.nlm.nih.gov/23431585/)

MeCCO is a useful later external comparison because its documented design
considers geography, circulation and reliable archive access. Its climate-query
series differs from our currently broad acquired source frame. Match title,
region, publication interval, unit, retrieval definition and topic stage before
comparing; do not force our total-text distribution to match its counts. No
MeCCO curve-fitting or climate filtering was performed.
[MeCCO methodology, issue 106, p.9](https://mecco.colorado.edu/summaries/issue106.pdf)

## Annual-share and dominant-channel sensitivity

Report 2026's full-corpus share and its share within the recent decade
separately. For an equal calendar window, compare January–August in each year
2016–2026. Do not compare eight/full historical months with partial September
2026 or assume that modern platform activity should be constant across years.
An observed recent-year concentration can arise from real growth, historical
retrievability, source mixture, crawler depth, repeated observations or date
errors. Shares alone cannot identify which explanation applies.

The closed social main-phase snapshot has a 29.60% full-corpus 2026 share, but
**64.77%** within the matched January–August 2016–2026 window (117,224 of 180,989
bodies). The common-source panel across those 11 years contains OSM Discourse,
Earth Science Stack Exchange and Sustainability Stack Exchange. It accounts
for only 1,019 of those 117,224 bodies in 2026, or **0.87%**. This is too narrow
to explain the overall peak. Positive observations in every year do not prove
complete capture, source independence or representativeness. The newspaper
nine-hour input has no common positive source across this entire comparison.

Add an explicitly optional **observed-mass sensitivity view**. Let p_y be the
observed annual share and p_g|y the within-year share of one declared group
dimension. Use:

```
q_y(alpha) = p_y^(1-alpha) / sum_y p_y^(1-alpha)
q_g|y(beta) = p_g|y^(1-beta) / sum_g p_g|y^(1-beta)
w_yg = q_y * q_g|y / p_yg
```

This is a proposed comparison operator. It is **not an estimated sampling
weight, an expected growth curve or population-bias correction**. Alpha=0 and
beta=0 reproduce the original; alpha=.25 is a gentle year scenario; alpha=.5
and/or beta=.5 are moderate sensitivity scenarios. Alpha=beta=1 equalizes only
observed years/groups as an extreme stress test. It is not the preferred
distribution. Missing years/parents receive no invented records. All original
records retain positive weight and are unchanged on disk.

In the full available social snapshot, the year-only .25/.5 scenarios give
2026 weighted shares of 21.76%/14.43%; within the recent January–August frame,
they give 49.87%/33.49%. These lower shares occur **by construction** and are
not evidence of improved data quality. Inspect whether a later validated
substantive result survives these comparisons; do not celebrate the smaller
share or use it as a next-round target. Source-only weighting deliberately
leaves annual shares unchanged, so year and source effects can be separated.

Weights have observed mean one and can exceed one; they are not bounded quality
scores. Output their minimum/maximum, bounded annual/joint total-variation
shift, and weight-only effective-N = (sum_i w_i)^2/sum_i w_i². The latter is
not adjusted for parent/time dependence and must not replace the separate ICC
scenarios. Large weights and tiny observed strata expose instability; this
implementation does not silently trim them or treat weighting as new evidence.

Actual calibration needs credible auxiliary population totals and suitable
selection/outcome assumptions. These are not currently established for the
media pool. If verified source-year inventories or comparable external totals
later become available, version those denominators and evaluate calibration
against held-out evidence. [Deville & Särndal (1992)](https://doi.org/10.1080/01621459.1992.10475217)

Apply group sensitivity separately to verified publisher/operator groups,
source IDs, threads, native entity types or explicitly declared automation
markers. Do not mix all dimensions into one parent label. The current run uses
source IDs because its selected inputs lack these other row-level mappings;
it does **not** claim to have identified bots, noise prevalence or emotional
feedback classes. Neutral, routine or strongly expressed content is not noise
merely because of its sentiment or volume. Shared software and technical
community membership are not automation evidence.

For future validated outcome summaries, add leave-one-parent/thread/type-out
analysis views and show the signed change in the normalized outcome, [-1,1],
beside the original estimate. Mark large changes as dependence on that group,
not proof it is wrong. Run this only after defining and validating the outcome;
there is no affect/fear model to test here yet. Repeat with confirmed work
deduplication versus retained-native-unit views while preserving originals.
Genuine highly engaged threads remain evidence, with their dependence visible.
