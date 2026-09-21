#!/usr/bin/env python3
"""Rebuild the bounded M1 database pilot from the saved M1.1 evidence."""

from __future__ import annotations

from pathlib import Path

from fear_temperature.database_pilot import rebuild_pilot

PROJECT_ROOT = Path(__file__).resolve().parents[4]
WORK_PACKAGE = Path(__file__).resolve().parents[1]
FEASIBILITY = WORK_PACKAGE.parent / "01_feasibility"


def main() -> int:
    result = rebuild_pilot(
        FEASIBILITY,
        WORK_PACKAGE / "fear_temperature_m1_pilot.duckdb",
        WORK_PACKAGE / "exports",
        project_root=PROJECT_ROOT,
        quality_report_path=WORK_PACKAGE / "data_quality_report.md",
        dictionary_path=WORK_PACKAGE / "data_dictionary.csv",
        manifest_path=WORK_PACKAGE / "rebuild_manifest.json",
    )
    print(
        "M1 database pilot rebuilt: "
        f"{result['validation']['table_counts']['documents']} documents, "
        f"status={result['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
