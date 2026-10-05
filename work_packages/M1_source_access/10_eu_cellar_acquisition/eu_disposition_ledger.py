"""One current, non-inflated acquisition disposition per enumerated EU Work."""
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

from eu_acquire import HERE
from eu_items import path_for, selected

OUT = HERE / "reports" / "eu_work_dispositions.csv"
SUMMARY = HERE / "reports" / "eu_work_dispositions.summary.json"


def read_json(path):
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except json.JSONDecodeError:
        return {}


def disposition(choice):
    if not choice["item_uri"]:
        return "no_english_digital_item_link", {}, {}, {}
    path = path_for(choice["item_uri"])
    meta = read_json(path.with_suffix(".request.json"))
    extract = read_json(path.with_suffix(".extract.json"))
    ocr = read_json(path.with_suffix(".ocr.meta.json"))
    if meta.get("status") == "failed":
        return "selected_item_failed", meta, extract, ocr
    if meta.get("status") != "downloaded":
        return "selected_item_not_requested", meta, extract, ocr
    if not path.exists() or path.stat().st_size != meta.get("byte_count"):
        return "downloaded_checkpoint_byte_size_mismatch", meta, extract, ocr
    if ocr.get("status") == "ocr_candidate_text_extracted":
        return "ocr_candidate_layout_review", meta, extract, ocr
    if extract.get("status") == "scanned_or_empty_text_layer":
        return "acquired_scan_ocr_pending", meta, extract, ocr
    if extract.get("status") == "text_extracted":
        if choice["format"].lower() in ("html", "xhtml"):
            blocks = path.with_suffix(".blocks.jsonl")
            if blocks.exists() and ">TABLE>" in blocks.read_text(encoding="utf-8"):
                return "source_html_table_placeholder_review", meta, extract, ocr
        return "source_text_extracted_relevance_unreviewed", meta, extract, ocr
    return "acquired_extraction_pending_or_failed", meta, extract, ocr


def main():
    months = sorted(p.stem for p in (HERE / "manifests" / "months").glob("*.json"))
    counts = Counter()
    by_year = defaultdict(Counter)
    seen = set()
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        fields = ["work_uri", "year_month", "document_dates", "expression_uri", "manifestation_uri",
                  "selected_item_uri", "selected_format", "item_alternatives", "selection_status",
                  "disposition", "http_status", "error", "raw_path", "raw_sha256", "byte_count",
                  "extraction_status", "ocr_status"]
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        for month in months:
            for choice in selected(month):
                work = choice["work_uri"]
                if work in seen:
                    raise RuntimeError(f"duplicate global Work URI in disposition ledger: {work}")
                seen.add(work)
                state, meta, extract, ocr = disposition(choice)
                writer.writerow({"work_uri": work, "year_month": month,
                                 "document_dates": choice["document_dates"],
                                 "expression_uri": choice["expression_uri"],
                                 "manifestation_uri": choice["manifestation_uri"],
                                 "selected_item_uri": choice["item_uri"],
                                 "selected_format": choice["format"],
                                 "item_alternatives": choice["item_alternatives"],
                                 "selection_status": choice["selection_status"],
                                 "disposition": state, "http_status": meta.get("http_status", ""),
                                 "error": meta.get("error", ""), "raw_path": meta.get("raw_path", ""),
                                 "raw_sha256": meta.get("sha256", ""), "byte_count": meta.get("byte_count", ""),
                                 "extraction_status": extract.get("status", ""),
                                 "ocr_status": ocr.get("status", "")})
                counts[state] += 1
                by_year[month[:4]][state] += 1
    result = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "unique_works": len(seen), "status_counts": dict(counts),
              "by_year": {y: dict(c) for y, c in sorted(by_year.items())},
              "notes": "Text extraction is not a relevance or complete-body review; pages, formats and annexes do not add Works."}
    SUMMARY.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"unique_works": len(seen), "status_counts": dict(counts)}), flush=True)


if __name__ == "__main__":
    main()
