"""Checkpointed Work-URI enumeration for the frozen Commission CELLAR series."""
import argparse
import csv
import hashlib
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

HERE = Path(__file__).resolve().parent
INDEX = HERE.parent / "08_cross_region_government_coverage" / "eu_cellar_commission_preparatory_month_index.csv"
ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"
PAGE_SIZE = 500
HEADERS = {"Accept": "text/csv", "User-Agent": "FearTemperatureResearch/1.0 (public academic source acquisition)"}


def sha(body):
    return hashlib.sha256(body).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def index():
    with INDEX.open(newline="", encoding="utf-8") as handle:
        return {r["year_month"]: int(r["work_count"]) for r in csv.DictReader(handle)
                if r["status"] == "verified_month_count"}


def month_bounds(month):
    year, mm = map(int, month.split("-"))
    following = f"{year+1}-01-01" if mm == 12 else f"{year}-{mm+1:02d}-01"
    if month == "2026-09":
        following = "2026-09-22"
    return f"{month}-01", following


def query(month, offset):
    start, end = month_bounds(month)
    return f'''PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?work ?date WHERE {{
  ?work a cdm:act_preparatory ;
        cdm:work_date_document ?date ;
        cdm:work_created_by_agent <http://publications.europa.eu/resource/authority/corporate-body/COM> .
  ?expr cdm:expression_belongs_to_work ?work ;
        cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
  FILTER (?date >= "{start}"^^xsd:date && ?date < "{end}"^^xsd:date)
}} ORDER BY ?work ?date LIMIT {PAGE_SIZE} OFFSET {offset}'''


def page_path(month, offset):
    return HERE / "raw" / "work_pages" / month[:4] / f"{month}_offset_{offset:05d}.csv"


def fetch_page(month, offset):
    path = page_path(month, offset)
    meta_path = path.with_suffix(".request.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        body = path.read_bytes()
        if meta.get("status") == "downloaded" and sha(body) == meta.get("sha256"):
            return body, meta
    sparql = query(month, offset)
    url = ENDPOINT + "?" + urlencode({"query": sparql, "format": "text/csv"})
    path.parent.mkdir(parents=True, exist_ok=True)
    body, status, final, mime, error, headers = b"", 0, url, "", "", {}
    try:
        response = requests.get(url, headers=HEADERS, timeout=90)
        status, final, mime = response.status_code, response.url, response.headers.get("Content-Type", "")
        headers = {k: v for k, v in response.headers.items() if k.lower() in {"retry-after", "date", "content-length", "etag"}}
        body = response.content
        if len(body) > 10_000_000:
            error = "response_exceeds_10MB_cap"
    except requests.RequestException as exc:
        error = f"{type(exc).__name__}: {str(exc)[:240]}"
    valid = status == 200 and "csv" in mime.lower() and not error
    if valid:
        path.write_bytes(body)
    elif body:
        path.with_suffix(".error.body").write_bytes(body[:8192])
    meta = {"request_url": url, "final_url": final, "http_status": status, "retrieved_at_utc": stamp(),
            "mime_type": mime, "byte_count": len(body), "sha256": sha(body) if body else "",
            "raw_path": str(path.relative_to(HERE)) if valid else "", "status": "downloaded" if valid else "failed",
            "error": error or ("unexpected_status_or_mime" if not valid else ""), "response_headers": headers}
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return body, meta


def parse(body):
    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
    if rows and not {"work", "date"} <= set(rows[0]):
        raise ValueError("missing Work/date columns")
    if not rows and b"work" not in body[:100]:
        raise ValueError("not a CSV Work/date result")
    for row in rows:
        if not row["work"].startswith("http://publications.europa.eu/resource/cellar/"):
            raise ValueError("unexpected Work URI")
        if len(row["date"]) < 10 or row["date"][4] != "-":
            raise ValueError("unexpected date literal")
    return rows


def save_month(month, expected, entries, pages):
    works = {r["work"] for r, _ in entries}
    status = "reconciled" if len(works) == expected else "count_mismatch"
    out = HERE / "manifests" / "months" / f"{month}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["year_month", "work_uri", "date_observed", "source_page"])
        writer.writeheader()
        for row, offset in entries:
            writer.writerow({"year_month": month, "work_uri": row["work"], "date_observed": row["date"],
                             "source_page": str(page_path(month, offset).relative_to(HERE))})
    state = {"year_month": month, "expected_distinct_works": expected, "observed_distinct_works": len(works),
             "work_date_rows": len(entries), "pages": pages, "status": status, "updated_at_utc": stamp()}
    (HERE / "manifests" / "months" / f"{month}.json").write_text(json.dumps(state, indent=2) + "\n")
    return state


def enumerate_month(month, expected, delay):
    offset, pages, entries = 0, 0, []
    while True:
        body, meta = fetch_page(month, offset)
        if meta["status"] != "downloaded":
            return {"year_month": month, "status": "request_failed", "http_status": meta["http_status"], "error": meta["error"]}
        rows = parse(body)
        entries.extend((row, offset) for row in rows)
        pages += 1
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(delay)
    return save_month(month, expected, entries, pages)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["enumerate"])
    parser.add_argument("--start", default="1988-01")
    parser.add_argument("--end", default="2026-09")
    parser.add_argument("--limit-months", type=int, default=0)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    counts = index()
    months = [m for m in sorted(counts) if args.start <= m <= args.end]
    if args.limit_months:
        months = months[:args.limit_months]
    for n, month in enumerate(months, 1):
        state_path = HERE / "manifests" / "months" / f"{month}.json"
        if state_path.exists() and json.loads(state_path.read_text()).get("status") == "reconciled":
            continue
        result = enumerate_month(month, counts[month], args.delay)
        print(n, month, result, flush=True)
        if result["status"] != "reconciled":
            break
        time.sleep(args.delay)


if __name__ == "__main__":
    main()
