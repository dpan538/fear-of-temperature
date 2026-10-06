"""Bounded public evidence retrieval; no keys, accounts, corpus or database access."""
import datetime, hashlib, json, pathlib, sys, urllib.request
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).resolve().parents[1]
def fetch(name, url):
    receipt = {"name": name, "requested_url": url, "retrieved_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AcademicEvidenceReview/1.0"})
        with urllib.request.urlopen(req, timeout=40) as response:
            data = response.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise ValueError("20 MiB per-object bound exceeded")
            receipt.update(final_url=response.url, status=response.status, content_type=response.headers.get("Content-Type"), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        suffix = ".pdf" if data.startswith(b"%PDF") else ".json" if data.lstrip().startswith(b"{") else ".html"
        path = ROOT / "sources" / (name + suffix)
        path.write_bytes(data)
        receipt["local_file"] = str(path.relative_to(ROOT))
        if suffix == ".pdf":
            reader = PdfReader(path)
            receipt["pdf_pages"] = len(reader.pages)
            (ROOT / "sources" / (name + ".txt")).write_text("\n".join("\n[PDF page %d]\n%s" % (i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)), encoding="utf-8")
        receipt["retrieval_status"] = "saved"
    except Exception as error:
        receipt.update(retrieval_status="failed", error=str(error))
    with (ROOT / "sources" / "RETRIEVAL_RECEIPTS.jsonl").open("a", encoding="utf-8") as output:
        output.write(json.dumps(receipt, ensure_ascii=False) + "\n")
    print(json.dumps(receipt, ensure_ascii=False))

if __name__ == "__main__":
    fetch(sys.argv[1], sys.argv[2])
