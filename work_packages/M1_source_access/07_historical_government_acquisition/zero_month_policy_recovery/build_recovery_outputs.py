#!/usr/bin/env python3
"""Build the bounded zero-month recovery evidence, reports and figures.

This program is deliberately read-only with respect to the formal 06 DuckDB.
It updates only the versioned ``zero_month_policy_recovery`` work directory.
Counts and coverage evidence remain separate: a zero count is never promoted to
historical completeness unless the applicable source route was enumerated.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/fear_temperature_zero_month_mpl")

import duckdb
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import StrMethodFormatter

SKILL_SCRIPTS = Path("/Users/jarlgiovanni/.codex/skills/nature-figure/scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment  # noqa: E402


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DB = ROOT / "work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb"
PRIOR = HERE.parent / "historical_coverage_recovery"
TEMPORAL = PRIOR / "reports/temporal_reference_availability"
REPORTS = HERE / "reports"
FIGURES = REPORTS / "figures"
QA = REPORTS / "qa"
EVIDENCE = HERE / "evidence"
GENERATED_AT = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

SERIES = ["policy_document", "ministerial_written_answer", "ministerial_written_statement"]
SERIES_LABELS = {
    "policy_document": "Policy records",
    "ministerial_written_answer": "Written answers",
    "ministerial_written_statement": "Written statements",
}
ZERO_MONTHS = [
    "1988-08", "1988-09", "1989-08", "1989-09", "1990-08", "1991-08", "1991-09",
    "1992-08", "1993-08", "1993-09", "1994-08", "1994-09", "1995-08", "1995-09",
    "1996-08", "1996-09", "1997-04", "1997-08", "1997-09", "1998-08", "1999-08",
    "2000-08", "2000-09", "2001-08", "2001-09", "2002-08", "2003-08", "2007-08",
    "2008-08", "2015-04", "2015-05",
]

RECESS_URL = (
    "https://www.parliament.uk/about/faqs/house-of-commons-faqs/"
    "business-faq-page/recess-dates/list-of-previous-commons-recess-dates/"
)
SESSIONAL_DIGEST_URL = (
    "https://www.parliament.uk/globalassets/documents/commons-information-office/"
    "sessional-info-digests/sid_1990_91.pdf"
)
PRIOR_ENUMERATION = "work_packages/M1_source_access/07_historical_government_acquisition/historical_coverage_recovery/reports/monthly_coverage_status.csv"

RECESS_CONTEXT = {
    "1988-08": "Summer recess 1988-07-29 to 1988-10-19.",
    "1988-09": "Summer recess 1988-07-29 to 1988-10-19.",
    "1989-08": "Summer recess 1989-07-28 to 1989-10-17.",
    "1989-09": "Summer recess 1989-07-28 to 1989-10-17.",
    "1990-08": "Summer recess 1990-07-26 to 1990-10-15.",
    "1991-08": "Not a full non-sitting month: the House was recalled and sat 1991-08-14 to 1991-08-22; bounded enumeration still found zero in-scope records.",
    "1991-09": "Summer recess resumed after the August recall and continued to 1991-10-14.",
    "1992-08": "Summer recess 1992-07-16 to 1992-10-19.",
    "1993-08": "Summer recess 1993-07-27 to 1993-10-18.",
    "1993-09": "Summer recess 1993-07-27 to 1993-10-18.",
    "1994-08": "Summer recess 1994-07-21 to 1994-10-17.",
    "1994-09": "Summer recess 1994-07-21 to 1994-10-17.",
    "1995-08": "Summer recess 1995-07-19 to 1995-10-16.",
    "1995-09": "Summer recess 1995-07-19 to 1995-10-16.",
    "1996-08": "Summer recess 1996-07-24 to 1996-10-14.",
    "1996-09": "Summer recess 1996-07-24 to 1996-10-14.",
    "1997-04": "Parliament was dissolved for the 1997 general election; bounded enumeration found zero in-scope records.",
    "1997-08": "Summer recess 1997-07-31 to 1997-10-27.",
    "1997-09": "Summer recess 1997-07-31 to 1997-10-27.",
    "1998-08": "Summer recess 1998-07-31 to 1998-10-19.",
    "1999-08": "Summer recess 1999-07-27 to 1999-10-19.",
    "2000-08": "Summer recess 2000-07-28 to 2000-10-23.",
    "2000-09": "Summer recess 2000-07-28 to 2000-10-23.",
    "2001-08": "Summer recess 2001-07-20 to 2001-10-15.",
    "2001-09": "Summer recess 2001-07-20 to 2001-10-15.",
    "2002-08": "Summer recess 2002-07-24 to 2002-10-15.",
    "2003-08": "Summer recess 2003-07-17 to 2003-09-08.",
    "2007-08": "Summer recess 2007-07-26 to 2007-10-08.",
    "2008-08": "Summer recess 2008-07-22 to 2008-10-06.",
    "2015-04": "Parliament was prorogued 2015-03-26 and dissolved 2015-03-30 for the general election.",
    "2015-05": "Election / new-Parliament interval; the State Opening was 2015-05-27.",
}

DATE_MAPPINGS = [
    {
        "document_id": "doc_58c8b99baa34eb825cbb",
        "title": "Securing the future: delivering UK sustainable development strategy",
        "content_object_id": "cnt_f4291a8e348e48c25a54",
        "content_version_id": "cntv_ed1b56a2aae61af65e40",
        "stored_publication_date": "2011-03-25",
        "stored_date_basis": "GOV.UK Content API first_published_at",
        "research_publication_date": "2005-03",
        "research_date_precision": "month",
        "eligible_for_exact_month_view": True,
        "evidence_location": "PDF page 2",
        "evidence_text": "Presented to Parliament ... March 2005; Cm 6467.",
        "raw_path": "work_packages/M1_source_access/06_government_content_acquisition/raw/content/cnt_f4291a8e348e48c25a54/cntv_ed1b56a2aae61af65e40.pdf",
        "official_url": "https://assets.publishing.service.gov.uk/media/5a78a0eae5274a277e68e375/pb10589-securing-the-future-050307.pdf",
        "decision": "Keep the stable record and stored GOV.UK migration date; use 2005-03 in the versioned research-date view. Do not infer a day from the filename or PDF metadata.",
    },
    {
        "document_id": "doc_624120433434fb59f427",
        "title": "Working with the grain of nature: a biodiversity strategy for England",
        "content_object_id": "cnt_b36a4a39ecd83e6898b7",
        "content_version_id": "cntv_3c6759a755931dda0c77",
        "stored_publication_date": "2011-03-29",
        "stored_date_basis": "GOV.UK Content API first_published_at",
        "research_publication_date": "2002-10",
        "research_date_precision": "month",
        "eligible_for_exact_month_view": True,
        "evidence_location": "PDF page 3",
        "evidence_text": "Published by Defra; Printed in the UK, October 2002; product code PB7718.",
        "raw_path": "work_packages/M1_source_access/06_government_content_acquisition/raw/content/cnt_b36a4a39ecd83e6898b7/cntv_3c6759a755931dda0c77.pdf",
        "official_url": "https://assets.publishing.service.gov.uk/media/5a78f2f8e5274a2acd18b099/pb7718-biostrategy-021016.pdf",
        "decision": "Keep the stable record and stored migration date; use 2002-10 in the research-date view.",
    },
    {
        "document_id": "doc_1721557b261590b7de32",
        "title": "Conserving biodiversity: the UK approach",
        "content_object_id": "cnt_7eed455240844cb3a00b",
        "content_version_id": "cntv_985dbe0d066a0840c7b8",
        "stored_publication_date": "2011-05-24",
        "stored_date_basis": "GOV.UK Content API first_published_at",
        "research_publication_date": "2007-10",
        "research_date_precision": "month",
        "eligible_for_exact_month_view": True,
        "evidence_location": "PDF pages 1-2",
        "evidence_text": "Cover states October 2007; imprint states Printed in the UK, October 2007; PB12772.",
        "raw_path": "work_packages/M1_source_access/06_government_content_acquisition/raw/content/cnt_7eed455240844cb3a00b/cntv_985dbe0d066a0840c7b8.pdf",
        "official_url": "https://assets.publishing.service.gov.uk/media/5a79b11540f0b642860da010/pb12772-conbiouk-071004.pdf",
        "decision": "Keep the stable record and stored migration date; use 2007-10 in the research-date view.",
    },
    {
        "document_id": "doc_185b77378ac885763118",
        "title": "England biodiversity strategy: Climate change adaptation principles",
        "content_object_id": "cnt_02dcfbd29b6a6d0a7b0e",
        "content_version_id": "cntv_4df532d6b3c7efc8e0af",
        "stored_publication_date": "2011-05-24",
        "stored_date_basis": "GOV.UK Content API first_published_at",
        "research_publication_date": "2008",
        "research_date_precision": "year",
        "eligible_for_exact_month_view": False,
        "evidence_location": "PDF page 2",
        "evidence_text": "Crown copyright 2008; no independently verified publication month on the inspected cover/imprint.",
        "raw_path": "work_packages/M1_source_access/06_government_content_acquisition/raw/content/cnt_02dcfbd29b6a6d0a7b0e/cntv_4df532d6b3c7efc8e0af.pdf",
        "official_url": "https://assets.publishing.service.gov.uk/media/5a79c6fae5274a18ba50ec2f/pb13168-ebs-ccap-081203.pdf",
        "decision": "Retain a year-only research date. Exclude from exact-month reassignment; do not infer December from the filename.",
    },
    {
        "document_id": "doc_f054c2fd6108dae2286d",
        "title": "United Kingdom overseas territories biodiversity strategy",
        "content_object_id": "cnt_18df43c9256866091fe5",
        "content_version_id": "cntv_78f81c2e53cd65f172ea",
        "stored_publication_date": "2011-05-26",
        "stored_date_basis": "GOV.UK Content API first_published_at",
        "research_publication_date": "2009",
        "research_date_precision": "year",
        "eligible_for_exact_month_view": False,
        "evidence_location": "PDF page 2",
        "evidence_text": "Crown copyright 2009; no independently verified publication month on the inspected cover/imprint.",
        "raw_path": "work_packages/M1_source_access/06_government_content_acquisition/raw/content/cnt_18df43c9256866091fe5/cntv_78f81c2e53cd65f172ea.pdf",
        "official_url": "https://assets.publishing.service.gov.uk/media/5a7998a440f0b63d72fc70a8/pb13335-uk-ot-strat-091201.pdf",
        "decision": "Retain a year-only research date. Exclude from exact-month reassignment; do not infer December from the filename.",
    },
]

EARLY_POLICY_TARGETS = [
    {
        "title": "This Common Inheritance: Britain's Environmental Strategy",
        "original_issuing_body": "UK Government (multi-department command paper)",
        "command_number": "Cm 1200",
        "isbn": "0101120028",
        "original_publication_date": "1990-09",
        "date_precision": "month",
        "date_evidence": "Archive catalogue description quotes presentation to Parliament in September 1990.",
        "database_match": "none",
        "full_text_route": "Internet Archive/Open Library scan",
        "route_result": "Metadata verified; scan is access-restricted and OCR/PDF derivatives are private.",
        "current_status": "known_target_original_unavailable",
        "next_bounded_step": "Request/inspect a lawful institutional or official-library copy using Cm 1200 / ISBN 0101120028.",
    },
    {
        "title": "Sustainable Development: The UK Strategy",
        "original_issuing_body": "UK Government",
        "command_number": "Cm 2426",
        "isbn": "010124262X",
        "original_publication_date": "1994-01-25",
        "date_precision": "day",
        "date_evidence": "Official Hansard states the four sustainable-development White Papers were launched on 25 January 1994.",
        "database_match": "none",
        "full_text_route": "Official catalogue / library holdings; Google Books bibliographic preview",
        "route_result": "No verified public full-text original found in this tranche.",
        "current_status": "catalogued_original_not_acquired",
        "next_bounded_step": "Use Cm 2426 / ISBN 010124262X for an institutional holding request; do not substitute Cm 2428.",
    },
    {
        "title": "Climate Change: The UK Programme",
        "original_issuing_body": "UK Government",
        "command_number": "Cm 2427",
        "isbn": "0101242727",
        "original_publication_date": "1994-01-25",
        "date_precision": "day",
        "date_evidence": "Official Hansard launch evidence; UNFCCC holds only a shorter first-national-communication summary.",
        "database_match": "none",
        "full_text_route": "Official catalogue / institutional holdings",
        "route_result": "No verified public full-text command paper found; the 17-page UNFCCC item is not the full command paper.",
        "current_status": "catalogued_original_not_acquired",
        "next_bounded_step": "Request the 80-page command paper by Cm 2427 / ISBN 0101242727.",
    },
    {
        "title": "A Better Quality of Life: A Strategy for Sustainable Development for the United Kingdom",
        "original_issuing_body": "Department of the Environment, Transport and the Regions",
        "command_number": "Cm 4345",
        "isbn": "0101434529",
        "original_publication_date": "1999-05",
        "date_precision": "month",
        "date_evidence": "Archive catalogue description states May 1999.",
        "database_match": "none",
        "full_text_route": "Internet Archive/Open Library scan",
        "route_result": "Metadata verified; scan is access-restricted and OCR/PDF derivatives are private.",
        "current_status": "catalogued_original_not_acquired",
        "next_bounded_step": "Request/inspect a lawful institutional copy using Cm 4345 / ISBN 0101434529.",
    },
    {
        "title": "Climate Change: The UK Programme",
        "original_issuing_body": "Department of the Environment, Transport and the Regions",
        "command_number": "Cm 4913",
        "isbn": "0101491328",
        "original_publication_date": "2000-11-17",
        "date_precision": "day",
        "date_evidence": "Official Commons statement on publication; catalogue sources describe November 2000.",
        "database_match": "none",
        "full_text_route": "UK Government Web Archive legacy sectional PDFs; public-library holdings",
        "route_result": "Archive request reached a WAF/captcha response (HTTP 405); no bypass attempted. Physical holdings identified.",
        "current_status": "official_archive_access_blocked",
        "next_bounded_step": "Use the exact old section URLs via a lawful archive/library mediation request, or inspect a physical copy.",
    },
    {
        "title": "Securing the Future: Delivering UK Sustainable Development Strategy",
        "original_issuing_body": "Department for Environment, Food and Rural Affairs",
        "command_number": "Cm 6467",
        "isbn": "",
        "original_publication_date": "2005-03",
        "date_precision": "month",
        "date_evidence": "Stored official PDF title page states March 2005.",
        "database_match": "doc_58c8b99baa34eb825cbb",
        "full_text_route": "Official GOV.UK asset already stored",
        "route_result": "Complete 188-page official PDF already present; no re-download performed.",
        "current_status": "existing_original_date_mapped",
        "next_bounded_step": "Use the versioned 2005-03 research date without changing the stable document ID or raw evidence.",
    },
]

SOURCE_EVIDENCE = [
    {
        "evidence_id": "calendar-recess-history",
        "source": "UK Parliament previous Commons recess dates",
        "request_or_source_url": RECESS_URL,
        "request_kind": "browser evidence check",
        "observed_http_status": "not captured; no status fabricated",
        "observed_format": "HTML",
        "result": "Official calendar provides the historical recess intervals used as context for the zero-month review.",
        "local_evidence_path": "",
        "use_decision": "Context only; recess does not prove policy-publication absence and does not replace source enumeration.",
    },
    {
        "evidence_id": "calendar-1991-recall",
        "source": "UK Parliament Sessional Information Digest 1990-91",
        "request_or_source_url": SESSIONAL_DIGEST_URL,
        "request_kind": "browser/PDF evidence check",
        "observed_http_status": "not captured; no status fabricated",
        "observed_format": "PDF",
        "result": "Official digest records a Commons recall and sittings from 14 to 22 August 1991.",
        "local_evidence_path": "",
        "use_decision": "1991-08 cannot be described as wholly explained by summer recess.",
    },
    {
        "evidence_id": "ia-cm1200-metadata",
        "source": "Internet Archive metadata API",
        "request_or_source_url": "https://archive.org/metadata/thiscommoninheri0000unse_n3z7",
        "request_kind": "actual GET",
        "observed_http_status": "200",
        "observed_format": "application/json",
        "result": "Title, September 1990 presentation statement, 291 pages and ISBN verified; access-restricted-item=true.",
        "local_evidence_path": "evidence/raw/ia_this_common_inheritance.metadata.json",
        "use_decision": "Catalogue/date evidence accepted; private PDF/OCR not treated as acquired full text.",
    },
    {
        "evidence_id": "ia-cm4345-metadata",
        "source": "Internet Archive metadata API",
        "request_or_source_url": "https://archive.org/metadata/betterqualityofl0000unse",
        "request_kind": "actual GET",
        "observed_http_status": "200",
        "observed_format": "application/json",
        "result": "Title, May 1999 date, 96 pages and ISBN verified; access-restricted-item=true.",
        "local_evidence_path": "evidence/raw/ia_better_quality_of_life.metadata.json",
        "use_decision": "Catalogue/date evidence accepted; private PDF/OCR not treated as acquired full text.",
    },
    {
        "evidence_id": "ukgwa-cm4913-section1",
        "source": "UK Government Web Archive legacy DEFRA route",
        "request_or_source_url": "https://webarchive.nationalarchives.gov.uk/20060512120000/http://www.defra.gov.uk/environment/climatechange/uk/ukccp/2000/pdf/section1.pdf",
        "request_kind": "actual GET following archive redirect",
        "observed_http_status": "405",
        "observed_format": "HTML WAF/captcha response",
        "result": "Archive access was blocked by an AWS WAF captcha response.",
        "local_evidence_path": "evidence/raw/ukgwa_cm4913_access.json",
        "use_decision": "Stopped; no captcha bypass and no repeated pressure on the endpoint.",
    },
    {
        "evidence_id": "google-books-three-isbns",
        "source": "Google Books API",
        "request_or_source_url": "https://www.googleapis.com/books/v1/volumes?q=isbn:010124262X (and ISBN 0101242727 / 0101491328)",
        "request_kind": "three bounded API checks",
        "observed_http_status": "429",
        "observed_format": "JSON error response",
        "result": "Quota/rate limit returned; daily quota appeared unavailable.",
        "local_evidence_path": "",
        "use_decision": "Stopped after bounded checks; no repeated retry.",
    },
    {
        "evidence_id": "unfccc-gbr01",
        "source": "UNFCCC official site",
        "request_or_source_url": "https://unfccc.int/cop5/resource/docs/nc/gbr01.pdf",
        "request_kind": "browser/PDF evidence check",
        "observed_http_status": "not captured; no status fabricated",
        "observed_format": "PDF",
        "result": "A 17-page executive summary / national communication was located, not the 80-page Cm 2427 command paper.",
        "local_evidence_path": "",
        "use_decision": "Retained as catalogue context; excluded as a substitute for the full policy original.",
    },
    {
        "evidence_id": "hansard-1994-launch",
        "source": "Official Hansard",
        "request_or_source_url": "https://publications.parliament.uk/pa/ld199495/ldhansrd/vo941123/text/41123-04.htm",
        "request_kind": "browser evidence check",
        "observed_http_status": "not captured; no status fabricated",
        "observed_format": "HTML",
        "result": "Records the 25 January 1994 launch of the four sustainable-development White Papers.",
        "local_evidence_path": "",
        "use_decision": "Accepted for original-date evidence for Cm 2426 and Cm 2427; not full text.",
    },
    {
        "evidence_id": "hansard-2000-publication",
        "source": "Official Hansard",
        "request_or_source_url": "https://hansard.parliament.uk/Commons/2000-11-17/debates/54d5a6b8-b0b0-4268-a98c-dae1fe755e08/ClimateChange",
        "request_kind": "browser evidence check",
        "observed_http_status": "not captured; no status fabricated",
        "observed_format": "HTML",
        "result": "Official publication statement identifies Cm 4913 on 17 November 2000.",
        "local_evidence_path": "",
        "use_decision": "Accepted for original-date evidence; not full text.",
    },
]


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot_db() -> dict[str, object]:
    before_mtime = DB.stat().st_mtime_ns
    with duckdb.connect(str(DB), read_only=True) as con:
        document_ids = [row["document_id"] for row in DATE_MAPPINGS]
        version_ids = [row["content_version_id"] for row in DATE_MAPPINGS]
        document_placeholders = ",".join(["?"] * len(document_ids))
        version_placeholders = ",".join(["?"] * len(version_ids))
        result = {
            "documents": int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]),
            "policy_records": int(con.execute("SELECT COUNT(*) FROM documents WHERE content_type IN ('policy_paper','guidance')").fetchone()[0]),
            "written_answers": int(con.execute("SELECT COUNT(*) FROM documents WHERE content_type='ministerial_written_answer'").fetchone()[0]),
            "written_statements": int(con.execute("SELECT COUNT(*) FROM documents WHERE content_type='ministerial_written_statement'").fetchone()[0]),
            "text_segments": int(con.execute("SELECT COUNT(*) FROM text_segments").fetchone()[0]),
            "reviewed_document_ids_present": int(
                con.execute(f"SELECT COUNT(*) FROM documents WHERE document_id IN ({document_placeholders})", document_ids).fetchone()[0]
            ),
            "reviewed_content_versions_present": int(
                con.execute(f"SELECT COUNT(*) FROM content_versions WHERE content_version_id IN ({version_placeholders})", version_ids).fetchone()[0]
            ),
        }
    after_mtime = DB.stat().st_mtime_ns
    if before_mtime != after_mtime:
        raise RuntimeError("Formal database mtime changed during read-only snapshot; aborting mixed-state report")
    return {**result, "database_mtime_ns": after_mtime, "snapshot_at": GENERATED_AT}


def enrich_date_mappings() -> list[dict]:
    rows = []
    for item in DATE_MAPPINGS:
        raw = ROOT / item["raw_path"]
        if not raw.exists():
            raise FileNotFoundError(raw)
        rows.append(
            {
                **item,
                "raw_sha256": sha256(raw),
                "raw_byte_size": raw.stat().st_size,
                "checked_at": GENERATED_AT,
            }
        )
    return rows


def write_access_evidence() -> None:
    raw = EVIDENCE / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    write_json(
        raw / "ukgwa_cm4913_access.json",
        {
            "evidence_type": "bounded_access_observation",
            "observed_date": "2026-09-23",
            "timestamp_precision": "date",
            "request_url": SOURCE_EVIDENCE[4]["request_or_source_url"],
            "observed_status": 405,
            "response_classification": "HTML AWS WAF captcha/access-control page",
            "handling": "Stopped without captcha bypass or repeated retries.",
            "note": "This evidence record preserves the observed result; it is not a downloaded policy original.",
        },
    )


def finalise_month_ledger() -> pd.DataFrame:
    ledger = pd.read_csv(HERE / "month_recovery_ledger.csv", dtype={"year_month": str})
    for column in [
        "check_source",
        "evidence_url_or_path",
        "parliamentary_context",
        "policy_catalogue_status",
        "recoverable_candidate_count",
        "processing_result",
        "final_status",
        "notes",
    ]:
        ledger[column] = ledger[column].astype("object")
    assert len(ledger) == 93 and set(ledger.year_month) == set(ZERO_MONTHS)
    for index, row in ledger.iterrows():
        ym, series = row["year_month"], row["series"]
        ledger.at[index, "after_record_count"] = 0
        ledger.at[index, "new_document_count"] = 0
        ledger.at[index, "excluded_count"] = 0
        ledger.at[index, "date_reassignment_count"] = 0
        if series in {"ministerial_written_answer", "ministerial_written_statement"}:
            ledger.at[index, "check_source"] = "Prior bounded full-route enumeration plus official UK Parliament calendar check"
            ledger.at[index, "evidence_url_or_path"] = f"{PRIOR_ENUMERATION}; {RECESS_URL}"
            if ym == "1991-08":
                ledger.at[index, "evidence_url_or_path"] += f"; {SESSIONAL_DIGEST_URL}"
            ledger.at[index, "parliamentary_context"] = RECESS_CONTEXT[ym]
            ledger.at[index, "policy_catalogue_status"] = "not applicable"
            ledger.at[index, "recoverable_candidate_count"] = 0
            ledger.at[index, "processing_result"] = "No in-scope record in the already enumerated applicable route; no re-acquisition performed."
            ledger.at[index, "final_status"] = "confirmed_zero_within_enumerated_parliamentary_scope"
            ledger.at[index, "notes"] = "Confirmed zero is scoped to the approved Commons source/department/document definition, not all parliamentary or government speech."
        else:
            ledger.at[index, "check_source"] = "Bounded early-policy catalogue and alternative-source review"
            ledger.at[index, "evidence_url_or_path"] = "early_policy_target_register.csv; source_evidence_log.csv"
            ledger.at[index, "parliamentary_context"] = "not applicable; parliamentary recess cannot establish policy-publication absence"
            if ym == "1990-09":
                ledger.at[index, "policy_catalogue_status"] = "Known target: This Common Inheritance, Cm 1200, presented September 1990."
                ledger.at[index, "recoverable_candidate_count"] = 1
                ledger.at[index, "processing_result"] = "Catalogue/date verified; public scan route is access-restricted, so no original was acquired."
                ledger.at[index, "final_status"] = "known_target_original_unavailable"
                ledger.at[index, "notes"] = "This is a known missing policy target, not a confirmed-zero month."
            elif ym in {"2015-04", "2015-05"}:
                ledger.at[index, "policy_catalogue_status"] = "Frozen current-DEFRA GOV.UK policy route was fully enumerated and returned zero in-scope records."
                ledger.at[index, "recoverable_candidate_count"] = 0
                ledger.at[index, "processing_result"] = "No additional target in the frozen route; no modern expansion authorised."
                ledger.at[index, "final_status"] = "confirmed_zero_within_frozen_govuk_scope"
                ledger.at[index, "notes"] = "This does not claim zero policy publications across all UK departments."
            else:
                ledger.at[index, "policy_catalogue_status"] = "Bounded seed/catalogue checks found no verified exact-month target; predecessor-department population denominator remains unknown."
                ledger.at[index, "recoverable_candidate_count"] = "unknown"
                ledger.at[index, "processing_result"] = "No evidence-sufficient original acquired for this exact month in the bounded tranche."
                ledger.at[index, "final_status"] = "catalogue_unknown_denominator"
                ledger.at[index, "notes"] = "Zero stored records remains a coverage gap, not evidence that no policy was published."
    ledger.to_csv(HERE / "month_recovery_ledger.csv", index=False)
    return ledger


def corrected_monthly_view(mappings: list[dict]) -> pd.DataFrame:
    source = pd.read_csv(TEMPORAL / "monthly_reference_availability.csv", dtype={"year_month": str})
    source["stored_record_count"] = source["record_count"].astype(int)
    source["research_exact_month_record_count"] = source["stored_record_count"]
    source["research_date_adjustment"] = 0
    source["year_only_research_date_withheld"] = 0
    policy_index = source.set_index(["series", "year_month"]).index
    for item in mappings:
        old_month = item["stored_publication_date"][:7]
        old_key = ("policy_document", old_month)
        assert old_key in policy_index
        old_mask = (source.series == old_key[0]) & (source.year_month == old_key[1])
        source.loc[old_mask, "research_exact_month_record_count"] -= 1
        source.loc[old_mask, "research_date_adjustment"] -= 1
        if item["eligible_for_exact_month_view"]:
            new_month = item["research_publication_date"]
            new_key = ("policy_document", new_month)
            assert new_key in policy_index
            new_mask = (source.series == new_key[0]) & (source.year_month == new_key[1])
            source.loc[new_mask, "research_exact_month_record_count"] += 1
            source.loc[new_mask, "research_date_adjustment"] += 1
        else:
            source.loc[old_mask, "year_only_research_date_withheld"] += 1
    if (source["research_exact_month_record_count"] < 0).any():
        raise AssertionError("Negative corrected monthly count")
    source["record_count_basis"] = (
        "stored database publication date plus reviewed original-date remappings; year-only originals withheld from exact-month view"
    )
    source.to_csv(REPORTS / "monthly_reference_availability_corrected.csv", index=False)
    wide = source.pivot(index="year_month", columns="series", values="research_exact_month_record_count").astype(int)
    wide.to_csv(REPORTS / "monthly_record_counts_research_date_wide.csv")
    return source


STATUS_ORDER = ["blocked", "unknown", "unrequested", "partial", "complete", "confirmed_zero"]
STATUS_LABELS = {
    "blocked": "Access / original blocked",
    "unknown": "Denominator unknown",
    "unrequested": "Known target not requested",
    "partial": "Partial / bounded exclusion",
    "complete": "Verified route complete",
    "confirmed_zero": "Verified scope; zero records",
}
STATUS_COLORS = {
    "blocked": "#A6423A",
    "unknown": "#5F6B75",
    "unrequested": "#806493",
    "partial": "#D39A4A",
    "complete": "#2F766D",
    "confirmed_zero": "#C5DCD7",
}
STATUS_PRIORITY = {name: i for i, name in enumerate(STATUS_ORDER)}


def updated_coverage(ledger: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = pd.read_csv(TEMPORAL / "monthly_reference_availability.csv", dtype={"year_month": str})
    source["recovery_detail_status"] = "unchanged_from_prior_coverage_refresh"
    source["recovery_detail_note"] = ""
    for row in ledger.itertuples():
        mask = (source.series == row.series) & (source.year_month == row.year_month)
        source.loc[mask, "recovery_detail_status"] = row.final_status
        source.loc[mask, "recovery_detail_note"] = row.notes
        if row.final_status == "known_target_original_unavailable":
            source.loc[mask, "status"] = "blocked"
            source.loc[mask, "status_label"] = STATUS_LABELS["blocked"]
            source.loc[mask, "note"] = "Known target Cm 1200 (September 1990); catalogue verified but original scan unavailable on checked public route."
    # September 1990 is not one of the 31 completely blank months because the
    # answer series contains seven records.  It is nevertheless a specific
    # policy-series gap and therefore belongs in the refreshed coverage view.
    cm1200_mask = (source.series == "policy_document") & (source.year_month == "1990-09")
    source.loc[cm1200_mask, "status"] = "blocked"
    source.loc[cm1200_mask, "status_label"] = STATUS_LABELS["blocked"]
    source.loc[cm1200_mask, "recovery_detail_status"] = "known_target_original_unavailable"
    source.loc[cm1200_mask, "recovery_detail_note"] = "Cm 1200 is a verified September 1990 target; checked public scan route is access-restricted."
    source.loc[cm1200_mask, "note"] = "Known policy target Cm 1200; catalogue/date verified but full original unavailable on the checked public route."
    source.to_csv(REPORTS / "coverage_status_by_series_month_updated.csv", index=False)
    rows = []
    for (series, quarter), group in source.assign(
        year_quarter=source.year_month.map(lambda value: str(pd.Period(value, "M").asfreq("Q")))
    ).groupby(["series", "year_quarter"], sort=True):
        states = group.status.tolist()
        if states and all(value == "confirmed_zero" for value in states):
            state = "confirmed_zero"
        else:
            state = min((value for value in states if value != "confirmed_zero"), key=lambda value: STATUS_PRIORITY[value])
        rows.append(
            {
                "series": series,
                "series_label": SERIES_LABELS[series],
                "year_quarter": quarter,
                "year": int(quarter[:4]),
                "quarter": int(quarter[-1]),
                "status": state,
                "status_label": STATUS_LABELS[state],
                "record_count": int(group.record_count.sum()),
                "aggregation_rule": "worst monthly evidence state; confirmed zero only if every month is confirmed zero",
            }
        )
    quarterly = pd.DataFrame(rows)
    quarterly.to_csv(REPORTS / "coverage_status_by_series_quarter_updated.csv", index=False)
    return source, quarterly


def configure_plotting() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 9,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def plot_monthly_records(corrected: pd.DataFrame) -> dict[str, object]:
    configure_plotting()
    data = corrected.pivot(index="year_month", columns="series", values="research_exact_month_record_count").astype(int)
    assert len(data) == 465
    assert int(data.to_numpy().sum()) == 248_033
    colors = {"policy_document": "#24495F", "ministerial_written_answer": "#C57A43", "ministerial_written_statement": "#6F7D4C"}
    labels = {"policy_document": "Policy records", "ministerial_written_answer": "Written answers", "ministerial_written_statement": "Written statements"}
    order = ["ministerial_written_answer", "ministerial_written_statement", "policy_document"]
    ink, muted, gap, grid = "#20303A", "#5D6A70", "#F4E4E1", "#DFE3E4"
    fig, axes = plt.subplots(3, 1, figsize=(18, 10))
    fig.subplots_adjust(left=0.065, right=0.985, bottom=0.15, top=0.805, hspace=0.69)
    fig.text(0.065, 0.956, "Monthly government records across the study period", fontsize=22, fontweight="bold", color=ink)
    fig.text(0.065, 0.915, "January 1988 to 21 September 2026  |  One bar per month  |  Research-date view", fontsize=12, color=muted)
    handles = [Patch(facecolor=colors[key], label=labels[key], edgecolor="none") for key in ["policy_document", "ministerial_written_answer", "ministerial_written_statement"]]
    handles.append(Patch(facecolor=gap, label="No records in any of the three genres", edgecolor="none"))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.061, 0.883), ncol=4, frameon=False, handlelength=1.5, columnspacing=2)
    ylim = math.ceil(float(data.sum(axis=1).max()) / 500) * 500
    summaries = []
    for ax, (lo, hi), panel in zip(axes, [(1988, 2000), (2001, 2013), (2014, 2026)], "abc"):
        subset = data[(data.index.str[:4].astype(int) >= lo) & (data.index.str[:4].astype(int) <= hi)]
        n, x = len(subset), np.arange(len(subset))
        totals = subset.sum(axis=1)
        empty = np.flatnonzero(totals.to_numpy() == 0)
        for value in empty:
            ax.axvspan(value - 0.5, value + 0.5, color=gap, linewidth=0, zorder=0)
        ax.set_axisbelow(True)
        ax.grid(axis="y", color=grid, linewidth=0.55)
        bottom = np.zeros(n)
        for key in order:
            values = subset[key].to_numpy()
            ax.bar(x, values, bottom=bottom, width=0.86, color=colors[key], linewidth=0, zorder=2)
            bottom += values
        ax.set_ylim(0, ylim)
        ax.set_xlim(-0.65, 155.65)
        ax.set_yticks(np.arange(0, ylim + 1, 500))
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.set_ylabel("Records (count)", labelpad=12)
        ax.spines["left"].set_color("#B9C2C6")
        ax.spines["bottom"].set_color("#B9C2C6")
        ax.tick_params(axis="y", length=0, pad=5)
        ax.set_xticks([])
        for i, month_value in enumerate(subset.index):
            month = int(month_value[5:])
            ax.text(i, -0.085, "JFMAMJJASOND"[month - 1], ha="center", va="top", fontsize=6.8, color=muted, transform=ax.get_xaxis_transform())
            if month == 1:
                ax.text(i + 5.5, -0.205, month_value[:4], ha="center", va="top", fontsize=10, transform=ax.get_xaxis_transform())
                if i:
                    ax.axvline(i - 0.5, color=grid, linewidth=0.5, zorder=0)
        period = f"{lo}–{hi}" if hi != 2026 else "2014–September 2026"
        ax.text(-0.034, 1.10, panel, transform=ax.transAxes, fontsize=14, fontweight="bold", va="bottom")
        ax.text(0, 1.10, period, transform=ax.transAxes, fontsize=13, fontweight="bold", va="bottom")
        ax.text(1, 1.10, f"{int(totals.sum()):,} exact-month records  |  {n-len(empty)}/{n} months with records  |  {len(empty)} empty months", transform=ax.transAxes, ha="right", va="bottom", fontsize=10, color=muted)
        if n < 156:
            ax.axvspan(n - 0.5, 155.65, color="#F3F4F4", linewidth=0, zorder=0)
        summaries.append({"period": period, "months": n, "empty_months": len(empty), "records": int(totals.sum())})
    fig.text(0.065, 0.066, "Research-date view remaps 3 reviewed policy originals to verified publication months. Two year-only policy dates are withheld from exact-month counts.", fontsize=9.5, color=muted)
    fig.text(0.065, 0.037, "Shading marks zero observed records, not proof of no historical publications. September 2026 is partial; October–December 2026 are outside the cutoff.", fontsize=9.5, color=muted)
    stem = FIGURES / "monthly_government_records_research_date_landscape"
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig,
        axes=list(axes),
        panel_ids=list("abc"),
        column_groups=[["a", "b", "c"]],
        json_out=str(QA / "monthly_government_records_research_date_landscape.alignment.json"),
        overlay_svg=str(QA / "monthly_government_records_research_date_landscape.alignment.svg"),
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        require_panel_labels=False,
        strict=True,
    )
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".svg"))
    plt.close(fig)
    return {"records": int(data.to_numpy().sum()), "months": len(data), "empty_months": int((data.sum(axis=1) == 0).sum()), "panels": summaries}


def plot_coverage(monthly: pd.DataFrame, quarterly: pd.DataFrame) -> None:
    configure_plotting()
    colors = [STATUS_COLORS[name] for name in STATUS_ORDER]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(-0.5, len(colors) + 0.5), len(colors))
    code = {name: i for i, name in enumerate(STATUS_ORDER)}
    years = list(range(1988, 2027))
    fig, axes = plt.subplots(3, 2, figsize=(13.5, 8.4), gridspec_kw={"width_ratios": [0.78, 1.65], "hspace": 0.30, "wspace": 0.15})
    letters = iter("abcdef")
    for row_index, series in enumerate(SERIES):
        q = quarterly[quarterly.series == series]
        qgrid = np.full((len(years), 4), np.nan)
        for value in q.itertuples():
            qgrid[years.index(int(value.year)), int(value.quarter) - 1] = code[value.status]
        m = monthly[monthly.series == series]
        mgrid = np.full((len(years), 12), np.nan)
        for value in m.itertuples():
            mgrid[years.index(int(value.year)), int(value.month) - 1] = code[value.status]
        for col_index, (axis, grid, labels, title) in enumerate(
            [
                (axes[row_index, 0], qgrid, ["Q1", "Q2", "Q3", "Q4"], "quarter overview"),
                (axes[row_index, 1], mgrid, ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"], "monthly evidence"),
            ]
        ):
            axis.imshow(grid, aspect="auto", interpolation="nearest", cmap=cmap, norm=norm, origin="upper")
            axis.set_xticks(range(len(labels)), labels)
            tick_years = [1988, 1995, 2000, 2005, 2010, 2015, 2020, 2026]
            axis.set_yticks([years.index(year) for year in tick_years], [str(year) for year in tick_years] if col_index == 0 else [])
            axis.set_title(f"{next(letters)}  {SERIES_LABELS[series]} · {title}", loc="left", fontweight="bold")
            axis.tick_params(length=0)
            for spine in axis.spines.values():
                spine.set_color("#9CA7AD")
                spine.set_linewidth(0.5)
    legend = [Patch(facecolor=STATUS_COLORS[name], edgecolor="none", label=STATUS_LABELS[name]) for name in STATUS_ORDER]
    fig.legend(handles=legend, loc="lower center", ncol=6, frameon=False, bbox_to_anchor=(0.5, 0.022), fontsize=7.5, columnspacing=1.25)
    fig.suptitle("Government corpus coverage over time", x=0.055, y=0.985, ha="left", fontsize=15, fontweight="bold", color="#20303A")
    fig.text(0.055, 0.947, "1988-01 to 2026-09-21  |  Evidence state, not document volume or UK-government-wide coverage", ha="left", fontsize=8.5, color="#4F5D63")
    fig.text(0.055, 0.075, "Quarter status uses the worst monthly evidence state. The early-policy denominator remains unknown; 1990-09 is a known target blocked at full-text access.\nVerified zero applies only to the enumerated source scope. September 2026 is partial at the cutoff.", ha="left", va="top", fontsize=7.2, color="#4F5D63")
    fig.subplots_adjust(top=0.91, bottom=0.15, left=0.055, right=0.99)
    stem = FIGURES / "05_government_corpus_coverage_over_time_updated"
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig,
        axes=list(axes.flat),
        panel_ids=list("abcdef"),
        row_groups=[["a", "b"], ["c", "d"], ["e", "f"]],
        column_groups=[["a", "c", "e"], ["b", "d", "f"]],
        json_out=str(QA / "05_government_corpus_coverage_over_time_updated.alignment.json"),
        overlay_svg=str(QA / "05_government_corpus_coverage_over_time_updated.alignment.svg"),
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        require_panel_labels=False,
        strict=True,
    )
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".svg"))
    plt.close(fig)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    def clean(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    return "\n".join(
        ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|", *["| " + " | ".join(clean(value) for value in row) + " |" for row in rows]]
    )


def build_report(snapshot: dict[str, object], ledger: pd.DataFrame, mappings: list[dict], plot_summary: dict[str, object]) -> str:
    policy_counts = Counter(ledger[ledger.series == "policy_document"].final_status)
    parliament_counts = Counter(ledger[ledger.series != "policy_document"].final_status)
    mapping_rows = [
        [row["title"], row["stored_publication_date"], row["research_publication_date"], row["research_date_precision"], "yes" if row["eligible_for_exact_month_view"] else "no"]
        for row in mappings
    ]
    target_rows = [
        [row["command_number"], row["title"], row["original_publication_date"], row["current_status"]]
        for row in EARLY_POLICY_TARGETS
    ]
    return f"""# Historical coverage recovery: zero-month and early-policy audit

