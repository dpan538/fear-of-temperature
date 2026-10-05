"""Reconcile every frozen DCCEEW catalogue candidate without inventing Works."""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from acquire import AU_CSV, HERE, PRE, au_rows, sid, verified_meta

OUT = HERE / "reports"
OBSERVATIONS = HERE / "browser_observations.jsonl"
WEB_OBSERVATIONS = HERE / "web_observations.jsonl"
KNOWN = {r["official_landing_url"]: r for r in csv.DictReader((PRE / "au_primary_work_evidence.csv").open())}
LEGACY = {
    "net-zero-plan": "au_net_zero_plan",
    "ncras-2021-25": "au_ncras_2021",
    "2015-ncras": "au_ncras_2015",
    "epbc-act-policy-statement-21-interaction-between-offshore-seismic-exploration-and-whales": "au_epbc_policy_2008",
}
FILE_ROOT = "https://www.dcceew.gov.au/sites/default/files/"


def landing_file(url):
    current = HERE / "raw" / "au_landing" / (sid("", url) + ".html")
    if verified_meta(current):
        return current, "new_verified"
    key = LEGACY.get(url.rstrip("/").split("/")[-1])
    if key:
        path = PRE / "evidence" / "continued_official_probes" / f"{key}.body"
        meta_path = path.with_suffix(".request.json")
        if path.exists() and meta_path.exists():
            import hashlib
            meta = json.loads(meta_path.read_text())
            if hashlib.sha256(path.read_bytes()).hexdigest() == meta.get("sha256"):
                return path, "reused_verified_08"
    return None, "none"


def parse_landing(path, url):
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    main = soup.find("main") or soup.find("article")
    if not main:
        return {"title": "", "date_candidate": "", "date_evidence": "", "file_links": [], "body_chars": 0}
    title = main.find("h1")
    title = title.get_text(" ", strip=True) if title else ""
    text = main.get_text(" ", strip=True)
    # A labelled visible date is a candidate for original-date review; CMS
    # meta tags and page timestamps never become research dates here.
    match = re.search(r"(?:Published|Publication date|Date published)\s*:?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})", text, re.I)
    links = []
    seen = set()
    for anchor in main.find_all("a", href=True):
        file_url = urljoin(url, anchor["href"])
        if not file_url.startswith(FILE_ROOT):
            continue
        extension = file_url.split("?", 1)[0].rsplit(".", 1)[-1].lower()
        if extension not in {"pdf", "docx", "rtf"} or file_url in seen:
            continue
        seen.add(file_url)
        label = anchor.get_text(" ", strip=True)
        lower = (label + " " + file_url).lower()
        role = "summary" if "summary" in lower else "end_notes" if "end-note" in lower else "background" if "background" in lower else "main_or_alternate_candidate"
        links.append({"url": file_url, "label": label, "role_candidate": role, "format": extension})
    return {"title": title, "date_candidate": match.group(1) if match else "",
            "date_evidence": "visible_labelled_landing_text_pending_original_confirmation" if match else "",
            "file_links": links, "body_chars": len(text)}


