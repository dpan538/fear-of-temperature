# Australian source options and processing budget

**Later decision, 12 October 2026:** Dai selects **100 GB as the primary peak Australian envelope**. The 50 GB preference below is retained as a previous planning scenario, not the current recommendation. See the [current source/rebuild report](../2026-10-12-australia-source-freeze/README.md) for the latest source evidence, PM interface limitations and archive/rebuild direction. The numerical assumptions and sensitivity results in this earlier report remain unchanged.

The preferred design is a **50 GB peak working-data envelope** for the Australian study, with a separately assessed **100 GB alternative**. Dai confirms that this includes new source data, derived text, passages, vectors, indexes, caches, outputs and temporary files. Previous international holdings remain preserved outside this envelope and serve only as methodological reference. The budget is a ceiling, not a volume target. It does not reactivate an expired collection window.

Use existing Australian data and suitable ready corpora first. Add only sources needed for a declared comparison. The fixed publication interval remains **1988-01-01 through 2026-09-21**; actual source and analysis windows can be narrower. The scope is based on Australian institutions, media and evidenced Australian communities, rather than inferred residence for every author. Attribution, analysis and comparison remain the objectives.

## Recommended source route

| Frame | First choice | Evidence and preparation issue |
|---|---|---|
| Parliamentary text | UQ RAPID-CDL analytical corpus | Four Parquet tables contain text, dates, speakers and procedural context, approximately **502.4 MB** deposited. Metadata-footer checks identify **6,911,269 paragraphs** and session dates **1996-05-30–2026-09-08**. It is an available Australian institutional corpus, with narrower observed bounds than the fixed study interval. [Deposit](https://zenodo.org/records/22868754). |
| Executive text | PM Transcripts | Official full-content XML and a URL index offer a practical route for a selected period. Historical OCR and original PDFs need proportionate checks. [Official developer interface](https://pmtranscripts.pmc.gov.au/developers). |
| News and public/community text | Existing accepted Australian stock | Reuse **8,169 regular articles** and, separately, **45,679 dated community-context bodies** as candidate pools. Their source/time distribution, local/federated origin and unit relationships remain explicit. |
| Necessary mainstream supplement | One verified library/provider or original route | ProQuest is subscription based and local full-text mining/export rights are not established by reading access. Trove's Canberra Times offers a possible **1988–1995** historical case, with OCR and source-use checks. Neither is an automatic replacement for the modern source frame. |

The parliamentary deposit is not seven million independent government speeches. A paragraph is a procedural text segment; government, opposition, independent members, questions, petitions and quoted material require dated speaker/role attribution. The current export has party validity but no ministerial-office field. Its CC BY-NC-ND 4.0 terms require attention to reuse and public redistribution of transformed text. Assess local research use and the intended derivative outputs against the actual terms; do not presume an open full-text redistribution grant.

The existing media/community records overlap concretely in **June 2024–September 2026**, dominated by a Northern Rivers Times/community comparison. This is a plausible initial Australian case, conditional on usable government evidence, rather than a nationally representative 1988–2026 three-role time series. Wider periods require their own source evidence. Detailed options and conditions are in [government sources](GOVERNMENT_SOURCES.md) and [news and public sources](NEWS_PUBLIC_SOURCES.md).

## AntConc before bulk vectors

AntConc provides concordances with keyword-in-context display, file views, word frequencies, collocates and target/reference keyword comparisons. These can help inspect wording and its original context on a small source/time subset before a costly embedding run. [Official AntConc page](https://www.laurenceanthony.net/software/antconc/).

Use whole native texts with stable document keys and date/source metadata in the initial AntConc subset. Keep role, source and period separate and compare normalized frequencies under a documented reference. Preserve original URLs, text/version hashes and passage locations in a sidecar. Lexical patterns nominate material for interpretation; negativity, keyness or the occurrence of a fear word does not establish fear prevalence or causal influence. AntConc is an analysis tool, not a substitute for provenance checks or a source-inclusion classifier.

The official help reviewed gives no demonstrated 50/100 GB operating limit. Keep the initial AntConc database bounded and benchmark its build, query speed and temporary footprint. The detailed workflow and the distinction between software licensing and text rights are in [ANTCONC_WORKFLOW.md](ANTCONC_WORKFLOW.md). No installation or app/model execution is part of this research result.

## Peak storage envelopes

All GB values below are decimal. These are proposed component reservations, not measured file sizes or collector quotas. Models and results are retained components. Temporary writes and uncommitted budget headroom are counted within the peak envelope; the filesystem's existing **15 GiB safety floor is additional**.

| Component | Preferred 50 GB | Alternative 100 GB |
|---|---:|---:|
| Original packages and source evidence | 10 | 20 |
| Canonical text and source metadata | 4 | 8 |
| Passages and original-text lineage | 6 | 14 |
| One vector representation and optional index | 8 | 20 |
| AntConc subset database | 2 | 4 |
| Model cache, quality logs and research outputs | 4 | 6 |
| Temporary writes and budget headroom | 16 | 28 |
| **Peak envelope** | **50** | **100** |

Component shares can be reallocated after the benchmark while the total peak limit remains fixed. Reusing saved Australian records requires a newly declared Australian view; the earlier international pooled sample is not an empirical input to the new comparisons. Referenced original Australian evidence remains accounted for as source material, even when a manifest avoids physically duplicating the protected store.

An entire RAPID paragraph table should not automatically be resegmented or embedded. Its native boundaries and the intended analysis may make some derived copies unnecessary. Preserve full source material, then declare the analysis-stage source/time and relevance frame. Budget pressure is not a reason to delete protected evidence, truncate required context, flatten peaks or reinterpret a small corpus as representative.

## Passage scenarios and the assumptions behind them

Dense vector bytes equal **passage count × dimensions × bytes per value**. A 384-dimensional float32 vector is 1,536 bytes; a 1024-dimensional float32 vector is 4,096 bytes. The dimensions are confirmed by the respective model cards, but neither model is selected solely by this comparison. [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3).

The following scenarios assume 1,500 text bytes plus 400 lineage bytes per passage, 5 GB fixed retained material, and, where present, one optional index reserving an additional dense payload plus 128 bytes per entry. Temporary peak reserves the larger of 2 GB or half the variable outputs. These are explicit conservative planning choices, not observed averages, compressed Parquet-to-text factors or measured index sizes.

| Scenario | Dense vectors alone | Retained data | Peak with temporary files |
|---|---:|---:|---:|
| 100,000 passages, 384 dimensions, no index | 0.154 GB | 5.344 GB | 7.344 GB |
| 500,000 passages, 384 dimensions, one index | 0.768 GB | 7.55 GB | 9.55 GB |
| 1 million passages, 384 dimensions, one index | 1.536 GB | 10.10 GB | **12.65 GB** |
| 1 million passages, 1024 dimensions, one index | 4.096 GB | 15.22 GB | **20.33 GB** |
| 3 million passages, 384 dimensions, one index | 4.608 GB | 20.30 GB | 27.95 GB |
| Every RAPID paragraph treated as one 384-dimensional unit | 10.616 GB | 40.247 GB | 57.871 GB |
| Every RAPID paragraph treated as one 1024-dimensional unit | 28.309 GB | 75.633 GB | 110.950 GB |

The last two are stress cases before date/role/relevance analysis selection. They omit media/community additions and any extra long-paragraph splitting or title vectors. They illustrate why even a 100 GB limit does not make an indiscriminate full-vector pipeline manageable. The 100,000/500,000/1 million cases are hypothetical workloads, not target source counts, statistical sample sizes or rules for dropping records.

The [calculator](estimate_processing_budget.py), [assumption file](BUDGET_ASSUMPTIONS.json) and [results](BUDGET_RESULTS.json) reproduce every estimate. Replace assumed passage sizes, multiplicity and index/temp factors with a bounded source-aware measurement before execution. The existing encoder returns a complete float32 matrix; incremental input, saved shards, manifests and restart semantics still need implementation for larger production work.

### Current local capacity

A read-only `df -k .` check on 12 October returned **35.24 GB available**. Preserving the existing **15 GiB** floor leaves approximately **19.13 GB for a new peak** at that snapshot. The 50/100 GB envelopes therefore require additional available storage to use fully. A bounded 7–13 GB first-run design is more compatible with current space, subject to a fresh complete-operation check and other concurrent writes. This is disk capacity, not RAM, GPU capacity or processing speed. The hardware memory probe was unavailable; no hardware throughput is asserted.

Do not delete or relocate protected historical data to make the plan fit. Extra storage is a separate deployment choice. Keep source stores, raw/version evidence and inherited cumulative counters unchanged.

## Work and machine time

For the ready-data/reuse route, allow **72–148 active researcher hours** for an initial bounded, interpretable RQ1/RQ2 analysis. At an assumed eight hours per working day this is **9–18.5 working days**, approximately **2–4 working weeks**. This is a planning judgement for a first analysis, not completion of the thesis, a validated national fear measure or the later prototype. It excludes access delays, unexpected historical recovery, extended annotation validation and machine time.

At **20 researcher hours per week**, the same labour estimate becomes approximately **4–8 calendar weeks**; at ten hours per week it becomes approximately **8–15 weeks**. These conversions show why staff effort, available study time and machine runtime should remain separate.

| Work package | Researcher-hour assumption |
|---|---:|
| Source, licence and coverage feasibility | 8–16 |
| Australian view, joins and date/source lineage | 8–16 |
| Named structural checks and dated role mapping | 16–32 |
| AntConc subset and documented comparison recipe | 8–20 |
| Passage/model benchmark preparation and evaluation | 8–16 |
| Initial RQ1/RQ2 analysis and original-passage checks | 24–48 |

If the project instead needs new extraction across several Australian routes, use a provisional **4–8 working weeks** to the comparable first-analysis stage. Older OCR recovery or institutional/provider permission waits are unbounded until the relevant access check resolves. Source-specific feasibility estimates are in the companion notes. The recommended route reuses the existing stock and one ready corpus before committing to custom collection.

For one million passages, assumed sustained rates of 1, 10 and 50 passages/second give **347.2, 34.7 and 6.9 machine hours** respectively after an explicit 25% planning overhead. These are sensitivity calculations, not measured rates or promises. They exclude external queue delays, annotation passes, index reconstruction and long-text effects beyond the assumed throughput. A small actual-device benchmark must determine the applicable rate. Two weeks of labour and two days of machine runtime are different quantities and should not be added without considering possible overlap.

The previous confirmed stage dates are not rewritten by this planning estimate. Its next concrete step is a bounded ready-corpus/source feasibility and AntConc-oriented trial, followed by a passage/embedding benchmark only in the analysis stage. No broad acquisition, account application, paid licence, migration or full corpus/model run has been launched.
