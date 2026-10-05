"""Create page and coordinate preserving OCR sidecars for scan-only EU PDFs."""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from eu_acquire import HERE

SWIFT = HERE / "eu_ocr_vision.swift"
TOOL_VERSION = "apple_vision_en_us_full_plus_heading_region_v2"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1048576), b""):
            h.update(part)
    return h.hexdigest()


def normalize(line, source):
    result = dict(line)
    if source == "top_region":
        result["x"] = 0.05 + 0.90 * line["x"]
        result["y"] = 0.70 + 0.20 * line["y"]
        result["width"] = 0.90 * line["width"]
        result["height"] = 0.20 * line["height"]
    result["method"] = source
    return result


def merge_lines(page):
    lines = [normalize(line, "full_page") for line in page["lines"]]
    for candidate in page.get("top_region_lines", []):
        line = normalize(candidate, "top_region")
        duplicate = any(
            abs(old["y"] - line["y"]) < 0.018
            and abs(old["x"] - line["x"]) < 0.05
            for old in lines
        )
        if not duplicate:
            lines.append(line)
    def is_top(line):
        if line["y"] >= 0.90:
            return True
        return (line["y"] >= 0.70 and 0.15 < line["x"] < 0.50
                and 0.50 < line["x"] + line["width"] < 0.85)
    top = [line for line in lines if is_top(line)]
    bottom = [line for line in lines if line["y"] < 0.08]
    body = [line for line in lines if not is_top(line) and line["y"] >= 0.08]
    left = [line for line in body if line["x"] < 0.50]
    right = [line for line in body if line["x"] >= 0.50]
    ordering = lambda line: (-line["y"], line["x"])
    return sorted(top, key=ordering) + sorted(left, key=ordering) + sorted(right, key=ordering) + sorted(bottom, key=ordering)


def candidates(max_pdf_pages, min_pdf_pages=0):
    roots = [HERE / "raw" / "items", HERE / "raw" / "items_external"]
    checkpoints = sorted(p for root in roots if root.exists() for p in root.glob("*/*.extract.json"))
    for checkpoint in checkpoints:
        try:
            extract = json.loads(checkpoint.read_text())
        except json.JSONDecodeError:
            continue
        if extract.get("status") != "scanned_or_empty_text_layer":
            continue
        if max_pdf_pages and extract.get("pdf_pages", 0) > max_pdf_pages:
            continue
        if extract.get("pdf_pages", 0) < min_pdf_pages:
            continue
        source = checkpoint.with_name(checkpoint.name.replace(".extract.json", ".bin"))
        if source.exists():
            yield source, extract


def run_one(binary, source, extract):
    raw_hash = digest(source)
    if raw_hash != extract["raw_sha256"]:
        raise RuntimeError(f"raw hash mismatch: {source}")
    meta_path = source.with_suffix(".ocr.meta.json")
    pages_path = source.with_suffix(".ocr.pages.txt")
    lines_path = source.with_suffix(".ocr.jsonl")
    if meta_path.exists() and pages_path.exists() and lines_path.exists():
        old = json.loads(meta_path.read_text())
        if (old.get("raw_sha256") == raw_hash and old.get("tool_version") == TOOL_VERSION
                and old.get("pages_sha256") == digest(pages_path)
                and old.get("lines_sha256") == digest(lines_path)):
            return {"status": "already_verified", "pages": old["pdf_pages"], "characters": old["text_characters"]}
    with tempfile.TemporaryDirectory(dir=HERE / "raw") as temp:
        tmp = Path(temp) / "vision.jsonl"
        with tmp.open("wb") as out:
            subprocess.run([str(binary), str(source)], stdout=out, check=True,
                           env={**os.environ, "TMPDIR": temp})
        rows = [json.loads(line) for line in tmp.read_text().splitlines() if line]
        if len(rows) != extract["pdf_pages"] or [r["page"] for r in rows] != list(range(1, len(rows) + 1)):
            raise RuntimeError(f"OCR page alignment failed: {source}")
        merged = []
        for row in rows:
            lines = merge_lines(row)
            merged.append({"page": row["page"], "lines": lines,
                           "source_text": "\n".join(line["text"] for line in lines)})
        lines_tmp = Path(temp) / "merged.jsonl"
        pages_tmp = Path(temp) / "pages.txt"
        lines_tmp.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in merged), encoding="utf-8")
        pages_tmp.write_text("".join(f"\fPAGE={row['page']}\n{row['source_text']}\n" for row in merged), encoding="utf-8")
        status = "ocr_candidate_text_extracted" if any(row["source_text"].strip() for row in merged) else "ocr_empty"
        meta = {"raw_sha256": raw_hash, "tool_version": TOOL_VERSION,
                "pdf_pages": len(merged), "text_characters": sum(len(row["source_text"]) for row in merged),
                "recognized_lines": sum(len(row["lines"]) for row in merged),
                "pages_sha256": digest(pages_tmp), "lines_sha256": digest(lines_tmp),
                "status": status, "reading_order_note": "top region, then left and right columns; inspect original page for layout-dependent quotations"}
        lines_tmp.replace(lines_path)
        pages_tmp.replace(pages_path)
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return {"status": status, "pages": meta["pdf_pages"], "characters": meta["text_characters"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-pdf-pages", type=int, default=30)
    parser.add_argument("--min-pdf-pages", type=int, default=0)
    args = parser.parse_args()
    processed = 0
    failures = HERE / "reports" / "ocr_failures.jsonl"
    for source, extract in candidates(args.max_pdf_pages, args.min_pdf_pages):
        if args.limit and processed >= args.limit:
            break
        try:
            result = run_one(args.binary, source, extract)
        except Exception as exc:
            result = {"status": "ocr_failed", "error": repr(exc)}
            with failures.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"source": str(source.relative_to(HERE)), **result}) + "\n")
        processed += 1
        print(json.dumps({"source": str(source.relative_to(HERE)), **result}), flush=True)


if __name__ == "__main__":
    main()
