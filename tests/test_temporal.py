from __future__ import annotations

import numpy as np
import pandas as pd

from fear_temperature.temporal import (
    AGGREGATION_COLUMNS,
    aggregate_role_time,
    conditional_var_demo,
    cross_correlation,
    generate_synthetic_timeseries,
)


def _aggregation_input() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "passage_id": "a",
                "source_id": "s1",
                "publisher_role": "public",
                "publication_date": "2015-01-01",
                "fixture_relevant": False,
                "fixture_future_worry": False,
                "weight": 1.0,
            },
            {
                "passage_id": "b",
                "source_id": "s1",
                "publisher_role": "public",
                "publication_date": "2015-03-01",
                "fixture_relevant": True,
                "fixture_future_worry": False,
                "weight": 1.0,
            },
            {
                "passage_id": "c",
                "source_id": "s2",
                "publisher_role": "public",
                "publication_date": "2015-03-02",
                "fixture_relevant": True,
                "fixture_future_worry": True,
                "weight": 1.0,
            },
        ]
    )


def test_missing_bins_are_not_zero_and_zero_relevant_has_no_emotion_denominator() -> None:
    result = aggregate_role_time(_aggregation_input(), roles=("public",))
    january, february, march = result.to_dict(orient="records")
    assert january["coverage_status"] == "observed_zero_relevant"
    assert january["attention_s"] == 0
    assert np.isnan(january["emotion_e"])
    assert january["joint_b"] == 0
    assert february["coverage_status"] == "missing_no_eligible_units"
    assert np.isnan(february["attention_s"])
    assert np.isnan(february["emotion_e"])
    assert np.isnan(february["joint_b"])
    assert march["attention_s"] == 1
    assert march["emotion_e"] == 0.5
    assert march["joint_b"] == 0.5


def test_s_e_b_identity_and_output_schema() -> None:
    result = aggregate_role_time(_aggregation_input(), roles=("public",))
    assert result.columns.tolist() == AGGREGATION_COLUMNS
    eligible = result["emotion_e"].notna()
    np.testing.assert_allclose(
        result.loc[eligible, "joint_b"],
        result.loc[eligible, "attention_s"] * result.loc[eligible, "emotion_e"],
    )


def test_positive_lag_means_x_precedes_y() -> None:
    rng = np.random.default_rng(42)
    x = rng.normal(size=100)
    y = np.concatenate([np.zeros(2), x[:-2]])
    result = cross_correlation(x, y, max_lag=6)
    peak_lag = int(result.loc[result["correlation"].idxmax(), "lag"])
    assert peak_lag == 2


def test_synthetic_series_is_reproducible_and_var_split_is_chronological() -> None:
    first = generate_synthetic_timeseries(seed=101)
    second = generate_synthetic_timeseries(seed=101)
    pd.testing.assert_frame_equal(first, second)
    metrics, forecasts = conditional_var_demo(first)
    assert metrics["train_end_index"].max() < metrics["test_start_index"].min()
    assert forecasts["index"].min() == metrics["test_start_index"].min()
    assert np.isfinite(metrics["heldout_mse"]).all()
