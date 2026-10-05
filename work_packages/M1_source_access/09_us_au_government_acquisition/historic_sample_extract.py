"""Extract independently bounded pre-1994 DOE/EPA rule audit samples."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone

import pypdfium2 as pdfium

from historic_index import RAW

SAMPLES = [
    {"date":"1988-06-09","fr_page":21646,"pdf_first":36,"pdf_last":39,
     "start":"DEPARTMENT OF ENERGY\r\nOffice of the Secretary","fr_doc":"88-13009",
     "title":"Acquisition Regulation","agency":"Department of Energy, Office of the Secretary",
     "boundary_basis":"issue page 36 DOE heading/action through page 39 FR Doc 88-13009 marker; neighboring FCC and Commerce articles excluded"},
    {"date":"1988-01-04","fr_page":20,"pdf_first":28,"pdf_last":29,
     "start":"ENVIRONMENTAL PROTECTION\r\nAGENCY\r\n21 CFR Parts 193 and 561","fr_doc":"87-29874",
     "title":"Pesticide Tolerances for Myclobutanil","agency":"Environmental Protection Agency",
     "boundary_basis":"issue page 28 EPA heading/action through page 29 FR Doc 87-29874 marker; neighboring FDA and Veterans Administration articles excluded"},
    {"date":"1988-01-05","fr_page":126,"pdf_first":26,"pdf_last":27,
     "start":"ENVIRONMENTAL PROTECTION\r\nAGENCY\r\n40 CFR Part 271","fr_doc":"88-50",
     "title":"Illinois; Immediate Final Decision on the Revision to the State Hazardous Waste Management Program",
     "title_marker":"Illinois; Immediate Final Decision","agency":"Environmental Protection Agency",
     "boundary_basis":"issue page 26 EPA heading/action through page 27 FR Doc 88-50 marker; neighboring Postal Service and subsequent EPA Florida rule excluded"},
    {"date":"1989-04-25","fr_page":17734,"pdf_first":58,"pdf_last":62,
     "start":"DEPARTMENT OF ENERGY\r\nOffice of the Secretary\r\n48 CFR Parts 951 and 952","fr_doc":"89-9909",
     "title":"Acquisition Regulations; Government Travel Discounts to Cost Reimbursement",
     "title_marker":"Travel Discounts to Cost","agency":"Department of Energy, Office of the Secretary",
     "boundary_basis":"issue page 58 DOE heading/final-rule action through page 62 FR Doc 89-9909 marker; preceding FCC and following NOAA articles excluded"},
    {"date":"1989-04-25","fr_page":17769,"pdf_first":93,"pdf_last":94,
     "start":"ENVIRONMENTAL PROTECTION\r\nAGENCY\r\n40 CFR Part 52","fr_doc":"89-9872",
     "title":"Approval and Promulgation of Implementation Plans; Indiana",
     "title_marker":"Approval and Promulgation of","agency":"Environmental Protection Agency, Region V",
     "genre":"PROPOSED_RULE","action":"Proposed rulemaking",
     "boundary_basis":"issue page 93 EPA heading/proposed-rule action through page 94 FR Doc 89-9872 marker; preceding DEA and following FCC articles excluded"},
    {"date":"1988-01-06","fr_page":392,"pdf_first":160,"pdf_last":164,
     "start":"ENVIRONMENTAL PROTECTION\r\nAGENCY\r\n40 CFR Parts 51 and 52","fr_doc":"88-177",
     "title":"Requirements for Preparation, Adoption, and Submittal of Implementation Plans",
     "title_marker":"Requirements for Preparation","agency":"Environmental Protection Agency",
     "boundary_basis":"printed 53 FR 392 begins on actual issue PDF page 160 despite the GovInfo link fragment pointing to PDF page 168; EPA final-rule heading through page 164 FR Doc 88-177 marker; subsequent article excluded"},
]


def extract(config):
    issue=RAW/"issues"/f"FR-{config['date']}.pdf"
    out=RAW/"sample_rules"/f"{config['date']}_{config['fr_doc']}"
    issue_meta=json.loads(issue.with_suffix(".request.json").read_text())
    digest=hashlib.sha256(issue.read_bytes()).hexdigest()
    if issue_meta.get("status")!="downloaded" or digest!=issue_meta.get("sha256"):
        raise RuntimeError("official issue hash does not match request evidence")
    document=pdfium.PdfDocument(str(issue))
    pieces=[]
    for page_no in range(config["pdf_first"],config["pdf_last"]+1):
        page=document[page_no-1];textpage=page.get_textpage()
        text=textpage.get_text_range() or ""
        textpage.close();page.close()
        if page_no==config["pdf_first"]:
            start=text.find(config["start"])
            if start<0:raise RuntimeError(f"{config['fr_doc']} article start absent")
            text=text[start:]
        if page_no==config["pdf_last"]:
            end=re.search(r"[\[(]FR Doc\.\s*"+re.escape(config["fr_doc"])+r" Filed",text,re.I)
            if not end:raise RuntimeError(f"{config['fr_doc']} article end absent")
            tail=text.find("\n",end.start())
            text=text[:tail if tail>0 else end.end()]
        pieces.append((page_no,text))
    document.close()
    source="\n".join(f"\fPDF_PAGE={number}\n{text}" for number,text in pieces)
    action=config.get("action","Final rule")
    if action.lower() not in source.lower() or config.get("title_marker",config["title"]) not in source or config["fr_doc"] not in source:
        raise RuntimeError("rule identity markers absent")
    cleaned=re.sub(r"\s+"," ",re.sub(r"\fPDF_PAGE=\d+"," ",source)).strip()
    out.parent.mkdir(parents=True,exist_ok=True)
    source_path=out.with_suffix(".source.txt");clean_path=out.with_suffix(".cleaned.txt")
    source_path.write_text(source);clean_path.write_text(cleaned)
    metadata={"canonical_issue_url":issue_meta["request_url"],
              "citation_url":f"https://www.govinfo.gov/link/fr/53/{config['fr_page']}",
              "issue_date":config["date"],"volume":int(config["date"][:4])-1935,"fr_start_page":config["fr_page"],
              "pdf_pages":list(range(config["pdf_first"],config["pdf_last"]+1)),
              "agency":config["agency"],"genre":config.get("genre","RULE"),"action":action,
              "title":config["title"],"fr_doc_number":config["fr_doc"],
              "source_issue_sha256":digest,"source_path":str(source_path.relative_to(RAW.parent)),
              "source_sha256":hashlib.sha256(source.encode()).hexdigest(),
              "cleaned_path":str(clean_path.relative_to(RAW.parent)),
              "cleaned_sha256":hashlib.sha256(cleaned.encode()).hexdigest(),
              "boundary_basis":config["boundary_basis"],
              "extracted_at_utc":datetime.now(timezone.utc).isoformat(),
              "status":"verified_historical_rule_sample_not_series_denominator"}
    out.with_suffix(".json").write_text(json.dumps(metadata,indent=2)+"\n")
    print(json.dumps({"fr_doc_number":config["fr_doc"],"source_chars":len(source),
                      "cleaned_chars":len(cleaned),"issue_sha256":digest}),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fr-doc",default="")
    args=parser.parse_args()
    for config in SAMPLES:
        if not args.fr_doc or config["fr_doc"]==args.fr_doc:
            extract(config)


if __name__=="__main__":main()
