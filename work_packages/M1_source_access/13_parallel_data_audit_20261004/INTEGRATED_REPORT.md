# Integrated corpus preparation review

4 October 2026 · Three parallel GPT-6 Sol / Extra High tasks

**The audits are complete; the next useful work is bounded structural repair, not another global collection or semantic screening round.** The publication interval remains 1 January 1988–21 September 2026, with September partial. Formal databases, raw sources, shared collection code and the proposal were not changed by these audits or this integration.

The recorded pooled government source-text presence remains 465/465 months as a historical result; this integration did not recalculate that union. It does not establish media/public coverage or topical relevance. Climate, emotion and fear validation remain later analysis tasks.

## Reconciled inventory

| Frame | Observed inventory | Interpretation |
|---|---:|---|
| UK government | 248,035 parents | Independent stored parent identities; cross-source equivalence still needs bounded review |
| Selected US Federal Register | 33,544 parents; 18,590 saved content versions | Metadata frame and saved-version inventory, not 33,544 readable bodies |
| Selected EU preparatory documents | 50,578 Works; 19,114 staged Item versions | Work and Item units differ; extracted status alone does not verify usable text |
| AU current catalogue | 821 candidate landing URLs | 819 lack a verified day-level original date in the main candidate frame; small overlapping original subsets are separate |
| Guardian December 2015 | 396 candidate URLs; 4 documented body checks | Four across both pilots, corrected from the quality worker's one-check inventory |
| Archived petition keyword query | 177 submitted IDs; 77 published, 100 rejected | A bounded civic query frame; not the whole public or a full monthly denominator |

The UK/US-AU/EU database modification checkpoints are respectively 22 September 13:37 UTC, 27 September 12:36 UTC and 27 September 15:31 UTC; they are file checkpoint proxies, not a synchronized transaction. Source-quality exports are earlier. No combined grand total is asserted. See the [correction and checkpoint addendum](COORDINATOR_CORRECTIONS.md).

## 1. Endpoint and date integrity

The audited UK, selected US and EU dates contain **no observed records outside the fixed publication interval**. However, 119 GOV.UK stored source-local calendar dates differ from their UTC timestamp dates by one day; **three cross a month boundary**. These are alternative date conventions, not proven incorrect publication dates. The coordinator recommends preserving both original local publication date and normalized UTC timestamp, explicitly choosing the monthly convention before changing derivatives. No dates were rewritten.

The 938-row date exception ledger consists of those 119 differences and 819 AU unresolved day-level dates. AU CMS creation time must not stand in for original publication. Proposed AU/EU guards should compare exact dates at the partial September boundary, rather than just the month. These are latent guard weaknesses; the audit did not demonstrate an out-of-scope stored UK/US/EU record.

## 2. Distribution and counting units

The distribution audit produced 7,442 rows across 16 source–genre frames: 465 months per frame plus two unknown-date rows. Its declared diagnostic rule flagged 85 source-months; 20 were reviewed with ordinary-period controls. A flag is a prioritization device, not a significance test or evidence of overcollection.

Object count is not parent count. The historic Hansard answer frame has 135,689 parents linked to 602 shared objects, while the DEFRA policy frame has 1,019 parents linked to 3,023 objects. One parliamentary container can carry many independent answers; one policy can have many attachments. PDF line/block extraction also produces far more segments than independent documents. Neither relationship alone warrants deduplication or deletion.

Several UK low months have calendar-consistent explanations; not every low is proven complete. The DEFRA April 2013 concentration, UK August 2024 answer dates, EU April 1988 date cluster and selected US 1994 frame need specific evidence checks if used. Source-local IDs and canonical URLs were unique, but **138 cross-source title/date candidate pairs involving 83 mirror parents remain candidates**, not confirmed duplicates. Legitimate publication peaks remain in the corpus.

## 3. Source quality

UK route rules classify 67,043 parents as original-utterance route candidates and 180,992 as archive/mirror reproductions. This is metadata-based route classification, not individual verification of every original. An archival reproduction may still preserve primary evidence. Original news and civic text are direct evidence of their own discourse; an official host does not automatically identify the author or prove all claims.

In the purposive 30-record/Work review, identity was supported for 22, date for 23 and content mapping for 18. Twelve had at least one partial/pending field. These overlapping counts describe the sample, not corpus-wide accuracy. Two UK parents have saved text inconsistent with old status labels; a DCCEEW-hosted report has CSIRO authorship; two Federal Register records share document number 95-24211 but have different dates, URLs and saved originals. Do not merge those US records solely on document number.

The Guardian frame correction is documented separately. The sample's own results remain unchanged. No substantive truth, climate relevance or emotion prevalence was assessed.

## Bounded next actions

Use [INTEGRATED_ACTIONS.csv](INTEGRATED_ACTIONS.csv), ordered high then medium then low. First align the date contract and state labels. Next resolve named identity/date exceptions, retaining unresolved states and all raw evidence. Supplement only an identified missing original or source mapping; do not restart national enumeration to flatten a histogram. These are recommendations; no repair or acquisition was executed here.

Only changed records and affected derivatives need one acceptance check. The helper and callsite patches from the cutoff worker remain proposals awaiting integration. No all-corpus rehash, re-import, broad semantic classification or new collection target is required by these findings.

## Evidence and verification limits

- [Cutoff audit](01_fixed_cutoff/REPORT.md), date exception ledger and proposed contract.
- [Distribution audit](02_distribution/REPORT.md), monthly counts, 20-case anomaly ledger and two diagnostic figures.
- [Source quality audit](03_source_quality/REPORT.md), 30-case evidence and 11-item source queue, read with the coordinator correction.

The coordinator checked the result files, checkpoint/count-unit compatibility, date-exception totals, distribution-ledger dimensions and four distinct Guardian body-check URLs against saved CSVs. No formal database query or live source request was repeated during integration. The distribution worker reports visual inspection and PDF font checks; automatic collision checking was unavailable because PyMuPDF was missing. It is not recorded as a full automatic figure-QA pass.
