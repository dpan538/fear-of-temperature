"""Stage official GovInfo HTML originals for FederalRegister.gov raw-text 404s.

Fetch is read-only with respect to the live 09 DuckDB writer. The original
raw-text failure checkpoint is retained beside each target.
"""
import argparse
import json
import time
from pathlib import Path

import requests

from acquire import HERE, HEADERS, now, rel, sha, us_fallback_path, us_path, us_rows, verified_meta

CAP = 20_000_000


def candidates():
    for row in us_rows():
        raw = us_path(row)
        checkpoint = raw.with_suffix(raw.suffix + ".request.json")
        if raw.exists() or not checkpoint.exists():
            continue
        failure = json.loads(checkpoint.read_text())
        if failure.get("status") == "failed" and failure.get("http_status") in (404, 410):
            yield row, checkpoint


def path_for(row):
    return us_fallback_path(row)


def url_for(row):
    return (f"https://www.govinfo.gov/content/pkg/FR-{row['publication_date']}"
            f"/html/{row['document_number']}.htm")


def fetch(row, old_checkpoint):
    path = path_for(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = verified_meta(path)
    if existing:
        return existing
    url = url_for(row)
    status, final, mime, body, error, headers = 0, url, "", b"", "", {}
    try:
        with requests.get(url, headers=HEADERS, timeout=(15, 45), stream=True) as response:
            status, final, mime = response.status_code, response.url, response.headers.get("Content-Type", "")
            headers = {k: v for k, v in response.headers.items()
                       if k.lower() in {"date", "content-length", "etag", "last-modified", "retry-after"}}
            chunks = []
            length = 0
            for chunk in response.iter_content(65536):
                length += len(chunk)
                if length > CAP:
                    error = "response_exceeds_20mb_cap"
                    break
                chunks.append(chunk)
            body = b"".join(chunks)
    except requests.RequestException as exc:
        error = f"{type(exc).__name__}: {str(exc)[:240]}"
    prefix = body[:12000].lower()
    valid = (not error and status == 200 and len(body) > 200
             and b"federal register" in prefix
             and row["document_number"].encode().lower() in prefix
             and (b"<pre" in prefix or b"<html" in prefix)
             and b"request access" not in prefix)
    if valid:
        path.write_bytes(body)
    elif body:
        path.with_suffix(".error.body").write_bytes(body[:8192])
    meta = {"request_url": url, "final_url": final, "http_status": status,
            "retrieved_at_utc": now().isoformat(), "mime_type": mime,
            "byte_count": len(body), "sha256": sha(body) if body else "",
            "raw_path": rel(path) if valid else "", "status": "downloaded" if valid else "failed",
            "error": error or ("" if valid else "unexpected_body_or_status"),
            "response_headers": headers, "source_route": "official_govinfo_html_fallback",
            "federalregister_raw_text_failure_checkpoint": rel(old_checkpoint),
            "canonical_url": row["canonical_url"]}
    meta_path = path.with_suffix(path.suffix + ".request.json")
    if meta_path.exists():
        prior = json.loads(meta_path.read_text())
        if prior.get("status") == "failed":
            with path.with_suffix(path.suffix + ".attempts.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(prior, ensure_ascii=False) + "\n")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    attempted = 0
    transport_failures = 0
    for row, old in candidates():
        if verified_meta(path_for(row)):
            continue
        if attempted >= args.limit:
            break
        meta = fetch(row, old)
        attempted += 1
        transport_failures = transport_failures + 1 if meta["http_status"] == 0 else 0
        print(json.dumps({"date": row["publication_date"], "document_number": row["document_number"],
                          "status": meta["status"], "http_status": meta["http_status"],
                          "bytes": meta["byte_count"], "error": meta["error"]}), flush=True)
        if meta["http_status"] in (403, 429, 503) or transport_failures >= 3:
            print("STOP: official GovInfo access or transport limit", flush=True)
            break
        time.sleep(args.delay)


if __name__ == "__main__":
    main()
