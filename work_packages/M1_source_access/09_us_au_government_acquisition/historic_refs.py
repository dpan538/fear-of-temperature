"""Extract candidate DOE/EPA annual-index locators for 1988-1993.

These are page tokens under parent agency RULES/PROPOSED RULES headings,
not counts of independent Federal Register documents. Issue checks follow.
"""
import argparse
import bisect
import csv
import json
import re

import pypdfium2 as pdfium

from historic_index import RAW, path_for


def extract(year):
    doc = pdfium.PdfDocument(str(path_for(year)))
    parts, offsets, body = [], [], ""
    for pdf_page in range(25, min(55, len(doc)) + 1):
        page = doc[pdf_page-1]
        textpage = page.get_textpage()
        text = textpage.get_text_range() or ""
        textpage.close(); page.close()
        offsets.append((len(body), pdf_page))
        body += text + "\n"
    doc.close()
    markers = [
        ("Energy Department", "Energy Department\r\nSee", "Energy Information Administration\r\nNOTICES"),
        ("Environmental Protection Agency", "Environmental Protection Agency\r\nRULES", "Farm Credit Administration\r\nRULES"),
    ]
    status = []
    starts = [x[0] for x in offsets]
    for agency, opening, ending in markers:
        a = body.find(opening)
        b = body.find(ending, a + len(opening))
        if min(a,b) < 0:
            raise RuntimeError(f"{year} {agency} heading boundary not found")
        section = body[a:b]
        rule = section.find("RULES")
        proposed = section.find("PROPOSED RULES", rule + 5)
        notices = section.find("NOTICES", proposed + 14)
        if min(rule, proposed, notices) < 0 or not rule < proposed < notices:
            raise RuntimeError(f"{year} {agency} genre headings unresolved")
        begin, end = offsets[bisect.bisect_right(starts, a)-1][1], offsets[bisect.bisect_right(starts, b)-1][1]
        n_before = len(parts)
        for genre, fragment, base in [
            ("RULE", section[rule+len("RULES"):proposed], a+rule+len("RULES")),
            ("PRORULE", section[proposed+len("PROPOSED RULES"):notices], a+proposed+len("PROPOSED RULES"))]:
            for match in re.finditer(r",\s*(\d{1,5})(?=\s*[,\r\n]|\s*$)", fragment, flags=re.M):
                number = int(match.group(1))
                if not 1 <= number <= 99999:
                    continue
                pos = base + match.start(1)
                pdf_page = offsets[bisect.bisect_right(starts,pos)-1][1]
                context_start = max(0, fragment.rfind("\n", 0, match.start()-1))
                context = re.sub(r"\s+", " ", fragment[context_start:match.end()]).strip()
                parts.append({"year":year,"volume":year-1935,"agency_parent_section":agency,
                              "genre_heading":genre,"fr_start_page_candidate":number,
                              "index_pdf_page":pdf_page,"index_context":context[:220],
                              "citation_url":f"https://www.govinfo.gov/link/fr/{year-1935}/{number}",
                              "identity_status":"index_locator_requires_issue_document_boundary_check"})
        status.append({"agency":agency,"index_span_pages":[begin,end],"candidate_locator_tokens":len(parts)-n_before,
                       "unique_page_numbers":len({p["fr_start_page_candidate"] for p in parts[n_before:]}),
                       "subagency_sections":"not_enumerated_from_parent_heading"})
    out = RAW / f"{year}_parent_agency_candidate_locators.csv"
    with out.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(parts[0]));writer.writeheader();writer.writerows(parts)
    summary={"year":year,"parent_sections":status,"index_locator_rows":len(parts),
             "unique_pages":len({p["fr_start_page_candidate"] for p in parts}),"document_count":"unknown",
             "reason":"candidate page tokens require official issue-date and independent document-boundary verification; linked subagencies pending"}
    out.with_suffix(".summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--start-year",type=int,default=1988)
    parser.add_argument("--end-year",type=int,default=1993)
    args=parser.parse_args()
    for year in range(args.start_year,args.end_year+1):
        extract(year)


if __name__=="__main__":
    main()
