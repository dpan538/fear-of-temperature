"""Stage browser-accessible Australian originals without touching the US writer."""
import csv
import hashlib
import json
import re
from pathlib import Path

import duckdb
import pypdfium2 as pdfium

from acquire import HERE, sid, verified_meta
from au_candidate_triage import OBSERVATIONS

DB = HERE / "au_browser_stage.duckdb"


def setup(c):
    c.execute("""CREATE TABLE IF NOT EXISTS au_browser_works (
      landing_url VARCHAR PRIMARY KEY, title VARCHAR NOT NULL, original_date VARCHAR NOT NULL,
      date_precision VARCHAR NOT NULL, date_evidence VARCHAR NOT NULL,
      original_publisher VARCHAR NOT NULL, scope_status VARCHAR NOT NULL,
      boundary_evidence VARCHAR NOT NULL, browser_observed_at_utc VARCHAR NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS au_browser_versions (
      version_id VARCHAR PRIMARY KEY, landing_url VARCHAR NOT NULL, file_url VARCHAR NOT NULL,
      sha256 VARCHAR NOT NULL, raw_path VARCHAR NOT NULL, byte_count BIGINT NOT NULL,
      retrieved_at_utc VARCHAR NOT NULL, http_status_basis VARCHAR NOT NULL,
      pdf_pages INTEGER NOT NULL, text_characters BIGINT NOT NULL)""")
    c.execute("ALTER TABLE au_browser_versions ADD COLUMN IF NOT EXISTS attachment_role VARCHAR")
    c.execute("""CREATE TABLE IF NOT EXISTS au_browser_pages (
      version_id VARCHAR NOT NULL, page_no INTEGER NOT NULL, source_text VARCHAR NOT NULL,
      cleaned_text VARCHAR NOT NULL, PRIMARY KEY(version_id,page_no))""")


def stage(c, observation):
    attachments=observation["attachments"]
    if not attachments or any(a["format"]!="pdf" for a in attachments):
        raise RuntimeError("this reviewed browser observation requires PDF attachments")
    verified=[]
    for attachment in attachments:
        url=attachment["url"]
        path=HERE/"raw"/"au_files"/f"{sid('',url)}.pdf"
        meta=verified_meta(path)
        if not meta:
            raise RuntimeError(f"verified saved original absent: {url}")
        version_id=sid("au_browser_version",url,meta["sha256"])
        document=pdfium.PdfDocument(str(path))
        pages=[]
        for i in range(len(document)):
            page=document[i];textpage=page.get_textpage();source=textpage.get_text_range() or ""
            textpage.close();page.close()
            cleaned=re.sub(r"\s+"," ",source).strip()
            pages.append((version_id,i+1,source,cleaned))
        document.close()
        if not any(p[3] for p in pages):
            raise RuntimeError("PDF has no extractable text; preserve raw and classify separately")
        role="primary" if url==observation.get("primary_file_url",attachments[0]["url"]) else attachment["role_candidate"]
        verified.append((url,path,meta,version_id,pages,role))
    c.execute("BEGIN")
    try:
        c.execute("INSERT INTO au_browser_works VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                  [observation["landing_url"],observation["title"],observation["original_date"],
                   observation["date_precision"],observation["date_evidence"],observation["original_publisher"],
                   observation.get("scope_status","eligible_predecessor_or_department"),observation["work_boundary"],
                   observation["observed_at_utc"]])
        for url,path,meta,version_id,pages,role in verified:
            c.execute("INSERT INTO au_browser_versions VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO UPDATE SET attachment_role=excluded.attachment_role",
                      [version_id,observation["landing_url"],url,meta["sha256"],meta["raw_path"],meta["byte_count"],
                       meta["retrieved_at_utc"],meta["status_code_basis"],len(pages),sum(len(p[2]) for p in pages),role])
            c.executemany("INSERT INTO au_browser_pages VALUES (?,?,?,?) ON CONFLICT DO NOTHING",pages)
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK");raise
    print(json.dumps({"landing_url":observation["landing_url"],"attachments":len(verified),"pages":sum(len(x[4]) for x in verified)}),flush=True)


def main():
    observations=[json.loads(line) for line in OBSERVATIONS.read_text().splitlines() if line.strip()]
    c=duckdb.connect(str(DB));setup(c)
    for observation in observations:stage(c,observation)
    print(json.dumps({"works":c.execute("SELECT COUNT(*) FROM au_browser_works").fetchone()[0],
                      "versions":c.execute("SELECT COUNT(*) FROM au_browser_versions").fetchone()[0],
                      "pages":c.execute("SELECT COUNT(*) FROM au_browser_pages").fetchone()[0]}),flush=True)
    c.close()


if __name__=="__main__":main()
