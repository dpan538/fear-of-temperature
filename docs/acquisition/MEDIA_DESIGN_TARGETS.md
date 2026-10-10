# Media source-frame and historical support targets

Version 1, 10 October 2026. This extends the descriptive diagnostic package with
an inverse design calculator. It replaces the earlier implication that a set of
diagnostic scores, more bodies or removal of the two-work predicate alone
constitutes the requested coverage/source repair.

## Required outputs and meaning of adequate

The direct source-development objectives are **at least 50 newspaper titles**
and **more than 20 distinct forum communities**. They are scope requirements,
not quantities inferred from the current biased collection. The current frame
has 14 contributing newspaper title IDs. The social frame has 25 source IDs,
but provisional structural classification identifies only 9 named forum-like
community candidates; feeds, list archives and federated instance collectors do
not automatically count as forums. Community identity, parent/operator
independence and historical validity still require evidence.

The calculator must answer four different questions:

1. Which title/community categories and historical intervals are absent from
   the intended frame, and which accessible inventories can resolve them?
2. How many effective independent groups are needed for a stated analytical
   precision and tolerated group influence at a finite amount of data?
3. Given a source mixture, is more text sufficient, or does the stated scenario
   require more independent groups? How large is the explicit gap?
4. Which requirements are met, unmet or unidentified? An unknown inventory,
   unverified parent or unspecified measurement cannot become a passed score.

The script is [media_design_targets.py](../../src/fear_temperature/media_design_targets.py).
The [closed-data run](../../work_packages/M1_source_access/32_media_design_targets_20261010/README.md)
includes requirements, source-class proposals and 8,370 month/scenario rows.
These are a planning interface for concrete collection work. No collector
imports the calculator or uses its values to discard bodies or stop writing.
The auxiliary parent monitor remains independent of runtime scheduling.

## Source taxonomy and counting contract

Use separate fields rather than one source-quality rank:

| Dimension | Newspaper | Social/public expression |
|---|---|---|
| Identity | Original title, edition, continuity/renaming | Community, native platform/instance and migration |
| Independent relation | Publisher/editorial operator, dated owner relation | Community operator, platform operator; neither is the author |
| Primary source purpose | National general, regional/local general, specialist/business, advocacy | General discussion, local/civic, household/consumer, travel/transport, outdoor/culture, technical/scientific |
| Unit/channel | Complete article; print reproduction distinct from born-digital | Root post, reply, quotation/repost wrapper; forum, feed and list distinct |
| Historical support | Publication era, observed archive era, issue inventory | Foundation/operating era, recoverable threads/posts, migration/archive coverage |
| Acquisition selection | Issue/index, archive search, retrospective reproduction | Chronological/category inventory, activity feed, actor selection, popularity-ranked index |
| Evidence | Original vs reproduction; identity/date/boundary verified or pending | Same provenance dimensions; native context and unresolved identities retained |

The general newspaper research frame needs conventional general-interest
national/regional/local titles. Specialist and advocacy newspapers remain
retained and separately reported; they cannot silently substitute for all
general-interest historical coverage. A campus title is not counted back into
the newspaper target. For social, public lists and technical communities remain
retained, but their abundance cannot establish coverage of civic/daily-life or
general forum expression. Technical purpose is a source-frame description, not
a verdict that each message is noise.

Category labels in the first CSV are proposed from existing source identities,
not corpus-wide semantic labels or externally validated classifications.
`regional_local_general` deliberately leaves finer geographic reach unresolved.
A full source registry must add primary evidence and time validity before this
taxonomy can certify a selected frame. Unknown categories appear in the gap
list. Do not infer author location from server or opportunity stratum.

There is no evidence-based universal rule that each category must have the same
number of sources. Declare which category/era contrasts will actually be made,
then run their own group/amount requirements. Do not demand every country ×
genre × month cell be complete, or assign invented population category shares.
A future category-specific comparison with insufficient support remains
unavailable even if the pooled panel meets a requirement.

## Inverse calculation: how many sources and how much text

Let N be countable bodies in one declared time cell and n_g group counts under
one verified parent dimension. P = N²/sum(n_g²) is the effective group count.
Source-ID inputs only provide a labelled proxy. Historical parent uncertainty,
syndication and shared-platform dependence can reduce independent support.

For a future binary proportion, obtain n* from the worst-case Wilson half-width
at nominal 95%: 93, 167 and 381 independent observations for margins of 10, 7.5
and 5 percentage points, respectively. Under equal marginal variance, common
within-group correlation rho and zero between-group covariance:

```
N_eff = N / [1 - rho + rho*N/P]
P_required(N) = rho*N / [N/n* - 1 + rho], if N >= n*
N_required(P) = ceil[n* (1-rho) / (1 - rho*n*/P)], if P > rho*n*
```

