"""Generate the source-specific US/AU/EU acceptance view from final ledgers.

Run after report.py, eu_disposition_ledger.py, eu_report.py and the final
integrity audits. This script does not open either acquisition database.
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from acquire import AU_SOURCE, HERE, US_SOURCE

EU = HERE.parent / "10_eu_cellar_acquisition"
EU_SOURCE = "eu_cellar_com_act_preparatory_eng"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def ym_window():
    center = 2015 * 12 + 11  # December 2015, zero-based month.
    for offset in range(-24, 25):
        year, month0 = divmod(center + offset, 12)
        yield offset, f"{year:04d}-{month0 + 1:02d}"


def source_rows(us_au_monthly, eu_monthly, dispositions):
    by_month = defaultdict(Counter)
    for row in dispositions:
        by_month[row["year_month"]][row["disposition"]] += 1
    result = []
    for row in us_au_monthly:
        result.append({
            "source_series": row["series"], "jurisdiction": row["jurisdiction"],
            "agency": row["agency"], "genre": row["genre"],
            "year_month": row["year_month"], "date_basis": row["date_basis"],
            "n_enumerated_targets": row["n_enumerated_targets"],
            "n_unique_parent_records": row["n_unique_parent_records"],
            "n_originals_in_db": row["in_db"],
            "n_text_available_parents": row["n_text_available_parents"],
            "n_ocr_candidate_parents": "", "n_usable_parents": row["n_usable_parents"],
            "n_relevant_usable_parents": row["n_relevant_usable_parents"],
            "n_segments": row["n_segments"], "coverage_status": row["coverage_status"],
            "reason": row["reason"]})
    for row in eu_monthly:
        month = row["year_month"]
        counts = by_month[month]
        enumerated = int(row["enumerated_works"])
        linked = int(row["works_with_english_item_link"])
        downloaded = sum(value for key, value in counts.items()
                         if key not in {"no_english_digital_item_link", "selected_item_not_requested",
                                        "selected_item_failed", "downloaded_checkpoint_byte_size_mismatch"})
        extracted = counts["source_text_extracted_relevance_unreviewed"]
        ocr = counts["ocr_candidate_layout_review"]
        placeholder = counts["source_html_table_placeholder_review"]
        if enumerated == 0:
            status = "verified_zero_in_frozen_class"
        elif downloaded < linked:
            status = "partial_original_acquisition"
        else:
            status = "item_link_route_processed_text_review_pending"
        result.append({
            "source_series": EU_SOURCE, "jurisdiction": "EU_supranational",
            "agency": "European_Commission_COM", "genre": "cdm:act_preparatory",
            "year_month": month, "date_basis": "cdm:work_date_document",
            "n_enumerated_targets": enumerated,
            "n_unique_parent_records": enumerated,
            "n_originals_in_db": row["staged_original_versions"],
            "n_text_available_parents": extracted,
            "n_ocr_candidate_parents": ocr,
            "n_usable_parents": "not_yet_validated",
            "n_relevant_usable_parents": "not_yet_assessed",
            "n_segments": int(row["staged_text_pages"]) + int(row["staged_structured_blocks"]),
            "coverage_status": status,
            "reason": (f"English Item links {linked}; no link {counts['no_english_digital_item_link']}; "
                       f"HTML table placeholders {placeholder}; frozen class only; "
                       "2026-09 capped at day 21")})
    return sorted(result, key=lambda row: (row["year_month"], row["source_series"],
                                             row["agency"], row["genre"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=HERE / "reports")
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    us_au = read_csv(HERE / "reports" / "monthly_progress.csv")
    eu = read_csv(EU / "reports" / "eu_monthly_status.csv")
    dispositions = read_csv(EU / "reports" / "eu_work_dispositions.csv")
    if len(eu) != 465 or len(dispositions) != 50_578:
        raise RuntimeError("EU monthly or Work ledger is not at its frozen target")
    monthly = source_rows(us_au, eu, dispositions)
    write_csv(out / "cross_source_monthly_coverage.csv", monthly)
    by_month = defaultdict(list)
    for row in monthly:
        by_month[row["year_month"]].append(row)
    event = []
    for offset, month in ym_window():
        for row in by_month[month]:
            event.append({"event_id": "paris_agreement_adoption_candidate",
                          "event_date": "2015-12-12", "relative_month": offset,
                          "bin_role": "pre" if offset < 0 else "event" if offset == 0 else "post",
                          "shared_role_availability": "government_only; media_and_public_not_audited_here",
                          **row})
    write_csv(out / "cross_source_event_window_2015_paris.csv", event)
    quality = json.loads((HERE / "reports" / "quality_metrics.json").read_text())
    eu_summary = json.loads((EU / "reports" / "eu_work_dispositions.summary.json").read_text())
    audit = json.loads((HERE / "reports" / "integrity_audit.json").read_text())
    eu_audit = json.loads((EU / "reports" / "work_enumeration_audit.json").read_text())
    au_outcomes = Counter(row["outcome"] for row in read_csv(HERE / "reports" / "au_candidate_outcomes.csv"))
    au_primary_urls = {row["url"] for row in read_csv(HERE / "reports" / "au_attachment_candidates.csv")
                       if row["role_status"] == "verified_primary"}
    au_body_parents = {row["document_id"] for row in read_csv(HERE / "reports" / "content_status.csv")
                       if row["series"] == AU_SOURCE and row["content_version_id"]
                       and row["canonical_url"] in au_primary_urls}
    c = eu_summary["status_counts"]
    eu_verified_originals = sum(c.get(status, 0) for status in (
        "source_text_extracted_relevance_unreviewed", "ocr_candidate_layout_review",
        "source_html_table_placeholder_review", "acquired_scan_ocr_pending",
        "acquired_extraction_pending_or_failed"))
    report = f"""# Cross-source government acquisition and coverage