Generated: `{GENERATED_AT}`. Formal database mode: **read-only**.

## Current-tranche outcome

- New formal documents: **0**; new text segments: **0**; formal database writes: **0**.
- Existing originals date-reviewed: **5** — **3** can be reassigned to a verified publication month, while **2** remain year-only and are withheld from exact-month analysis.
- Previously blank months made non-zero: **0 of 31**. The date corrections land in months that already contained records.
- Within the 31 completely blank months, policy dispositions are **{policy_counts['catalogue_unknown_denominator']}** denominator-unknown and **{policy_counts['confirmed_zero_within_frozen_govuk_scope']}** confirmed zero only within the frozen current-DEFRA route.
- Parliamentary dispositions: **{parliament_counts['confirmed_zero_within_enumerated_parliamentary_scope']} of 62 genre-month rows** remain confirmed zero within the already enumerated Commons scope. Recess/dissolution is calendar context, not the enumeration denominator.
- The known missing September 1990 policy target is *This Common Inheritance* (Cm 1200). That month is **not** one of the 31 completely blank months because seven written answers are present. Its metadata and date were verified, but the checked scan is access-restricted; it was not counted as recovered.

## Formal 06 database snapshot

{markdown_table(['Metric', 'Count'], [
    ['Documents', f"{snapshot['documents']:,}"],
    ['Policy records', f"{snapshot['policy_records']:,}"],
    ['Ministerial written answers', f"{snapshot['written_answers']:,}"],
    ['Ministerial written statements', f"{snapshot['written_statements']:,}"],
    ['Text segments', f"{snapshot['text_segments']:,}"],
])}

