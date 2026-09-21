#!/usr/bin/env python3
"""Collect and verify a small, bounded GOV.UK policy-paper index.

Scope: metadata only. The script reads the public Search and Content APIs, writes
selected metadata fields, and deliberately does not persist or analyse body text.
It uses only the Python standard library so it is independent of the project NLP
environment being configured elsewhere.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE = "https://www.gov.uk"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
WINDOW_START = "2026-07-01"
WINDOW_END = "2026-07-31"
DOC_TYPE = "policy_paper"
SELECTED_ORG = "department-for-environment-food-rural-affairs"
SELECTED_ORG_TITLE = "Department for Environment, Food & Rural Affairs"
USER_AGENT = "FearOfTemperature-M1-feasibility/0.1 (research metadata audit)"

CANDIDATES = [
    ("defra", "Department for Environment, Food & Rural Affairs", SELECTED_ORG, True),
    ("desnz", "Department for Energy Security and Net Zero", "department-for-energy-security-and-net-zero", False),
    ("cabinet-office", "Cabinet Office", "cabinet-office", False),
]

SEARCH_DOCS = "https://docs.publishing.service.gov.uk/repos/search-api/using-the-search-api.html"
CONTENT_DOCS = "https://docs.publishing.service.gov.uk/repos/content-store/content-store-api.html"
TERMS_URL = "https://www.gov.uk/help/terms-conditions"
OGL_URL = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_search_url(org: str, *, count: int, start: int | None = None, order: str | None = None) -> str:
    params: list[tuple[str, str]] = [
        ("filter_organisations", org),
        ("filter_content_store_document_type", DOC_TYPE),
        ("filter_first_published_at", f"from:{WINDOW_START},to:{WINDOW_END}"),
        ("count", str(count)),
    ]
    if start is not None:
        params.append(("start", str(start)))
    if order is not None:
        params.append(("order", order))
    return f"{BASE}/api/search.json?{urllib.parse.urlencode(params)}"


def request(url: str, *, method: str = "GET", read_limit: int | None = None) -> tuple[int, str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = b"" if method == "HEAD" else response.read(read_limit)
            return response.status, response.geturl(), body
    except urllib.error.HTTPError as error:
        body = b"" if method == "HEAD" else error.read(read_limit)
        return error.code, error.geturl(), body


def fetch_json(url: str) -> tuple[dict[str, Any], int, str]:
    status, final_url, body = request(url)
    if status != 200:
        raise RuntimeError(f"HTTP {status} for {url}: {body[:300]!r}")
    return json.loads(body), status, final_url


def metadata_view(item: dict[str, Any], content_url: str, content_status: int, canonical_status: int) -> dict[str, Any]:
    orgs = [
        {"title": org.get("title"), "base_path": org.get("base_path"), "content_id": org.get("content_id")}
        for org in item.get("links", {}).get("organisations", [])
    ]
    details = item.get("details", {})
    return {
        "content_id": item.get("content_id"),
        "base_path": item.get("base_path"),
        "canonical_url": f"{BASE}{item.get('base_path', '')}",
        "content_api_url": content_url,
        "title": item.get("title"),
        "description": item.get("description"),
        "document_type": item.get("document_type"),
        "document_type_label": details.get("document_type_label"),
        "schema_name": item.get("schema_name"),
        "first_published_at": item.get("first_published_at"),
        "public_updated_at": item.get("public_updated_at"),
        "publishing_app": item.get("publishing_app"),
        "rendering_app": item.get("rendering_app"),
        "organisations": orgs,
        "content_api_http_status": content_status,
        "canonical_http_status": canonical_status,
        "body_persisted": False,
    }


def parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.max.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def write_json(path: Path, payload: Any) -> str:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(rendered, encoding="utf-8")
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    accessed_at = now_utc()

    candidate_results: list[dict[str, Any]] = []
    for candidate_id, title, slug, selected in CANDIDATES:
        url = build_search_url(slug, count=0)
        payload, status, final_url = fetch_json(url)
        candidate_results.append(
            {
                "candidate_id": candidate_id,
                "institution": title,
                "organisation_slug": slug,
                "selected": selected,
                "query_url": url,
                "final_url": final_url,
                "http_status": status,
                "total": payload.get("total"),
            }
        )

    full_url = build_search_url(SELECTED_ORG, count=50, order="public_timestamp")
    full, full_status, full_final_url = fetch_json(full_url)
    result_links = [row["link"] for row in full.get("results", [])]

    page1_url = build_search_url(SELECTED_ORG, count=5, start=0, order="public_timestamp")
    page2_url = build_search_url(SELECTED_ORG, count=5, start=5, order="public_timestamp")
    page1, page1_status, _ = fetch_json(page1_url)
    page2, page2_status, _ = fetch_json(page2_url)
    page_links = [row["link"] for row in page1.get("results", []) + page2.get("results", [])]

    content_records: list[dict[str, Any]] = []
    for link in result_links:
        content_url = f"{BASE}/api/content{link}"
        content, content_status, _ = fetch_json(content_url)
        canonical_status, _, _ = request(f"{BASE}{link}", method="HEAD")
        content_records.append(metadata_view(content, content_url, content_status, canonical_status))

    content_records.sort(key=lambda row: (parse_time(row["first_published_at"]), row["title"] or ""))

    unsupported_order_url = build_search_url(SELECTED_ORG, count=0, order="first_published_at")
    unsupported_order_status, _, _ = request(unsupported_order_url, read_limit=500)

    reference_statuses = {}
    for label, url in {
        "search_api_docs": SEARCH_DOCS,
        "content_api_docs": CONTENT_DOCS,
        "govuk_terms": TERMS_URL,
        "ogl_v3": OGL_URL,
    }.items():
        status, final_url, _ = request(url, method="HEAD")
        reference_statuses[label] = {"url": url, "http_status": status, "final_url": final_url}

    snapshot = {
        "accessed_at": accessed_at,
        "query_url": full_url,
        "http_status": full_status,
        "final_url": full_final_url,
        "total": full.get("total"),
        "start": full.get("start"),
        "results": [
            {
                "title": row.get("title"),
                "description": row.get("description"),
                "link": row.get("link"),
                "content_id": row.get("content_id"),
                "format": row.get("format"),
                "first_published_at_as_returned_by_search": row.get("first_published_at"),
                "public_timestamp": row.get("public_timestamp"),
                "organisation_titles": [org.get("title") for org in row.get("organisations", [])],
            }
            for row in full.get("results", [])
        ],
    }
    search_hash = write_json(EVIDENCE / "search_index_snapshot.json", snapshot)
    metadata_hash = write_json(
        EVIDENCE / "content_metadata_snapshot.json",
        {"accessed_at": accessed_at, "records": content_records},
    )

    sample_fields = [
        "document_id",
        "source_name",
        "source_role",
        "document_type",
        "title",
        "canonical_url",
        "published_at",
        "updated_at",
        "accessed_at",
        "language",
        "institution_region",
        "retrieval_route",
        "access_result",
        "content_status",
        "rights_status",
        "selection_rule",
        "notes",
    ]
    with (ROOT / "document_sample.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sample_fields)
        writer.writeheader()
        for row in content_records:
            org_titles = [org["title"] for org in row["organisations"]]
            notes = (
                f"schema_name={row['schema_name']}; document_type_label={row['document_type_label']}; "
                f"organisations={' | '.join(org_titles)}; Search API public_timestamp is not used as published_at"
            )
            writer.writerow(
                {
                    "document_id": row["content_id"],
                    "source_name": "GOV.UK — DEFRA policy papers",
                    "source_role": "government_policy_source",
                    "document_type": row["document_type"],
                    "title": row["title"],
                    "canonical_url": row["canonical_url"],
                    "published_at": row["first_published_at"],
                    "updated_at": row["public_updated_at"],
                    "accessed_at": accessed_at,
                    "language": "en",
                    "institution_region": "United Kingdom; policy coverage varies and several records are England-specific",
                    "retrieval_route": f"Search API enumeration: {full_url}; Content API metadata: {row['content_api_url']}",
                    "access_result": f"search={full_status}; content_api={row['content_api_http_status']}; canonical_html={row['canonical_http_status']}",
                    "content_status": "metadata_verified; body_not_persisted_or_analysed",
                    "rights_status": "Most GOV.UK content is OGL v3 except where otherwise stated; item/attachment exceptions not audited",
                    "selection_rule": "Complete enumeration of all GOV.UK policy_paper records tagged to DEFRA with first_published_at in 2026-07-01..2026-07-31 inclusive; sorted locally by verified first_published_at then title",
                    "notes": notes,
                }
            )

    register_fields = [
        "candidate_id",
        "selected",
        "source_name",
        "institution",
        "source_role",
        "document_type",
        "language",
        "region",
        "window_start",
        "window_end",
        "date_field",
        "retrieval_route",
        "authentication",
        "rate_limit",
        "official_documentation",
        "test_url",
        "http_status",
        "claimed_coverage",
        "observed_count",
        "enumeration_status",
        "pagination_rule",
        "deduplication_rule",
        "access_conditions",
        "storage_redistribution",
        "accessed_at",
        "decision",
        "notes",
    ]
    with (ROOT / "source_access_register.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=register_fields)
        writer.writeheader()
        for row in candidate_results:
            selected = row["selected"]
            writer.writerow(
                {
                    "candidate_id": row["candidate_id"],
                    "selected": str(selected).lower(),
                    "source_name": f"GOV.UK — {row['institution']} policy papers",
                    "institution": row["institution"],
                    "source_role": "government_policy_source",
                    "document_type": DOC_TYPE,
                    "language": "en",
                    "region": "United Kingdom; document-specific territorial coverage",
                    "window_start": WINDOW_START,
                    "window_end": WINDOW_END,
                    "date_field": "first_published_at (Search filter; verified per item through Content API)",
                    "retrieval_route": "Public GOV.UK Search API -> public Content API -> canonical HTML",
                    "authentication": "None observed for read-only public endpoints",
                    "rate_limit": "No numerical public quota found in reviewed API documentation; use conservative request pacing",
                    "official_documentation": f"{SEARCH_DOCS} | {CONTENT_DOCS}",
                    "test_url": row["query_url"],
                    "http_status": row["http_status"],
                    "claimed_coverage": "Search docs give no exact historical start; Content Store docs say it contains almost all published GOV.UK content",
                    "observed_count": row["total"],
                    "enumeration_status": "complete response for the bounded query" if selected else "count-only candidate check",
                    "pagination_rule": "count maximum documented as 1500; start is zero-based; selected source also tested as 5+4 records",
                    "deduplication_rule": "Content API content_id; canonical base_path as secondary key",
                    "access_conditions": "Public read access; lawful use required; GOV.UK content can change or be removed",
                    "storage_redistribution": "Most content is OGL v3 except stated exclusions; attribution required; third-party/personal-data exceptions remain",
                    "accessed_at": accessed_at,
                    "decision": "selected" if selected else "not selected for this pilot",
                    "notes": "Chosen because the fixed July window yields 9 records (within requested 5–10)" if selected else "Same portal and rules; lower July count than selected stratum",
                }
            )

    missing_by_field = {
        field: sum(1 for row in content_records if not row.get(field))
        for field in ["content_id", "title", "canonical_url", "first_published_at", "public_updated_at", "document_type"]
    }
    ids = [row["content_id"] for row in content_records]
    links = [row["canonical_url"] for row in content_records]
    in_window = [
        WINDOW_START <= parse_time(row["first_published_at"]).date().isoformat() <= WINDOW_END
        for row in content_records
    ]
    defra_tagged = [
        SELECTED_ORG_TITLE in [org["title"] for org in row["organisations"]]
        for row in content_records
    ]
    checks = {
        "run": {
            "accessed_at": accessed_at,
            "script": "scripts/collect_and_check.py",
            "python": sys.version.split()[0],
            "scope": "metadata-only feasibility pilot; no body text persisted or analysed",
        },
        "window": {"start": WINDOW_START, "end": WINDOW_END, "inclusive": True, "date_field": "first_published_at"},
        "candidate_counts": candidate_results,
        "selected_query": {
            "url": full_url,
            "http_status": full_status,
            "reported_total": full.get("total"),
            "returned_count": len(result_links),
            "content_api_records_verified": len(content_records),
        },
        "pagination_check": {
            "page_urls": [page1_url, page2_url],
            "http_statuses": [page1_status, page2_status],
            "page_counts": [len(page1.get("results", [])), len(page2.get("results", []))],
            "union_count": len(set(page_links)),
            "matches_full_result_set": set(page_links) == set(result_links),
        },
        "record_checks": {
            "duplicate_content_id_count": len(ids) - len(set(ids)),
            "duplicate_canonical_url_count": len(links) - len(set(links)),
            "missing_by_field": missing_by_field,
            "all_first_published_dates_in_window": all(in_window),
            "all_document_types_policy_paper": all(row["document_type"] == DOC_TYPE for row in content_records),
            "all_tagged_to_defra": all(defra_tagged),
            "content_api_http_statuses": sorted(set(row["content_api_http_status"] for row in content_records)),
            "canonical_html_http_statuses": sorted(set(row["canonical_http_status"] for row in content_records)),
            "co_published_or_multi_org_count": sum(1 for row in content_records if len(row["organisations"]) > 1),
        },
        "content_collection": {
            "body_persisted_count": 0,
            "paragraph_examples_count": 0,
            "reason": "This first pass persists index/content metadata only; substantive body collection awaits supervisor/ethics and item-rights confirmation.",
        },
        "api_behaviour": {
            "search_results_with_non_null_first_published_at": sum(
                1 for row in full.get("results", []) if row.get("first_published_at")
            ),
            "content_api_records_with_non_null_first_published_at": sum(
                1 for row in content_records if row.get("first_published_at")
            ),
            "unsupported_order_first_published_at_url": unsupported_order_url,
            "unsupported_order_first_published_at_http_status": unsupported_order_status,
            "interpretation": "Search API accepts first_published_at as a date filter, but this response did not expose populated values and returned HTTP 422 when the field was used for ordering. Dates and local ordering are therefore verified through Content API metadata.",
        },
        "rights_references": reference_statuses,
        "evidence_files": {
            "search_index_snapshot.json": {"sha256": search_hash},
            "content_metadata_snapshot.json": {"sha256": metadata_hash},
        },
        "denominator_status": {
            "code": 1,
            "label": "bounded complete list verified",
            "unit": "GOV.UK publication landing-page content item (document)",
            "n_total": len(content_records),
            "scope_limit": "Only GOV.UK policy_paper records tagged to DEFRA and first published during July 2026; not all DEFRA output, not all UK government policy, and not a paragraph denominator.",
        },
    }
    write_json(ROOT / "checks.json", checks)

    print(json.dumps({"accessed_at": accessed_at, "records": len(content_records), "total": full.get("total"), "checks": checks["record_checks"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