The implementation separately handles rho=0, rho=1, no data and impossible
finite-N cases. Rho values .01, .05 and .10 are assumptions, not fitted ICCs.
Unknown rho must not be replaced by zero just to make a requirement pass.
Unequal cluster sizes and dependence are recognized sample-design problems;
the displayed inversion is our derivation under the stated model, not a media
quality standard from a paper.
[Eldridge et al. (2006)](https://pubmed.ncbi.nlm.nih.gov/16943232/),
[NIST Wilson documentation](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/propconf.htm).

| Planned bodies in a cell | Nominal planning margin | Assumed rho | Necessary effective group support, rounded up |
|---:|---:|---:|---:|
| 500 | ±10 percentage points | .05–.10 | 6–12 |
| 500 | ±7.5 percentage points | .05–.10 | 13–24 |
| 500 | ±5 percentage points | .05–.10 | 69–122 |

The first working comparison is the middle scenario, alongside the other
margins and 250/1,000-body alternatives. This is an explicit proposed design
tolerance, not a claim that 500/month or 13–24 sources is universally adequate,
and not an acquisition minimum/cap. Each future estimand requires validation;
Wilson scenarios do not establish actual confidence coverage for purposively
collected discourse, continuous affect scores or lead/lag models.

This makes an important decision actionable: if the current P is below the
finite-N feasibility boundary, adding unlimited text with the same mixture
cannot meet the scenario. The plan must expand independent support for that
era or revise the intended resolution/inference. It must not replace missing
older periods with large recent batches or silently aggregate away gaps.

## Influence tolerance is a design choice with a mathematical consequence

For a fixed-weight mean of an outcome bounded in [0,1], removing group g and
renormalizing changes the mean by at most its original share p_g. Thus a chosen
worst-case leave-one-group tolerance of .10 requires every group share <=.10,
and necessarily at least 10 groups. A .05 tolerance necessarily requires at
least 20. Counts alone do not satisfy the share condition. The bound does not
apply to arbitrary correlations, regressions or nonlinear trend statistics.

These are tolerances on the proposed analytical view, not raw-data retention
caps or evidence that a real high-volume group is erroneous. Keep raw and
explicitly defined source/genre panel estimates alongside each other. Unknown
population totals mean any balanced view is a selected estimand, not a
calibrated estimate of all public discourse.

With no deletions, reducing the largest raw group to share epsilon requires at
least max(0, n_max/epsilon - N) additional non-leading bodies. At epsilon=.10,
the current social source-ID proxy requires at least **5,213,395** more bodies
outside the largest group, even under optimistic availability assumptions.
This is not a recommended collection target. It demonstrates why collecting
millions more records merely to dilute a dominant archive is the wrong repair.

## Coverage goals and normalized coefficients

Replace the single `coverage >= 2` flag with explicit requirements per declared
frame and time cell:

- **Frame breadth:** the user-defined title/forum objectives, verified identity
  and the declared categories; report actual and missing source/era entries.
- **Historical archive recovery:** loaded eligible native IDs / enumerated
  eligible native IDs, with the inventory scope, pagination and pending reasons.
  Unknown denominator remains unknown. Old `processed` is not completion.
- **Amount attainment:** min(1, N_eff/n*), under each stated scenario.
- **Group attainment:** min(1, P/P_required(N)); zero if even independent N is
  insufficient. Always show the actual needed effective groups.
- **Influence attainment:** min(1, epsilon/max(p_g)), for the stated bounded-mean
  view. Keep the same relation dimension and unknown-mapping mass explicit.

The last three coefficients lie in [0,1]. One means only that the named
scenario requirement is met. They cannot compensate for one another through a
weighted average. `quality_certified` is false until the missing empirical
requirements are evaluated; `scenario_met` remains available as a separate,
auditable conditional result. Fifty nominal sources or a million texts cannot
make unverified categories, unknown archive recovery or unsupported time cells
pass by arithmetic.

## Temporal distribution and source classification must be evaluated together

The final social total has 17.62% dated bodies in 2026. In the matched
January–August 2016–2026 comparison, 2026 still supplies **129,858/212,090 =
61.23%**, versus **117,224/181,050 = 64.75%** before the round (including its
capacity append). The calendar is matched, not the source mixture. A falling
full-history fraction largely driven by 2004–2012 technical mail cannot certify
repair of the recent-period composition.

Compute source/parent × year × source-purpose views, then same-source or
explicitly standardized comparisons where sufficient support exists. Mark
unmatched-source mass and missing eras. Recover dated inventory and pagination
evidence for genuine concentration checks; no uniform year distribution,
replacement noise threshold, semantic exclusion or automatic deletion follows.

## What would establish adequacy beyond this first calculator

1. Verify the prospective frame: original title/community identity, genre,
   time-valid parent relations and source existence/retrievability separately.
2. Reconcile the declared historical native inventories and legacy queue state.
3. Define the actual outcome and time resolution; estimate dependence using a
   separately validated design. Replace scenario-only rho where defensible.
4. Check stability across source/parent/time-held-out subsets and leave-one-
   parent/community/class analyses of that outcome. Keep selection mechanisms
   and external frame comparisons visible.

The current code provides concrete conditional source/amount gaps now, rather
than pretending these later validations are already complete. The corresponding
source development and snapshot recovery plan is local and does not renew the
expired collection release.

Source selection needs more than numerical diversity. MeCCO documents
geography, circulation and reliable historical archive access as design
considerations; this supports recording those dimensions, not borrowing its
counts or treating its climate-query population as ours.
[MeCCO methodology](https://mecco.colorado.edu/about/index.html).
Social-data selection and processing biases need explicit treatment and are
not resolved by larger volume.
[Olteanu et al. (2019)](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2019.00013/full).
