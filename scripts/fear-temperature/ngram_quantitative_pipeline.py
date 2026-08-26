#!/usr/bin/env python3
"""Retrieve and analyse the complete provisional Google Books Ngram baseline.

The pipeline executes every compatible rule from the 143-rule audit, caches one
raw response per unique surface form, checkpoints after every request, and keeps
zero/failure/non-executable states visible. Annual observations are always
requested with smoothing=0. Display smoothing is derived separately.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = ROOT / "data" / "fear-temperature" / "seed"
NGRAM_DIR = ROOT / "data" / "fear-temperature" / "ngram"
RAW_DIR = NGRAM_DIR / "raw"
ANALYSIS_DIR = ROOT / "data" / "fear-temperature" / "analysis"
EXPORT_DIR = ROOT / "data" / "fear-temperature" / "exports"
FIGURE_DIR = ROOT / "figures" / "fear-temperature"
SQL_PATH = ROOT / "db" / "seeds" / "004_ngram_quantitative.sql"

VERSION_ID = "fear-temperature-quant-v0.1-provisional"
PROVIDER = "Google Books Ngram Viewer"
CORPUS_ID = "eng"
CORPUS_VERSION = "current English corpus (July 2024 dataset; public shorthand eng; mutable current corpus)"
PERSISTENT_CORPUS_ID = "NOT_EXPOSED_FOR_CURRENT_ENG_IN_PUBLIC_CORPUS_TABLE"
YEAR_START = 1842
PROBE_START = 2019
PROBE_END = 2026
SMOOTHING = 0
CASE_INSENSITIVE = True
ENDPOINT = "https://books.google.com/ngrams/json"
INFO_URL = "https://books.google.com/ngrams/info"
RUN_ID = "FT-NGRAM-QUANT-V01-ENG"
USER_AGENT = "FearOfTemperatureQuantitativeBaseline/0.1 (provisional academic research)"

ANCHORS = [
    ("FT-A1842", "1842", 1842, 1842, 1839, 1845),
    ("FT-A1938", "1938", 1938, 1938, 1936, 1940),
    ("FT-A1988", "1988", 1988, 1988, 1986, 1990),
    ("FT-A0607", "2006–2007", 2006, 2007, 2005, 2008),
    ("FT-A2015", "2015", 2015, 2015, 2014, 2016),
    ("FT-A2022", "2022", 2022, 2022, 2021, 2023),
]

MANDATORY_SURFACES = [
    "climatic change", "climate change", "greenhouse effect", "global warming",
    "changing atmosphere", "climate system", "climate crisis", "climate emergency",
    "temperature", "mean temperature", "temperature increase", "global temperature",
    "global average temperature", "heat", "heat wave", "extreme heat", "fear",
    "afraid", "worry", "worried", "concern", "anxiety", "climate anxiety",
    "eco-anxiety", "distress", "psychological distress", "depressed", "danger",
    "threat", "risk", "crisis", "emergency", "damage", "loss and damage", "mortality",
]

COLORS = [
    "#0B6E75", "#C65D3B", "#6B5CA5", "#D49B28", "#2E7D4F", "#9A3F65",
    "#3D6FA3", "#A65F00", "#5B7F28", "#6A4C93",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def request_url(surface: str, year_start: int, year_end: int) -> str:
    params = {
        "content": surface,
        "year_start": str(year_start),
        "year_end": str(year_end),
        "corpus": CORPUS_ID,
        "smoothing": str(SMOOTHING),
        "case_insensitive": "true",
    }
    return ENDPOINT + "?" + urllib.parse.urlencode(params)


def fetch_json(url: str, attempts: int = 4, timeout: int = 60) -> tuple[bytes, list[dict[str, Any]], int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, list):
                    raise ValueError("Response is not a JSON list")
                return raw, payload, attempt, response.headers.get("Content-Type", "")
        except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(last_error)


def select_series(payload: list[dict[str, Any]]) -> dict[str, Any] | None:
    aggregates = [
        row for row in payload
        if row.get("type") == "CASE_INSENSITIVE" or str(row.get("ngram", "")).endswith("(All)")
    ]
    if aggregates:
        return aggregates[0]
    rows = [row for row in payload if isinstance(row.get("timeseries"), list)]
    return rows[0] if len(rows) == 1 else None


def verify_corpus(reuse_raw: bool) -> tuple[int, dict[str, Any]]:
    """Infer the live supported end year from a bounded recent-year probe."""
    probe_path = RAW_DIR / "_corpus_probe_2019_current.json"
    url = request_url("climate change", PROBE_START, PROBE_END)
    if reuse_raw and probe_path.exists():
        raw = probe_path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        attempts, content_type = 0, "application/json (cached probe)"
    else:
        raw, payload, attempts, content_type = fetch_json(url)
        probe_path.parent.mkdir(parents=True, exist_ok=True)
        probe_path.write_bytes(raw)
    selected = select_series(payload)
    if not selected:
        raise RuntimeError("Current English corpus probe returned no usable case-insensitive series")
    values = selected.get("timeseries", [])
    if not values:
        raise RuntimeError("Current English corpus probe returned an empty time series")
    end_year = PROBE_START + len(values) - 1
    if end_year < 2020 or end_year > PROBE_END:
        raise RuntimeError(f"Implausible corpus end year inferred from probe: {end_year}")
    metadata = {
        "probe_url": url,
        "probe_year_start": PROBE_START,
        "probe_year_end_requested": PROBE_END,
        "probe_observation_count": len(values),
        "inferred_supported_year_end": end_year,
        "probe_response_ngram": selected.get("ngram", ""),
        "probe_attempt_count": attempts,
        "probe_content_type": content_type,
        "raw_probe_path": str(probe_path.relative_to(ROOT)),
        "interface_release": "July 2024 new dataset",
        "ordinary_word_limit": 7,
        "persistent_current_eng_identifier": PERSISTENT_CORPUS_ID,
        "verification_note": "End year inferred from the length of a recent bounded live response; the interface truncates at the current supported corpus year.",
    }
    return end_year, metadata


def series_hash(surface: str, year_end: int) -> str:
    parameter = json.dumps({
        "surface": surface, "year_start": YEAR_START, "year_end": year_end,
        "corpus": CORPUS_ID, "smoothing": SMOOTHING, "case_insensitive": CASE_INSENSITIVE,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(parameter.encode("utf-8")).hexdigest()


def centered_mean(values: dict[int, float], year: int, radius: int = 3) -> float | None:
    selected = [values[y] for y in range(year - radius, year + radius + 1) if y in values]
    return statistics.fmean(selected) if selected else None


def complete_mean(values: dict[int, float], years: range) -> float | None:
    selected = [values[y] for y in years if y in values]
    return statistics.fmean(selected) if len(selected) == len(years) else None


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.16g}"


def stats_for_query(rule: dict[str, str], values: dict[int, float], year_end: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    nonzero = [year for year, value in values.items() if value > 0]
    peak_year = max(values, key=values.get) if values else None
    if not values:
        sparse = "NO_SERIES"
    elif not nonzero:
        sparse = "ZERO"
    elif len(nonzero) < 10:
        sparse = "SPARSE"
    else:
        sparse = "AVAILABLE"
    summary: dict[str, Any] = {
        "query_id": rule["query_id"],
        "surface_form": rule["surface_form"],
        "canonical_concept": rule["concept_label"],
        "lexical_family": rule["family_code"],
        "primary_layer": rule["primary_layer_code"],
        "query_classification": rule["query_classification"],
        "ambiguity_class": rule["interpretation_class"],
        "corpus": CORPUS_ID,
        "corpus_version": CORPUS_VERSION,
        "year_start": YEAR_START,
        "year_end": year_end,
        "first_nonzero_year": min(nonzero) if nonzero else "",
        "nonzero_year_count": len(nonzero),
        "peak_year": peak_year or "",
        "peak_frequency": fmt(values.get(peak_year) if peak_year else None),
        "latest_year_value": fmt(values.get(year_end)),
        "zero_sparse_flag": sparse,
        "trajectory_availability": "AVAILABLE" if values else "NOT_AVAILABLE",
        "interpretation_note": (
            "Generic corpus string frequency; not climate-specific semantic frequency."
            if rule["interpretation_class"] == "BACKGROUND_AMBIGUOUS"
            else "Climate/temperature-linked lexical frequency; still not evidence of reception, voice, or affect without passage review."
        ),
    }
    anchor_stats: list[dict[str, Any]] = []
    for anchor_id, anchor_label, strict_start, strict_end, context_start, context_end in ANCHORS:
        strict_years = [y for y in range(strict_start, strict_end + 1) if y in values]
        context_years = [y for y in range(context_start, context_end + 1) if y in values]
        strict_values = [values[y] for y in strict_years]
        context_values = [values[y] for y in context_years]
        row = {
            "query_id": rule["query_id"],
            "surface_form": rule["surface_form"],
            "family": rule["family_code"],
            "anchor_id": anchor_id,
            "anchor_label": anchor_label,
            "strict_start_year": strict_start,
            "strict_end_year": strict_end,
            "strict_start_value": fmt(values.get(strict_start)),
            "strict_end_value": fmt(values.get(strict_end)),
            "strict_window_mean": fmt(statistics.fmean(strict_values) if strict_values else None),
            "contextual_start_year": context_start,
            "contextual_end_year": context_end,
            "contextual_years_available": len(context_years),
            "contextual_window_mean": fmt(statistics.fmean(context_values) if context_values else None),
            "contextual_window_median": fmt(statistics.median(context_values) if context_values else None),
            "contextual_window_maximum": fmt(max(context_values) if context_values else None),
            "five_year_pre_anchor_mean": fmt(complete_mean(values, range(strict_start - 5, strict_start))),
            "five_year_post_anchor_mean": fmt(complete_mean(values, range(strict_end + 1, strict_end + 6))),
            "statistics_note": "Descriptive only; unavailable edge years are blank rather than imputed.",
        }
        anchor_stats.append(row)
        if anchor_id == "FT-A0607":
            summary["2006_value"] = fmt(values.get(2006))
            summary["2007_value"] = fmt(values.get(2007))
            summary["2006_07_mean"] = fmt(statistics.fmean(strict_values) if len(strict_values) == 2 else None)
        else:
            summary[f"{strict_start}_value"] = fmt(values.get(strict_start))
    summary["2022_or_latest_value"] = fmt(values.get(year_end))
    summary["latest_supported_year"] = year_end
    return summary, anchor_stats


def build_family_summary(
    rules: list[dict[str, str]],
    series: dict[str, dict[int, float]],
    summaries: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for rule in rules:
        by_family[rule["family_code"]].append(rule)
    result = []
    for family in sorted(by_family):
        members = by_family[family]
        successful = [rule for rule in members if rule["query_id"] in series]
        sparse = [rule for rule in successful if summaries[rule["query_id"]]["zero_sparse_flag"] in {"ZERO", "SPARSE"}]
        first_members = [
            (int(summaries[rule["query_id"]]["first_nonzero_year"]), rule["surface_form"])
            for rule in successful if summaries[rule["query_id"]]["first_nonzero_year"] != ""
        ]
        peaks = sorted(
            successful,
            key=lambda rule: float(summaries[rule["query_id"]]["peak_frequency"] or 0),
            reverse=True,
        )
        peak_notes = [
            f"{rule['surface_form']}:{summaries[rule['query_id']]['peak_year']}"
            for rule in successful
        ]
        result.append({
            "family_id": members[0]["family_id"],
            "family_code": family,
            "members_queried": " | ".join(dict.fromkeys(rule["surface_form"] for rule in members)),
            "query_rule_count": len(members),
            "members_successful": len(successful),
            "members_sparse_or_zero": len(sparse),
            "earliest_observable_member": f"{min(first_members)[1]} ({min(first_members)[0]})" if first_members else "",
            "representative_terms_by_peak_frequency": " | ".join(rule["surface_form"] for rule in peaks[:3]),
            "member_peak_years": " | ".join(peak_notes),
            "anchor_period_notes": "Compare member trajectories and anchor values individually; no family total is computed.",
            "semantic_comparability_warning": "Semantic family is not a synonym set. Overlapping and differently scoped strings are never summed.",
        })
    return result


def load_fonts() -> dict[str, ImageFont.ImageFont]:
    regular = [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Helvetica.ttf"),
    ]
    bold = [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Helvetica Bold.ttf"),
    ]

    def font(paths: list[Path], size: int) -> ImageFont.ImageFont:
        for path in paths:
            if path.exists():
                return ImageFont.truetype(str(path), size)
        return ImageFont.load_default()

    return {
        "title": font(bold, 50), "subtitle": font(regular, 25), "panel": font(bold, 26),
        "axis": font(regular, 18), "legend": font(regular, 20), "small": font(regular, 17),
    }


def tick(value: float) -> str:
    if value >= 1000:
        return f"{value:,.0f}"
    if value >= 10:
        return f"{value:.1f}"
    if value >= 1:
        return f"{value:.2f}"
    if value >= 0.01:
        return f"{value:.3f}"
    return f"{value:.4f}"


def draw_panel(
    image: Image.Image,
    box: tuple[int, int, int, int],
    title: str,
    entries: list[tuple[str, dict[int, float]]],
    start: int,
    end: int,
    shared_lines: bool,
) -> None:
    draw = ImageDraw.Draw(image)
    fonts = load_fonts()
    left, top, right, bottom = box
    draw.text((left, top - 34), title, font=fonts["panel"], fill="#17324D")
    plot_left, plot_top, plot_right, plot_bottom = left + 90, top, right - 25, bottom - 48
    draw.rectangle((plot_left, plot_top, plot_right, plot_bottom), fill="#FCFDFE", outline="#C9D4DF", width=2)
    visible = [v * 1_000_000 for _, values in entries for y, v in values.items() if start <= y <= end]
    ymax = max(visible, default=1.0) * 1.08 or 1.0
    for step in range(5):
        value = ymax * step / 4
        y = plot_bottom - (plot_bottom - plot_top) * step / 4
        draw.line((plot_left, y, plot_right, y), fill="#E6EBF0")
        label = tick(value)
        bb = draw.textbbox((0, 0), label, font=fonts["axis"])
        draw.text((plot_left - 12 - (bb[2] - bb[0]), y - 10), label, font=fonts["axis"], fill="#52606D")
    ticks = sorted(set([start, end] + [y for y in (1880, 1920, 1960, 1980, 2000, 2010, 2020) if start < y < end]))
    if len(ticks) > 7:
        ticks = ticks[::2] + ([end] if ticks[-1] != end else [])
    for year in ticks:
        x = plot_left + (plot_right - plot_left) * (year - start) / max(1, end - start)
        draw.line((x, plot_bottom, x, plot_bottom + 6), fill="#52606D", width=2)
        label = str(year)
        bb = draw.textbbox((0, 0), label, font=fonts["axis"])
        draw.text((x - (bb[2] - bb[0]) / 2, plot_bottom + 10), label, font=fonts["axis"], fill="#52606D")
    for index, (label, values) in enumerate(entries):
        color = COLORS[index % len(COLORS)]
        raw, smooth = [], []
        for year in range(start, end + 1):
            if year not in values:
                continue
            x = plot_left + (plot_right - plot_left) * (year - start) / max(1, end - start)
            raw_v = values[year] * 1_000_000
            raw.append((x, plot_bottom - (plot_bottom - plot_top) * raw_v / ymax))
            sm = centered_mean(values, year, 3)
            if sm is not None:
                smooth.append((x, plot_bottom - (plot_bottom - plot_top) * (sm * 1_000_000) / ymax))
        if len(raw) > 1:
            draw.line(raw, fill=color + "66", width=2)
        if len(smooth) > 1:
            draw.line(smooth, fill=color, width=4)
        if shared_lines:
            ly = plot_top + 14 + index * 27
            draw.line((plot_left + 15, ly + 8, plot_left + 45, ly + 8), fill=color, width=4)
            draw.text((plot_left + 55, ly - 2), label, font=fonts["legend"], fill="#243B53")
    draw.text((left + 6, plot_top + 8), "per million", font=fonts["small"], fill="#52606D")


def save_line_figure(
    filename: str,
    title: str,
    subtitle: str,
    panels: list[tuple[str, list[tuple[str, dict[int, float]]], int, int]],
    caution: str,
) -> None:
    panel_height = 370
    height = 210 + panel_height * len(panels) + 90
    image = Image.new("RGB", (1800, height), "#F4F7FA")
    draw = ImageDraw.Draw(image)
    fonts = load_fonts()
    draw.text((70, 42), title, font=fonts["title"], fill="#102A43")
    draw.text((72, 108), subtitle, font=fonts["subtitle"], fill="#486581")
    top = 205
    for panel_title, entries, start, end in panels:
        draw_panel(image, (65, top, 1740, top + panel_height - 25), panel_title, entries, start, end, len(entries) > 1)
        top += panel_height
    draw.text((72, height - 48), caution, font=fonts["small"], fill="#7B341E")
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    image.save(FIGURE_DIR / filename, optimize=True)


def write_figure_source(filename: str, entries: list[tuple[str, str, dict[int, float]]], start: int) -> None:
    rows = []
    for query_id, surface, values in entries:
        for year in sorted(y for y in values if y >= start):
            rows.append({
                "query_id": query_id, "surface_form": surface, "year": year,
                "raw_normalized_frequency": fmt(values[year]),
                "smoothed_radius_3_frequency": fmt(centered_mean(values, year, 3)),
                "raw_scale": "normalized share", "display_scale": "normalized share × 1,000,000",
            })
    write_csv(FIGURE_DIR / filename, rows, [
        "query_id", "surface_form", "year", "raw_normalized_frequency",
        "smoothed_radius_3_frequency", "raw_scale", "display_scale",
    ])


def save_emergence_timeline(entries: list[tuple[str, int]]) -> None:
    entries = sorted(entries, key=lambda item: item[1])
    height = max(700, 190 + 42 * len(entries))
    image = Image.new("RGB", (1800, height), "#F4F7FA")
    draw = ImageDraw.Draw(image)
    fonts = load_fonts()
    draw.text((70, 40), "Corpus-observed emergence of climate-specific phrases", font=fonts["title"], fill="#102A43")
    draw.text((72, 108), "First non-zero year in the 1842–2022 current-English Ngram interval", font=fonts["subtitle"], fill="#486581")
    x0, x1, top = 510, 1700, 190
    draw.line((x0, top - 15, x1, top - 15), fill="#A9B7C6", width=2)
    for year in (1842, 1880, 1920, 1960, 1980, 2000, 2022):
        x = x0 + (x1 - x0) * (year - 1842) / (2022 - 1842)
        draw.line((x, top - 22, x, height - 70), fill="#E1E7ED")
        draw.text((x - 22, top - 55), str(year), font=fonts["axis"], fill="#52606D")
    for i, (surface, year) in enumerate(entries):
        y = top + i * 42
        x = x0 + (x1 - x0) * (year - 1842) / (2022 - 1842)
        draw.text((70, y - 11), surface, font=fonts["legend"], fill="#243B53")
        draw.line((x0, y, x, y), fill="#BFD1D8", width=3)
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill="#0B6E75")
        draw.text((x + 14, y - 11), str(year), font=fonts["legend"], fill="#17324D")
    draw.text((72, height - 44), "Corpus-observed presence is not historical coinage; OCR and the ≥40-book inclusion threshold affect observability.", font=fonts["small"], fill="#7B341E")
    image.save(FIGURE_DIR / "figure_06_emergence_timeline.png", optimize=True)


def save_anchor_heatmap(rows: list[dict[str, Any]]) -> None:
    labels = [r["surface_form"] for r in rows]
    columns = ["1842_value", "1938_value", "1988_value", "2006_value", "2007_value", "2015_value", "2022_or_latest_value"]
    col_labels = ["1842", "1938", "1988", "2006", "2007", "2015", "2022"]
    cell_w, cell_h = 135, 34
    width, height = 800 + cell_w * len(columns), 200 + cell_h * len(rows)
    image = Image.new("RGB", (width, height), "#F4F7FA")
    draw = ImageDraw.Draw(image)
    fonts = load_fonts()
    draw.text((45, 28), "Anchor heatmap — row-normalized display", font=fonts["title"], fill="#102A43")
    draw.text((47, 92), "Each keyword is normalized to its own maximum; colors are not raw corpus frequencies", font=fonts["subtitle"], fill="#486581")
    x0, y0 = 690, 150
    for j, label in enumerate(col_labels):
        draw.text((x0 + j * cell_w + 34, y0 - 31), label, font=fonts["legend"], fill="#243B53")
    for i, row in enumerate(rows):
        y = y0 + i * cell_h
        draw.text((45, y + 5), row["surface_form"][:52], font=fonts["axis"], fill="#243B53")
        values = [float(row.get(column) or 0) for column in columns]
        maximum = max(values) if values else 0
        for j, value in enumerate(values):
            ratio = value / maximum if maximum > 0 else 0
            base = (235, 244, 247)
            strong = (11, 110, 117)
            color = tuple(round(base[k] + ratio * (strong[k] - base[k])) for k in range(3))
            draw.rectangle((x0 + j * cell_w, y, x0 + (j + 1) * cell_w - 3, y + cell_h - 3), fill=color)
            draw.text((x0 + j * cell_w + 50, y + 5), f"{ratio:.2f}", font=fonts["axis"], fill="#FFFFFF" if ratio > 0.55 else "#17324D")
    draw.text((47, height - 38), "Use anchor_keyword_frequency_matrix.csv for raw normalized values.", font=fonts["small"], fill="#7B341E")
    image.save(FIGURE_DIR / "figure_07_anchor_heatmap_row_normalized.png", optimize=True)


def sql_literal(value: Any) -> str:
    if value is None or value == "":
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def write_sql(
    year_end: int,
    retrieved_at: str,
    parameter_hash: str,
    run_status: str,
    probe: dict[str, Any],
    executions: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> None:
    metadata = json.dumps({
        "provider_info_url": INFO_URL,
        "corpus_probe": probe,
        "persistent_identifier": PERSISTENT_CORPUS_ID,
        "ordinary_word_limit": 7,
        "method": "one exact string/phrase per request; case-insensitive aggregate; smoothing=0",
    }, ensure_ascii=False)
    lines = [
        "BEGIN;", "SET search_path = fear_temperature, public;", "",
        "INSERT INTO query_run (query_run_id, research_version_id, provider, corpus_identifier, corpus_version_label, year_start, year_end, retrieval_smoothing, case_insensitive, parameter_set_hash, retrieved_at, endpoint_url, status, raw_response_path, response_metadata) VALUES ("
        + ", ".join([
            sql_literal(RUN_ID), sql_literal(VERSION_ID), sql_literal(PROVIDER), sql_literal(CORPUS_ID), sql_literal(CORPUS_VERSION),
            str(YEAR_START), str(year_end), "0", "true", sql_literal(parameter_hash), sql_literal(retrieved_at), sql_literal(ENDPOINT),
            sql_literal(run_status), sql_literal("data/fear-temperature/ngram/raw"), sql_literal(metadata) + "::jsonb",
        ]) + ") ON CONFLICT DO NOTHING;", "",
    ]
    execution_fields = [
        "query_run_id", "query_id", "request_surface_form", "execution_status", "attempt_count", "observation_count",
        "first_response_ngram", "raw_response_path", "raw_payload_sha256", "error_reason", "retrieved_at", "response_metadata",
    ]
    for row in executions:
        values = [RUN_ID, row["query_id"], row["request_surface_form"], row["execution_status"], int(row["attempt_count"]), int(row["observation_count"]), row.get("first_response_ngram", ""), row.get("raw_response_path", ""), row.get("raw_payload_sha256", ""), row.get("error_reason", ""), row.get("retrieved_at", ""), json.dumps({"request_url": row.get("request_url", "")}, ensure_ascii=False)]
        rendered = [str(v) if i in {4, 5} else sql_literal(v) + ("::jsonb" if i == 11 else "") for i, v in enumerate(values)]
        lines.append(f"INSERT INTO query_execution_result ({', '.join(execution_fields)}) VALUES ({', '.join(rendered)}) ON CONFLICT DO NOTHING;")
    lines.append("")
    observation_fields = [
        "frequency_observation_id", "query_run_id", "research_version_id", "query_id", "lexical_form_id", "concept_id", "family_id",
        "provider", "corpus_identifier", "corpus_version_label", "surface_form", "response_ngram", "year", "normalized_frequency",
        "retrieval_smoothing", "parameter_set_hash", "retrieved_at", "raw_response_path", "raw_payload_sha256",
    ]
    for row in observations:
        values = [
            f"FT-FREQ-{row['query_id']}-{row['year']}", RUN_ID, VERSION_ID, row["query_id"], row["lexical_form_id"], row["concept_id"], row["family_id"],
            PROVIDER, CORPUS_ID, CORPUS_VERSION, row["term"], row["response_ngram"], int(row["year"]), row["normalized_frequency"],
            0, parameter_hash, row["retrieved_at"], row["raw_response_path"], row["raw_payload_sha256"],
        ]
        rendered = [str(v) if i in {12, 13, 14} else sql_literal(v) for i, v in enumerate(values)]
        lines.append(f"INSERT INTO frequency_observation ({', '.join(observation_fields)}) VALUES ({', '.join(rendered)}) ON CONFLICT DO NOTHING;")
    lines.extend(["", "COMMIT;", ""])
    SQL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQL_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-raw", action="store_true", help="Build outputs from cached raw responses without new requests.")
    parser.add_argument("--throttle", type=float, default=0.30, help="Seconds between unique-surface requests.")
    args = parser.parse_args()

    for path in (NGRAM_DIR, RAW_DIR, ANALYSIS_DIR, EXPORT_DIR, FIGURE_DIR):
        path.mkdir(parents=True, exist_ok=True)
    retrieved_at = utc_now()
    year_end, probe = verify_corpus(args.reuse_raw)
    rules = read_csv(SEED_DIR / "query_rules.csv")
    rule_by_id = {rule["query_id"]: rule for rule in rules}
    parameter_hash = hashlib.sha256(json.dumps({
        "provider": PROVIDER, "corpus": CORPUS_ID, "corpus_version": CORPUS_VERSION,
        "year_start": YEAR_START, "year_end": year_end, "smoothing": 0, "case_insensitive": True,
    }, sort_keys=True).encode("utf-8")).hexdigest()

    surface_cache: dict[str, dict[str, Any]] = {}
    executions: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    series_by_query: dict[str, dict[int, float]] = {}
    checkpoint_path = NGRAM_DIR / "checkpoint.json"

    eligible_rules = [rule for rule in rules if rule["ngram_execution_eligible"] == "True"]
    for index, rule in enumerate(rules, 1):
        query_id = rule["query_id"]
        surface = rule["surface_form"]
        if rule["ngram_execution_eligible"] != "True":
            executions.append({
                "query_id": query_id, "request_surface_form": surface,
                "execution_status": "NOT_RUN_INCOMPATIBLE", "attempt_count": 0, "observation_count": 0,
                "error_reason": rule["ngram_compatibility_reason"], "retrieved_at": "",
            })
            continue
        cache_key = series_hash(surface, year_end)
        raw_path = RAW_DIR / f"{cache_key}.json"
        url = request_url(surface, YEAR_START, year_end)
        try:
            if cache_key in surface_cache:
                fetched = surface_cache[cache_key]
            else:
                if raw_path.exists():
                    raw = raw_path.read_bytes()
                    payload = json.loads(raw.decode("utf-8"))
                    attempts, content_type = 0, "application/json (cached)"
                elif args.reuse_raw:
                    raise FileNotFoundError(f"Missing cached response: {raw_path}")
                else:
                    raw, payload, attempts, content_type = fetch_json(url)
                    raw_path.write_bytes(raw)
                    time.sleep(args.throttle)
                raw_sha = hashlib.sha256(raw).hexdigest()
                selected = select_series(payload)
                fetched = {
                    "raw": raw, "payload": payload, "attempts": attempts, "content_type": content_type,
                    "raw_sha": raw_sha, "selected": selected,
                }
                surface_cache[cache_key] = fetched
            selected = fetched["selected"]
            if selected is None:
                status, values, response_ngram = "ZERO_RESULT", {}, ""
            else:
                ts = selected.get("timeseries", [])
                expected = year_end - YEAR_START + 1
                if len(ts) != expected:
                    raise ValueError(f"Expected {expected} annual values, received {len(ts)}")
                values = {YEAR_START + offset: float(value) for offset, value in enumerate(ts)}
                response_ngram = str(selected.get("ngram", surface))
                status = "ZERO_RESULT" if not any(value > 0 for value in values.values()) else "SUCCEEDED"
                series_by_query[query_id] = values
                for year, value in values.items():
                    observations.append({
                        "query_id": query_id, "term": surface, "family": rule["family_code"],
                        "family_id": rule["family_id"], "lexical_form_id": rule["lexical_form_id"],
                        "concept_id": rule["concept_id"], "year": year,
                        "normalized_frequency": f"{value:.20g}", "corpus": CORPUS_ID,
                        "version": CORPUS_VERSION, "response_ngram": response_ngram,
                        "retrieval_smoothing": 0, "retrieved_at": retrieved_at,
                        "raw_response_path": str(raw_path.relative_to(ROOT)),
                        "raw_payload_sha256": fetched["raw_sha"], "parameter_set_hash": parameter_hash,
                    })
            executions.append({
                "query_id": query_id, "request_surface_form": surface, "execution_status": status,
                "attempt_count": fetched["attempts"], "observation_count": len(values),
                "first_response_ngram": response_ngram, "raw_response_path": str(raw_path.relative_to(ROOT)),
                "raw_payload_sha256": fetched["raw_sha"], "error_reason": "", "retrieved_at": retrieved_at,
                "request_url": url, "content_type": fetched["content_type"],
            })
        except Exception as exc:
            executions.append({
                "query_id": query_id, "request_surface_form": surface, "execution_status": "FAILED",
                "attempt_count": 4, "observation_count": 0, "error_reason": f"{type(exc).__name__}: {exc}",
                "retrieved_at": utc_now(), "request_url": url,
            })
        checkpoint_path.write_text(json.dumps({
            "last_query_id": query_id, "processed_rules": index, "total_rules": len(rules),
            "unique_surfaces_cached": len(surface_cache), "updated_at": utc_now(),
        }, indent=2) + "\n", encoding="utf-8")
        if index % 10 == 0:
            print(f"checkpoint {index}/{len(rules)} cached_surfaces={len(surface_cache)}", flush=True)

    execution_fields = [
        "query_id", "request_surface_form", "execution_status", "attempt_count", "observation_count",
        "first_response_ngram", "raw_response_path", "raw_payload_sha256", "error_reason", "retrieved_at",
        "request_url", "content_type",
    ]
    write_csv(NGRAM_DIR / "ngram_query_execution_results.csv", executions, execution_fields)
    observation_fields = [
        "query_id", "term", "family", "year", "normalized_frequency", "corpus", "version",
        "response_ngram", "retrieval_smoothing", "retrieved_at", "raw_response_path",
        "raw_payload_sha256", "parameter_set_hash", "lexical_form_id", "concept_id", "family_id",
    ]
    write_csv(NGRAM_DIR / "ngram_timeseries_full.csv", observations, observation_fields)
    write_csv(NGRAM_DIR / "ngram_timeseries.csv", observations, observation_fields)

    summaries_list: list[dict[str, Any]] = []
    anchor_stats: list[dict[str, Any]] = []
    summary_by_id: dict[str, dict[str, Any]] = {}
    for rule in rules:
        summary, stats = stats_for_query(rule, series_by_query.get(rule["query_id"], {}), year_end)
        summary_by_id[rule["query_id"]] = summary
        summaries_list.append(summary)
        anchor_stats.extend(stats)
    summary_fields = [
        "query_id", "surface_form", "canonical_concept", "lexical_family", "primary_layer",
        "query_classification", "ambiguity_class", "corpus", "corpus_version", "year_start", "year_end",
        "first_nonzero_year", "nonzero_year_count", "peak_year", "peak_frequency", "latest_year_value",
        "1842_value", "1938_value", "1988_value", "2006_value", "2007_value", "2006_07_mean",
        "2015_value", "2022_value", "2022_or_latest_value", "latest_supported_year",
        "zero_sparse_flag", "trajectory_availability", "interpretation_note",
    ]
    write_csv(EXPORT_DIR / "keyword_frequency_summary.csv", summaries_list, summary_fields)
    write_csv(ANALYSIS_DIR / "ngram_anchor_statistics.csv", anchor_stats, list(anchor_stats[0].keys()))

    matrix_rows = [{
        "query_id": row["query_id"], "surface_form": row["surface_form"],
        "family": row["lexical_family"], "interpretation_class": row["ambiguity_class"],
        "1842_value": row.get("1842_value", ""), "1938_value": row.get("1938_value", ""),
        "1988_value": row.get("1988_value", ""), "2006_value": row.get("2006_value", ""),
        "2007_value": row.get("2007_value", ""), "2006_07_mean": row.get("2006_07_mean", ""),
        "2015_value": row.get("2015_value", ""), "2022_or_latest_value": row.get("2022_or_latest_value", ""),
        "latest_supported_year": year_end,
    } for row in summaries_list]
    matrix_fields = list(matrix_rows[0].keys())
    write_csv(EXPORT_DIR / "anchor_keyword_frequency_matrix.csv", matrix_rows, matrix_fields)

    stats_by_query_anchor = {(r["query_id"], r["anchor_id"]): r for r in anchor_stats}
    contextual_rows = []
    for rule in rules:
        row = {"query_id": rule["query_id"], "surface_form": rule["surface_form"], "family": rule["family_code"]}
        for anchor_id, label, *_ in ANCHORS:
            slug = "2006_07" if anchor_id == "FT-A0607" else label
            stats = stats_by_query_anchor[(rule["query_id"], anchor_id)]
            row[f"{slug}_contextual_mean"] = stats["contextual_window_mean"]
            row[f"{slug}_contextual_median"] = stats["contextual_window_median"]
            row[f"{slug}_contextual_maximum"] = stats["contextual_window_maximum"]
        contextual_rows.append(row)
    write_csv(EXPORT_DIR / "anchor_keyword_contextual_matrix.csv", contextual_rows, list(contextual_rows[0].keys()))

    family_rows = build_family_summary(rules, series_by_query, summary_by_id)
    write_csv(EXPORT_DIR / "lexical_family_frequency_summary.csv", family_rows, list(family_rows[0].keys()))

    metadata_rows = []
    execution_by_id = {row["query_id"]: row for row in executions}
    for rule in rules:
        execution = execution_by_id[rule["query_id"]]
        metadata_rows.append({
            **{key: rule[key] for key in [
                "query_id", "surface_form", "anchor_id", "concept_id", "concept_label", "family_id", "family_code",
                "query_classification", "interpretation_class", "ngram_compatibility_status", "ngram_execution_eligible",
                "ngram_compatibility_reason", "source_report", "source_page", "provenance_status",
            ]},
            "provider": PROVIDER, "corpus_identifier": CORPUS_ID, "corpus_version": CORPUS_VERSION,
            "year_start": YEAR_START, "year_end": year_end, "smoothing": 0,
            "case_insensitive": True, "retrieved_at": retrieved_at,
            "execution_status": execution["execution_status"], "observation_count": execution["observation_count"],
            "raw_response_path": execution.get("raw_response_path", ""), "failure_reason": execution.get("error_reason", ""),
        })
    write_csv(NGRAM_DIR / "ngram_query_metadata.csv", metadata_rows, list(metadata_rows[0].keys()))

    # Select the first successful anchor-specific rule for each distinct surface.
    unique: dict[str, tuple[str, str, dict[int, float]]] = {}
    for rule in rules:
        norm = rule["normalized_form"]
        if norm not in unique and rule["query_id"] in series_by_query:
            unique[norm] = (rule["query_id"], rule["surface_form"], series_by_query[rule["query_id"]])

    def entries(terms: list[str]) -> list[tuple[str, str, dict[int, float]]]:
        return [unique[term] for term in terms if term in unique]

    figure_specs = [
        ("figure_01_climate_framing.png", "Climate framing vocabulary", "Current English Ngram corpus · raw annual values plus radius-3 display smoothing",
         [("Climate-specific framing, 1842–2022", entries(["climatic change", "greenhouse effect", "global warming", "climate change"]), 1842, year_end)],
         "Lexical frequency is descriptive; anchor years are not causal interventions."),
        ("figure_02_temperature_heat.png", "Temperature and heat vocabulary", "Independent panels avoid forcing broad and constrained strings onto one scale",
         [
             ("Broad background strings", entries(["temperature", "heat"]), 1842, year_end),
             ("Mean-temperature usage", entries(["mean temperature"]), 1842, year_end),
             ("More constrained temperature and heat phrases", entries(["temperature increase", "global temperature", "global average temperature", "heat wave", "extreme heat"]), 1842, year_end),
         ],
         "Broad temperature/heat strings are semantically ambiguous; passage context is required."),
        ("figure_03_threat_risk.png", "Threat and risk vocabulary", "Independent y-scales; generic string frequencies are background controls",
         [
             ("Danger and threat", entries(["danger", "threat"]), 1842, year_end),
             ("Risk", entries(["risk"]), 1842, year_end),
             ("Crisis, emergency and damage", entries(["crisis", "emergency", "damage"]), 1842, year_end),
             ("Loss-and-damage and mortality phrases", entries(["loss and damage", "mortality"]), 1842, year_end),
         ],
         "Threat and risk are not emotions. Generic curves do not measure climate threat or fear."),
        ("figure_04_affect.png", "Affect vocabulary", "Independent y-scales separate broad affect strings",
         [
             ("Fear / afraid", entries(["fear", "afraid"]), 1842, year_end),
             ("Worry / worried", entries(["worry", "worried"]), 1842, year_end),
             ("Concern / anxiety", entries(["concern", "anxiety"]), 1842, year_end),
             ("Distress / depressed", entries(["distress", "depressed"]), 1842, year_end),
         ],
         "Generic affect-string frequency is not historical climate affect."),
        ("figure_05_modern_climate_compounds.png", "Modern climate-specific affect and threat compounds", "Detail view of usable returned series",
         [("Climate-specific compounds, 1970–2022", entries(["climate anxiety", "eco-anxiety", "climate crisis", "climate emergency"]), 1970, year_end)],
         "Research constructs, crisis frames, declarations, and participant affect remain distinct."),
    ]
    for filename, title, subtitle, raw_panels, caution in figure_specs:
        panels = [(p_title, [(surface, vals) for _, surface, vals in p_entries], start, end) for p_title, p_entries, start, end in raw_panels if p_entries]
        if panels:
            save_line_figure(filename, title, subtitle, panels, caution)
            source_entries = [item for _, p_entries, _, _ in raw_panels for item in p_entries]
            write_figure_source(filename.replace(".png", "_source.csv"), source_entries, min(p[2] for p in raw_panels if p[1]))

    emergence = []
    for term in ["climatic change", "greenhouse effect", "global warming", "climate change", "climate crisis", "climate emergency", "climate anxiety", "eco-anxiety"]:
        if term in unique:
            query_id, surface, _ = unique[term]
            first = summary_by_id[query_id]["first_nonzero_year"]
            if first != "":
                emergence.append((surface, int(first)))
    if emergence:
        save_emergence_timeline(emergence)
        write_csv(FIGURE_DIR / "figure_06_emergence_timeline_source.csv", [{"surface_form": s, "first_nonzero_year": y, "note": "Corpus-observed presence, not historical coinage."} for s, y in emergence], ["surface_form", "first_nonzero_year", "note"])

    heatmap_by_surface: dict[str, dict[str, Any]] = {}
    heatmap_terms = set(MANDATORY_SURFACES[:16] + ["fear", "worry", "anxiety", "risk", "threat"])
    for row in matrix_rows:
        normalized_surface = row["surface_form"].casefold()
        if normalized_surface in heatmap_terms and normalized_surface not in heatmap_by_surface:
            heatmap_by_surface[normalized_surface] = row
    heatmap_rows = list(heatmap_by_surface.values())
    if heatmap_rows:
        save_anchor_heatmap(heatmap_rows)

    # One compact family figure where at least one usable series exists.
    for family_row in family_rows:
        family = family_row["family_code"]
        candidates = []
        seen = set()
        for rule in rules:
            if rule["family_code"] != family or rule["query_id"] not in series_by_query or rule["normalized_form"] in seen:
                continue
            seen.add(rule["normalized_form"])
            candidates.append((rule["query_id"], rule["surface_form"], series_by_query[rule["query_id"]]))
        candidates.sort(key=lambda item: max(item[2].values(), default=0), reverse=True)
        candidates = candidates[:4]
        if not candidates:
            continue
        filename = f"family_{family}.png"
        save_line_figure(
            filename, f"Family: {family.replace('_', ' ')}", "Representative member trajectories; no family total or index",
            [("Selected members", [(surface, values) for _, surface, values in candidates], YEAR_START, year_end)],
            "Members differ in sense and scope. Overlapping normalized frequencies are never summed.",
        )
        write_figure_source(filename.replace(".png", "_source.csv"), candidates, YEAR_START)

    counts = Counter(row["execution_status"] for row in executions)
    run_status = "SUCCEEDED" if counts["FAILED"] == 0 else ("PARTIAL" if counts["SUCCEEDED"] or counts["ZERO_RESULT"] else "FAILED")
    run_metadata = {
        "research_version": VERSION_ID, "provider": PROVIDER, "provider_info_url": INFO_URL,
        "endpoint": ENDPOINT, "corpus_identifier": CORPUS_ID, "corpus_version": CORPUS_VERSION,
        "persistent_current_corpus_identifier": PERSISTENT_CORPUS_ID,
        "year_start": YEAR_START, "year_end": year_end, "retrieval_smoothing": 0,
        "case_insensitive": True, "retrieved_at": retrieved_at, "parameter_set_hash": parameter_hash,
        "query_rule_count": len(rules), "ngram_eligible_count": len(eligible_rules),
        "execution_counts": counts, "annual_observation_count": len(observations),
        "unique_surface_request_count": len(surface_cache), "corpus_probe": probe,
        "method_note": "Raw annual normalized values retained; radius-3 smoothing exists only in figure-source CSVs.",
        "interpretation_warning": "Generic string frequency is not climate-specific semantic frequency; voice and meaning require passage-level validation.",
    }
    (NGRAM_DIR / "ngram_run_metadata.json").write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False, default=dict) + "\n", encoding="utf-8")
    write_sql(year_end, retrieved_at, parameter_hash, run_status, probe, executions, observations)
    print(
        f"NGRAM_STATUS={run_status} corpus={CORPUS_ID} years={YEAR_START}-{year_end} "
        f"rules={len(rules)} eligible={len(eligible_rules)} success={counts['SUCCEEDED']} "
        f"zero={counts['ZERO_RESULT']} failed={counts['FAILED']} observations={len(observations)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
