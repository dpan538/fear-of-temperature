"""Check saved GovInfo HTML fallback bytes against the failed raw-text targets."""
import json
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from acquire import HERE, verified_meta
from us_govinfo_fallback import candidates, path_for, url_for

OUT = HERE / "reports" / "us_govinfo_fallback_audit.json"


def main():
    rows = []
    for row, old in candidates():
        path = path_for(row)
        meta = verified_meta(path)
        issues = []
        text = ""
        if not meta:
            issues.append("missing_or_hash_mismatch")
        else:
            if meta["request_url"] != url_for(row):
                issues.append("unexpected_source_url")
            pre = BeautifulSoup(path.read_bytes(), "html.parser").find_all("pre")
            if len(pre) != 1:
                issues.append("not_one_document_pre_block")
            else:
                text = pre[0].get_text()
                number = re.escape(row["document_number"])
                if not re.search(r"\[FR Doc No:\s*" + number + r"\]", text):
                    issues.append("document_number_missing_from_header")
                if not re.search(r"\[FR Doc\.\s*" + number + r"\s+Filed", text):
                    issues.append("document_number_missing_from_footer")
                if len(text) < 1000:
                    issues.append("short_text")
        failure = json.loads(old.read_text())
        if failure.get("http_status") not in (404, 410):
            issues.append("original_raw_text_exception_not_404_or_410")
        rows.append({"date": row["publication_date"], "document_number": row["document_number"],
                     "canonical_url": row["canonical_url"], "raw_html_path": meta["raw_path"] if meta else "",
                     "html_sha256": meta["sha256"] if meta else "", "source_text_characters": len(text),
                     "issues": issues})
    result = {"audited_at_utc": datetime.now(timezone.utc).isoformat(),
              "target_raw_text_404_or_410": len(rows),
              "verified_full_document_html": sum(not r["issues"] for r in rows),
              "issue_count": sum(len(r["issues"]) for r in rows), "rows": rows}
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    main()
