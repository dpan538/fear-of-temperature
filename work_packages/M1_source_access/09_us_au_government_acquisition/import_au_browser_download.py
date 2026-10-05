"""Preserve an ordinary in-app-browser download with explicit status basis.

Browser downloads expose the completed bytes and source URL but not the HTTP
response headers. `200` in the relational status-code field is a compatibility
inference; the checkpoint makes that evidence limit explicit.
"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from acquire import HERE, rel, sid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--landing-url", required=True)
    parser.add_argument("--original-date", default="")
    parser.add_argument("--date-evidence", default="")
    parser.add_argument("--issuer", default="")
    args = parser.parse_args()
    src = Path(args.source_file)
    if not src.is_file() or not src.resolve().is_relative_to(Path.home() / "Downloads"):
        raise ValueError("source must be an existing browser download in Downloads")
    if not args.url.startswith("https://www.dcceew.gov.au/sites/default/files/"):
        raise ValueError("source URL is outside the official DCCEEW file route")
    extension = args.url.split("?", 1)[0].rsplit(".", 1)[-1].lower()
    if extension not in {"pdf", "docx", "rtf"}:
        raise ValueError("unsupported downloaded format")
    data = src.read_bytes()
    if extension == "pdf" and not data.startswith(b"%PDF-"):
        raise ValueError("downloaded bytes are not PDF")
    if extension == "docx" and not data.startswith(b"PK\x03\x04"):
        raise ValueError("downloaded bytes are not DOCX")
    if extension == "rtf" and not data.lstrip().startswith(b"{\\rtf"):
        raise ValueError("downloaded bytes are not RTF")
    path = HERE / "raw" / "au_files" / f"{sid('', args.url)}.{extension}"
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError("existing official URL has different bytes; preserve as a new version deliberately")
    if not path.exists():
        shutil.copyfile(src, path)
    meta = {"request_url": args.url, "final_url": args.url, "http_status": 200,
            "status_code_basis": "inferred_from_completed_browser_download_not_response_header",
            "transport": "Codex_in_app_browser_downloadMedia", "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "mime_type": {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "rtf": "application/rtf"}[extension],
            "byte_count": len(data), "sha256": digest, "raw_path": rel(path), "status": "downloaded",
            "error": "", "response_headers": {}, "landing_url": args.landing_url,
            "original_date_candidate": args.original_date, "original_date_evidence": args.date_evidence,
            "issuer_candidate": args.issuer}
    path.with_suffix(path.suffix + ".request.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"saved": str(path), "sha256": digest, "bytes": len(data), "status_basis": meta["status_code_basis"]}))


if __name__ == "__main__":
    main()
