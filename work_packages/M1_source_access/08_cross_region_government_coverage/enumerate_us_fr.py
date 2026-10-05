"""Enumerate bounded US Federal Register administrative-document metadata.

Selected strata are official agency hierarchy filters (EPA and Energy
Department) crossed with final and proposed rules, not a climate-keyword
subset and not a UK policy-paper equivalent. No GovInfo key is used.
"""

import csv
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
RAW = HERE / "evidence" / "us_federal_register"
RAW.mkdir(parents=True, exist_ok=True)
PARTITIONS = HERE / "us_fr_partitions.csv"
RECORDS = HERE / "us_fr_records.csv"
AGENCIES = (("EPA", "environmental-protection-agency", 145),
            ("DOE", "energy-department", 136))
GENRES = (("final_rule", "RULE"), ("proposed_rule", "PRORULE"))
PART_FIELDS = ("agency", "agency_slug", "agency_id", "genre", "year", "start", "end",
               "official_count", "records_enumerated", "pages_expected", "pages_obtained",
               "status", "failure_reason")
REC_FIELDS = ("source_record_id", "document_number", "agency_stratum", "genre",
              "publication_date", "title", "canonical_url", "pdf_url", "agency_ids",
              "agency_names", "language", "boundary", "raw_partition")


def request_page(agency, genre, year, page):
    start = f"{year}-01-01"
    end = "2026-09-21" if year == 2026 else f"{year}-12-31"
    params = {
        "conditions[agencies][]": agency,
        "conditions[type][]": genre,
        "conditions[publication_date][gte]": start,
        "conditions[publication_date][lte]": end,
        "per_page": "1000", "page": str(page),
    }
    url = "https://www.federalregister.gov/api/v1/documents.json?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "FearTemperatureCoverageAudit/1.0 (research metadata)"})
    acquired = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            body, status, final_url = response.read(), response.status, response.url
            mime, headers = response.headers.get("Content-Type", ""), dict(response.headers)
    except urllib.error.HTTPError as error:
        body, status, final_url = error.read(), error.code, error.url
        mime, headers = error.headers.get("Content-Type", ""), dict(error.headers)
    except urllib.error.URLError as error:
        body, status, final_url, mime, headers = str(error).encode(), 0, url, "error/transport", {}
    key = f"{agency}_{genre}_{year}_p{page:03d}"
    (RAW / f"{key}.body").write_bytes(body)
    (RAW / f"{key}.request.json").write_text(json.dumps({
        "request_url": url, "final_url": final_url, "http_status": status,
        "content_type": mime, "retrieved_at_utc": acquired,
        "sha256": hashlib.sha256(body).hexdigest(), "response_headers": headers,
    }, indent=2) + "\n", encoding="utf-8")
    parsed = json.loads(body) if status == 200 and "json" in mime.lower() else None
    return parsed, status, headers


def main():
    done = set()
    if PARTITIONS.exists():
        with PARTITIONS.open(newline="", encoding="utf-8") as handle:
            done = {(r["agency"], r["genre"], int(r["year"]))
                    for r in csv.DictReader(handle) if r["status"] == "verified_enumerated"}
    with PARTITIONS.open("a", newline="", encoding="utf-8") as part_file, \
         RECORDS.open("a", newline="", encoding="utf-8") as rec_file:
        pw = csv.DictWriter(part_file, fieldnames=PART_FIELDS)
        rw = csv.DictWriter(rec_file, fieldnames=REC_FIELDS)
        if part_file.tell() == 0:
            pw.writeheader()
        if rec_file.tell() == 0:
            rw.writeheader()
        requests_made = 0
        for agency_name, agency_slug, agency_id in AGENCIES:
            for genre_name, genre_code in GENRES:
                for year in range(1994, 2027):
                    if (agency_name, genre_name, year) in done:
                        continue
                    if requests_made:
                        time.sleep(1.2)
                    parsed, http_status, headers = request_page(agency_slug, genre_code, year, 1)
                    requests_made += 1
                    row = dict(agency=agency_name, agency_slug=agency_slug, agency_id=agency_id,
                               genre=genre_name, year=year, start=f"{year}-01-01",
                               end="2026-09-21" if year == 2026 else f"{year}-12-31",
                               official_count="", records_enumerated=0, pages_expected="",
                               pages_obtained=0, status="partial", failure_reason="")
                    if parsed is None or not isinstance(parsed.get("results"), list):
                        row["status"] = "blocked" if http_status in (403, 429) else "request_failed"
                        row["failure_reason"] = f"HTTP {http_status}; Retry-After={headers.get('Retry-After', '')}"
                        pw.writerow(row); part_file.flush()
                        print(agency_name, genre_name, year, row["status"], flush=True)
                        if http_status in (0, 403, 429) or http_status >= 500:
                            return
                        continue
                    count = parsed.get("count")
                    expected = parsed.get("total_pages")
                    items = list(parsed["results"])
                    got_pages = 1
                    if isinstance(expected, int) and expected > 1:
                        for page in range(2, expected + 1):
                            time.sleep(1.2)
                            next_parsed, next_status, next_headers = request_page(agency_slug, genre_code, year, page)
                            requests_made += 1
                            if next_parsed is None or not isinstance(next_parsed.get("results"), list):
                                row["failure_reason"] = f"page {page}: HTTP {next_status}; Retry-After={next_headers.get('Retry-After', '')}"
                                break
                            items.extend(next_parsed["results"])
                            got_pages += 1
                    row.update(official_count=count, records_enumerated=len(items),
                               pages_expected=expected, pages_obtained=got_pages)
                    ids = [item.get("document_number") for item in items]
                    if len(ids) == len(set(ids)) and len(items) == count and got_pages == expected:
                        row["status"] = "verified_enumerated"
                    for item in items:
                        agencies = item.get("agencies") or []
                        rw.writerow(dict(source_record_id=f"us_fr:{item.get('document_number', '')}",
                                         document_number=item.get("document_number", ""),
                                         agency_stratum=agency_name, genre=genre_name,
                                         publication_date=item.get("publication_date", ""),
                                         title=item.get("title", ""), canonical_url=item.get("html_url", ""),
                                         pdf_url=item.get("pdf_url", ""),
                                         agency_ids=";".join(str(a.get("id", "")) for a in agencies),
                                         agency_names=";".join(a.get("name", "") for a in agencies),
                                         language="en presumed; verify on original", boundary="Federal Register document",
                                         raw_partition=f"{agency_slug}_{genre_code}_{year}"))
                    rec_file.flush()
                    pw.writerow(row); part_file.flush()
                    print(agency_name, genre_name, year, count, len(items), row["status"], flush=True)


if __name__ == "__main__":
    main()
