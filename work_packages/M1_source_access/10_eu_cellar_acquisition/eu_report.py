"""Report source-specific EU metadata, Item links and actual staged bodies."""
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone

import duckdb

from eu_acquire import HERE

OUT = HERE / "reports"


def main():
    OUT.mkdir(exist_ok=True)
    month_states = {p.stem: json.loads(p.read_text()) for p in (HERE / "manifests" / "months").glob("*.json")}
    wemi_states = {p.stem: json.loads(p.read_text()) for p in (HERE / "manifests" / "wemi").glob("*.json")}
    c = duckdb.connect(str(HERE / "eu_stage.duckdb"), read_only=True)
    staged = dict(c.execute("""SELECT w.first_seen_month, count(*)
        FROM eu_content_versions v JOIN eu_works w USING(work_uri)
        GROUP BY 1""").fetchall())
    pages = dict(c.execute("""SELECT w.first_seen_month, count(*)
        FROM eu_source_pages p JOIN eu_content_versions v USING(version_id)
        JOIN eu_works w USING(work_uri) GROUP BY 1""").fetchall())
    has_blocks = c.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='eu_source_blocks'").fetchone()[0] > 0
    blocks = dict(c.execute("""SELECT w.first_seen_month, count(*)
        FROM eu_source_blocks b JOIN eu_content_versions v USING(version_id)
        JOIN eu_works w USING(work_uri) GROUP BY 1""").fetchall()) if has_blocks else {}
    statuses = dict(c.execute("SELECT extraction_status, count(*) FROM eu_content_versions GROUP BY 1").fetchall())
    alternatives = c.execute("SELECT count(*) FROM eu_item_candidates WHERE alternatives > 1").fetchone()[0]
    works_in_db = c.execute("SELECT count(*) FROM eu_works").fetchone()[0]
    c.close()
    rows = []
    for month in sorted(month_states):
        work = month_states[month]
        rel = wemi_states.get(month, {})
        rows.append({"year_month": month,
                     "enumerated_works": work["observed_distinct_works"],
                     "work_reconciliation": work["status"],
                     "wemi_status": rel.get("status", "not_yet_harvested"),
                     "works_with_english_item_link": rel.get("works_with_items", ""),
                     "works_without_english_item_link": rel.get("works_without_items", ""),
                     "staged_original_versions": staged.get(month, 0),
                     "staged_text_pages": pages.get(month, 0),
                     "staged_structured_blocks": blocks.get(month, 0),
                     "source_population_boundary": "COM act_preparatory ENG; 2026-09 capped at 21st"})
    with (OUT / "eu_monthly_status.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    annual = defaultdict(lambda: {"months": 0, "works": 0, "wemi_months": 0, "linked": 0,
                                 "no_item": 0, "versions": 0, "pages": 0, "blocks": 0})
    for row in rows:
        year = row["year_month"][:4]
        a = annual[year]
        a["months"] += 1
        a["works"] += row["enumerated_works"]
        if row["wemi_status"] == "complete":
            a["wemi_months"] += 1
            a["linked"] += row["works_with_english_item_link"]
            a["no_item"] += row["works_without_english_item_link"]
        a["versions"] += row["staged_original_versions"]
        a["pages"] += row["staged_text_pages"]
        a["blocks"] += row["staged_structured_blocks"]
    lines = ["# EU Commission CELLAR acquisition status", "",
             f"Generated {datetime.now(timezone.utc).isoformat()}. Study cutoff: 2026-09-21.", "",
             f"The official monthly Work manifest reconciles {len(rows)}/465 bins and {works_in_db:,} unique Work URIs. "
             "Item links and saved original bytes are separate evidence stages.", "",
             "| Year | Work bins | Works | WEMI bins | Item-linked Works | No English digital Item | Staged originals | PDF text pages | Structured text blocks |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for year, a in sorted(annual.items()):
        lines.append(f"| {year} | {a['months']} | {a['works']:,} | {a['wemi_months']} | {a['linked']:,} | {a['no_item']:,} | {a['versions']:,} | {a['pages']:,} | {a['blocks']:,} |")
    lines += ["", f"Staged extraction outcomes: {', '.join(f'{k} {v:,}' for k, v in sorted(statuses.items())) or 'none'}. "
              f"Selected Items with more than one candidate relationship: {alternatives:,}; these require Work/annex review.", "",
              "Annual Item-link and no-Item values cover completed WEMI bins only; zero in an unharvested year means unassessed. "
              "A Work with an Item link is not counted as a downloaded body until the Item stream is saved and hash checked. "
              "A missing English digital Item link is a source outcome, not a zero Work month. "
              "The current Item choice is one candidate per Work; multiple formats or annexes are retained in the WEMI relationship ledger. "
              "The stage and monthly CSV preserve dates and parent boundaries without treating pages as independent Works.", "",
              "See [monthly status](eu_monthly_status.csv), the EU [runbook](../RUNBOOK.md), and the cross-source "
              "[staging integrity audit](../../09_us_au_government_acquisition/reports/staging_quality_audit.json).", ""]
    (OUT / "eu_status.md").write_text("\n".join(lines))
    print(json.dumps({"works": works_in_db, "wemi_months": len(wemi_states),
                      "versions": sum(staged.values()), "text_pages": sum(pages.values()),
                      "structured_blocks": sum(blocks.values())}), flush=True)


if __name__ == "__main__":
    main()
