#!/usr/bin/env python3
"""Check the completed validator outputs without reopening source databases."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXPECTED = {
    "UK_TWFY", "UK_HISTORIC", "UK_QS_API", "UK_HANSARD",
    "UK_DEFRA", "UK_GOVUK_HIST", "US_FR", "AU_CATALOGUE",
    "EU_CELLAR", "GUARDIAN_DEC2015", "PETITION_QUERY",
}


def rows(name):
    with (HERE / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    coverage = rows("execution_coverage.csv")
    findings = rows("findings.csv")
    quality = rows("source_quality_summary.csv")
    manifest = json.loads((HERE / "INPUT_MANIFEST.json").read_text())
    result = json.loads((HERE / "RESULT.json").read_text())
    assert len(coverage) == 110
    assert {r["frame_id"] for r in coverage} == EXPECTED
    assert len({(r["frame_id"], r["rule_id"]) for r in coverage}) == len(coverage)
    assert {r["frame_id"] for r in quality} == EXPECTED
    assert manifest["publication_interval_inclusive"] == ["1988-01-01", "2026-09-21"]
    assert result["publication_interval_inclusive"] == manifest["publication_interval_inclusive"]
    assert sum(int(r["denominator"]) for r in quality if r["frame_id"].startswith("UK_")) == 248035
    assert {r["frame_id"]: int(r["denominator"]) for r in quality if not r["frame_id"].startswith("UK_")} == {
        "US_FR": 33544, "AU_CATALOGUE": 821, "EU_CELLAR": 50578,
        "GUARDIAN_DEC2015": 396, "PETITION_QUERY": 177,
    }
    for r in coverage:
        assert int(r["eligible"]) == sum(int(r[x]) for x in
            ("supported", "conflict", "needs_review", "uncheckable", "not_applicable", "unassessed"))
        assert int(r["checked"]) == sum(int(r[x]) for x in ("supported", "conflict", "needs_review"))
        assert int(r["unassessed"]) == 0
    ids = set()
    finding_tally = Counter()
    evidence_paths = set()
    for r in findings:
        key = "|".join((r["frame_id"], r["unit_id"], r["rule_id"], r["rule_version"], r["input_snapshot"]))
        assert r["finding_id"] == hashlib.sha256(key.encode()).hexdigest()
        assert r["finding_id"] not in ids
        assert r["outcome"] in ("conflict", "needs_review", "uncheckable")
        assert r["evidence_path"] and r["evidence_locator"]
        assert r["input_snapshot"] == manifest["source_checkpoints"][r["frame_id"]]
        finding_tally[r["frame_id"], r["rule_id"], r["outcome"]] += 1
        evidence_paths.update(x.strip() for x in r["evidence_path"].split("|") if x.strip())
        ids.add(r["finding_id"])
    for path in evidence_paths:
        assert (ROOT / path).is_file(), path
    c = {(r["frame_id"], r["rule_id"]): r for r in coverage}
    for r in coverage:
        for outcome in ("conflict", "needs_review"):
            assert finding_tally[r["frame_id"], r["rule_id"], outcome] == int(r[outcome])
    assert int(c["GUARDIAN_DEC2015", "CONTENT_LINK"]["supported"]) == 4
    assert int(c["GUARDIAN_DEC2015", "CONTENT_LINK"]["uncheckable"]) == 392
    assert int(c["US_FR", "CONTENT_LINK"]["uncheckable"]) == 14954
    assert int(c["EU_CELLAR", "CONTENT_LINK"]["uncheckable"]) >= 30000
    assert int(c["UK_DEFRA", "DATE_CROSS"]["needs_review"]) + int(c["UK_GOVUK_HIST", "DATE_CROSS"]["needs_review"]) == 119
    assert sum(r["frame_id"] == "US_FR" and r["rule_id"] == "IDENT" and "95-24211" in r["observed"] for r in findings) == 2
    assert result["finding_rows"] == len(findings)
    for entry in manifest["inputs"]:
        assert (ROOT / entry["path"]).is_file(), entry["path"]
    summary = {
        "status": "PASS", "coverage_rows": len(coverage), "finding_rows": len(findings),
        "frames": {r["frame_id"]: int(r["denominator"]) for r in quality},
        "finding_outcomes": dict(Counter(r["outcome"] for r in findings)),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
