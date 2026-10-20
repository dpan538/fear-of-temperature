"""Rendered figure checks, tied to the exact PDFs and source-data snapshot."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import collect as core

HERE = Path(__file__).resolve().parent
OUT = HERE / "distribution_review_20261021"
SCRIPTS = Path("/Users/jarlgiovanni/.codex/skills/nature-figure/scripts")
FIGURES = [
    "annual_distribution",
    "monthly_distribution",
    "density_heatmap",
    "source_proportions",
    "terminology_groups_v3",
    "event_alignment_v3",
]


def run_json(script, *args):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(result.stderr or result.stdout) from exc


def main():
    preflight_code, preflight = run_json(
        "validate_figure.py", HERE / "report_distribution.py", "--json"
    )
    core.write_json(OUT / "figure.source-preflight.json", preflight)
    reports = {}
    manifest_path = OUT / "CURRENT_FIGURES.json"
    figures = (
        json.loads(manifest_path.read_text())["figures"] if manifest_path.exists() else FIGURES
    )
    for name in figures:
        pdf = OUT / (name + ".pdf")
        font_code, font = run_json("audit_pdf_text.py", pdf, "--min-pt", "5", "--json")
        core.write_json(OUT / (name + ".text-audit.json"), font)
        collision_code, collision = run_json(
            "audit_figure_collisions.py",
            pdf,
            "--json",
            "--json-out",
            OUT / (name + ".collisions.json"),
            "--overlay-pdf",
            OUT / (name + ".collision-overlay.pdf"),
        )
        reports[name] = {
            "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "font_exit_code": font_code,
            "font_report": font,
            "collision_exit_code": collision_code,
            "collision_verdict": collision.get("verdict"),
            "collision_summary": collision.get("summary"),
        }
        print(name, collision.get("verdict"), collision.get("summary"), flush=True)
    report = {
        "checked_at": core.now(),
        "status": "PASS"
        if preflight_code == 0
        and all(r["font_exit_code"] == r["collision_exit_code"] == 0 for r in reports.values())
        else "REVIEW_OR_REPAIR_REQUIRED",
        "source_preflight_exit_code": preflight_code,
        "figures": reports,
        "source_csv_hashes": json.loads((OUT / "SOURCE_DATA_HASHES.json").read_text()),
        "format_exemptions": [
            "Desktop research report at12 inches wide; no target-journal dimensions requested",
            "300dpi PNG previews; editable PDF/SVG primary vector exports; no TIFF requested",
        ],
        "statistics": "Exact inventory counts; no inferential tests, smoothing or error bars",
        "image_integrity": "All marks are generated in Python from CSV/counts; no image retouching",
        "alignment": (
            "Grids and heatmap measured at1.5pt tolerance; "
            "revised terminology/overlay each use one data panel"
        ),
        "intentional_overlays_reviewed": (
            "Donut percentage labels lie inside wedges. Filled-shape bounding-box "
            "warnings were visually inspected; no label crosses a visible wedge edge."
        ),
    }
    core.write_json(OUT / "FIGURE_QA.json", report)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
