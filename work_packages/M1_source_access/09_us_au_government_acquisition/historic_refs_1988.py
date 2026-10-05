"""Produce reviewable 1988 parent-agency index locators, not document counts.

The annual index uses agency/genre headings and printed FR start pages. OCR
tokens are candidate citations until matched to the corresponding issue.
"""
import bisect
import csv
import json
import re
from pathlib import Path

import pypdfium2 as pdfium

from historic_index import RAW, path_for

YEAR = 1988
VOLUME = 53
OUT = RAW / "1988_parent_agency_candidate_locators.csv"


def pages(doc, first, last):
    values = []
    for page_no in range(first, last + 1):
        page = doc[page_no - 1]
        textpage = page.get_textpage()
        text = textpage.get_text_range() or ""
        textpage.close(); page.close()
        values.append((page_no, text))
    return values


def candidates(values, agency, start, end):
    offsets = []
    body = ""
    for page_no, text in values:
        offsets.append((len(body), page_no))
        body += text + "\n"
    a = body.find(start)
    b = body.find(end, a + len(start))
    if a < 0 or b < 0:
        raise RuntimeError(f"{agency} heading boundary not found")
    section = body[a:b]
    rule = section.find("RULES")
    proposed = section.find("PROPOSED RULES", rule + 5)
    notices = section.find("NOTICES", proposed + 14)
    if min(rule, proposed, notices) < 0 or not rule < proposed < notices:
        raise RuntimeError(f"{agency} genre headings unresolved")
    genre_sections = [("RULE", section[rule + len("RULES"):proposed], a + rule + len("RULES")),
                      ("PRORULE", section[proposed + len("PROPOSED RULES"):notices], a + proposed + len("PROPOSED RULES"))]
    rows = []
    for genre, text, base in genre_sections:
        for match in re.finditer(r",\s*(\d{1,5})(?=\s*[,\r\n]|\s*$)", text, flags=re.M):
            number = int(match.group(1))
            if not 1 <= number <= 53376:
                continue
            global_pos = base + match.start(1)
            idx = bisect.bisect_right([x[0] for x in offsets], global_pos) - 1
            index_page = offsets[idx][1]
            context_start = max(0, text.rfind("\n", 0, match.start() - 1))
            context = re.sub(r"\s+", " ", text[context_start:match.end()]).strip()
            rows.append({"year": YEAR, "volume": VOLUME, "agency_parent_section": agency,
                         "genre_heading": genre, "fr_start_page_candidate": number,
                         "index_pdf_page": index_page, "index_context": context[:220],
                         "citation_url": f"https://www.govinfo.gov/link/fr/{VOLUME}/{number}",
                         "identity_status": "index_locator_requires_issue_document_boundary_check"})
    return rows, {"agency": agency, "index_span_pages": [values[0][0], values[-1][0]],
                  "candidate_locator_tokens": len(rows), "unique_page_numbers": len({r["fr_start_page_candidate"] for r in rows}),
                  "subagency_sections": "not_enumerated_from_parent_heading"}


def main():
    doc = pdfium.PdfDocument(str(path_for(YEAR)))
    doe, doe_status = candidates(pages(doc, 30, 32), "Energy Department", "Energy Department\r\nSee also", "Energy Information Administration")
    epa, epa_status = candidates(pages(doc, 32, 41), "Environmental Protection Agency", "Environmental Protection Agency\r\nRULES", "Farmers\r\nFamily Support Administration")
    doc.close()
    rows = doe + epa
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    status = {"year": YEAR, "parent_sections": [doe_status, epa_status],
              "index_locator_rows": len(rows), "document_count": "unknown",
              "reason": "candidate page tokens need issue date/section/independent document checks; linked subagency sections remain to enumerate"}
    OUT.with_suffix(".summary.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
