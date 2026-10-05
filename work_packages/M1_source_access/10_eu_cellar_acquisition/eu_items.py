"""Acquire one candidate English digital Item per CELLAR Work, with byte evidence.

Item availability and extractability are outcomes, not assumptions about body
usability. The complete WEMI relationship CSV remains the alternative ledger.
"""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

from eu_acquire import HERE, sha

PREF = {"pdfa1b": 0, "pdfa1a": 1, "pdf": 2, "pdf1x": 3,
        "html": 4, "xhtml": 5, "docx": 6, "xml": 7}
HEADERS = {"User-Agent": "FearTemperatureResearch/1.0 (public academic source acquisition)", "Accept": "*/*"}
OVERRIDES = HERE / "manifests" / "item_selection_overrides.json"
MIN_FREE_BYTES = 15_000_000_000  # Item bytes, extraction/OCR temp files and stage growth.


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def selected(month):
    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    parent = read_csv(HERE / "manifests" / "months" / f"{month}.csv")
    dates = defaultdict(set)
    for row in parent:
        dates[row["work_uri"]].add(row["date_observed"])
    wemi = read_csv(HERE / "manifests" / "wemi" / f"{month}.csv")
    by_work = defaultdict(list)
    for row in wemi:
        by_work[row["work"]].append(row)
    choices = []
    for work in sorted(dates):
        rows = sorted(by_work[work], key=lambda r: (PREF.get(r["format"].lower(), 100), r["item"]))
        override = overrides.get(work)
        if override:
            chosen = [r for r in rows if r["item"] == override["item_uri"]]
            if len(chosen) != 1:
                raise ValueError(f"selection override does not match one WEMI Item: {work}")
            rows = chosen + [r for r in rows if r["item"] != override["item_uri"]]
        if rows:
            row = rows[0]
            choices.append({"year_month": month, "work_uri": work, "document_dates": ";".join(sorted(dates[work])),
                            "expression_uri": row["expr"], "manifestation_uri": row["manif"],
                            "format": row["format"], "item_uri": row["item"],
                            "item_alternatives": len(rows), "selection_status": "alternative_after_oversize" if override else "candidate_item_not_yet_body_verified"})
        else:
            choices.append({"year_month": month, "work_uri": work, "document_dates": ";".join(sorted(dates[work])),
                            "expression_uri": "", "manifestation_uri": "", "format": "", "item_uri": "",
                            "item_alternatives": 0, "selection_status": "no_english_digital_item_link"})
    return choices


def path_for(uri):
    digest = hashlib.sha256(uri.encode()).hexdigest()
    local = HERE / "raw" / "items" / digest[:2] / f"{digest}.bin"
    if local.exists() or local.with_suffix(".request.json").exists():
        return local
    # When an approved external store is attached through this repository
    # symlink, put only new Items there. Older local checkpoints stay stable.
    external_link = HERE / "raw" / "items_external"
    if external_link.is_symlink():
        return external_link / digest[:2] / f"{digest}.bin"
    return local


