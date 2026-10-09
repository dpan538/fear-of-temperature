"""Auxiliary parent-source statistics from metadata events; never collector feedback.

The monitor owns only its diagnostic files. It does not read corpus databases,
change source policy, call a scheduler or send network requests. A future writer
can expose committed metadata events without waiting for this monitor to succeed.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import time
import uuid
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path

from .core import END, START, Unit, eligible_day

DIMENSIONS = (
    "acquisition_family",
    "publisher_organization",
    "platform_network",
    "software_family",
    "instance",
    "community",
)


class ParentMonitor:
    """Revision-aware materialized diagnostic view over an append-only event log.

    Metadata entities and mappings can be corrected without changing the original
    journal. Lower revisions are stale; identical replays are idempotent. Revision
    numbers are monotonic per monitor object, not inferred from publication time.
    """

    def __init__(self):
        self.sources: dict[str, dict] = {}
        self.units: dict[tuple[str, str], Unit] = {}
        self.assertions: dict[tuple[str, str], list[dict]] = {}
        self.revisions: dict[tuple, tuple[int, str]] = {}
        self.by_source: dict[str, set[tuple]] = defaultdict(set)
        self.applied_events = 0
        self.last_totals = {}
        self.last_diagnostics = {}

    def apply(self, event: dict) -> bool:
        kind = event["kind"]
        revision = event["revision"]
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ValueError("A positive per-object revision is required")
        if kind == "source":
            payload = event["source"]
            source = payload["source_id"]
            if payload["stream"] not in {"newspaper", "social", "campus_publication"}:
                raise ValueError("Unknown stream")
            key = (kind, source)
            if source in self.sources and self.sources[source]["stream"] != payload["stream"]:
                raise ValueError("An established source cannot silently change streams")
        elif kind == "entity":
            payload = Unit(**event["unit"])
            source = payload.source
            key = (kind, payload.stream, payload.entity_id)
        elif kind == "parent_assertions":
            source = event["source_id"]
            dimension = event["dimension"]
            if dimension not in DIMENSIONS:
                raise ValueError("Unknown parent dimension")
            payload = event["assertions"]
            if not isinstance(payload, list):
                raise ValueError("Assertions must be a full replacement list")
            for row in payload:
                if row["status"] not in {"confirmed", "recorded", "candidate", "unresolved"}:
                    raise ValueError("Unknown parent assertion status")
                if row["status"] in {"confirmed", "recorded"} and not (
                    row.get("parent_id") and row.get("evidence_ref")
                ):
                    raise ValueError("A mapped parent needs a stable ID and evidence")
                for field in ("valid_from", "valid_to"):
                    if row.get(field):
                        date.fromisoformat(row[field])
                if (
                    row.get("valid_from")
                    and row.get("valid_to")
                    and row["valid_from"] > row["valid_to"]
                ):
                    raise ValueError("Parent validity interval is reversed")
            key = (kind, source, dimension)
        else:
            raise ValueError("Unknown metadata event kind")
        if kind != "source" and source not in self.sources:
            raise ValueError("Source registration must precede dependent events")
        if kind == "entity" and payload.stream != self.sources[source]["stream"]:
            raise ValueError("Entity/source stream mismatch")
        digest = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
        previous = self.revisions.get(key)
        if previous and revision <= previous[0]:
            if revision == previous[0] and digest != previous[1]:
                raise ValueError("Conflicting payload at the same revision")
            return False
        if kind == "source":
            self.sources[source] = dict(payload)
        elif kind == "parent_assertions":
            self.assertions[(source, dimension)] = [dict(row) for row in payload]
        else:
            entity_key = (payload.stream, payload.entity_id)
            old = self.units.get(entity_key)
            if old:
                self.by_source[old.source].discard(entity_key)
            self.units[entity_key] = payload
            self.by_source[source].add(entity_key)
        self.revisions[key] = (revision, digest)
        self.applied_events += 1
        return True

    def parents_for(self, unit: Unit, dimension: str) -> set[str]:
        parents = set()
        day = eligible_day(unit.publication_day) if unit.date_usable else None
        for row in self.assertions.get((unit.source, dimension), []):
            if row["status"] not in {"confirmed", "recorded"}:
                continue
            # Missing validity dates mean snapshot classification, not an assertion
            # that the same historical owner existed throughout the study period.
            if row.get("valid_from") or row.get("valid_to"):
                if not day:
                    continue
                if row.get("valid_from") and day < row["valid_from"]:
                    continue
                if row.get("valid_to") and day > row["valid_to"]:
                    continue
            parents.add(row["parent_id"])
        return parents

    def snapshot(self) -> dict:
        """Aggregate in-memory metadata only, once per dirty micro-batch.

        Parent memberships overlap: totals are unique within each parent but are
        not additive across parents/dimensions. Unmapped is a bucket, not a parent.
        """
        cells = defaultdict(
            lambda: {
                "entities": set(),
                "bodies": set(),
                "dated": set(),
                "works": set(),
                "sources": set(),
            }
        )
        diagnostics = []
        assertions = []
        for (source, dimension), values in sorted(self.assertions.items()):
            assertions.extend({"source_id": source, "dimension": dimension, **r} for r in values)
        for stream in sorted({s["stream"] for s in self.sources.values()}):
            units = [u for u in self.units.values() if u.stream == stream]
            body_total = sum(u.countable_body for u in units)
            dated_total = sum(
                u.countable_body and u.date_usable and bool(eligible_day(u.publication_day))
                for u in units
            )
            for dimension in DIMENSIONS:
                unknown = unknown_bodies = multiple = 0
                registered = {
                    r["parent_id"]
                    for (source, dim), values in self.assertions.items()
                    if dim == dimension and self.sources[source]["stream"] == stream
                    for r in values
                    if r["status"] in {"recorded", "confirmed"}
                }
                observed, body_parents = set(), set()
                for u in units:
                    parents = self.parents_for(u, dimension)
                    unknown += not parents
                    unknown_bodies += not parents and u.countable_body
                    multiple += len(parents) > 1
                    observed.update(parents)
                    if u.countable_body:
                        body_parents.update(parents)
                    day = eligible_day(u.publication_day) if u.date_usable else None
                    month = day[:7] if day else "UNRESOLVED_OR_OUTSIDE_INTERVAL"
                    for parent in parents or {"UNMAPPED"}:
                        for period in ("ALL", month):
                            c = cells[(stream, dimension, parent, period)]
                            c["entities"].add(u.entity_id)
                            c["sources"].add(u.source)
                            if u.countable_body:
                                c["bodies"].add(u.entity_id)
                                if day:
                                    c["dated"].add(u.entity_id)
                                    if u.publication_key:
                                        c["works"].add(u.publication_key)
                largest = max(
                    (len(cells[(stream, dimension, p, "ALL")]["dated"]) for p in observed),
                    default=0,
                )
                diagnostics.append(
                    {
                        "stream": stream,
                        "dimension": dimension,
                        "registered_parent_count": len(registered),
                        "observed_parent_count": len(observed),
                        "parents_with_readable_bodies": len(body_parents),
                        "retained_entities": len(units),
                        "readable_body_entities": body_total,
                        "dated_readable_body_entities": dated_total,
                        "unmapped_entities": unknown,
                        "unmapped_body_entities": unknown_bodies,
                        "unmapped_body_share": unknown_bodies / body_total if body_total else None,
                        "multi_parent_entities": multiple,
                        "largest_parent_dated_body_share": largest / dated_total
                        if dated_total and observed
                        else None,
                        "collection_effect": "none; auxiliary_only",
                    }
                )
        rows = [
            {
                "stream": stream,
                "dimension": dimension,
                "parent_id": parent,
                "publication_month": month,
                "retained_entities": len(c["entities"]),
                "readable_body_entities": len(c["bodies"]),
                "dated_readable_body_entities": len(c["dated"]),
                "known_publication_keys": len(c["works"]),
                "contributing_sources": sorted(c["sources"]),
            }
            for (stream, dimension, parent, month), c in sorted(cells.items())
        ]
        return {
            "schema_version": "parent-source-monitor-1",
            "snapshot_at": datetime.now(UTC).isoformat(),
            "publication_interval": [START.isoformat(), END.isoformat()],
            "applied_events": self.applied_events,
            "retained_metadata_entities": len(self.units),
            "source_registry_entries": len(self.sources),
            "dimension_summary": diagnostics,
            "parent_counts": rows,
            "mapping_assertions": assertions,
            "scope": "current accepted metadata states and as-of mapping assertions",
            "limitations": [
                "parent dimensions are distinct relations, not independent publishers",
                "unbounded mappings are snapshot classifications, not proven historical ownership",
                "memberships can overlap; do not sum across parents or dimensions",
                "no target diversity score, sampling weight or collection feedback",
            ],
        }


def bootstrap_parent_monitor(registry: dict, units: list[Unit]) -> ParentMonitor:
    monitor = ParentMonitor()
    for source, row in sorted(registry.items()):
        monitor.apply({"kind": "source", "revision": 1, "source": row})
        mappings = {}
        if row.get("acquisition_parent"):
            mappings["acquisition_family"] = row["acquisition_parent"]
        platform = row.get("platform_family", "")
        if row["stream"] == "social":
            if platform in {"Stack Exchange", "Bluesky", "Reddit", "Meta", "YouTube"}:
                mappings["platform_network"] = platform
            if platform in {"Discourse", "Mastodon", "Lemmy"}:
                mappings["software_family"] = platform
            if platform in {"Mastodon", "Lemmy"}:
                mappings["instance"] = row["base_url"]
            elif platform in {"Stack Exchange", "Discourse", "forum_software_unverified"}:
                mappings["community"] = row["base_url"]
        for dimension, parent in mappings.items():
            monitor.apply(
                {
                    "kind": "parent_assertions",
                    "revision": 1,
                    "source_id": source,
                    "dimension": dimension,
                    "assertions": [
                        {
                            "parent_id": dimension + ":" + parent,
                            "status": "recorded",
                            "evidence_ref": row.get("parent_evidence", "")
                            if dimension == "acquisition_family"
                            else "source_registry_final.json:platform/base_url",
                            "validity_basis": "snapshot_only; historical_ownership_unverified",
                        }
                    ],
                }
            )
    for unit in units:
        monitor.apply({"kind": "entity", "revision": 1, "unit": asdict(unit)})
    return monitor


def publish_snapshot(
    output: Path,
    monitor: ParentMonitor,
    rejected: int,
    max_output_bytes: int = 64 * 1024**2,
    feed: dict | None = None,
) -> Path:
    """Refresh a disposable view, preserving compact change history and input.

    The append-only input is authoritative. The live JSON may be atomically
    replaced; closed snapshots elsewhere are immutable. This avoids one full
    snapshot every few seconds exhausting acquisition storage.
    """
    output.mkdir(parents=True, exist_ok=True)
    snapshot = monitor.snapshot()
    snapshot["rejected_metadata_events"] = rejected
    snapshot["feed"] = feed or {}
    snapshot["report_id"] = uuid.uuid4().hex
    totals = {
        "|".join((r["stream"], r["dimension"], r["parent_id"])): r
        for r in snapshot["parent_counts"]
        if r["publication_month"] == "ALL"
    }
    diagnostics = {
        "|".join((r["stream"], r["dimension"])): r for r in snapshot["dimension_summary"]
    }
    delta = {
        "report_id": snapshot["report_id"],
        "snapshot_at": snapshot["snapshot_at"],
        "applied_events": monitor.applied_events,
        "rejected_events": rejected,
        "parent_totals_changed": {
            k: v for k, v in totals.items() if monitor.last_totals.get(k) != v
        },
        "parent_keys_no_longer_in_current_view": sorted(set(monitor.last_totals) - set(totals)),
        "diagnostics_changed": {
            k: v for k, v in diagnostics.items() if monitor.last_diagnostics.get(k) != v
        },
    }
    data = (json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n").encode()
    change = (json.dumps(delta, ensure_ascii=False) + "\n").encode()
    used = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
    if used + len(data) + len(change) > max_output_bytes:
        raise RuntimeError(
            "Diagnostic output capacity reached; stop monitor only, never collection"
        )
    history = output / "history.jsonl"
    with history.open("ab") as stream:
        stream.write(change)
        stream.flush()
        os.fsync(stream.fileno())
    temporary = output / (".latest-" + uuid.uuid4().hex)
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    target = output / "latest.json"
    os.replace(temporary, target)
    monitor.last_totals, monitor.last_diagnostics = totals, diagnostics
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--follow", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=5)
    parser.add_argument("--duration-seconds", type=float, default=0)
    parser.add_argument("--max-output-bytes", type=int, default=64 * 1024**2)
    args = parser.parse_args()
    if args.poll_seconds < 0.2 or args.poll_seconds > 60 or args.duration_seconds < 0:
        parser.error("Poll must be 0.2..60 seconds; duration must be nonnegative")
    if args.max_output_bytes <= 0:
        parser.error("Output capacity must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    marker = args.output / ".parent-monitor"
    if any(args.output.iterdir()) and not marker.exists():
        parser.error("Output must be empty or an existing parent-monitor directory")
    marker.touch(exist_ok=True)
    # This lock belongs only to diagnostics, never to either collector/store.
    lock = (args.output / ".monitor.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    monitor, rejected = ParentMonitor(), 0
    started, offset, published = time.monotonic(), 0, False
    identity = None
    while True:
        current = args.events.stat()
        if identity is not None and (
            identity != (current.st_dev, current.st_ino) or current.st_size < offset
        ):
            raise RuntimeError("Event file replaced/truncated; use a declared new feed and replay")
        identity = (current.st_dev, current.st_ino)
        dirty = False
        with args.events.open("rb") as stream:
            stream.seek(offset)
            for _ in range(100000):
                line = stream.readline()
                if not line.endswith(b"\n"):
                    break  # partial append is retried from its previous byte offset
                offset = stream.tell()
                try:
                    dirty = monitor.apply(json.loads(line)) or dirty
                except (ValueError, KeyError, TypeError):
                    rejected += 1
                    dirty = True  # input remains intact; diagnostics expose the rejection
        if dirty or not published:
            print(
                publish_snapshot(
                    args.output,
                    monitor,
                    rejected,
                    args.max_output_bytes,
                    {
                        "consumed_bytes": offset,
                        "observed_file_bytes": current.st_size,
                        "pending_bytes": max(0, current.st_size - offset),
                    },
                ),
                flush=True,
            )
            published = True
        if args.duration_seconds and time.monotonic() - started >= args.duration_seconds:
            break
        if line.endswith(b"\n") and offset < args.events.stat().st_size:
            continue  # bounded chunk ended; drain backlog even in one-shot mode
        if not args.follow:
            break
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
