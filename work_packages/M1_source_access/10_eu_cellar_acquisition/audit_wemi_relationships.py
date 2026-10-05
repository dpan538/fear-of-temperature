"""Verify completed Work-to-English-Item manifests against saved SPARQL batches."""
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone

from eu_acquire import HERE

OUT = HERE / "reports" / "wemi_relationship_audit.json"


def rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    states = sorted((HERE / "manifests" / "wemi").glob("*.json"))
    completed = [p for p in states if json.loads(p.read_text()).get("status") == "complete"]
    issues = []
    pages = 0
    linked_total = 0
    unlinked_total = 0
    relationships = 0
    for state_path in completed:
        month = state_path.stem
        state = json.loads(state_path.read_text())
        work_list = sorted({r["work_uri"] for r in rows(HERE / "manifests" / "months" / f"{month}.csv")})
        manifest = rows(state_path.with_suffix(".csv"))
        columns = ("work", "expr", "manif", "format", "item", "source_page")
        want = Counter(tuple(r[k] for k in columns) for r in manifest)
        got = Counter()
        batch_count = state["batches"]
        requested_in_order = []
        actual_page_files = list((HERE / "raw" / "wemi_pages" / month[:4]).glob(f"{month}_batch_*.csv"))
        if len(actual_page_files) != batch_count:
            issues.append({"month": month, "reason": "batch_count", "observed": len(actual_page_files), "expected": batch_count})
        for batch_no in range(batch_count):
            page = HERE / "raw" / "wemi_pages" / month[:4] / f"{month}_batch_{batch_no:04d}.csv"
            metadata = page.with_suffix(".request.json")
            if not page.exists() or not metadata.exists():
                issues.append({"month": month, "reason": "missing_page_or_request", "batch": batch_no})
                continue
            body = page.read_bytes()
            meta = json.loads(metadata.read_text())
            expected_works = meta.get("requested_works", [])
            requested_in_order.extend(expected_works)
            if (meta.get("status") != "downloaded" or meta.get("http_status") != 200
                    or meta.get("sha256") != hashlib.sha256(body).hexdigest()
                    or meta.get("byte_count") != len(body)
                    or not expected_works or expected_works != sorted(set(expected_works))):
                issues.append({"month": month, "reason": "page_hash_or_request", "batch": batch_no})
            parsed = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
            locator = str(page.relative_to(HERE))
            for r in parsed:
                if r["work"] not in expected_works:
                    issues.append({"month": month, "reason": "response_work_outside_batch", "batch": batch_no})
                    break
                got[tuple(r[k] if k != "source_page" else locator for k in columns)] += 1
            pages += 1
        if requested_in_order != work_list:
            issues.append({"month": month, "reason": "requested_works_not_exact_month_partition"})
        if got != want:
            issues.append({"month": month, "reason": "raw_manifest_rows_differ",
                           "raw_only": sum((got-want).values()), "manifest_only": sum((want-got).values())})
        linked = {r["work"] for r in manifest}
        if (len(linked) != state.get("works_with_items") or len(work_list)-len(linked) != state.get("works_without_items")
                or len(manifest) != state.get("item_relationship_rows") or len(work_list) != state.get("enumerated_works")):
            issues.append({"month": month, "reason": "relationship_count"})
        linked_total += len(linked)
        unlinked_total += len(work_list)-len(linked)
        relationships += len(manifest)
    result = {"audited_at_utc": datetime.now(timezone.utc).isoformat(),
              "completed_months": len(completed), "saved_batch_pages": pages,
              "item_linked_work_months": linked_total, "no_item_work_months": unlinked_total,
              "relationship_rows": relationships, "issue_count": len(issues), "issues": issues[:100]}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "issues"}), flush=True)
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
