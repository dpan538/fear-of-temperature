"""Sample official issue Content-Length headers to size the historical queue."""
import csv
import json
import statistics
import time
from datetime import datetime, timezone

import requests

from historic_index import RAW

OUT = RAW / "issue_size_sample.csv"
SUMMARY = RAW / "issue_size_sample.summary.json"


def dates_by_year():
    result = {}
    for year in range(1988, 1994):
        with (RAW / f"{year}_parent_agency_resolved_locators.csv").open(newline="") as handle:
            dates = sorted({row["issue_date_from_official_link"] for row in csv.DictReader(handle)
                            if row["link_state"] == "resolved_to_issue_page"})
        result[year] = dates
    return result


def main():
    dates = dates_by_year()
    existing = {}
    if OUT.exists():
        with OUT.open(newline="") as handle:
            existing = {row["issue_date"]: row for row in csv.DictReader(handle)}
    selected = {day for days in dates.values() for day in (days[len(days)//10], days[len(days)//2], days[9*len(days)//10])}
    session = requests.Session()
    for day in sorted(selected):
        if day in existing and existing[day]["http_status"] == "200" and existing[day]["content_length"].isdigit():
            continue
        url = f"https://www.govinfo.gov/content/pkg/FR-{day}/pdf/FR-{day}.pdf"
        row = {"issue_date": day, "url": url, "http_status": "", "content_length": "",
               "content_type": "", "checked_at_utc": datetime.now(timezone.utc).isoformat(), "error": ""}
        try:
            response = session.head(url, timeout=(10, 30), allow_redirects=True,
                                    headers={"User-Agent": "FearTemperatureResearch/1.0 (public issue storage estimate)"})
            row.update(http_status=str(response.status_code),
                       content_length=response.headers.get("Content-Length", ""),
                       content_type=response.headers.get("Content-Type", ""))
        except requests.RequestException as exc:
            row["error"] = f"{type(exc).__name__}: {str(exc)[-200:]}"
        existing[day] = row
        print(json.dumps(row), flush=True)
        time.sleep(0.5)
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(next(iter(existing.values()))))
        writer.writeheader()
        writer.writerows(existing[day] for day in sorted(existing))
    lengths = [int(existing[day]["content_length"]) for day in selected
               if existing[day]["http_status"] == "200" and existing[day]["content_length"].isdigit()]
    summary = {"issue_dates_in_candidate_locator_queue": sum(map(len, dates.values())),
               "sampled_issues": len(selected), "valid_content_lengths": len(lengths),
               "median_bytes": int(statistics.median(lengths)) if lengths else None,
               "min_bytes": min(lengths) if lengths else None,
               "max_bytes": max(lengths) if lengths else None,
               "median_extrapolation_bytes": int(statistics.median(lengths))*sum(map(len, dates.values())) if lengths else None,
               "meaning": "Storage planning sample, not a document denominator or proof that every candidate locator is a rule.",
               "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