def fetch(row):
    uri = row["item_uri"]
    path = path_for(uri)
    meta_path = path.with_suffix(".request.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("status") == "downloaded" and sha(path.read_bytes()) == meta.get("sha256"):
            return meta
    elif meta_path.exists():
        meta = json.loads(meta_path.read_text())
        retry = meta.get("retry_not_before_utc", "")
        if retry and datetime.now(timezone.utc) < datetime.fromisoformat(retry):
            return {**meta, "error": "retry_after_not_elapsed"}
    if min(shutil.disk_usage(HERE).free, shutil.disk_usage(path.parent.parent).free) < MIN_FREE_BYTES:
        raise RuntimeError("less than 15GB free on EU stage or Item storage volume")
    url = uri.replace("http://", "https://", 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    status, final, mime, size, error, headers = 0, url, "", 0, "", {}
    digest = hashlib.sha256()
    try:
        with requests.get(url, headers=HEADERS, timeout=(15, 90), stream=True) as response:
            status, final, mime = response.status_code, response.url, response.headers.get("Content-Type", "")
            headers = {k: v for k, v in response.headers.items() if k.lower() in {"retry-after", "date", "content-length", "etag", "content-disposition"}}
            if status == 200:
                with part.open("wb") as handle:
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > 100_000_000:
                            raise ValueError("Item exceeds 100MB cap")
                        digest.update(chunk)
                        handle.write(chunk)
                prefix = part.open("rb").read(4096).lstrip(b"\xef\xbb\xbf \t\r\n").lower()
                fmt = row["format"].lower()
                if "pdf" in fmt:
                    valid = prefix.startswith(b"%pdf-")
                elif fmt in ("html", "xhtml"):
                    valid = b"<html" in prefix or b"<xhtml" in prefix
                elif fmt == "doc":
                    valid = prefix.startswith(b"\xd0\xcf\x11\xe0")
                else:
                    valid = size > 0
                if not valid:
                    error = "unexpected_file_signature"
                else:
                    part.replace(path)
            else:
                error = "unexpected_http_status"
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:240]}"
    if part.exists():
        part.unlink()
    meta = {"request_url": url, "item_uri": uri, "work_uri": row["work_uri"],
            "expression_uri": row["expression_uri"], "manifestation_uri": row["manifestation_uri"],
            "document_dates": row["document_dates"], "format": row["format"], "final_url": final,
            "http_status": status, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "mime_type": mime, "byte_count": size, "sha256": digest.hexdigest() if size else "",
            "raw_path": str(path.relative_to(HERE)) if path.exists() and not error else "",
            "status": "downloaded" if path.exists() and not error else "failed", "error": error,
            "response_headers": headers}
    retry_after = headers.get("Retry-After", "")
    if retry_after:
        try:
            base = parsedate_to_datetime(headers["Date"]) if headers.get("Date") else datetime.fromisoformat(meta["retrieved_at_utc"])
            until = base + timedelta(seconds=int(retry_after)) if retry_after.isdigit() else parsedate_to_datetime(retry_after)
            meta["retry_not_before_utc"] = until.astimezone(timezone.utc).isoformat()
        except Exception:
            meta["retry_not_before_utc"] = ""
    if meta_path.exists():
        prior = json.loads(meta_path.read_text())
        if prior.get("status") == "failed":
            with path.with_suffix(".attempts.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(prior, ensure_ascii=False) + "\n")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def extract_pdf(path):
    import pypdfium2 as pdfium
    document = pdfium.PdfDocument(str(path))
    lines = []
    for page_no in range(len(document)):
        page = document[page_no]
        textpage = page.get_textpage()
        text = textpage.get_text_range() or ""
        if text.strip():
            lines.append(f"\fPAGE={page_no+1}\n{text}")
        textpage.close(); page.close()
    pages = len(document)
    document.close()
    return pages, "\n".join(lines)


def extract_html(path):
    """Keep source block order and a reproducible locator within the saved HTML."""
    from bs4 import BeautifulSoup, NavigableString, Tag

    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    root = soup.body or soup
    for tag in root(["script", "style", "noscript"]):
        tag.decompose()
    block_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "pre", "blockquote"}
    selected = {id(tag) for tag in root.find_all(block_tags) if not tag.find(block_tags)}
    blocks = []
    loose = []

    def add(source, kind):
        cleaned = " ".join(source.split())
        if cleaned:
            blocks.append({"block_no": len(blocks) + 1,
                           "source_locator": f"html_block_{len(blocks)+1:06d}:{kind}",
                           "source_text": source, "cleaned_text": cleaned})

    def flush_loose():
        if loose:
            add(" ".join(loose), "loose")
            loose.clear()

    for node in root.descendants:
        if isinstance(node, Tag) and id(node) in selected:
            flush_loose()
            add(node.get_text(" ", strip=False), node.name)
        elif isinstance(node, NavigableString) and not any(id(parent) in selected for parent in node.parents):
            loose.append(str(node))
    flush_loose()
    if not blocks:
        source = root.get_text(" ", strip=False)
        cleaned = " ".join(source.split())
        if cleaned:
            blocks.append({"block_no": 1, "source_locator": "html_block_000001:body",
                           "source_text": source, "cleaned_text": cleaned})
    return blocks


