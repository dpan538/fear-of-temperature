"""Additional documented public routes. Source text exists only in transient memory."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime
from datetime import time as day_time
from zoneinfo import ZoneInfo

# Set by collect.py after loading its core definitions; avoids a duplicate importer.
core = None

LOG = logging.getLogger("official_voice")


class RangeFile(io.RawIOBase):
    """Seekable memory-only HTTP byte-range reader; refuses an ignored Range header."""

    def __init__(self, url, size):
        super().__init__()
        self.url, self.size, self.position = url, size, 0
        self.cache_start, self.cache = 0, b""

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = (
            offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        )
        return self.position

    def fetch(self, start, end):
        request = urllib.request.Request(
            self.url,
            headers={"Range": f"bytes={start}-{end}", "User-Agent": "FearTemperatureResearch/1.0"},
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    expected = f"bytes {start}-{end}/{self.size}"
                    if response.status != 206 or response.headers.get("Content-Range") != expected:
                        raise RuntimeError(
                            f"range contract failed: {response.status}, "
                            f"{response.headers.get('Content-Range')}"
                        )
                    body = response.read(end - start + 2)
                    if len(body) != end - start + 1:
                        raise RuntimeError("short or oversized byte range")
                    return body
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)

    def prefetch(self, start, end):
        self.cache_start, self.cache = start, self.fetch(start, end)
        return self.cache

    def read(self, size=-1):
        if size < 0:
            size = self.size - self.position
        size = min(size, self.size - self.position)
        if size <= 0:
            return b""
        start = self.position
        self.position += size
        if self.cache_start <= start and start + size <= self.cache_start + len(self.cache):
            return self.cache[start - self.cache_start : start - self.cache_start + size]
        return self.fetch(start, start + size - 1)


def verified_table(client, file):
    import pyarrow.parquet as pq

    body = client.get(file["links"]["self"], max_bytes=file["size"] + 1)
    if len(body) != file["size"]:
        raise RuntimeError("table size differs from deposit manifest")
    algorithm, expected = file["checksum"].split(":", 1)
    if hashlib.new(algorithm, body).hexdigest() != expected:
        raise RuntimeError("table checksum differs from deposit manifest")
    return pq.read_table(io.BytesIO(body)).to_pylist()


def collect_rapid(store, client):
    import pyarrow as pa
    import pyarrow.parquet as pq

    source, deposit = "hansard_federal_rapid", "22868754"
    job = "rapid:" + deposit + ":all_row_groups:extended33"
    previous = store.cursor(job)
    if previous and previous["state"] == "exhausted":
        return
    info = json.loads(client.get("https://zenodo.org/api/records/" + deposit))
    files = {item["key"]: item for item in info["files"]}
    sessions = {r["session_id"]: r for r in verified_table(client, files["session.parquet"])}
    speakers = {
        r["speaker_detail_id"]: r for r in verified_table(client, files["speaker_detail.parquet"])
    }
    debates = {r["debate_id"]: r for r in verified_table(client, files["debate_title.parquet"])}
    file = files["paragraph.parquet"]
    reader = RangeFile(file["links"]["self"], file["size"])
    parquet = pq.ParquetFile(pa.PythonFile(reader, mode="r"))
    cursor = json.loads(previous["cursor"]) if previous else 0
    for group in range(cursor or 0, parquet.num_row_groups):
        metadata = parquet.metadata.row_group(group)
        starts, ends = [], []
        for column in range(metadata.num_columns):
            item = metadata.column(column)
            start = min(
                x
                for x in [item.dictionary_page_offset, item.data_page_offset]
                if x is not None and x >= 0
            )
            starts.append(start)
            ends.append(start + item.total_compressed_size - 1)
        core.capacity(store.output, max(ends) - min(starts) + 1)
        body = reader.prefetch(min(starts), max(ends))
        rows = parquet.read_row_group(group).to_pylist()
        units = {}
        for row in rows:
            session = sessions.get(row["session_id"])
            if session is None:
                raise RuntimeError("paragraph has no session foreign-key target")
            date_value = session["date"].isoformat()
            if not core.START <= date_value <= core.END:
                continue
            text = row.get("text") or ""
            hits = core.matches(text)
            title = (debates.get(row.get("debate_id")) or {}).get("title") or ""
            if not hits and not core.matches(title):
                continue
            # Session-qualified procedural units, NOT arbitrary paragraphs or presumed speeches.
            number = row.get("procedural_unit_number")
            native = (
                f"zenodo:{deposit}:session:{row['session_id']}:unit:{number}:"
                f"type:{row.get('procedural_unit_type')}"
            )
            if number is None:
                native = f"zenodo:{deposit}:unresolved-unit:paragraph:{row['para_id']}"
            entry = units.setdefault(
                native,
                {
                    "row": row,
                    "session": session,
                    "date": date_value,
                    "title": title,
                    "text": text,
                    "terms": set(),
                    "para_ids": [],
                    "speakers": set(),
                },
            )
            entry["terms"].update(h[1] for h in hits + core.matches(title))
            entry["para_ids"].append(row["para_id"])
            speaker = speakers.get(row.get("speaker_detail_id")) or {}
            name = " ".join(
                str(speaker.get(k) or "") for k in ["given_name", "family_name"]
            ).strip()
            if name:
                entry["speakers"].add(name)
        saved = 0
        for native, entry in units.items():
            row = entry["row"]
            existing = store.db.execute(
                "SELECT * FROM source_documents WHERE source_channel=? AND native_id=?",
                (source, native),
            ).fetchone()
            extra = {
                "deposit_doi": "10.5281/zenodo." + deposit,
                "session_id": row["session_id"],
                "procedural_unit_number": row.get("procedural_unit_number"),
                "procedural_unit_type": row.get("procedural_unit_type"),
                "matched_para_ids": entry["para_ids"],
                "speaker_names": sorted(entry["speakers"]),
                "grouping": "session-qualified native procedural unit; "
                "not a validated independent speech",
                "original_url": entry["session"]["url"],
                "full_file_checksum_verified": False,
                "published_file_checksum": file["checksum"],
            }
            terms = entry["terms"]
            text = entry["text"]
            if existing:
                context = json.loads(existing["source_context_json"])
                extra["matched_para_ids"] = sorted(
                    set(context.get("matched_para_ids", [])) | set(extra["matched_para_ids"])
                )
                extra["speaker_names"] = sorted(
                    set(context.get("speaker_names", [])) | set(extra["speaker_names"])
                )
                terms.update(json.loads(existing["query_matched"]))
                # Retain one bounded excerpt across row-group boundaries.
                text = existing["excerpt_text"] or text
            saved += store.save(
                source,
                native,
                entry["title"],
                text,
                entry["date"],
                entry["session"]["url"],
                tier="federal",
                unit="parliamentary_procedural_unit"
                if row.get("procedural_unit_number") is not None
                else "parliamentary_paragraph_unit_unresolved",
                version="zenodo:22868754;2026-09-21",
                parent=str(row["session_id"]),
                speaker="; ".join(extra["speaker_names"]) or None,
                role="parliamentary_holder_unresolved",
                role_evidence="official parliamentary record; deposit has no dated "
                "executive/government-office classification",
                basis="nominal sitting start date; may extend after midnight; "
                "original publication time not separately verified",
                excerpt_kind="parliamentary_text_excerpt",
                provider_terms=sorted(terms),
                extra=extra,
            )
            store.db.execute(
                "UPDATE source_documents SET excerpt_locator=?,research_use_status=? "
                "WHERE doc_id=?",
                (
                    f"zenodo:{deposit}/paragraph.parquet; para_ids={extra['matched_para_ids']}; "
                    f"session={row['session_id']}; first matching paragraph excerpt",
                    "CC-BY-NC-ND-4.0; source terms retained; "
                    "redistribution of derivatives not inferred",
                    core.digest([source, native]),
                ),
            )
        next_group = group + 1 if group + 1 < parquet.num_row_groups else None
        store.page(
            job,
            source,
            group,
            reader.url + f"#row_group={group}",
            body,
            len(rows),
            saved,
            next_group,
        )
        store.job(
            job,
            source,
            "running" if next_group is not None else "exhausted",
            next_group,
            f"row_groups={parquet.num_row_groups}; "
            f"source paragraphs={parquet.metadata.num_rows}; "
            "all groups required; no complete body saved",
        )
    reader.close()


def collect_csiro(store, client):
    source = "csiro_dap"
    for terms in core.COLLECTION_MATRIX["dimensions"].values():
        for term in terms:
            job = "csiro_dap:publication_window_v1:" + term
            previous = store.cursor(job)
            if previous and previous["state"] == "exhausted":
                continue
            cursor = json.loads(previous["cursor"]) if previous else None
            zone = ZoneInfo("Australia/Sydney")
            lower = datetime.combine(
                datetime.fromisoformat(core.START).date(), day_time.min, zone
            ).isoformat()
            upper = datetime.combine(
                datetime.fromisoformat(core.END).date(), day_time.max, zone
            ).isoformat()
            url = (
                cursor
                or "https://data.csiro.au/dap/ws/v2/collections.json?"
                + urllib.parse.urlencode(
                    {"q": '"' + term + '"', "p": 1, "rpp": 100, "psd": lower, "ped": upper}
                )
            )
            seen = set()
            while url:
                if url in seen or urllib.parse.urlparse(url).hostname != "data.csiro.au":
                    raise RuntimeError("repeated or off-host CSIRO next link")
                seen.add(url)
                body = client.get(url, {"Accept": "application/json"})
                payload = json.loads(body)
                if "dataCollections" not in payload:
                    raise RuntimeError("unexpected CSIRO response schema")
                rows = payload["dataCollections"]
                next_url = (payload.get("next") or {}).get("href")
                if payload.get("query") != '"' + term + '"':
                    raise RuntimeError("CSIRO response did not retain submitted query")
                if next_url and not rows:
                    raise RuntimeError("CSIRO empty page with continuation")
                saved = 0
                for row in rows:
                    native = row["id"]["identifier"]
                    saved += store.save(
                        source,
                        native,
                        row.get("title"),
                        row.get("description", ""),
                        row.get("published"),
                        row["landingPage"]["href"],
                        tier="agency_csiro",
                        unit="dataset_catalogue_metadata",
                        version=str(row.get("dataVersionNumber")),
                        speaker=row.get("leadResearcher"),
                        role="research_data_publication_not_institutional_position_verified",
                        provider_terms=[term],
                        basis="DAP collection publication timestamp, "
                        "not underlying observation years",
                        excerpt_kind="collection_description",
                        persistent_id=row.get("doi"),
                        extra={
                            "collection_type": row.get("collectionType"),
                            "licence": row.get("licence"),
                            "rights": row.get("rights"),
                            "contributors": row.get("contributors"),
                        },
                    )
                store.page(
                    job, source, payload.get("page", url), url, body, len(rows), saved, next_url
                )
                store.job(
                    job,
                    source,
                    "running" if next_url else "exhausted",
                    next_url,
                    f"advertised_total={payload.get('totalResults')}; "
                    f"server_complete={payload.get('complete')}; all next links required",
                )
                if not next_url and str(payload.get("totalResults", "")).endswith("+"):
                    raise RuntimeError("CSIRO capped total with no continuation: not exhaustive")
                url = next_url


def collect_trove(store, client):
    # No account/key creation, terms acceptance, or private interface fallback.
    if not os.environ.get("TROVE_API_KEY"):
        store.job(
            "trove:credential",
            "trove",
            "pending_credentials",
            detail="Live public request returned HTTP401; "
            "user instructed missing-credential sources stay pending",
        )
        return "pending_credentials"
    raise RuntimeError(
        "Trove key present, but versioned category/publisher and response contract "
        "must be confirmed before harvesting; "
        "no unverified all-Trove-to-official relabelling"
    )


COLLECTORS = {
    "hansard_federal_rapid": collect_rapid,
    "csiro_dap": collect_csiro,
    "trove": collect_trove,
}
