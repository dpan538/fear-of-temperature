"""Transcribe and reconcile the observed official NZ Parliament UI counts.

These are browser-rendered list counts, not downloaded individual replies. The
filter is question-asked date, portfolio, and current answered status.
"""

import calendar
import csv
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEST = HERE / "nz_parliament_climate_answered_2025_month_index.csv"
COUNTS = (14, 106, 64, 20, 79, 22, 24, 36, 32, 49, 56, 34)
PORTS = "81081C1A-44AC-4D80-9B95-8C3D043BA3AA_1,81081C1A-44AC-4D80-9B95-8C3D043BA3AA_0"


def main():
    assert sum(COUNTS) == 536  # independent UI full-year filtered count
    fields = ("year_month", "date_from", "date_to", "displayed_count", "unit", "status_filter",
              "portfolio_filter_label", "portfolio_filter_code", "date_basis", "official_url",
              "evidence_type", "observed_at_utc", "coverage_status", "caveat")
    with DEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for month, count in enumerate(COUNTS, 1):
            start = f"2025-{month:02d}-01"
            end = f"2025-{month:02d}-{calendar.monthrange(2025, month)[1]:02d}"
            url = ("https://questions.parliament.nz/written-questions?tab=0&status=Question%20Answered"
                   f"&ports={PORTS}&from={start}&to={end}&period=0&col=1&dir=1&lang=en")
            writer.writerow({"year_month": f"2025-{month:02d}", "date_from": start, "date_to": end,
                "displayed_count": count, "unit": "written question record whose current status is Question Answered",
                "status_filter": "Question Answered", "portfolio_filter_label": "Climate Change",
                "portfolio_filter_code": PORTS, "date_basis": "question-asked date range in official UI",
                "official_url": url, "evidence_type": "official browser-rendered list count; HTTP shell alone does not contain count",
                "observed_at_utc": "2026-09-23T06:54:08Z", "coverage_status": "verified_UI_index_count",
                "caveat": "Not answer-received-date distribution; individual records and corrected versions not exhaustively downloaded"})
    print("months", len(COUNTS), "reconciled annual answered-question count", sum(COUNTS))


if __name__ == "__main__":
    main()
