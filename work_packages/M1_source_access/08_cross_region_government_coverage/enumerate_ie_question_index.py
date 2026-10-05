"""Bounded official Oireachtas written-question index count audit.

This intentionally does not call a count of all written questions an environment
department count. The API has no department filter in its Swagger definition.
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
RAW = HERE / "evidence" / "ireland_oireachtas_yearly"
RAW.mkdir(parents=True, exist_ok=True)
END_DATE = "2026-09-21"


def fetch(year):
    start = "2012-07-01" if year == 2012 else f"{year}-01-01"
    end = END_DATE if year == 2026 else f"{year}-12-31"
    params = {
        "date_start": start,
        "date_end": end,
        "qtype": "written",
        "limit": "1",
        "show_answers": "false",
    }
    url = "https://api.oireachtas.ie/v1/questions?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "FearTemperatureCoverageAudit/1.0 (research metadata)"})
    acquired = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            body = response.read()
            status = response.status
            final_url = response.url
            mime = response.headers.get("Content-Type", "")
            headers = dict(response.headers)
    except urllib.error.HTTPError as error:
        body = error.read()
        status = error.code
        final_url = error.url
        mime = error.headers.get("Content-Type", "")
        headers = dict(error.headers)
    digest = hashlib.sha256(body).hexdigest()
    (RAW / f"{year}.body").write_bytes(body)
    (RAW / f"{year}.request.json").write_text(
        json.dumps({"request_url": url, "final_url": final_url, "http_status": status,
                    "content_type": mime, "retrieved_at_utc": acquired, "sha256": digest,
                    "response_headers": headers}, indent=2) + "\n", encoding="utf-8"
    )
    count = None
    returned = None
    if status == 200 and "json" in mime.lower():
        parsed = json.loads(body)
        counts = parsed.get("head", {}).get("counts", {})
        count = counts.get("questionCount")
        returned = len(parsed.get("results", []))
    return {"source": "ie_oireachtas_questions", "year": year, "start": start, "end": end,
            "filter": "qtype=written; all departments", "unit": "question (not government answer)",
            "official_index_count": count, "response_rows": returned, "http_status": status,
            "content_type": mime, "request_url": url, "final_url": final_url,
            "retrieved_at_utc": acquired, "sha256": digest}


def main():
    path = HERE / "ie_written_question_year_index.csv"
    rows = []
    for year in range(2012, 2027):
        if year > 2012:
            time.sleep(1.2)
        row = fetch(year)
        rows.append(row)
        print(year, row["http_status"], row["official_index_count"], flush=True)
        if row["http_status"] in (403, 429) or row["http_status"] >= 500:
            break
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
