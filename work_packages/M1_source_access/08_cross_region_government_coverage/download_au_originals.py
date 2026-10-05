"""Acquire four explicitly linked AU primary PDFs for bounded boundary checks.

This is not a sweep of 821 landing URLs. It preserves response metadata and
does not conflate summaries, background papers, or DOCX formats with new Works.
"""

import csv
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence" / "au_primary_originals"
OUT.mkdir(parents=True, exist_ok=True)
PDFS = {
    "au_net_zero_plan_2025": "https://www.dcceew.gov.au/sites/default/files/documents/net-zero-report.pdf",
    "au_ncras_2021": "https://www.dcceew.gov.au/sites/default/files/documents/national-climate-resilience-and-adaptation-strategy.pdf",
    "au_ncras_2015": "https://www.dcceew.gov.au/sites/default/files/documents/2015-national-climate-resilience-and-adaptation-strategy.pdf",
    "au_epbc_policy_2008": "https://www.dcceew.gov.au/sites/default/files/documents/seismic-whales.pdf",
}


def main():
    fields = ("key", "request_url", "final_url", "http_status", "content_type", "retrieved_at_utc",
              "byte_count", "sha256", "local_path", "file_role", "status")
    rows = []
    for key, url in PDFS.items():
        path = OUT / f"{key}.pdf"
        meta_path = OUT / f"{key}.request.json"
        if path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            body = path.read_bytes()
            if hashlib.sha256(body).hexdigest() == meta["sha256"]:
                rows.append(meta)
                print(key, "cached", len(body), flush=True)
                continue
        stamp = datetime.now(timezone.utc).isoformat()
        req = urllib.request.Request(url, headers={"User-Agent": "FearTemperatureCoverageAudit/1.0 (official original verification)"})
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                body = response.read(25_000_001)
                status, final, mime, headers = response.status, response.url, response.headers.get("Content-Type", ""), dict(response.headers)
        except urllib.error.HTTPError as error:
            body, status, final, mime, headers = error.read(), error.code, error.url, error.headers.get("Content-Type", ""), dict(error.headers)
        except Exception as error:
            body, status, final, mime, headers = repr(error).encode(), 0, url, "error/transport", {}
        okay = status == 200 and body.startswith(b"%PDF-") and len(body) <= 25_000_000
        if okay:
            path.write_bytes(body)
        else:
            (OUT / f"{key}.error.body").write_bytes(body[:4096])
        meta = {"key": key, "request_url": url, "final_url": final, "http_status": status,
                "content_type": mime, "retrieved_at_utc": stamp, "byte_count": len(body),
                "sha256": hashlib.sha256(body).hexdigest(), "local_path": str(path.relative_to(HERE)) if okay else "",
                "file_role": "primary PDF linked from official landing page", "status": "pdf_acquired" if okay else "failed_or_not_pdf"}
        meta_path.write_text(json.dumps({**meta, "response_headers": headers}, indent=2) + "\n")
        rows.append(meta)
        print(key, status, mime, len(body), meta["status"], flush=True)
        if status in (0, 403, 429) or status >= 500:
            break
    with (HERE / "au_primary_originals_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    main()
