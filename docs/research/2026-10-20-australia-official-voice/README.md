# Australian official voice: metadata and core excerpts

**Closed by user, 21 October 2026:** Official Voice acquisition has ended. The available-route
snapshot below remains frozen; eight pending routes remain disclosed and are not an automatic
follow-up queue. `all_sources_complete=false` is unchanged. Dai selects approximately
**2003–2024/2025** for subsequent dense Australian Social Media and Personal Discourse collection,
with **1988–2002** as historical/background reference. The exact endpoint awaits Dai's instructions
in a new window. Preserve the full official **1988-01-01–2026-09-21** inventory and all earlier evidence.
See [current state](CURRENT_STATE.json), [selected scope and evidence](CLOSEOUT_SCOPE_DECISION.json)
and the [closeout log](../../PROJECT_LOG.md#21-october--close-official-voice-and-select-the-next-public-expression-window).
The scope choice does not establish exponential growth, statistical power, causal exogeneity,
complete platform coverage or guaranteed event matches. No new acquisition is launched.

**Completed available-route snapshot, 21 October2026 01:27:17AEST:**9public routes
traversed to their actual ends;42,006retained native metadata records,41,689inside the fixed
interval. Baseline26=3,676; Extended33=41,689; the matrices are overlapping, not additive.
UQ ends at a null token after6,086pages/608,570OAI observations. There are91/15zero-observed
pooled months respectively. Eight named routes remain pending, so
`all_available_sources_complete=true` and `all_sources_complete=false`. The formal new JSONL
export remains withheld under the requested completion condition; the prior frozen export
is preserved. See [delivery counts](DELIVERY_SUMMARY.json), [current dashboard](distribution_review_20261021/dashboard.html),
[pooled missing months](distribution_review_20261021/pooled_missing_months.csv),
[pending routes](distribution_review_20261021/pending_sources.csv) and
[Extended33 annual phase CSV](distribution_review_20261021/extended33_annual_phases.csv).
The current corrected display files are `event_alignment_final_20261021` and
`terminology_groups_final_20261021` (PNG/PDF/SVG); earlier previews are superseded.

20 October 2026 replacement of the retired v7/event-led pipeline. The publication reference
interval remains **1988-01-01–2026-09-21**, with September 2026 partial. The two research tables
are `source_documents` and `event_claims`. This is a source-led, query-defined inventory, not a
complete national discourse series or a validated research calendar.

## Data contract

- [SQLite acquisition schema](schema.sqlite.sql), [PostgreSQL schema](schema.postgresql.sql),
  [document JSON Schema](source_documents.schema.json) and [claim JSON Schema](event_claims.schema.json)
  implement the requested two-table design.
- Save metadata, native/parent IDs, date precision/status, source links, retrieval time and one
  excerpt of at most **500 Unicode characters** per record. Full HTML/PDF/source bodies are
  not retained. Source text may be streamed in memory to identify the excerpt. Operational
  page receipts keep request parameters, response hashes, counts and continuation state only.
- `publication_date` is nullable for coarse/unknown dates. Separate lower/upper date bounds
  describe the source's precision; month/year records are not assigned an invented first day.
  Date-pending and out-of-interval raw candidates remain labelled, outside the in-interval export.
  UQ's January-01 dates are conservatively treated as potentially year-only until confirmed.
  The previously evidenced RAPID session-date/URL conflicts (2146 and 4891) remain pending,
  retain their supplied dates, and are excluded from monthly date claims until resolved.
- All matching terms/dimensions are JSON arrays; repeated query matches do not add documents.
  Source-qualified native IDs yield SHA-256 `doc_id` values. Known version/context links persist.
  A provider search hit without a locally observed phrase remains explicitly unconfirmed.
- Parliament contains multiple speaker/holder roles. UQ research authorship and repository
  membership do not establish an institutional position. A CSIRO/QLD dataset catalogue is not
  a government article or a public statement; native units/counts stay separate.
- `event_claims` starts empty. Claims default to `draft`, require an evidence excerpt and locator,
  and cannot become `verified` without a reviewer/time. Publication dates do not become physical
  event dates. Different claims about one event can share `event_group_id`; they remain claims,
  not independent event counts. No v7 case or illustrative user JSON is imported as real data.

## Five modules and verified routes

| Module | Actual route and current scope | Limits / pending items |
|---|---|---|
| 1. Parliament | [UQ RAPID-CDL federal export](https://zenodo.org/records/22868754), frozen 2026-09-21; all 57 paragraph-file row groups, joined to checksum-verified session/speaker/debate tables | 3,300 sittings, nominal 1996–2026, documented gaps; not 1988–2026 continuous coverage. Matching paragraphs are consolidated into session-qualified native procedural records, not counted as independent speeches. Original ParlInfo links and matched paragraph IDs persist. Full paragraph-file checksum is not claimed: checked byte ranges and row-group receipts are used. |
| 1. State parliament | [NSW official Hansard API](https://www.parliament.nsw.gov.au/parliamentary-business/hansard/hansard-api), [API contract](https://parliament-api-docs.readthedocs.io/en/latest/new-south-wales/) | Official description says September 1991 onward; year index and table of contents returned 200, a fragment returned 403. No whole-period/no-digitisation-gap claim. CheckHansard is a third-party republication, not an established public bulk API. |
| 2. Meteorology/science | [CSIRO DAP documented public ws/v2](https://research.csiro.au/dap/developer-tools/web-services-ws-v2/), [official harvesting guidance](https://research.csiro.au/dap/developer-tools/harvesting-metadata/) | Metadata collection descriptions, not a full report/news corpus. `psd`/`ped` filter collection publication dates; all returned next links are traversed. BoM has a public [SCS index](https://www.bom.gov.au/climate/current/statements/), but a documented historical text-search API has not been established. CSIRO's publications repository request returned 403; not silently replaced by DAP as equivalent text. |
| 3. National archives | [Trove v3](https://trove.nla.gov.au/about/create-something/using-api) | Live request returned 401 without a key. At Dai's instruction this module stays pending credentials. No account creation, private-interface fallback or full-text permission is inferred. Gazette/catalogue historical coverage is title-specific. |
| 4. Universities | [UQ eSpace OAI-PMH](https://espace.library.uq.edu.au/v2/oai?verb=Identify), `oai_dc`, all resumption tokens | Public Identify/ListMetadataFormats/ListRecords returned 200. OAI datestamps describe updates, not publication; harvest and filter the separate `dc:date`. `earliestDatestamp=2001` is not the earliest publication year. Other universities remain unconfigured, not exhausted or included by assertion. |
| 5. Queensland/local | [QLD CKAN public API](https://www.data.qld.gov.au/api/3/action/package_search), [government documentation](https://www.data.qld.gov.au/article/standards-and-guidance/publishing-guides-standards) | Catalogue rows, not underlying resource rows or warning bulletins. Follow offsets until returned count is reconciled. Unknown publication dates stay pending; metadata-created/modified times are not substituted. [SLQ open datasets](https://www.slq.qld.gov.au/get-involved/open-data/open-datasets-released-state-library) use this portal; One Search does not establish an unrestricted bulk API. |

Five modules are not five uniform APIs, and the current public routes cannot substantiate the
supplied assertion of gap-free 1988–2026 coverage. International sources are not added to the
Australian empirical frame. No fear/emotion filter, model or production warehouse is involved.

## Query and count rules

[The unchanged Baseline](query_matrix.json) contains Dai's original 26 phrases. Dai subsequently
confirms [Extended33](query_matrix_extended.json): the union of those 26 and seven additional
phrases (`heat wave`, `extreme temperature event`, `global warming`, `greenhouse effect`,
`greenhouse gas`, `climate change`, `extreme weather`). The four dimensions remain recorded;
no baseline phrase is deleted or replaced. Matching is case-insensitive, with whitespace/hyphen
and final-word plural variants (including `gas/gases`); no score selects records.

Reports show Baseline26, Extended33 union and Extended-only unique IDs separately, including
source/month counts. Baseline is a subset of Extended, so the two totals must not be added.
The [first baseline prefix checkpoint](BASELINE_CHECKPOINT.json) is historical and incomplete.
Because full originals were not retained, the expanded matrix requires replay of that prefix
in memory; native IDs prevent duplicate rows. Frozen Hansard comparisons use the same deposit.
Live repository records can change between retrievals, and in-progress observed unions are not
claimed to be a fixed simultaneous snapshot. Broader climate/emissions/weather matches are not
automatically verified warming statements or physical events.

There is no total row/page cap: page size 100 is a transport setting, never a 100-record stop.
OAI uses resumption tokens; CKAN reconciles offset and reported count; DAP follows next links;
the frozen Hansard file traverses every row group. Empty premature pages, repeated continuation
tokens, malformed responses and unavailable access pause with incomplete status.

`audit` emits all465 month bins and warns for zero-observed months. The21October directive removes **all numerical threshold checks/flags**, including the preceding15,000/10,000 warning checks. Counts never stop collection. CKAN now requests the actual terminal empty page; OAI/DAP follow null tokens/next links; Hansard ends after57/57 row groups. `exhaustion_status` and `page_traversal_complete` report each route. Blocked access, malformed/repeated responses and physical failures remain incomplete rather than false exhaustion. `all_sources_complete` is computed across the named registry, never hard-coded true. Formal JSONL export is withheld while the user-requested all-sources-complete condition is unmet; clearly labelled distribution reviews can still show observed inventory and pending routes.

Zero bins are re-counted against saved native records. Complete scans provide source-frame checks; native monthly requery can remain unavailable for OAI publication dates or blocked routes. Zero is not validated absence. Native item/catalogue/procedural units, pending dates and year-only dates remain separate. Annual counts include in-interval year-precision records; monthly counts do not assign them to January.

The21October expansion adds `bom_scs` (all eight public index fragments, linked SCS revisions consolidated by number), `bom_annual` (all300 paths generated by the public annual index controls/legacy list, with real404s recorded), `qld_resources` (all204 saved catalogue resource links classified; structured/spatial rows are not utterances), and `qld_statements` (all33queries across all13 government terms, following every actual next page; the default current-government limitation is explicitly avoided). BoM publication headers/time fields and Queensland `NewsArticle.datePublished` are distinct from report/event years and catalogue updates. Original HTML/PDF/OCR exists transiently in memory; only metadata/core excerpts persist.

The proposed Trove `official-record?q=` URL is a JavaScript shell, not a verified RSS/OpenSearch feed. The actual public Gazette route is `search/advanced/category/newspapers` with `keyword.phrase`, `l-artType=gazette`, `date.from=1988-01-01`, `date.to=2026-09-21` and actual next links (`startPos`). Its33queries are traversed in the public browser and saved as compact DOM-ID receipts. `trove_web_gazette` reads the publicly linked article HTML to obtain title/date/publisher and OCR excerpts. Search receipts hash compact DOM IDs, not original page HTML; article receipts hash the actual transient responses. A live-page repeated ID is counted once, with an independent date-sort recheck. This is an archival Gazette article frame, not every official publication or verified institutional stance. Its API remains separately pending credentials. AustLII's DFAT page and the SLSA-linked SA Gazette endpoint return403; DFAT treaties are not relabelled as gazettes.

## Run and storage

From the repository root, use its existing `.venv`. The21October figure QA adds PyMuPDF and its declared dependencies through the existing uv environment:

```sh
.venv/bin/python docs/research/2026-10-20-australia-official-voice/collect.py collect --source uq_espace
.venv/bin/python docs/research/2026-10-20-australia-official-voice/collect.py collect --source hansard_federal_rapid
.venv/bin/python docs/research/2026-10-20-australia-official-voice/collect.py collect --source csiro_dap
.venv/bin/python docs/research/2026-10-20-australia-official-voice/collect.py collect --source qld_opendata
.venv/bin/python docs/research/2026-10-20-australia-official-voice/collect.py collect --source trove
.venv/bin/python docs/research/2026-10-20-australia-official-voice/collect.py audit
.venv/bin/python docs/research/2026-10-20-australia-official-voice/collect.py export
```

Output is local under `work_packages/official_voice_20261020/`, including `official_voice.sqlite`,
`STATUS.json`, `monthly_counts.csv`, `monthly_module_counts.csv`, `monthly_matrix_counts.csv`
and `zero_month_rechecks.json`. Independent source workers
share transactional, native-ID-idempotent writes. A saved continuation resumes the same job;
running the same exhausted frozen/source snapshot does not re-download it. A future fresh
snapshot needs an explicit version/update strategy, not deletion of checkpoints.

Counts within one report use one SQLite read snapshot, and report files are replaced atomically.
The JSONL export writes `EXPORT_MANIFEST.json` with its own row/matrix counts and SHA-256.
The live `STATUS.json` may be newer than that export; compare an export with its manifest.

Dai removed the **15 GiB fixed free-space floor for this official-voice task**. The collector
checks actual response/transaction space and pauses if the next operation cannot fit. No
50–100 MB storage claim is assumed: actual SQLite/index/receipt/export usage is measured.

The [retirement catalog](RETIREMENT.json) maps former v7 and earlier paths to recoverable
historical evidence outside the active pipeline. No unique-copy purge or compressed package
was performed, and historical materials do not supply new collection results.

## Distribution review and figure revisions, 21 October

The [local dashboard](distribution_review_20261021/dashboard.html) links all figures, CSVs,
date evidence, missing-month lists and route states from one SQLite read snapshot. The
16-panel annual grid and monthly grid use independent Y axes (`sharey=False`, recorded
`free_y=True`), with measured per-panel limits. The six-group density heatmap uses
`log10(count+1)` and separately displays Baseline26/Extended33 on one color scale. Its
footnote identifies the searched Trove Gazette titles' archival taper/end by2012 and the
21September2026 cutoff. QLD groups include catalogue and release units; the source CSV
retains their distinction.

`extended33_annual_phases.csv` contains39 annual totals with Dai's three supplied phase
labels. These are user-specified period labels, not empirically established growth,
peak or normalization conclusions. The source-tier donut includes a separate federal
executive/Gazette tier: it does not misclassify those notices as Parliament. Unresolved
issuers remain labelled.

At Dai's latest readability correction, the current terminology figure is
`terminology_groups_v3`: four curves in one panel, with an explicit `log10(count+1)`
vertical scale and tick labels expressed in counts. Contrasting colors, line styles
and markers keep the small blue Policy Response series visible. This replaces the
stacked-area/detail-panel layout as the active display; previous rendered versions
are historical previews. A record matching k dimensions contributes1/k to each;
`annual_terminology_fractional.csv` reconciles exactly with annual unique-ID totals,
while `annual_terminology_multihit.csv` retains overlapping unweighted category hits.
No values are inflated to make a category visually larger or statistically significant.

`event_alignment_v3` moves the legend above the dual-axis plot, clear of its X-axis
title. It compares the current Extended33 annual inventory with the **preserved**
v7 reference CSV only:77 temperature-case starts and13 warming-report releases, each
counted once in its start/release year. `event_reference_lineage.csv` retains every
reference ID/date/type/link; a SHA-256 check confirms the frozen input is unchanged.
The old collectors and claims are not reinstated or imported. The90 rows remain a
non-exhaustive external inventory. Visual alignment cannot validate a Research Calendar,
estimate event incidence or establish causal relationships. New filenames prevent stale
previews from being mistaken for the corrected figures.

The automated validation suite checks native-ID uniqueness, every aggregated month/year
cell, Baseline-subset membership, fixed interval and terminology allocation. Middle-year
zeros are flagged in `middle_year_zero_checks.csv`, with source pagination status. QLD
releases2012 now contains24 Extended33 records (5 Baseline26); its earlier empty year was
an incomplete-scan artefact. The Hansard session lookup is independently checksum-verified
in `HANSARD_SOURCE_COVERAGE.json`;1997 is absent from the source itself.

`resolve_qld_dates.py` traverses **all** public activity pages for each of72 QLD catalogue
objects through an empty response. A retained `new package` activity must identify the
same object as public and active before it supplies a catalogue first-publication date.
Because these activity timestamps have no timezone, the date uses conservative month/year
precision. This resolves47 catalogue records;25 without retained creation evidence remain
pending. Neither catalogue metadata_created/modified nor report reference years are
substituted for publication. Prior pending metadata and the evidence are preserved.

Reproduce the figures and their rendered font/collision checks with:

```sh
MPLBACKEND=Agg MPLCONFIGDIR=work_packages/official_voice_20261020/mpl_cache .venv/bin/python docs/research/2026-10-20-australia-official-voice/report_distribution.py
.venv/bin/python docs/research/2026-10-20-australia-official-voice/verify_figures.py
```