Generated {datetime.now(timezone.utc).isoformat()}. Sources remain distinct. The study cutoff is 2026-09-21.

| Source | Frozen target | Parents with verified originals | Text/extraction status | Boundary |
|---|---:|---:|---|---|
| US Federal Register EPA/DOE final and proposed rules, 1994–cutoff | 33,544 canonical URLs | {quality['US_downloaded_verified']:,} | {quality['versions_by_series'].get(US_SOURCE, 0):,} versions in the 09 DB; relevance not assessed | The 1988–1993 print series has no verified article denominator |
| Australian DCCEEW current catalogue | 821 landing candidates | {len(au_body_parents)} candidate parents with verified primary files | {quality['versions_by_series'].get(AU_SOURCE, 0)} saved versions, including landings and attachments; most original dates unresolved | Catalogue candidates are not a verified monthly Work denominator |
| EU Commission COM `cdm:act_preparatory` with English Expression | 50,578 globally unique Works | {eu_verified_originals:,} Works with verified selected Item bytes | {c.get('source_text_extracted_relevance_unreviewed', 0):,} source texts; {c.get('ocr_candidate_layout_review', 0):,} OCR candidates need layout review | 3,106 Works lack a digital English Item link; adjacent proposal classes are outside scope |

The [source-specific monthly ledger](cross_source_monthly_coverage.csv) keeps US agency/genre strata, AU date uncertainty and the EU frozen class in separate rows. It never fills one jurisdiction's missing month with another's records. The [49-bin Paris event-window audit](cross_source_event_window_2015_paris.csv) has 24 complete pre-months, the event month, and 24 complete post-months for government sources only. Media and public coverage and warming/fear relevance remain unassessed.

Within the Australian primary-file count, {au_outcomes['browser_original_pair_verified_issuer_review']} candidate still needs issuer-scope review and {au_outcomes['browser_files_verified_date_pending']} has no verified original date. Landing summaries, appendix files and read-only PDF links do not increase that primary-file count.

The EU 2024-08 zero is only a zero for the frozen `act_preparatory` class. A bounded official CELLAR query found a COM proposal dated 2024-08-09 typed `proposal_decision_implementing_ec`; see the [EU runbook](../../10_eu_cellar_acquisition/RUNBOOK.md). The class scope is unchanged.

Integrity at the last recorded audit: UK baseline unchanged `{audit.get('uk_baseline_unchanged')}`, US/AU hash mismatches {len(audit.get('hash_or_size_mismatches', []))}, orphan segments {audit.get('orphan_segments')}; EU Work enumeration issues {eu_audit['issue_count']}. Check audit timestamps and rerun the source-specific audits on the final committed snapshot before treating these as final acceptance values. Originals, OCR candidates, formats and segments are separate from independent parent counts.
"""
    (out / "cross_source_coverage_report.md").write_text(report)
    print(json.dumps({"monthly_rows": len(monthly), "event_rows": len(event),
                      "us_originals": quality["US_downloaded_verified"],
                      "au_original_parents": len(au_body_parents),
                      "eu_works": eu_summary["unique_works"]}), flush=True)


if __name__ == "__main__":
    main()
