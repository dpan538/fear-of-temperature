"""Read-only receipt and calendar reconciliation of package 23, without network.

This public coordinator check does not locate or run the sealed evaluator.
It does not open a corpus database or re-extract newspaper content.
"""
import collections
import csv
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import shutil


PACKAGE = Path(__file__).resolve().parents[1]
REPO = next(p for p in PACKAGE.parents if (p / "AGENTS.md").exists())
ACQUIRED = PACKAGE / "transition_research/acquisition_followthrough_20261005"
OUT = PACKAGE / "control"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def main():
    checks = []

    def check(name, passed, detail):
        checks.append(dict(check=name, passed=bool(passed), detail=detail))

    with (REPO / "work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock").open("a+b") as mutex:
        fcntl.flock(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # These are the two newly submitted packages, not earlier corpus inputs.
        for directory, index_name, key in [
            (PACKAGE / "newspaper", "DELIVERY_INDEX.json", "records"),
            (PACKAGE / "transition_research", "PACKAGE_MANIFEST.json", "files"),
        ]:
            index = json.loads((directory / index_name).read_text())
            mismatches = []
            for entry in index[key]:
                file = directory / entry["path"]
                if not file.is_file() or file.stat().st_size != entry["bytes"] or sha(file) != entry["sha256"]:
                    mismatches.append(entry["path"])
            check("Frozen delivery receipts: " + directory.name, not mismatches,
                  dict(files=len(index[key]), mismatches=mismatches))

        units = [json.loads(line) for line in (ACQUIRED / "PUBLICATION_UNITS.jsonl").read_text().splitlines() if line]
        requests = [json.loads(line) for line in (ACQUIRED / "REQUESTS.jsonl").read_text().splitlines() if line]
        issues = json.loads((ACQUIRED / "ISSUE_CONTAINER_MANIFEST.json").read_text())
        ledger = rows(ACQUIRED / "NEWSPAPER_MONTH_LEDGER.csv")
        readable = [u for u in units if u["state"].startswith("saved_readable")]
        check("Distinct retained native URLs", len({u["url"] for u in units}) == len(units), len(units))
        check("Readable states retain the traced OCR article", len(readable) == 1214,
              dict(states=dict(collections.Counter(u["state"] for u in units))))
        check("Fixed publication interval", all("1988-01-01" <= u.get("publication_date", "") <= "2026-09-21" for u in readable),
              "Publication dates only; retrieval times remain separate")
        strata = ["EU/Europe excluding UK", "UK", "AU", "US", "NZ"]
        calendar = sorted({r["month"] for r in ledger})
        expected_calendar = [f"{year:04}-{month:02}" for year in range(1988, 2027)
                             for month in range(1, 13) if f"{year:04}-{month:02}" <= "2026-09"]
        check("Full planning calendar and unique geographic cells",
              calendar == expected_calendar and len(ledger) == 2790 and
              len({(r["stratum"], r["month"]) for r in ledger}) == 2790,
              "465 months x (five disjoint strata plus pooled)")
        summary = []
        month_rows = []
        for stratum in strata + ["pooled"]:
            retained = [u for u in units if stratum == "pooled" or u["stratum"] == stratum]
            selected = [u for u in readable if stratum == "pooled" or u["stratum"] == stratum]
            counts = collections.Counter(u["publication_date"][:7] for u in selected)
            pending = collections.Counter(u["publication_date"][:7] for u in retained)
            pdfs = collections.Counter(i["publication_date"][:7] for i in issues if stratum == "pooled" or i["stratum"] == stratum)
            old = {r["month"]: r for r in ledger if r["stratum"] == stratum}
            agrees = all(int(old[m]["readable_saved_units"]) == counts[m] and
                         int(old[m]["retained_publication_units"]) == pending[m] and
                         int(old[m]["whole_issue_PDFs"]) == pdfs[m] and
                         (old[m]["dated_source_presence"] == "True") == bool(counts[m] or pdfs[m])
                         for m in calendar)
            check("Ledger reconciliation: " + stratum, agrees, "Native readable units and whole issues separately counted")
            summary.append(dict(stratum=stratum, retained_native_units=len(retained),
                                readable_native_units=len(selected), readable_unit_months=len(counts),
                                whole_issue_PDFs=sum(pdfs.values()), dated_presence_months=len(set(counts) | set(pdfs)),
                                issue_only_months=len(set(pdfs) - set(counts)), calendar_months=465,
                                months_without_acquired_readable_unit=465-len(counts), independent_story_total="unestablished"))
            for month in calendar:
                state = "readable_native_unit_present" if counts[month] else "whole_issue_only_no_article_mapping" if pdfs[month] else "not_acquired_or_unknown"
                month_rows.append(dict(month=month, stratum=stratum, readable_native_units=counts[month],
                                       whole_issue_PDFs=pdfs[month], observed_state=state, fixed_upper_cutoff="2026-09-21"))

        owner = json.loads((ACQUIRED / "ACQUISITION_VERIFICATION.json").read_text())
        cache = json.loads((ACQUIRED / "VERIFIED_FILE_RECEIPTS.json").read_text())
        changed = []
        for name, receipt in cache.items():
            file = ACQUIRED / name
            if not file.is_file() or file.stat().st_size != receipt["bytes"] or file.stat().st_mtime_ns != receipt["mtime_ns"]:
                changed.append(name)
        check("Reuse owner raw/body hash checkpoint with unchanged size and mtime",
              owner["passed"] and not changed, dict(owner_checks=len(owner["checks"]), file_receipts=len(cache), changed=changed))
        # A bounded additional inspection, not another complete raw/text hash scan.
        samples = []
        sample_units = [u for u in readable if u["source"] == "InDaily"][:2]
        sample_units += [u for u in readable if "OCR" in u["state"]]
        for year in [2007, 2013, 2020, 2026]:
            sample_units.append(next(u for u in readable if u["stratum"] == "US" and u["publication_date"].startswith(str(year))))
        sample_units += [u for u in readable if u["body_sha256"] == "53fac5e4304173fcceb982cb2e796cb6006f4afdc6d84895c797c05a57d9c1bf"]
        for unit in sample_units:
            body = ACQUIRED / unit["body_path"]
            raw = ACQUIRED / unit["raw_path"]
            body_ok = sha(body) == unit["body_sha256"]
            raw_ok = sha(raw) == unit["raw_sha256"] if raw.suffix != ".pdf" else "reused unchanged owner PDF receipt"
            samples.append(dict(url=unit["url"], date=unit["publication_date"], state=unit["state"],
                                body_characters=unit["body_characters"], body_hash_agrees=body_ok, raw_hash_agrees=raw_ok))
        check("Nine bounded body/raw sample receipts", len(samples) == 9 and all(s["body_hash_agrees"] and s["raw_hash_agrees"] for s in samples), samples)
        hashes = collections.defaultdict(list)
        for unit in readable:
            hashes[unit["body_sha256"]].append(unit["url"])
        equal_body_groups = [urls for urls in hashes.values() if len(urls) > 1]
        check("Identical-text relationship recorded without deletion", len(equal_body_groups) == 1,
              equal_body_groups)
        research = PACKAGE / "transition_research"
        evidence = rows(research / "EVIDENCE_TABLE.csv")
        waves = rows(research / "LONGITUDINAL_VALUES.csv")
        registry = rows(research / "SOURCE_REGISTRY.csv")
        valid_ids = {r["source_id"] for r in registry}
        check("Research source references and distinct claim IDs",
              len(evidence) == 25 and len(waves) == 53 and len(valid_ids) == 16 and
              all(r["source_id"] in valid_ids for r in evidence + waves) and
              len({r["evidence_id"] for r in evidence}) == len(evidence),
              "25 claims, 53 wave comparisons, 16 sources; no universal crossover claim")
        owner_research = json.loads((research / "VALIDATION.json").read_text())
        check("Reuse research DOI/chart validation checkpoint", owner_research["passed"],
              dict(checks=len(owner_research["checks"]), counts=owner_research["counts"]))
        budget = json.loads((ACQUIRED / "CLOSING_BUDGET.json").read_text())
        at = dt.datetime.now(dt.timezone.utc).isoformat()
        inputs = ["PUBLICATION_UNITS.jsonl", "REQUESTS.jsonl", "NEWSPAPER_MONTH_LEDGER.csv",
                  "ISSUE_CONTAINER_MANIFEST.json", "ACQUISITION_VERIFICATION.json", "VERIFIED_FILE_RECEIPTS.json",
                  "SOURCE_REGISTRY_SUCCESSOR.json", "CLOSING_BUDGET.json", "RESOURCE_DECISION.json", "plan_next_round.py"]
        output = dict(reviewed_at_utc=at, publication_interval=["1988-01-01", "2026-09-21"],
                      scope="New package 23 receipts/metadata and nine sampled units; no formal DB, new network, models or sealed evaluator",
                      input_receipts=[dict(path=str((ACQUIRED/n).relative_to(PACKAGE)), bytes=(ACQUIRED/n).stat().st_size,
                                           sha256=sha(ACQUIRED/n)) for n in inputs],
                      passed=all(c["passed"] for c in checks), checks=checks, summary=summary,
                      readable_units_by_source=dict(collections.Counter(u["source"] for u in readable)),
                      readable_units_by_year=dict(sorted(collections.Counter(u["publication_date"][:4] for u in readable).items())),
                      issue_only_pooled_months=[r["month"] for r in month_rows if r["stratum"] == "pooled" and r["observed_state"] == "whole_issue_only_no_article_mapping"],
                      saved_closing_budget=budget, current_free_bytes=shutil.disk_usage(PACKAGE).free,
                      saved_lifetime_headroom_bytes=budget["media_lifetime_cap_bytes"]-budget["media_lifetime_used_bytes"],
                      budget_note="Current free space is a new observation; lifetime headroom is the earlier saved snapshot, not a fresh download release")
        (OUT / "COORDINATOR_REVIEW_RECEIPT_20261006.json").write_text(json.dumps(output, indent=2) + "\n")
        for filename, data in [("COVERAGE_SUMMARY_20261006.csv", summary), ("MONTH_PRESENCE_20261006.csv", month_rows)]:
            with (OUT / filename).open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(data[0]))
                writer.writeheader()
                writer.writerows(data)
        with (OUT / "VERIFICATION_TABLE_20261006.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["check", "passed", "detail"])
            writer.writeheader()
            writer.writerows(dict(check=c["check"], passed=c["passed"], detail=json.dumps(c["detail"])) for c in checks)
        print(json.dumps(dict(passed=output["passed"], checks=len(checks), summary=summary,
                              current_free_bytes=output["current_free_bytes"], issue_only=output["issue_only_pooled_months"])))
        if not output["passed"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
