"""Verify saved CELLAR Work query pages against the frozen month manifests."""
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone

from eu_acquire import HERE, index, month_bounds

OUT = HERE / "reports" / "work_enumeration_audit.json"


def main():
    expected = index()
    issues = []
    total_pages = 0
    all_works = set()
    manifest_rows = 0
    for month, official_count in sorted(expected.items()):
        state_path = HERE / "manifests" / "months" / f"{month}.json"
        manifest_path = state_path.with_suffix(".csv")
        if not state_path.exists() or not manifest_path.exists():
            issues.append({"month": month, "reason": "missing_month_manifest"})
            continue
        state = json.loads(state_path.read_text())
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            manifest = list(csv.DictReader(handle))
        manifest_rows += len(manifest)
        want = Counter((r["work_uri"], r["date_observed"], r["source_page"]) for r in manifest)
        got = Counter()
        page_files = sorted((HERE / "raw" / "work_pages" / month[:4]).glob(f"{month}_offset_*.csv"))
        expected_pages = (official_count // 500) + 1
        if len(page_files) != expected_pages:
            issues.append({"month": month, "reason": "page_count", "observed": len(page_files), "expected": expected_pages})
        for offset in range(0, expected_pages * 500, 500):
            page = HERE / "raw" / "work_pages" / month[:4] / f"{month}_offset_{offset:05d}.csv"
            metadata = page.with_suffix(".request.json")
            if not page.exists() or not metadata.exists():
                issues.append({"month": month, "reason": "missing_page_or_request", "offset": offset})
                continue
            body = page.read_bytes()
            meta = json.loads(metadata.read_text())
            digest = hashlib.sha256(body).hexdigest()
            if meta.get("status") != "downloaded" or meta.get("sha256") != digest or meta.get("byte_count") != len(body):
                issues.append({"month": month, "reason": "page_bytes_or_status", "offset": offset})
            page_rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
            expected_size = min(500, max(official_count - offset, 0))
            if len(page_rows) != expected_size:
                issues.append({"month": month, "reason": "page_row_count", "offset": offset,
                               "observed": len(page_rows), "expected": expected_size})
            source_page = str(page.relative_to(HERE))
            for row in page_rows:
                got[(row["work"], row["date"][:10], source_page)] += 1
            total_pages += 1
        if got != want:
            issues.append({"month": month, "reason": "raw_manifest_rows_differ",
                           "raw_only": sum((got - want).values()), "manifest_only": sum((want - got).values())})
        works = {r["work_uri"] for r in manifest}
        if len(works) != official_count or state.get("observed_distinct_works") != official_count or state.get("status") != "reconciled":
            issues.append({"month": month, "reason": "official_count_or_state",
                           "observed": len(works), "expected": official_count})
        start, end = month_bounds(month)
        for row in manifest:
            if not start <= row["date_observed"][:10] < end:
                issues.append({"month": month, "reason": "date_outside_month", "work": row["work_uri"]})
                break
        all_works.update(works)
    result = {"audited_at_utc": datetime.now(timezone.utc).isoformat(),
              "official_months": len(expected), "official_month_counts_sum": sum(expected.values()),
              "saved_query_pages": total_pages, "manifest_rows": manifest_rows,
              "globally_distinct_works": len(all_works), "issues": issues[:100], "issue_count": len(issues)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "issues"}), flush=True)
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
