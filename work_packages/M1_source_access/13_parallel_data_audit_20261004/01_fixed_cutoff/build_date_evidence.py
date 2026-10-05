"""Read only metadata audit; writes only beside this script.

Run from repository root with .venv/bin/python. It reads no body/segment tables,
does not hash source files, and treats the 09 UK tables as a copy of 06.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
M1 = ROOT / "work_packages/M1_source_access"
UK = M1 / "06_government_content_acquisition/fear_temperature_government_content.duckdb"
USAU = M1 / "09_us_au_government_acquisition/fear_temperature_us_au_v1.duckdb"
EU = M1 / "10_eu_cellar_acquisition/eu_stage.duckdb"
UK_MANIFEST = M1 / "04_government_corpus_batch/enumeration_manifest.csv"
UK_HIST_MANIFEST = M1 / "07_historical_government_acquisition/manifests/policy_manifest.csv"
AU_OUTCOMES = M1 / "09_us_au_government_acquisition/reports/au_candidate_outcomes.csv"
END = "2026-09-21"
START = "1988-01-01"


def utc_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def publication_strings():
    values = {}
    for path in (UK_HIST_MANIFEST, UK_MANIFEST):
        for row in csv_rows(path):
            values[row["canonical_url"]] = row["first_published_at"]
    return values


def main():
    raw_times = publication_strings()
    au_rows = {r["landing_url"]: r for r in csv_rows(AU_OUTCOMES)}
    c = duckdb.connect(str(USAU), read_only=True)
    c.execute("SET TimeZone='UTC'")
    frames = c.execute("""
      SELECT source_id, count(*) AS parents,
        count(*) FILTER (WHERE publication_date IS NULL) AS unknown_date,
        count(*) FILTER (WHERE publication_date < DATE '1988-01-01') AS before_start,
        count(*) FILTER (WHERE publication_date > DATE '2026-09-21') AS after_end,
        count(*) FILTER (WHERE publication_timestamp IS NOT NULL AND
          CAST(publication_timestamp AS DATE) IS DISTINCT FROM publication_date) AS utc_day_difference
      FROM documents WHERE parent_document_id IS NULL GROUP BY source_id ORDER BY source_id
    """).fetchall()
    au_evidence = c.execute("""
      SELECT d.document_id,d.source_id,d.canonical_url,d.publication_date,
             d.publication_date_basis,e.date_value,e.date_precision,
             e.cms_created_at,e.source_status,e.metadata_snapshot_path
      FROM documents d JOIN us_au_record_evidence e USING(document_id)
      WHERE d.source_id='au_dcceew_current_catalogue_2026_snapshot'
        AND d.publication_date IS NULL ORDER BY d.document_id
    """).fetchall()
    mismatches = c.execute("""
      SELECT document_id,source_id,canonical_url,publication_date,
             CAST(publication_timestamp AS VARCHAR),
             CAST(publication_timestamp AS DATE),publication_date_basis
      FROM documents
      WHERE publication_timestamp IS NOT NULL
        AND CAST(publication_timestamp AS DATE) IS DISTINCT FROM publication_date
      ORDER BY source_id,document_id
    """).fetchall()
    c.close()
    fields = ["exception_type", "source_id", "document_id", "canonical_url",
              "stored_publication_date", "utc_timestamp_date", "publication_timestamp_utc",
              "raw_source_first_published_at", "date_value", "date_precision", "raw_pending_date_candidate", "cms_created_at_not_publication",
              "publication_date_basis", "source_status", "evidence_path", "boundary_status", "review_action"]
    exceptions = []
    for did, source, url, published, basis, value, precision, cms, status, evidence in au_evidence:
        outcome = au_rows.get(url, {})
        exceptions.append(dict(exception_type="original_publication_date_unresolved", source_id=source,
            document_id=did, canonical_url=url, stored_publication_date="", utc_timestamp_date="",
            publication_timestamp_utc="", raw_source_first_published_at="",
            date_value=value or "", date_precision=precision,
            raw_pending_date_candidate=outcome.get("web_original_date_candidate_raw_pending", ""),
            cms_created_at_not_publication=cms or outcome.get("cms_created_at_not_original_date", ""),
            publication_date_basis=basis, source_status=status,
            evidence_path=evidence + " | " + str(AU_OUTCOMES.relative_to(ROOT)),
            boundary_status="uncertain_month_crosses_cutoff" if (value or outcome.get("web_original_date_candidate_raw_pending", "")) == "2026-09" else "unresolved_original_date",
            review_action="verify original issue date and independent Work/primary file; do not use CMS date"))
    for did, source, url, published, stamp, utc_day, basis in mismatches:
        raw = raw_times.get(url, "")
        exceptions.append(dict(exception_type="source_calendar_day_vs_utc_day", source_id=source,
            document_id=did, canonical_url=url, stored_publication_date=published.isoformat(),
            utc_timestamp_date=utc_day.isoformat(), publication_timestamp_utc=stamp,
            raw_source_first_published_at=raw, date_value="", date_precision="timestamp", raw_pending_date_candidate="",
            cms_created_at_not_publication="", publication_date_basis=basis, source_status="",
            evidence_path=str((UK_MANIFEST if source == 'src_ac30b1ae596ab5ab5379' else UK_HIST_MANIFEST).relative_to(ROOT)),
            boundary_status="both_days_inside_study_interval",
            review_action="decide source-local vs UTC monthly bin using raw timestamp; preserve both dates"))
    with (OUT / "date_exceptions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(exceptions)

    u = duckdb.connect(str(UK), read_only=True)
    uk_counts = u.execute("""
      SELECT count(*),count(*) FILTER (WHERE publication_date IS NULL),
        count(*) FILTER (WHERE publication_date < DATE '1988-01-01'),
        count(*) FILTER (WHERE publication_date > DATE '2026-09-21')
      FROM documents WHERE parent_document_id IS NULL
    """).fetchone()
    u.close()
    e = duckdb.connect(str(EU), read_only=True)
    eu_counts = {
      "works": e.execute("SELECT count(*) FROM eu_works").fetchone()[0],
      "work_date_rows": e.execute("SELECT count(*) FROM eu_work_dates").fetchone()[0],
      "date_before_start": e.execute("SELECT count(*) FROM eu_work_dates WHERE document_date < ?", [START]).fetchone()[0],
      "date_after_end": e.execute("SELECT count(*) FROM eu_work_dates WHERE document_date > ?", [END]).fetchone()[0],
      "invalid_date": e.execute("SELECT count(*) FROM eu_work_dates WHERE try_cast(document_date AS DATE) IS NULL").fetchone()[0],
      "month_mismatch": e.execute("SELECT count(*) FROM eu_work_dates WHERE left(document_date,7) <> source_month").fetchone()[0],
      "multiple_dates_per_work": e.execute("SELECT count(*) FROM (SELECT work_uri FROM eu_work_dates GROUP BY 1 HAVING count(DISTINCT document_date)>1)").fetchone()[0],
    }
    e.close()
    mismatch_month = sum(x["stored_publication_date"][:7] != x["utc_timestamp_date"][:7] for x in exceptions if x["exception_type"] == "source_calendar_day_vs_utc_day")
    raw_missing = sum(not x["raw_source_first_published_at"] for x in exceptions if x["exception_type"] == "source_calendar_day_vs_utc_day")
    summary = {
      "generated_at_utc": datetime.now(timezone.utc).isoformat(),
      "input_file_mtimes_utc": {str(p.relative_to(ROOT)): utc_mtime(p) for p in (UK, USAU, EU, UK_MANIFEST, UK_HIST_MANIFEST, AU_OUTCOMES)},
      "units": "UK and US/AU documents are independent parent rows; EU is distinct Work URI; 09 contains a UK copy, not an additional UK corpus",
      "fixed_publication_interval": [START, END],
      "uk_original_db": dict(zip(["parents", "unknown", "before", "after"], uk_counts)),
      "09_source_counts": [dict(zip(["source_id", "parents", "unknown", "before", "after", "utc_day_difference"], row)) for row in frames],
      "eu_stage": eu_counts,
      "exception_ledger_rows": len(exceptions),
      "exception_types": dict(Counter(x["exception_type"] for x in exceptions)),
      "govuk_month_boundary_differences": mismatch_month,
      "govuk_mismatch_rows_without_raw_timestamp": raw_missing,
      "AU_missing_date_evidence_precision": dict(Counter(x["date_precision"] for x in exceptions if x["source_id"] == 'au_dcceew_current_catalogue_2026_snapshot')),
      "AU_CMS_dates_after_cutoff_among_unresolved": sum((x["cms_created_at_not_publication"] or "")[:10] > END for x in exceptions if x["source_id"] == 'au_dcceew_current_catalogue_2026_snapshot'),
    }
    (OUT / "date_counts.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("exception_ledger_rows", "exception_types", "govuk_month_boundary_differences", "govuk_mismatch_rows_without_raw_timestamp")}, indent=2))


if __name__ == "__main__":
    main()