def extract_doc(path):
    """Extract text paragraphs from a saved OLE Word original via macOS textutil."""
    import re

    with tempfile.TemporaryDirectory() as directory:
        named = Path(directory) / "source.doc"
        shutil.copyfile(path, named)
        result = subprocess.run(["/usr/bin/textutil", "-convert", "txt", "-stdout", str(named)],
                                capture_output=True, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError(f"textutil exited {result.returncode}: {result.stderr[:200]!r}")
    source = result.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    blocks = []
    for section_no, section in enumerate(source.split("\f"), 1):
        section_block = 0
        for paragraph in re.split(r"\n\s*\n+", section):
            buffer = ""
            for line in paragraph.splitlines(keepends=True):
                if buffer and len(buffer) + len(line) > 4000:
                    cleaned = " ".join(buffer.split())
                    if cleaned:
                        section_block += 1
                        blocks.append({"block_no": len(blocks)+1,
                                       "source_locator": f"doc_textutil_section_{section_no:04d}_block_{section_block:04d}",
                                       "source_text": buffer, "cleaned_text": cleaned})
                    buffer = ""
                buffer += line
            cleaned = " ".join(buffer.split())
            if cleaned:
                section_block += 1
                blocks.append({"block_no": len(blocks)+1,
                               "source_locator": f"doc_textutil_section_{section_no:04d}_block_{section_block:04d}",
                               "source_text": buffer, "cleaned_text": cleaned})
    return blocks, source


def run(start, end, limit, delay):
    months = sorted(p.stem for p in (HERE / "manifests" / "wemi").glob("*.json") if start <= p.stem <= end)
    attempted = 0
    for month in months:
        manifest = HERE / "manifests" / "item_choices" / f"{month}.csv"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        choices = selected(month)
        with manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(choices[0])); writer.writeheader(); writer.writerows(choices)
        for row in choices:
            if not row["item_uri"]:
                continue
            path = path_for(row["item_uri"])
            already = path.exists() and path.with_suffix(".request.json").exists()
            if attempted >= limit and not already:
                return
            meta = fetch(row)
            if not already:
                attempted += 1
            outcome = {"month": month, "work": row["work_uri"], "status": meta["status"],
                       "http_status": meta["http_status"], "bytes": meta["byte_count"], "error": meta["error"]}
            if meta["status"] == "downloaded" and ("pdf" in row["format"].lower() or row["format"].lower() in ("html", "xhtml", "doc")):
                extract_meta = path.with_suffix(".extract.json")
                fmt = row["format"].lower()
                is_pdf = "pdf" in fmt
                text_path = path.with_suffix(".pages.txt") if is_pdf else path.with_suffix(".blocks.jsonl")
                if not text_path.exists() or not extract_meta.exists():
                    try:
                        if is_pdf:
                            pages, text = extract_pdf(path)
                            text_path.write_text(text)
                            evidence = {"raw_sha256": meta["sha256"], "pdf_pages": pages,
                                        "text_characters": len(text), "status": "text_extracted" if text.strip() else "scanned_or_empty_text_layer"}
                        else:
                            if fmt in ("html", "xhtml"):
                                blocks = extract_html(path)
                                textutil_source = ""
                            else:
                                blocks, textutil_source = extract_doc(path)
                                path.with_suffix(".source.txt").write_text(textutil_source, encoding="utf-8")
                            text_path.write_text("".join(json.dumps(block, ensure_ascii=False) + "\n" for block in blocks))
                            evidence = {"raw_sha256": meta["sha256"], "source_blocks": len(blocks),
                                        "locator_kind": "html_block" if fmt in ("html", "xhtml") else "doc_textutil_section_block",
                                        "text_characters": sum(len(b["source_text"]) for b in blocks),
                                        "status": "text_extracted" if blocks else "empty_text_body"}
                            if fmt == "doc":
                                evidence["textutil_source_sha256"] = sha(textutil_source.encode("utf-8"))
                                evidence["textutil_source_path"] = str(path.with_suffix(".source.txt").relative_to(HERE))
                        extract_meta.write_text(json.dumps(evidence, indent=2) + "\n")
                    except Exception as exc:
                        extract_meta.write_text(json.dumps({"raw_sha256": meta["sha256"], "status": "extraction_failed", "error": repr(exc)}) + "\n")
                outcome["extraction"] = json.loads(extract_meta.read_text())["status"]
            print(json.dumps(outcome), flush=True)
            if meta["http_status"] in (403, 429, 503) or meta["http_status"] == 0 or meta["error"] == "retry_after_not_elapsed":
                print("STOP: official Item access limit or transport failure", flush=True)
                return
            if not already:
                time.sleep(delay)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="1988-01")
    parser.add_argument("--end", default="2026-09")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    run(args.start, args.end, args.limit, args.delay)


if __name__ == "__main__":
    main()
