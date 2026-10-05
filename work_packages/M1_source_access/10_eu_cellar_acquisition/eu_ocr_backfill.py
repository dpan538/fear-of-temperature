"""Idempotently restage months with verified OCR sidecars while Item writer is stopped."""
import csv
import fcntl
import json

import duckdb

from eu_acquire import HERE
from eu_stage import DB, setup, stage_month


def main():
    audit = json.loads((HERE / "reports" / "item_byte_audit.json").read_text())
    if audit["issue_count"]:
        raise RuntimeError("Item byte audit must pass before OCR backfill")
    with (HERE / "reports" / "eu_work_dispositions.csv").open(newline="", encoding="utf-8") as handle:
        months = sorted({row["year_month"] for row in csv.DictReader(handle)
                         if row["disposition"] == "ocr_candidate_layout_review"})
    lock_path = HERE / "manifests" / "item_supervisor.lock"
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        c = duckdb.connect(str(DB))
        try:
            setup(c)
            for month in months:
                stage_month(c, month)
            result = c.execute("SELECT COUNT(*) FROM eu_content_versions WHERE extraction_status='ocr_candidate_text_extracted'").fetchone()[0]
        finally:
            c.close()
    print(json.dumps({"restaged_months": len(months), "ocr_candidate_versions_in_stage": result}))


if __name__ == "__main__":
    main()
