"""General DCCEEW landing/attachment route for the frozen 821 candidates.

Use only when the US supervisor is stopped; both commands that ingest write the
09 database. Unknown original dates and attachment roles remain unknown.
"""
import argparse
import csv
import json
import re
import time
from pathlib import Path

import duckdb
from bs4 import BeautifulSoup

from acquire import (AU_BATCH, AU_SOURCE, DB, HERE, ROOT, ensure_runs, insert_segments,
                     link_clean, rel, save_fetch, sha, sid, verified_meta)
from au_candidate_triage import KNOWN
from au_candidate_triage import OBSERVATIONS

ATTACHMENTS = HERE / "reports" / "au_attachment_candidates.csv"
OUTCOMES = HERE / "reports" / "au_candidate_outcomes.csv"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def file_path(url, extension):
    return HERE / "raw" / "au_files" / f"{sid('', url)}.{extension}"


def fetch_files(limit, delay):
    seen, attempted = set(), 0
    for row in read_csv(ATTACHMENTS):
        url = row["url"]
        if url in seen:
            continue
        seen.add(url)
        if attempted >= limit:
            break
        path = file_path(url, row["format"])
        if verified_meta(path):
            continue
        expected = {"pdf": "pdf", "docx": "docx", "rtf": "rtf"}[row["format"]]
        meta = save_fetch(url, path, expected=expected, timeout=40, max_bytes=100_000_000)
        attempted += 1
        print(attempted, meta["http_status"], meta["status"], url, flush=True)
        if meta["http_status"] in (0, 403, 429) or meta["error"] == "access_challenge":
            print("STOP: official Australian file host unavailable", flush=True)
            break
        time.sleep(delay)


def landing_segments(body):
    soup = BeautifulSoup(body, "html.parser")
    main = soup.find("main") or soup.find("article")
    if not main:
        return [], []
    raw = []
    for i, element in enumerate(main.find_all(["h1", "h2", "h3", "p", "li"]), 1):
        value = element.get_text(" ", strip=True)
        if value:
            raw.append((f"main:{element.name}[{i}]", value))
    cleaned = [(loc, re.sub(r"\s+", " ", value)) for loc, value in raw
               if len(value) >= 25 and not re.search(r"^(download|share|print|skip to|last updated)", value, re.I)]
    return raw, cleaned


def pdf_segments(body):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(body)
    raw, cleaned = [], []
    for page_no in range(len(pdf)):
        page = pdf[page_no]
        textpage = page.get_textpage()
        source = textpage.get_text_range() or ""
        locator = f"page={page_no+1}"
        if source.strip():
            raw.append((locator, source))
            normalized = re.sub(r"\s+", " ", source).strip()
            if len(normalized) >= 25 and not re.fullmatch(r"\d+", normalized):
                # PDF line wrapping does not establish independent paragraphs.
                cleaned.append((locator, normalized))
        textpage.close(); page.close()
    pdf.close()
    return raw, cleaned


def docx_segments(body):
    import io
    from docx import Document
    document = Document(io.BytesIO(body))
    raw = [(f"paragraph={i}", p.text.strip()) for i, p in enumerate(document.paragraphs, 1) if p.text.strip()]
    return raw, [(loc, re.sub(r"\s+", " ", val)) for loc, val in raw if len(val) >= 15]


def rtf_segments(body):
    from striprtf.striprtf import rtf_to_text
    text = rtf_to_text(body.decode("utf-8", "replace"))
    raw = [(f"paragraph={i}", value.strip()) for i, value in enumerate(text.splitlines(), 1) if value.strip()]
    return raw, [(loc, re.sub(r"\s+", " ", val)) for loc, val in raw if len(val) >= 15]


