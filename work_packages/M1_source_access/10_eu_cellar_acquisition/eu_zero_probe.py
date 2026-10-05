"""Bounded official CELLAR diagnostic for one 2024-08 CELEX document."""
import hashlib
import json

import requests

from eu_acquire import ENDPOINT, HEADERS, HERE, stamp

CELEX = "52024PC0999"
QUERY = """PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?work ?date ?creator ?type WHERE {
  ?work cdm:resource_legal_id_celex ?celex .
  FILTER (STR(?celex) = "52024PC0999")
  OPTIONAL { ?work cdm:work_date_document ?date . }
  OPTIONAL { ?work cdm:work_created_by_agent ?creator . }
  OPTIONAL { ?work a ?type . }
} LIMIT 100"""


def main():
    out = HERE / "raw" / "diagnostics" / f"{CELEX}_cellar_work.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = out.with_suffix(".request.json")
    if out.exists() and checkpoint.exists():
        prior = json.loads(checkpoint.read_text())
        if (prior.get("status") == "downloaded" and prior.get("byte_count") == out.stat().st_size
                and prior.get("sha256") == hashlib.sha256(out.read_bytes()).hexdigest()):
            print(json.dumps({"status": "already_verified", "http_status": prior["http_status"],
                              "bytes": out.stat().st_size}))
            return
    response = requests.get(ENDPOINT, params={"query": QUERY, "format": "text/csv"},
                            headers=HEADERS, timeout=60)
    body = response.content
    valid = (response.status_code == 200 and "csv" in response.headers.get("Content-Type", "").lower()
             and len(body) <= 1_000_000)
    meta = {"request_url": response.url, "final_url": response.url,
            "http_status": response.status_code, "retrieved_at_utc": stamp(),
            "mime_type": response.headers.get("Content-Type", ""), "byte_count": len(body),
            "sha256": hashlib.sha256(body).hexdigest(), "status": "downloaded" if valid else "failed",
            "raw_path": str(out.relative_to(HERE)) if valid else "",
            "error": "" if valid else "unexpected_status_mime_or_size"}
    if valid:
        out.write_bytes(body)
    elif body:
        out.with_suffix(".error.body").write_bytes(body[:8192])
    checkpoint.write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"status": meta["status"], "http_status": meta["http_status"],
                      "bytes": len(body), "rows": body.decode("utf-8-sig", errors="replace")[:4000] if valid else ""}))


if __name__ == "__main__":
    main()
