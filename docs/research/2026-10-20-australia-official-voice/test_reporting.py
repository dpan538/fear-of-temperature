"""Synthetic regression cases for count integrity and evidence-based date recovery."""

import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect as core  # noqa: E402
import report_enhancements as reporting  # noqa: E402
import resolve_qld_dates as qld_dates  # noqa: E402


def test_middle_year_zero_and_runs_without_boundary_false_positives():
    assert reporting.middle_zeros({2010: 4, 2011: 1, 2012: 0, 2013: 3}) == [2012]
    assert reporting.middle_zeros({2010: 4, 2011: 0, 2012: 0, 2013: 3}) == [2011, 2012]
    assert reporting.middle_zeros({2010: 0, 2011: 1, 2012: 0, 2013: 0}) == []
    assert reporting.middle_zeros({2010: 0, 2011: 0}) == []


def test_strict_native_ids_and_aggregated_counts_reconcile():
    row = dict(
        doc_id=core.digest(["fixture", "1"]),
        native_id="1",
        source_channel="fixture",
        query_matched='["heatwave"]',
        date_status="inside_fixed_interval",
        publication_start="2001-01-01",
        publication_end="2001-12-31",
        publication_month=None,
    )
    monthly, annual, totals = Counter(), Counter(), Counter()
    for matrix in reporting.MATRICES:
        annual[(matrix, "fixture", 2001)] = 1
        totals[(matrix, "fixture")] = 1
    result = reporting.validate([row], monthly, annual, totals, ["fixture"])
    assert result["status"] == "PASS"
    annual[("extended33_union", "fixture", 2001)] = 2
    with pytest.raises(ValueError, match="annual/native-ID mismatch"):
        reporting.validate([row], monthly, annual, totals, ["fixture"])
    with pytest.raises(ValueError, match="duplicate doc_id"):
        reporting.validate([row, row], monthly, annual, totals, ["fixture"])


def activity(kind="new package", private=False, timestamp="2015-05-26T19:37:02"):
    return {
        "id": "creation",
        "activity_type": kind,
        "timestamp": timestamp,
        "data": {"package": {"id": "fixture", "state": "active", "private": private}},
    }


def test_date_recovery_requires_retained_public_creation():
    assert qld_dates.public_creation([activity()], "fixture")["value"] == "2015-05"
    assert qld_dates.public_creation([activity("changed package")], "fixture") is None
    assert qld_dates.public_creation([activity(private=True)], "fixture") is None
    assert qld_dates.public_creation([activity()], "different_object") is None
    # No invented month/day when an unzoned timestamp straddles a calendar boundary.
    assert (
        qld_dates.public_creation([activity(timestamp="2015-05-31T23:59:00")], "fixture")["value"]
        == "2015"
    )
    assert qld_dates.public_creation([activity(timestamp="2015-12-31T23:59:00")], "fixture") is None


def test_activity_traversal_reaches_empty_page_and_preserves_pending_version(tmp_path):
    store = core.Store(tmp_path)
    store.save(
        "qld_opendata",
        "fixture",
        "Heatwave dataset",
        "heatwave",
        None,
        "https://data.qld.gov.au/dataset/fixture",
        tier="state_qld",
        unit="dataset_catalogue_metadata",
    )
    store.db.commit()
    visited = []

    class Client:
        def get(self, url):
            if "package_show" in url:
                return json.dumps(
                    {"success": True, "result": {"metadata_created": "1990-01-01"}}
                ).encode()
            offset = int(parse_qs(urlparse(url).query)["offset"][0])
            visited.append(offset)
            rows = [{**activity("changed package"), "id": str(i)} for i in range(104)] + [
                activity()
            ]
            return json.dumps({"success": True, "result": rows[offset : offset + 100]}).encode()

    qld_dates.run(store, Client())
    assert visited == [0, 100, 105]
    row = store.db.execute("SELECT * FROM source_documents").fetchone()
    assert row["publication_month"] == "2015-05"
    assert row["date_granularity"] == "month"
    assert row["publication_date"] is None
    assert (
        json.loads(row["metadata_version_history"])[0]["date_status"] == "pending_publication_date"
    )
    qld_dates.run(store, Client())
    assert visited == [0, 100, 105]


def test_user_phase_labels_are_stable_boundaries():
    assert reporting.phase(2005) == (1, "Historical Baseline")
    assert reporting.phase(2006) == (2, "Political & Policy Peak")
    assert reporting.phase(2014)[0] == 2
    assert reporting.phase(2015) == (3, "Institutional Normalization")
    assert reporting.phase(2026)[0] == 3
