#!/usr/bin/env python3
"""Coverage-first recovery for bounded historical government gaps.

This script intentionally works only on the frozen gaps named in the 2026-09-22
decision/handoff.  It enumerates a mirror, downloads individual XML files, derives
traceable records, deduplicates them against the formal 06 database, and commits
genuinely new identities in bounded transactions.  It also recovers one verified
early policy publication from an official archived GOV.UK route.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import duckdb
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[4]
WORK = ROOT / "work_packages/M1_source_access/07_historical_government_acquisition"
OUT = WORK / "historical_coverage_recovery"
RAW = OUT / "raw"
EVIDENCE = OUT / "evidence"
MANIFESTS = OUT / "manifests"
CHECKPOINTS = OUT / "checkpoints"
REPORTS = OUT / "reports"
RECOVERY = OUT / "recovery"
DB = ROOT / "work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb"
BASE_MANIFESTS = WORK / "manifests"
TARGETED = WORK / "targeted_gap_repair"
HGA_PATH = WORK / "historical_government_acquisition.py"

SCRIPT_VERSION = "historical_coverage_recovery_v1"
EXTRACTOR_VERSION = "parlparse_xml_derived_records_v1"
POLICY_EXTRACTOR_VERSION = "official_archived_pdf_text_v1"
CUTOFF = date(2026, 9, 21)
MIRROR_HTTP = "https://www.theyworkforyou.com/pwdata/scrapedxml"
MIRROR_RSYNC = "data.theyworkforyou.com::parldata/scrapedxml"
PARLIAMENT_SOURCE_NAME = "ParlParse/TheyWorkForYou mirror — Commons written answers/statements"
PARLIAMENT_SOURCE_ID = "src_" + hashlib.sha256(PARLIAMENT_SOURCE_NAME.encode()).hexdigest()[:20]
PARLIAMENT_BATCH_ID = "commons_parlparse_targeted_gap_recovery_20260922_v1"
POLICY_BATCH_ID = "govuk_historical_policy_targeted_recovery_20260922_v1"
POLICY_SOURCE_ID = "src_eaf57ccafde8ffd97f7e"

APPROVED_2004_DEPARTMENTS = {
    "TRADE AND INDUSTRY",
    "ENVIRONMENT FOOD AND RURAL AFFAIRS",
}
APPROVED_GAP_DEPARTMENTS = {
    "ENERGY AND CLIMATE CHANGE",
    "ENVIRONMENT FOOD AND RURAL AFFAIRS",
}
BERR = "BUSINESS, ENTERPRISE AND REGULATORY REFORM"
EXCLUDED_IDS = {
    "90ab8a69-5a83-41d5-8761-35c4051f3a77": "Asda: saved navigator/detail evidence resolves to inconsistent department attribution",
    "06071282000011": "Asda: saved detail contains no separable question/response text",
    "historic-item_4d25e8510d84ee46f2e3": "Self-regulating Bodies: mixed text cannot be reliably separated or attributed",
    "1009068000001": "Cross-date Written Ministerial Statements container; identified children retained separately",
}

POLICY_CANDIDATES = [
    {
        "external_id": "govuk-command-paper:cm-2428",
        "title": "Biodiversity: the UK action plan",
        "publication_date": "1994-01-25",
        "publisher": "UK Government / Department of the Environment",
        "organisation": "Department of the Environment",
        "landing_url": "https://www.gov.uk/government/publications/biodiversity-the-uk-action-plan",
        "content_api_url": "https://www.gov.uk/api/content/government/publications/biodiversity-the-uk-action-plan",
        "fallback_pdf_url": "https://assets.publishing.service.gov.uk/media/5a7ced59ed915d2017106d17/2428.pdf",
        "publication_number": "Cm 2428",
        "isbn": "0101242824",
        "reason": "Verified official 1994 policy paper absent from the formal database; exact title/date/command number available on GOV.UK.",
    }
]


def _load_hga() -> Any:
    spec = importlib.util.spec_from_file_location("historical_government_acquisition", HGA_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {HGA_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hga = _load_hga()


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dirs() -> None:
    for path in [RAW, EVIDENCE, MANIFESTS, CHECKPOINTS, REPORTS, RECOVERY]:
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str] | None = None) -> None:
    hga.write_csv(path, list(rows), columns)


def write_json(path: Path, value: Any) -> None:
    hga.write_json(path, value)


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def sha(path: Path) -> str:
    return hga.sha256_file(path)


def norm(value: str) -> str:
    return hga.normalise_space(value)


def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm(value).lower())


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def bootstrap() -> dict[str, Any]:
    """Freeze target units and source-route decisions before any acquisition."""
    ensure_dirs()
    index_rows = read_csv(BASE_MANIFESTS / "hansard_gap_archive_index_status.csv")
    failed_indexes = [row for row in index_rows if row.get("status") != "success"]
    page_rows = read_csv(BASE_MANIFESTS / "hansard_gap_archive_page_acquisition_status.csv")
    failed_pages = [row for row in page_rows if row.get("download_status") != "success"]
    unrequested = read_csv(BASE_MANIFESTS / "hansard_gap_archive_unprocessed_page_targets.csv")
    historic_days = read_csv(TARGETED / "evidence/historic_daily_index_status.csv")
    seam_dates = sorted(
        {
            row["date"]
            for row in historic_days
            if "2004-10-05" <= row.get("date", "") <= "2004-12-31"
        }
    )
    date_reasons: dict[str, set[str]] = defaultdict(set)
    for value in seam_dates:
        date_reasons[value].add("2004_q4_commons_seam")
    for row in failed_indexes:
        date_reasons[row["date"]].add("failed_date_index")
    for row in failed_pages:
        date_reasons[row["date"]].add("failed_known_page")
    for row in unrequested:
        date_reasons[row["date"]].add("unrequested_known_page")
    date_reasons["2007-09-17"].add("companies_house_named_access_failure")
    targets = [
        {
            "date": value,
            "year": value[:4],
            "reasons": ";".join(sorted(reasons)),
            "wrans": True,
            "wms": "2004_q4_commons_seam" in reasons,
        }
        for value, reasons in sorted(date_reasons.items())
    ]
    write_csv(MANIFESTS / "parlparse_target_dates.csv", targets)

    gap_rows = [
        {
            "gap_id": "policy:early-predecessor-departments",
            "department_scope": "DoE; MAFF; DETR; DTI; BERR; DECC; DEFRA predecessors",
            "genre": "policy_document",
            "time_interval": "1988-01-01..2009-12-31",
            "unit": "publication population",
            "denominator": "unknown",
            "missing_level": "catalogue/index plus known publication text",
            "baseline_evidence": "GOV.UK historical manifest has 35 enumerated / 34 net-new records and is not a complete predecessor-department historical catalogue.",
            "priority": "highest",
            "current_status": "partial_unknown_population",
        },
        {
            "gap_id": "parliament:commons-2004-q4-seam",
            "department_scope": "DTI; DEFRA",
            "genre": "ministerial_written_answer;ministerial_written_statement",
            "time_interval": "2004-10-05..2004-12-31",
            "unit": "dated mirror files then records",
            "denominator": "unknown until bounded mirror enumeration",
            "missing_level": "date/window index and record text",
            "baseline_evidence": f"Historic route checked {len(seam_dates)} sitting dates but exposed Lords only; no Commons zero claim.",
            "priority": "highest",
            "current_status": "enumeration_incomplete",
        },
        {
            "gap_id": "parliament:answer-index-failures-2010-2014",
            "department_scope": "DECC; DEFRA",
            "genre": "ministerial_written_answer",
            "time_interval": "2010-05-01..2014-09-11",
            "unit": "date index",
            "denominator": len(index_rows),
            "missing_level": "index",
            "baseline_evidence": f"{len(failed_indexes)} failed date indexes among {len(index_rows)} planned date indexes.",
            "priority": "highest",
            "current_status": "enumeration_incomplete",
        },
        {
            "gap_id": "parliament:answer-page-failures-2010-2014",
            "department_scope": "DECC; DEFRA",
            "genre": "ministerial_written_answer",
            "time_interval": "2010-05-01..2014-09-11",
            "unit": "known archive page",
            "denominator": len(page_rows),
            "missing_level": "page text",
            "baseline_evidence": f"{len(failed_pages)} known pages failed among {len(page_rows)} attempted pages.",
            "priority": "highest",
            "current_status": "complete_enumeration_with_failures",
        },
        {
            "gap_id": "parliament:answer-unrequested-pages-2010-2014",
            "department_scope": "DECC; DEFRA",
            "genre": "ministerial_written_answer",
            "time_interval": "2010-05-01..2014-09-11",
            "unit": "known archive page",
            "denominator": len(unrequested),
            "missing_level": "page never requested",
            "baseline_evidence": f"{len(unrequested)} separately enumerated known pages were not requested after the dynamic throttle stop.",
            "priority": "highest",
            "current_status": "not_requested",
        },
        {
            "gap_id": "parliament:companies-house-2007-09-17",
            "department_scope": "BERR",
            "genre": "ministerial_written_answer",
            "time_interval": "2007-09-17",
            "unit": "named answer target",
            "denominator": 1,
            "missing_level": "record text",
            "baseline_evidence": "Official detail route failed for external ID 07091719000037; ambiguity was not established.",
            "priority": "high",
            "current_status": "access_failure_recovery_target",
        },
    ]
    write_csv(OUT / "historical_gap_register.csv", gap_rows)

    route_rows = [
        {
            "route_id": "parlparse_twf_xml",
            "scope": "Commons written answers and written ministerial statements",
            "years_checked": "2001 onward; bounded target dates only",
            "provider": "mySociety ParlParse / TheyWorkForYou",
            "route_url": "https://parser.theyworkforyou.com/hansard.html",
            "holdings_evidence": "rsync directory exposes separate wrans and wms XML; files retain question/reply structure, speakers and original Parliament URLs.",
            "access_method": "rsync list-only enumeration; individual HTTPS XML acquisition",
            "rights_access": "public mirror; derived records retained for internal research; original Parliament URL preserved",
            "identity_mapping": "date + Commons + department + question number/original URL/text fingerprint; provider ID alone is insufficient",
            "decision": "selected_bounded",
            "reason": "Representative overlap and missing-window samples parsed successfully; no whole mirror download.",
        },
        {
            "route_id": "ukgwa_department_archives",
            "scope": "DTI/BERR/DECC/DoE/DETR/MAFF/DEFRA historical policy pages and files",
            "years_checked": "1988-2009",
            "provider": "UK Government Web Archive / The National Archives",
            "route_url": "https://www.nationalarchives.gov.uk/webarchive/",
            "holdings_evidence": "Archive starts in 2003 with some earlier captures; snapshots are selective rather than a complete backup.",
            "access_method": "normal public archive/search routes",
            "rights_access": "Crown/OGL commonly applies, with item exceptions; internal-use status retained",
            "identity_mapping": "original department URL + title + date + publication number",
            "decision": "unavailable_current_host",
            "reason": "Normal UKGWA route returned an AWS WAF challenge. The denied route was not repeatedly hit or bypassed.",
        },
        {
            "route_id": "tna_discovery_catalogue",
            "scope": "official catalogue evidence for predecessor-department records",
            "years_checked": "1988-2009",
            "provider": "The National Archives Discovery",
            "route_url": "https://discovery.nationalarchives.gov.uk/API/search/v1/records",
            "holdings_evidence": "Discovery describes archival records and may establish identifiers/holdings; a catalogue hit is not full policy text.",
            "access_method": "public search/API metadata",
            "rights_access": "catalogue metadata only unless a separately downloadable replica is verified",
            "identity_mapping": "catalogue reference + issuing department + title + covering dates",
            "decision": "catalogue_evidence_only",
            "reason": "Useful for target formation; not admitted as recovered full text without an exact public replica.",
        },
        {
            "route_id": "govuk_archived_command_papers",
            "scope": "individually verified historical policy papers omitted from the predecessor query",
            "years_checked": "1988-2009",
            "provider": "GOV.UK / assets.publishing.service.gov.uk",
            "route_url": POLICY_CANDIDATES[0]["landing_url"],
            "holdings_evidence": "GOV.UK labels Biodiversity: the UK action plan as a policy paper, dated 25 January 1994, ISBN 0101242824, Cm 2428, with a 194-page PDF.",
            "access_method": "single Content API/landing-page/PDF request",
            "rights_access": "official Crown publication; internal-use status retained and page-level exceptions remain possible",
            "identity_mapping": "exact title + publication date + Cm 2428 + ISBN + official PDF",
            "decision": "selected_single_verified_target",
            "reason": "Exact official policy identity and full-text attachment are available; absent from formal database at baseline.",
        },
        {
            "route_id": "jncc_institutional_copy_cm2428",
            "scope": "Biodiversity: the UK action plan (1994)",
            "years_checked": "1994",
            "provider": "Joint Nature Conservation Committee Resource Hub",
            "route_url": "https://jncc.gov.uk/resources/cb0ef1c9-2325-4d17-9f87-a5c84fe400bd",
            "holdings_evidence": "JNCC describes the same UK Government action plan and supplies a PDF with no public-access limitation under OGL 3.0.",
            "access_method": "institutional repository fallback",
            "rights_access": "JNCC metadata states OGL 3.0 and no public-access limitation",
            "identity_mapping": "same 1994 title/content; GOV.UK official PDF selected as primary copy",
            "decision": "verified_fallback_not_downloaded",
            "reason": "Retained as an independent fallback; not downloaded because the official GOV.UK copy is available.",
        },
    ]
    write_csv(OUT / "alternative_source_register.csv", route_rows)

    exclusion_rows = [
        {
            "target_id": key,
            "disposition": "excluded_ambiguous_text_or_attribution" if key != "1009068000001" else "excluded_non_includable_container",
            "reason": reason,
            "raw_evidence_retained": True,
            "counted_as_recovered": False,
        }
        for key, reason in EXCLUDED_IDS.items()
    ]
    write_csv(OUT / "exclusion_ledger.csv", exclusion_rows)
    result = {
        "generated_at": now_iso(),
        "baseline": {"documents": 239586, "text_segments": 3623437},
        "failed_date_indexes": len(failed_indexes),
        "failed_known_pages": len(failed_pages),
        "unrequested_known_pages": len(unrequested),
        "seam_sitting_dates_checked": len(seam_dates),
        "unique_target_dates": len(targets),
        "exclusions": len(exclusion_rows),
    }
    write_json(REPORTS / "bootstrap_summary.json", result)
    return result


def enumerate_mirror() -> dict[str, Any]:
    """List only target-year mirror directories and freeze matching filenames."""
    ensure_dirs()
    targets = read_csv(MANIFESTS / "parlparse_target_dates.csv")
    if not targets:
        raise RuntimeError("Run bootstrap first")
    target_dates = {row["date"]: row for row in targets}
    years_by_kind: dict[str, set[int]] = defaultdict(set)
    for row in targets:
        if row.get("wrans") == "True":
            years_by_kind["wrans"].add(int(row["year"]))
        if row.get("wms") == "True":
            years_by_kind["wms"].add(int(row["year"]))
    listed: list[dict[str, Any]] = []
    listing_runs: list[dict[str, Any]] = []
    for kind, years in sorted(years_by_kind.items()):
        for year in sorted(years):
            command = ["rsync", "--list-only", f"{MIRROR_RSYNC}/{kind}/{'answers' if kind == 'wrans' else 'ministerial'}{year}-*"]
            started = now_iso()
            proc = subprocess.run(command, capture_output=True, text=True, timeout=180)
            listing_runs.append(
                {
                    "kind": kind,
                    "year": year,
                    "started_at": started,
                    "finished_at": now_iso(),
                    "command": " ".join(command),
                    "return_code": proc.returncode,
                    "stderr": norm(proc.stderr),
                }
            )
            if proc.returncode not in {0, 23}:
                continue
            for line in proc.stdout.splitlines():
                match = re.search(r"([^\s/]+\.xml)$", line)
                if not match:
                    continue
                filename = match.group(1)
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
                if not date_match or date_match.group(1) not in target_dates:
                    continue
                target = target_dates[date_match.group(1)]
                if kind == "wms" and target.get("wms") != "True":
                    continue
                size_match = re.match(r"\S+\s+([0-9,]+)\s+(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s+", line)
                listed.append(
                    {
                        "file_id": hga.stable_id("mirror-file", kind, filename),
                        "kind": kind,
                        "record_genre": "ministerial_written_answer" if kind == "wrans" else "ministerial_written_statement",
                        "date": date_match.group(1),
                        "year": year,
                        "filename": filename,
                        "size_from_listing": (size_match.group(1).replace(",", "") if size_match else ""),
                        "remote_mtime": (size_match.group(2) if size_match else ""),
                        "listing_route": command[-1],
                        "target_reasons": target["reasons"],
                        "request_url": f"{MIRROR_HTTP}/{kind}/{filename}",
                        "enumerated_at": now_iso(),
                    }
                )
    listed = sorted({(row["kind"], row["filename"]): row for row in listed}.values(), key=lambda row: (row["date"], row["kind"], row["filename"]))
    write_csv(MANIFESTS / "parlparse_remote_file_manifest.csv", listed)
    write_csv(EVIDENCE / "parlparse_rsync_listing_runs.csv", listing_runs)
    by_date = Counter(row["date"] for row in listed)
    date_rows = []
    for target in targets:
        date_rows.append(
            {
                **target,
                "enumerated_files": by_date[target["date"]],
                "mirror_date_status": "files_enumerated" if by_date[target["date"]] else "no_matching_mirror_file",
                "note": "No matching mirror file is not treated as proof of zero official records." if not by_date[target["date"]] else "",
            }
        )
    write_csv(EVIDENCE / "parlparse_target_date_enumeration.csv", date_rows)
    result = {
        "generated_at": now_iso(),
        "target_dates": len(targets),
        "enumerated_files": len(listed),
        "dates_with_files": len(by_date),
        "dates_without_files": len(targets) - len(by_date),
        "by_kind": dict(Counter(row["kind"] for row in listed)),
    }
    write_json(REPORTS / "mirror_enumeration_summary.json", result)
    return result


def _node_text(element: ET.Element) -> str:
    return norm(" ".join(part for part in element.itertext() if part))


def _block_values(element: ET.Element) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    candidates = list(element)
    if not candidates:
        candidates = [element]
    for index, child in enumerate(candidates, start=1):
        text = _node_text(child)
        if not text:
            continue
        if child.tag == "table":
            rows = []
            for tr in child.findall(".//tr"):
                cells = [_node_text(cell) for cell in tr if cell.tag in {"td", "th"}]
                if any(cells):
                    rows.append(" | ".join(value for value in cells if value))
            text = " || ".join(rows) or text
        output.append({"text": text, "paragraph_id": child.attrib.get("pid") or f"block:{index}"})
    return output


def parse_xml(path: Path, genre: str, sitting_date: str) -> list[dict[str, Any]]:
    root = ET.parse(path).getroot()
    current_department = ""
    current_title = ""
    questions: list[dict[str, str]] = []
    responses: list[dict[str, str]] = []
    output: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal questions, responses
        if genre.endswith("answer") and (not questions or not responses):
            questions, responses = [], []
            return
        if genre.endswith("statement") and not responses:
            questions, responses = [], []
            return
        qnums = sorted({value.get("qnum", "") for value in questions if value.get("qnum")})
        seed = (questions[0].get("publicwhip_id") if questions else responses[0].get("publicwhip_id")) or hga.stable_id(
            "mirror-record", sitting_date, current_department, current_title, hga.canonical_json(responses)
        )
        base_id = re.sub(r"\.(?:q|r)\d+$", "", seed)
        external_id = f"parlparse:{base_id}"
        canonical = next((value.get("url") for value in questions + responses if value.get("url")), "")
        if canonical.startswith("http://"):
            canonical = "https://" + canonical[len("http://") :]
        respondent = next((value.get("speaker") for value in responses if value.get("speaker")), "")
        output.append(
            {
                "external_id": external_id,
                "genre": genre,
                "house": "Commons",
                "sitting_date": sitting_date,
                "department": current_department,
                "title": current_title or ("Written ministerial statement" if genre.endswith("statement") else "Written answer"),
                "questions": [{key: value for key, value in item.items() if key in {"speaker", "text", "paragraph_id"}} for item in questions],
                "responses": [{key: value for key, value in item.items() if key in {"speaker", "text", "paragraph_id"}} for item in responses],
                "canonical_url": canonical or f"https://www.theyworkforyou.com/search/?q={external_id}",
                "government_respondent": respondent,
                "attribution_status": "confirmed" if respondent else "pending",
                "uin": ";".join(qnums),
                "qnums": qnums,
                "source_category": "Commons Written Answers" if genre.endswith("answer") else "Commons Written Ministerial Statements",
                "provider_record_id": base_id,
                "record_is_derived": True,
            }
        )
        questions, responses = [], []

    for child in root:
        tag = child.tag
        if tag == "major-heading":
            flush()
            current_department = hga.normalise_label(_node_text(child))
            current_title = ""
        elif tag == "minor-heading":
            flush()
            current_title = _node_text(child)
        elif tag == "ques":
            if responses:
                flush()
            blocks = _block_values(child)
            qnum = next((node.attrib.get("qnum", "") for node in child.iter() if node.attrib.get("qnum")), "")
            text = " ".join(value["text"] for value in blocks)
            questions.append(
                {
                    "speaker": norm(child.attrib.get("speakername", "")),
                    "text": text,
                    "paragraph_id": blocks[0]["paragraph_id"] if blocks else child.attrib.get("id", ""),
                    "qnum": qnum,
                    "publicwhip_id": child.attrib.get("id", ""),
                    "url": child.attrib.get("url", ""),
                }
            )
        elif tag in {"reply", "speech"}:
            for block in _block_values(child):
                responses.append(
                    {
                        "speaker": norm(child.attrib.get("speakername", "")),
                        "text": block["text"],
                        "paragraph_id": block["paragraph_id"],
                        "publicwhip_id": child.attrib.get("id", ""),
                        "url": child.attrib.get("url", ""),
                    }
                )
    flush()
    return output


def validate_samples() -> dict[str, Any]:
    ensure_dirs()
    sample_root = RAW / "parlparse/wrans/validation"
    samples = [
        (sample_root / "answers2004-10-04.xml", "ministerial_written_answer", "2004-10-04", "official_historic_overlap"),
        (sample_root / "answers2004-10-11.xml", "ministerial_written_answer", "2004-10-11", "missing_seam_sample"),
        (sample_root / "answers2012-01-11a.xml", "ministerial_written_answer", "2012-01-11", "official_publications_overlap"),
    ]
    rows: list[dict[str, Any]] = []
    overlap_qnums: set[str] = set()
    for row in read_csv(BASE_MANIFESTS / "hansard_gap_archive_answer_manifest.csv"):
        if row.get("date") != "2012-01-11":
            continue
        record_path = ROOT / row["record_path"]
        if not record_path.exists():
            continue
        payload = json.loads(record_path.read_text(encoding="utf-8"))
        for question in payload.get("questions") or []:
            overlap_qnums.update(re.findall(r"\[(\d+[A-Z]?)\]", question.get("text", "")))
    for path, genre, sitting_date, role in samples:
        records = parse_xml(path, genre, sitting_date)
        approved = [
            record
            for record in records
            if record["department"] in (APPROVED_2004_DEPARTMENTS if sitting_date.startswith("2004") else APPROVED_GAP_DEPARTMENTS)
        ]
        sample_qnums = {qnum for record in approved for qnum in record.get("qnums", [])}
        rows.append(
            {
                "sample_role": role,
                "date": sitting_date,
                "path": rel(path),
                "sha256": sha(path),
                "all_question_reply_groups": len(records),
                "approved_department_groups": len(approved),
                "departments": json.dumps(sorted({record["department"] for record in approved})),
                "groups_with_question": sum(bool(record["questions"]) for record in approved),
                "groups_with_reply": sum(bool(record["responses"]) for record in approved),
                "original_urls_present": sum(record["canonical_url"].startswith("https://www.publications.parliament.uk") for record in approved),
                "official_overlap_qnum_matches": len(sample_qnums & overlap_qnums) if sitting_date == "2012-01-11" else "not_applicable",
                "decision": "validated_for_bounded_recovery",
            }
        )
    write_csv(EVIDENCE / "parlparse_sample_validation.csv", rows)
    result = {
        "generated_at": now_iso(),
        "samples": len(rows),
        "all_samples_parse": all(int(row["all_question_reply_groups"]) > 0 for row in rows),
        "official_2012_question_number_matches": next(row["official_overlap_qnum_matches"] for row in rows if row["date"] == "2012-01-11"),
        "decision": "validated_for_bounded_target_dates",
    }
    write_json(REPORTS / "parlparse_validation_summary.json", result)
    return result


def _fetch(session: requests.Session, url: str, path: Path, minimum_interval: float = 1.0) -> dict[str, Any]:
    meta_path = path.with_suffix(path.suffix + ".fetch.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if int(meta.get("status") or 0) == 200 and path.stat().st_size > 0:
            return {**meta, "body": path.read_bytes(), "resumed": True}
    path.parent.mkdir(parents=True, exist_ok=True)
    attempt = 0
    interval = minimum_interval
    error = ""
    while attempt < 2:
        attempt += 1
        time.sleep(interval)
        retrieved_at = now_iso()
        try:
            response = session.get(url, timeout=120, allow_redirects=True)
            status = response.status_code
            body = response.content
            mime = response.headers.get("Content-Type", "").split(";", 1)[0]
            final_url = response.url
            if status == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    interval = max(interval * 2, float(retry_after))
                except ValueError:
                    interval *= 2
                continue
            if status == 200:
                temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
                temporary.write_bytes(body)
                os.replace(temporary, path)
            error = "" if status == 200 else f"HTTP {status}"
            meta = {
                "url": url,
                "final_url": final_url,
                "retrieved_at": retrieved_at,
                "status": status,
                "mime": mime,
                "byte_size": len(body),
                "sha256": hashlib.sha256(body).hexdigest() if status == 200 else "",
                "attempts": attempt,
                "error": error,
            }
            write_json(meta_path, meta)
            return {**meta, "body": body, "resumed": False}
        except requests.RequestException as exc:
            error = f"{type(exc).__name__}: {exc}"
    meta = {"url": url, "final_url": "", "retrieved_at": now_iso(), "status": 0, "mime": "", "byte_size": 0, "sha256": "", "attempts": attempt, "error": error}
    write_json(meta_path, meta)
    return {**meta, "body": b"", "resumed": False}


def acquire_mirror() -> dict[str, Any]:
    ensure_dirs()
    files = read_csv(MANIFESTS / "parlparse_remote_file_manifest.csv")
    if not files:
        raise RuntimeError("Run enumerate-mirror first")
    session = requests.Session()
    session.headers.update({"User-Agent": "fear-of-temperature-research/1.0 bounded academic recovery"})
    statuses: list[dict[str, Any]] = []
    consecutive_denials = 0
    host_stopped = False
    for index, row in enumerate(files):
        raw_path = RAW / "parlparse" / row["kind"] / row["date"][:4] / row["filename"]
        if host_stopped:
            statuses.append({**row, "download_status": "unrequested_host_stop", "failure_reason": "three_consecutive_403_or_429", "raw_path": "", "raw_sha256": ""})
            continue
        result = _fetch(session, row["request_url"], raw_path, 1.0)
        denied = int(result["status"] or 0) in {403, 429}
        consecutive_denials = consecutive_denials + 1 if denied else 0
        if consecutive_denials >= 3:
            host_stopped = True
        valid = int(result["status"] or 0) == 200 and result["body"].lstrip().startswith(b"<?xml")
        statuses.append(
            {
                **row,
                "retrieved_at": result["retrieved_at"],
                "final_url": result["final_url"],
                "http_status": result["status"],
                "mime_type": result["mime"],
                "attempt_count": result["attempts"],
                "download_status": "success" if valid else "failed",
                "validation_status": "parseable_xml_candidate" if valid else "invalid_or_unavailable_xml",
                "failure_reason": "" if valid else (result["error"] or "response_not_xml"),
                "raw_path": rel(raw_path) if valid else "",
                "raw_sha256": sha(raw_path) if valid else "",
                "byte_size": raw_path.stat().st_size if valid else 0,
                "fetch_meta_path": rel(raw_path.with_suffix(raw_path.suffix + ".fetch.json")),
                "resumed": result["resumed"],
            }
        )
        if (index + 1) % 25 == 0:
            write_csv(EVIDENCE / "parlparse_acquisition_status.csv", statuses)
            write_json(CHECKPOINTS / "parlparse_acquisition.json", {"updated_at": now_iso(), "processed": len(statuses), "targets": len(files), "host_stopped": host_stopped})
            print(f"[{now_iso()}] FETCH CHECKPOINT files={len(statuses)}/{len(files)} success={sum(r.get('download_status') == 'success' for r in statuses)}", flush=True)
    write_csv(EVIDENCE / "parlparse_acquisition_status.csv", statuses)
    result = {
        "generated_at": now_iso(),
        "frozen_files": len(files),
        "attempted_or_resumed": sum(row.get("download_status") != "unrequested_host_stop" for row in statuses),
        "acquired": sum(row.get("download_status") == "success" for row in statuses),
        "failed": sum(row.get("download_status") == "failed" for row in statuses),
        "unrequested_after_stop": sum(row.get("download_status") == "unrequested_host_stop" for row in statuses),
        "host_stopped": host_stopped,
    }
    write_json(REPORTS / "mirror_acquisition_summary.json", result)
    return result


def acquire_policy() -> dict[str, Any]:
    ensure_dirs()
    session = requests.Session()
    session.headers.update({"User-Agent": "fear-of-temperature-research/1.0 bounded academic recovery"})
    rows: list[dict[str, Any]] = []
    for candidate in POLICY_CANDIDATES:
        stem = candidate["external_id"].replace(":", "_")
        content_path = RAW / "early_policy" / f"{stem}.content.json"
        landing_path = RAW / "early_policy" / f"{stem}.html"
        content_result = _fetch(session, candidate["content_api_url"], content_path, 1.25)
        landing_result = _fetch(session, candidate["landing_url"], landing_path, 1.25)
        metadata = {}
        if content_result["status"] == 200:
            try:
                metadata = json.loads(content_result["body"].decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                metadata = {}
        attachment_url = ""
        details = metadata.get("details") if isinstance(metadata.get("details"), dict) else {}
        attachments = details.get("attachments") if isinstance(details.get("attachments"), list) else []
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            url = attachment.get("url") or ""
            if url.lower().endswith(".pdf"):
                attachment_url = urljoin(candidate["landing_url"], url)
                break
        if not attachment_url and landing_result["status"] == 200:
            soup = BeautifulSoup(landing_result["body"], "html.parser")
            attachment_url = next((urljoin(candidate["landing_url"], str(a.get("href"))) for a in soup.find_all("a", href=True) if str(a.get("href")).lower().endswith(".pdf")), "")
        attachment_url = attachment_url or candidate["fallback_pdf_url"]
        pdf_path = RAW / "early_policy" / f"{stem}.pdf"
        pdf_result = _fetch(session, attachment_url, pdf_path, 1.25)
        valid_pdf = pdf_result["status"] == 200 and pdf_result["body"].startswith(b"%PDF-")
        rows.append(
            {
                **candidate,
                "content_id": metadata.get("content_id") or candidate["external_id"],
                "content_api_status": content_result["status"],
                "content_api_final_url": content_result["final_url"],
                "content_api_retrieved_at": content_result["retrieved_at"],
                "content_api_path": rel(content_path) if content_path.exists() else "",
                "content_api_sha256": sha(content_path) if content_path.exists() else "",
                "landing_status": landing_result["status"],
                "landing_final_url": landing_result["final_url"],
                "landing_retrieved_at": landing_result["retrieved_at"],
                "landing_mime_type": landing_result["mime"],
                "landing_path": rel(landing_path) if landing_path.exists() else "",
                "landing_sha256": sha(landing_path) if landing_path.exists() else "",
                "attachment_url": attachment_url,
                "pdf_status": pdf_result["status"],
                "pdf_final_url": pdf_result["final_url"],
                "pdf_retrieved_at": pdf_result["retrieved_at"],
                "pdf_mime_type": pdf_result["mime"],
                "pdf_path": rel(pdf_path) if valid_pdf else "",
                "pdf_sha256": sha(pdf_path) if valid_pdf else "",
                "pdf_byte_size": pdf_path.stat().st_size if valid_pdf else 0,
                "acquisition_status": "success" if valid_pdf and landing_result["status"] == 200 else "failed",
                "failure_reason": "" if valid_pdf and landing_result["status"] == 200 else (pdf_result["error"] or landing_result["error"] or "invalid_pdf_or_landing_page"),
            }
        )
    write_csv(MANIFESTS / "early_policy_recovery_manifest.csv", rows)
    result = {"generated_at": now_iso(), "targets": len(rows), "acquired": sum(row["acquisition_status"] == "success" for row in rows), "failed": sum(row["acquisition_status"] != "success" for row in rows)}
    write_json(REPORTS / "early_policy_acquisition_summary.json", result)
    return result


def _existing_answer_index(target_dates: set[str]) -> tuple[dict[tuple[str, str], set[str]], dict[tuple[str, str], set[str]]]:
    qnum_index: dict[tuple[str, str], set[str]] = defaultdict(set)
    text_index: dict[tuple[str, str], set[str]] = defaultdict(set)
    with duckdb.connect(str(DB), read_only=True) as con:
        con.execute("CREATE TEMP TABLE target_dates(value DATE)")
        con.executemany("INSERT INTO target_dates VALUES (?)", [(value,) for value in sorted(target_dates)])
        rows = con.execute(
            """
            SELECT d.document_id, CAST(d.publication_date AS VARCHAR), ts.segment_text
            FROM documents d
            JOIN target_dates td ON td.value=d.publication_date
            JOIN voice_attributions va ON va.document_id=d.document_id
            JOIN text_segments ts ON ts.segment_id=va.segment_id
            WHERE d.content_type='ministerial_written_answer'
              AND ts.heading LIKE 'Question/context%'
            """
        ).fetchall()
        for document_id, sitting_date, text in rows:
            for qnum in re.findall(r"\[(\d+[A-Z]?)\]", text or ""):
                qnum_index[(sitting_date, qnum)].add(str(document_id))
            text_index[(sitting_date, norm_key(text or ""))].add(str(document_id))
    return qnum_index, text_index


def parse_and_match() -> dict[str, Any]:
    ensure_dirs()
    statuses = [row for row in read_csv(EVIDENCE / "parlparse_acquisition_status.csv") if row.get("download_status") == "success"]
    target_dates = {row["date"] for row in statuses}
    qnum_index, text_index = _existing_answer_index(target_dates)
    records: list[dict[str, Any]] = []
    identity_rows: list[dict[str, Any]] = []
    parse_failures: list[dict[str, Any]] = []
    seen_new: set[tuple[str, str, str]] = set()
    for status in statuses:
        path = ROOT / status["raw_path"]
        try:
            parsed = parse_xml(path, status["record_genre"], status["date"])
        except (ET.ParseError, OSError, ValueError) as exc:
            parse_failures.append(
                {
                    "date": status["date"],
                    "kind": status["kind"],
                    "filename": status["filename"],
                    "raw_path": status["raw_path"],
                    "raw_sha256": status["raw_sha256"],
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue
        for record in parsed:
            reasons = set(status["target_reasons"].split(";"))
            in_scope = False
            if "2004_q4_commons_seam" in reasons and record["department"] in APPROVED_2004_DEPARTMENTS:
                in_scope = True
            elif (
                reasons & {"failed_date_index", "failed_known_page", "unrequested_known_page"}
                and record["department"] in APPROVED_GAP_DEPARTMENTS
                and status["kind"] == "wrans"
            ):
                in_scope = True
            elif "companies_house_named_access_failure" in reasons and record["department"] == BERR and norm_key(record["title"]) == "companieshouse":
                in_scope = True
            if not in_scope:
                continue
            qnums = record.get("qnums") or []
            matched_ids: set[str] = set()
            for qnum in qnums:
                matched_ids.update(qnum_index.get((record["sitting_date"], qnum), set()))
            method = "date_and_question_number" if matched_ids else ""
            if not matched_ids and record.get("questions"):
                for question in record["questions"]:
                    matched_ids.update(text_index.get((record["sitting_date"], norm_key(question.get("text", ""))), set()))
                if matched_ids:
                    method = "date_and_normalised_question_text"
            identity = "already_present" if matched_ids else "new_recovered_identity"
            unique_key = (record["genre"], record["sitting_date"], record["external_id"])
            if not matched_ids and unique_key in seen_new:
                identity = "duplicate_within_mirror_files"
                method = "provider_record_id"
            seen_new.add(unique_key)
            record_path = RAW / "parlparse" / "derived_records" / record["genre"] / record["sitting_date"][:4] / f"{hga.stable_id('record', record['external_id'])}.json"
            record.update(
                {
                    "source_xml_path": status["raw_path"],
                    "source_xml_sha256": status["raw_sha256"],
                    "source_xml_locator": record["provider_record_id"],
                    "provider": "ParlParse/TheyWorkForYou",
                    "provider_transformation_note": "XML is a processed mirror representation; original Parliament URL is preserved where supplied.",
                }
            )
            write_json(record_path, record)
            manifest_row = {
                "partition_id": hga.stable_id("part", PARLIAMENT_BATCH_ID, record["sitting_date"][:7], record["genre"], record["department"]),
                "source": "parlparse_twf_bounded_xml_mirror",
                "genre": record["genre"],
                "year": record["sitting_date"][:4],
                "date": record["sitting_date"],
                "department": record["department"],
                "external_id": record["external_id"],
                "canonical_url": record["canonical_url"],
                "title": record["title"],
                "government_respondent": record["government_respondent"],
                "question_count": len(record["questions"]),
                "response_segment_count": len(record["responses"]),
                "attribution_status": record["attribution_status"],
                "uin": record.get("uin") or "",
                "record_path": rel(record_path),
                "record_sha256": sha(record_path),
                "parent_raw_path": status["raw_path"],
                "parent_raw_sha256": status["raw_sha256"],
                "parent_fetch_meta_path": status["fetch_meta_path"],
                "parent_request_url": status["request_url"],
                "parent_final_url": status["final_url"],
                "parent_retrieved_at": status["retrieved_at"],
                "parent_status_code": status["http_status"],
                "parent_mime_type": status["mime_type"],
                "source_locator": record["provider_record_id"],
                "identity_status": "mirror_derived_record_mapped_by_original_identifiers",
                "record_is_derived": True,
                "storage_mode": "derived_list",
                "identity_disposition": identity,
                "matched_document_ids": ";".join(sorted(matched_ids)),
                "match_method": method,
                "target_reasons": status["target_reasons"],
            }
            records.append(manifest_row)
            identity_rows.append(
                {
                    "provider_external_id": record["external_id"],
                    "genre": record["genre"],
                    "date": record["sitting_date"],
                    "department": record["department"],
                    "title": record["title"],
                    "qnums": record.get("uin") or "",
                    "original_url": record["canonical_url"],
                    "identity_disposition": identity,
                    "matched_document_ids": ";".join(sorted(matched_ids)),
                    "match_method": method,
                    "source_xml_path": status["raw_path"],
                    "source_locator": record["provider_record_id"],
                }
            )
    records.sort(key=lambda row: (row["date"], row["genre"], row["department"], row["external_id"]))
    identity_rows.sort(key=lambda row: (row["date"], row["genre"], row["department"], row["provider_external_id"]))
    write_csv(MANIFESTS / "parlparse_record_manifest.csv", records)
    write_csv(EVIDENCE / "parlparse_identity_mapping.csv", identity_rows)
    write_csv(EVIDENCE / "parlparse_parse_failures.csv", parse_failures)
    result = {
        "generated_at": now_iso(),
        "parsed_in_scope_records": len(records),
        "already_present": sum(row["identity_disposition"] == "already_present" for row in records),
        "new_recovered_identity": sum(row["identity_disposition"] == "new_recovered_identity" for row in records),
        "duplicate_within_mirror_files": sum(row["identity_disposition"] == "duplicate_within_mirror_files" for row in records),
        "source_files_parse_failed": len(parse_failures),
        "by_genre": dict(Counter(row["genre"] for row in records)),
    }
    write_json(REPORTS / "parlparse_parse_match_summary.json", result)
    return result


def _ensure_parliament_parent_context(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    counts: Counter[str] = Counter()
    offsets: dict[str, dict[str, int]] = defaultdict(dict)
    for row in rows:
        parent = row["parent_raw_path"]
        record = json.loads((ROOT / row["record_path"]).read_text(encoding="utf-8"))
        offsets[parent][row["external_id"]] = counts[parent]
        counts[parent] += len(record.get("questions") or []) + len(record.get("responses") or [])
    return {parent: {"segment_count": counts[parent], "record_offsets": offsets[parent]} for parent in offsets}


def _rewrite_mirror_provenance(prepared: dict[str, list[tuple[Any, ...]]]) -> None:
    rewritten_raw = []
    for row in prepared["raw_records"]:
        values = list(row)
        values[8] = values[8].replace("derived_record_from_official_api_list_response", "derived_record_from_parlparse_twf_xml_mirror").replace("source_json=", "source_xml=")
        rewritten_raw.append(tuple(values))
    prepared["raw_records"] = rewritten_raw
    rewritten_objects = []
    for row in prepared["content_objects"]:
        values = list(row)
        values[3] = values[3]
        values[4] = "application/xml"
        values[10] = f"ParlParse/TheyWorkForYou XML parent {values[10].split()[-1]}"
        values[12] = hga.canonical_json({"source_key": "parlparse_twf_mirror", "record_is_derived": True, "provider_transformation": "processed XML mirror", "original_parliament_urls_preserved": True})
        rewritten_objects.append(tuple(values))
    prepared["content_objects"] = rewritten_objects
    prepared["content_versions"] = [tuple(list(row[:6]) + ["application/xml"] + list(row[7:])) for row in prepared["content_versions"]]
    prepared["content_fetches"] = [tuple(list(row[:8]) + ["application/xml"] + list(row[9:])) for row in prepared["content_fetches"]]
    rewritten_status = []
    for row in prepared["acquisition_statuses"]:
        values = list(row)
        values[5] = "application/xml"
        values[6] = "application/xml"
        values[7] = "xml"
        values[11] = "valid_parlparse_twf_xml_parent_of_derived_record"
        values[13] = "Question/context and government response derived separately from mirror XML; original Parliament locator retained"
        rewritten_status.append(tuple(values))
    prepared["acquisition_statuses"] = rewritten_status


def _backup_once() -> Path:
    backup = RECOVERY / f"fear_temperature_government_content.before_{PARLIAMENT_BATCH_ID}.duckdb"
    if not backup.exists():
        shutil.copy2(DB, backup)
    return backup


def _ensure_parliament_source_batch(con: duckdb.DuckDBPyConnection, rows: list[dict[str, str]]) -> None:
    con.execute(
        """
        INSERT INTO sources VALUES (?, ?, 'policy', ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        ON CONFLICT (source_id) DO NOTHING
        """,
        [
            PARLIAMENT_SOURCE_ID,
            PARLIAMENT_SOURCE_NAME,
            "ministerial_parliamentary_record_mirror",
            "ministerial_written_record",
            "rsync list-only enumeration followed by individual HTTPS XML requests",
            "Only frozen 2004-Q4 seam and unresolved 2007/2010-2014 target dates; mirror overlap excluded from new-document counts",
            "open_parliament_licence_internal_research",
            "Mirror transformations retained; redistribution not asserted by this task.",
            "Project collection is authorised; no institutional ethics approval/exemption is asserted by this task.",
            hga.canonical_json(["https://parser.theyworkforyou.com/hansard.html", "https://data.mysociety.org/datasets/theyworkforyou-api/", "https://github.com/mysociety/parlparse"]),
            rel(OUT / "alternative_source_register.csv"),
        ],
    )
    manifest_path = MANIFESTS / "parlparse_record_manifest.csv"
    con.execute(
        """
        INSERT INTO collection_batches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (batch_id) DO NOTHING
        """,
        [
            PARLIAMENT_BATCH_ID,
            PARLIAMENT_SOURCE_ID,
            datetime.now(UTC),
            f"{MIRROR_RSYNC}/wrans and /wms bounded listings",
            hga.canonical_json({"target_dates_only": True, "approved_departments_only": True, "mirror_duplicates_not_new": True, "script_version": SCRIPT_VERSION}),
            date(2004, 10, 5),
            date(2014, 9, 11),
            "parliamentary_sitting_date",
            hga.canonical_json({"partition": "month_genre_department", "source_rows": len(rows)}),
            len(rows),
            len(rows),
            "partial_targeted_recovery",
            "Bounded alternative-source recovery; unresolved dates without mirror files remain explicit.",
            rel(manifest_path),
            sha(manifest_path),
            rel(EVIDENCE / "parlparse_acquisition_status.csv"),
            sha(EVIDENCE / "parlparse_acquisition_status.csv"),
            True,
        ],
    )
    for partition_id, part_rows in _group(rows, lambda row: row["partition_id"]).items():
        paths = sorted({row["parent_raw_path"] for row in part_rows})
        dates = [date.fromisoformat(row["date"]) for row in part_rows]
        con.execute(
            """
            INSERT INTO query_partitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (query_partition_id) DO NOTHING
            """,
            [partition_id, PARLIAMENT_BATCH_ID, min(dates), max(dates), MIRROR_HTTP, datetime.now(UTC), datetime.now(UTC), len(paths), len(part_rows), len(part_rows), len(part_rows), len(part_rows), "complete_for_matching_mirror_files", "Only records in matched bounded XML files and approved departments.", hga.canonical_json(paths)],
        )


def _group(rows: list[dict[str, str]], key: Any) -> dict[str, list[dict[str, str]]]:
    output: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        output[str(key(row))].append(row)
    return output


def _prepare_policy_rows(con: duckdb.DuckDBPyConnection, extraction_run_id: str) -> dict[str, list[tuple[Any, ...]]]:
    from fear_temperature.government_collection import _extract_pdf

    prepared: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    for row in read_csv(MANIFESTS / "early_policy_recovery_manifest.csv"):
        if row.get("acquisition_status") != "success":
            continue
        existing = con.execute("SELECT document_id FROM documents WHERE canonical_url=? OR external_id=?", [row["landing_url"], row["external_id"]]).fetchone()
        if existing:
            continue
        acquired = parse_dt(row["content_api_retrieved_at"] or row["landing_retrieved_at"])
        metadata_path = ROOT / row["content_api_path"]
        raw_payload = metadata_path.read_text(encoding="utf-8") if metadata_path.exists() else hga.canonical_json(row)
        raw_sha = hashlib.sha256(raw_payload.encode()).hexdigest()
        document_id = hga.stable_id("doc", POLICY_SOURCE_ID, row["external_id"])
        raw_id = hga.stable_id("raw", POLICY_BATCH_ID, row["external_id"], raw_sha)
        publication_date = date.fromisoformat(row["publication_date"])
        published = datetime.combine(publication_date, datetime.min.time(), tzinfo=UTC)
        normalised = {key: row[key] for key in ["external_id", "title", "publication_date", "publisher", "organisation", "landing_url", "publication_number", "isbn"]}
        normalised_json = hga.canonical_json(normalised)
        version_id = hga.stable_id("docv", document_id, raw_sha, hga.NORMALISATION_RULE_VERSION)
        partition_id = hga.stable_id("part", POLICY_BATCH_ID, publication_date.year, row["organisation"])
        prepared["raw_records"].append((raw_id, POLICY_BATCH_ID, POLICY_SOURCE_ID, row["external_id"], raw_payload, raw_sha, acquired, row["content_api_path"], "verified_official_govuk_content_and_command_paper_identity"))
        prepared["documents"].append((document_id, POLICY_SOURCE_ID, row["external_id"], row["landing_url"], row["title"], "en", publication_date, published, "GOV.UK policy-paper publication date and command-paper metadata", None, acquired, "policy", "policy_paper", "document", None, "original", "downloaded_and_extracted", "Verified official 1994 command paper recovered through a bounded archived GOV.UK route", "exact_title_date_command_number_isbn", "checked_against_existing_06_database", "official_open_licence_terms_item_exceptions_not_reassessed", "pending", "Project-authorised internal research; institutional ethics status not asserted", True))
        prepared["document_versions"].append((version_id, document_id, hga.NORMALISATION_RULE_VERSION, raw_sha, normalised_json, hashlib.sha256(normalised_json.encode()).hexdigest(), datetime.now(UTC), True))
        prepared["document_version_raw_links"].append((version_id, raw_id))
        prepared["enumeration_records"].append((POLICY_BATCH_ID, partition_id, document_id, raw_id, acquired, "verified_single_historical_policy_target", row["content_api_path"], row["content_api_sha256"]))
        org_external = f"uk_government_department:{hga.normalise_label(row['organisation'])}"
        org_id = hga.stable_id("org", org_external)
        prepared["organisations"].append((org_id, org_external, row["organisation"], row["landing_url"]))
        prepared["document_organisations"].append((document_id, org_id, "publishing_department", "confirmed", 1.0, 1.0, "official_page_and_command_paper"))
        for ordinal, (kind, url_key, final_key, time_key, mime_key, path_key, sha_key, relation) in enumerate([
            ("webpage", "landing_url", "landing_final_url", "landing_retrieved_at", "landing_mime_type", "landing_path", "landing_sha256", "landing_page"),
            ("attachment", "attachment_url", "pdf_final_url", "pdf_retrieved_at", "pdf_mime_type", "pdf_path", "pdf_sha256", "attachment"),
        ]):
            object_id = hga.stable_id("cnt", kind, row[final_key] or row[url_key])
            content_sha = row[sha_key]
            fetch_id = hga.stable_id("fet", POLICY_BATCH_ID, object_id)
            content_version_id = hga.stable_id("cntv", object_id, content_sha)
            content_path = ROOT / row[path_key]
            mime = row[mime_key] or ("application/pdf" if kind == "attachment" else "text/html")
            retrieved = parse_dt(row[time_key])
            segments = _extract_pdf(content_path.read_bytes()) if kind == "attachment" else []
            prepared["content_objects"].append((object_id, kind, row["external_id"] if kind == "webpage" else row["publication_number"], row[final_key] or row[url_key], mime, content_path.stat().st_size, 194 if kind == "attachment" else None, "public", "internal_only_not_cleared_for_redistribution", "pending", row["title"], "success", hga.canonical_json({"publication_number": row["publication_number"], "isbn": row["isbn"], "original_publisher": row["publisher"], "retrieval_provider": "GOV.UK"})))
            prepared["document_content_objects"].append((document_id, object_id, relation, ordinal))
            prepared["content_versions"].append((content_version_id, object_id, content_sha, row[final_key] or row[url_key], retrieved, 200, mime, content_path.stat().st_size, row[path_key], content_sha, fetch_id, "verified"))
            prepared["content_fetches"].append((fetch_id, POLICY_BATCH_ID, object_id, content_version_id, row[url_key], row[final_key] or row[url_key], retrieved, 200, mime, content_sha, row[path_key], SCRIPT_VERSION, "success", "success", "internal_only_not_cleared_for_redistribution", ""))
            if kind == "attachment":
                for segment_order, segment in enumerate(segments):
                    text = norm(segment["text"])
                    text_sha = hashlib.sha256(text.encode()).hexdigest()
                    segment_id = hga.stable_id("seg", content_version_id, extraction_run_id, segment_order, text_sha)
                    prepared["text_segments"].append((segment_id, content_version_id, extraction_run_id, None, "source_extracted", segment.get("segment_kind") or "unknown", segment_order, segment.get("heading"), text, segment["locator"], None, None, text_sha, "project_authorized_internal_use_institutional_ethics_not_asserted", True, datetime.now(UTC)))
                seg_count = len(segments)
            else:
                seg_count = 0
            prepared["acquisition_statuses"].append((POLICY_BATCH_ID, object_id, fetch_id, content_version_id, kind, mime, mime, "pdf" if kind == "attachment" else "html", 1, row[url_key] != (row[final_key] or row[url_key]), "success", "official_govuk_command_paper" if kind == "attachment" else "official_govuk_landing_page", "success" if kind == "attachment" else "not_selected_for_text", "PDF lines retained as source blocks; no semantic cleaning" if kind == "attachment" else "Body text is sourced from the complete command-paper attachment", content_path.stat().st_size, content_sha, row[path_key], seg_count, row[path_key] + ".fetch.json", datetime.now(UTC)))
    return prepared


def ingest() -> dict[str, Any]:
    ensure_dirs()
    _backup_once()
    all_rows = read_csv(MANIFESTS / "parlparse_record_manifest.csv")
    new_rows = [row for row in all_rows if row.get("identity_disposition") == "new_recovered_identity"]
    context = _ensure_parliament_parent_context(new_rows)
    before: dict[str, int]
    after: dict[str, int]
    commits: list[dict[str, Any]] = []
    with duckdb.connect(str(DB)) as con:
        before = {table: int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in ["documents", "content_objects", "content_versions", "text_segments", "voice_attributions"]}
        authorization_id = hga._new_authorization(con)
        _ensure_parliament_source_batch(con, new_rows)
        parliament_extraction = hga.stable_id("ext", PARLIAMENT_BATCH_ID, EXTRACTOR_VERSION)
        con.execute("INSERT INTO extraction_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING", [parliament_extraction, PARLIAMENT_BATCH_ID, EXTRACTOR_VERSION, datetime.now(UTC), datetime.now(UTC), 0, 0, "partial", "Bounded mirror-derived records only."])
        existing = {str(row[0]) for row in con.execute("SELECT external_id FROM documents WHERE source_id=?", [PARLIAMENT_SOURCE_ID]).fetchall()}
        pending = [row for row in new_rows if row["external_id"] not in existing]
        for offset in range(0, len(pending), 500):
            chunk = pending[offset : offset + 500]
            prepared = hga._prepare_parliament_rows("hansard_gap", PARLIAMENT_SOURCE_ID, PARLIAMENT_BATCH_ID, parliament_extraction, chunk, context)
            _rewrite_mirror_provenance(prepared)
            chunk_before = int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
            con.execute("BEGIN TRANSACTION")
            try:
                hga._insert_prepared_chunk(con, prepared)
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
            chunk_after = int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
            checkpoint = CHECKPOINTS / f"parliament_commit_{offset:06d}.json"
            write_json(checkpoint, {"committed_at": now_iso(), "source_rows": len(chunk), "new_documents": chunk_after - chunk_before, "external_ids": [row["external_id"] for row in chunk]})
            commits.append({"series": "parliament", "offset": offset, "source_rows": len(chunk), "new_documents": chunk_after - chunk_before, "checkpoint": rel(checkpoint)})
            print(f"[{now_iso()}] COMMIT parliament records={len(chunk)} new_documents={chunk_after - chunk_before}", flush=True)
            del prepared
            gc.collect()
        parliament_segments = int(con.execute("SELECT COUNT(*) FROM text_segments WHERE extraction_run_id=?", [parliament_extraction]).fetchone()[0])
        con.execute("UPDATE extraction_runs SET finished_at=?, input_content_count=?, output_segment_count=?, status='complete', status_reason=? WHERE extraction_run_id=?", [datetime.now(UTC), len({row['parent_raw_path'] for row in pending}), parliament_segments, "All eligible non-overlap mirror records committed; residual missing-date states remain in coverage ledger.", parliament_extraction])

        policy_manifest = read_csv(MANIFESTS / "early_policy_recovery_manifest.csv")
        policy_manifest_path = MANIFESTS / "early_policy_recovery_manifest.csv"
        con.execute(
            """
            INSERT INTO collection_batches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (batch_id) DO NOTHING
            """,
            [POLICY_BATCH_ID, POLICY_SOURCE_ID, datetime.now(UTC), POLICY_CANDIDATES[0]["landing_url"], hga.canonical_json({"single_verified_gap_target": True, "script_version": SCRIPT_VERSION}), date(1994, 1, 25), date(1994, 1, 25), "verified_original_publication_date", hga.canonical_json({"targets": len(policy_manifest)}), len(policy_manifest), len(policy_manifest), "complete_for_frozen_single_target", "Exact official command-paper identity; not a complete historical policy enumeration.", rel(policy_manifest_path), sha(policy_manifest_path), rel(policy_manifest_path), sha(policy_manifest_path), True],
        )
        policy_partition = hga.stable_id("part", POLICY_BATCH_ID, 1994, "Department of the Environment")
        con.execute("INSERT INTO query_partitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING", [policy_partition, POLICY_BATCH_ID, date(1994, 1, 25), date(1994, 1, 25), POLICY_CANDIDATES[0]["landing_url"], datetime.now(UTC), datetime.now(UTC), 3, 1, 1, 1, 1, "complete_for_frozen_single_target", "Single exact policy recovery; no population denominator inferred.", hga.canonical_json([row.get("content_api_path") for row in policy_manifest] + [row.get("landing_path") for row in policy_manifest] + [row.get("pdf_path") for row in policy_manifest])])
        policy_extraction = hga.stable_id("ext", POLICY_BATCH_ID, POLICY_EXTRACTOR_VERSION)
        con.execute("INSERT INTO extraction_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING", [policy_extraction, POLICY_BATCH_ID, POLICY_EXTRACTOR_VERSION, datetime.now(UTC), datetime.now(UTC), 0, 0, "partial", "Single verified historic policy target."])
        policy_prepared = _prepare_policy_rows(con, policy_extraction)
        policy_before = int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
        con.execute("BEGIN TRANSACTION")
        try:
            hga._insert_prepared_chunk(con, policy_prepared)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        policy_after = int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
        if policy_prepared.get("documents"):
            checkpoint = CHECKPOINTS / "policy_commit_000000.json"
            write_json(checkpoint, {"committed_at": now_iso(), "source_rows": len(policy_prepared["documents"]), "new_documents": policy_after - policy_before, "external_ids": [row[2] for row in policy_prepared["documents"]]})
            commits.append({"series": "policy", "offset": 0, "source_rows": len(policy_prepared["documents"]), "new_documents": policy_after - policy_before, "checkpoint": rel(checkpoint)})
            print(f"[{now_iso()}] COMMIT policy records={len(policy_prepared['documents'])} new_documents={policy_after - policy_before}", flush=True)
        policy_segments = int(con.execute("SELECT COUNT(*) FROM text_segments WHERE extraction_run_id=?", [policy_extraction]).fetchone()[0])
        con.execute("UPDATE extraction_runs SET finished_at=?, input_content_count=?, output_segment_count=?, status='complete', status_reason=? WHERE extraction_run_id=?", [datetime.now(UTC), len(policy_prepared.get("documents", [])), policy_segments, "Exact verified historic policy target committed; no broader population completeness claimed.", policy_extraction])
        run_id = hga.stable_id("run", PARLIAMENT_BATCH_ID, SCRIPT_VERSION)
        manifest_path = MANIFESTS / "parlparse_record_manifest.csv"
        con.execute("INSERT INTO acquisition_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (run_id) DO UPDATE SET finished_at=excluded.finished_at,status=excluded.status,attempted_count=excluded.attempted_count,successful_download_count=excluded.successful_download_count,successful_extraction_count=excluded.successful_extraction_count,failure_count=excluded.failure_count,result_json=excluded.result_json", [run_id, PARLIAMENT_BATCH_ID, authorization_id, datetime.now(UTC), datetime.now(UTC), "bounded_mirror_gap_recovery_ingest", SCRIPT_VERSION, f"{sys.executable} {Path(__file__).name} ingest", rel(manifest_path), sha(manifest_path), str(DB), "complete_with_documented_residuals", len(all_rows), len(all_rows), len(pending), 0, hga.canonical_json({"parsed": len(all_rows), "already_present": sum(row['identity_disposition']=='already_present' for row in all_rows), "eligible_new": len(pending), "segments": parliament_segments})])
        after = {table: int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in before}
    write_csv(REPORTS / "incremental_commit_chunks.csv", commits)
    result = {"generated_at": now_iso(), "backup": rel(_backup_once()), "before": before, "after": after, "added": {key: after[key] - before[key] for key in before}, "parliament_candidates_new": len(new_rows), "committed_chunks": len(commits)}
    write_json(REPORTS / "incremental_ingestion_summary.json", result)
    return result


def reconcile() -> dict[str, Any]:
    ensure_dirs()
    identities = read_csv(EVIDENCE / "parlparse_identity_mapping.csv")
    new_ids = {row["provider_external_id"] for row in identities if row["identity_disposition"] == "new_recovered_identity"}
    policy_ids = {row["external_id"] for row in read_csv(MANIFESTS / "early_policy_recovery_manifest.csv") if row.get("acquisition_status") == "success"}
    with duckdb.connect(str(DB), read_only=True) as con:
        totals = {
            "documents": int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]),
            "policy_document": int(con.execute("SELECT COUNT(*) FROM documents d JOIN sources s USING(source_id) WHERE s.source_name LIKE 'GOV.UK%' ").fetchone()[0]),
            "ministerial_written_answer": int(con.execute("SELECT COUNT(*) FROM documents WHERE content_type='ministerial_written_answer'").fetchone()[0]),
            "ministerial_written_statement": int(con.execute("SELECT COUNT(*) FROM documents WHERE content_type='ministerial_written_statement'").fetchone()[0]),
            "text_segments": int(con.execute("SELECT COUNT(*) FROM text_segments").fetchone()[0]),
        }
        mirror_present = {str(row[0]) for row in con.execute("SELECT external_id FROM documents WHERE source_id=?", [PARLIAMENT_SOURCE_ID]).fetchall()}
        policy_present = {str(row[0]) for row in con.execute("SELECT external_id FROM documents WHERE source_id=? AND external_id IN (SELECT unnest(?))", [POLICY_SOURCE_ID, list(policy_ids)]).fetchall()} if policy_ids else set()
        duplicate_groups = int(con.execute("SELECT COUNT(*) FROM (SELECT source_id,external_id,COUNT(*) n FROM documents GROUP BY 1,2 HAVING n>1)").fetchone()[0])
        question_response = con.execute("SELECT ts.heading,COUNT(*) FROM documents d JOIN voice_attributions va USING(document_id) JOIN text_segments ts USING(segment_id) WHERE d.source_id=? GROUP BY 1 ORDER BY 1", [PARLIAMENT_SOURCE_ID]).fetchall()
        original_urls = int(con.execute("SELECT COUNT(*) FROM documents WHERE source_id=? AND canonical_url LIKE 'https://www.publications.parliament.uk/%'", [PARLIAMENT_SOURCE_ID]).fetchone()[0])
    excluded_rows = read_csv(OUT / "exclusion_ledger.csv")
    result = {
        "generated_at": now_iso(),
        "totals": totals,
        "new_mirror_ids_expected": len(new_ids),
        "new_mirror_ids_present": len(new_ids & mirror_present),
        "new_mirror_ids_missing": sorted(new_ids - mirror_present),
        "policy_ids_expected": len(policy_ids),
        "policy_ids_present": len(policy_ids & policy_present),
        "source_external_duplicate_groups": duplicate_groups,
        "mirror_question_response_segments": {str(key): int(value) for key, value in question_response},
        "mirror_records_with_original_parliament_url": original_urls,
        "exclusions_retained": len(excluded_rows),
        "excluded_records_inserted_by_recovery": sum(row["target_id"] in mirror_present for row in excluded_rows),
        "passed": len(new_ids - mirror_present) == 0 and len(policy_ids - policy_present) == 0 and duplicate_groups == 0,
    }
    write_json(REPORTS / "incremental_reconciliation.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["bootstrap", "enumerate-mirror", "validate-samples", "acquire-mirror", "acquire-policy", "parse-match", "ingest", "reconcile"])
    args = parser.parse_args()
    function = {
        "bootstrap": bootstrap,
        "enumerate-mirror": enumerate_mirror,
        "validate-samples": validate_samples,
        "acquire-mirror": acquire_mirror,
        "acquire-policy": acquire_policy,
        "parse-match": parse_and_match,
        "ingest": ingest,
        "reconcile": reconcile,
    }[args.phase]
    print(json.dumps(function(), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
