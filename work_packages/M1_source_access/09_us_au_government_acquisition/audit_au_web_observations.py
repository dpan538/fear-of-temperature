"""Audit read-only Australian page evidence against the frozen catalogue."""
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone

from acquire import HERE, au_rows


def main():
    rows = [json.loads(line) for line in (HERE / "web_observations.jsonl").read_text().splitlines()
            if line.strip()]
    frozen = {row["landing_url"] for row in au_rows()}
    issues = []
    seen = set()
    statuses = Counter()
    attachment_urls = 0
    for row in rows:
        url = row["landing_url"]
        if url not in frozen:
            issues.append(f"not_in_frozen_catalogue: {url}")
        if url in seen:
            issues.append(f"duplicate_landing: {url}")
        seen.add(url)
        status = row.get("web_fetch_status", "earlier_manual_observation")
        statuses[status] += 1
        if status == "observed_official_landing":
            evidence = row.get("article_text", "")
            if url not in evidence or "Content type: text/html" not in evidence or not row.get("title"):
                issues.append(f"landing_evidence_mismatch: {url}")
        for attachment in row.get("attachments", []):
            attachment_urls += 1
            if not attachment["url"].startswith("https://www.dcceew.gov.au/sites/default/files/"):
                issues.append(f"unexpected_attachment_route: {url}")
            if row.get("transport") == "web_read_only_official_landing_pdf_no_raw_bytes":
                pdf_evidence = row.get("pdf_web_excerpt", "")
                landing_ref = re.search(r"cite(turn\d+view\d+)", row.get("article_text", ""))
                clicked_ref = re.search(r'Source: click\(\{"ref_id":"(turn\d+view\d+)"', pdf_evidence)
                if attachment["url"] not in pdf_evidence or not landing_ref or not clicked_ref or landing_ref[1] != clicked_ref[1]:
                    issues.append(f"attachment_landing_click_mismatch: {url}")
    outcome_path = HERE / "reports" / "au_candidate_outcomes.csv"
    with outcome_path.open(newline="", encoding="utf-8") as handle:
        outcomes = list(csv.DictReader(handle))
    if len(outcomes) != len(frozen) or {row["landing_url"] for row in outcomes} != frozen:
        issues.append("per_candidate_outcomes_do_not_match_frozen_catalogue")
    if any(row["outcome"] == "not_yet_visited_browser_route" for row in outcomes):
        issues.append("unvisited_candidate_remains")
    result = {"audited_at_utc": datetime.now(timezone.utc).isoformat(),
              "frozen_landing_candidates": len(frozen), "web_observation_rows": len(rows),
              "web_observation_statuses": dict(statuses), "web_attachment_urls": attachment_urls,
              "per_candidate_outcomes": dict(Counter(row["outcome"] for row in outcomes)),
              "issue_count": len(issues), "issues": issues}
    out = HERE / "reports" / "au_web_observations_audit.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("frozen_landing_candidates", "web_observation_rows",
                                             "web_observation_statuses", "web_attachment_urls", "issue_count")}))
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
