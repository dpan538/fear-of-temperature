"""Planning arithmetic only. Does not read text, collect data or run a model."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

GB = 1_000_000_000
GIB = 1_073_741_824


def token_window_count(tokens: int, window: int, overlap: int) -> int:
    if tokens < 0 or window <= 0 or not 0 <= overlap < window:
        raise ValueError("Require tokens >= 0 and 0 <= overlap < window")
    return 0 if tokens == 0 else 1 + max(0, math.ceil((tokens - window) / (window - overlap)))


def estimate_case(case: dict, assumptions: dict, available_bytes: int, reserve_bytes: int) -> dict:
    count, dimensions = case["passages"], case["dimensions"]
    value_bytes = case["bytes_per_value"]
    if count < 0 or dimensions <= 0 or value_bytes not in (2, 4):
        raise ValueError("Invalid count, dimension or dtype size")
    vectors = count * dimensions * value_bytes
    chunks = count * assumptions["text_and_lineage_bytes_per_passage"]
    index = (vectors * assumptions["index_additional_payload_multiplier"]
             + count * assumptions["index_metadata_bytes_per_passage"]) if case["build_index"] else 0
    variable_bytes = vectors + chunks + index
    retained = assumptions["fixed_retained_bytes"] + variable_bytes
    scratch = max(assumptions["minimum_temporary_bytes"],
                  math.ceil(variable_bytes * assumptions["temporary_fraction_of_variable_outputs"]))
    peak = retained + scratch
    headroom = max(0, available_bytes - reserve_bytes)
    rates = []
    for rate in assumptions["assumed_passages_per_second"]:
        pure_seconds = count / rate
        planned_seconds = pure_seconds * assumptions["runtime_overhead_factor"]
        rates.append({"assumed_passages_per_second": rate,
                      "encoding_only_hours": pure_seconds / 3600,
                      "with_assumed_overhead_hours": planned_seconds / 3600,
                      "continuous_days_with_assumed_overhead": planned_seconds / 86400})
    return {**case, "dense_vector_bytes": vectors, "text_and_lineage_bytes": chunks,
            "optional_index_bytes": index, "retained_bytes": retained,
            "temporary_bytes": scratch, "peak_bytes": peak,
            "retained_decimal_GB": retained / GB, "peak_decimal_GB": peak / GB,
            "fits_preferred_50GB_peak": peak <= 50 * GB,
            "fits_alternative_100GB_peak": peak <= 100 * GB,
            "fits_observed_disk_after_existing_reserve": peak <= headroom,
            "runtime_sensitivity_not_a_benchmark": rates}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    directory = Path(__file__).resolve().parent
    parser.add_argument("--config", type=Path, default=directory / "BUDGET_ASSUMPTIONS.json")
    parser.add_argument("--output", type=Path, default=directory / "BUDGET_RESULTS.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    disk = config["observed_storage"]
    available_bytes = disk["available_1024_blocks"] * 1024
    reserve_bytes = disk["existing_physical_floor_GiB"] * GIB
    cases = [estimate_case(c, config["scenario_assumptions"], available_bytes, reserve_bytes)
             for c in config["passage_scenarios"]]
    for cap in config["planning_envelopes"]:
        assert sum(cap["component_GB"].values()) == cap["peak_limit_GB"]
    # Check boundary handling and the payload arithmetic, rather than running any corpus.
    assert token_window_count(0, 220, 20) == 0
    assert token_window_count(220, 220, 20) == 1
    assert token_window_count(221, 220, 20) == 2
    assert token_window_count(420, 220, 20) == 2
    assert token_window_count(421, 220, 20) == 3
    assert 1_000_000 * 1024 * 4 == 4_096_000_000
    result = {"status": "planning scenarios, not measured workload or execution gates",
              "budget_scope": config["budget_scope"],
              "current_storage": {"available_bytes": available_bytes,
                                  "available_decimal_GB": available_bytes / GB,
                                  "physical_floor_bytes": reserve_bytes,
                                  "new_peak_headroom_bytes": max(0, available_bytes - reserve_bytes),
                                  "new_peak_headroom_decimal_GB": max(0, available_bytes - reserve_bytes) / GB},
              "cases": cases,
              "planning_envelopes": config["planning_envelopes"],
              "researcher_hours": {"minimum": sum(p["hours_min"] for p in config["staff_work_phases"]),
                                   "maximum": sum(p["hours_max"] for p in config["staff_work_phases"]),
                                   "hours_per_working_day_assumption": 8},
              "benchmark_executed": False, "corpus_or_model_run": False}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(args.output),
                      "current_new_peak_headroom_GB": round(result["current_storage"]["new_peak_headroom_decimal_GB"], 2),
                      "researcher_hours": result["researcher_hours"],
                      "cases": [{"name": c["name"], "peak_GB": round(c["peak_decimal_GB"], 2)} for c in cases]}))


if __name__ == "__main__":
    main()
