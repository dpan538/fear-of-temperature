"""Official Oireachtas written-question monthly index enumeration.

The yearly endpoint visibly caps `questionCount` at 10,000. Monthly partitions
avoid treating that sentinel as an annual count. These are all-department
question totals, not the intended environment-minister government-response set.
"""

import csv
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from calendar import monthrange
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
RAW = HERE / "evidence" / "ireland_oireachtas_monthly"
RAW.mkdir(parents=True, exist_ok=True)
OUT = HERE / "ie_written_question_month_index.csv"
FIELDS = ("year_month", "start", "end", "unit", "institution_filter", "genre_filter",
          "official_index_count", "response_rows", "count_capped_or_unknown", "http_status",
          "content_type", "request_url", "final_url", "retrieved_at_utc", "sha256")


def months():
    for year in range(2012, 2027):
        for month in range(1, 13):
            if (year, month) < (2012, 7) or (year, month) > (2026, 9):
                continue
            start = f"{year:04d}-{month:02d}-01"
            end_day = 21 if (year, month) == (2026, 9) else monthrange(year, month)[1]
            end = f"{year:04d}-{month:02d}-{end_day:02d}"
            yield f"{year:04d}-{month:02d}", start, end


def fetch(key, start, end):
    params = {"date_start": start, "date_end": end, "qtype": "written", "limit": "1",
              "show_answers": "false"}
    url = "https://api.oireachtas.ie/v1/questions?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "FearTemperatureCoverageAudit/1.0 (research metadata)"})
    acquired = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body, status, final_url = response.read(), response.status, response.url
            mime, headers = response.headers.get("Content-Type", ""), dict(response.headers)
    except urllib.error.HTTPError as error:
        body, status, final_url = error.read(), error.code, error.url
        mime, headers = error.headers.get("Content-Type", ""), dict(error.headers)
    except urllib.error.URLError as error:
        body, status, final_url, mime, headers = str(error).encode(), 0, url, "error/transport", {}
    digest = hashlib.sha256(body).hexdigest()
    (RAW / f"{key}.body").write_bytes(body)
    (RAW / f"{key}.request.json").write_text(json.dumps({
        "request_url": url, "final_url": final_url, "http_status": status,
        "content_type": mime, "retrieved_at_utc": acquired, "sha256": digest,
        "response_headers": headers}, indent=2) + "\n", encoding="utf-8")
    count = rows = None
    if status == 200 and "json" in mime.lower():
        parsed = json.loads(body)
        count = parsed.get("head", {}).get("counts", {}).get("questionCount")
        rows = len(parsed.get("results", []))
    return dict(zip(FIELDS, (key, start, end, "question (not minister response)",
                             "none; all departments", "qtype=written", count, rows,
                             count is None or count >= 10000, status, mime, url, final_url,
                             acquired, digest)))


def main():
    completed = {}
    if OUT.exists():
        with OUT.open(newline="", encoding="utf-8") as handle:
            completed = {row["year_month"]: row for row in csv.DictReader(handle)}
    with OUT.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not completed:
            writer.writeheader()
        for key, start, end in months():
            if key in completed:
                continue
            if completed:
                time.sleep(1.5)
            row = fetch(key, start, end)
            writer.writerow(row)
            handle.flush()
            completed[key] = row
            print(key, row["http_status"], row["official_index_count"], flush=True)
            if row["http_status"] in (0, 403, 429) or row["http_status"] >= 500:
                break


if __name__ == "__main__":
    main()
