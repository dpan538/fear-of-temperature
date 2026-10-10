"""Named historical repairs, without network or corpus-store writes."""
import datetime as dt
import json
import tempfile
from pathlib import Path

import collect as c
import entities as e
import transport as t

checks = []
with tempfile.TemporaryDirectory(dir=t.WORK) as fixture:
    root = Path(fixture)
    first = root / "first"; first.mkdir()
    second = root / "second"; second.mkdir()
    third = root / "third"; third.mkdir()
    t.atomic(first / "STATE.json", dict(requests=6000, attempts={"old": "saved"},
        returned_object_ids=["s|post|1", "s|post|2"], object_ids=["stable1", "stable2"]))
    t.atomic(second / "STATE.json", dict(inherited_state_reference=str(first / "STATE.json"),
        requests=6489, attempts={"second": "saved"}, returned_object_count=3))
    t.append(second / "RETURNED_KEYS.jsonl", {"keys": ["s|post|3"]})
    t.atomic(third / "STATE.json", dict(inherited_state_reference=str(second / "STATE.json"),
        requests=6489, attempts={}, returned_object_count=3))
    got = t.hydrate_state(third / "STATE.json")
    assert got["requests"] == 6489 and len(got["returned_object_ids"]) == 3
    assert got["attempts"] == {"old": "saved", "second": "saved"}
    assert got["object_ids"] == ["stable1", "stable2"]
    checks.append("recursive_compact_state_and_append_only_keys_preserve_counters")
    t.atomic(first / "STATE.json", {"inherited_state_reference": str(third / "STATE.json")})
    try:
        t.hydrate_state(third / "STATE.json")
    except t.Stop as exc:
        assert str(exc) == "inherited_state_reference_cycle"
    else:
        raise AssertionError("cycle was accepted")
    checks.append("state_cycle_rejected_without_mutation")

f = dict(source="forum", kind="discourse_archive", base="https://public.example",
    license="unknown", topics=[], chunks=[], seen_topics=[], status="active")
url, route = c.job(f)
assert "order=created" in url and "ascending=true" in url
c.advance(f, {"topic_list": {"topics": [{"id": 1}, {"id": 2}],
    "more_topics_url": "/latest?order=created&ascending=true&page=1"}}, route)
assert f["status"] == "active" and f["topics"] == [1, 2]
assert f["native_next_url"] == "https://public.example/latest.json?order=created&ascending=true&page=1"
checks.append("oldest_first_first_page_not_completion_and_native_link_preserved")
c.advance(f, {"id": 1, "post_stream": {"posts": [{"id": 10}], "stream": [10, 11, 12]}}, "discourse_topic")
assert f["chunks"] == [{"topic": 1, "ids": [11, 12]}] and f["status"] == "active"
c.advance(f, {}, "discourse_chunk")
c.advance(f, {"id": 2, "post_stream": {"posts": [], "stream": []}}, "discourse_topic")
assert f["status"] == "active"
c.advance(f, {"topic_list": {"topics": [], "more_topics_url": None}}, "discourse_archive_index")
assert f["status"] == "native_index_exhausted"
checks.append("complete_native_topics_and_replies_drain_before_genuine_index_end")

# Two already loaded bodies have no bearing on additional eligible native work.
f = dict(source="se_test", kind="se_questions", year=2020, page=1,
    status="active", context_queue=[], loaded_body_count=2)
c.advance(f, {"items": [{"question_id": 3, "creation_date": 1600000000}], "has_more": True}, "se_questions")
assert f["status"] == "active" and f["page"] == 2
f["context_queue"] = []
c.advance(f, {"items": [], "has_more": False}, "se_questions")
assert f["year"] == 2021 and f["status"] == "active"
checks.append("two_loaded_bodies_do_not_complete_source_month_or_year")
f = {"max_id": "200", "status": "active"}
c.advance(f, [{"id": "199", "created_at": "2020-01-01"}, {"id": "180", "created_at": "2019-12-31"}], "mastodon")
assert f["max_id"] == "180" and f["status"] == "active"
checks.append("backward_native_cursor_crosses_year_boundary_without_excluding_returns")
r = e.discourse({"posts": [{"id": 1, "topic_id": 2, "post_number": 1,
    "created_at": "1999-01-01T00:00:00Z", "updated_at": "2026-10-10T00:00:00Z",
    "post_type": 1, "cooked": "unchanged native historical body"}]}, "fixture", "https://public.example", "unknown")[0]
assert r["native_created_at"].startswith("1999") and r["native_edited_at"].startswith("2026")
assert e.prepare(r)["readable_native_unit"] == 1
checks.append("publication_and_edit_dates_separate_retrieval_does_not_move_endpoint")

actual = t.state()
baseline = t.read_json(t.WORK / "INHERITED_BASELINE.json")
assert actual["requests"] >= baseline["lifetime_charged_requests"] == 6489
assert len(actual["returned_object_ids"]) >= baseline["lifetime_distinct_returned_objects"] == 268386
checks.append("live_metadata_baseline_preserved_no_body_scan")
t.atomic(t.WORK / "HISTORICAL_REPAIR_REGRESSION.json", {
    "at_utc": t.utc(), "passed": True, "checks": checks,
    "source_requests": 0, "corpus_writes": 0,
    "no_expected_historical_volume_or_replacement_count_target": True})
print(json.dumps({"passed": True, "checks": len(checks), "source_requests": 0}))
