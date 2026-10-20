"""Audit public CKAN activity pages; date the catalogue, never its underlying report.

No metadata_created/modified fallback. A retained 'new package' activity must
identify this native object as public and active. Activity timestamps lack a
timezone in this deployment, so allocation is conservatively month precision.
All public activity pages are traversed through an empty page; hidden activity
is not requested. Full package/activity responses are never persisted.
"""

import json
import logging
import urllib.parse
from datetime import datetime, timedelta

import collect as core

BASE = "https://data.qld.gov.au/api/3/action/"


def public_creation(activities, native):
    candidates = []
    for activity in activities:
        package = activity.get("data", {}).get("package", {})
        if (
            activity.get("activity_type") == "new package"
            and package.get("id") == native
            and package.get("private") is False
            and package.get("state") == "active"
        ):
            raw = activity.get("timestamp", "")
            stamp = datetime.fromisoformat(raw)
            # Unknown native timezone: month must survive the full UTC-offset envelope.
            lower, upper = stamp - timedelta(hours=14), stamp + timedelta(hours=14)
            precision = 7 if lower.strftime("%Y-%m") == upper.strftime("%Y-%m") else 4
            if lower.year != upper.year:
                continue
            candidates.append(
                {"value": raw[:precision], "raw_timestamp": raw, "activity_id": activity["id"]}
            )
    return min(candidates, key=lambda x: x["raw_timestamp"]) if candidates else None


def apply_evidence(store, row, evidence, url, inspected):
    record = dict(row)
    context = json.loads(record["source_context_json"])
    context["publication_date_audit"] = {
        "checked_at": core.now(),
        "activity_endpoint": url,
        "public_activity_records_inspected": inspected,
        "page_traversal_complete": True,
        "result": evidence or "No retained public creation activity; publication stays pending",
        "date_scope": "catalogue first-publication only; not underlying report publication",
        "timezone": "native timestamp unzoned; conservative month/year allocation",
    }
    updates = {"source_context_json": core.encode(context), "retrieved_at": core.now()}
    if evidence and record["date_status"] == "pending_publication_date":
        history = json.loads(record["metadata_version_history"])
        history.append({k: v for k, v in record.items() if k != "metadata_version_history"})
        updates.update(
            core.publication(
                evidence["value"],
                "retained new-package public+active activity proves catalogue first publication; "
                "month/year precision because native activity timestamp has no timezone; "
                "underlying report date not inferred",
            )
        )
        updates["metadata_version_history"] = core.encode(history)
        updates["source_metadata_hash"] = core.digest([record["source_metadata_hash"], evidence])
    store.db.execute(
        "UPDATE source_documents SET " + ",".join(k + "=?" for k in updates) + " WHERE doc_id=?",
        [*updates.values(), record["doc_id"]],
    )
    store.db.commit()


def run(store, client):
    rows = list(
        store.db.execute("SELECT * FROM source_documents WHERE source_channel='qld_opendata'")
    )
    for row in rows:
        native = row["native_id"]
        job = "qld_publication_activity:" + native
        if (old := store.cursor(job)) and old["state"] == "exhausted":
            continue
        # Package detail is a separate public metadata check, not proof of publication.
        detail_url = BASE + "package_show?" + urllib.parse.urlencode({"id": native})
        body = client.get(detail_url)
        detail = json.loads(body)
        if detail.get("success") is not True:
            raise RuntimeError("CKAN package_show success=false")
        store.page(job, "qld_opendata", "package_show", detail_url, body, 1, 0, 0)
        offset, activities, seen = 0, [], set()
        while True:
            url = (
                BASE
                + "package_activity_list?"
                + urllib.parse.urlencode({"id": native, "limit": 100, "offset": offset})
            )
            body = client.get(url)
            payload = json.loads(body)
            if payload.get("success") is not True:
                raise RuntimeError("CKAN activity success=false")
            page = payload["result"]
            signature = core.digest([a["id"] for a in page])
            if page and signature in seen:
                raise RuntimeError("CKAN activity repeated page; not exhaustion")
            seen.add(signature)
            activities.extend(page)
            next_offset = offset + len(page) if page else None
            store.page(job, "qld_opendata", offset, url, body, len(page), 0, next_offset)
            if next_offset is None:
                break
            offset = next_offset
        evidence = public_creation(activities, native)
        apply_evidence(
            store, row, evidence, BASE + "package_activity_list?id=" + native, len(activities)
        )
        store.job(job, "qld_opendata", "exhausted", detail=core.encode(evidence))
        print(native, evidence["value"] if evidence else "pending", flush=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    run(core.Store(), core.Client())
