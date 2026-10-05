# Project EDA atlas — 27 September 2026

This atlas audits source acquisition and pilot readiness. It contains **eight distinct English figures**, each exported as 320 dpi PNG, PDF and editable-text SVG. The [contact sheet](figures/contact_sheet.png) is an overview. The figures are not a thesis result or an emotion time series.

| Figure | Main reading | Boundary |
|---|---|---|
| [01 — Inventory](figures/figure_01.png) ([PDF](figures/figure_01.pdf), [SVG](figures/figure_01.svg)) | UK has 248,035 dated parents with linked stored text; selected US has 17,930 of 33,544; EU has 15,299 readable Works of 50,578 enumerated; verified AU has five originals. | Parents, EU Works, Guardian URLs and petition IDs are different units. The stages are from source-specific checkpoints, not a synchronized census. |
| [02 — Monthly presence](figures/figure_02.png) ([PDF](figures/figure_02.pdf), [SVG](figures/figure_02.svg)) | The corrected pooled government ledger has stored text in all 465 study months after the 2015 EPA bridge. | Presence says nothing about climate relevance. Media and public rows are bounded pilots; public zero means zero inside the published `q=climate` frame. September 2026 is partial. |
| [03 — Annual volume](figures/figure_03.png) ([PDF](figures/figure_03.pdf), [SVG](figures/figure_03.svg)) | Written answers account for 98.5% of dated UK parents, dominating annual volume. | US selected parents and EU preparatory Works use their own log axis; source regimes and download depth differ. |
| [04 — Issuer footprint](figures/figure_04.png) ([PDF](figures/figure_04.pdf), [SVG](figures/figure_04.svg)) | UK contributes 434 unique government text months, EU adds 27, US adds four, verified AU adds none after those sources. | These are issuer/provenance scopes, not a map of populations or impacts. Guardian and petitions are UK-based pilots. |
| [05 — Text shape](figures/figure_05.png) ([PDF](figures/figure_05.pdf), [SVG](figures/figure_05.svg)) | UK policy parents are much longer than written answers; PDF layout blocks dominate segment counts. | UK character quantiles come from a historical quality snapshot; US EPA bridge quantiles cover 125 accepted parents. Segments are not independent documents. |
| [06 — Paris readiness](figures/figure_06.png) ([PDF](figures/figure_06.pdf), [SVG](figures/figure_06.svg)) | Government has stored text in 49/49 Paris months; Guardian and published-petition coverage remain narrower. | December Guardian has 396 candidate URLs and four body checks. Petition opened-at counts in the query frame are Nov 0, Dec 8, Jan 5. No comparable three-role monthly measure exists. |
| [07 — Manual label breadth](figures/figure_07.png) ([PDF](figures/figure_07.pdf), [SVG](figures/figure_07.svg)) | Among 48 deliberately selected review parents, 22 have a climate-topic label, six anticipated-harm, and zero explicit-fear. | The 23 government, four media and 21 petition records are a diagnostic sample. Public rows include published and rejected submissions; no population percentage is inferred. |
| [08 — Evidence topology](figures/figure_08.png) ([PDF](figures/figure_08.pdf), [SVG](figures/figure_08.svg)) | Three actual pilot parents retain source, parent, version/field and observed date/topic links. | Dashed speaker–target–responsibility/fear boxes are proposed review steps. No causal edge or copyrighted Guardian body is reproduced. |

## Counting and source methods

| Field or stage | Operational rule |
|---|---|
| Dated government unit | Distinct UK/US/AU document parent or EU preparatory Work with an original date. An EU Item version is not another Work. |
| Saved original | A linked content version or verified saved original. EU saved stage counts 15,455 Item versions linked one-to-one to Works at the 10:53 UTC checkpoint. |
| Stored/readable text | Nonempty source text linked to an independent parent. The older UK `body_status` gate missed saved text; the corrected source-text ledger is used for month presence. EU excludes 27 placeholder-only extractions from its 15,326 text-extracted Works, yielding 15,299 readable source-text Works at its 10:53 UTC checkpoint. |
| Government monthly coverage | Set union of source months, with the 125 committed EPA bridge originals included. A month is counted once even if multiple jurisdictions have text. No full-month climate review is implied. |
| Media pilot | Current Guardian archive candidate URLs and four checked current bodies are separate stages. Publication month uses original-published metadata; no climate/fear rate is computed. |
| Public pilot | The `q=climate` query has 177 distinct submitted IDs, 77 published with `opened_at`, and 100 rejected. The main month uses `opened_at` for published IDs; rejected/created records appear only in the diagnostic review. The all-published monthly denominator remains unavailable. |
| Manual labels | Climate topic, anticipated climate harm and explicit fear are separate parent-level review fields. Sampling is enriched/diagnostic, so counts are not prevalence estimates and fear is not a source gate. |

Source checkpoints differ: UK read-only database plus corrected 12:36 UTC source-text ledger; US 10:53 UTC pooled checkpoint plus 125 committed EPA bridge originals; EU/AU 10:53 UTC checkpoint; Paris round-2 14:16 UTC. The [data manifest](DATA_MANIFEST.json) records input paths, modification times and the atlas assembly time. Figure-specific CSVs are in [data](data/).

## Reproduce and QA

From the repository root, using the existing project virtual environment:

```bash
.venv/bin/python work_packages/M1_source_access/12_project_eda_snapshot_20260927/assemble_data.py
.venv/bin/python work_packages/M1_source_access/12_project_eda_snapshot_20260927/plot_atlas.py
```

`assemble_data.py` opens the static UK database read-only and reads frozen source reports/CSVs; it does not mutate acquisition data or make network requests. `plot_atlas.py 1` through `plot_atlas.py 8` can rerender individual figures. The [QA summary](qa/QA_SUMMARY.json) and per-figure PDF text/collision reports are saved under `qa/`. Final PNGs were visually inspected at intended landscape size. All eight have PNG/PDF/SVG, ≥300 dpi PNG, PDF text ≥5 pt and no detected clipping/collision. Multi-panel figures 03 and 04 passed the nature-figure alignment audit. Static source preflight passed with nonblocking journal-template warnings for TIFF, 600 dpi default, journal width and log guard; the requested deliverables use 320 dpi PNG at a 13.4-inch landscape size.
