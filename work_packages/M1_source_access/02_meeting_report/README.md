# M1 group-meeting report

## Deliverables

- `meeting_report.md` — English report source, based on `docs/meetings/2026-09-16/meeting_report_en.md` and checked against the latest proposal and saved M1.1 evidence.
- `meeting_report.html` — browser and print-ready English report.
- `meeting_report.pdf` — seven-page A4 English report generated with ReportLab and inspected page by page.
- `speaking_notes_en.md` — approximately five-minute English speaking script plus short answers for likely questions.
- `assets/technical_pipeline.svg` — planned technical workflow; it is explicitly labelled as a design, not a completed experiment.
- `assets/m1_verification.svg` — engineering figure using only saved M1.1 values.
- `scripts/build_pdf.py` — offline PDF builder; it reads `checks.json` to assert the saved values and makes no network requests.
- `scripts/render_pdf.swift` — macOS PDFKit renderer used for visual inspection.

## Evidence sources

1. Starting narrative: `docs/meetings/2026-09-16/meeting_report_en.md`.
2. Current design: `proposal/thesis_proposal.md` and the 21-page `proposal/thesis_proposal.pdf`.
3. Clarifications and next-week schedule: `docs/meetings/2026-09-16/research_narrative_zh.md`.
4. Saved M1.1 evidence: `work_packages/M1_source_access/01_feasibility/README.md`, `document_sample.csv`, `source_access_register.csv`, `denominator_assessment.md` and `checks.json`.

No network collection was performed for this report. The M1.1 collection script was not rerun, and no M1.1 output was changed.

## Rebuild

From the repository root:

```bash
/Users/jarlgiovanni/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  work_packages/M1_source_access/02_meeting_report/scripts/build_pdf.py
```

Render every PDF page for inspection:

```bash
swift -module-cache-path /tmp/m1_pdf_module_cache \
  work_packages/M1_source_access/02_meeting_report/scripts/render_pdf.swift \
  work_packages/M1_source_access/02_meeting_report/meeting_report.pdf \
  work_packages/M1_source_access/02_meeting_report/tmp/pdfs/rendered
```

## Validation

- PDF reopens as seven A4 pages and has extractable text.
- Every page was rendered to PNG and checked for font problems, overlap, clipping, chart legibility, table wrapping, headers, footers and page breaks.
- HTML structure, local asset links, seven print-page sections and print CSS were checked. The local-file browser preview was blocked by the browser URL policy; the exported seven-page PDF was therefore the artifact inspected visually page by page.
- Saved pilot values were checked against `checks.json`: 9 records, 9/9 access, pagination 5 + 4, zero missing/duplicate keys, three multi-organisation records and zero retained bodies.

## Interpretation limits

- NLP, CCF, VAR, ITS, BERTopic and the passage pilot are planned methods, not completed experiments.
- “Complete” refers only to the saved July 2026 GOV.UK `policy_paper` set tagged to DEFRA at that index time.
- Nine is a document-level denominator, not a passage denominator. There are no relevance or emotion labels, so S, E and B have not been estimated.
