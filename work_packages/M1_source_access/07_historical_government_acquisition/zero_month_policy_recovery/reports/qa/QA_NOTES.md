# Figure QA notes

Checked on 2026-09-23 after the final report refresh.

## Figures

- `monthly_government_records_research_date_landscape`: 18 × 10 inch English-only landscape figure; PNG is 5400 × 3000 pixels at 300 dpi. All 465 months are retained. The plotted exact-month total is 248,033 because two reviewed policy originals have year-only research dates and are deliberately withheld from month assignment.
- `05_government_corpus_coverage_over_time_updated`: 13.5 × 8.4 inch English-only landscape figure. Monthly and quarterly panels preserve blocked, unknown, unrequested, partial, complete and confirmed-zero evidence states separately.

## Automated checks

- Source parses successfully and is reported ready by the Nature Figure source validator: 17 pass, 4 non-blocking warnings, 0 fail.
- Panel-alignment gates pass: one comparison for the stacked chart and five comparisons for the coverage figure; 0 warn, 0 fail.
- Rendered collision audits pass for both PDFs: 0 warn, 0 fail.
- PDF text-floor audits pass at 5.5 pt: minimum 6.8 pt for the stacked chart and 7.2 pt for the coverage figure.

The source-validator warnings are expected for this requested deliverable: PNG rather than TIFF, 300 dpi rather than the skill's default 600 dpi, a deliberately wide landscape canvas rather than a journal-column width, and a false-positive uncertainty warning caused by words such as `mean`/`seed` in non-statistical code or data. These warnings do not indicate missing observations, statistical uncertainty, or a visual defect.

## Visual inspection

Both final PNGs were inspected at rendered size. Titles, legends, panel labels, date axes, footnotes and zero-month shading are legible; no overlaps or clipped labels were observed. The count figure and coverage-state figure remain visually and conceptually separate.
