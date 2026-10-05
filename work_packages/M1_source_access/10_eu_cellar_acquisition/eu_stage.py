"""Idempotently stage enumerated EU Works and verified Item bytes in a separate DB."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import duckdb

from eu_acquire import HERE, sha
from eu_items import path_for, selected

DB = HERE / "eu_stage.duckdb"


def setup(c):
    c.execute("""CREATE TABLE IF NOT EXISTS eu_works (
      work_uri VARCHAR PRIMARY KEY, issuer_uri VARCHAR NOT NULL,
      work_type_uri VARCHAR NOT NULL, language_uri VARCHAR NOT NULL,
      first_seen_month VARCHAR NOT NULL, boundary_status VARCHAR NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS eu_work_dates (
      work_uri VARCHAR NOT NULL, document_date VARCHAR NOT NULL, source_month VARCHAR NOT NULL,
      source_page VARCHAR NOT NULL, PRIMARY KEY(work_uri, document_date, source_month))""")
    c.execute("""CREATE TABLE IF NOT EXISTS eu_item_candidates (
      item_uri VARCHAR PRIMARY KEY, work_uri VARCHAR NOT NULL, expression_uri VARCHAR NOT NULL,
      manifestation_uri VARCHAR NOT NULL, format VARCHAR NOT NULL, alternatives INTEGER NOT NULL,
      selection_status VARCHAR NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS eu_content_versions (
      version_id VARCHAR PRIMARY KEY, item_uri VARCHAR NOT NULL, work_uri VARCHAR NOT NULL,
      sha256 VARCHAR NOT NULL, raw_path VARCHAR NOT NULL, retrieved_at_utc VARCHAR NOT NULL,
      http_status INTEGER NOT NULL, mime_type VARCHAR NOT NULL, bytes BIGINT NOT NULL,
      extraction_status VARCHAR NOT NULL, pdf_pages INTEGER, text_characters BIGINT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS eu_source_pages (
      version_id VARCHAR NOT NULL, page_no INTEGER NOT NULL, source_text VARCHAR NOT NULL,
      cleaned_text VARCHAR NOT NULL, PRIMARY KEY(version_id, page_no))""")
    c.execute("""CREATE TABLE IF NOT EXISTS eu_source_blocks (
      version_id VARCHAR NOT NULL, block_no INTEGER NOT NULL, source_locator VARCHAR NOT NULL,
      source_text VARCHAR NOT NULL, cleaned_text VARCHAR NOT NULL,
      PRIMARY KEY(version_id, block_no))""")
    c.execute("""CREATE TABLE IF NOT EXISTS eu_month_status (
      year_month VARCHAR PRIMARY KEY, expected_distinct_works INTEGER NOT NULL,
      observed_distinct_works INTEGER NOT NULL, reconciliation_status VARCHAR NOT NULL)""")


def stage_month(c, month, metadata_only=False):
    state_path = HERE / "manifests" / "months" / f"{month}.json"
    state = json.loads(state_path.read_text())
    if state["status"] != "reconciled":
        raise RuntimeError(f"month {month} not reconciled")
    with (HERE / "manifests" / "months" / f"{month}.csv").open(newline="", encoding="utf-8") as handle:
        parent_rows = list(csv.DictReader(handle))
    choice_rows = selected(month) if not metadata_only and (HERE / "manifests" / "wemi" / f"{month}.json").exists() else []
    c.execute("BEGIN")
    try:
        c.execute("INSERT INTO eu_month_status VALUES (?,?,?,?) ON CONFLICT DO UPDATE SET expected_distinct_works=excluded.expected_distinct_works, observed_distinct_works=excluded.observed_distinct_works, reconciliation_status=excluded.reconciliation_status",
                  [month, state["expected_distinct_works"], state["observed_distinct_works"], state["status"]])
        for row in parent_rows:
            work = row["work_uri"]
            c.execute("INSERT INTO eu_works VALUES (?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [work, "http://publications.europa.eu/resource/authority/corporate-body/COM",
                       "http://publications.europa.eu/ontology/cdm#act_preparatory",
                       "http://publications.europa.eu/resource/authority/language/ENG", month,
                       "CELLAR_Work_URI_unique"])
            c.execute("INSERT INTO eu_work_dates VALUES (?,?,?,?) ON CONFLICT DO NOTHING",
                      [work, row["date_observed"], month, row["source_page"]])
        for row in choice_rows:
            if not row["item_uri"]:
                continue
            c.execute("INSERT INTO eu_item_candidates VALUES (?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                      [row["item_uri"], row["work_uri"], row["expression_uri"], row["manifestation_uri"],
                       row["format"], int(row["item_alternatives"]), row["selection_status"]])
            path = path_for(row["item_uri"])
            meta_path = path.with_suffix(".request.json")
            if not path.exists() or not meta_path.exists():
                continue
            meta = json.loads(meta_path.read_text())
            if meta.get("status") != "downloaded" or meta.get("sha256") != sha(path.read_bytes()):
                raise RuntimeError(f"EU source byte mismatch: {path}")
            version_id = "euver:" + hashlib.sha256((row["item_uri"] + "\x1f" + meta["sha256"]).encode()).hexdigest()[:32]
            extract_path = path.with_suffix(".extract.json")
            extract = json.loads(extract_path.read_text()) if extract_path.exists() else {}
            if extract and extract.get("raw_sha256") != meta["sha256"]:
                raise RuntimeError(f"EU extraction/source mismatch: {path}")
            if extract.get("textutil_source_sha256"):
                derivative = path.with_suffix(".source.txt")
                if not derivative.exists() or sha(derivative.read_bytes()) != extract["textutil_source_sha256"]:
                    raise RuntimeError(f"EU DOC textutil derivative mismatch: {derivative}")
            ocr = {}
            if extract.get("status") == "scanned_or_empty_text_layer":
                ocr_meta = path.with_suffix(".ocr.meta.json")
                if ocr_meta.exists():
                    ocr = json.loads(ocr_meta.read_text())
                    ocr_pages = path.with_suffix(".ocr.pages.txt")
                    ocr_lines = path.with_suffix(".ocr.jsonl")
                    if (ocr.get("raw_sha256") != meta["sha256"]
                            or not ocr_pages.exists() or not ocr_lines.exists()
                            or sha(ocr_pages.read_bytes()) != ocr.get("pages_sha256")
                            or sha(ocr_lines.read_bytes()) != ocr.get("lines_sha256")):
                        raise RuntimeError(f"EU OCR/source mismatch: {path}")
            effective = ocr if ocr.get("status") == "ocr_candidate_text_extracted" else extract
            c.execute("INSERT INTO eu_content_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO UPDATE SET extraction_status=excluded.extraction_status, pdf_pages=excluded.pdf_pages, text_characters=excluded.text_characters",
                      [version_id, row["item_uri"], row["work_uri"], meta["sha256"], meta["raw_path"],
                       meta["retrieved_at_utc"], meta["http_status"], meta["mime_type"], meta["byte_count"],
                       effective.get("status", "not_extracted"), effective.get("pdf_pages"), effective.get("text_characters")])
            text_path = path.with_suffix(".ocr.pages.txt") if effective is ocr else path.with_suffix(".pages.txt")
            if effective.get("status") in ("text_extracted", "ocr_candidate_text_extracted") and text_path.exists():
                for match in re.finditer(r"\fPAGE=(\d+)\n(.*?)(?=\fPAGE=|\Z)", text_path.read_text(), flags=re.S):
                    page_no = int(match.group(1))
                    source = match.group(2).strip("\n")
                    clean = re.sub(r"\s+", " ", source).strip()
                    c.execute("INSERT INTO eu_source_pages VALUES (?,?,?,?) ON CONFLICT DO NOTHING",
                              [version_id, page_no, source, clean])
            blocks_path = path.with_suffix(".blocks.jsonl")
            if extract.get("status") == "text_extracted" and blocks_path.exists():
                with blocks_path.open(encoding="utf-8") as handle:
                    for line in handle:
                        block = json.loads(line)
                        c.execute("INSERT INTO eu_source_blocks VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",
                                  [version_id, block["block_no"], block["source_locator"],
                                   block["source_text"], block["cleaned_text"]])
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK")
        raise
    counts = c.execute("SELECT (SELECT COUNT(*) FROM eu_works), (SELECT COUNT(*) FROM eu_content_versions), (SELECT COUNT(*) FROM eu_source_pages)").fetchone()
    print(json.dumps({"month": month, "works_total": counts[0], "versions_total": counts[1], "pages_total": counts[2]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="1988-01")
    parser.add_argument("--end", default="2026-09")
    parser.add_argument("--limit-months", type=int, default=0)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    months = sorted(p.stem for p in (HERE / "manifests" / "months").glob("*.json") if args.start <= p.stem <= args.end)
    if args.limit_months:
        months = months[:args.limit_months]
    c = duckdb.connect(str(DB))
    setup(c)
    for month in months:
        stage_month(c, month, args.metadata_only)
    c.close()


if __name__ == "__main__":
    main()
