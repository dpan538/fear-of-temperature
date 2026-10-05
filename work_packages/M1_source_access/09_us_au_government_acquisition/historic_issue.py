"""Checkpoint a bounded GovInfo historical Federal Register issue PDF."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from historic_index import RAW


def fetch(date):
    url=f"https://www.govinfo.gov/content/pkg/FR-{date}/pdf/FR-{date}.pdf"
    path=RAW/"issues"/f"FR-{date}.pdf"
    meta_path=path.with_suffix(".request.json")
    if path.exists() and meta_path.exists():
        meta=json.loads(meta_path.read_text())
        if meta.get("status")=="downloaded" and hashlib.sha256(path.read_bytes()).hexdigest()==meta.get("sha256"):
            print(json.dumps({"date":date,"status":"verified_existing","bytes":path.stat().st_size}));return
    path.parent.mkdir(parents=True,exist_ok=True)
    part=path.with_suffix(".part")
    digest=hashlib.sha256();size=0;status=0;final=url;mime="";error="";headers={}
    try:
        with requests.get(url,headers={"User-Agent":"FearTemperatureResearch/1.0 (official historic issue boundary audit)"},timeout=(10,60),stream=True) as response:
            status,final,mime=response.status_code,response.url,response.headers.get("Content-Type","")
            headers={k:v for k,v in response.headers.items() if k.lower() in {"date","last-modified","content-length","etag"}}
            if status==200 and "pdf" in mime.lower():
                with part.open("wb") as handle:
                    for chunk in response.iter_content(1048576):
                        size+=len(chunk)
                        if size>100_000_000: raise ValueError("issue exceeds 100MB cap")
                        digest.update(chunk);handle.write(chunk)
                if part.open("rb").read(5)!=b"%PDF-": raise ValueError("not PDF bytes")
                part.replace(path)
            else:error="unexpected_status_or_mime"
    except Exception as exc:error=f"{type(exc).__name__}: {str(exc)[:240]}"
    if part.exists():part.unlink()
    meta={"request_url":url,"final_url":final,"http_status":status,"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
          "mime_type":mime,"byte_count":size,"sha256":digest.hexdigest() if size else "",
          "raw_path":str(path.relative_to(RAW.parent)) if path.exists() and not error else "",
          "status":"downloaded" if path.exists() and not error else "failed","error":error,"response_headers":headers}
    meta_path.write_text(json.dumps(meta,indent=2)+"\n")
    print(json.dumps({"date":date,"status":meta["status"],"bytes":size,"error":error}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--date",required=True)
    args=parser.parse_args();fetch(args.date)


if __name__=="__main__":main()
