"""Reconcile the fixed enumerations, saved bytes and US/AU database increment."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

from acquire import (AU_SOURCE, DB, HERE, PRE, ROOT, US_SOURCE, au_rows, rows,
                     sid, us_fallback_path, us_path, us_rows, verified_meta)


def csv_write(path: Path, fields: list[str], data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        w.writerows(data)


def main() -> None:
    c = duckdb.connect(str(DB), read_only=True)
    us = us_rows()
    au = au_rows()
    status = []
    for r in us:
        path = us_path(r)
        meta_path = path.with_suffix(path.suffix + ".request.json")
        primary = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        primary_meta = verified_meta(path)
        fallback_meta = verified_meta(us_fallback_path(r)) if not primary_meta else None
        m = primary if primary_meta else fallback_meta or primary
        verified = bool(primary_meta or fallback_meta)
        oid = sid("obj", "us_fr_raw", r["canonical_url"])
        status.append({"series": US_SOURCE, "document_id": sid("doc", US_SOURCE, r["canonical_url"]),
                       "canonical_url": r["canonical_url"], "date_value": r["publication_date"], "date_precision": "day",
                       "agency": r["agency_strata"], "genre": r["genre"], "request_url": m.get("request_url", ""),
                       "final_url": m.get("final_url", ""), "http_status": m.get("http_status", ""),
                       "retrieved_at_utc": m.get("retrieved_at_utc", ""), "mime_type": m.get("mime_type", ""),
                       "byte_count": m.get("byte_count", ""), "sha256": m.get("sha256", ""),
                       "raw_path": m.get("raw_path", ""), "fetch_status": "downloaded" if verified else m.get("status", "not_requested"),
                       "failure_reason": m.get("error", ""),
                       "source_route": "govinfo_html_fallback" if fallback_meta else "federalregister_raw_text",
                       "primary_raw_text_http_status": primary.get("http_status", "")})
    ae = {r[0]: r for r in c.execute("SELECT document_id, date_value, date_precision, original_publisher FROM us_au_record_evidence WHERE source_series=?", [AU_SOURCE]).fetchall()}
    reused = {r[0]: r for r in c.execute("SELECT content_object_id, request_url, final_url, http_status, retrieved_at, mime_type, byte_count, sha256, raw_path, fetch_status, failure_reason FROM us_au_fetch_evidence").fetchall()}
    for r in au:
        did = sid("doc", AU_SOURCE, r["landing_url"])
        p = HERE / "raw" / "au_landing" / (sid("", r["landing_url"]) + ".html")
        mp = p.with_suffix(p.suffix + ".request.json")
        m = json.loads(mp.read_text()) if mp.exists() else {}
        prior = reused.get(sid("obj", "au_landing", r["landing_url"]))
        if prior and not m:
            m = {"request_url": prior[1], "final_url": prior[2], "http_status": prior[3],
                 "retrieved_at_utc": str(prior[4]), "mime_type": prior[5], "byte_count": prior[6],
                 "sha256": prior[7], "raw_path": prior[8], "status": "reused_verified_08", "error": ""}
        status.append({"series": AU_SOURCE, "document_id": did, "canonical_url": r["landing_url"],
                       "date_value": ae.get(did, (None, "", "unknown", ""))[1] or "", "date_precision": ae.get(did, (None, "", "unknown", ""))[2],
                       "agency": ae.get(did, (None, "", "", ""))[3] or "unknown", "genre": "catalogue_candidate",
                       "request_url": m.get("request_url", ""), "final_url": m.get("final_url", ""),
                       "http_status": m.get("http_status", ""), "retrieved_at_utc": m.get("retrieved_at_utc", ""),
                       "mime_type": m.get("mime_type", ""), "byte_count": m.get("byte_count", ""),
                       "sha256": m.get("sha256", ""), "raw_path": m.get("raw_path", ""),
                       "fetch_status": "downloaded" if verified_meta(p) else m.get("status", "not_requested"),
                       "failure_reason": m.get("error", ""), "source_route": "dcceew_current_or_reused",
                       "primary_raw_text_http_status": ""})
    fields = list(status[0])
    csv_write(HERE / "reports" / "object_status.csv", fields, status)
    csv_write(HERE / "reports" / "exceptions.csv", fields, [r for r in status if r["fetch_status"] == "failed"])
    csv_write(HERE / "reports" / "pending_records.csv", fields, [r for r in status if r["fetch_status"] == "not_requested"])
    dbrows = c.execute("""SELECT d.source_id, d.document_id, e.date_value, e.date_precision,
        count(DISTINCT v.content_version_id) AS versions,
        count(DISTINCT CASE WHEN s.representation_kind='source_extracted' THEN s.content_version_id END) AS extracted_versions,
        count(DISTINCT CASE WHEN s.representation_kind='cleaned' THEN s.content_version_id END) AS cleaned_versions,
        count(DISTINCT CASE WHEN s.representation_kind='source_extracted' THEN s.segment_id END) AS source_segments
        FROM documents d JOIN us_au_record_evidence e USING(document_id)
        LEFT JOIN document_content_objects x USING(document_id)
        LEFT JOIN content_versions v USING(content_object_id)
        LEFT JOIN text_segments s USING(content_version_id)
        WHERE d.source_id IN (?,?) GROUP BY 1,2,3,4""", [US_SOURCE, AU_SOURCE]).fetchall()
    db = {r[1]: r for r in dbrows}
    object_rows = c.execute("""SELECT d.source_id, d.document_id, x.content_object_id, x.relationship_type,
        o.canonical_url, v.content_version_id, v.raw_path, v.storage_sha256, v.byte_size, v.mime_type,
        count(DISTINCT CASE WHEN s.representation_kind='source_extracted' THEN s.segment_id END),
        count(DISTINCT CASE WHEN s.representation_kind='cleaned' THEN s.segment_id END)
        FROM documents d JOIN document_content_objects x USING(document_id)
        JOIN content_objects o USING(content_object_id)
        LEFT JOIN content_versions v USING(content_object_id)
        LEFT JOIN text_segments s USING(content_version_id)
        WHERE d.source_id IN (?,?)
        GROUP BY 1,2,3,4,5,6,7,8,9,10""", [US_SOURCE, AU_SOURCE]).fetchall()
    content_status = []
    for x in object_rows:
        state = "not_requested" if x[5] is None else "cleaned" if x[11] else "source_extracted" if x[10] else "needs_ocr" if "pdf" in (x[9] or "").lower() else "unsupported_format" if any(s in (x[9] or "").lower() for s in ["rtf", "octet-stream"]) else "no_text_or_extraction_failed"
        content_status.append({"series": x[0], "document_id": x[1], "content_object_id": x[2], "role": x[3],
            "canonical_url": x[4], "content_version_id": x[5] or "", "raw_path": x[6] or "", "sha256": x[7] or "",
            "byte_count": x[8] or "", "mime_type": x[9] or "", "source_segments": x[10], "cleaned_segments": x[11], "status": state})
    csv_write(HERE / "reports" / "content_status.csv", list(content_status[0]), content_status)
    csv_write(HERE / "reports" / "success_records.csv", list(content_status[0]), [r for r in content_status if r["status"] == "cleaned"])
    csv_write(HERE / "reports" / "extraction_exceptions.csv", list(content_status[0]), [r for r in content_status if r["status"] in {"needs_ocr", "unsupported_format", "no_text_or_extraction_failed"}])
    months = []
    y, m = 1988, 1
    while (y, m) <= (2026, 9):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13: y, m = y + 1, 1
    agg = defaultdict(lambda: Counter())
    us_hits = rows(PRE / "us_fr_records.csv")
    seen = set()
    for r in us_hits:
        key = (r["agency_stratum"], r["genre"], r["publication_date"][:7], r["canonical_url"])
        if key in seen: continue
        seen.add(key)
        agg[(US_SOURCE, r["agency_stratum"], r["genre"], r["publication_date"][:7])]["target"] += 1
    for r in status:
        d = db.get(r["document_id"])
        if r["series"] == US_SOURCE:
            mm = r["date_value"][:7]
            for org in r["agency"].split(";"):
                a = agg[(US_SOURCE, org, r["genre"], mm)]
                a["enumerated"] += 1
                if r["fetch_status"] != "not_requested": a["requested"] += 1
                if r["fetch_status"] in {"downloaded", "reused_verified_08"}: a["downloaded"] += 1
                if d:
                    a["in_db"] += 1
                    if d[5]: a["extractable"] += 1
                    if d[6]: a["cleaned"] += 1
                    a["segments"] += d[7]
        else:
            a = agg[(AU_SOURCE, r["agency"], r["genre"], r["date_value"][:7] if r["date_precision"] in {"day", "month"} else "unknown")]
            a["enumerated"] += 1
            if r["fetch_status"] != "not_requested": a["requested"] += 1
            if r["fetch_status"] in {"downloaded", "reused_verified_08"}: a["downloaded"] += 1
            if d:
                a["in_db"] += 1
                if d[5]: a["extractable"] += 1
                if d[6]: a["cleaned"] += 1
                a["segments"] += d[7]
    monthly = []
    for mm in months:
        for org in ["EPA", "DOE"]:
            for genre in ["final_rule", "proposed_rule"]:
                a = agg[(US_SOURCE, org, genre, mm)]
                monthly.append({"series": US_SOURCE, "jurisdiction": "US_federal", "role": "government", "agency": org, "genre": genre,
                                "date_basis": "Federal_Register_publication_date_day", "year_month": mm,
                                "target": a["target"] if mm >= "1994-01" else "", "enumerated": a["enumerated"], "requested": a["requested"],
                                "downloaded": a["downloaded"], "extractable": a["extractable"],
                                "in_db": a["in_db"], "cleaned": a["cleaned"],
                                "n_enumerated_targets": a["enumerated"] if mm >= "1994-01" else "",
                                "n_unique_parent_records": a["enumerated"] if mm >= "1994-01" else "",
                                "n_text_available_parents": a["extractable"], "n_usable_parents": a["cleaned"],
                                "n_relevant_usable_parents": "not_yet_assessed", "n_segments": a["segments"],
                                "coverage_status": "unsupported_source_period" if mm < "1994-01" else ("verified_zero_in_selected_series" if a["target"] == 0 else "partial_body_acquisition" if a["downloaded"] < a["target"] else "enumerated_and_usable" if a["cleaned"] == a["target"] else "downloaded_extraction_pending"),
                                "reason": "API starts in 1994; separate print archive needed" if mm < "1994-01" else "US selected agency/genre partitions; cutoff bin partial" if mm == "2026-09" else "Selected API series only"})
        a = Counter()
        for key, value in agg.items():
            if key[0] == AU_SOURCE and key[3] == mm: a.update(value)
        monthly.append({"series": AU_SOURCE, "jurisdiction": "AU_federal", "role": "government", "agency": "publisher_mixed_or_unknown", "genre": "catalogue_candidate",
                        "date_basis": "original_issue_date_only; CMS_excluded", "year_month": mm,
                        "target": "", "enumerated": a["enumerated"], "requested": a["requested"], "downloaded": a["downloaded"],
                        "extractable": a["extractable"], "in_db": a["in_db"], "cleaned": a["cleaned"],
                        "n_enumerated_targets": "", "n_unique_parent_records": a["enumerated"],
                        "n_text_available_parents": a["extractable"], "n_usable_parents": a["cleaned"],
                        "n_relevant_usable_parents": "not_yet_assessed", "n_segments": a["segments"],
                        "coverage_status": "original_date_denominator_unknown", "reason": "Current catalogue has no verified monthly denominator; only independently dated originals appear in month"})
    unknown = Counter()
    for key, value in agg.items():
        if key[0] == AU_SOURCE and key[3] == "unknown": unknown.update(value)
    monthly.append({"series": AU_SOURCE, "jurisdiction": "AU_federal", "role": "government", "agency": "publisher_mixed_or_unknown",
                    "genre": "catalogue_candidate", "date_basis": "year_only_or_unknown_original_issue_date", "year_month": "unknown_month",
                    "target": 821, "enumerated": unknown["enumerated"], "requested": unknown["requested"], "downloaded": unknown["downloaded"],
                    "extractable": unknown["extractable"], "in_db": unknown["in_db"], "cleaned": unknown["cleaned"],
                    "n_enumerated_targets": unknown["enumerated"], "n_unique_parent_records": "not_verified_for_all_candidates",
                    "n_text_available_parents": unknown["extractable"], "n_usable_parents": "not_month_assignable",
                    "n_relevant_usable_parents": "not_yet_assessed", "n_segments": unknown["segments"],
                    "coverage_status": "unknown_original_month", "reason": "Year-only and undated candidates are retained outside exact-month bins"})
    csv_write(HERE / "reports" / "monthly_progress.csv", list(monthly[0]), monthly)
    event = []
    for offset in range(-24, 25):
        index = 2015 * 12 + 11 + offset
        year, month0 = divmod(index, 12)
        mm = f"{year:04d}-{month0+1:02d}"
        for record in monthly:
            if record["year_month"] == mm:
                event.append({"event_id": "paris_agreement_adoption_candidate", "event_date": "2015-12-12",
                    "event_source": "https://unfccc.int/process-and-meetings/the-paris-agreement",
                    "relative_month": offset, "bin_role": "pre" if offset < 0 else "event" if offset == 0 else "post",
                    "shared_role_availability": "government_only; media_and_public_not_audited_here", **record})
    csv_write(HERE / "reports" / "event_window_2015_paris_coverage.csv", list(event[0]), event)
    counts = c.execute("""SELECT source_id, count(*) FROM documents WHERE source_id IN (?,?) GROUP BY 1""", [US_SOURCE, AU_SOURCE]).fetchall()
    versions = c.execute("""SELECT d.source_id, count(DISTINCT v.content_version_id) FROM documents d JOIN document_content_objects x USING(document_id) JOIN content_versions v USING(content_object_id) WHERE d.source_id IN (?,?) GROUP BY 1""", [US_SOURCE, AU_SOURCE]).fetchall()
    au_browser_files = c.execute("""SELECT count(DISTINCT v.content_version_id), count(DISTINCT d.document_id)
        FROM documents d JOIN document_content_objects x USING(document_id)
        JOIN content_versions v USING(content_object_id)
        WHERE d.source_id=? AND v.raw_path LIKE '%/raw/au_files/%'""", [AU_SOURCE]).fetchone()
    raw_count = c.execute("SELECT count(*) FROM text_segments WHERE extraction_run_id IN (SELECT extraction_run_id FROM extraction_runs WHERE batch_id IN ('us_fr_epa_doe_rules_1994_v1','au_dcceew_2026_snapshot_v1')) AND representation_kind='source_extracted'").fetchone()[0]
    clean_count = c.execute("SELECT count(*) FROM text_segments WHERE extraction_run_id IN (SELECT extraction_run_id FROM extraction_runs WHERE batch_id IN ('us_fr_epa_doe_rules_1994_v1','au_dcceew_2026_snapshot_v1')) AND representation_kind='cleaned'").fetchone()[0]
    orphan = c.execute("SELECT count(*) FROM text_segments s LEFT JOIN content_versions v USING(content_version_id) WHERE v.content_version_id IS NULL").fetchone()[0]
    result = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "documents_by_series": dict(counts), "versions_by_series": dict(versions),
              "US_enumerated_unique": len(us), "AU_catalogue_unique": len(au),
              "US_downloaded_verified": sum(r["series"] == US_SOURCE and r["fetch_status"] == "downloaded" for r in status),
              "US_raw_text_404_or_410_recovered_by_govinfo_html": sum(r["series"] == US_SOURCE and r["source_route"] == "govinfo_html_fallback" for r in status),
              "AU_new_landing_downloaded_verified": sum(r["series"] == AU_SOURCE and r["fetch_status"] == "downloaded" for r in status),
              "AU_browser_original_file_versions_ingested": au_browser_files[0],
              "AU_browser_parent_works_with_files": au_browser_files[1],
              "AU_reused_landing_verified": sum(r["series"] == AU_SOURCE and r["fetch_status"] == "reused_verified_08" for r in status),
              "source_segments": raw_count, "cleaned_segments": clean_count, "orphan_segments": orphan,
              "failed_requests": sum(r["fetch_status"] == "failed" for r in status),
              "AU_precise_month_candidates": sum(r["series"] == AU_SOURCE and r["date_precision"] in {"day", "month"} for r in status),
              "AU_original_date_unknown": sum(r["series"] == AU_SOURCE and r["date_precision"] == "unknown" for r in status)}
    (HERE / "reports" / "quality_metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    c.close()


if __name__ == "__main__": main()
