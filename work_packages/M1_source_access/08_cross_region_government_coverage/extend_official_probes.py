"""Bounded follow-up probes of official EU, AU and NZ publication routes.

No source is assigned a denominator by this script. Raw bodies and request
metadata are retained for each attempted URL; access challenges are not retried.
"""

import csv
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup


HERE = Path(__file__).resolve().parent
RAW = HERE / "evidence" / "continued_official_probes"
RAW.mkdir(parents=True, exist_ok=True)


def request(key, url, headers=None):
    stamp = datetime.now(timezone.utc).isoformat()
    req = urllib.request.Request(url, headers={"User-Agent": "FearTemperatureCoverageAudit/1.0 (official-source metadata)", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            body, status, final, mime, response_headers = response.read(), response.status, response.url, response.headers.get("Content-Type", ""), dict(response.headers)
    except urllib.error.HTTPError as error:
        body, status, final, mime, response_headers = error.read(), error.code, error.url, error.headers.get("Content-Type", ""), dict(error.headers)
    except Exception as error:
        body, status, final, mime, response_headers = repr(error).encode(), 0, url, "error/transport", {}
    (RAW / f"{key}.body").write_bytes(body)
    meta = {"request_url": url, "final_url": final, "status": status,
            "retrieved_at_utc": stamp, "content_type": mime, "sha256": hashlib.sha256(body).hexdigest(),
            "response_headers": response_headers, "body_bytes": len(body)}
    (RAW / f"{key}.request.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return body, meta


def main():
    cellar_query = """PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?work ?date ?agent ?legalType WHERE {
  ?work a cdm:act_preparatory ;
        cdm:work_date_document ?date ;
        cdm:work_created_by_agent ?agent .
  OPTIONAL { ?work cdm:resource_legal_type ?legalType . }
  FILTER (?date >= \"2022-01-01\"^^xsd:date && ?date < \"2022-02-01\"^^xsd:date)
} LIMIT 5"""
    cellar_url = "https://publications.europa.eu/webapi/rdf/sparql?" + urllib.parse.urlencode({"query": cellar_query, "format": "text/csv"})
    _, cellar_meta = request("eu_cellar_2022_01_sample", cellar_url, {"Accept": "text/csv"})
    print("CELLAR", cellar_meta["status"], cellar_meta["content_type"], cellar_meta["body_bytes"], flush=True)

    ep_url = "https://data.europarl.europa.eu/api/v2/parliamentary-questions?year=2025&limit=2"
    _, ep_meta = request("eu_ep_questions_2025_year_probe", ep_url, {"Accept": "application/ld+json"})
    print("EP", ep_meta["status"], ep_meta["content_type"], ep_meta["body_bytes"], {k:v for k,v in ep_meta["response_headers"].items() if "count" in k.lower()}, flush=True)

    nz_urls = {
        "nz_parliament_written_questions": "https://www3.parliament.nz/en/pb/order-paper-questions/written-questions/",
        "nz_natlib_mfe_1997": "https://natlib.govt.nz/records/21776420",
        "nz_natlib_mfe_2024": "https://natlib.govt.nz/records/56996467",
    }
    for key, url in nz_urls.items():
        _, meta = request(key, url)
        print(key, meta["status"], meta["content_type"], meta["body_bytes"], flush=True)

    au_urls = {
        "au_net_zero_plan": "https://www.dcceew.gov.au/climate-change/publications/net-zero-plan",
        "au_emissions_reduction_plan": "https://www.dcceew.gov.au/about/reporting/emissions-reduction-plan",
        "au_ncras_2021": "https://www.dcceew.gov.au/climate-change/policy/adaptation/strategy/ncras-2021-25",
        "au_ncras_2015": "https://www.dcceew.gov.au/climate-change/policy/adaptation/publications/2015-ncras",
        "au_epbc_policy_2008": "https://www.dcceew.gov.au/environment/epbc/publications/epbc-act-policy-statement-21-interaction-between-offshore-seismic-exploration-and-whales",
    }
    fields = ["key", "request_url", "http_status", "html_title", "heading", "date_text_candidates", "date_time_attrs", "pdf_href_count", "pdf_hrefs", "boundary_note"]
    rows = []
    for key, url in au_urls.items():
        body, meta = request(key, url)
        if meta["status"] != 200 or "html" not in meta["content_type"].lower():
            rows.append(dict(key=key, request_url=url, http_status=meta["status"], boundary_note="not parsed; access failure"))
            print(key, meta["status"], "not parsed", flush=True)
            continue
        soup = BeautifulSoup(body, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        heading = soup.select_one("h1")
        times = soup.select("time[datetime]")
        date_text = [x.get_text(" ", strip=True) for x in soup.select(".field--name-field-date, .field--name-created, .date-display-single")]
        pdfs = sorted({urllib.parse.urljoin(meta["final_url"], a.get("href", "")) for a in soup.select("a[href]") if ".pdf" in a.get("href", "").lower()})
        rows.append(dict(key=key, request_url=url, http_status=meta["status"], html_title=title,
                         heading=heading.get_text(" ", strip=True) if heading else "",
                         date_text_candidates=";".join(date_text),
                         date_time_attrs=";".join(x.get("datetime", "") for x in times),
                         pdf_href_count=len(pdfs), pdf_hrefs=";".join(pdfs),
                         boundary_note="landing page; original date/edition require file inspection"))
        print(key, meta["status"], len(pdfs), flush=True)
    with (HERE / "au_policy_landing_probe.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    main()
