"""Audit saved EU Item originals without locking the active stage database."""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

from eu_acquire import HERE

OUT = HERE / "reports" / "item_byte_audit.json"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    issues = []
    outcomes = Counter()
    roots = [HERE / "raw" / "items", HERE / "raw" / "items_external"]
    files = sorted(p for root in roots if root.exists() for p in root.glob("*/*.request.json"))
    if args.limit:
        files = files[:args.limit]
    for request in files:
        try:
            meta = json.loads(request.read_text())
        except json.JSONDecodeError:
            outcomes["in_progress_checkpoint"] += 1
            continue
        outcomes[meta.get("status", "unknown")] += 1
        if meta.get("status") != "downloaded":
            continue
        source = request.with_name(request.name.replace(".request.json", ".bin"))
        if not source.exists():
            issues.append({"item": meta.get("item_uri"), "issue": "raw_file_missing"})
            continue
        if source.stat().st_size != meta.get("byte_count") or digest(source) != meta.get("sha256"):
            issues.append({"item": meta.get("item_uri"), "issue": "raw_byte_mismatch"})
            continue
        extract_path = source.with_suffix(".extract.json")
        if extract_path.exists():
            try:
                extract = json.loads(extract_path.read_text())
            except json.JSONDecodeError:
                outcomes["in_progress_extraction_checkpoint"] += 1
                continue
            outcomes["extract_" + extract.get("status", "unknown")] += 1
            if extract.get("raw_sha256") != meta["sha256"]:
                issues.append({"item": meta.get("item_uri"), "issue": "extraction_parent_hash_mismatch"})
            derivative = extract.get("textutil_source_path")
            if derivative:
                path = HERE / derivative
                if not path.exists() or digest(path) != extract.get("textutil_source_sha256"):
                    issues.append({"item": meta.get("item_uri"), "issue": "doc_derivative_hash_mismatch"})
        ocr_path = source.with_suffix(".ocr.meta.json")
        if ocr_path.exists():
            ocr = json.loads(ocr_path.read_text())
            outcomes["ocr_" + ocr.get("status", "unknown")] += 1
            pages = source.with_suffix(".ocr.pages.txt")
            lines = source.with_suffix(".ocr.jsonl")
            if (ocr.get("raw_sha256") != meta["sha256"]
                    or not pages.exists() or digest(pages) != ocr.get("pages_sha256")
                    or not lines.exists() or digest(lines) != ocr.get("lines_sha256")):
                issues.append({"item": meta.get("item_uri"), "issue": "ocr_derivative_hash_mismatch"})
    result = {"audited_at_utc": datetime.now(timezone.utc).isoformat(),
              "checkpoint_files": len(files), "outcomes": dict(outcomes),
              "issue_count": len(issues), "issues": issues}
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "issues"}), flush=True)


if __name__ == "__main__":
    main()
