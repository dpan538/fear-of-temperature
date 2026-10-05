"""Bounded record-level enumeration of one Oireachtas written-Q month.

Question, answer, House and addressed-minister metadata remain distinct. This
is an evidence pilot, not a claim that all Irish government replies are covered.
"""

import csv
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
RAW = HERE / "evidence" / "ireland_2012_09_questions_with_answers"
RAW.mkdir(parents=True, exist_ok=True)
RECORDS = HERE / "ie_2012_09_question_answer_records.csv"
SUMMARY = HERE / "ie_2012_09_response_summary.csv"
FIELDS = ("question_uri", "question_date", "house_code", "questioner", "addressed_minister_label",
          "answer_text_present", "answer_prefix", "answer_date_independent", "debate_section_xml_url",
          "raw_page", "record_boundary")


def fetch(skip, limit=500):
    key = f"skip_{skip:05d}"
    cached_body, cached_meta = RAW / f"{key}.body", RAW / f"{key}.request.json"
    if cached_body.exists() and cached_meta.exists():
        meta = json.loads(cached_meta.read_text())
        body = cached_body.read_bytes()
        if meta["http_status"] == 200 and hashlib.sha256(body).hexdigest() == meta["sha256"]:
            return json.loads(body), 200, meta["response_headers"], key
    params = {"date_start": "2012-09-01", "date_end": "2012-09-30", "qtype": "written",
              "show_answers": "true", "skip": str(skip), "limit": str(limit)}
    url = "https://api.oireachtas.ie/v1/questions?" + urllib.parse.urlencode(params)
    stamp = datetime.now(timezone.utc).isoformat()
    req = urllib.request.Request(url, headers={"User-Agent": "FearTemperatureCoverageAudit/1.0 (research metadata)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body, status, final, mime, headers = response.read(), response.status, response.url, response.headers.get("Content-Type", ""), dict(response.headers)
    except urllib.error.HTTPError as error:
        body, status, final, mime, headers = error.read(), error.code, error.url, error.headers.get("Content-Type", ""), dict(error.headers)
    except Exception as error:
        body, status, final, mime, headers = repr(error).encode(), 0, url, "error/transport", {}
    (RAW / f"{key}.body").write_bytes(body)
    (RAW / f"{key}.request.json").write_text(json.dumps({"request_url": url, "final_url": final,
        "http_status": status, "retrieved_at_utc": stamp, "content_type": mime,
        "sha256": hashlib.sha256(body).hexdigest(), "response_headers": headers}, indent=2) + "\n")
    return json.loads(body) if status == 200 and "json" in mime.lower() else None, status, headers, key


def main():
    records = []
    expected = 3171  # verified from the prior official month index; assert again.
    for skip in range(0, expected, 500):
        if skip:
            time.sleep(1.5)
        data, status, headers, key = fetch(skip)
        print(skip, status, len(data.get("results", [])) if data else "no JSON", flush=True)
        if data is None:
            break
        count = data.get("head", {}).get("counts", {}).get("questionCount")
        if count is not None and int(count) != expected:
            raise ValueError(f"Official count changed: {count}, baseline {expected}")
        for item in data.get("results", []):
            question = item.get("question") or {}
            answer = question.get("answerText") or ""
            debate = question.get("debateSection") or {}
            formats = debate.get("formats") or {}
            xml = formats.get("xml") or {}
            records.append({"question_uri": question.get("uri", ""),
                "question_date": question.get("date", ""),
                "house_code": (question.get("house") or {}).get("houseCode", ""),
                "questioner": (question.get("by") or {}).get("showAs", ""),
                "addressed_minister_label": (question.get("to") or {}).get("showAs", ""),
                "answer_text_present": bool(answer.strip()), "answer_prefix": answer.strip()[:160],
                "answer_date_independent": "not supplied by /questions result",
                "debate_section_xml_url": xml.get("uri", ""), "raw_page": key,
                "record_boundary": "MP question URI; answer linked field, not separately dated"})
        if len(data.get("results", [])) < 500:
            break
    with RECORDS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader(); writer.writerows(records)
    exact = len(records) == expected and len({r["question_uri"] for r in records}) == expected
    # The API's `to.showAs` abbreviates these portfolios; sample question and
    # answer text confirms the full titles in the frozen month.
    target_labels = {"Environment", "Communications"}
    target = [r for r in records if r["addressed_minister_label"] in target_labels and r["house_code"] == "dail"]
    rows = [
        {"measure": "official_question_index", "count": expected, "unit": "all-house written questions in month", "status": "verified_month_index"},
        {"measure": "retrieved_unique_question_records", "count": len({r["question_uri"] for r in records}), "unit": "question URI", "status": "verified" if exact else "partial"},
        {"measure": "target_Dail_question_records", "count": len(target), "unit": "question URI addressed to two named minister portfolios", "status": "verified" if exact else "partial"},
        {"measure": "target_Dail_records_with_answer_field", "count": sum(r["answer_text_present"] for r in target), "unit": "question URI with nonempty answerText", "status": "verified" if exact else "partial"},
    ]
    with SUMMARY.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
    print(json.dumps({"retrieved": len(records), "unique": len({r['question_uri'] for r in records}),
                      "target_labels": dict(Counter(r["addressed_minister_label"] for r in target)),
                      "target_with_answer": sum(r["answer_text_present"] for r in target),
                      "complete": exact}, indent=2), flush=True)


if __name__ == "__main__":
    main()
