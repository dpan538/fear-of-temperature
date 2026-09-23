"""Build the initial 31-month, three-series recovery ledger.

This is a checkpoint artefact. It copies the current observed counts and
coverage states without treating a zero record count as evidence of complete
historical coverage. Later stages update evidence and outcomes in a versioned
copy rather than overwriting the source availability CSVs.
"""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE = (
    ROOT.parent
    / "historical_coverage_recovery"
    / "reports"
    / "temporal_reference_availability"
)
OUTPUT = ROOT / "month_recovery_ledger.csv"

SERIES = (
    "policy_document",
    "ministerial_written_answer",
    "ministerial_written_statement",
)


def main() -> None:
    empty = pd.read_csv(SOURCE / "months_without_any_reference.csv", dtype={"year_month": str})
    monthly = pd.read_csv(SOURCE / "monthly_reference_availability.csv", dtype={"year_month": str})

    zero_months = sorted(empty.loc[empty["record_count"].eq(0), "year_month"].unique())
    assert len(zero_months) == 31, zero_months

    indexed = monthly.set_index(["year_month", "series"])
    rows: list[dict[str, object]] = []
    for year_month in zero_months:
        for series in SERIES:
            current = indexed.loc[(year_month, series)]
            rows.append(
                {
                    "year_month": year_month,
                    "series": series,
                    "before_record_count": int(current["record_count"]),
                    "before_coverage_status": current["status"],
                    "before_coverage_note": current["note"],
                    "check_source": "pending bounded source check",
                    "evidence_url_or_path": "",
                    "parliamentary_context": (
                        "not applicable to policy; pending separate parliamentary calendar check"
                        if series == "policy_document"
                        else "pending official parliamentary calendar check"
                    ),
                    "policy_catalogue_status": (
                        "pending bounded predecessor-department/publication-catalogue check"
                        if series == "policy_document"
                        else "not applicable"
                    ),
                    "recoverable_candidate_count": "unknown",
                    "processing_result": "not yet checked in this tranche",
                    "date_reassignment_count": 0,
                    "new_document_count": 0,
                    "excluded_count": 0,
                    "after_record_count": int(current["record_count"]),
                    "final_status": "pending",
                    "notes": "Initial checkpoint copied from prior coverage view; zero count is not a completeness claim.",
                }
            )

    frame = pd.DataFrame(rows)
    assert len(frame) == 31 * 3
    assert frame["before_record_count"].eq(0).all()
    assert frame.groupby("year_month")["series"].nunique().eq(3).all()
    ROOT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT, index=False)
    print(f"{OUTPUT}|rows={len(frame)}|months={frame['year_month'].nunique()}")


if __name__ == "__main__":
    main()
