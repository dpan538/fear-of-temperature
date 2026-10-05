"""Resumable US/AU official-source capture and append-only DuckDB ingestion.

Run from the repository root. The UK database is never opened for writing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import duckdb
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRE = HERE.parent / "08_cross_region_government_coverage"
DB = HERE / "fear_temperature_us_au_v1.duckdb"
US_CSV = PRE / "reports" / "us_fr_unique_documents.csv"
AU_CSV = PRE / "au_dcceew_catalogue_rows.csv"
US_SOURCE = "us_fr_epa_doe_rules_1994"
AU_SOURCE = "au_dcceew_current_catalogue_2026_snapshot"
US_BATCH = "us_fr_epa_doe_rules_1994_v1"
AU_BATCH = "au_dcceew_2026_snapshot_v1"
RAW_VERSION = "us_au_source_extract_v1"
RAW_VERSION_US_V2 = "us_fr_whole_source_extract_v2"
CLEAN_VERSION = "us_au_source_clean_v1"
HEADERS = {"User-Agent": "FearTemperatureResearch/1.0 (academic government-source capture)", "Accept": "*/*"}


def sid(prefix: str, *parts: object) -> str:
    return prefix + ":" + hashlib.sha256("\x1f".join(map(str, parts)).encode()).hexdigest()[:32]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> datetime:
    return datetime.now(timezone.utc)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def us_rows() -> list[dict[str, str]]:
    return rows(US_CSV)


def au_rows() -> list[dict[str, str]]:
    return list({r["landing_url"]: r for r in rows(AU_CSV)}.values())


def us_raw_url(row: dict[str, str]) -> str:
    date = row["publication_date"].replace("-", "/")
    return f"https://www.federalregister.gov/documents/full_text/text/{date}/{row['document_number']}.txt"


def us_path(row: dict[str, str]) -> Path:
    key = sid("", row["canonical_url"])
    return HERE / "raw" / "us_fr" / row["publication_date"][:4] / f"{row['publication_date']}_{row['document_number']}_{key}.txt"


def us_fallback_path(row: dict[str, str]) -> Path:
    key = sid("", row["canonical_url"])
    return HERE / "raw" / "us_fr_govinfo_html" / row["publication_date"][:4] / f"{row['publication_date']}_{row['document_number']}_{key}.htm"


def verified_meta(path: Path) -> dict | None:
    meta_path = path.with_suffix(path.suffix + ".request.json")
    if not (path.exists() and meta_path.exists()):
        return None
    meta = json.loads(meta_path.read_text())
    if meta.get("status") == "downloaded" and sha(path.read_bytes()) == meta.get("sha256"):
        return meta
    return None


def save_fetch(url: str, path: Path, *, expected: str, timeout: int = 25, max_bytes: int = 20_000_000) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = verified_meta(path)
    if existing:
        return existing
    started = now().isoformat()
    status, final, mime, body, error, headers = 0, url, "", b"", "", {}
    try:
        with requests.get(url, headers=HEADERS, timeout=timeout, stream=True, allow_redirects=True) as response:
            status, final, mime = response.status_code, response.url, response.headers.get("Content-Type", "")
            headers = {k: v for k, v in response.headers.items() if k.lower() in {"retry-after", "content-length", "last-modified", "etag", "date"}}
            chunks = []
            length = 0
            for chunk in response.iter_content(65536):
                length += len(chunk)
                if length > max_bytes:
                    error = f"response_exceeds_{max_bytes}_byte_cap"
                    break
                chunks.append(chunk)
            body = b"".join(chunks)
    except requests.RequestException as exc:
        error = f"{type(exc).__name__}: {str(exc)[:240]}"
    valid = False
    if expected == "us_text":
        valid = status == 200 and b"Federal Register" in body[:1500] and b"Request Access" not in body[:2000] and len(body) > 100
    elif expected == "au_html":
        valid = status == 200 and b"dcceew" in body.lower()[:3000] and b"<html" in body.lower()[:1000]
    elif expected == "pdf":
        valid = status == 200 and body.startswith(b"%PDF-")
    elif expected == "docx":
        valid = status == 200 and body.startswith(b"PK\x03\x04")
    elif expected == "rtf":
        valid = status == 200 and body.lstrip().startswith(b"{\\rtf")
    valid = valid and not error
    if valid:
        path.write_bytes(body)
    else:
        error = error or ("access_challenge" if b"Request Access" in body[:2000] else "unexpected_body_or_status")
        if body:
            path.with_suffix(path.suffix + ".error.body").write_bytes(body[:8192])
    meta = {"request_url": url, "final_url": final, "http_status": status, "retrieved_at_utc": started,
            "mime_type": mime, "byte_count": len(body), "sha256": sha(body) if body else "",
            "raw_path": rel(path) if valid else "", "status": "downloaded" if valid else "failed",
            "error": error, "response_headers": headers}
    meta_path = path.with_suffix(path.suffix + ".request.json")
    if meta_path.exists():
        prior = json.loads(meta_path.read_text())
        if prior.get("status") == "failed":
            with path.with_suffix(path.suffix + ".attempts.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(prior, ensure_ascii=False) + "\n")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return meta


def fetch_us(limit: int, start_year: int, end_year: int, delay: float) -> None:
    ordered = [r for r in us_rows() if start_year <= int(r["publication_date"][:4]) <= end_year]
    attempted = 0
    last = 0.0
    transport_failures = 0
    for row in ordered:
        path = us_path(row)
        if verified_meta(path):
            continue
        checkpoint = path.with_suffix(path.suffix + ".request.json")
        if checkpoint.exists():
            previous = json.loads(checkpoint.read_text())
            if previous.get("http_status") in (404, 410):
                # A documented absent raw-text object stays in the exception
                # ledger; move on to other parents rather than retrying it in
                # every supervised block.
                continue
        if attempted >= limit:
            break
        gap = delay - (time.monotonic() - last)
        if gap > 0:
            time.sleep(gap)
        meta = save_fetch(us_raw_url(row), path, expected="us_text")
        last = time.monotonic()
        attempted += 1
        transport_failures = transport_failures + 1 if meta["http_status"] == 0 else 0
        if attempted % 25 == 0 or meta["status"] != "downloaded":
            print(f"US fetch {attempted}/{limit} {row['publication_date']} {row['document_number']} {meta['http_status']} {meta['status']} {meta['error']}", flush=True)
        if meta["http_status"] in (403, 429) or transport_failures >= 3:
            print("STOP: access/transport limit; checkpoint retained", flush=True)
            break


def fetch_au(limit: int, delay: float) -> None:
    attempted = 0
    # CMS time sets request priority only; it never supplies original issue date.
    for row in sorted(au_rows(), key=lambda value: value["catalogue_created_at"]):
        path = HERE / "raw" / "au_landing" / (sid("", row["landing_url"]) + ".html")
        if verified_meta(path):
            continue
        if attempted >= limit:
            break
        meta = save_fetch(row["landing_url"], path, expected="au_html", timeout=20)
        attempted += 1
        print(f"AU fetch {attempted}/{limit} {meta['http_status']} {meta['status']} {meta['error']} {row['landing_url']}", flush=True)
        if meta["http_status"] in (0, 403, 429) or meta["error"] == "access_challenge":
            print("STOP: official host unavailable; checkpoint retained", flush=True)
            break
        time.sleep(delay)


def seed_db() -> None:
    """Legacy row-wise prototype; public CLI delegates to seed_bulk.py instead."""
    c = duckdb.connect(str(DB))
    c.execute("""CREATE TABLE IF NOT EXISTS us_au_record_evidence (
        document_id VARCHAR PRIMARY KEY, source_series VARCHAR NOT NULL, date_value VARCHAR,
        date_precision VARCHAR NOT NULL, original_publisher VARCHAR, cms_created_at VARCHAR,
        metadata_snapshot_path VARCHAR NOT NULL, raw_partition VARCHAR,
        attachment_role_status VARCHAR NOT NULL, source_status VARCHAR NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS us_au_fetch_evidence (
        content_object_id VARCHAR PRIMARY KEY, request_url VARCHAR NOT NULL, final_url VARCHAR,
        http_status INTEGER, retrieved_at TIMESTAMPTZ, mime_type VARCHAR, byte_count BIGINT,
        sha256 VARCHAR, raw_path VARCHAR, fetch_status VARCHAR NOT NULL, failure_reason VARCHAR NOT NULL)""")
    for source_id, name, coverage, entry in [
        (US_SOURCE, "Federal Register EPA/DOE RULE/PRORULE", "1994-01-01..2026-09-21; 33544 unique document URLs", "https://www.federalregister.gov/api/v1/documents.json"),
        (AU_SOURCE, "DCCEEW current publications listing", "2026-09-23 snapshot; 821 unique landing URL candidates; original dates unresolved", "https://www.dcceew.gov.au/about/publications")]:
        c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                  [source_id, name, "policy", "government publication record", "source-specific publication", "official public site/API", coverage,
                   "internal_only_rights_not_reassessed", "Source/item terms require review", "pending", "Project-authorised; no UQ institutional ethics approval/exemption asserted",
                   json.dumps([entry]), rel(HERE / "FILTER_CONTRACT.md")])
    for bid, source, url, start, count, path in [
        (US_BATCH, US_SOURCE, "https://www.federalregister.gov/api/v1/documents.json", "1994-01-01", 33544, US_CSV),
        (AU_BATCH, AU_SOURCE, "https://www.dcceew.gov.au/about/publications", "1988-01-01", 821, AU_CSV)]:
        c.execute("INSERT INTO collection_batches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                  [bid, source, now(), url, json.dumps({"contract": rel(HERE / "FILTER_CONTRACT.md")}), start, "2026-09-21",
                   "publication_date" if source == US_SOURCE else "original_issue_date_unknown", json.dumps({"US": "132 partitions", "AU": "83 pages"}), count, count,
                   "enumerated_metadata_only", "Body acquisition tracked separately", rel(path), sha(path.read_bytes()), rel(path), sha(path.read_bytes()), True])
    c.execute("BEGIN")
    try:
        us = us_rows()
        au = au_rows()
        for i, r in enumerate(us, 1):
            did = sid("doc", US_SOURCE, r["canonical_url"])
            c.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [did, US_SOURCE, r["canonical_url"], r["canonical_url"], r["title"], "en", r["publication_date"], None,
                       "Federal Register publication_date; day", None, now(), "policy", r["genre"], "document", None, "original", "not_requested", "Metadata enumerated; body pending", "canonical_URL_and_date", "cross_agency_deduplicated", "internal_only_rights_not_reassessed", "pending", "Project-authorised; no UQ institutional approval/exemption asserted", True])
            c.execute("INSERT INTO us_au_record_evidence VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [did, US_SOURCE, r["publication_date"], "day", r["agency_names_from_api"], None, rel(US_CSV), None, "format_links_pending", "enumerated"])
            oid = sid("obj", "us_fr_raw", r["canonical_url"])
            c.execute("INSERT INTO content_objects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [oid, "webpage", r["document_number"], us_raw_url(r), "text/plain", None, None, "public", "internal_only", "pending", r["title"], "not_attempted", json.dumps({"canonical_html_url": r["canonical_url"], "representation": "official raw-text route"})])
            c.execute("INSERT INTO document_content_objects VALUES (?,?,?,?) ON CONFLICT DO NOTHING", [did, oid, "landing_page", 0])
            for agency in r["agency_strata"].split(";"):
                orgid = sid("org", "us_fr", agency)
                c.execute("INSERT INTO organisations VALUES (?,?,?,?) ON CONFLICT DO NOTHING", [orgid, agency, "Environmental Protection Agency" if agency == "EPA" else "Energy Department", "https://www.federalregister.gov/agencies/" + ("environmental-protection-agency" if agency == "EPA" else "energy-department")])
                c.execute("INSERT INTO document_organisations VALUES (?,?,?,?,?,?,?) ON CONFLICT DO NOTHING", [did, orgid, "official_API_agency_hierarchy_stratum", "unknown", 1.0, 1.0 / len(r["agency_strata"].split(";")), "verified_partition_membership"])
            if i % 2000 == 0:
                print("US metadata seeded", i, flush=True)
        for i, r in enumerate(au, 1):
            did = sid("doc", AU_SOURCE, r["landing_url"])
            c.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [did, AU_SOURCE, r["landing_url"], r["landing_url"], r["title"], "en", None, None,
                       "Original date unresolved; CMS timestamp excluded", None, now(), "policy", "catalogue_publication_candidate", "document", None, "original", "not_requested", "Landing and primary-file boundary pending", "canonical_landing_URL_candidate", "original_work_identity_pending", "internal_only_rights_not_reassessed", "pending", "Project-authorised; no UQ institutional approval/exemption asserted", True])
            c.execute("INSERT INTO us_au_record_evidence VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [did, AU_SOURCE, None, "unknown", None, r["catalogue_created_at"], rel(AU_CSV), r["catalogue_page"], "primary_file_unknown", "catalogue_candidate"])
            oid = sid("obj", "au_landing", r["landing_url"])
            c.execute("INSERT INTO content_objects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [oid, "webpage", None, r["landing_url"], "text/html", None, None, "public", "internal_only", "pending", r["title"], "not_attempted", json.dumps({"role": "catalogue_landing", "original_date_unknown": True})])
            c.execute("INSERT INTO document_content_objects VALUES (?,?,?,?) ON CONFLICT DO NOTHING", [did, oid, "landing_page", 0])
            if i % 200 == 0:
                print("AU metadata seeded", i, flush=True)
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK")
        raise
    print("SEED COMPLETE", len(us), len(au), flush=True)
    c.close()


def source_text_us(body: bytes) -> str:
    text = body.decode("utf-8", "replace")
    if "<pre" in text[:3000].lower():
        text = BeautifulSoup(text, "html.parser").find("pre").get_text()
    return text


def source_lines_us(body: bytes) -> list[tuple[str, str]]:
    return [(f"line={i}", line.rstrip()) for i, line in enumerate(source_text_us(body).splitlines(), 1) if line.strip()]


def clean_us(lines: list[tuple[str, str]]) -> list[tuple[str, str]]:
    out = []
    buf, first, last = [], "", ""
    def flush():
        nonlocal buf, first, last
        if buf:
            value = re.sub(r"\s+", " ", " ".join(buf)).strip()
            if len(value) >= 12:
                out.append((first + ".." + last, value))
        buf, first, last = [], "", ""
    for locator, line in lines:
        value = line.strip()
        if re.match(r"^\[(?:Federal Register|FR Doc No|Page|Unknown Section)", value) or re.match(r"^\[\[Page", value):
            flush(); continue
        if value.startswith("From the Federal Register Online") or re.fullmatch(r"[=_-]{5,}", value):
            flush(); continue
        if not value:
            flush(); continue
        if not first: first = locator
        last = locator
        if buf and buf[-1].endswith("-") and re.match(r"^[a-z]", value):
            buf[-1] = buf[-1][:-1] + value
        else:
            buf.append(value)
        if value.endswith((".", ":", ";", "?", "!")) and len(" ".join(buf)) > 70:
            flush()
    flush()
    return out


def clean_rule_json() -> str:
    return json.dumps({"version": CLEAN_VERSION,
        "US_Federal_Register": {"remove": "FR boilerplate/page markers", "join": "line wraps and hyphenated word continuations", "min_chars": 12},
        "AU_DCCEEW": {"landing": "main headings/paragraphs/list items; cleaned excludes under-25-character and generic share/navigation lines",
                         "PDF": "source page lines retained; cleaned whitespace-normalized lines at least 15 characters; page-number-only lines removed"},
        "metadata_description_corrected": "2026-09-26; same extraction code and immutable segments retained"}, sort_keys=True)


def ensure_runs(c, batch: str) -> tuple[str, str]:
    c.execute("""CREATE TABLE IF NOT EXISTS us_au_clean_source_map (
        clean_segment_id VARCHAR NOT NULL REFERENCES text_segments(segment_id),
        source_segment_id VARCHAR NOT NULL REFERENCES text_segments(segment_id),
        mapping_rule VARCHAR NOT NULL,
        PRIMARY KEY(clean_segment_id, source_segment_id))""")
    rule = clean_rule_json()
    existing = c.execute("SELECT rule_sha256 FROM normalisation_rules WHERE rule_version=?", [CLEAN_VERSION]).fetchone()
    if existing and existing[0] != sha(rule.encode()):
        raise RuntimeError("Cleaning-rule metadata mismatch; run correct_clean_rule.py before ingestion")
    c.execute("INSERT INTO normalisation_rules VALUES (?,?,?,?) ON CONFLICT DO NOTHING", [CLEAN_VERSION, sha(rule.encode()), rule, "active"])
    ids = []
    raw_version = RAW_VERSION_US_V2 if batch == US_BATCH else RAW_VERSION
    for kind, version in [("source", raw_version), ("cleaned", CLEAN_VERSION)]:
        rid = sid("extr", batch, version)
        c.execute("INSERT INTO extraction_runs VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING", [rid, batch, version, now(), now(), 0, 0, "incremental", "Versioned source-specific extraction; counts in us_au progress report"])
        ids.append(rid)
    return ids[0], ids[1]


def insert_segments(c, vid: str, run_id: str, representation: str, values: list[tuple[str, str]]) -> dict[str, str]:
    import pandas as pd
    ids = {}
    records = []
    created = now()
    for i, (locator, value) in enumerate(values):
        digest = sha(value.encode())
        segid = sid("seg", vid, run_id, i, digest)
        records.append((segid, vid, run_id, None, representation, "paragraph", i, None, value, locator, None, None, digest,
                        "project_authorized_internal_use_institutional_ethics_not_asserted", True, created))
        ids[locator] = segid
    if records:
        frame = pd.DataFrame.from_records(records, columns=[r[1] for r in c.execute("PRAGMA table_info('text_segments')").fetchall()])
        c.register("_segment_batch", frame)
        try:
            c.execute("INSERT INTO text_segments SELECT * FROM _segment_batch ON CONFLICT DO NOTHING")
        finally:
            c.unregister("_segment_batch")
    return ids


def link_clean(c, raw_ids: dict[str, str], clean_ids: dict[str, str]) -> None:
    import pandas as pd
    links = []
    if "whole_document" in raw_ids:
        links = [(clean_id, raw_ids["whole_document"], "line_range_into_whole_source_v2") for clean_id in clean_ids.values()]
    else:
        for locator, clean_id in clean_ids.items():
            if ".." in locator and locator.startswith("line="):
                start, end = locator.split("..")
                candidates = (f"line={n}" for n in range(int(start[5:]), int(end[5:]) + 1))
            else:
                candidates = (locator,)
            for raw_locator in candidates:
                raw_id = raw_ids.get(raw_locator)
                if raw_id:
                    links.append((clean_id, raw_id, "exact_source_line_locator_v1"))
    if links:
        c.register("_clean_map_batch", pd.DataFrame.from_records(links, columns=["clean_segment_id", "source_segment_id", "mapping_rule"]))
        try:
            c.execute("INSERT INTO us_au_clean_source_map SELECT * FROM _clean_map_batch ON CONFLICT DO NOTHING")
        finally:
            c.unregister("_clean_map_batch")


def ingest_us(limit: int) -> None:
    c = duckdb.connect(str(DB))
    raw_run, clean_run = ensure_runs(c, US_BATCH)
    done = 0
    transaction_open = False
    for row in us_rows():
        path = us_path(row)
        meta = verified_meta(path)
        if not meta:
            path = us_fallback_path(row)
            meta = verified_meta(path)
        if not meta:
            continue
        oid = sid("obj", "us_fr_raw", row["canonical_url"])
        vid = sid("cntv", oid, meta["sha256"])
        if c.execute("SELECT 1 FROM content_versions WHERE content_version_id=?", [vid]).fetchone():
            continue
        if done >= limit:
            break
        body = path.read_bytes()
        source_lines = source_lines_us(body)
        source = [("whole_document", source_text_us(body))]
        cleaned = clean_us(source_lines)
        fetchid = sid("fet", US_BATCH, oid)
        if not transaction_open:
            c.execute("BEGIN")
            transaction_open = True
        try:
            c.execute("INSERT INTO content_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [vid, oid, meta["sha256"], meta["final_url"], meta["retrieved_at_utc"], meta["http_status"], meta["mime_type"], len(body), rel(path), meta["sha256"], fetchid, "verified"])
            c.execute("INSERT INTO us_au_fetch_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [oid, meta["request_url"], meta["final_url"], meta["http_status"], meta["retrieved_at_utc"], meta["mime_type"], len(body), meta["sha256"], rel(path), "downloaded", ""])
            raw_ids = insert_segments(c, vid, raw_run, "source_extracted", source)
            clean_ids = insert_segments(c, vid, clean_run, "cleaned", cleaned)
            link_clean(c, raw_ids, clean_ids)
            c.execute("UPDATE content_objects SET acquisition_status='downloaded' WHERE content_object_id=?", [oid])
            reason = ("Official GovInfo HTML fallback verified and versioned"
                      if path.suffix == ".htm" else "Official raw text verified and versioned")
            c.execute("UPDATE documents SET body_status='source_extracted_and_cleaned', body_status_reason=? WHERE canonical_url=?", [reason, row["canonical_url"]])
        except Exception:
            c.execute("ROLLBACK")
            transaction_open = False
            raise
        done += 1
        if done % 25 == 0:
            c.execute("COMMIT")
            transaction_open = False
            print("US ingested", done, "last", row["publication_date"], flush=True)
    if transaction_open:
        c.execute("COMMIT")
    print("US INGEST COMPLETE", done, flush=True)
    c.close()


def ingest_au_existing() -> None:
    c = duckdb.connect(str(DB))
    raw_run, clean_run = ensure_runs(c, AU_BATCH)
    evidence = rows(PRE / "au_primary_work_evidence.csv")
    manifest = {r["request_url"]: r for r in rows(PRE / "au_primary_originals_manifest.csv")}
    for r in evidence:
        landing = r["official_landing_url"]
        did = sid("doc", AU_SOURCE, landing)
        exists = c.execute("SELECT 1 FROM documents WHERE document_id=?", [did]).fetchone()
        if not exists:
            print("AU existing evidence outside 821 candidate list", landing, flush=True)
            continue
        date = r["original_issue_date"]
        precision = r["date_precision"]
        c.execute("UPDATE us_au_record_evidence SET date_value=?, date_precision=?, original_publisher=?, attachment_role_status='primary_pdf_evidenced', source_status='original_verified' WHERE document_id=?",
                  [date, precision, r["original_publisher"], did])
        if precision == "day":
            c.execute("UPDATE documents SET publication_date=?, publication_date_basis='original landing/PDF evidence; day' WHERE document_id=?", [date, did])
        landing_key = {"net-zero-plan":"au_net_zero_plan", "ncras-2021-25":"au_ncras_2021", "2015-ncras":"au_ncras_2015", "epbc-act-policy-statement-21-interaction-between-offshore-seismic-exploration-and-whales":"au_epbc_policy_2008"}.get(landing.rstrip("/").split("/")[-1])
        landing_body = PRE / "evidence" / "continued_official_probes" / f"{landing_key}.body" if landing_key else None
        if landing_body and landing_body.exists():
            from urllib.parse import urljoin
            soup = BeautifulSoup(landing_body.read_bytes(), "html.parser")
            main = soup.find("main")
            seen_urls = set()
            for ordinal, anchor in enumerate(main.find_all("a", href=True), 1):
                file_url = urljoin("https://www.dcceew.gov.au", anchor["href"])
                extension = file_url.lower().split("?")[0].rsplit(".", 1)[-1]
                if not file_url.startswith("https://www.dcceew.gov.au/sites/default/files/documents/") or extension not in {"pdf", "docx", "rtf"} or file_url in seen_urls:
                    continue
                seen_urls.add(file_url)
                file_role = "primary_pdf" if file_url == r["primary_pdf_url"] else "summary" if "summary" in file_url.lower() else "end_notes" if "end-notes" in file_url.lower() else "background_paper" if "background" in file_url.lower() else "alternate_format"
                file_oid = sid("obj", "au_primary_pdf" if file_role == "primary_pdf" else "au_attachment", file_url)
                identity = {"role": file_role, "work_id": r["work_id"], "edition": r["edition_or_version"],
                            "parent_original_relationship": r["parent_original_relationship"], "related_files_note": r["related_files"]}
                c.execute("INSERT INTO content_objects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                          [file_oid, "attachment", None, file_url, {"pdf":"application/pdf","docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document","rtf":"application/rtf"}[extension],
                           None, None, "public", "internal_only", "pending", anchor.get_text(" ", strip=True), "not_attempted", json.dumps(identity)])
                c.execute("UPDATE content_objects SET identity_metadata_json=? WHERE content_object_id=?", [json.dumps(identity), file_oid])
                c.execute("INSERT INTO document_content_objects VALUES (?,?,?,?) ON CONFLICT DO NOTHING", [did, file_oid, "attachment", ordinal])
        for role, url in [("landing_page", landing), ("attachment", r["primary_pdf_url"])]:
            if role == "landing_page":
                # Four verified landing responses have explicit names in 08.
                key = {"net-zero-plan":"au_net_zero_plan", "ncras-2021-25":"au_ncras_2021", "2015-ncras":"au_ncras_2015", "epbc-act-policy-statement-21-interaction-between-offshore-seismic-exploration-and-whales":"au_epbc_policy_2008"}.get(landing.rstrip("/").split("/")[-1])
                path = PRE / "evidence" / "continued_official_probes" / f"{key}.body" if key else None
                meta_path = PRE / "evidence" / "continued_official_probes" / f"{key}.request.json" if key else None
                if not path or not path.exists() or not meta_path.exists():
                    continue
                meta = json.loads(meta_path.read_text())
                digest = meta["sha256"]
                status = meta["status"]
                mime = meta["content_type"]
                stamp = meta["retrieved_at_utc"]
                final = meta["final_url"]
                source = []
                soup = BeautifulSoup(path.read_bytes(), "html.parser")
                main = soup.find("main") or soup.find("article")
                if main:
                    for i, el in enumerate(main.find_all(["h1", "h2", "h3", "p", "li"]), 1):
                        value = el.get_text(" ", strip=True)
                        if value: source.append((f"main:{el.name}[{i}]", value))
                cleaned = [(loc, val) for loc, val in source if len(val) >= 25 and not re.search(r"^(download|share|print|skip to|last updated)", val, re.I)]
                oid = sid("obj", "au_landing", landing)
            else:
                m = manifest.get(url)
                if not m:
                    continue
                path = PRE / m["local_path"]
                digest, status, mime, stamp, final = m["sha256"], int(m["http_status"]), m["content_type"], m["retrieved_at_utc"], m["final_url"]
                oid = sid("obj", "au_primary_pdf", url)
                c.execute("INSERT INTO content_objects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                          [oid, "attachment", None, url, "application/pdf", len(path.read_bytes()), None, "public", "internal_only", "pending", r["title"], "downloaded", json.dumps({"role": "primary_pdf", "work_id": r["work_id"], "edition": r["edition_or_version"]})])
                c.execute("INSERT INTO document_content_objects VALUES (?,?,?,?) ON CONFLICT DO NOTHING", [did, oid, "attachment", 1])
                try:
                    import pypdfium2 as pdfium
                    pdf = pdfium.PdfDocument(path.read_bytes())
                    source = []
                    for page_no in range(len(pdf)):
                        page = pdf[page_no]
                        textpage = page.get_textpage()
                        for line_no, line in enumerate((textpage.get_text_range() or "").splitlines(), 1):
                            if line.strip(): source.append((f"page={page_no+1};line={line_no}", line.strip()))
                        textpage.close(); page.close()
                    pdf.close()
                    cleaned = [(loc, re.sub(r"\s+", " ", val)) for loc, val in source if len(val.strip()) >= 15 and not re.fullmatch(r"\d+", val.strip())]
                except Exception as exc:
                    print("AU PDF extraction exception", url, repr(exc), flush=True)
                    source = cleaned = []
            body = path.read_bytes()
            if sha(body) != digest or not 200 <= int(status) < 300:
                raise RuntimeError(f"Hash/status mismatch {path}")
            vid = sid("cntv", oid, digest)
            if c.execute("SELECT 1 FROM content_versions WHERE content_version_id=?", [vid]).fetchone():
                continue
            fetchid = sid("fet", AU_BATCH, oid)
            c.execute("BEGIN")
            try:
                c.execute("INSERT INTO content_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                          [vid, oid, digest, final, stamp, int(status), mime, len(body), rel(path), digest, fetchid, "verified"])
                c.execute("INSERT INTO us_au_fetch_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                          [oid, url, final, int(status), stamp, mime, len(body), digest, rel(path), "downloaded", ""])
                raw_ids = insert_segments(c, vid, raw_run, "source_extracted", source)
                clean_ids = insert_segments(c, vid, clean_run, "cleaned", cleaned)
                link_clean(c, raw_ids, clean_ids)
                c.execute("UPDATE content_objects SET acquisition_status='downloaded' WHERE content_object_id=?", [oid])
                c.execute("UPDATE documents SET body_status='source_extracted_and_cleaned', body_status_reason='Verified current landing/primary original' WHERE document_id=?", [did])
                c.execute("COMMIT")
            except Exception:
                c.execute("ROLLBACK")
                raise
            print("AU ingested", role, r["work_id"], len(source), len(cleaned), flush=True)
    c.close()


def backfill_map() -> None:
    c = duckdb.connect(str(DB))
    ensure_runs(c, AU_BATCH)
    c.execute("""INSERT INTO us_au_clean_source_map
        SELECT clean.segment_id, raw.segment_id, 'exact_source_line_locator_v1'
        FROM text_segments clean JOIN text_segments raw
          ON clean.content_version_id=raw.content_version_id AND clean.locator=raw.locator
        WHERE clean.representation_kind='cleaned' AND raw.representation_kind='source_extracted'
          AND clean.extraction_run_id IN (SELECT extraction_run_id FROM extraction_runs WHERE batch_id=?)
        ON CONFLICT DO NOTHING""", [AU_BATCH])
    print("clean/source maps", c.execute("SELECT count(*) FROM us_au_clean_source_map").fetchone()[0], flush=True)
    c.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["seed-db", "fetch-us", "fetch-au", "ingest-us", "ingest-au-existing", "backfill-map"])
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--start-year", type=int, default=1994)
    p.add_argument("--end-year", type=int, default=2002)
    p.add_argument("--delay", type=float, default=1.0)
    a = p.parse_args()
    if a.command == "seed-db":
        from seed_bulk import main as seed_bulk_main
        seed_bulk_main()
    elif a.command == "fetch-us": fetch_us(a.limit, a.start_year, a.end_year, a.delay)
    elif a.command == "fetch-au": fetch_au(a.limit, a.delay)
    elif a.command == "ingest-us": ingest_us(a.limit)
    elif a.command == "ingest-au-existing": ingest_au_existing()
    elif a.command == "backfill-map": backfill_map()


if __name__ == "__main__":
    main()