def main():
    OUT.mkdir(exist_ok=True)
    browser = {r["landing_url"]: r for r in (json.loads(line) for line in OBSERVATIONS.read_text().splitlines() if line.strip())} if OBSERVATIONS.exists() else {}
    web = {r["landing_url"]: r for r in (json.loads(line) for line in WEB_OBSERVATIONS.read_text().splitlines() if line.strip())} if WEB_OBSERVATIONS.exists() else {}
    records, files = [], []
    for row in au_rows():
        url = row["landing_url"]
        path, provenance = landing_file(url)
        known = KNOWN.get(url)
        parsed = parse_landing(path, url) if path else {"title": "", "date_candidate": "", "date_evidence": "", "file_links": [], "body_chars": 0}
        observation = browser.get(url)
        web_observation = web.get(url)
        web_success = (web_observation if web_observation and
                       web_observation.get("web_fetch_status", "observed_official_landing") == "observed_official_landing"
                       else None)
        if observation and not path:
            parsed = {"title": observation["title"], "date_candidate": "", "date_evidence": "",
                      "file_links": observation["attachments"], "body_chars": len(observation["article_text"])}
        elif web_success and not path:
            parsed = {"title": web_success["title"], "date_candidate": web_success["original_date_candidate"],
                      "date_evidence": web_success["date_evidence"],
                      "file_links": web_success["attachments"], "body_chars": len(web_success["article_text"])}
        error_meta = HERE / "raw" / "au_landing" / (sid("", url) + ".html.request.json")
        failure = json.loads(error_meta.read_text()) if error_meta.exists() and not path else {}
        if known:
            outcome = "original_pair_verified"
            reason = "08 landing and primary PDF hashes independently checked; original date precision recorded"
        elif observation and observation.get("original_date") and any(verified_meta(HERE / "raw" / "au_files" / f"{sid('', item['url'])}.{item['format']}") for item in observation["attachments"]):
            outcome = "browser_original_pair_verified_issuer_review" if observation.get("scope_status") else "browser_original_pair_verified"
            reason = observation["date_evidence"] + "; browser file SHA-256 checkpoint independently checked"
        elif observation and observation["attachments"] and all(
                verified_meta(HERE / "raw" / "au_files" / f"{sid('', item['url'])}.{item['format']}")
                for item in observation["attachments"]):
            outcome = "browser_files_verified_date_pending"
            reason = observation["date_evidence"] + "; all related file SHA-256 checkpoints independently checked"
        elif observation:
            outcome = "browser_landing_observed_file_pending"
            reason = "official landing visible in browser; original file not yet verified"
        elif web_success:
            outcome = ("official_web_pdf_identified_raw_pending" if web_success["attachments"]
                       else "official_web_landing_observed_raw_pending")
            reason = web_success["date_evidence"] + "; original raw bytes not yet acquired"
        elif web_observation:
            outcome = "official_web_read_only_open_failed_raw_pending"
            reason = web_observation.get("web_fetch_status", "web_open_error")
        elif path:
            outcome = "landing_saved_original_review_pending"
            reason = "saved landing requires issuer/date/primary-file and Work-boundary review"
        elif failure:
            outcome = "individual_request_failed"
            reason = failure.get("error", "")
        else:
            outcome = "not_yet_visited_browser_route"
            reason = "direct HTTP route timed out in bounded probes; in-app browser route works; no candidate-specific absence asserted"
        verified_date = known["original_issue_date"] if known else observation.get("original_date", "") if observation else ""
        precision = known["date_precision"] if known else observation.get("date_precision", "unknown") if observation else "unknown"
        publisher = known["original_publisher"] if known else observation.get("original_publisher", "") if observation else ""
        records.append({"landing_url": url, "catalogue_title": row["title"], "catalogue_page": row["catalogue_page"],
                        "cms_created_at_not_original_date": row["catalogue_created_at"],
                        "outcome": outcome, "reason": reason, "landing_provenance": provenance,
                        "landing_raw_path": str(path.relative_to(HERE.parent.parent.parent)) if path else "",
                        "visible_title": parsed["title"], "labelled_date_candidate_unverified": parsed["date_candidate"],
                        "labelled_date_evidence": parsed["date_evidence"],
                        "verified_original_date": verified_date,
                        "verified_date_precision": precision,
                        "verified_original_publisher": publisher,
                        "web_original_date_candidate_raw_pending": web_observation.get("original_date_candidate", "") if web_observation else "",
                        "web_observed_at_utc": web_observation.get("observed_at_utc", "") if web_observation else "",
                        "web_fetch_status": web_observation.get("web_fetch_status", "earlier_manual_observation") if web_observation else "",
                        "web_first_pdf_url": web_success["attachments"][0]["url"] if web_success and web_success["attachments"] else "",
                        "original_scope_status": observation.get("scope_status", "") if observation else "",
                        "attachment_candidates": len(parsed["file_links"]) + (web_success.get("unresolved_pdf_link_count", 0) if web_success else 0),
                        "landing_body_chars": parsed["body_chars"],
                        "primary_work_boundary": "verified_one_work_with_primary_pdf" if known or outcome.startswith("browser_original_pair_verified") else "unresolved"})
        for item in parsed["file_links"]:
            browser_verified = bool(observation and verified_meta(HERE / "raw" / "au_files" / f"{sid('', item['url'])}.{item['format']}"))
            primary_url = observation.get("primary_file_url", observation["attachments"][0]["url"]) if observation else ""
            files.append({"landing_url": url, **item,
                          "role_status": "verified_primary" if (known and item["url"] == known["primary_pdf_url"]) or (browser_verified and item["url"] == primary_url) else "verified_related_attachment" if browser_verified and item["role_candidate"] == "appendix" else "unverified_candidate"})
    with (OUT / "au_candidate_outcomes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    if files:
        with (OUT / "au_attachment_candidates.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(files[0])); writer.writeheader(); writer.writerows(files)
    from collections import Counter
    print(json.dumps({"candidates": len(records), "outcomes": dict(Counter(r["outcome"] for r in records)),
                      "file_links": len(files)}, indent=2))


if __name__ == "__main__":
    main()
