from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from statsmodels.tsa.ar_model import AutoReg

AGGREGATION_COLUMNS = [
    "time",
    "publisher_role",
    "eligible_n",
    "relevant_n",
    "future_worry_n",
    "source_n",
    "attention_s",
    "emotion_e",
    "joint_b",
    "coverage_status",
]


def aggregate_role_time(
    passages: pd.DataFrame,
    frequency: str = "MS",
    roles: tuple[str, ...] = ("policy", "media", "public"),
    relevant_column: str = "fixture_relevant",
    emotion_column: str = "fixture_future_worry",
) -> pd.DataFrame:
    data = passages.copy()
    data["time"] = pd.to_datetime(data["publication_date"]).dt.to_period("M").dt.to_timestamp()
    if "weight" in data:
        data["eligible_weight"] = data["weight"].astype(float)
    else:
        data["eligible_weight"] = 1.0
    data["relevant_weight"] = data["eligible_weight"] * data[relevant_column].astype(float)
    data["emotion_weight"] = (
        data["eligible_weight"]
        * data[relevant_column].astype(float)
        * data[emotion_column].astype(float)
    )
    grouped = (
        data.groupby(["time", "publisher_role"], observed=True)
        .agg(
            eligible_n=("eligible_weight", "sum"),
            relevant_n=("relevant_weight", "sum"),
            future_worry_n=("emotion_weight", "sum"),
            source_n=("source_id", "nunique"),
        )
        .reset_index()
    )
    start = data["time"].min()
    end = data["time"].max()
    grid = pd.MultiIndex.from_product(
        [pd.date_range(start, end, freq=frequency), list(roles)],
        names=["time", "publisher_role"],
    ).to_frame(index=False)
    result = grid.merge(grouped, on=["time", "publisher_role"], how="left")
    for column in ["eligible_n", "relevant_n", "future_worry_n", "source_n"]:
        result[column] = result[column].fillna(0)

    observed = result["eligible_n"] > 0
    relevant = result["relevant_n"] > 0
    result["attention_s"] = np.where(observed, result["relevant_n"] / result["eligible_n"], np.nan)
    result["emotion_e"] = np.where(
        relevant, result["future_worry_n"] / result["relevant_n"], np.nan
    )
    result["joint_b"] = np.where(observed, result["future_worry_n"] / result["eligible_n"], np.nan)
    result["coverage_status"] = np.select(
        [~observed, observed & ~relevant, relevant],
        ["missing_no_eligible_units", "observed_zero_relevant", "observed_relevant"],
        default="invalid",
    )
    return (
        result[AGGREGATION_COLUMNS].sort_values(["time", "publisher_role"]).reset_index(drop=True)
    )


def generate_synthetic_timeseries(
    periods: int = 96, seed: int = 20260916, transition_index: int = 56
) -> pd.DataFrame:
    if periods < 60:
        raise ValueError("Temporal interface demo requires at least 60 synthetic periods")
    rng = np.random.default_rng(seed)
    time = pd.date_range("2012-01-01", periods=periods, freq="MS")
    policy = np.zeros(periods)
    for index in range(1, periods):
        shock = 0.6 if index in {24, 48, 72} else 0.0
        policy[index] = 0.72 * policy[index - 1] + shock + rng.normal(0, 0.11)
    media = np.zeros(periods)
    public = np.zeros(periods)
    for index in range(2, periods):
        media[index] = 0.45 * media[index - 1] + 0.55 * policy[index - 1] + rng.normal(0, 0.10)
        public[index] = 0.48 * public[index - 1] + 0.50 * media[index - 1] + rng.normal(0, 0.10)
    channel_shift = (np.arange(periods) >= transition_index).astype(float) * 0.22
    return pd.DataFrame(
        {
            "time": time,
            "policy_attention": policy,
            "media_attention": media,
            "public_emotion": public + channel_shift,
            "public_fixed_source": public,
            "channel_mix_shift": channel_shift,
            "data_status": "synthetic_interface_validation_not_research_result",
        }
    )


