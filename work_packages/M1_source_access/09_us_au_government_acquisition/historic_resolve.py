"""Resolve official annual-index page references to FR issue dates by HEAD.

This maps citation locators only. It does not prove an independent article
boundary or usable full text.
"""
import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from historic_index import RAW

def now():
    return datetime.now(timezone.utc).isoformat()


def source_rows(year):
    with (RAW / f"{year}_parent_agency_candidate_locators.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def key(row):
    return int(row["fr_start_page_candidate"])


def path_for(year, page):
    return RAW / f"{year}_resolved_pages" / f"{year-1935}_FR_{page}.request.json"


def request_page(year, page, session):
    path = path_for(year, page)
    if path.exists():
        return json.loads(path.read_text()), False
    url = f"https://www.govinfo.gov/link/fr/{year-1935}/{page}"
    status, location, error, headers = 0, "", "", {}
    try:
        response = session.head(url, allow_redirects=False, timeout=25,
                                headers={"User-Agent": "FearTemperatureResearch/1.0 (official historical citation check)"})
        status = response.status_code
        location = response.headers.get("Location", "")
        headers = {k: v for k, v in response.headers.items() if k.lower() in {"location", "date", "retry-after"}}
    except requests.RequestException as exc:
        error = f"{type(exc).__name__}: {str(exc)[:240]}"
    match = re.search(r"/FR-(\d{4}-\d{2}-\d{2})/pdf/FR-\1\.pdf#page=(\d+)", location)
    state = "resolved_to_issue_page" if status in (301, 302, 303) and match else "unresolved"
    record = {"request_url": url, "http_status": status, "retrieved_at_utc": now(),
              "location": location, "issue_date": match.group(1) if match else "",
              "issue_pdf_page": int(match.group(2)) if match else "",
              "state": state, "error": error, "response_headers": headers}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n")
    return record, True


def export(year, rows):
    out = []
    for row in rows:
        path = path_for(year, key(row))
        meta = json.loads(path.read_text()) if path.exists() else {}
        out.append({**row, "issue_date_from_official_link": meta.get("issue_date", ""),
                    "issue_pdf_page": meta.get("issue_pdf_page", ""),
                    "link_state": meta.get("state", "not_requested"),
                    "link_http_status": meta.get("http_status", ""),
                    "link_response_evidence": str(path.relative_to(RAW)) if meta else ""})
    with (RAW / f"{year}_parent_agency_resolved_locators.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out[0])); writer.writeheader(); writer.writerows(out)
    print(json.dumps({"index_locator_rows": len(out), "unique_pages": len(set(key(r) for r in rows)),
                      "resolved_rows": sum(r["link_state"] == "resolved_to_issue_page" for r in out),
                      "not_requested_rows": sum(r["link_state"] == "not_requested" for r in out)}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--start-year", type=int, default=1988)
    parser.add_argument("--end-year", type=int, default=1988)
    args = parser.parse_args()
    session = requests.Session()
    for year in range(args.start_year, args.end_year + 1):
        rows = source_rows(year)
        pages = sorted(set(key(r) for r in rows))
        attempted, transport, stopped = 0, 0, False
        for page in pages:
            if attempted >= args.limit:
                break
            meta, fresh = request_page(year, page, session)
            if not fresh:
                continue
            attempted += 1
            transport = transport + 1 if meta["http_status"] == 0 else 0
            if attempted % 25 == 0 or meta["state"] != "resolved_to_issue_page":
                print(year, attempted, page, meta["http_status"], meta["state"], flush=True)
            if meta["http_status"] in (403, 429) or transport >= 3:
                print("STOP: historical link access/transport limit", flush=True)
                stopped = True
                break
            time.sleep(args.delay)
        export(year, rows)
        if stopped:
            break


if __name__ == "__main__":
    main()
