# Fear of Temperature — Australian corpus aggregates, 2003–2025

This archive documents the composition and partitioning of
`formal-corpus-release-20261117-v1`. The aggregate companion is version `1.0.2`.
The project uses Australian public discourse to study descriptions of changing
temperatures, bodily experience and cultural learning.

## Corpus accounting

| Scope | Records | Definition |
| --- | ---: | --- |
| **Preserved acquisition holdings** | **890,024** | 801,559 historical identities plus 88,465 phase 32 identities, including holds |
| Historical snapshot plus active phase 32 records | 849,638 | 801,559 historical identities plus 48,079 active phase 32 identities |
| Active acquisition pool | 765,610 | 717,531 baseline records plus 48,079 active phase 32 additions |
| Materialized release | 723,158 | 717,531 baseline records plus 5,627 selected candidates |
| Structural holds within the materialized release | 4,828 | 4,825 baseline records plus three selected candidates |
| **Formal eligible corpus** | **718,330** | 712,706 retained baseline records plus 5,624 promoted texts |
| Frozen v1 training (`ml_train`) | 646,414 | 90.0% of the eligible corpus |
| Frozen v1 validation (`ml_validation`) | 36,110 | 5.0% of the eligible corpus |
| Frozen v1 test (`ml_test`) | 35,806 | 5.0% of the eligible corpus |

The formal partition targets 90:5:5. Content groups are assigned together, and
the development-reviewed groups stay in training. The exact shares are 89.9884%,
5.0269% and 4.9846%.

The release database retains all 4,828 structural holds in `quarantine_records`
with original body locators. Its 723,158 records represent **722,160 distinct
native bodies**, based on stored SHA-256. The held subset contributes **4,826**
distinct bodies, all absent from the formal subset. The frozen model views
exclude structural holds. The research workflow also holds **732** formal
records whose original body hashes appear in the historical source-use archive.
These 714 matching hashes affect 663 train, 42 validation and 27 test records.
Notebook 13 applies these holds, its remaining model-input holds and exact-text
canonicalization to obtain **641,180** eligible training documents. Its
development cohort contains **20,000** documents.

The historical snapshot and phase 32 appendix are disjoint by native identity.
The cross-snapshot metadata check also found zero matches on stored body SHA,
document ID or exact nonempty source URL. Counts use native identities and may
include near copies or distinct versions. The 88,465 phase 32 receipts include
40,386 appendix holds. The 849,638 subtotal retains the historical holds. The
47,280 records between the active pool and eligible
release comprise 4,825 baseline structural holds and 42,455 active appendix
records outside formal eligibility. The release fell **1,670** below the later
target range of **720,000–750,000** total eligible records.

