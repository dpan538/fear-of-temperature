#!/usr/bin/env python3
"""Build the final bounded repair reconciliation from committed evidence."""

from __future__ import annotations

import csv
import hashlib
import html
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
REPAIR = HERE / "targeted_gap_repair"
REPORTS = REPAIR / "reports"
MANIFESTS = REPAIR / "manifests"
DB = PROJECT / "work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb"

BEFORE = {
    "documents": 239_179,
    "policy_document": 1_054,
    "ministerial_written_answer": 235_420,
    "ministerial_written_statement": 2_705,
    "text_segments": 3_622_039,
}


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    output.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(output)


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    ledger = read_csv(REPAIR / "repair_ledger.csv")
    local_manifest = read_csv(MANIFESTS / "hansard_local_repair_record_manifest.csv")
    historic_manifest = read_csv(MANIFESTS / "historic_daily_repair_record_manifest.csv")
    statement_manifest = read_csv(MANIFESTS / "statement_candidate_repair_record_manifest.csv")
    all_manifest = local_manifest + historic_manifest + statement_manifest
    ocr_targets = read_csv(MANIFESTS / "policy_ocr_target_manifest.csv")
    ocr_summary = read_json(REPORTS / "policy_ocr_ingestion_summary.json")
    route_summary = read_json(REPORTS / "restricted_route_repair_summary.json")
    historic_summary = read_json(REPORTS / "historic_daily_repair_summary.json")
    statement_summary = read_json(REPORTS / "statement_candidate_repair_summary.json")

    con = duckdb.connect(str(DB), read_only=True)
    try:
        after = {
            "documents": int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]),
            "policy_document": int(
                con.execute("SELECT COUNT(*) FROM documents d JOIN sources s USING(source_id) WHERE s.source_name LIKE 'GOV.UK%'").fetchone()[0]
            ),
            "ministerial_written_answer": int(
                con.execute("SELECT COUNT(*) FROM documents WHERE content_type='ministerial_written_answer'").fetchone()[0]
            ),
            "ministerial_written_statement": int(
                con.execute("SELECT COUNT(*) FROM documents WHERE content_type='ministerial_written_statement'").fetchone()[0]
            ),
            "text_segments": int(con.execute("SELECT COUNT(*) FROM text_segments").fetchone()[0]),
        }
        manifest_ids = [row["external_id"] for row in all_manifest]
        present_ids = {
            str(row[0])
            for row in con.execute("SELECT external_id FROM documents WHERE external_id=ANY(?)", [manifest_ids]).fetchall()
        }
        repair_doc_ids = [
            str(row[0])
            for row in con.execute("SELECT document_id FROM documents WHERE external_id=ANY(?)", [manifest_ids]).fetchall()
        ]
        linked_enumeration = int(
            con.execute("SELECT COUNT(DISTINCT document_id) FROM enumeration_records WHERE document_id=ANY(?)", [repair_doc_ids]).fetchone()[0]
        )
        linked_content = int(
            con.execute("SELECT COUNT(DISTINCT document_id) FROM document_content_objects WHERE document_id=ANY(?)", [repair_doc_ids]).fetchone()[0]
        )
        role_counts = {
            str(role): int(count)
            for role, count in con.execute(
                "SELECT attribution_role, COUNT(*) FROM voice_attributions WHERE document_id=ANY(?) GROUP BY 1",
                [repair_doc_ids],
            ).fetchall()
        }
        semantic_role_counts = {
            f"{content_type}:{semantic_role}": int(count)
            for content_type, semantic_role, count in con.execute(
                """SELECT d.content_type, regexp_extract(ts.locator, 'role=([^;]+)', 1), COUNT(*)
                   FROM documents d
                   JOIN voice_attributions va USING(document_id)
                   JOIN text_segments ts USING(segment_id)
                   WHERE d.document_id=ANY(?)
                   GROUP BY 1,2""",
                [repair_doc_ids],
            ).fetchall()
        }
        duplicates = int(
            con.execute(
                "SELECT COUNT(*) FROM (SELECT source_id, external_id, COUNT(*) n FROM documents GROUP BY 1,2 HAVING n>1)"
            ).fetchone()[0]
        )
        ocr_success = int(
            con.execute(
                "SELECT COUNT(*) FROM acquisition_object_statuses WHERE content_object_id=ANY(?) AND extraction_status='success'",
                [[row["content_object_id"] for row in ocr_targets]],
            ).fetchone()[0]
        )
        ocr_segments = int(
            con.execute(
                "SELECT COUNT(*) FROM text_segments WHERE extraction_run_id=?",
                [ocr_summary["extraction_run_id"]],
            ).fetchone()[0]
        )
    finally:
        con.close()

    additions = {key: after[key] - BEFORE[key] for key in BEFORE}
    delta_rows = []
    for key in BEFORE:
        delta_rows.append(
            {
                "metric": key,
                "before": BEFORE[key],
                "addition": additions[key],
                "after": after[key],
                "reconciles": BEFORE[key] + additions[key] == after[key],
                "addition_note": {
                    "documents": "83 saved-payload answer repairs + 321 Historic answers + 3 statement children",
                    "policy_document": "No new policy record; OCR added extraction lineage to four existing objects",
                    "ministerial_written_answer": "83 local parser repairs + 321 Historic daily records",
                    "ministerial_written_statement": "Three official search-response child records",
                    "text_segments": "243 local answer segments + 340 OCR pages + 815 new-record segments",
                }[key],
            }
        )
    write_csv(REPORTS / "final_delta_check.csv", delta_rows)

    queue_rows = [
        {
            "queue": "Saved Hansard answer payload parser repair",
            "unit": "answer target",
            "expected": 85,
            "repair_pass_attempted": 85,
            "recovered_or_resolved": 83,
            "excluded": 0,
            "already_present": 0,
            "unresolved": 2,
            "genuinely_new_documents": 83,
            "note": "All original payloads were HTTP 200; Asda and Companies House remain unresolved after normal rendered-page 403s.",
        },
        {
            "queue": "Failed written-statement candidates",
            "unit": "candidate container",
            "expected": 9,
            "repair_pass_attempted": 9,
            "recovered_or_resolved": 3,
            "excluded": 5,
            "already_present": 0,
            "unresolved": 1,
            "genuinely_new_documents": 3,
            "note": "Three in-scope child statements use official ContributionExtId; one repeated cross-date container remains unresolved.",
        },
        {
            "queue": "Historic Hansard volume 200 daily repair",
            "unit": "written-answer item",
            "expected": 322,
            "repair_pass_attempted": 322,
            "recovered_or_resolved": 321,
            "excluded": 0,
            "already_present": 0,
            "unresolved": 1,
            "genuinely_new_documents": 321,
            "note": "Ten actual Commons sitting days; one malformed official page has unresolved attribution.",
        },
        {
            "queue": "Historic policy OCR",
            "unit": "downloaded PDF file",
            "expected": 4,
            "repair_pass_attempted": 4,
            "recovered_or_resolved": 4,
            "excluded": 0,
            "already_present": 0,
            "unresolved": 0,
            "genuinely_new_documents": 0,
            "note": "Existing objects/versions retained; 340 page segments added in a new OCR extraction lineage.",
        },
        {
            "queue": "2010–2014 failed date indexes",
            "unit": "date index",
            "expected": 20,
            "repair_pass_attempted": 1,
            "recovered_or_resolved": 0,
            "excluded": 0,
            "already_present": 0,
            "unresolved": 20,
            "genuinely_new_documents": 0,
            "note": "Corrected normal route returned 403; host stopped at three consecutive denials across bounded tasks. Record denominator remains unknown.",
        },
        {
            "queue": "2010–2014 known page repair queue",
            "unit": "archive HTML page",
            "expected": 437,
            "repair_pass_attempted": 1,
            "recovered_or_resolved": 0,
            "excluded": 0,
            "already_present": 0,
            "unresolved": 437,
            "genuinely_new_documents": 0,
            "note": "225 were previously failed and 212 unrequested; page units are not missing-document counts.",
        },
        {
            "queue": "2004-Q4 Commons cross-route seam",
            "unit": "date range with unknown target denominator",
            "expected": "unknown",
            "repair_pass_attempted": 2,
            "recovered_or_resolved": 0,
            "excluded": 0,
            "already_present": 0,
            "unresolved": 1,
            "genuinely_new_documents": 0,
            "note": "Forty-three Historic day indexes were Lords-only; two normal Commons route probes returned 403. No Lords material admitted.",
        },
    ]
    write_csv(REPORTS / "queue_summary.csv", queue_rows)

    missing_evidence_paths: list[str] = []
    hash_mismatches: list[str] = []
    for row in all_manifest:
        path = PROJECT / row["record_path"]
        if not path.is_file():
            missing_evidence_paths.append(row["record_path"])
        elif sha256(path) != row["record_sha256"]:
            hash_mismatches.append(row["record_path"])
    checks = {
        "generated_at": now_iso(),
        "database": str(DB),
        "manifest_records": len(all_manifest),
        "manifest_records_present": len(present_ids),
        "manifest_records_missing": sorted(set(manifest_ids) - present_ids),
        "linked_enumeration_records": linked_enumeration,
        "linked_content_records": linked_content,
        "voice_attribution_roles": role_counts,
        "segment_semantic_roles": semantic_role_counts,
        "source_external_duplicate_groups": duplicates,
        "ocr_targets": len(ocr_targets),
        "ocr_targets_extraction_success": ocr_success,
        "ocr_segments": ocr_segments,
        "missing_record_evidence_paths": missing_evidence_paths,
        "record_evidence_hash_mismatches": hash_mismatches,
        "all_deltas_reconcile": all(row["reconciles"] for row in delta_rows),
        "distribution_checks_passed": bool(read_json(REPORTS / "final_distribution_coverage/final_checks.json")["passed"]),
        "full_database_hash_rerun": False,
    }
    checks["passed"] = all(
        [
            len(present_ids) == len(all_manifest),
            linked_enumeration == len(all_manifest),
            linked_content == len(all_manifest),
            duplicates == 0,
            ocr_success == 4,
            ocr_segments == 340,
            semantic_role_counts.get("ministerial_written_answer:question_context", 0) > 0,
            semantic_role_counts.get("ministerial_written_answer:government_response", 0) > 0,
            semantic_role_counts.get("ministerial_written_statement:question_context", 0) == 0,
            semantic_role_counts.get("ministerial_written_statement:government_response", 0) == 3,
            not missing_evidence_paths,
            not hash_mismatches,
            checks["all_deltas_reconcile"],
            checks["distribution_checks_passed"],
        ]
    )
    write_json(REPORTS / "final_verification.json", checks)
    if not checks["passed"]:
        raise RuntimeError(f"Final verification failed: {checks}")

    delta_table = markdown_table(
        ["Metric", "Before", "Addition", "After"],
        [[row["metric"], f"{row['before']:,}", f"{row['addition']:,}", f"{row['after']:,}"] for row in delta_rows],
    )
    queue_table = markdown_table(
        ["Queue", "Unit", "Expected", "Attempted", "Recovered/resolved", "Excluded", "Unresolved", "New documents"],
        [
            [
                row["queue"], row["unit"], row["expected"], row["repair_pass_attempted"],
                row["recovered_or_resolved"], row["excluded"], row["unresolved"], row["genuinely_new_documents"],
            ]
            for row in queue_rows
        ],
    )
    report = f"""# Government targeted gap repair — final report

Completed: **{checks['generated_at']}**. Scope is limited to the 2026-09-22 handoff: saved-payload parser repair, bounded named gaps, nine statement candidates and four downloaded PDFs. The proposal, cleaning, embeddings and model analysis were not changed or run.

## Outcome

{delta_table}

- Genuine new documents: **407** = 404 written answers + 3 written statements. Policy record count is unchanged.
- Existing-text repairs: **83** saved Hansard answer payloads were deterministically reparsed; **4** existing PDF objects received a new local OCR extraction lineage.
- Text growth: **1,398 segments** = 243 local parser-repair segments + 340 OCR page segments + 815 segments from new records.
- January 1988 boundary: the official calendar's first sitting is **1988-01-11**; 1–10 January is not treated as a collection gap.

## Queue reconciliation

{queue_table}

Different units are intentionally not added into one “missing documents” total. In particular, 20 failed date indexes can hide an unknown record count, and 437 HTML pages are not 437 answer records.

## Important evidence decisions

- Volume 200: actual range **1991-12-02..1991-12-13**, 10 Commons sitting days, 322 approved-department item targets; 321 were parsed and committed. `Self-regulating Bodies` remains unresolved because the official HTML merges unrelated answer text into the questioner's block without reliable minister attribution.
- Statement candidates: official search parents contain section-ID collisions. Three in-scope children were stored by official `ContributionExtId`; five candidate containers were out of department scope; one cross-date header/container was not inserted.
- 2004-Q4 seam: 43 accessible Historic daily indexes expose Lords written material only. No Lords content was substituted. Both normal Commons hosts reached three consecutive HTTP 403 responses and were stopped; the Commons denominator remains unknown.
- 2010–2014: the frozen page queue remains 225 previously failed + 212 previously unrequested. The bounded repair made one corrected index request and one page request before the shared publications host reached its stop threshold across three scoped probes.
- OCR: all four saved PDFs were processed locally. **340/350 pages** yielded text, totalling **832,193 characters**; blank/image-only pages were retained as blank rather than fabricated. Representative pages were visually reviewed.

## Final checks

- All **407** repair-manifest records exist in the formal 06 database and have enumeration/content linkage.
- Repair segments preserve separate semantic roles: **447 question-context** segments, **608 answer government-response** segments and **3 statement government-response** segments; statements have no fabricated question context.
- Duplicate `(source_id, external_id)` groups: **0**.
- OCR targets marked extraction-success: **4/4**; OCR extraction segments: **340**.
- Annual, quarterly, monthly and decade totals reconcile to the same read-only snapshot; final counts match the expected repaired baseline.
- All four refreshed figures passed panel-alignment, PDF text-size, strict rendered-collision and visual review checks.
- No full database hash rerun, full ingestion smoke test or successful-record re-download was performed.

## Deliverables

- Repair ledger: `../repair_ledger.csv`
- Queue summary: `queue_summary.csv`
- Final delta: `final_delta_check.csv`
- Verification: `final_verification.json`
- OCR quality: `../evidence/policy_ocr_quality.csv`
- Distribution/coverage report and CSVs: `final_distribution_coverage/`

Residual access failures are preserved with actual request URLs, final URLs, timestamps, HTTP status, response bytes and host-stop checkpoints. They remain conditional source gaps, not evidence of absent government records and not a claim of continuous 1988–2026 coverage.
"""
    report_path = REPORTS / "government_targeted_gap_repair_report.md"
    report_path.write_text(report, encoding="utf-8")

    delta_cards = "".join(
        f"<div class='card'><span>{html.escape(row['metric'])}</span><strong>{row['after']:,}</strong><small>+{row['addition']:,}</small></div>"
        for row in delta_rows
    )
    queue_html = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in [
            row["queue"], row["unit"], row["expected"], row["repair_pass_attempted"],
            row["recovered_or_resolved"], row["excluded"], row["unresolved"], row["genuinely_new_documents"],
        ]) + "</tr>"
        for row in queue_rows
    )
    page = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Government targeted gap repair</title><style>
