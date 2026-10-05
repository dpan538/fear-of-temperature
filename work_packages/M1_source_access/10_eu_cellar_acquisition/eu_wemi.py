"""Checkpoint official English WEMI/Item links for enumerated CELLAR Works.

The CSV is relationship evidence, not a claim that every Item is full text.
"""
import argparse
import csv
import hashlib
import io
import json
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode

import requests

from eu_acquire import ENDPOINT, HERE, HEADERS, sha

BATCH = 50


def retry_not_before(meta):
    value = meta.get("response_headers", {}).get("Retry-After", "")
    if not value:
        return ""
    if value.isdigit():
        base = parsedate_to_datetime(meta["response_headers"]["Date"]) if meta["response_headers"].get("Date") else datetime.fromisoformat(meta["retrieved_at_utc"])
        return (base + timedelta(seconds=int(value))).astimezone(timezone.utc).isoformat()
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except Exception:
        return ""


def fetch(month, n, works):
    values = " ".join(f"<{work}>" for work in works)
    query = f'''PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?work ?expr ?manif ?format ?item WHERE {{
 VALUES ?work {{ {values} }}
 ?expr cdm:expression_belongs_to_work ?work ;
       cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
 ?manif cdm:manifestation_manifests_expression ?expr .
 OPTIONAL {{ ?manif cdm:manifestation_type ?format . }}
 ?item cdm:item_belongs_to_manifestation ?manif .
}} ORDER BY ?work ?expr ?manif ?item'''
    url = ENDPOINT + "?" + urlencode({"query": query, "format": "text/csv"})
    path = HERE / "raw" / "wemi_pages" / month[:4] / f"{month}_batch_{n:04d}.csv"
    meta_path = path.with_suffix(".request.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("status") == "downloaded" and sha(path.read_bytes()) == meta.get("sha256"):
            return path.read_bytes(), meta
        if meta.get("retry_not_before_utc") and datetime.now(timezone.utc) < datetime.fromisoformat(meta["retry_not_before_utc"]):
            return b"", {**meta, "error": "retry_after_not_elapsed"}
        if not meta.get("retry_not_before_utc") and retry_not_before(meta) and datetime.now(timezone.utc) < datetime.fromisoformat(retry_not_before(meta)):
            return b"", {**meta, "error": "retry_after_not_elapsed"}
    path.parent.mkdir(parents=True, exist_ok=True)
    status, final, mime, body, error, headers = 0, url, "", b"", "", {}
    try:
        with requests.get(url, headers=HEADERS, timeout=120, stream=True) as response:
            status, final, mime = response.status_code, response.url, response.headers.get("Content-Type", "")
            headers = {k: v for k, v in response.headers.items() if k.lower() in {"retry-after", "date", "content-length", "etag"}}
            chunks, total = [], 0
            for chunk in response.iter_content(65536):
                total += len(chunk)
                if total > 10_000_000:
                    error = "response_exceeds_10MB_cap"
                    break
                chunks.append(chunk)
            body = b"".join(chunks)
    except requests.RequestException as exc:
        error = f"{type(exc).__name__}: {str(exc)[:240]}"
    valid = status == 200 and "csv" in mime.lower() and not error
    if valid:
        path.write_bytes(body)
    elif body:
        path.with_suffix(".error.body").write_bytes(body[:8192])
    meta = {"request_url": url, "final_url": final, "http_status": status,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "mime_type": mime,
            "byte_count": len(body), "sha256": sha(body) if body else "",
            "raw_path": str(path.relative_to(HERE)) if valid else "",
            "status": "downloaded" if valid else "failed", "error": error or ("unexpected_status_or_mime" if not valid else ""),
            "response_headers": headers, "requested_works": works}
    meta["retry_not_before_utc"] = retry_not_before(meta)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return body, meta


def harvest_month(month, delay):
    parent = HERE / "manifests" / "months" / f"{month}.csv"
    state = json.loads(parent.with_suffix(".json").read_text())
    if state["status"] != "reconciled":
        raise RuntimeError(f"month not reconciled: {month}")
    with parent.open(newline="", encoding="utf-8") as handle:
        works = sorted({row["work_uri"] for row in csv.DictReader(handle)})
    all_rows = []
    for n, start in enumerate(range(0, len(works), BATCH)):
        batch = works[start:start+BATCH]
        body, meta = fetch(month, n, batch)
        if meta["status"] != "downloaded":
            print(json.dumps({"month": month, "batch": n, "status": "request_failed", "error": meta["error"], "http_status": meta["http_status"]}), flush=True)
            return False
        rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
        if rows and not {"work", "expr", "manif", "format", "item"} <= set(rows[0]):
            raise ValueError("unexpected WEMI columns")
        for row in rows:
            if row["work"] not in batch or not row["item"].startswith("http://publications.europa.eu/resource/"):
                raise ValueError("unexpected Work/Item in WEMI response")
            row["source_page"] = str((HERE / "raw" / "wemi_pages" / month[:4] / f"{month}_batch_{n:04d}.csv").relative_to(HERE))
        all_rows.extend(rows)
        print(month, n, len(batch), len(rows), flush=True)
        time.sleep(delay)
    out = HERE / "manifests" / "wemi" / f"{month}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["work", "expr", "manif", "format", "item", "source_page"])
        writer.writeheader()
        writer.writerows(all_rows)
    linked = {r["work"] for r in all_rows}
    summary = {"year_month": month, "enumerated_works": len(works), "works_with_items": len(linked),
               "works_without_items": len(works)-len(linked), "item_relationship_rows": len(all_rows),
               "batches": (len(works)+BATCH-1)//BATCH, "status": "complete", "updated_at_utc": datetime.now(timezone.utc).isoformat()}
    out.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="1988-01")
    parser.add_argument("--end", default="2026-09")
    parser.add_argument("--limit-months", type=int, default=0)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    states = sorted((HERE / "manifests" / "months").glob("*.json"))
    months = [p.stem for p in states if args.start <= p.stem <= args.end and json.loads(p.read_text()).get("status") == "reconciled"]
    if args.limit_months:
        months = months[:args.limit_months]
    for month in months:
        summary = HERE / "manifests" / "wemi" / f"{month}.json"
        if summary.exists() and json.loads(summary.read_text()).get("status") == "complete":
            continue
        if not harvest_month(month, args.delay):
            break


if __name__ == "__main__":
    main()