This matches the post-repair baseline (248,035 documents and 3,668,275 text segments). No re-ingestion, full smoke test or full-database hash was run.

## Original-publication date decisions

{markdown_table(['Title', 'Stored date', 'Research date', 'Precision', 'Exact-month view'], mapping_rows)}

The stored GOV.UK dates and stable IDs are preserved as source metadata. The research-date CSV is a versioned analytical mapping, not an overwrite. Filenames and PDF creation timestamps were not used to manufacture exact dates.

## Bounded early-policy target register

{markdown_table(['Command', 'Title', 'Verified date', 'Status'], target_rows)}

No evidence-sufficient new full original was acquired. Catalogue records, bibliographic previews, excerpts, parliamentary citations and the UNFCCC summary are not substituted for full policy originals. The UK Government Web Archive route for Cm 4913 returned an access-control/WAF page; retries stopped without bypass.

## The 31 blank months

All 31 remain blank in the database and in the exact-month research view. That observation has three different meanings:

1. Written answers and statements: scoped confirmed zero after the prior applicable-route enumeration. Most months coincide with Commons recess or dissolution, but August 1991 included a recall and is therefore not explained solely by recess.
2. Policy records, 1988–2009: the predecessor-department catalogue denominator is still unknown. Separately, September 1990 is stronger evidence of a policy-series gap because a specific policy target is known but unavailable; seven written answers mean it is outside this 31-month all-series-zero set.
3. Policy records, April–May 2015: confirmed zero only within the frozen GOV.UK current-DEFRA policy query; this is not a claim about all departments.