def cross_correlation(
    x: pd.Series | np.ndarray,
    y: pd.Series | np.ndarray,
    max_lag: int,
) -> pd.DataFrame:
    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    if len(x_values) != len(y_values):
        raise ValueError("CCF inputs must have equal length")
    rows = []
    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            x_aligned, y_aligned = x_values[:-lag], y_values[lag:]
        elif lag < 0:
            x_aligned, y_aligned = x_values[-lag:], y_values[:lag]
        else:
            x_aligned, y_aligned = x_values, y_values
        valid = np.isfinite(x_aligned) & np.isfinite(y_aligned)
        correlation = np.corrcoef(x_aligned[valid], y_aligned[valid])[0, 1]
        rows.append(
            {
                "lag": lag,
                "correlation": float(correlation),
                "n": int(valid.sum()),
                "definition": "positive lag means x precedes y",
            }
        )
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class ItsResult:
    coefficients: pd.DataFrame
    fitted: pd.DataFrame


def fit_segmented_its(values: pd.Series | np.ndarray, event_index: int) -> ItsResult:
    outcome = np.asarray(values, dtype=float)
    if event_index < 12 or len(outcome) - event_index < 12:
        raise ValueError("ITS demo requires at least 12 observations on both sides")
    centred = np.arange(len(outcome), dtype=float) - event_index
    intervention = (centred >= 0).astype(float)
    design = pd.DataFrame(
        {
            "intercept": 1.0,
            "time": centred,
            "intervention": intervention,
            "post_slope": centred * intervention,
        }
    )
    fitted = sm.OLS(outcome, design).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    coefficients = pd.DataFrame(
        {
            "term": fitted.params.index,
            "estimate": fitted.params.values,
            "std_error_hac": fitted.bse.values,
            "p_value": fitted.pvalues.values,
        }
    )
    fitted_values = pd.DataFrame(
        {"index": np.arange(len(outcome)), "observed": outcome, "fitted": fitted.fittedvalues}
    )
    return ItsResult(coefficients=coefficients, fitted=fitted_values)


def conditional_var_demo(
    frame: pd.DataFrame,
    columns: tuple[str, ...] = ("policy_attention", "media_attention", "public_emotion"),
    train_fraction: float = 0.75,
    lags: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = frame.loc[:, columns].astype(float).reset_index(drop=True)
    split = int(len(data) * train_fraction)
    if split <= lags * 5 or len(data) - split < 12:
        raise ValueError("Insufficient chronological observations for VAR demo")
    train, test = data.iloc[:split], data.iloc[split:]
    var_model = VAR(train).fit(maxlags=lags, ic=None, trend="ct")
    var_forecast = var_model.forecast(train.values[-var_model.k_ar :], steps=len(test))
    target = columns[-1]
    own_model = AutoReg(train[target], lags=lags, trend="ct").fit()
    own_forecast = own_model.predict(start=split, end=len(data) - 1, dynamic=False)
    actual = test[target].to_numpy()
    var_target = var_forecast[:, columns.index(target)]
    own_target = np.asarray(own_forecast)
    metrics = pd.DataFrame(
        {
            "model": ["own_history_autoreg", "conditional_var"],
            "heldout_mse": [
                float(np.mean((actual - own_target) ** 2)),
                float(np.mean((actual - var_target) ** 2)),
            ],
            "train_end_index": [split - 1, split - 1],
            "test_start_index": [split, split],
            "interpretation": [
                "synthetic predictive baseline; not causal evidence",
                "synthetic added-prediction candidate; not causal evidence",
            ],
        }
    )
    forecasts = pd.DataFrame(
        {
            "index": np.arange(split, len(data)),
            "actual_public_emotion": actual,
            "own_history_forecast": own_target,
            "conditional_var_forecast": var_target,
        }
    )
    return metrics, forecasts


def channel_transition_diagnostic(frame: pd.DataFrame, transition_index: int) -> pd.DataFrame:
    aggregate = fit_segmented_its(frame["public_emotion"], transition_index).coefficients
    fixed = fit_segmented_its(frame["public_fixed_source"], transition_index).coefficients
    aggregate.insert(0, "series", "aggregate_with_channel_mix")
    fixed.insert(0, "series", "fixed_source_subset")
    result = pd.concat([aggregate, fixed], ignore_index=True)
    result["interpretation"] = (
        "composition-bias diagnostic only; a discontinuity is not causal proof"
    )
    return result
