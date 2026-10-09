from dataclasses import asdict, replace

import pytest

from fear_temperature.media_planning.core import Unit
from fear_temperature.media_planning.parent_monitor import ParentMonitor, bootstrap_parent_monitor


def monitor():
    m = ParentMonitor()
    m.apply({"kind": "source", "revision": 1, "source": {"source_id": "s", "stream": "newspaper"}})
    return m


def entity(revision=1, **kwargs):
    u = Unit("newspaper", "s", "a", "work:a", "2026-08-01", True, True)
    return {"kind": "entity", "revision": revision, "unit": asdict(replace(u, **kwargs))}


def parents(revision=1, ids=("p",), **kwargs):
    return {
        "kind": "parent_assertions",
        "revision": revision,
        "source_id": "s",
        "dimension": "publisher_organization",
        "assertions": [
            {"parent_id": i, "status": "confirmed", "evidence_ref": "mapping-1", **kwargs}
            for i in ids
        ],
    }


def summary(m):
    return next(
        r for r in m.snapshot()["dimension_summary"] if r["dimension"] == "publisher_organization"
    )


def test_replay_and_new_versions_count_one_entity():
    m = monitor()
    assert m.apply(entity())
    assert not m.apply(entity())
    assert m.apply(entity(2, body_hash="corrected"))
    assert not m.apply(entity())
    assert len(m.units) == 1
    with pytest.raises(ValueError, match="Conflicting"):
        m.apply(entity(2, body_hash="contradiction"))


def test_parent_mapping_revision_changes_view_without_removing_entity():
    m = monitor()
    m.apply(entity())
    assert summary(m)["unmapped_entities"] == 1
    m.apply(parents())
    assert summary(m)["observed_parent_count"] == 1
    m.apply(parents(2, ids=("new",)))
    s = m.snapshot()
    assert len(m.units) == 1
    assert {
        r["parent_id"] for r in s["parent_counts"] if r["dimension"] == "publisher_organization"
    } == {"new"}
    assert summary(m)["unmapped_entities"] == 0


def test_candidate_parent_is_unresolved_and_does_not_inflate_parent_count():
    m = monitor()
    m.apply(entity())
    m.apply(parents(status="candidate"))
    assert summary(m)["observed_parent_count"] == 0
    assert summary(m)["unmapped_body_share"] == 1


def test_known_work_duplicates_and_multiple_parents_have_explicit_count_units():
    m = monitor()
    m.apply(entity())
    m.apply(entity(entity_id="b"))
    m.apply(parents(ids=("p", "q")))
    s = m.snapshot()
    rows = [
        r
        for r in s["parent_counts"]
        if r["dimension"] == "publisher_organization" and r["publication_month"] == "ALL"
    ]
    assert len(rows) == 2
    assert all(r["retained_entities"] == 2 and r["known_publication_keys"] == 1 for r in rows)
    assert summary(m)["multi_parent_entities"] == 2
    assert len(m.units) == 2


def test_historical_parent_validity_uses_publication_date_and_pending_stays_unknown():
    m = monitor()
    m.apply(entity())
    m.apply(parents(valid_from="2026-09-01"))
    assert summary(m)["unmapped_entities"] == 1
    m.apply(entity(2, publication_day="2026-09-01"))
    assert summary(m)["unmapped_entities"] == 0
    m.apply(entity(3, date_usable=False))
    assert summary(m)["unmapped_entities"] == 1
    assert summary(m)["dated_readable_body_entities"] == 0
    assert len(m.units) == 1


def test_date_correction_moves_the_month_without_double_counting():
    m = monitor()
    m.apply(parents())
    m.apply(entity())
    m.apply(entity(2, publication_day="2026-07-01"))
    rows = [r for r in m.snapshot()["parent_counts"] if r["dimension"] == "publisher_organization"]
    assert {r["publication_month"] for r in rows} == {"ALL", "2026-07"}
    assert all(r["retained_entities"] == 1 for r in rows)


def test_bootstrap_does_not_invent_independent_publishers_from_software():
    registry = {
        "s": {
            "source_id": "s",
            "stream": "social",
            "platform_family": "Discourse",
            "base_url": "https://forum.example",
        }
    }
    m = bootstrap_parent_monitor(
        registry, [Unit("social", "s", "a", "a", "2026-08-01", True, True)]
    )
    rows = {r["dimension"]: r for r in m.snapshot()["dimension_summary"]}
    assert rows["software_family"]["observed_parent_count"] == 1
    assert rows["community"]["observed_parent_count"] == 1
    assert rows["publisher_organization"]["observed_parent_count"] == 0
    assert rows["platform_network"]["observed_parent_count"] == 0


def test_invalid_mapping_or_stream_does_not_change_view():
    m = monitor()
    m.apply(entity())
    before = summary(m)
    with pytest.raises(ValueError, match="evidence"):
        m.apply(parents(evidence_ref=""))
    with pytest.raises(ValueError, match="mismatch"):
        m.apply(entity(2, stream="social"))
    assert summary(m) == before


def test_live_publication_preserves_history_and_limits_only_monitor(tmp_path):
    import json

    from fear_temperature.media_planning.parent_monitor import publish_snapshot

    m = monitor()
    m.apply(entity())
    target = publish_snapshot(tmp_path, m, 0)
    first = json.loads(target.read_text())
    m.apply(parents())
    publish_snapshot(tmp_path, m, 0)
    second = json.loads(target.read_text())
    assert first["report_id"] != second["report_id"]
    assert len((tmp_path / "history.jsonl").read_text().splitlines()) == 2
    assert list(tmp_path.glob("snapshot-*.json")) == []
    before = target.read_bytes()
    with pytest.raises(RuntimeError, match="stop monitor only"):
        publish_snapshot(tmp_path, m, 0, max_output_bytes=1)
    assert target.read_bytes() == before
    assert len(m.units) == 1


def test_follow_reads_new_events_and_waits_for_complete_lines(tmp_path):
    import json
    import subprocess
    import sys
    import time

    events = tmp_path / "events.jsonl"
    output = tmp_path / "dashboard"
    first = {"kind": "source", "revision": 1, "source": {"source_id": "s", "stream": "newspaper"}}
    events.write_text(json.dumps(first) + "\n")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "fear_temperature.media_planning.parent_monitor",
            "--events",
            str(events),
            "--output",
            str(output),
            "--follow",
            "--poll-seconds",
            "0.2",
            "--duration-seconds",
            "1.6",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 1
        while not (output / "latest.json").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (output / "latest.json").exists()
        payload = json.dumps(entity())
        with events.open("a") as stream:
            stream.write(payload[:20])
        time.sleep(0.25)
        assert json.loads((output / "latest.json").read_text())["retained_metadata_entities"] == 0
        with events.open("a") as stream:
            stream.write(payload[20:] + "\n" + payload + "\n")
        stdout, stderr = process.communicate(timeout=4)
        assert process.returncode == 0, (stdout, stderr)
        final = json.loads((output / "latest.json").read_text())
        assert final["retained_metadata_entities"] == 1
        assert final["rejected_metadata_events"] == 0
        assert final["feed"]["pending_bytes"] == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
