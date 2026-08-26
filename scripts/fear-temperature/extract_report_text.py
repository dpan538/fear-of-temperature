#!/usr/bin/env python3
"""Extract supplied research PDFs for reproducible inspection.

Text extraction is an inspection aid only; page images remain authoritative
when layout, tables, or quotation boundaries matter.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path("/tmp/fear_temperature_report_text")


def safe_name(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("_") + ".txt"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for path in sorted(ROOT.glob("*.pdf")):
        reader = PdfReader(path)
        page_texts = []
        for page_number, page in enumerate(reader.pages, start=1):
            page_texts.append(f"\n\n===== PAGE {page_number} =====\n\n{page.extract_text() or ''}")
        text = "".join(page_texts)
        output_path = OUTPUT / safe_name(path)
        output_path.write_text(text, encoding="utf-8")
        manifest.append(
            {
                "file": path.name,
                "pages": len(reader.pages),
                "extracted_characters": len(text),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "extracted_text": str(output_path),
            }
        )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