The 13 November historical acquisition closeout counted **801,559** records
under its original rules. Its frozen partition had **721,793 training**,
**39,990 validation** and **39,776 test** records. The eligibility audit carried
forward 717,531 candidate records after 16,805 topic holds, 67,222 recorded
source-use holds and one access-provenance hold. The 17 November version then
added 5,627 selected records and assigned 4,828 materialized records to
structural review. The historical snapshot and its splits remain available in
the research workspace. [Historical closeout](https://github.com/dpan538/fear-of-temperature/blob/main/docs/research/2026-11-13-corpus-release/README.md)

The formal corpus has 716,529 distinct cleaned-body hashes. The 1,801 additional
exact-body copies retain separate provenance and share a split with their matched
record. Split counts are document counts for the 17 November content-group
partition. The release verification reported zero known cross-split group,
exact-body or qualifying reused-paragraph conflicts. Model fitting and supervised
emotion annotation are outside this release.

## Proposed training design

The successor design targets **about 720,000 training records**. An exact
90:5:5 allocation at that training count requires **800,000 eligible records**,
including **40,000 validation** and **40,000 test** records. The active pool of
765,610 falls short by at least **34,390**, even before further eligibility and
group-disjointness checks. A successor design requires a new versioned partition.
The v1 counts refer to its frozen views.

## File inventory

| File | Unit and fields |
| --- | --- |
| `release_counts.csv` | One row per named measure, with its count, unit and supporting evidence file |
| `split_counts.csv` | Records and distinct content groups within each split and cohort. A group spanning cohorts can contribute to both cohort counts. |
| `year_by_stage.csv` | Eligible record counts by year and cohort. `Unknown` preserves the 43 records without a single assigned publication year. |
| `family_by_stage.csv` | Eligible record counts by native record family and cohort |
| `corpus_accounting.png`, `publication_coverage.png` | Summary graphics for the repository README |
| `render_figures.py` | Matplotlib source for the two graphics |
| `restore_frozen_catalog.py` | Verifies frozen inputs and rebinds a copy of the catalog after a restricted bundle is relocated |
| `RESTORATION_VERIFICATION.json` | Read-only input hashes, relocated-view counts and exact native-body counts from the restoration check |
| `MODEL_INPUT_COUNTS.json` | Frozen split sizes, source-use body-overlap holds and the downstream document-level development frame |
| `FORMAL_RELEASE_REPORT.json`, `POST_COMMIT_VERIFICATION.json` | Release receipt and read-only post-commit verification |
| `METADATA_COUNTS.json` | Historical eligibility counts, phase 32 metadata reconciliation and verified cross-snapshot holdings |
| `zenodo_metadata.json` | Draft deposit fields. Set the approved aggregate licence and deposit date in the repository form. |
| `LICENSE` | MIT terms for the project-authored plotting software and associated documentation |
| `SHA256SUMS` | Digest of each payload file in the packaged archive. Verify with `shasum -a 256 -c SHA256SUMS` after extraction. |

Cohort values `baseline` and `supplement` describe membership provenance. The
annual counts describe publication coverage. Emotion measurement requires
validated labels and modelling.

Regenerate the graphics with Python 3.12 and Matplotlib from the project
environment. The script reads the companion CSV files beside it.

```bash
python render_figures.py
```

## Integrity and restricted restoration

The source catalog digest and the membership digest identify the frozen v1
snapshot. The relocation check validated the 150 materialized Parquet parts
against the materialization receipts and replayed the formal, quarantine and
split counts from a separate directory using DuckDB 1.5.5.

With authorized access to the full private bundle, keep the source layout
(`release_v1/` and `supplement_selection_v1/`) intact. This command creates a
separate, relocated catalog with the same frozen membership.

```bash
python restore_frozen_catalog.py /path/to/private-bundle /path/to/restored.duckdb
```

The check establishes file integrity and reproducibility of the catalog counts.
Source-specific access, reuse and research permissions apply separately.

## Data availability

The aggregate companion contains corpus accounting, coverage tables, figures and
release verification. It contains zero source texts and zero record-level
rows. The formal full-text corpus, native captures and provenance records are
retained in the research workspace. The local release uses a DuckDB catalog
and its linked Parquet files. Contact the maintainer privately to discuss a
specific reuse proposal. Any access depends on source-specific permissions,
privacy review and applicable institutional requirements.

## Deposit and citation

The aggregate companion is prepared for a Zenodo Dataset record. Review the
aggregate licence, creator information and deposit fields, then reserve the DOI
in the Zenodo draft. After publication and verification of the record, cite the
registered **version DOI** for these exact files and link it from the repository.
A future software DOI would cite a tagged software release.
[Zenodo DOI reservation](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/) · [GitHub software archiving](https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content)

The provisional aggregate citation is Pan, D. *Fear of Temperature — Australian
corpus aggregates, 2003–2025*, version 1.0.2. The underlying corpus version is
`formal-corpus-release-20261117-v1`. [Project repository](https://github.com/dpan538/fear-of-temperature)

For software citation, use the repository's `CITATION.cff` and the exact Git
commit. The MIT terms cover project-authored software and associated
documentation. Full-text access and any future text deposit have separate
source-specific rights and privacy requirements.
