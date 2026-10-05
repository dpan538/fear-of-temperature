"""Enumerate a narrowly defined EC preparatory-Act Work series in CELLAR.

This is not all EU policy. Monthly counts are DISTINCT Work identifiers with an
English expression, created by the Commission (`COM`) and dated by the Work's
document date. Full Work IDs/files are not harvested in this index pass.
"""

import csv
import io
import json
import time
import urllib.parse
from pathlib import Path

from extend_official_probes import request


HERE = Path(__file__).resolve().parent
DEST = HERE / "eu_cellar_commission_preparatory_month_index.csv"
FIELDS = ("year_month", "year", "month", "work_count", "unit", "institution_filter",
          "genre_filter", "language_filter", "date_basis", "status", "http_status",
          "request_url", "response_evidence")


def query(year):
    end = "2026-09-22" if year == 2026 else f"{year+1}-01-01"
    sparql = f"""PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT (MONTH(?date) AS ?month) (COUNT(DISTINCT ?work) AS ?work_count) WHERE {{
  ?work a cdm:act_preparatory ;
        cdm:work_date_document ?date ;
        cdm:work_created_by_agent <http://publications.europa.eu/resource/authority/corporate-body/COM> .
  ?expr cdm:expression_belongs_to_work ?work ;
        cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
  FILTER (?date >= \"{year}-01-01\"^^xsd:date && ?date < \"{end}\"^^xsd:date)
}} GROUP BY (MONTH(?date)) ORDER BY ?month"""
    url = "https://publications.europa.eu/webapi/rdf/sparql?" + urllib.parse.urlencode({"query": sparql, "format": "text/csv"})
    body, meta = request(f"eu_cellar_commission_en_work_months_{year}", url, {"Accept": "text/csv"})
    return body, meta


def main():
    completed = set()
    if DEST.exists():
        with DEST.open(newline="", encoding="utf-8") as handle:
            completed = {int(row["year"]) for row in csv.DictReader(handle) if row["status"] == "verified_month_count"}
    with DEST.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if handle.tell() == 0:
            writer.writeheader()
        for year in range(1988, 2027):
            if year in completed:
                continue
            if year > 1988:
                time.sleep(2.0)
            body, meta = query(year)
            key = f"eu_cellar_commission_en_work_months_{year}"
            status = "verified_month_count" if meta["status"] == 200 and "csv" in meta["content_type"].lower() else "request_failed"
            parsed = []
            if status == "verified_month_count":
                try:
                    parsed = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
                    assert {"month", "work_count"} <= set(parsed[0]) if parsed else body.strip().startswith(b'"month"')
                    assert all(1 <= int(r["month"]) <= 12 and int(r["work_count"]) >= 0 for r in parsed)
                    assert len({int(r["month"]) for r in parsed}) == len(parsed)
                except Exception:
                    status, parsed = "parse_failed", []
            counts = {int(r["month"]): int(r["work_count"]) for r in parsed}
            for month in range(1, 10 if year == 2026 else 13):
                writer.writerow({"year_month": f"{year:04d}-{month:02d}", "year": year, "month": month,
                                 "work_count": counts.get(month, 0) if status == "verified_month_count" else "",
                                 "unit": "DISTINCT CELLAR Work with English expression",
                                 "institution_filter": "cdm:work_created_by_agent=corporate-body/COM",
                                 "genre_filter": "rdf:type=cdm:act_preparatory",
                                 "language_filter": "cdm:expression_uses_language=language/ENG",
                                 "date_basis": "cdm:work_date_document",
                                 "status": status, "http_status": meta["status"],
                                 "request_url": meta["request_url"],
                                 "response_evidence": f"evidence/continued_official_probes/{key}.body"})
            handle.flush()
            print(year, meta["status"], status, sum(counts.values()) if counts else "unknown", flush=True)
            if status != "verified_month_count":
                break


if __name__ == "__main__":
    main()
