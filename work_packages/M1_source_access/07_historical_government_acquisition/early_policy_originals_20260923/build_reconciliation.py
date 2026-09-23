"""Read-only, bounded reconciliation for the early-policy originals tranche."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
DB = ROOT / "work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb"
PRIOR = ROOT / "work_packages/M1_source_access/07_historical_government_acquisition/zero_month_policy_recovery/reports/monthly_reference_availability_corrected.csv"
POLICY_SOURCES = ("src_ac30b1ae596ab5ab5379", "src_eaf57ccafde8ffd97f7e")
NAMED_GAPS = {
    "1990-09": ("Cm 1200", "restricted_original"),
    "1994-01": ("Cm 2426; Cm 2427; Cm 2429", "catalogued_original_missing"),
    "1995-12": ("Cm 3040", "catalogued_original_missing"),
    "1997-02": ("NC2 1997", "official_pdf_direct_access_blocked"),
    "1997-03": ("Cm 3587", "official_later_strategy_citation_original_missing"),
    "1999-05": ("Cm 4345", "restricted_original"),
    "2000-01": ("Cm 4548", "official_later_strategy_citation_original_missing"),
    "2000-11": ("Cm 4913", "archive_access_blocked"),
}


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    before_stat = DB.stat()
    con = duckdb.connect(str(DB), read_only=True)
    totals = {
        "documents": con.execute("select count(*) from documents").fetchone()[0],
        "text_segments": con.execute("select count(*) from text_segments").fetchone()[0],
        "policy_source_records": con.execute(
            "select count(*) from documents where source_id in (?, ?)", POLICY_SOURCES
        ).fetchone()[0],
    }
    raw = con.execute(
        """select strftime(publication_date, '%Y-%m') as year_month, count(*) as records
           from documents
           where source_id in (?, ?) and publication_date >= '1988-01-01'
             and publication_date < '2010-01-01'
           group by 1""",
        POLICY_SOURCES,
    ).fetchall()
    current = dict(raw)
    old = {}
    with PRIOR.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["series"] == "policy_document" and "1988-01" <= row["year_month"] <= "2009-12":
                old[row["year_month"]] = row
    months = []
    for year in range(1988, 2010):
        for month in range(1, 13):
            key = f"{year:04d}-{month:02d}"
            prior = old[key]
            observed = current.get(key, 0)
            assert observed == int(prior["stored_record_count"]), key
            months.append(
                {
                    "year_month": key,
                    "policy_records_before_stored_date": observed,
                    "policy_records_after_stored_date": observed,
                    "policy_records_research_exact_month_view": int(prior["research_exact_month_record_count"]),
                    "new_full_originals_this_tranche": 0,
                    "coverage_denominator_status": "unknown_predecessor_population",
                    "named_missing_identity": NAMED_GAPS.get(key, ("", ""))[0],
                    "named_gap_evidence_state": NAMED_GAPS.get(key, ("", ""))[1],
                    "note": "Record count is not acquisition coverage; stored and research dates are distinct.",
                }
            )
    write_csv(HERE / "policy_month_before_after.csv", list(months[0]), months)
    periods = (("1988-1994", 1988, 1994), ("1995-2000", 1995, 2000), ("2001-2009", 2001, 2009))
    period_rows = []
    for label, start, end in periods:
        subset = [r for r in months if start <= int(r["year_month"][:4]) <= end]
        period_rows.append(
            {
                "period": label,
                "stored_policy_before": sum(r["policy_records_before_stored_date"] for r in subset),
                "stored_policy_after": sum(r["policy_records_after_stored_date"] for r in subset),
                "research_exact_month_view": sum(r["policy_records_research_exact_month_view"] for r in subset),
                "new_originals": 0,
                "months": len(subset),
                "historical_population_denominator": "unknown",
            }
        )
    write_csv(HERE / "policy_period_before_after.csv", list(period_rows[0]), period_rows)
    con.close()
    after_stat = DB.stat()
    assert (before_stat.st_size, before_stat.st_mtime_ns) == (after_stat.st_size, after_stat.st_mtime_ns)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "formal_db_size_bytes_unchanged": before_stat.st_size,
        "formal_db_mtime_ns_unchanged": before_stat.st_mtime_ns,
        "totals": totals,
        "periods": period_rows,
        "new_documents": 0,
        "new_text_segments": 0,
        "formal_db_writes": 0,
        "monthly_rows": len(months),
        "prior_stored_months_match_db": True,
    }
    (HERE / "reconciliation.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
