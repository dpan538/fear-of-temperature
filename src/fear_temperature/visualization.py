# Matplotlib must see the project-local writable cache before it is imported.
# ruff: noqa: E402,I001
from __future__ import annotations

import os
from pathlib import Path

_MPL_CACHE = Path(__file__).resolve().parents[2] / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go

ROLE_COLOURS = {
    "policy_attention": "#386CB0",
    "media_attention": "#7FC97F",
    "public_emotion": "#F0027F",
}


def export_temporal_figure(frame: pd.DataFrame, output_dir: str | Path) -> list[Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
    labels = {
        "policy_attention": "Policy attention",
        "media_attention": "Media attention",
        "public_emotion": "Public emotion",
    }
    for column, colour in ROLE_COLOURS.items():
        axis.plot(frame["time"], frame[column], label=labels[column], color=colour, linewidth=1.8)
    transition_time = frame.loc[frame["channel_mix_shift"].gt(0), "time"].min()
    axis.axvline(transition_time, color="#A65628", linestyle="--", linewidth=1.3)
    axis.text(
        transition_time,
        axis.get_ylim()[1],
        " synthetic channel transition",
        color="#A65628",
        va="top",
        fontsize=9,
    )
    axis.set(
        title="Synthetic temporal interface check (not research results)",
        xlabel="Synthetic month",
        ylabel="Standardised synthetic value",
    )
    axis.legend(frameon=False, ncol=3, loc="lower left")
    axis.spines[["top", "right"]].set_visible(False)
    paths = [
        target / "synthetic_temporal_demo.png",
        target / "synthetic_temporal_demo.pdf",
        target / "synthetic_temporal_demo.svg",
    ]
    for path in paths:
        figure.savefig(path, dpi=220 if path.suffix == ".png" else None)
    plt.close(figure)
    return paths


def export_interactive_temporal(frame: pd.DataFrame, output_dir: str | Path) -> Path:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    figure = go.Figure()
    labels = {
        "policy_attention": "Policy attention",
        "media_attention": "Media attention",
        "public_emotion": "Public emotion",
    }
    for column, colour in ROLE_COLOURS.items():
        figure.add_trace(
            go.Scatter(
                x=frame["time"],
                y=frame[column],
                mode="lines",
                name=labels[column],
                line={"color": colour, "width": 2},
            )
        )
    figure.update_layout(
        title="Synthetic temporal interface check — not research results",
        xaxis_title="Synthetic month",
        yaxis_title="Standardised synthetic value",
        template="plotly_white",
        hovermode="x unified",
    )
    path = target / "synthetic_temporal_demo_interactive.html"
    figure.write_html(path, include_plotlyjs=True, full_html=True)
    return path
