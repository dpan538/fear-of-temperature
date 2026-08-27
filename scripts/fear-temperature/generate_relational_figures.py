#!/usr/bin/env python3
"""Generate the 12 presentation figures for relational analysis v0.1."""

from __future__ import annotations

import csv
import html
import json
import math
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
REL = ROOT / "data/fear-temperature/analysis/relational-v01"
OUT = ROOT / "figures/fear-temperature/relational-v01"
SOURCES = OUT / "sources"
OUT.mkdir(parents=True, exist_ok=True)
SOURCES.mkdir(parents=True, exist_ok=True)

W, H = 1600, 1000
WHITE = "#FFFFFF"
INK = "#182435"
MUTED = "#5E6A79"
GRID = "#DCE2E8"
MISSING = "#E5E9EE"
MISSING_DARK = "#8B96A5"
OBJECT = "#2F6B8A"
OBJECT_2 = "#4D8BA8"
THREAT = "#D05A32"
THREAT_LIGHT = "#F6DED5"
AFFECT = "#6655A4"
AFFECT_LIGHT = "#E8E3F4"
AMBER = "#D79A2B"
SUPPORTED = "#3C7F78"
ZERO = "#E0A44E"

ANCHORS = ["1842", "1938", "1988", "2006–2007", "2015", "2022"]
VOICES = ["V1", "V2", "V3", "V4", "V5"]
VOICE_LABELS = {
    "V1": "Scientific / research", "V2": "Institutional / governance",
    "V3": "Mediated public", "V4": "Civic / advocacy", "V5": "Direct public / lay",
}
LAYER_COLORS = {"A": OBJECT, "B": OBJECT_2, "C": AFFECT, "D": THREAT}
LAYER_LABELS = {"A": "A Object", "B": "B Climate frame", "C": "C Affect", "D": "D Threat / harm"}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    filename = "Arial Bold.ttf" if bold else "Arial.ttf"
    return ImageFont.truetype(f"/System/Library/Fonts/Supplemental/{filename}", size)


