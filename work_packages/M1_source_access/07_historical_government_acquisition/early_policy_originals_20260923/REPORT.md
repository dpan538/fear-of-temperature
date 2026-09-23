# Early policy catalogue and original-publication recovery

**Status (23 September 2026): partial discovery, no new original acquired.** This is a bounded continuation of the approved 1988–2009 predecessor-policy recovery, not a claim that those years have been completely enumerated. The formal 06 database was read-only in this tranche. No proposal, modern records, ministerial collection, cleaning, vectors or models were changed.

## Result and before/after

| Publication period | Stored policy records before | After | Research exact-month view* | New complete originals |
|---|---:|---:|---:|---:|
| 1988–1994 | 3 | 3 | 3 | 0 |
| 1995–2000 | 7 | 7 | 7 | 0 |
| 2001–2009 | 80 | 80 | 83 | 0 |

\* The research view reassigns **three already-held PDFs** to independently verified original publication months; it is not three newly acquired documents. Two other previously reviewed originals have year-only dates and are not forced into a month. The [264-month table](policy_month_before_after.csv) preserves stored before/after counts, the research view and named-gap states separately.

The database remains at **248,035 documents, 1,055 policy-source records and 3,668,275 text segments**. The database size and modification time were identical before and after the read-only reconciliation. The [machine-readable check](reconciliation.json) confirms every 1988–2009 stored monthly policy count against the preceding report. There were **0 formal writes, 0 new documents and 0 new segments**; no acquisition attempt is counted as an ingested record.

## Catalogue findings, original versus alternative

The [target register](catalogue_target_register.csv) has **ten named missing in-scope or scope-review policy candidates**: five prior command-paper seeds and five further titles identified in this tranche (Cm 2429, Cm 3040, the 1997 second climate report, Cm 3587 and Cm 4548). These are a *known-target floor*, not the 1988–2009 population denominator. The 1991 Forestry Commission standalone statement is tracked separately because its issuing-body scope still needs a decision. The already-held 1993 DTI *Prospects for Coal* (Cm 2235) and 2005 *Securing the Future* (Cm 6467) were identity-checked and not reimported.

- [UK Parliament's Command Papers guidance](https://www.parliament.uk/about/how/publications/government/) says that the series mixes White/Green Papers with treaties, inquiry reports, statistics and annual reports. It also directs pre-2005 copy requests to The National Archives and identifies digitised 1833–2015 numbered papers via subscription ProQuest at libraries/TNA. Command numbers alone cannot be treated as a policy denominator.
- The [NBS publication index](https://www.thenbs.com/PublicationIndex/documents/details?DocId=258404&Pub=PARL_PUBS) supports title/ISBN identification for several candidates, but its specialist index and subscriber download do not establish full public text or a complete approved-department universe. The [source-route register](source_route_register.csv) documents each route's time/genre scope and limitation.
- [Hansard confirms the public launch of the 1997 climate report on 18 February](https://hansard.parliament.uk/Commons/1997-02-17/debates/618a7fd6-0654-4dfb-a8f9-313f9d0d5d9d/WrittenAnswers). The [UNFCCC indexed file](https://unfccc.int/sites/default/files/resource/uknc2%2520United%2520Kingdom.pdf) renders as an 81-page PDF in search, but the direct request returned HTTP 200 **`text/html`** (an access page), not PDF bytes. It was not saved, hashed or ingested. UNFCCC's receipt date, 13 February, is not silently substituted for the Hansard publication date.
- A later [official 2007 air-quality strategy](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/69336/pb12654-air-quality-strategy-vol1-070712.pdf) cites the earlier March 1997 Cm 3587 and January 2000 Cm 4548. Those are new identity leads, **not** recovered earlier editions; the 2007 original already in the database cannot fill either earlier policy slot.
- The direct official Forestry Research annual-report URL returned **HTTP 403** at `2026-09-23T01:42:05Z`. Its indexed appendix appears to reproduce the 1991 statement, but access and departmental eligibility both remain unresolved. No repeated 403 attempt was made. The earlier Cm 4913 UK Government Web Archive WAF result and restricted Internet Archive scans were likewise not retried or bypassed.

The [acquisition/exception ledger](acquisition_and_exception_ledger.csv) distinguishes catalogue evidence, access failure, existing identity and actual original acquisition for every inspected item. Bibliographic previews, parliamentary quotations, a 17-page summary of Cm 2427, a later 2007 strategy and an unverified third-party Cm 4913 transcript were **not** used as substitutes for complete originals.

## Coverage interpretation and next concrete route

The ten named candidates make particular publication months known gaps, while other months retain an unknown predecessor-department denominator. A zero database count does **not** mean no policy was published. Nor do the 31 all-series-empty months define the policy search: Cm 1200 is a documented missing policy in September 1990, a month with seven written answers. No title was assigned an invented day; month-only and year-only evidence retain their precision.

The next lawful recovery step is the [exact-title library/TNA request list](library_request_list.csv), with command numbers, ISBNs, known extents, edition cautions and identified physical holdings. In particular, seek the 80-page Cm 2427 rather than its shorter UNFCCC summary, and the 209-page Cm 4913 from [Redbridge/Havering holdings](https://libraries.newham.gov.uk/manifestations/69DC044957C3442E9D384C5DF4E074%3A626935). No request was sent on Dai's behalf; no subscription, login or access control was bypassed. If copies become available, verify title page, publication date, issuer, extent and edition, then hash and incrementally insert only genuinely absent complete originals under stable IDs.

The early-policy series remains **partial/denominator-unknown**. The [period CSV](policy_period_before_after.csv) and monthly CSV are record distributions; they are not historical-government coverage rates. The existing Figure 5 evidence-state design and monthly stacked chart remain valid numerically because no document/date mapping changed in this tranche; this report adds the newly identified policy-gap labels without presenting a new plot as if coverage had improved.