The authoritative row-level decision is in `month_recovery_ledger.csv`; unknown candidates are not converted to a numeric missing-document total.

## Refreshed views

![Monthly records using reviewed research dates](figures/monthly_government_records_research_date_landscape.png)

The exact-month research view contains **{plot_summary['records']:,}** of the **{snapshot['documents']:,}** database records. Two policy originals with year-only dates are deliberately withheld, and the companion CSV preserves both stored and research counts.

![Government corpus coverage over time](figures/05_government_corpus_coverage_over_time_updated.png)

The second figure encodes evidence state, not document volume or a UK-government-wide coverage percentage. Quarterly cells use the worst monthly evidence state; monthly data remain in the paired CSV.

## Next bounded actions

- Pursue institutional/official-library copies by command number and ISBN for Cm 1200, 2426, 2427, 4345 and 4913. This improves early-policy full-text coverage without expanding modern data.
- Keep year-only original dates out of monthly/quarterly comparisons until an independent month is verified.
- Do not retry the WAF/captcha route automatically. Resume only through an ordinary lawful archive or library access path.
- Retain the policy series as partial/unknown for 1988–2009; do not interpret its zeros as absence of policy activity.

## Delivered evidence

- `month_recovery_ledger.csv`: 31 months × 3 genres, before/after counts and scoped decisions.
- `research_publication_date_mapping_v1.csv`: five reviewed originals with page-level evidence and hashes.
- `early_policy_target_register.csv`: six bounded policy targets and exact next steps.
- `source_evidence_log.csv`: source route, real response evidence where captured, and stop decisions.
- `actual_acquisition_manifest.csv`: current-tranche outcome; no new full original.
- `incremental_reconciliation.csv`: unchanged formal-database counts.
- `reports/monthly_reference_availability_corrected.csv`: stored-date and research-date counts kept side by side.
- `reports/coverage_status_by_series_month_updated.csv`: refreshed monthly evidence state.
"""


def build_html(markdown_report: str) -> str:
    # A deliberately compact standalone page; the Markdown remains the full report.
    policy_rows = "".join(
        f"<tr><td>{html.escape(row['command_number'])}</td><td>{html.escape(row['title'])}</td><td>{html.escape(row['original_publication_date'])}</td><td>{html.escape(row['current_status'])}</td></tr>"
        for row in EARLY_POLICY_TARGETS
    )
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Historical coverage recovery</title><style>
body{{font-family:Arial,sans-serif;max-width:1180px;margin:36px auto;padding:0 24px;color:#20303A;line-height:1.5}}h1,h2{{color:#24495F}}.callout{{background:#F3F6F6;border-left:5px solid #2F766D;padding:14px 18px}}img{{width:100%;height:auto;margin:10px 0 28px;border:1px solid #D8DFE1}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #D8DFE1;padding:8px;text-align:left;vertical-align:top}}th{{background:#EEF2F3}}code{{background:#F3F4F4;padding:2px 4px}}a{{color:#245A73}}
</style></head><body><h1>Historical coverage recovery</h1>
<div class='callout'><strong>Current tranche:</strong> 0 new documents; 5 existing originals date-reviewed; 3 exact-month reassignments; 2 year-only dates withheld; 0 of 31 blank months became non-zero.</div>
<h2>What changed</h2><p>The formal 06 database was read only. September 1990 is now a known missing policy target rather than an undifferentiated zero; most other early-policy months still have an unknown population denominator.</p>
<h2>Monthly record view</h2><img src='figures/monthly_government_records_research_date_landscape.svg' alt='Monthly government records using reviewed research dates'>
<h2>Coverage evidence state</h2><img src='figures/05_government_corpus_coverage_over_time_updated.svg' alt='Government corpus coverage over time'>
<h2>Early-policy targets</h2><table><thead><tr><th>Command</th><th>Title</th><th>Date</th><th>Status</th></tr></thead><tbody>{policy_rows}</tbody></table>
<h2>Files</h2><ul><li><a href='../month_recovery_ledger.csv'>31-month recovery ledger</a></li><li><a href='../research_publication_date_mapping_v1.csv'>Date mapping</a></li><li><a href='../early_policy_target_register.csv'>Policy targets</a></li><li><a href='../source_evidence_log.csv'>Source evidence</a></li><li><a href='historical_coverage_recovery_report.md'>Markdown report</a></li></ul>
<p><small>Generated {html.escape(GENERATED_AT)}. Counts and coverage states are deliberately separate.</small></p></body></html>"""


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    write_access_evidence()
    snapshot = snapshot_db()
    assert snapshot["documents"] == 248_035, snapshot
    assert snapshot["policy_records"] == 1_055, snapshot
    assert snapshot["written_answers"] == 244_229, snapshot
    assert snapshot["written_statements"] == 2_751, snapshot
    assert snapshot["text_segments"] == 3_668_275, snapshot
    assert snapshot["reviewed_document_ids_present"] == 5, snapshot
    assert snapshot["reviewed_content_versions_present"] == 5, snapshot

    mappings = enrich_date_mappings()
    write_csv(HERE / "research_publication_date_mapping_v1.csv", mappings)
    write_csv(HERE / "early_policy_target_register.csv", EARLY_POLICY_TARGETS)
    evidence_rows = [{**row, "checked_at": GENERATED_AT} for row in SOURCE_EVIDENCE]
    write_csv(HERE / "source_evidence_log.csv", evidence_rows)

    ledger = finalise_month_ledger()
    corrected = corrected_monthly_view(mappings)
    coverage_monthly, coverage_quarterly = updated_coverage(ledger)
    monthly_summary = plot_monthly_records(corrected)
    plot_coverage(coverage_monthly, coverage_quarterly)

    acquisition_rows = []
    for row in EARLY_POLICY_TARGETS:
        acquisition_rows.append(
            {
                "title": row["title"],
                "command_number": row["command_number"],
                "target_date": row["original_publication_date"],
                "route_checked": row["full_text_route"],
                "result": row["route_result"],
                "new_original_acquired": False,
                "new_document_id": "",
                "new_content_object_id": "",
                "formal_database_written": False,
                "checked_at": GENERATED_AT,
            }
        )
    write_csv(HERE / "actual_acquisition_manifest.csv", acquisition_rows)
    excluded = [
        {
            "candidate": "UNFCCC gbr01.pdf",
            "candidate_url": "https://unfccc.int/cop5/resource/docs/nc/gbr01.pdf",
            "decision": "excluded_as_full_original_substitute",
            "reason": "17-page summary/national communication is not the 80-page Cm 2427 command paper.",
        },
        {
            "candidate": "Studyres transcript of Cm 4913",
            "candidate_url": "https://studyres.com/doc/4040387/detr---climate-change",
            "decision": "excluded_as_acquisition_source",
            "reason": "Third-party transcript was not verified as a complete, authoritative original.",
        },
    ]
    write_csv(HERE / "excluded_alternatives.csv", excluded)

    reconciliation = [
        {
            "metric": key,
            "before": snapshot[key],
            "after": snapshot[key],
            "delta": 0,
            "unit": "record" if key != "text_segments" else "text segment",
            "note": "Formal 06 database was opened read-only; no current-tranche original met insertion conditions.",
        }
        for key in ["documents", "policy_records", "written_answers", "written_statements", "text_segments"]
    ]
    reconciliation.extend(
        [
            {"metric": "reviewed_existing_originals", "before": 0, "after": 5, "delta": 5, "unit": "existing policy original", "note": "Versioned analytical evidence only; not a database insert."},
            {"metric": "exact_month_reassignments", "before": 0, "after": 3, "delta": 3, "unit": "date mapping", "note": "Used only in research-date view."},
            {"metric": "year_only_dates_withheld", "before": 0, "after": 2, "delta": 2, "unit": "date mapping", "note": "Not assigned to a month."},
            {"metric": "blank_months_made_nonzero", "before": 31, "after": 31, "delta": 0, "unit": "month", "note": "No evidence-sufficient new full original acquired."},
        ]
    )
    write_csv(HERE / "incremental_reconciliation.csv", reconciliation)
    write_json(REPORTS / "database_snapshot.json", snapshot)
    write_json(REPORTS / "monthly_plot_summary.json", monthly_summary)

    report = build_report(snapshot, ledger, mappings, monthly_summary)
    (REPORTS / "historical_coverage_recovery_report.md").write_text(report, encoding="utf-8")
    (REPORTS / "historical_coverage_recovery_report.html").write_text(build_html(report), encoding="utf-8")

    verification = {
        "generated_at": GENERATED_AT,
        "database_read_only": True,
        "database_counts": snapshot,
        "ledger_rows": len(ledger),
        "ledger_months": int(ledger.year_month.nunique()),
        "ledger_genres_per_month_ok": bool(ledger.groupby("year_month").series.nunique().eq(3).all()),
        "all_before_after_counts_zero": bool(ledger.before_record_count.eq(0).all() and ledger.after_record_count.eq(0).all()),
        "date_mappings": len(mappings),
        "exact_month_mappings": sum(bool(row["eligible_for_exact_month_view"]) for row in mappings),
        "year_only_mappings": sum(not bool(row["eligible_for_exact_month_view"]) for row in mappings),
        "new_originals": 0,
        "database_delta": 0,
        "research_exact_month_total": int(corrected.research_exact_month_record_count.sum()),
        "stored_total": int(corrected.stored_record_count.sum()),
        "zero_months_after": int(
            corrected.pivot(index="year_month", columns="series", values="research_exact_month_record_count").sum(axis=1).eq(0).sum()
        ),
        "cm1200_month_policy_count": int(
            corrected[(corrected.series == "policy_document") & (corrected.year_month == "1990-09")].stored_record_count.iloc[0]
        ),
        "cm1200_month_answer_count": int(
            corrected[(corrected.series == "ministerial_written_answer") & (corrected.year_month == "1990-09")].stored_record_count.iloc[0]
        ),
        "figure_files_exist": all(
            path.exists()
            for path in [
                FIGURES / "monthly_government_records_research_date_landscape.png",
                FIGURES / "monthly_government_records_research_date_landscape.pdf",
                FIGURES / "monthly_government_records_research_date_landscape.svg",
                FIGURES / "05_government_corpus_coverage_over_time_updated.png",
                FIGURES / "05_government_corpus_coverage_over_time_updated.pdf",
                FIGURES / "05_government_corpus_coverage_over_time_updated.svg",
            ]
        ),
    }
    assert verification["ledger_rows"] == 93
    assert verification["ledger_months"] == 31
    assert verification["research_exact_month_total"] == 248_033
    assert verification["stored_total"] == 248_035
    assert verification["zero_months_after"] == 31
    assert verification["cm1200_month_policy_count"] == 0
    assert verification["cm1200_month_answer_count"] == 7
    assert verification["figure_files_exist"]
    write_json(REPORTS / "verification_summary.json", verification)
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