def ingest_one(c, did, oid, url, path, meta, raw, cleaned, role, known):
    digest = meta["sha256"]
    body = path.read_bytes()
    if sha(body) != digest or meta["http_status"] != 200:
        raise RuntimeError(f"saved byte/status mismatch: {path}")
    vid = sid("cntv", oid, digest)
    if c.execute("SELECT 1 FROM content_versions WHERE content_version_id=?", [vid]).fetchone():
        return False
    raw_run, clean_run = ensure_runs(c, AU_BATCH)
    c.execute("BEGIN")
    try:
        if role != "landing_page":
            c.execute("INSERT INTO content_objects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [oid, "attachment", None, url, meta["mime_type"], len(body), None, "public", "internal_only", "pending", url.rsplit("/", 1)[-1],
                       "downloaded", json.dumps({"role": role, "boundary": "verified_primary" if known else "unverified_attachment_candidate"})])
            c.execute("INSERT INTO document_content_objects VALUES (?,?,?,?) ON CONFLICT DO NOTHING", [did, oid, "attachment", 1])
        c.execute("INSERT INTO content_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                  [vid, oid, digest, meta["final_url"], meta["retrieved_at_utc"], 200, meta["mime_type"], len(body), rel(path), digest, sid("fet", AU_BATCH, oid), "verified"])
        c.execute("INSERT INTO us_au_fetch_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                  [oid, url, meta["final_url"], 200, meta["retrieved_at_utc"], meta["mime_type"], len(body), digest, rel(path), "downloaded", ""])
        raw_ids = insert_segments(c, vid, raw_run, "source_extracted", raw)
        clean_ids = insert_segments(c, vid, clean_run, "cleaned", cleaned)
        link_clean(c, raw_ids, clean_ids)
        c.execute("UPDATE content_objects SET acquisition_status='downloaded' WHERE content_object_id=?", [oid])
        if not known and role == "landing_page":
            c.execute("UPDATE documents SET body_status=?, body_status_reason=? WHERE document_id=?",
                      ["landing_summary_only", "Original issue date and independent Work/primary-file boundary pending", did])
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK")
        raise
    return True


def ingest_saved(limit):
    c = duckdb.connect(str(DB))
    done = 0
    browser = {r["landing_url"]: r for r in (json.loads(line) for line in OBSERVATIONS.read_text().splitlines() if line.strip())} if OBSERVATIONS.exists() else {}
    file_rows = read_csv(ATTACHMENTS) if ATTACHMENTS.exists() else []
    by_landing = {}
    for row in file_rows:
        by_landing.setdefault(row["landing_url"], []).append(row)
    for row in read_csv(OUTCOMES):
        if done >= limit:
            break
        url = row["landing_url"]
        did = sid("doc", AU_SOURCE, url)
        observation = browser.get(url)
        primary_saved = any(a["role_status"] == "verified_primary"
                            and verified_meta(file_path(a["url"], a["format"]))
                            for a in by_landing.get(url, []))
        if observation and primary_saved:
            scope_review = bool(observation.get("scope_status"))
            date_verified = observation.get("date_precision") in {"day", "month"}
            c.execute("UPDATE us_au_record_evidence SET date_value=?, date_precision=?, original_publisher=?, attachment_role_status='primary_pdf_evidenced', source_status=? WHERE document_id=?",
                      [observation["original_date"], observation["date_precision"], observation["original_publisher"],
                       "original_verified_issuer_review" if scope_review else "source_files_verified_date_pending" if not date_verified else "original_verified", did])
            if observation["date_precision"] == "day":
                c.execute("UPDATE documents SET publication_date=?, publication_date_basis=? WHERE document_id=?",
                          [observation["original_date"], observation["date_evidence"], did])
        path = HERE / "raw" / "au_landing" / (sid("", url) + ".html")
        meta = verified_meta(path)
        if meta:
            raw, cleaned = landing_segments(path.read_bytes())
            if ingest_one(c, did, sid("obj", "au_landing", url), url, path, meta, raw, cleaned, "landing_page", url in KNOWN):
                done += 1
        for attachment in by_landing.get(url, []):
            if done >= limit:
                break
            file_url = attachment["url"]
            file = file_path(file_url, attachment["format"])
            meta = verified_meta(file)
            if not meta:
                continue
            try:
                extractor = {"pdf": pdf_segments, "docx": docx_segments, "rtf": rtf_segments}[attachment["format"]]
                raw, cleaned = extractor(file.read_bytes())
            except Exception as exc:
                print("EXTRACTION_EXCEPTION", file_url, repr(exc), flush=True)
                raw = cleaned = []
            primary = attachment["role_status"] == "verified_primary"
            oid = sid("obj", "au_primary_pdf" if primary else "au_attachment", file_url)
            if ingest_one(c, did, oid, file_url, file, meta, raw, cleaned,
                          "primary_pdf" if primary else "attachment_candidate", primary):
                done += 1
            if primary and observation:
                scope_review = bool(observation.get("scope_status"))
                date_verified = observation.get("date_precision") in {"day", "month"}
                c.execute("UPDATE documents SET body_status=?, body_status_reason=? WHERE document_id=?",
                          ["source_extracted_scope_review" if scope_review else "source_extracted_date_unverified" if not date_verified else "source_extracted_and_cleaned" if cleaned else "source_downloaded_no_text",
                           observation["date_evidence"] + ("; original issuer differs from DCCEEW predecessor scope" if scope_review else ""), did])
    c.close()
    print("AU generic saved versions ingested", done, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["fetch-files", "ingest-saved"])
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    if args.action == "fetch-files":
        fetch_files(args.limit, args.delay)
    else:
        ingest_saved(args.limit)


if __name__ == "__main__":
    main()
