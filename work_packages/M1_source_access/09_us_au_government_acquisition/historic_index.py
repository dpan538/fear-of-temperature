"""Acquire and inspect the separate 1988-1993 official FR annual indexes."""
import argparse
import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "us_fr_annual_index"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def path_for(year):
    return RAW / f"GPO-FR-INDEX-{year}.pdf"


def fetch(year):
    RAW.mkdir(parents=True, exist_ok=True)
    path = path_for(year)
    meta_path = path.with_suffix(".request.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("status") == "downloaded" and hashlib.sha256(path.read_bytes()).hexdigest() == meta.get("sha256"):
            print(json.dumps({"year": year, "state": "verified_existing", "bytes": path.stat().st_size}))
            return
    url = f"https://www.govinfo.gov/content/pkg/GPO-FR-INDEX-{year}/pdf/GPO-FR-INDEX-{year}.pdf"
    part = path.with_suffix(".part")
    digest, size, status, final, mime, error, headers = hashlib.sha256(), 0, 0, url, "", "", {}
    try:
        with requests.get(url, timeout=(10, 60), stream=True,
                          headers={"User-Agent": "FearTemperatureResearch/1.0 (historical official index)"}) as response:
            status, final, mime = response.status_code, response.url, response.headers.get("Content-Type", "")
            headers = {k: v for k, v in response.headers.items() if k.lower() in {"date", "last-modified", "content-length", "etag"}}
            if status == 200 and "pdf" in mime.lower():
                with part.open("wb") as handle:
                    for chunk in response.iter_content(1024 * 1024):
                        size += len(chunk)
                        if size > 200_000_000:
                            raise ValueError("index exceeds 200 MB cap")
                        digest.update(chunk)
                        handle.write(chunk)
                if not part.open("rb").read(5).startswith(b"%PDF-"):
                    raise ValueError("download does not begin with PDF header")
                os.replace(part, path)
            else:
                error = "unexpected_status_or_mime"
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:240]}"
    if part.exists():
        part.unlink()
    meta = {"request_url": url, "final_url": final, "http_status": status, "retrieved_at_utc": stamp(),
            "mime_type": mime, "byte_count": size, "sha256": digest.hexdigest() if size else "",
            "raw_path": str(path.relative_to(HERE)) if path.exists() else "",
            "status": "downloaded" if path.exists() and not error else "failed", "error": error,
            "response_headers": headers}
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"year": year, "status": meta["status"], "bytes": size, "error": error}), flush=True)


def inspect(year):
    import pypdfium2 as pdfium
    path = path_for(year)
    doc = pdfium.PdfDocument(str(path))
    head = []
    matched = []
    for i in range(len(doc)):
        page = doc[i]
        textpage = page.get_textpage()
        text = textpage.get_text_range() or ""
        textpage.close(); page.close()
        if i < 5:
            head.append({"page": i + 1, "characters": len(text), "sample": text[:300]})
        lowered = text.lower()
        if "environmental protection agency" in lowered or "department of energy" in lowered or "energy department" in lowered:
            matched.append({"page": i + 1, "characters": len(text),
                            "epa": "environmental protection agency" in lowered,
                            "doe": "department of energy" in lowered or "energy department" in lowered})
    result = {"year": year, "pdf_pages": len(doc), "first_pages": head, "agency_match_pages": matched,
              "text_characters_first_five": sum(x["characters"] for x in head), "inspected_at_utc": stamp()}
    doc.close()
    out = RAW / f"GPO-FR-INDEX-{year}.inspection.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ["year", "pdf_pages", "text_characters_first_five", "agency_match_pages"]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["fetch", "inspect", "fetch-range"])
    parser.add_argument("--year", type=int, choices=range(1988, 1994))
    parser.add_argument("--start-year", type=int, default=1988)
    parser.add_argument("--end-year", type=int, default=1993)
    args = parser.parse_args()
    if args.action == "fetch-range":
        for year in range(args.start_year, args.end_year + 1):
            if shutil.disk_usage(HERE).free < 5_000_000_000:
                print("STOP: less than 5 GB free", flush=True)
                break
            fetch(year)
            meta = json.loads(path_for(year).with_suffix(".request.json").read_text())
            if meta["status"] != "downloaded":
                break
            time.sleep(2)
    else:
        if args.year is None:
            parser.error("--year is required for fetch or inspect")
        (fetch if args.action == "fetch" else inspect)(args.year)


if __name__ == "__main__":
    main()