class Canvas:
    def __init__(self, title: str, subtitle: str, caption: str):
        self.image = Image.new("RGB", (W, H), WHITE)
        self.draw = ImageDraw.Draw(self.image, "RGBA")
        self.svg: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
            f'<rect width="{W}" height="{H}" fill="{WHITE}"/>',
        ]
        self.text(70, 52, title, 38, INK, True)
        self.text(70, 102, subtitle, 19, MUTED)
        for i, line in enumerate(textwrap.wrap(caption, 170)):
            self.text(70, 944 + i * 18, line, 14, MUTED)

    def text(self, x: float, y: float, value: object, size: int = 16, color: str = INK,
             bold: bool = False, anchor: str = "la") -> None:
        text = str(value)
        pil_anchor = {"la": "la", "ma": "ma", "ra": "ra", "mm": "mm"}.get(anchor, "la")
        self.draw.text((x, y), text, fill=color, font=font(size, bold), anchor=pil_anchor)
        svg_anchor = {"la": "start", "ma": "middle", "ra": "end", "mm": "middle"}.get(anchor, "start")
        baseline = "middle" if anchor == "mm" else "auto"
        weight = "700" if bold else "400"
        self.svg.append(
            f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-family="Arial,sans-serif" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{svg_anchor}" '
            f'dominant-baseline="{baseline}">{html.escape(text)}</text>'
        )

    def multiline(self, x: float, y: float, value: str, width: int, size: int = 16,
                  color: str = INK, bold: bool = False, line_height: int | None = None,
                  anchor: str = "la") -> None:
        line_height = line_height or int(size * 1.3)
        for i, line in enumerate(textwrap.wrap(value, width)):
            self.text(x, y + i * line_height, line, size, color, bold, anchor)

    def rect(self, xy: tuple[float, float, float, float], fill: str = WHITE,
             outline: str | None = None, width: int = 1, alpha: int = 255) -> None:
        rgba = fill + (f"{alpha:02x}" if alpha < 255 else "")
        self.draw.rectangle(xy, fill=rgba, outline=outline, width=width)
        x1, y1, x2, y2 = xy
        self.svg.append(
            f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{x2-x1:.1f}" height="{y2-y1:.1f}" '
            f'fill="{fill}" fill-opacity="{alpha/255:.3f}" stroke="{outline or "none"}" stroke-width="{width}"/>'
        )

    def line(self, points: list[tuple[float, float]], color: str = GRID, width: int = 1,
             dash: str | None = None, alpha: int = 255) -> None:
        self.draw.line(points, fill=color + (f"{alpha:02x}" if alpha < 255 else ""), width=width)
        coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.svg.append(
            f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-opacity="{alpha/255:.3f}"{dash_attr}/>'
        )

    def circle(self, x: float, y: float, radius: float, fill: str, outline: str | None = None,
               width: int = 1) -> None:
        self.draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=fill, outline=outline, width=width)
        self.svg.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" '
            f'stroke="{outline or "none"}" stroke-width="{width}"/>'
        )

    def diamond(self, x: float, y: float, radius: float, fill: str, outline: str | None = None) -> None:
        pts = [(x, y-radius), (x+radius, y), (x, y+radius), (x-radius, y)]
        self.polygon(pts, fill, outline)

    def polygon(self, points: list[tuple[float, float]], fill: str, outline: str | None = None,
                alpha: int = 255) -> None:
        self.draw.polygon(points, fill=fill + (f"{alpha:02x}" if alpha < 255 else ""), outline=outline)
        coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        self.svg.append(
            f'<polygon points="{coords}" fill="{fill}" fill-opacity="{alpha/255:.3f}" '
            f'stroke="{outline or "none"}"/>'
        )

    def arrow(self, x1: float, y1: float, x2: float, y2: float, color: str, width: int = 5) -> None:
        self.line([(x1, y1), (x2, y2)], color, width)
        angle = math.atan2(y2-y1, x2-x1)
        size = 14
        points = [
            (x2, y2),
            (x2-size*math.cos(angle-0.55), y2-size*math.sin(angle-0.55)),
            (x2-size*math.cos(angle+0.55), y2-size*math.sin(angle+0.55)),
        ]
        self.polygon(points, color)

    def ribbon(self, x1: float, top1: float, bottom1: float, x2: float, top2: float,
               bottom2: float, fill: str, alpha: int = 90) -> None:
        steps = 28
        upper: list[tuple[float, float]] = []
        lower: list[tuple[float, float]] = []
        for i in range(steps + 1):
            t = i / steps
            smooth = t * t * (3 - 2 * t)
            x = x1 + (x2 - x1) * t
            upper.append((x, top1 + (top2 - top1) * smooth))
            lower.append((x, bottom1 + (bottom2 - bottom1) * smooth))
        self.polygon(upper + list(reversed(lower)), fill, None, alpha)
        path = (
            f'M {x1:.1f},{top1:.1f} C {(x1+x2)/2:.1f},{top1:.1f} {(x1+x2)/2:.1f},{top2:.1f} {x2:.1f},{top2:.1f} '
            f'L {x2:.1f},{bottom2:.1f} C {(x1+x2)/2:.1f},{bottom2:.1f} {(x1+x2)/2:.1f},{bottom1:.1f} {x1:.1f},{bottom1:.1f} Z'
        )
        self.svg.append(f'<path d="{path}" fill="{fill}" fill-opacity="{alpha/255:.3f}" stroke="none"/>')

    def save(self, stem: str) -> None:
        self.image.save(OUT / f"{stem}.png", optimize=True)
        self.svg.append("</svg>")
        (OUT / f"{stem}.svg").write_text("\n".join(self.svg) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_source(stem: str, rows: list[dict[str, object]], fields: list[str] | None = None) -> Path:
    if not rows and not fields:
        raise ValueError("source table requires rows or explicit fields")
    fields = fields or list(rows[0])
    path = SOURCES / f"{stem}_source.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def record(metadata: list[dict[str, str]], stem: str, title: str, caption: str,
           metric: str, warning: str, source_path: Path) -> None:
    item = {
        "figure_id": stem,
        "title": title,
        "caption": caption,
        "metric_definition": metric,
        "interpretation_warning": warning,
        "source_csv": str(source_path.relative_to(ROOT)),
        "generation_script": "scripts/fear-temperature/generate_relational_figures.py",
    }
    metadata.append(item)
    (OUT / f"{stem}_metadata.json").write_text(
        json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def figure_01(metadata: list[dict[str, str]]) -> None:
    stem = "figure_01_research_model"
    title = "How temperature and climate become historically consequential"
    caption = "The analysis validates relations from A/B objects to D threat and C affect separately. Co-occurrence alone does not establish either relation."
    c = Canvas(title, "Relationship-centred research model", caption)
    c.rect((90, 260, 575, 720), "#E3F0F5", OBJECT, 3)
    c.text(332, 320, "A / B", 38, OBJECT, True, "mm")
    c.text(332, 375, "Temperature + climate objects", 24, INK, True, "mm")
    c.multiline(332, 440, "temperature · heat · warming · climate · greenhouse effect · thresholds", 34, 19, MUTED, False, 32, "ma")

    c.rect((1010, 210, 1510, 490), THREAT_LIGHT, THREAT, 3)
    c.text(1260, 270, "D — Threat / risk / harm", 27, THREAT, True, "mm")
    c.multiline(1260, 335, "danger · threat · risk · crisis · emergency · loss · damage", 35, 18, INK, False, 29, "ma")
    c.text(1260, 450, "Evaluated consequence; not automatically emotion", 17, MUTED, True, "mm")

    c.rect((1010, 560, 1510, 840), AFFECT_LIGHT, AFFECT, 3)
    c.text(1260, 620, "C — Explicit affect", 27, AFFECT, True, "mm")
    c.multiline(1260, 680, "fear · worry · anxiety · distress · concern", 35, 18, INK, False, 29, "ma")
    c.text(1260, 795, "Direct · prescribed · elicited · researcher-labelled", 17, MUTED, True, "mm")

    c.arrow(585, 420, 995, 350, THREAT)
    c.arrow(585, 570, 995, 695, AFFECT)
    c.rect((625, 455, 965, 605), INK)
    c.text(795, 515, "THREAT ≠ AFFECT", 30, WHITE, True, "mm")
    c.text(795, 562, "D is not the same as C", 18, WHITE, False, "mm")
    c.save(stem)
    src = write_source(stem, [
        {"from": "A/B temperature-climate object", "to": "D threat/risk/harm", "validation": "explicit relation required"},
        {"from": "A/B temperature-climate object", "to": "C explicit affect", "validation": "explicit relation + affect mode required"},
    ])
    record(metadata, stem, title, caption, "Conceptual relation model", "Threat language must never be used as a proxy for affect.", src)


def unavailable_anchor_figure(metadata: list[dict[str, str]], linkage: str) -> None:
    lower = linkage.lower()
    color = THREAT if linkage == "Threat" else AFFECT
    stem = f"figure_{'02' if linkage == 'Threat' else '03'}_{lower}_link_rate_by_anchor"
    title = f"{linkage}-link rate by anchor"
    caption = "No validated A/B object passages are currently populated. Blank rates are unsupported, not zero historical linkage."
    c = Canvas(title, "Validated linked passages / validated A/B object passages", caption)
    left, top, right, bottom = 160, 210, 1510, 790
    c.rect((left, top, right, bottom), WHITE, GRID)
    for tick in range(5):
        y = bottom - (bottom-top) * tick / 4
        c.line([(left, y), (right, y)], GRID)
        c.text(left-18, y+5, f"{tick*25}%", 15, MUTED, anchor="ra")
    c.text(74, (top+bottom)/2, "Link rate", 16, MUTED, True, "mm")
    for i, anchor in enumerate(ANCHORS):
        x = left + (right-left) * (i + 0.5) / len(ANCHORS)
        c.text(x, bottom+38, anchor, 16, INK, True, "ma")
        c.text(x, 475, "N/A", 24, MISSING_DARK, True, "mm")
        c.text(x, 515, "0 / 0", 17, MISSING_DARK, False, "mm")
        c.line([(x-28, 545), (x+28, 545)], MISSING_DARK, 3, "7 5")
    c.rect((990, 148, 1020, 178), MISSING, MISSING_DARK)
    c.text(1035, 171, "Unsupported: denominator = 0", 16, MUTED)
    c.save(stem)
    src_rows = read_csv(REL / f"{lower}_linkage_by_anchor.csv")
    src = write_source(stem, src_rows)
    record(metadata, stem, title, caption, f"{linkage}_Link_Count / AB_Object_Passage_Count", "All six rates are not estimable because all six denominators are zero.", src)


def figure_04(metadata: list[dict[str, str]]) -> None:
    stem = "figure_04_threat_vs_affect_by_anchor"
    title = "Threat versus affect linkage by anchor"
    caption = "A dumbbell comparison becomes estimable only after validated A/B passages exist. Missing markers are shown as N/A, not placed at 0%."
    c = Canvas(title, "Paired linkage rates within each historical anchor", caption)
    left, top, right, bottom = 260, 195, 1500, 820
    for tick in range(5):
        x = left + (right-left) * tick / 4
        c.line([(x, top), (x, bottom)], GRID)
        c.text(x, bottom+32, f"{tick*25}%", 15, MUTED, anchor="ma")
    for i, anchor in enumerate(ANCHORS):
        y = top + 60 + i * 93
        c.text(left-30, y+5, anchor, 18, INK, True, "ra")
        c.line([(left, y), (right, y)], "#EEF1F4")
        c.text((left+right)/2, y-7, "Threat N/A   ·   Affect N/A", 17, MISSING_DARK, True, "mm")
        c.text((left+right)/2, y+24, "AB denominator 0", 14, MISSING_DARK, False, "mm")
    c.circle(965, 154, 7, THREAT)
    c.text(983, 159, "Threat", 15, INK)
    c.circle(1085, 154, 7, AFFECT)
    c.text(1103, 159, "Affect", 15, INK)
    c.text(1200, 159, "(markers withheld while unsupported)", 14, MUTED)
    c.save(stem)
    threat = {(r["anchor"]): r for r in read_csv(REL / "threat_linkage_by_anchor.csv")}
    affect = {(r["anchor"]): r for r in read_csv(REL / "affect_linkage_by_anchor.csv")}
    rows = [{
        "anchor": anchor,
        "AB_Object_Passage_Count": threat[anchor]["AB_Object_Passage_Count"],
        "Threat_Link_Rate": threat[anchor]["Threat_Link_Rate"],
        "Affect_Link_Rate": affect[anchor]["Affect_Link_Rate"],
        "Data_Status": threat[anchor]["Data_Status"],
    } for anchor in ANCHORS]
    src = write_source(stem, rows)
    record(metadata, stem, title, caption, "Paired Threat_Link_Rate and Affect_Link_Rate", "No points are plotted at zero because zero is not the observed rate.", src)


def heatmap_unsupported(metadata: list[dict[str, str]], linkage: str) -> None:
    lower = linkage.lower()
    stem = f"figure_{'05' if linkage == 'Threat' else '06'}_{lower}_linkage_heatmap"
    title = f"{linkage} linkage by anchor and voice"
    caption = "Every cell is low-N and unsupported because no validated A/B object passages are populated. The dash encodes missing estimands, not 0%."
    c = Canvas(title, "Cell value = validated passage-level link rate", caption)
    left, top, right, bottom = 360, 215, 1490, 810
    cw, ch = (right-left)/len(ANCHORS), (bottom-top)/len(VOICES)
    for j, anchor in enumerate(ANCHORS):
        c.text(left+(j+0.5)*cw, top-34, anchor, 16, INK, True, "ma")
    for i, voice in enumerate(VOICES):
        c.text(left-20, top+(i+0.5)*ch-8, voice, 17, INK, True, "ra")
        c.text(left-20, top+(i+0.5)*ch+18, VOICE_LABELS[voice], 13, MUTED, False, "ra")
        for j in range(len(ANCHORS)):
            x1, y1 = left+j*cw, top+i*ch
            c.rect((x1, y1, x1+cw, y1+ch), MISSING, WHITE, 2)
            c.text(x1+cw/2, y1+ch/2-8, "—", 30, MISSING_DARK, True, "mm")
            c.text(x1+cw/2, y1+ch/2+25, "AB n=0", 13, MISSING_DARK, False, "mm")
            c.polygon([(x1+cw-22, y1+5), (x1+cw-5, y1+5), (x1+cw-5, y1+22)], AMBER)
    c.rect((950, 150, 978, 178), MISSING, MISSING_DARK)
    c.text(990, 173, "Unsupported", 14, MUTED)
    c.polygon([(1115, 153), (1135, 153), (1135, 173)], AMBER)
    c.text(1148, 173, "Low denominator (<5)", 14, MUTED)
    c.save(stem)
    src = write_source(stem, read_csv(REL / f"{lower}_linkage_by_anchor_voice.csv"))
    record(metadata, stem, title, caption, f"{linkage}_Link_Rate by anchor × voice", "Low-N flags do not convert unsupported cells into zero rates.", src)


def year_x(year: int, left: float, right: float) -> float:
    return left + (right-left) * (year-1842) / (2022-1842)


def lexical_timeline(metadata: list[dict[str, str]], number: str, family: str,
                     terms: list[str], title: str, color: str) -> None:
    stem = f"figure_{number}_{family}_lexicalisation_timeline"
    caption = "Markers separate raw sustained Ngram presence and peak publication-string frequency from the earliest candidate-level target-sense anchor."
    c = Canvas(title, "First sustained Ngram · peak · candidate-level target-sense anchor", caption)
    rows = {r["term"]: r for r in read_csv(REL / "lexicalisation_comparison.csv")}
    left, right, top, bottom = 360, 1490, 205, 820
    ticks = [1842, 1880, 1920, 1960, 2000, 2022]
    for tick in ticks:
        x = year_x(tick, left, right)
        c.line([(x, top), (x, bottom)], GRID)
        c.text(x, bottom+34, tick, 14, MUTED, anchor="ma")
    row_gap = (bottom-top) / len(terms)
    for i, term in enumerate(terms):
        row = rows[term]
        y = top + (i+0.5)*row_gap
        c.text(left-24, y+6, term, 17, INK, True, "ra")
        c.line([(left, y), (right, y)], "#EEF1F4", 2)
        sustained = row["first_sustained_ngram_year"]
        peak = int(row["ngram_peak_year"])
        target = row["first_validated_target_sense_year"]
        if sustained != "UNRESOLVED":
            sx = year_x(int(sustained), left, right)
            c.circle(sx, y-10, 7, MISSING_DARK)
            c.text(sx, y-24, sustained, 12, MUTED, anchor="ma")
        px = year_x(peak, left, right)
        c.diamond(px, y, 9, color)
        c.text(px, y+28, peak, 12, color, True, "ma")
        if target != "UNRESOLVED":
            tx = year_x(int(target), left, right)
            c.rect((tx-8, y-8, tx+8, y+8), WHITE, INK, 3)
            c.text(tx, y-24, target, 12, INK, True, "ma")
        else:
            c.text(right-5, y-16, "target sense unresolved", 12, MISSING_DARK, True, "ra")
    c.circle(830, 158, 7, MISSING_DARK)
    c.text(846, 163, "First sustained", 14, MUTED)
    c.diamond(1025, 158, 8, color)
    c.text(1042, 163, "Peak", 14, MUTED)
    c.rect((1135, 150, 1151, 166), WHITE, INK, 3)
    c.text(1165, 163, "Target-sense anchor", 14, MUTED)
    c.save(stem)
    source_rows = [rows[term] for term in terms]
    src = write_source(stem, source_rows)
    record(metadata, stem, title, caption, "Three temporal markers per term", "Ngram markers are raw-string observations; target markers remain candidate-level until passage review.", src)


def node_layout(labels: list[str], counts: dict[str, int], top: float, bottom: float,
                scale: float) -> dict[str, tuple[float, float]]:
    gap = (bottom-top-scale*sum(counts.values())) / (len(labels)-1)
    cursor = top
    result = {}
    for label in labels:
        height = counts[label] * scale
        result[label] = (cursor, cursor+height)
        cursor += height + gap
    return result


def figure_10(metadata: list[dict[str, str]]) -> None:
    stem = "figure_10_inventory_structure_flow"
    title = "Structure of the constructed inventory"
    caption = "Ribbon widths are counts among the 180 Priority Candidates. This figure describes the designed inventory, not historical prevalence or passage linkage."
    c = Canvas(title, "Anchor → layer → voice", caption)
    candidates = read_csv(ROOT / "data/fear-temperature/analysis/candidate_analysis_180.csv")
    anchor_counts = Counter(r["anchor_label"] for r in candidates)
    layer_counts = Counter(r["layer_code"] for r in candidates)
    voice_counts = Counter(r["voice_code"] for r in candidates)
    al = Counter((r["anchor_label"], r["layer_code"]) for r in candidates)
    lv = Counter((r["layer_code"], r["voice_code"]) for r in candidates)
    top, bottom = 210, 835
    flow_scale = 2.8
    anchor_pos = node_layout(ANCHORS, anchor_counts, top, bottom, flow_scale)
    layers = ["A", "B", "C", "D"]
    layer_pos = node_layout(layers, layer_counts, top, bottom, flow_scale)
    voice_pos = node_layout(VOICES, voice_counts, top, bottom, flow_scale)
    x_anchor, x_layer, x_voice, node_w = 230, 785, 1360, 28
    scale = flow_scale

    a_out = {a: anchor_pos[a][0] for a in ANCHORS}
    l_in = {l: layer_pos[l][0] for l in layers}
    for a in ANCHORS:
        for l in layers:
            count = al[(a, l)]
            if not count:
                continue
            thick = count * scale
            c.ribbon(x_anchor+node_w, a_out[a], a_out[a]+thick, x_layer, l_in[l], l_in[l]+thick, LAYER_COLORS[l], 70)
            a_out[a] += thick
            l_in[l] += thick

    l_out = {l: layer_pos[l][0] for l in layers}
    v_in = {v: voice_pos[v][0] for v in VOICES}
    for l in layers:
        for v in VOICES:
            count = lv[(l, v)]
            if not count:
                continue
            thick = count * scale
            c.ribbon(x_layer+node_w, l_out[l], l_out[l]+thick, x_voice, v_in[v], v_in[v]+thick, LAYER_COLORS[l], 70)
            l_out[l] += thick
            v_in[v] += thick

    for a in ANCHORS:
        y1, y2 = anchor_pos[a]
        c.rect((x_anchor, y1, x_anchor+node_w, y2), OBJECT)
        c.text(x_anchor-16, (y1+y2)/2+5, f"{a}  {anchor_counts[a]}", 15, INK, True, "ra")
    for l in layers:
        y1, y2 = layer_pos[l]
        c.rect((x_layer, y1, x_layer+node_w, y2), LAYER_COLORS[l])
        c.text(x_layer-15, (y1+y2)/2+5, f"{LAYER_LABELS[l]}  {layer_counts[l]}", 15, INK, True, "ra")
    for v in VOICES:
        y1, y2 = voice_pos[v]
        c.rect((x_voice, y1, x_voice+node_w, y2), "#536A7A")
        c.text(x_voice+node_w+15, (y1+y2)/2-4, f"{v}  {voice_counts[v]}", 15, INK, True)
        c.text(x_voice+node_w+15, (y1+y2)/2+18, VOICE_LABELS[v], 12, MUTED)
    c.text(x_anchor, 170, "Anchor", 17, MUTED, True, "mm")
    c.text(x_layer, 170, "Layer", 17, MUTED, True, "mm")
    c.text(x_voice, 170, "Voice", 17, MUTED, True, "mm")
    c.save(stem)
    rows = []
    for a in ANCHORS:
        for l in layers:
            for v in VOICES:
                count = sum(1 for r in candidates if r["anchor_label"] == a and r["layer_code"] == l and r["voice_code"] == v)
                if count:
                    rows.append({"anchor": a, "layer": l, "voice": v, "candidate_count": count, "evidence_class": "CONSTRUCTED_INVENTORY_PATTERN"})
    src = write_source(stem, rows)
    record(metadata, stem, title, caption, "Priority Candidate count by anchor × layer × voice", "Inventory structure must not be interpreted as historical prevalence.", src)


def figure_11(metadata: list[dict[str, str]]) -> None:
    stem = "figure_11_searchability_corpus_caution"
    title = "Searchability differs across historical anchors"
    caption = "Supported, zero-result, and unsupported are query/provider states. A zero metadata result is not evidence that the language was historically absent."
    c = Canvas(title, "Internet Archive metadata discoverability among 30 Priority Candidates per anchor", caption)
    candidates = read_csv(ROOT / "data/fear-temperature/analysis/candidate_analysis_180.csv")
    rows = []
    for anchor in ANCHORS:
        subset = [r for r in candidates if r["anchor_label"] == anchor]
        supported = sum(r["search_status"] == "COMPLETED_NONZERO" for r in subset)
        zero = sum(r["search_status"] == "COMPLETED_ZERO" for r in subset)
        unsupported = len(subset) - supported - zero
        rows.append({"anchor": anchor, "supported": supported, "zero": zero, "unsupported": unsupported, "total": len(subset)})
    left, top, right, bottom = 260, 235, 1480, 800
    bar_h, gap = 55, 34
    colors = {"supported": SUPPORTED, "zero": ZERO, "unsupported": MISSING_DARK}
    for tick in [0, 10, 20, 30]:
        x = left+(right-left)*tick/30
        c.line([(x, top), (x, bottom)], GRID)
        c.text(x, bottom+30, tick, 14, MUTED, anchor="ma")
    for i, row in enumerate(rows):
        y1 = top+i*(bar_h+gap)
        y2 = y1+bar_h
        c.text(left-25, (y1+y2)/2+6, row["anchor"], 17, INK, True, "ra")
        cursor = left
        for status in ["supported", "zero", "unsupported"]:
            value = int(row[status])
            width = (right-left)*value/30
            if width:
                c.rect((cursor, y1, cursor+width, y2), colors[status])
                if width > 45:
                    c.text(cursor+width/2, (y1+y2)/2+1, value, 17, WHITE, True, "mm")
            cursor += width
        c.text(right+12, (y1+y2)/2+5, f"unsupported {row['unsupported']}", 13, MUTED)
    x = 820
    for status in ["supported", "zero", "unsupported"]:
        c.rect((x, 165, x+22, 183), colors[status])
        c.text(x+32, 182, status, 14, MUTED)
        x += 190
    c.save(stem)
    src = write_source(stem, rows)
    record(metadata, stem, title, caption, "Candidate count by bounded-search result state", "Discoverability reflects digitisation, metadata, provider indexing, and query construction.", src)


def figure_12(metadata: list[dict[str, str]]) -> None:
    stem = "figure_12_ngram_vs_validated_sense"
    title = "Raw string appearance and validated sense are different events"
    caption = "Four markers are kept separate. Candidate-level attestation and target-sense years remain provisional until source-linked passage validation."
    c = Canvas(title, "First Ngram nonzero · first sustained · candidate attestation · candidate target sense", caption)
    rows = read_csv(REL / "lexicalisation_comparison.csv")
    left, right, top, bottom = 430, 1490, 190, 860
    for tick in [1842, 1880, 1920, 1960, 2000, 2022]:
        x = year_x(tick, left, right)
        c.line([(x, top), (x, bottom)], GRID)
        c.text(x, bottom+30, tick, 13, MUTED, anchor="ma")
    gap = (bottom-top)/len(rows)
    for i, row in enumerate(rows):
        y = top+(i+0.5)*gap
        c.text(left-18, y+4, row["term"], 13, INK, True, "ra")
        c.line([(left, y), (right, y)], "#F0F2F5")
        markers = [
            (row["first_ngram_nonzero_year"], -9, "circle", MISSING_DARK),
            (row["first_sustained_ngram_year"], -3, "circle", OBJECT_2),
            (row["first_validated_attestation_year"], 4, "diamond", AMBER),
            (row["first_validated_target_sense_year"], 10, "square", INK),
        ]
        for value, offset, shape, color in markers:
            if value == "UNRESOLVED":
                continue
            x = year_x(int(value), left, right)
            if shape == "circle":
                c.circle(x, y+offset, 4, color)
            elif shape == "diamond":
                c.diamond(x, y+offset, 5, color)
            else:
                c.rect((x-4, y+offset-4, x+4, y+offset+4), WHITE, color, 2)
    legend = [
        ("circle", MISSING_DARK, "First Ngram nonzero"),
        ("circle", OBJECT_2, "First sustained"),
        ("diamond", AMBER, "Candidate attestation"),
        ("square", INK, "Candidate target sense"),
    ]
    x = 690
    for shape, color, label in legend:
        if shape == "circle": c.circle(x, 152, 5, color)
        elif shape == "diamond": c.diamond(x, 152, 6, color)
        else: c.rect((x-5, 147, x+5, 157), WHITE, color, 2)
        c.text(x+14, 157, label, 13, MUTED)
        x += 210
    c.save(stem)
    src = write_source(stem, rows)
    record(metadata, stem, title, caption, "Four temporal markers for 17 selected terms", "Raw Ngram observations must not be narrated as first historical meaning.", src)


def main() -> None:
    metadata: list[dict[str, str]] = []
    figure_01(metadata)
    unavailable_anchor_figure(metadata, "Threat")
    unavailable_anchor_figure(metadata, "Affect")
    figure_04(metadata)
    heatmap_unsupported(metadata, "Threat")
    heatmap_unsupported(metadata, "Affect")
    lexical_timeline(metadata, "07", "climate_framing", ["climatic change", "greenhouse effect", "global warming", "climate change"], "Climate framing lexicalisation", OBJECT)
    lexical_timeline(metadata, "08", "affect", ["anxiety", "climate anxiety", "eco-anxiety", "worry", "fear"], "Affect lexicalisation", AFFECT)
    lexical_timeline(metadata, "09", "threat", ["crisis", "climate crisis", "emergency", "climate emergency", "threat", "risk"], "Threat lexicalisation", THREAT)
    figure_10(metadata)
    figure_11(metadata)
    figure_12(metadata)
    write_source("figure_metadata", metadata)
    manifest = {
        "analysis_id": "fear-temperature-relational-v0.1",
        "figure_count": len(metadata),
        "formats": ["PNG", "SVG"],
        "dimensions": [W, H],
        "figures": metadata,
    }
    (OUT / "figure_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
