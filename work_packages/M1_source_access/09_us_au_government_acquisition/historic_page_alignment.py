"""Check GovInfo PDF jump fragments against printed pages in saved issues."""
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone

import pypdfium2 as pdfium

from historic_index import RAW

OUT = RAW / "saved_issue_page_alignment.csv"
SUMMARY = RAW / "saved_issue_page_alignment.summary.json"


def main():
    entries = []
    for year in range(1988, 1994):
        with (RAW / f"{year}_parent_agency_resolved_locators.csv").open(newline="", encoding="utf-8") as handle:
            entries.extend(csv.DictReader(handle))
    by_date = {}
    for row in entries:
        by_date.setdefault(row["issue_date_from_official_link"], []).append(row)
    output = []
    for issue in sorted((RAW / "issues").glob("FR-*.pdf")):
        day = issue.stem[3:]
        document = pdfium.PdfDocument(str(issue))
        headers = []
        for i in range(len(document)):
            page = document[i]
            text = page.get_textpage()
            lines = (text.get_text_range() or "").splitlines()
            headers.append(lines[0][:200] if lines else "")
            text.close()
            page.close()
        document.close()
        for row in by_date.get(day, []):
            printed = int(row["fr_start_page_candidate"])
            fragment = int(row["issue_pdf_page"]) if row["issue_pdf_page"] else 0
            # Printed page numbers sit at an edge of the running header. A
            # number elsewhere in the OCR text is not page-header evidence.
            matches = []
            for i, header in enumerate(headers):
                compact = re.sub(r"\s+", "", header)
                if "federal" not in compact.lower():
                    continue
                if (re.search(r"^" + str(printed) + r"(?!\d)", compact)
                        or re.search(r"(?<!\d)" + str(printed) + r"$", compact)):
                    matches.append(i + 1)
            ranked = sorted(matches, key=lambda p: abs(p-fragment))
            if not matches:
                actual, status = "", "printed_page_not_found_in_header"
            elif fragment in matches:
                actual, status = fragment, "fragment_matches_printed_page"
            elif len(ranked) > 1 and abs(ranked[0]-fragment) == abs(ranked[1]-fragment):
                actual, status = "", "multiple_equidistant_header_matches"
            else:
                actual, status = ranked[0], "corrected_from_printed_page_header"
            output.append({"issue_date": day, "volume": row["volume"],
                           "agency_parent_section": row["agency_parent_section"],
                           "genre_heading": row["genre_heading"],
                           "fr_page_candidate": printed,
                           "link_pdf_fragment_page": fragment,
                           "actual_pdf_page_from_printed_header": actual,
                           "header_match_pdf_pages": ";".join(map(str, matches)),
                           "alignment_status": status,
                           "article_boundary_status": "not_verified_by_page_alignment",
                           "actual_page_header_excerpt": headers[actual-1][:160].replace("\r", " ").replace("\n", " ") if actual else ""})
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    summary = {"audited_at_utc": datetime.now(timezone.utc).isoformat(),
               "saved_issue_pdfs": len(list((RAW / "issues").glob("FR-*.pdf"))),
               "candidate_locator_rows_in_saved_issues": len(output),
               "alignment_status_counts": dict(Counter(r["alignment_status"] for r in output)),
               "meaning": "Printed-page header alignment only; agency, genre and article boundaries still require issue-level validation."}
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
