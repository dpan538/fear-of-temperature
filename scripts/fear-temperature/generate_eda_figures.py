#!/usr/bin/env python3
"""Generate reproducible EDA figures as PNG + SVG with source tables."""

from __future__ import annotations

import csv
import html
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "fear-temperature"
ANALYSIS = DATA / "analysis"
OUT = ROOT / "figures" / "fear-temperature" / "eda-v02"
SOURCES = OUT / "sources"
OUT.mkdir(parents=True, exist_ok=True)
SOURCES.mkdir(parents=True, exist_ok=True)

W, H = 1600, 920
BG = "#F7F8FA"
INK = "#172033"
MUTED = "#5C667A"
GRID = "#D9DEE8"
WHITE = "#FFFFFF"
ACCENT = "#D95D39"
PALETTE = ["#2457A7", "#2A9D8F", "#E9C46A", "#E76F51", "#7B61A8", "#4D908E", "#F8961E", "#577590"]
LAYER_COLORS = {"A": "#2457A7", "B": "#2A9D8F", "C": "#E76F51", "D": "#7B61A8"}
VOICE_COLORS = {"V1": "#2457A7", "V2": "#2A9D8F", "V3": "#E9C46A", "V4": "#E76F51", "V5": "#7B61A8"}
STATUS_COLORS = {
    "COMPLETE": "#2A9D8F", "DIRECT_HEADWORD": "#2457A7", "TECHNICAL_GLOSSARY": "#2A9D8F",
    "NO_STANDALONE_HEADWORD": "#E9C46A", "UNRESOLVED": "#D95D39", "ZERO_RESULT": "#E76F51",
    "NOT_APPLICABLE": "#A7AFBE", "NOT_EXPOSED": "#E9C46A", "NOT_LOCATED": "#D95D39",
    "SUCCEEDED": "#2A9D8F", "SUPPORTED": "#2A9D8F",
}
ANCHORS = ["1842", "1938", "1988", "2006–2007", "2015", "2022"]
FAMILIES = [
    "temperature_threshold", "heat", "warming", "climate", "carbon_greenhouse",
    "concern_alarm", "worry", "fear_afraid", "anxiety", "distress_depression",
    "danger_threat", "risk", "crisis_emergency", "harm_loss_consequences",
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    return ImageFont.truetype(f"/System/Library/Fonts/Supplemental/{name}", size)


class Canvas:
    def __init__(self, title: str, subtitle: str, warning: str):
        self.image = Image.new("RGB", (W, H), BG)
        self.draw = ImageDraw.Draw(self.image, "RGBA")
        self.svg: list[str] = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', f'<rect width="{W}" height="{H}" fill="{BG}"/>']
        self.text(70, 48, title, 34, INK, True)
        self.text(70, 94, subtitle, 18, MUTED)
        self.text(70, 875, warning, 15, MUTED)

    def text(self, x: float, y: float, value: object, size: int, color: str = INK, bold: bool = False, anchor: str = "la") -> None:
        txt = str(value)
        pil_anchor = {"la": "la", "ma": "ma", "ra": "ra", "mm": "mm"}.get(anchor, "la")
        self.draw.text((x, y), txt, fill=color, font=font(size, bold), anchor=pil_anchor)
        svg_anchor = {"la": "start", "ma": "middle", "ra": "end", "mm": "middle"}.get(anchor, "start")
        weight = "700" if bold else "400"
        baseline = "middle" if anchor == "mm" else "auto"
        self.svg.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{svg_anchor}" dominant-baseline="{baseline}">{html.escape(txt)}</text>')

    def rect(self, xy: tuple[float, float, float, float], fill: str, outline: str | None = None, width: int = 1, alpha: int = 255) -> None:
        self.draw.rectangle(xy, fill=fill + (f"{alpha:02x}" if len(fill) == 7 and alpha < 255 else ""), outline=outline, width=width)
        x1, y1, x2, y2 = xy
        opacity = alpha / 255
        stroke = outline or "none"
        self.svg.append(f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{x2-x1:.1f}" height="{y2-y1:.1f}" fill="{fill}" fill-opacity="{opacity:.3f}" stroke="{stroke}" stroke-width="{width}"/>')

    def line(self, xy: list[tuple[float, float]], fill: str, width: int = 2, alpha: int = 255) -> None:
        self.draw.line(xy, fill=fill + (f"{alpha:02x}" if len(fill) == 7 and alpha < 255 else ""), width=width, joint="curve")
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
        self.svg.append(f'<polyline points="{pts}" fill="none" stroke="{fill}" stroke-opacity="{alpha/255:.3f}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>')

    def polygon(self, xy: list[tuple[float, float]], fill: str, alpha: int = 255, outline: str | None = None) -> None:
        self.draw.polygon(xy, fill=fill + (f"{alpha:02x}" if len(fill) == 7 and alpha < 255 else ""), outline=outline)
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
        self.svg.append(f'<polygon points="{pts}" fill="{fill}" fill-opacity="{alpha/255:.3f}" stroke="{outline or "none"}"/>')

    def circle(self, x: float, y: float, r: float, fill: str, outline: str | None = None) -> None:
        self.draw.ellipse((x-r, y-r, x+r, y+r), fill=fill, outline=outline)
        self.svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{outline or "none"}"/>')

    def save(self, stem: str) -> tuple[Path, Path]:
        png = OUT / f"{stem}.png"
        svg = OUT / f"{stem}.svg"
        self.image.save(png, optimize=True)
        self.svg.append("</svg>")
        svg.write_text("\n".join(self.svg) + "\n", encoding="utf-8")
        return png, svg


def source(frame: pd.DataFrame, stem: str) -> Path:
    path = SOURCES / f"{stem}_source.csv"
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


def nice_max(value: float) -> float:
    if value <= 0:
        return 1
    magnitude = 10 ** math.floor(math.log10(value))
    scaled = value / magnitude
    step = 1 if scaled <= 1 else 2 if scaled <= 2 else 5 if scaled <= 5 else 10
    return step * magnitude


def stacked_bars(frame: pd.DataFrame, categories: list[str], title: str, subtitle: str, warning: str,
                 stem: str, percentage: bool = False, color_map: dict[str, str] | None = None) -> None:
    c = Canvas(title, subtitle, warning)
    left, top, right, bottom = 180, 190, 1480, 765
    c.rect((left, top, right, bottom), WHITE, GRID)
    bar_gap = 26
    bar_h = (bottom - top - bar_gap * (len(frame) + 1)) / len(frame)
    scale_max = 1 if percentage else max(float(frame["total"].max()), 1)
    for tick in range(6):
        value = scale_max * tick / 5
        x = left + (right - left) * tick / 5
        c.line([(x, top), (x, bottom)], GRID, 1)
        label = f"{value:.0%}" if percentage else f"{value:.0f}"
        c.text(x, bottom + 28, label, 15, MUTED, anchor="ma")
    for i, row in frame.reset_index(drop=True).iterrows():
        y1 = top + bar_gap + i * (bar_h + bar_gap)
        y2 = y1 + bar_h
        c.text(left - 22, (y1 + y2) / 2, row["anchor"], 17, INK, True, "ra")
        cursor = left
        for j, category in enumerate(categories):
            key = f"{category}_percentage" if percentage else f"{category}_count"
            value = float(row[key])
            width = (right - left) * value / scale_max
            color = (color_map or {}).get(category, PALETTE[j % len(PALETTE)])
            if width > 0:
                c.rect((cursor, y1, cursor + width, y2), color)
                if width > 48:
                    c.text(cursor + width / 2, (y1 + y2) / 2, f"{value:.0%}" if percentage else str(int(value)), 14, WHITE, True, "mm")
            cursor += width
    legend_y = 145
    for i, category in enumerate(categories):
        x = 180 + i * 230
        color = (color_map or {}).get(category, PALETTE[i % len(PALETTE)])
        c.rect((x, legend_y, x + 22, legend_y + 16), color)
        c.text(x + 32, legend_y + 15, category, 15, INK)
    c.save(stem)
    source(frame, stem)


def heatmap(matrix: pd.DataFrame, row_col: str, value_col: str, title: str, subtitle: str,
            warning: str, stem: str, row_order: list[str], col_order: list[str], normalize_rows: bool = False) -> None:
    pivot = matrix.pivot_table(index=row_col, columns="anchor" if "anchor" in matrix.columns else "family", values=value_col, aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(index=row_order, columns=col_order, fill_value=0)
    display = pivot.astype(float)
    if normalize_rows:
        denom = display.max(axis=1).replace(0, 1)
        display = display.div(denom, axis=0)
    c = Canvas(title, subtitle, warning)
    left, top, right, bottom = 330, 175, 1480, 800
    cell_w = (right - left) / len(col_order)
    cell_h = (bottom - top) / len(row_order)
    max_v = float(display.to_numpy().max()) or 1
    short_labels = {
        "temperature_threshold": ["temperature", "threshold"],
        "carbon_greenhouse": ["carbon /", "greenhouse"],
        "concern_alarm": ["concern /", "alarm"],
        "fear_afraid": ["fear / afraid"],
        "distress_depression": ["distress /", "depression"],
        "danger_threat": ["danger /", "threat"],
        "crisis_emergency": ["crisis /", "emergency"],
        "harm_loss_consequences": ["harm / loss /", "consequences"],
    }
    for j, col in enumerate(col_order):
        lines = short_labels.get(col, [str(col).replace("_", " ")]) if len(col_order) > 8 else [str(col)]
        label_size = 10 if len(col_order) > 8 else 15
        for line_no, label in enumerate(lines):
            c.text(left + (j + 0.5) * cell_w, top - 34 + line_no * 14, label, label_size, INK, True, "ma")
    for i, row_name in enumerate(row_order):
        c.text(left - 18, top + (i + 0.5) * cell_h, row_name.replace("_", " "), 14, INK, anchor="ra")
        for j, col in enumerate(col_order):
            value = float(display.loc[row_name, col])
            intensity = value / max_v
            base = (36, 87, 167)
            rgb = tuple(int(245 + (channel - 245) * intensity) for channel in base)
            color = "#" + "".join(f"{x:02X}" for x in rgb)
            x1, y1 = left + j * cell_w, top + i * cell_h
            c.rect((x1, y1, x1 + cell_w, y1 + cell_h), color, WHITE)
            raw = float(pivot.loc[row_name, col])
            label = f"{value:.2f}" if normalize_rows else f"{int(raw)}"
            c.text(x1 + cell_w / 2, y1 + cell_h / 2, label, 13, WHITE if intensity > 0.45 else INK, True, "mm")
    source_df = pivot.reset_index()
    if normalize_rows:
        norm = display.reset_index()
        source_df = source_df.merge(norm, on=row_col, suffixes=("_raw", "_display"))
    source(source_df, stem)
    c.save(stem)


def line_chart(frame: pd.DataFrame, title: str, subtitle: str, warning: str, stem: str,
               normalized: bool = False) -> None:
    work = frame.copy()
    if normalized:
        work["display_value"] = work.groupby("term")["normalized_frequency"].transform(lambda s: s / s.max() if s.max() else s)
        y_col = "display_value"
    else:
        work["frequency_per_million"] = work["normalized_frequency"] * 1_000_000
        y_col = "frequency_per_million"
    c = Canvas(title, subtitle, warning)
    left, top, right, bottom = 130, 175, 1480, 760
    c.rect((left, top, right, bottom), WHITE, GRID)
    y_max = nice_max(float(work[y_col].max()))
    for tick in range(6):
        value = y_max * tick / 5
        y = bottom - (bottom - top) * tick / 5
        c.line([(left, y), (right, y)], GRID, 1)
        c.text(left - 18, y + 5, f"{value:.2g}", 14, MUTED, anchor="ra")
    for year in [1842, 1880, 1920, 1960, 1988, 2007, 2015, 2022]:
        x = left + (right - left) * (year - 1842) / (2022 - 1842)
        c.line([(x, top), (x, bottom)], "#E5E8EF", 1)
        c.text(x, bottom + 28, year, 14, MUTED, anchor="ma")
    for marker in [1938, 1988, 2006, 2007, 2015, 2022]:
        x = left + (right - left) * (marker - 1842) / 180
        c.line([(x, top), (x, bottom)], "#7B8496", 1, 110)
    for i, (term, group) in enumerate(work.groupby("term", sort=False)):
        group = group.sort_values("year")
        points = []
        for _, row in group.iterrows():
            x = left + (right - left) * (float(row.year) - 1842) / 180
            y = bottom - (bottom - top) * float(row[y_col]) / y_max
            points.append((x, y))
        c.line(points, PALETTE[i % len(PALETTE)], 3)
        x = 160 + (i % 4) * 330
        y = 140 + (i // 4) * 26
        c.line([(x, y), (x + 30, y)], PALETTE[i % len(PALETTE)], 4)
        c.text(x + 40, y + 5, term, 15, INK)
    source(work, stem)
    c.save(stem)


def grouped_status_bars(frame: pd.DataFrame, category_col: str, status_col: str, title: str, subtitle: str,
                        warning: str, stem: str, status_order: list[str]) -> None:
    counts = frame.groupby([category_col, status_col]).size().reset_index(name="candidate_count")
    wide = counts.pivot(index=category_col, columns=status_col, values="candidate_count").fillna(0)
    wide = wide.reindex(index=ANCHORS, columns=status_order, fill_value=0)
    chart = wide.reset_index().rename(columns={category_col: "anchor"})
    chart["total"] = chart[status_order].sum(axis=1)
    for status in status_order:
        chart[f"{status}_count"] = chart[status]
    stacked_bars(chart, status_order, title, subtitle, warning, stem, False,
                 {s: STATUS_COLORS.get(s, PALETTE[i % len(PALETTE)]) for i, s in enumerate(status_order)})
    source(counts, stem)


def emergence_figure(term_series: pd.DataFrame) -> None:
    validated = {
        "climatic change": 1938, "greenhouse effect": 1988, "global warming": 1988,
        "climate change": 2006, "climate crisis": 2006, "climate emergency": 2022,
        "climate anxiety": 2022, "eco-anxiety": 2022,
    }
    rows = []
    for term, year in validated.items():
        group = term_series[term_series.term == term].sort_values("year")
        nonzero = group[group.normalized_frequency > 0]
        first = int(nonzero.year.min()) if not nonzero.empty else None
        sustained = None
        values = dict(zip(group.year.astype(int), group.normalized_frequency.astype(float)))
        for candidate_year in range(1842, 2021):
            if all(values.get(y, 0) > 0 for y in range(candidate_year, candidate_year + 3)):
                sustained = candidate_year
                break
        rows.append({
            "term": term, "first_ngram_nonzero_year": first,
            "first_sustained_ngram_year": sustained,
            "first_validated_attestation_year": year,
            "first_validated_target_sense_year": year,
            "validated_year_semantics": "earliest project-validated anchor evidence, not first-ever attestation",
        })
    frame = pd.DataFrame(rows)
    stem = "visual_07_ngram_vs_validated_attestation"
    c = Canvas("Raw Ngram appearance versus project-validated evidence",
               "First string occurrence and sustained presence are separated from validated anchor evidence",
               "Raw string occurrence ≠ validated historical meaning; validated year means earliest evidence in this project, not coinage.")
    left, top, right, bottom = 230, 190, 1480, 760
    for tick in [1842, 1880, 1920, 1960, 2000, 2022]:
        x = left + (right-left)*(tick-1842)/180
        c.line([(x, top), (x, bottom)], GRID, 1)
        c.text(x, bottom+28, tick, 14, MUTED, anchor="ma")
    for i, row in frame.iterrows():
        y = top + 35 + i * 66
        c.text(left-18, y+4, row.term, 15, INK, True, "ra")
        years = [row.first_ngram_nonzero_year, row.first_sustained_ngram_year, row.first_validated_attestation_year]
        colors = ["#A7AFBE", "#E9C46A", "#D95D39"]
        for j, (year, color) in enumerate(zip(years, colors)):
            if pd.notna(year):
                x = left + (right-left)*(float(year)-1842)/180
                c.circle(x, y, 7 if j < 2 else 9, color, WHITE)
        if pd.notna(years[0]) and pd.notna(years[2]):
            x1 = left + (right-left)*(float(years[0])-1842)/180
            x2 = left + (right-left)*(float(years[2])-1842)/180
            c.line([(x1, y), (x2, y)], "#7B8496", 2, 150)
    for i, (label, color) in enumerate([("first Ngram nonzero", "#A7AFBE"), ("first sustained (3 years)", "#E9C46A"), ("project-validated anchor evidence", "#D95D39")]):
        x = 270 + i*370
        c.circle(x, 145, 7, color)
        c.text(x+16, 150, label, 14, INK)
    source(frame, stem)
    c.save(stem)


def scatter_figure(candidate: pd.DataFrame) -> None:
    frame = candidate.copy()
    frame["x"] = pd.to_numeric(frame.search_log10_result_count, errors="coerce")
    frame["y"] = pd.to_numeric(frame.ngram_peak_per_million, errors="coerce")
    frame = frame.dropna(subset=["x", "y"])
    stem = "visual_08_ngram_vs_search_discoverability"
    c = Canvas("Corpus frequency versus provider discoverability",
               "Candidate-level comparison of Ngram peak frequency and Internet Archive metadata text-item counts",
               "Search result count measures provider discoverability, not language prevalence; axes are not interchangeable metrics.")
    left, top, right, bottom = 150, 180, 1470, 760
    c.rect((left, top, right, bottom), WHITE, GRID)
    x_max = max(float(frame.x.max()), 1)
    y_plot = frame.y.map(lambda y: math.log10(float(y) + 1e-6) - math.log10(1e-6))
    y_max = max(float(y_plot.max()), 1)
    for tick in range(6):
        x = left + (right-left)*tick/5
        c.line([(x, top), (x, bottom)], GRID, 1)
        c.text(x, bottom+28, f"{x_max*tick/5:.1f}", 14, MUTED, anchor="ma")
        y = bottom - (bottom-top)*tick/5
        c.line([(left, y), (right, y)], GRID, 1)
        c.text(left-18, y+4, f"{y_max*tick/5:.1f}", 14, MUTED, anchor="ra")
    frame = frame.assign(y_log_display=y_plot)
    for _, row in frame.iterrows():
        x = left + (right-left)*float(row.x)/x_max
        y = bottom - (bottom-top)*float(row.y_log_display)/y_max
        c.circle(x, y, 5, LAYER_COLORS.get(str(row.layer_code), ACCENT))
    outliers = frame.sort_values(["y", "x"], ascending=False).head(8)
    for _, row in outliers.iterrows():
        x = left + (right-left)*float(row.x)/x_max
        y = bottom - (bottom-top)*float(row.y_log_display)/y_max
        c.text(x+8, y-8, str(row.surface_form)[:28], 12, INK)
    c.text((left+right)/2, bottom+62, "log10(Internet Archive result count + 1)", 16, INK, True, "ma")
    c.text(18, (top+bottom)/2, "log display of Ngram peak per million", 14, INK, True)
    source(frame.drop(columns=["x", "y"]).rename(columns={"search_log10_result_count": "x_log10_search_count", "ngram_peak_per_million": "y_ngram_peak_per_million"}), stem)
    c.save(stem)


def missingness_figure(candidate: pd.DataFrame) -> None:
    rows = []
    columns = ["voice", "expression_mode", "source", "dictionary", "ngram", "search", "provenance"]
    for _, row in candidate.iterrows():
        values = {
            "voice": "COMPLETE" if str(row.voice_code).startswith("V") else "NOT_EXPOSED",
            "expression_mode": "COMPLETE" if str(row.expression_mode).startswith("E") else "NOT_EXPOSED",
            "source": "COMPLETE" if str(row.evidence_source) not in {"", "NOT_EXPOSED_IN_REPORT"} else "NOT_EXPOSED",
            "dictionary": "UNRESOLVED" if row.dictionary_status == "UNRESOLVED" else "COMPLETE",
            "ngram": "NOT_APPLICABLE" if row.ngram_status == "TECHNICALLY_UNREPRESENTABLE" else ("ZERO_RESULT" if "ZERO_RESPONSE" in row.ngram_status else "COMPLETE"),
            "search": "ZERO_RESULT" if row.search_status == "COMPLETED_ZERO" else ("COMPLETE" if row.search_status == "COMPLETED_NONZERO" else "UNRESOLVED"),
            "provenance": "COMPLETE" if row.provenance_status else "UNRESOLVED",
        }
        rows.append({"candidate_id": row.candidate_id, "anchor": row.anchor_label, **values})
    frame = pd.DataFrame(rows)
    stem = "visual_11_candidate_missingness_heatmap"
    c = Canvas("Candidate-level coverage and missingness",
               "180 Priority Candidates × seven evidence/annotation dimensions",
               "Zero results and not-applicable states remain visible; this chart prioritises future review rather than imputing missing data.")
    left, top, right, bottom = 300, 175, 1460, 800
    cell_w = (right-left)/len(columns)
    cell_h = (bottom-top)/len(frame)
    for j, col in enumerate(columns):
        c.text(left+(j+0.5)*cell_w, top-24, col.replace("_", " "), 15, INK, True, "ma")
    for i, row in frame.iterrows():
        for j, col in enumerate(columns):
            status = row[col]
            c.rect((left+j*cell_w, top+i*cell_h, left+(j+1)*cell_w, top+(i+1)*cell_h), STATUS_COLORS.get(status, "#A7AFBE"))
        if i % 30 == 0:
            c.line([(left, top+i*cell_h), (right, top+i*cell_h)], INK, 2)
            c.text(left-18, top+i*cell_h+10, row.anchor, 13, INK, True, "ra")
    legend = [("complete", "COMPLETE"), ("zero", "ZERO_RESULT"), ("not applicable", "NOT_APPLICABLE"), ("unresolved", "UNRESOLVED")]
    for i, (label, status) in enumerate(legend):
        x = 330+i*260
        c.rect((x, 825, x+22, 841), STATUS_COLORS[status])
        c.text(x+32, 840, label, 14, INK)
    source(frame, stem)
    c.save(stem)


def alluvial_figure(candidate: pd.DataFrame) -> None:
    dimensions = ["anchor_label", "layer_code", "voice_code", "lexical_family"]
    labels = [ANCHORS, ["A", "B", "C", "D"], ["V1", "V2", "V3", "V4", "V5"], FAMILIES]
    xs = [170, 590, 1010, 1430]
    node_w, top, bottom, gap = 22, 190, 800, 8
    node_boxes: list[dict[str, tuple[float, float]]] = []
    for dim, order in zip(dimensions, labels):
        counts = candidate[dim].value_counts().to_dict()
        available = bottom-top-gap*(len(order)-1)
        scale = available/len(candidate)
        pos = top
        boxes = {}
        for value in order:
            height = max(counts.get(value, 0)*scale, 2)
            boxes[value] = (pos, pos+height)
            pos += height+gap
        node_boxes.append(boxes)
    c = Canvas("Structure of the constructed lexical inventory",
               "Metadata flow: Anchor → Layer → Voice → Lexical family; ribbon width = candidate count",
               "This is a metadata structure, not a historical process, causal flow, or semantic-evolution network.")
    for d in range(3):
        left_dim, right_dim = dimensions[d], dimensions[d+1]
        grouped = candidate.groupby([left_dim, right_dim]).size().reset_index(name="count")
        left_offsets = {k: v[0] for k, v in node_boxes[d].items()}
        right_offsets = {k: v[0] for k, v in node_boxes[d+1].items()}
        scale = (bottom-top-gap*(len(labels[d])-1))/180
        for _, row in grouped.sort_values([left_dim, right_dim]).iterrows():
            a, bval, count = row[left_dim], row[right_dim], int(row["count"])
            thickness = max(count*scale, 1)
            y1a, y1b = left_offsets[a], left_offsets[a]+thickness
            y2a, y2b = right_offsets[bval], right_offsets[bval]+thickness
            left_offsets[a] += thickness
            right_offsets[bval] += thickness
            color = PALETTE[(labels[d].index(a) if a in labels[d] else 0) % len(PALETTE)]
            c.polygon([(xs[d]+node_w, y1a), (xs[d+1], y2a), (xs[d+1], y2b), (xs[d]+node_w, y1b)], color, 55)
    for d, (dim, order) in enumerate(zip(dimensions, labels)):
        c.text(xs[d]+node_w/2, 145, dim.replace("_", " "), 17, INK, True, "ma")
        for i, value in enumerate(order):
            y1, y2 = node_boxes[d][value]
            color = PALETTE[i % len(PALETTE)]
            c.rect((xs[d], y1, xs[d]+node_w, y2), color)
            label = value.replace("_", " ")
            if d == 3:
                c.text(xs[d]+30, (y1+y2)/2+4, label[:25], 11, INK)
            else:
                c.text(xs[d]-10, (y1+y2)/2+4, label, 13, INK, True, "ra")
    flows = candidate.groupby(dimensions).size().reset_index(name="candidate_count")
    source(flows, "visual_12_structural_alluvial")
    c.save("visual_12_structural_alluvial")


def dedup_term_series() -> pd.DataFrame:
    series = pd.read_csv(DATA / "ngram" / "ngram_timeseries_full.csv")
    series["term"] = series.term.str.casefold()
    series = series.sort_values("query_id").drop_duplicates(["term", "year"], keep="first")
    series["normalized_frequency"] = pd.to_numeric(series.normalized_frequency)
    series["year"] = pd.to_numeric(series.year)
    return series


def metadata(stem: str, title: str, caption: str, metric: str, warning: str, source_file: str) -> dict[str, str]:
    return {"figure_id": stem, "title": title, "caption": caption, "metric_definition": metric,
            "interpretation_warning": warning, "source_csv": source_file,
            "generation_script": "scripts/fear-temperature/generate_eda_figures.py"}


def main() -> None:
    candidate = pd.read_csv(ANALYSIS / "candidate_analysis_180.csv", keep_default_na=False)
    layers = pd.read_csv(ANALYSIS / "anchor_layer_counts.csv")
    voices = pd.read_csv(ANALYSIS / "anchor_voice_counts.csv")
    anchor_family = pd.read_csv(ANALYSIS / "anchor_family_counts.csv")
    voice_family = pd.read_csv(ANALYSIS / "voice_family_counts.csv")
    series = dedup_term_series()

    stacked_bars(layers, ["A", "B", "C", "D"], "Composition of the constructed lexical inventory",
                 "Priority Candidate counts by historical anchor and lexical layer", "Inventory composition ≠ historical prevalence.",
                 "visual_01a_anchor_layer_counts", False, LAYER_COLORS)
    stacked_bars(layers, ["A", "B", "C", "D"], "Composition of the constructed lexical inventory",
                 "Within-anchor percentage by lexical layer", "Within-anchor shares describe the constructed inventory, not prevalence in historical language.",
                 "visual_01b_anchor_layer_percentages", True, LAYER_COLORS)
    stacked_bars(voices, ["V1", "V2", "V3", "V4", "V5"], "Voice composition of the constructed lexical inventory",
                 "Priority Candidate counts by historical anchor and substantive voice", "Speaker/source composition can explain apparent lexical differences; absence is not imputed.",
                 "visual_02_anchor_voice_counts", False, VOICE_COLORS)
    heatmap(anchor_family, "family", "candidate_count", "Lexical-family composition by anchor",
            "Candidate counts for 14 controlled semantic families across six anchors", "Inventory counts ≠ corpus frequency or historical prevalence.",
            "visual_03a_anchor_family_counts", FAMILIES, ANCHORS)
    heatmap(anchor_family, "family", "candidate_count", "Within-family normalized inventory presence",
            "Each family is scaled to its own maximum across anchors", "Within-family normalized display — not frequency.",
            "visual_03b_anchor_family_row_normalized", FAMILIES, ANCHORS, True)
    vf = voice_family.rename(columns={"voice": "row", "family": "anchor"})
    heatmap(vf, "row", "candidate_count", "Voice × lexical-family reconstruction",
            "Candidate counts expose which voices contribute to each family", "This is source/speaker composition in the constructed inventory, not social prevalence.",
            "visual_04_voice_family_heatmap", ["V1", "V2", "V3", "V4", "V5"], FAMILIES)

    climate_terms = ["climatic change", "greenhouse effect", "global warming", "climate change"]
    climate = series[series.term.isin(climate_terms)].copy()
    line_chart(climate, "Climate-framing string trajectories", "Unsmoothed annual Google Books Ngram values, 1842–2022",
               "Raw annual string frequency; no causal or reception claim. Generic/cross-sense occurrences still require passage validation.",
               "visual_05_climate_framing_trajectories")
    modern_terms = ["climate crisis", "climate emergency", "climate anxiety", "eco-anxiety"]
    modern = series[series.term.isin(modern_terms)].copy()
    line_chart(modern, "Modern specialised climate compounds", "Raw unsmoothed annual Google Books Ngram values, 1842–2022",
               "Low-frequency strings may be affected by corpus/OCR artefacts; string occurrence is not validated meaning.",
               "visual_06a_modern_compounds_raw")
    line_chart(modern, "Modern specialised climate compounds", "Term-normalized display of each raw unsmoothed annual trajectory",
               "Term-normalized display — not corpus frequency. Raw values remain in the paired source table and raw-scale figure.",
               "visual_06b_modern_compounds_normalized", True)
    emergence_figure(series)
    scatter_figure(candidate)
    grouped_status_bars(candidate, "anchor_label", "dictionary_status", "Dictionary treatment across anchors",
                        "Candidate-level lexicographic status", "Lexicalisation/technicalisation diagnostic only; not direct semantic evolution.",
                        "visual_09_dictionary_status_by_anchor", ["DIRECT_HEADWORD", "TECHNICAL_GLOSSARY", "NO_STANDALONE_HEADWORD"])
    search_frame = candidate.copy()
    search_frame["search_display"] = search_frame.search_status.map({"COMPLETED_NONZERO": "SUCCEEDED", "COMPLETED_ZERO": "ZERO_RESULT"}).fillna("UNRESOLVED")
    grouped_status_bars(search_frame, "anchor_label", "search_display", "Searchability and archival bias",
                        "Internet Archive metadata-search outcomes by anchor", "Easier modern retrieval must not be interpreted as historical lexical abundance.",
                        "visual_10_searchability_bias", ["SUCCEEDED", "ZERO_RESULT", "UNRESOLVED"])
    missingness_figure(candidate)
    alluvial_figure(candidate)

    metadata_rows = []
    definitions = {
        "visual_01a_anchor_layer_counts": ("Composition of the constructed lexical inventory", "Raw candidate counts by anchor/layer.", "Priority Candidate count", "Inventory composition ≠ historical prevalence."),
        "visual_01b_anchor_layer_percentages": ("Composition of the constructed lexical inventory", "Within-anchor candidate shares by layer.", "Candidate share within anchor", "Inventory composition ≠ historical prevalence."),
        "visual_02_anchor_voice_counts": ("Voice composition", "Candidate counts by anchor/voice.", "Priority Candidate count", "Source composition may shape apparent lexical change."),
        "visual_03a_anchor_family_counts": ("Anchor × family", "Candidate count heatmap.", "Priority Candidate count", "Not corpus frequency."),
        "visual_03b_anchor_family_row_normalized": ("Anchor × family normalized", "Family-wise maximum-normalized display.", "Count divided by family maximum", "Within-family normalized display — not frequency."),
        "visual_04_voice_family_heatmap": ("Voice × family", "Candidate count heatmap.", "Priority Candidate count", "Source/speaker composition, not prevalence."),
        "visual_05_climate_framing_trajectories": ("Climate framing trajectories", "Raw annual Ngram series.", "Normalized frequency × 1,000,000", "String frequency is not semantic evidence."),
        "visual_06a_modern_compounds_raw": ("Modern specialised compounds", "Raw annual Ngram series.", "Normalized frequency × 1,000,000", "String occurrence is not validated target sense."),
        "visual_06b_modern_compounds_normalized": ("Modern compounds normalized", "Each trajectory scaled to its own peak.", "Term value / term maximum", "Normalized display is not corpus frequency."),
        "visual_07_ngram_vs_validated_attestation": ("Ngram versus validated evidence", "Raw string appearance versus project evidence.", "Year", "Project evidence is not first-ever attestation."),
        "visual_08_ngram_vs_search_discoverability": ("Frequency versus discoverability", "Parallel measurement comparison.", "Ngram peak per million; IA count log10", "Metrics answer different questions."),
        "visual_09_dictionary_status_by_anchor": ("Dictionary status", "Candidate lexicographic treatment by anchor.", "Priority Candidate count", "Does not establish semantic evolution."),
        "visual_10_searchability_bias": ("Searchability bias", "Bounded-search outcomes by anchor.", "Candidate count", "Retrieval ease is not lexical abundance."),
        "visual_11_candidate_missingness_heatmap": ("Missingness heatmap", "Coverage across seven candidate dimensions.", "Controlled status", "Zero and missing states are not imputed."),
        "visual_12_structural_alluvial": ("Structural alluvial", "Metadata composition flow.", "Candidate count", "Not a historical process or causal flow."),
    }
    for stem, (title, caption, metric_def, warning) in definitions.items():
        source_file = f"figures/fear-temperature/eda-v02/sources/{stem}_source.csv"
        item = metadata(stem, title, caption, metric_def, warning, source_file)
        metadata_rows.append(item)
        (OUT / f"{stem}_metadata.json").write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(metadata_rows).to_csv(OUT / "figure_metadata.csv", index=False, lineterminator="\n")
    (OUT / "figure_manifest.json").write_text(json.dumps({
        "version": "exploratory-analysis-v0.2", "figure_count": len(metadata_rows),
        "formats": ["png", "svg"], "source_table_count": len(metadata_rows),
        "generator": "scripts/fear-temperature/generate_eda_figures.py",
    }, indent=2) + "\n", encoding="utf-8")
    catalog_lines = [
        "# Figure Catalog — Exploratory Analysis v0.2", "",
        "All figures are generated from version-controlled CSV exports. PNG and SVG versions share the same source table and metadata.", "",
        "| Figure | Research question / purpose | Metric | Interpretation warning |",
        "| --- | --- | --- | --- |",
    ]
    for item in metadata_rows:
        catalog_lines.append(
            f"| `{item['figure_id']}` | {item['caption']} | {item['metric_definition']} | {item['interpretation_warning']} |"
        )
    catalog_lines.extend([
        "", "## Reproduction", "",
        "Run `python3 scripts/fear-temperature/generate_eda_figures.py` from the repository root.", "",
        "The alluvial diagram visualises metadata structure only. It does not assert a historical process, causal flow, or semantic-evolution pathway.", "",
    ])
    catalog_path = ROOT / "docs" / "research" / "fear-temperature" / "FIGURE_CATALOG.md"
    catalog_path.write_text("\n".join(catalog_lines), encoding="utf-8")
    print(json.dumps({"status": "PASS", "figure_count": len(metadata_rows), "output_dir": str(OUT.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
