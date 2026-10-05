"""Harvest the bounded current-DCCEEW publication listing (83 frozen pages).

Listing rows are catalogue landing pages, not necessarily unique policy files.
Drupal 'created' timestamps are kept distinct from original publication dates.
"""

import csv
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup


HERE = Path(__file__).resolve().parent
RAW = HERE / "evidence" / "au_dcceew_catalogue"
RAW.mkdir(parents=True, exist_ok=True)
PROBE = HERE / "raw_probe" / "au_dcceew_page0.html"
BASE = "https://www.dcceew.gov.au/about/publications?page={}"
PAGE_MAX = 82  # frozen from first official page's Last-page link on 2026-09-23
PAGE_FIELDS = ("page", "request_url", "http_status", "content_type", "retrieved_at_utc",
               "sha256", "listing_rows", "last_page_link", "state")
REC_FIELDS = ("source_id", "catalogue_page", "landing_url", "title", "catalogue_created_at",
              "displayed_publication_year", "tags", "description", "record_boundary",
              "original_publication_date", "within_cutoff")


def acquire(page):
    dest = RAW / f"page_{page:03d}.html"
    meta = RAW / f"page_{page:03d}.request.json"
    if dest.exists() and meta.exists():
        return dest.read_bytes(), json.loads(meta.read_text())
    url = BASE.format(page)
    acquired = datetime.now(timezone.utc).isoformat()
    if page == 0 and PROBE.exists():
        body = PROBE.read_bytes()
        status, final_url, mime = 200, url, "text/html"
        headers = {"provenance": "raw_probe/au_dcceew_page0.headers"}
        # This page was obtained in an earlier real request. The current run's
        # clock is a reuse time, not the acquisition time; use the saved HTTP
        # Date header as an explicitly approximate request timestamp.
        raw_headers = (HERE / "raw_probe" / "au_dcceew_page0.headers").read_text()
        response_date = next((line.split(":", 1)[1].strip() for line in raw_headers.splitlines()
                              if line.lower().startswith("date:")), "")
        acquired = parsedate_to_datetime(response_date).astimezone(timezone.utc).isoformat() if response_date else "unknown"
        headers["timestamp_basis"] = "saved HTTP Date header; approximate retrieval time"
        headers["reused_at_utc"] = datetime.now(timezone.utc).isoformat()
    else:
        request = urllib.request.Request(url, headers={"User-Agent": "FearTemperatureCoverageAudit/1.0 (research metadata)"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body, status, final_url = response.read(), response.status, response.url
                mime, headers = response.headers.get("Content-Type", ""), dict(response.headers)
        except urllib.error.HTTPError as error:
            body, status, final_url = error.read(), error.code, error.url
            mime, headers = error.headers.get("Content-Type", ""), dict(error.headers)
        except urllib.error.URLError as error:
            body, status, final_url, mime, headers = str(error).encode(), 0, url, "error/transport", {}
    digest = hashlib.sha256(body).hexdigest()
    dest.write_bytes(body)
    metadata = {"request_url": url, "final_url": final_url, "http_status": status,
                "content_type": mime, "retrieved_at_utc": acquired, "sha256": digest,
                "response_headers": headers}
    meta.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return body, metadata


def parse(page, body, meta):
    if meta["http_status"] != 200 or "html" not in meta["content_type"].lower():
        return [], {"page": page, "request_url": meta["request_url"],
                    "http_status": meta["http_status"], "content_type": meta["content_type"],
                    "retrieved_at_utc": meta["retrieved_at_utc"], "sha256": meta["sha256"],
                    "listing_rows": 0, "last_page_link": "", "state": "failed"}
    soup = BeautifulSoup(body, "html.parser")
    cards = soup.select(".view-publications-listing .view-content > .views-row")
    last = soup.select_one('a[rel="last"]')
    if last is None:
        last = next((a for a in soup.select('a[href*="page="]') if "Last page" in a.get_text(" ", strip=True)), None)
    records = []
    for card in cards:
        anchor = card.select_one(".views-field-title a[href]")
        if not anchor:
            continue
        url = urljoin("https://www.dcceew.gov.au", anchor["href"])
        stamp = card.select_one(".views-field-created-1 time")
        created = stamp.get("datetime", "") if stamp else ""
        display_year = stamp.get_text(" ", strip=True) if stamp else ""
        tags = [x.get_text(" ", strip=True) for x in card.select(".news-tag li")]
        desc = card.select_one(".views-field-body")
        records.append({"source_id": "au_dcceew_publications_listing", "catalogue_page": page,
                        "landing_url": url, "title": anchor.get_text(" ", strip=True),
                        "catalogue_created_at": created, "displayed_publication_year": display_year,
                        "tags": ";".join(tags), "description": desc.get_text(" ", strip=True) if desc else "",
                        "record_boundary": "landing_page; attachment_count_unknown",
                        "original_publication_date": "unknown",
                        "within_cutoff": bool(created and created[:10] <= "2026-09-21")})
    audit = {"page": page, "request_url": meta["request_url"],
             "http_status": meta["http_status"], "content_type": meta["content_type"],
             "retrieved_at_utc": meta["retrieved_at_utc"], "sha256": meta["sha256"],
             "listing_rows": len(records), "last_page_link": last.get("href", "") if last else "",
             "state": "enumerated" if records else "empty_or_parse_failure"}
    return records, audit


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    records, pages = [], []
    for page in range(PAGE_MAX + 1):
        if page > 0:
            time.sleep(1.2)
        body, meta = acquire(page)
        found, audit = parse(page, body, meta)
        records.extend(found); pages.append(audit)
        write_csv(HERE / "au_dcceew_catalogue_pages.csv", PAGE_FIELDS, pages)
        write_csv(HERE / "au_dcceew_catalogue_rows.csv", REC_FIELDS, records)
        print(page, audit["http_status"], audit["listing_rows"], flush=True)
        if audit["http_status"] in (0, 403, 429) or audit["http_status"] >= 500:
            break
    unique = len({r["landing_url"] for r in records})
    print(json.dumps({"pages_attempted": len(pages), "rows": len(records),
                      "unique_landing_urls": unique, "duplicates": len(records) - unique}), flush=True)


if __name__ == "__main__":
    main()
