"""Meaningful conformance checks on synthetic data only; no protected store reads."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import adapter_contract as a


def record(native_id="fixture-1", kind="news_article", value="2025-06-12", precision="day"):
    text = "Routine local announcement.\r\nA second neutral paragraph."
    return dict(
        archive=dict(snapshot_id="synthetic-archive-v1", snapshot_path="synthetic://protected-reference", snapshot_observed_at="2026-10-12T00:00:00Z",
                     original_id=native_id, original_version_id="old-v1", locator="fixture:" + native_id,
                     recorded_content_hash=a.text_hash(text), hash_basis="fixture_utf8_original_native_string"),
        source=dict(id="synthetic_au", label="Synthetic Australian source", stream="newspaper", genre="regional_news",
                    source_url="https://example.invalid/" + native_id, context_basis="australian_publisher", context_state="verified",
                    identity_state="verified", context_evidence="fixture:Australian-publisher-evidence"),
        native=dict(id=native_id, namespace="fixture-news", kind=kind, identity_state="verified", identity_evidence="fixture:native-ID",
                    unit_state="verified", unit_evidence="fixture:complete-native-boundary", independently_authored_body=True),
        publication=dict(value=value, precision=precision, state="verified", evidence="fixture:original-publication-label"),
        content=dict(original_text=text, original_text_sha256=a.text_hash(text), original_text_sha256_basis="utf8_original_native_string",
                     original_format="plain", completeness="verified_complete", readable_original=True, provenance="direct_original",
                     reference="fixture:original-body", evidence="fixture:body-to-native-ID"),
        rights=dict(public_access="allowed", local_retention="allowed", internal_analysis="allowed", redistribution="unknown", licence="synthetic",
                    intended_use="internal structural fixture", evidence="fixture:internal-use-authority", checked_at="2026-10-12T00:00:00Z"),
        legacy_disposition=dict(state="checked_no_hold", evidence="fixture:legacy-disposition-lookup"),
        times=dict(retrieved_at="2026-10-10T00:00:00Z", extracted_at="2026-10-10T00:01:00Z", content_version_at=None, report_at="2026-10-12T00:00:00Z"))


class ContractTest(unittest.TestCase):
    def setUp(self):
        self.c = a.fixture_database()

    def tearDown(self):
        self.c.close()

    def test_replay_is_idempotent_and_originals_survive_derived_fix(self):
        r = record()
        x, y = a.import_record(self.c, r), a.import_record(self.c, r)
        self.assertEqual(x, y)
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM admission_ledger").fetchone()[0], 1)
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM structural_changes").fetchone()[0], 1)
        values = {row[0]:row[1] for row in self.c.execute("SELECT representation_kind,text_value FROM text_representations")}
        self.assertEqual(values["original"], r["content"]["original_text"])
        self.assertEqual(values["structural_derived"], r["content"]["original_text"].replace("\r\n", "\n"))
        self.assertEqual(a.validate_fixture(self.c)["integrity"], "ok")

    def test_neutral_text_and_unknown_author_country_are_admitted(self):
        r = record()
        r["native"]["author_geography"] = None
        r["historical_fear_pilot"] = 0  # Historical diagnostic cannot control admission.
        r["source_concentration"] = 1.0
        self.assertEqual(a.import_record(self.c, r)["disposition"], "admitted")

    def test_partial_month_and_year_never_become_invented_days(self):
        r = record(value="2026-09", precision="month")
        self.assertEqual(a.import_record(self.c, r)["disposition"], "pending")
        r = record("year", value="2025", precision="year")
        self.assertEqual(a.import_record(self.c, r)["disposition"], "admitted")
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM accepted_monthly_versions").fetchone()[0], 0)
        r = record("bounded", value="2026-09", precision="month")
        r["publication"]["bounded_interval"] = dict(lower="2026-09-01", upper="2026-09-21", evidence="fixture:cutoff-bounded-publication-range")
        self.assertEqual(a.import_record(self.c, r)["disposition"], "admitted")

    def test_cutoff_is_publication_not_retrieval(self):
        r = record(value="2026-09-22")
        r["times"]["retrieved_at"] = "2026-09-20T00:00:00Z"
        self.assertEqual(a.import_record(self.c, r)["disposition"], "archive_only")
        r = record("cutoff", value="2026-09-21")
        self.assertEqual(a.import_record(self.c, r)["disposition"], "admitted")
        r = record("bad-date", value="2025-02-30")
        self.assertEqual(a.import_record(self.c, r)["disposition"], "quarantine")

    def test_hash_mismatch_and_explicit_legacy_hold_are_record_specific(self):
        r = record()
        r["content"]["original_text_sha256"] = "0" * 64
        self.assertEqual(a.import_record(self.c, r)["disposition"], "quarantine")
        r = record("pending-wrapper")
        r["legacy_disposition"] = dict(state="pending", reason="image_wrapper_boundary", evidence="fixture:old-row-disposition")
        self.assertEqual(a.import_record(self.c, r)["disposition"], "pending")
        self.assertEqual(a.import_record(self.c, record("same-source-good"))["disposition"], "admitted")

    def test_rights_unknown_pending_but_unknown_redistribution_not_internal_barrier(self):
        r = record()
        r["rights"]["internal_analysis"] = "unknown"
        self.assertEqual(a.import_record(self.c, r)["disposition"], "pending")
        r = record("denied")
        r["rights"]["local_retention"] = "denied"
        self.assertEqual(a.import_record(self.c, r)["disposition"], "restricted")
        self.assertEqual(a.import_record(self.c, record("internal"))["disposition"], "admitted")

    def test_identical_bodies_do_not_merge_independent_works(self):
        x = a.import_record(self.c, record("one"))
        y = a.import_record(self.c, record("two"))
        self.assertNotEqual(x["mapping"]["new_unit_id"], y["mapping"]["new_unit_id"])
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM accepted_news_works").fetchone()[0], 2)

    def test_boost_is_context_not_independent_authored_body(self):
        r = record("boost", kind="repost")
        r["source"]["stream"] = "public_civic"
        r["source"]["context_basis"] = "australian_community"
        r["content"] = dict(original_text=None, completeness="native_context", provenance="direct_original", evidence="fixture:bodyless-boost")
        self.assertEqual(a.import_record(self.c, r)["disposition"], "context_only")
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM accepted_public_authored_bodies").fetchone()[0], 0)

    def test_parliamentary_lineage_and_no_automatic_executive_role(self):
        r = record("paragraph", kind="parliament_paragraph")
        r["source"]["stream"] = "institutional"
        r["source"]["context_basis"] = "australian_institution"
        r["native"]["paragraph_parent_mode"] = "utterance"
        self.assertEqual(a.import_record(self.c, r)["disposition"], "pending")
        r["relations"] = [dict(type=t, target_source="synthetic_au", target_namespace="parliament", target_id=t + "-1",
                               state="verified", evidence="fixture:explicit-parent-key") for t in ("in_sitting", "in_procedural_unit", "in_utterance")]
        self.assertEqual(a.import_record(self.c, r)["disposition"], "admitted")
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM accepted_parliamentary_paragraphs").fetchone()[0], 1)
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM speaker_role_assertions").fetchone()[0], 0)

    def test_pending_evidence_can_resolve_through_new_metadata_version(self):
        r = record()
        r["publication"]["state"] = "pending"
        x = a.import_record(self.c, r)
        r["publication"]["state"] = "verified"
        y = a.import_record(self.c, r)
        self.assertEqual(x["mapping"]["new_unit_id"], y["mapping"]["new_unit_id"])
        self.assertNotEqual(x["mapping"]["unit_version_id"], y["mapping"]["unit_version_id"])
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM metadata_versions").fetchone()[0], 2)

    def test_append_only_and_production_connection_refusal(self):
        a.import_record(self.c, record())
        for sql in ("DELETE FROM archive_to_new_map", "UPDATE content_versions SET original_reference='changed'"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.c.execute(sql)
        # A sandbox temporary empty DB proves refusal; it is not an active corpus.
        with tempfile.TemporaryDirectory() as root:
            conn = sqlite3.connect(str(Path(root) / "empty-fixture.sqlite3"))
            try:
                with self.assertRaisesRegex(ValueError, "only_in_memory"):
                    a.import_record(conn, record())
            finally:
                conn.close()

    def test_cross_unit_or_role_sum_is_refused(self):
        rows = [dict(unit_kind=k, role_frame="institutional", version_basis="distinct_native_ID", disjoint_verified=True, count=1)
                for k in ("news_article", "parliament_paragraph")]
        with self.assertRaises(ValueError):
            a.combine_compatible_counts(rows)
        rows[0]["unit_kind"] = "parliament_paragraph"
        rows[0]["role_frame"] = "executive"
        with self.assertRaises(ValueError):
            a.combine_compatible_counts(rows)

    def test_naive_timestamp_pending_and_original_offset_preserved(self):
        r = record(value="2026-09-21T23:30:00", precision="timestamp")
        self.assertEqual(a.import_record(self.c, r)["disposition"], "pending")
        r = record("offset", value="2026-09-21T23:30:00+10:00", precision="timestamp")
        self.assertEqual(a.import_record(self.c, r)["disposition"], "admitted")
        self.assertEqual(a.publication_bounds(r["publication"])[0], "2026-09-21")

    def test_frozen_view_rejects_pending_and_duplicate_unit_version(self):
        pending = record("pending-view")
        pending["rights"]["internal_analysis"] = "unknown"
        x = a.import_record(self.c, pending)["mapping"]
        self.c.execute("INSERT INTO analysis_views VALUES (?,?,?,?,?,?,?)",
                       ("fixture-view", '["synthetic_au"]', "news_article", "2025-01-01", "2025-12-31", "2026-10-12T00:00:00Z", "fixture:review"))
        self.c.execute("INSERT INTO analysis_view_sources VALUES (?,?,?,?,?)",
                       ("fixture-view", "synthetic_au", "regional_news", "media", "fixture:source-frame-review"))
        with self.assertRaisesRegex(sqlite3.IntegrityError, "unverified"):
            self.c.execute("INSERT INTO analysis_view_members VALUES (?,?,?,?)", ("fixture-view", x["new_unit_id"], x["unit_version_id"], x["decision_id"]))
        y = a.import_record(self.c, record("accepted-view"))["mapping"]
        self.c.execute("INSERT INTO analysis_view_members VALUES (?,?,?,?)", ("fixture-view", y["new_unit_id"], y["unit_version_id"], y["decision_id"]))
        with self.assertRaises(sqlite3.IntegrityError):
            self.c.execute("INSERT INTO analysis_view_members VALUES (?,?,?,?)", ("fixture-view", y["new_unit_id"], y["unit_version_id"], y["decision_id"]))
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM frozen_native_versions").fetchone()[0], 1)

    def test_view_cannot_import_wrong_time_or_unproved_executive_role(self):
        r = record(value="2024-06-12")
        x = a.import_record(self.c, r)["mapping"]
        self.c.execute("INSERT INTO analysis_views VALUES (?,?,?,?,?,?,?)",
                       ("scope-view", '["synthetic_au"]', "news_article", "2025-01-01", "2025-12-31", "2026-10-12T00:00:00Z", "fixture:review"))
        self.c.execute("INSERT INTO analysis_view_sources VALUES (?,?,?,?,?)",
                       ("scope-view", "synthetic_au", "regional_news", "executive", "fixture:proposed-role"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.c.execute("INSERT INTO analysis_view_members VALUES (?,?,?,?)", ("scope-view", x["new_unit_id"], x["unit_version_id"], x["decision_id"]))
        y = a.import_record(self.c, record("current-year"))["mapping"]
        with self.assertRaises(sqlite3.IntegrityError):
            self.c.execute("INSERT INTO analysis_view_members VALUES (?,?,?,?)", ("scope-view", y["new_unit_id"], y["unit_version_id"], y["decision_id"]))

    def test_full_465_month_calendar_is_unknown_until_evidenced(self):
        cells = a.full_period_cells("fixture-frame", "synthetic_au", "regional_news", "media", "news_article")
        self.assertEqual(len(cells), 465)
        self.assertEqual(cells[0]["month"], "1988-01")
        self.assertEqual(cells[-1]["upper_day"], "2026-09-21")
        self.assertTrue(all(x["applicability_state"] == "unknown" and x["readable_native_units"] is None for x in cells))

    def test_historical_public_letter_stays_distinct_from_modern_post_and_news(self):
        r = record("letter-1988", kind="public_letter", value="1988-01-12")
        r["source"].update(stream="public_civic", genre="archival_public_letter", context_basis="australian_community")
        r["native"]["namespace"] = "historical-letter-original"
        self.assertEqual(a.import_record(self.c, r)["disposition"], "admitted")
        self.assertEqual(self.c.execute("SELECT unit_kind FROM accepted_public_authored_bodies").fetchone()[0], "public_letter")
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM accepted_news_works").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
