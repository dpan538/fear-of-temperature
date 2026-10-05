"""Confirm HTML table placeholders are present in saved source Items."""
import csv
import json
from collections import Counter
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from eu_acquire import HERE


def main():
    source = HERE / "reports" / "eu_work_dispositions.csv"
    with source.open(newline="", encoding="utf-8") as handle:
        selected = [row for row in csv.DictReader(handle)
                    if row["disposition"] == "source_html_table_placeholder_review"]
    rows = []
    issues = []
    for row in selected:
        path = HERE / row["raw_path"]
        if not path.exists():
            issues.append(f"missing_original: {row['work_uri']}")
            continue
        body = path.read_bytes()
        escaped = body.count(b"&gt;TABLE&gt;")
        html_tables = len(BeautifulSoup(body, "html.parser").find_all("table"))
        if not escaped:
            issues.append(f"disposition_without_source_placeholder: {row['work_uri']}")
        rows.append({"work_uri": row["work_uri"], "year_month": row["year_month"],
                     "raw_path": row["raw_path"], "raw_sha256": row["raw_sha256"],
                     "escaped_table_placeholders": escaped, "html_table_elements": html_tables,
                     "english_item_alternatives": row["item_alternatives"],
                     "status": "source_placeholder_no_html_table" if escaped and not html_tables
                     else "source_table_structure_review"})
    output = HERE / "reports" / "html_placeholder_audit.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["work_uri", "year_month", "raw_path", "raw_sha256",
                                                  "escaped_table_placeholders", "html_table_elements",
                                                  "english_item_alternatives", "status"])
        writer.writeheader()
        writer.writerows(rows)
    result = {"audited_at_utc": datetime.now(timezone.utc).isoformat(),
              "selected_placeholder_works": len(selected), "source_checked": len(rows),
              "status_counts": dict(Counter(row["status"] for row in rows)),
              "issue_count": len(issues), "issues": issues}
    (HERE / "reports" / "html_placeholder_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