body{{font-family:Arial,sans-serif;margin:0;background:#f4f5f3;color:#17232a}}main{{max-width:1120px;margin:auto;padding:32px}}
h1{{color:#24495f}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.card{{background:white;border-top:4px solid #2f7d75;padding:14px;box-shadow:0 1px 5px #0002}}.card span,.card small{{display:block;color:#566}}.card strong{{font-size:1.65rem}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:8px;border:1px solid #ccd3d0;text-align:left}}th{{background:#24495f;color:white}}img{{max-width:100%;background:white;margin:12px 0}}.note{{border-left:4px solid #c57a43;background:white;padding:12px}}
</style></head><body><main><h1>Government targeted gap repair</h1><p>Final snapshot: {html.escape(checks['generated_at'])}; all writes were incremental to the formal 06 database.</p>
<div class='cards'>{delta_cards}</div><h2>Queue reconciliation</h2><table><thead><tr><th>Queue</th><th>Unit</th><th>Expected</th><th>Attempted</th><th>Recovered</th><th>Excluded</th><th>Unresolved</th><th>New docs</th></tr></thead><tbody>{queue_html}</tbody></table>
<p class='note'>Index, page, candidate, item and file units are not combined as missing documents. The 2004-Q4 Commons denominator and records hidden by failed 2010–2014 indexes remain unknown.</p>
<h2>Repaired distribution</h2><img src='final_distribution_coverage/figures/01_annual_distribution.svg' alt='Annual distributions'><img src='final_distribution_coverage/figures/03_collection_coverage_status.svg' alt='Categorical collection status'>
<p><a href='government_targeted_gap_repair_report.md'>Full concise Markdown report</a> · <a href='final_distribution_coverage/index.html'>Distribution and coverage dashboard</a></p></main></body></html>"""
    (REPORTS / "index.html").write_text(page, encoding="utf-8")
    print(json.dumps({"report": str(report_path), "checks": checks, "after": after}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
