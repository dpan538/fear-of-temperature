#!/usr/bin/env python3
"""One bounded verification of this audit's derived files; no corpus rescan."""
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def csv_rows(name):
    with (HERE / name).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def main():
    summary = csv_rows("source_quality_summary.csv")
    ledger = csv_rows("source_quality_ledger.csv")
    sample = csv_rows("verification_sample.csv")
    queue = csv_rows("supplementation_queue.csv")
    manifest = json.loads((HERE / "INPUT_MANIFEST.json").read_text())
    result = json.loads((HERE / "RESULT.json").read_text())
    assert manifest["study_publication_interval_inclusive"] == ["1988-01-01", "2026-09-21"]
    assert len(summary) == 14 and len(ledger) == 44 and len(sample) == 30 and len(queue) == 11
    assert Counter(row["record_level"] for row in ledger) == {"frame_rule": 14, "individual_sample": 30}
    assert len({(row["frame_id"], row["parent_id"]) for row in sample}) == 30
    assert len({row["frame_id"] for row in summary}) == 14
    by_frame = Counter(row["frame_id"] for row in sample)
    for row in summary:
        n = int(row["denominator"])
        assert n == int(row["rule_derived_count"])
        assert int(row["sampled_n"]) == by_frame[row["frame_id"]]
        assert int(row["unassessed_individual_n"]) + int(row["sampled_n"]) == n
        assert all(0 <= int(row[k]) <= int(row["sampled_n"]) for k in ["individually_verified_identity_n", "individually_verified_date_n", "individually_verified_mapping_n", "sample_pending_or_partial_n", "sample_provenance_conflict_n"])
    counts = {row["frame_id"]: int(row["denominator"]) for row in summary}
    assert sum(counts[k] for k in counts if k.startswith("UK_")) == 248035
    assert counts["US_FR_RAW"] + counts["US_GOVINFO_FALLBACK"] == 33544
    assert counts["EU_ITEM"] + counts["EU_NO_ITEM"] == 50578
    assert counts["AU_ORIGINAL_PAIR"] + counts["AU_UNRESOLVED"] == 821
    assert counts["GUARDIAN_DEC2015"] == 396 and counts["PETITION_QUERY"] == 177
    assert all(row["checked_at_utc"] and row["evidence_reference"] and row["classification_basis"] for row in sample)
    assert all(row["priority"] and row["exact_target"] and row["original_or_reproduction_route"] and row["stopping_rule"] for row in queue)
    assert len(manifest["frames"]) == 14 and all((ROOT / row["path"]).is_file() for row in manifest["inputs"])
    assert all((ROOT / row["path"]).is_file() for row in manifest["sample_local_originals"])
    assert all((ROOT / path).is_file() for path in result["output_paths"])
    assert result["counts"]["sample_parents_or_works"] == 30
    assert sum(int(x["individually_verified_identity_n"]) for x in summary) == 22
    assert sum(int(x["individually_verified_date_n"]) for x in summary) == 23
    assert sum(int(x["individually_verified_mapping_n"]) for x in summary) == 18
    assert sum(int(x["sample_pending_or_partial_n"]) for x in summary) == 12
    assert "1988-01-01 through 2026-09-21" in (HERE / "REPORT.md").read_text()
    print("PASS: 14 source-route frames, 30 bounded sample cases, 11 targeted queue items, source-specific denominators and cited local evidence paths.")


if __name__ == "__main__":
    main()
