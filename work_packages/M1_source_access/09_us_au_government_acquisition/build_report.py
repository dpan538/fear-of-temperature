"""Generate a concise, measured coverage and quality report from current ledgers."""
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from acquire import HERE, US_SOURCE, AU_SOURCE


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def main():
    rep = HERE / "reports"
    metrics = json.loads((rep / "quality_metrics.json").read_text())
    audit_path = rep / "integrity_audit.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    state_path = HERE / "checkpoints" / "supervisor_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"status": "manual_bounded_blocks"}
    objects = load_csv(rep / "object_status.csv")
    content = load_csv(rep / "content_status.csv")
    monthly = load_csv(rep / "monthly_progress.csv")
    text_parents = {r["document_id"] for r in content if r["status"] == "cleaned"}
    us = [r for r in objects if r["series"] == US_SOURCE]
    au = [r for r in objects if r["series"] == AU_SOURCE]
    au_year_only = sum(r["date_precision"] == "year" for r in au)
    au_outcome_path = rep / "au_candidate_outcomes.csv"
    au_outcomes = Counter(r["outcome"] for r in load_csv(au_outcome_path)) if au_outcome_path.exists() else Counter()
    au_web_pages = (au_outcomes["official_web_pdf_identified_raw_pending"]
                    + au_outcomes["official_web_landing_observed_raw_pending"])
    au_web_failures = au_outcomes["official_web_read_only_open_failed_raw_pending"]
    lines = []
    for name, lo, hi in [("1988–1993", 1988, 1993), ("1994–2002", 1994, 2002), ("2003–2026-09-21", 2003, 2026)]:
        selected = [r for r in us if lo <= int(r["date_value"][:4]) <= hi]
        lines.append((name, len(selected), sum(r["fetch_status"] == "downloaded" for r in selected),
                      sum(r["document_id"] in text_parents for r in selected)))
    known_months = 0
    usable_months = 0
    zero_months = 0
    unresolved = []
    for year in range(1988, 2027):
        for month in range(1, 13):
            ym = f"{year:04d}-{month:02d}"
            if ym > "2026-09": break
            r = [x for x in monthly if x["series"] == US_SOURCE and x["year_month"] == ym]
            if r and all(x["coverage_status"] in {"verified_zero_in_selected_series", "enumerated_and_usable"} for x in r):
                known_months += 1
                if any(int(x["n_usable_parents"] or 0) > 0 for x in r): usable_months += 1
                if all(x["coverage_status"] == "verified_zero_in_selected_series" for x in r): zero_months += 1
            else:
                unresolved.append(ym)
    max_gap = 0
    gap = 0
    for year in range(1988, 2027):
        for month in range(1, 13):
            ym = f"{year:04d}-{month:02d}"
            if ym > "2026-09": break
            gap = gap + 1 if ym in unresolved else 0
            max_gap = max(max_gap, gap)
    source_segments = metrics["source_segments"]
    clean_segments = metrics["cleaned_segments"]
    report = f"""# US/Australia government acquisition: coverage and data quality

Generated {datetime.now(timezone.utc).isoformat()} from ledger snapshot {metrics.get('generated_at_utc', 'earlier snapshot; rerun report.py')}. Study window **1988-01-01 to 2026-09-21**. US supervisor state: `{state['status']}`. This report reflects the last committed database reconciliation and hash-verified files; the selected US series is complete only if that state is `us_selected_series_complete` and the audit passes.

## Source-specific progress

| Source period | Enumerated unique US parents | Verified downloaded texts | Parents with cleaned text in DB | Interpretation |
|---|---:|---:|---:|---|
| 1988–1993 | unknown | 0 | 0 | FederalRegister.gov API route unsupported; GovInfo annual indexes and scanned issues exist, but agency/genre document denominator is not enumerated |
| 1994–2002 | {lines[1][1]:,} | {lines[1][2]:,} | {lines[1][3]:,} | Fixed EPA/DOE final/proposed-rule series; historically prioritised |
| 2003–2026-09-21 | {lines[2][1]:,} | {lines[2][2]:,} | {lines[2][3]:,} | Same selected US series; September 2026 is a partial calendar bin |

The 132 reconciled agency × genre × year partitions contain **33,560 stratum hits** and **33,544 unique canonical document URLs**. The 16 cross-agency hits remain one parent with two associations. These are administrative rule/proposed-rule Works, not a US climate-policy denominator. No climate keyword filter was applied. The database has {metrics['documents_by_series'].get(US_SOURCE, 0):,} US metadata parents, {metrics['versions_by_series'].get(US_SOURCE, 0):,} saved US content versions and {metrics['US_downloaded_verified']:,} locally hash-verified downloaded text files. Downloaded files awaiting insertion remain separately visible.

The Australian 83-page snapshot has **823 cards / 821 unique landing URL candidates**. All {metrics['documents_by_series'].get(AU_SOURCE, 0)} candidates are stored as catalogue records with CMS time separate from original issue date. Four earlier official landing/PDF pairs were reused, and {metrics.get('AU_browser_parent_works_with_files', 0)} further official landings have {metrics.get('AU_browser_original_file_versions_ingested', 0)} saved original/attachment versions. The working DB has {metrics['versions_by_series'].get(AU_SOURCE, 0)} AU content versions across these sources. {metrics.get('AU_precise_month_candidates', 0)} candidates have an evidenced issue month or day, {au_year_only} have only an issue year, and {metrics['AU_original_date_unknown']} still lack an original issue date. The browser-observed landing HTML is not claimed as a saved raw landing file. Catalogue candidates are not automatically distinct policy Works or exact-month observations. Ordinary direct requests to the current host failed; one tested predecessor-domain PDF route was reachable but has a separate, unenumerated population. Neither outcome is a zero month.

The per-candidate [Australian outcome ledger](au_candidate_outcomes.csv) records {au_web_pages} official landing pages observed through the read-only web route, including {au_outcomes['official_web_pdf_identified_raw_pending']} with a linked PDF URL. A further {au_web_failures} web-reader queries returned an error or no page. These page and URL observations are metadata evidence only; they add no downloaded body, verified original date, or independent Work. Original raw-file acquisition remains limited to the hash-verified versions above.

## Parent-based monthly acceptance

The [monthly ledger](monthly_progress.csv) gives source, jurisdiction, agency, genre, date basis, enumerated target, unique parent, text-available parent, usable parent, unassessed relevant-parent and segment counts for all 465 study months. For the selected US agency/genre series, {known_months} months currently have resolved usable-or-verified-zero acquisition states, {usable_months} have usable parent observations, and {zero_months} are verified zero across all four US strata. The longest unresolved run is {max_gap} months. These are **series-processing states**, not historical population coverage. The AU original-date monthly denominator is unknown; {metrics['AU_original_date_unknown']} undated candidates and {au_year_only} year-only originals cannot be assigned exact months. No country or genre fills another's missing observation.

The [49-bin event-window ledger](event_window_2015_paris_coverage.csv) uses the independently dated 12 December 2015 Paris Agreement adoption as a *coverage candidate*: 24 complete pre-event months, December 2015 separately, and 24 complete post-event months. It reports government-only source states; media and public roles have not been audited here. No RQ1 shared three-role window or RQ2 effect estimate is claimed. Relevance to warming/fear remains `not_yet_assessed` for every parent.

## Version, extraction and integrity

Only actual saved 2xx bytes that match SHA-256 create content versions. AU landing, primary PDF and alternative roles remain linked to one candidate parent; PDF files are not new parent documents. Source extraction and initial structural cleaning use separate runs, with raw bytes and clean-to-source mappings retained. The current DB contains {source_segments:,} source segments and {clean_segments:,} cleaned segments in this tranche; **neither count is an independent sample size**. US extraction v1 used printed lines for its first blocks; v2 stores one complete source-text segment per later document to control storage growth. The cleaned paragraphs retain source line-range locators. The source-specific rules remove Federal Register page boilerplate, repair broken line wraps/hyphens, and discard short fragments; they do not normalise sentiment or run models.

The [content-status manifest](content_status.csv) distinguishes downloaded/cleaned, no-text or OCR candidates and not-requested content objects. [Successful extractions](success_records.csv), [extraction/OCR exceptions](extraction_exceptions.csv), [pending records](pending_records.csv), [request failures](exceptions.csv) and [route exceptions](../route_exceptions.csv) are separate, machine-readable lists. Current targeted audit: UK baseline unchanged = `{audit.get('uk_baseline_unchanged', 'pending')}`; verified new version hashes = `{audit.get('verified_content_versions', 'pending')}`; hash mismatches = `{len(audit.get('hash_or_size_mismatches', [])) if audit else 'pending'}`; orphan segments = `{metrics['orphan_segments']}`; unmapped cleaned segments = `{audit.get('unmapped_new_clean_segments', 'pending')}`. Source language is presumed from the English official entrances and verified for retrieved texts; uncollected catalogue candidates are not represented as confirmed English bodies.

## Remaining work and use boundary

US body retrieval/insertion remains {33_544 - metrics['versions_by_series'].get(US_SOURCE, 0):,} parents short of the selected denominator. The 1988–1993 GovInfo annual indexes are an official finding aid, and their EPA/DOE rule and proposed-rule entries still need document-level enumeration and issue matching. AU needs original-date, publisher and primary-file review across the remaining catalogue candidates and a separately enumerated predecessor archive. The current DCCEEW direct-route failures and National Library access challenge are documented without bypass. Source-specific US and AU raw counts must not be summed into a single global policy time series. Project authorisation for collection is recorded separately from institutional ethics status; no UQ approval or exemption is asserted. Raw full text is held for internal research, with public redistribution unassessed.

See [filter contract](../FILTER_CONTRACT.md), [runbook](../RUNBOOK.md), [object status](object_status.csv), [monthly progress](monthly_progress.csv), [identity spot checks](identity_spot_checks.csv), [integrity audit](integrity_audit.json), and [Figure 5](figure_5_us_au_coverage.pdf). The UK 06 database is a frozen comparator; the US/AU working copy is the only write target for this tranche.
"""
    (rep / "coverage_data_quality_report.md").write_text(report)
    print(rep / "coverage_data_quality_report.md")


if __name__ == "__main__": main()
