#!/usr/bin/env python3
"""Re-render the existing EDA v0.2 figures at native ultra-high resolution.

This module deliberately imports and calls the existing chart functions so the
data, calculations, ordering, colours, smoothing choices, and annotations stay
unchanged. Only the output canvas, font scale, stroke scale, and PNG metadata
are changed.
"""

from __future__ import annotations

import hashlib
import html
import importlib.util
import json
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
BASE_SCRIPT = ROOT / "scripts" / "fear-temperature" / "generate_eda_figures.py"
BASE_OUT = ROOT / "figures" / "fear-temperature" / "eda-v02"
OUT = BASE_OUT / "ultra_hd"
SOURCES = OUT / "sources"

BASE_W = 1600
BASE_H = 920
SCALE = 5
PNG_W = BASE_W * SCALE
PNG_H = BASE_H * SCALE
PNG_DPI = 601


def load_base_module():
    spec = importlib.util.spec_from_file_location("generate_eda_figures_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_base_module()


def scaled_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    return ImageFont.truetype(
        f"/System/Library/Fonts/Supplemental/{name}", size * SCALE
    )


def scaled_points(points: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    return [(x * SCALE, y * SCALE) for x, y in points]


class UHDCanvas:
    """Five-times-native raster canvas with the original SVG coordinate system."""

    def __init__(self, title: str, subtitle: str, warning: str):
        self.image = Image.new("RGB", (PNG_W, PNG_H), base.BG)
        self.draw = ImageDraw.Draw(self.image, "RGBA")
        self.svg: list[str] = [
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{PNG_W}" '
                f'height="{PNG_H}" viewBox="0 0 {BASE_W} {BASE_H}">'
            ),
            f'<rect width="{BASE_W}" height="{BASE_H}" fill="{base.BG}"/>',
        ]
        self.content_bbox = [float(PNG_W), float(PNG_H), 0.0, 0.0]
        self.text(70, 48, title, 34, base.INK, True)
        self.text(70, 94, subtitle, 18, base.MUTED)
        self.text(70, 875, warning, 15, base.MUTED)

    def _track(self, bbox: tuple[float, float, float, float]) -> None:
        x1, y1, x2, y2 = bbox
        self.content_bbox[0] = min(self.content_bbox[0], x1)
        self.content_bbox[1] = min(self.content_bbox[1], y1)
        self.content_bbox[2] = max(self.content_bbox[2], x2)
        self.content_bbox[3] = max(self.content_bbox[3], y2)

    def text(
        self,
        x: float,
        y: float,
        value: object,
        size: int,
        color: str = base.INK,
        bold: bool = False,
        anchor: str = "la",
    ) -> None:
        txt = str(value)
        pil_anchor = {"la": "la", "ma": "ma", "ra": "ra", "mm": "mm"}.get(anchor, "la")
        sx, sy = x * SCALE, y * SCALE
        text_font = scaled_font(size, bold)
        self.draw.text((sx, sy), txt, fill=color, font=text_font, anchor=pil_anchor)
        self._track(tuple(float(v) for v in self.draw.textbbox((sx, sy), txt, font=text_font, anchor=pil_anchor)))
        svg_anchor = {"la": "start", "ma": "middle", "ra": "end", "mm": "middle"}.get(anchor, "start")
        weight = "700" if bold else "400"
        baseline = "middle" if anchor == "mm" else "auto"
        self.svg.append(
            f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-family="Arial,sans-serif" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{svg_anchor}" '
            f'dominant-baseline="{baseline}">{html.escape(txt)}</text>'
        )

    def rect(
        self,
        xy: tuple[float, float, float, float],
        fill: str,
        outline: str | None = None,
        width: int = 1,
        alpha: int = 255,
    ) -> None:
        scaled = tuple(v * SCALE for v in xy)
        rgba_fill = fill + (f"{alpha:02x}" if len(fill) == 7 and alpha < 255 else "")
        self.draw.rectangle(scaled, fill=rgba_fill, outline=outline, width=max(1, width * SCALE))
        self._track(tuple(float(v) for v in scaled))
        x1, y1, x2, y2 = xy
        self.svg.append(
            f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{x2-x1:.1f}" height="{y2-y1:.1f}" '
            f'fill="{fill}" fill-opacity="{alpha/255:.3f}" stroke="{outline or "none"}" stroke-width="{width}"/>'
        )

    def line(
        self,
        xy: list[tuple[float, float]],
        fill: str,
        width: int = 2,
        alpha: int = 255,
    ) -> None:
        points = scaled_points(xy)
        rgba_fill = fill + (f"{alpha:02x}" if len(fill) == 7 and alpha < 255 else "")
        self.draw.line(points, fill=rgba_fill, width=max(1, width * SCALE), joint="curve")
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        pad = width * SCALE / 2
        self._track((min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad))
        svg_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
        self.svg.append(
            f'<polyline points="{svg_points}" fill="none" stroke="{fill}" '
            f'stroke-opacity="{alpha/255:.3f}" stroke-width="{width}" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )

    def polygon(
        self,
        xy: list[tuple[float, float]],
        fill: str,
        alpha: int = 255,
        outline: str | None = None,
    ) -> None:
        points = scaled_points(xy)
        rgba_fill = fill + (f"{alpha:02x}" if len(fill) == 7 and alpha < 255 else "")
        self.draw.polygon(points, fill=rgba_fill, outline=outline)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        self._track((min(xs), min(ys), max(xs), max(ys)))
        svg_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
        self.svg.append(
            f'<polygon points="{svg_points}" fill="{fill}" fill-opacity="{alpha/255:.3f}" '
            f'stroke="{outline or "none"}"/>'
        )

    def circle(
        self,
        x: float,
        y: float,
        r: float,
        fill: str,
        outline: str | None = None,
    ) -> None:
        sx, sy, sr = x * SCALE, y * SCALE, r * SCALE
        bbox = (sx - sr, sy - sr, sx + sr, sy + sr)
        self.draw.ellipse(bbox, fill=fill, outline=outline, width=SCALE if outline else 1)
        self._track(bbox)
        self.svg.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{outline or "none"}"/>'
        )

    def save(self, stem: str, bbox_inches: str = "tight") -> tuple[Path, Path]:
        """Save a native UHD image after a tight content-boundary check.

        ``bbox_inches`` mirrors the requested Matplotlib export contract. The
        project renderer is Pillow-based, so tightness is enforced by asserting
        the complete tracked content bounding box lies inside the fixed canvas.
        """
        if bbox_inches != "tight":
            raise ValueError("UHD exports require bbox_inches='tight'")
        x1, y1, x2, y2 = self.content_bbox
        if x1 < 0 or y1 < 0 or x2 > PNG_W or y2 > PNG_H:
            raise RuntimeError(
                f"Content would be clipped for {stem}: bbox={self.content_bbox}, canvas={(PNG_W, PNG_H)}"
            )
        png = OUT / f"{stem}_uhd.png"
        svg = OUT / f"{stem}_uhd.svg"
        self.image.save(png, format="PNG", dpi=(PNG_DPI, PNG_DPI), compress_level=6)
        self.svg.append("</svg>")
        svg.write_text("\n".join(self.svg) + "\n", encoding="utf-8")
        return png, svg


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_all() -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    SOURCES.mkdir(parents=True, exist_ok=True)
    base.OUT = OUT
    base.SOURCES = SOURCES
    base.Canvas = UHDCanvas

    candidate = pd.read_csv(base.ANALYSIS / "candidate_analysis_180.csv", keep_default_na=False)
    layers = pd.read_csv(base.ANALYSIS / "anchor_layer_counts.csv")
    voices = pd.read_csv(base.ANALYSIS / "anchor_voice_counts.csv")
    anchor_family = pd.read_csv(base.ANALYSIS / "anchor_family_counts.csv")
    voice_family = pd.read_csv(base.ANALYSIS / "voice_family_counts.csv")
    series = base.dedup_term_series()

    base.stacked_bars(layers, ["A", "B", "C", "D"], "Composition of the constructed lexical inventory",
                      "Priority Candidate counts by historical anchor and lexical layer", "Inventory composition ≠ historical prevalence.",
                      "visual_01a_anchor_layer_counts", False, base.LAYER_COLORS)
    base.stacked_bars(layers, ["A", "B", "C", "D"], "Composition of the constructed lexical inventory",
                      "Within-anchor percentage by lexical layer", "Within-anchor shares describe the constructed inventory, not prevalence in historical language.",
                      "visual_01b_anchor_layer_percentages", True, base.LAYER_COLORS)
    base.stacked_bars(voices, ["V1", "V2", "V3", "V4", "V5"], "Voice composition of the constructed lexical inventory",
                      "Priority Candidate counts by historical anchor and substantive voice", "Speaker/source composition can explain apparent lexical differences; absence is not imputed.",
                      "visual_02_anchor_voice_counts", False, base.VOICE_COLORS)
    base.heatmap(anchor_family, "family", "candidate_count", "Lexical-family composition by anchor",
                 "Candidate counts for 14 controlled semantic families across six anchors", "Inventory counts ≠ corpus frequency or historical prevalence.",
                 "visual_03a_anchor_family_counts", base.FAMILIES, base.ANCHORS)
    base.heatmap(anchor_family, "family", "candidate_count", "Within-family normalized inventory presence",
                 "Each family is scaled to its own maximum across anchors", "Within-family normalized display — not frequency.",
                 "visual_03b_anchor_family_row_normalized", base.FAMILIES, base.ANCHORS, True)
    vf = voice_family.rename(columns={"voice": "row", "family": "anchor"})
    base.heatmap(vf, "row", "candidate_count", "Voice × lexical-family reconstruction",
                 "Candidate counts expose which voices contribute to each family", "This is source/speaker composition in the constructed inventory, not social prevalence.",
                 "visual_04_voice_family_heatmap", ["V1", "V2", "V3", "V4", "V5"], base.FAMILIES)

    climate_terms = ["climatic change", "greenhouse effect", "global warming", "climate change"]
    climate = series[series.term.isin(climate_terms)].copy()
    base.line_chart(climate, "Climate-framing string trajectories", "Unsmoothed annual Google Books Ngram values, 1842–2022",
                    "Raw annual string frequency; no causal or reception claim. Generic/cross-sense occurrences still require passage validation.",
                    "visual_05_climate_framing_trajectories")
    modern_terms = ["climate crisis", "climate emergency", "climate anxiety", "eco-anxiety"]
    modern = series[series.term.isin(modern_terms)].copy()
    base.line_chart(modern, "Modern specialised climate compounds", "Raw unsmoothed annual Google Books Ngram values, 1842–2022",
                    "Low-frequency strings may be affected by corpus/OCR artefacts; string occurrence is not validated meaning.",
                    "visual_06a_modern_compounds_raw")
    base.line_chart(modern, "Modern specialised climate compounds", "Term-normalized display of each raw unsmoothed annual trajectory",
                    "Term-normalized display — not corpus frequency. Raw values remain in the paired source table and raw-scale figure.",
                    "visual_06b_modern_compounds_normalized", True)
    base.emergence_figure(series)
    base.scatter_figure(candidate)
    base.grouped_status_bars(candidate, "anchor_label", "dictionary_status", "Dictionary treatment across anchors",
                             "Candidate-level lexicographic status", "Lexicalisation/technicalisation diagnostic only; not direct semantic evolution.",
                             "visual_09_dictionary_status_by_anchor", ["DIRECT_HEADWORD", "TECHNICAL_GLOSSARY", "NO_STANDALONE_HEADWORD"])
    search_frame = candidate.copy()
    search_frame["search_display"] = search_frame.search_status.map(
        {"COMPLETED_NONZERO": "SUCCEEDED", "COMPLETED_ZERO": "ZERO_RESULT"}
    ).fillna("UNRESOLVED")
    base.grouped_status_bars(search_frame, "anchor_label", "search_display", "Searchability and archival bias",
                             "Internet Archive metadata-search outcomes by anchor", "Easier modern retrieval must not be interpreted as historical lexical abundance.",
                             "visual_10_searchability_bias", ["SUCCEEDED", "ZERO_RESULT", "UNRESOLVED"])
    base.missingness_figure(candidate)
    base.alluvial_figure(candidate)

    return [
        "visual_01a_anchor_layer_counts", "visual_01b_anchor_layer_percentages",
        "visual_02_anchor_voice_counts", "visual_03a_anchor_family_counts",
        "visual_03b_anchor_family_row_normalized", "visual_04_voice_family_heatmap",
        "visual_05_climate_framing_trajectories", "visual_06a_modern_compounds_raw",
        "visual_06b_modern_compounds_normalized", "visual_07_ngram_vs_validated_attestation",
        "visual_08_ngram_vs_search_discoverability", "visual_09_dictionary_status_by_anchor",
        "visual_10_searchability_bias", "visual_11_candidate_missingness_heatmap",
        "visual_12_structural_alluvial",
    ]


def validate(stems: list[str]) -> dict[str, object]:
    records: list[dict[str, object]] = []
    failures: list[str] = []
    for stem in stems:
        png = OUT / f"{stem}_uhd.png"
        svg = OUT / f"{stem}_uhd.svg"
        source_copy = SOURCES / f"{stem}_source.csv"
        source_original = BASE_OUT / "sources" / f"{stem}_source.csv"
        svg_original = BASE_OUT / f"{stem}.svg"
        try:
            with Image.open(png) as image:
                image.verify()
            with Image.open(png) as image:
                image.load()
                width, height = image.size
                dpi = image.info.get("dpi", (0, 0))
                png_format = image.format
            ET.parse(svg)
            source_match = sha256(source_copy) == sha256(source_original)
            svg_content_match = (
                svg.read_text(encoding="utf-8").splitlines()[1:]
                == svg_original.read_text(encoding="utf-8").splitlines()[1:]
            )
            record = {
                "figure_id": stem,
                "png": png.relative_to(ROOT).as_posix(),
                "svg": svg.relative_to(ROOT).as_posix(),
                "pixel_width": width,
                "pixel_height": height,
                "long_edge_px": max(width, height),
                "dpi_x": round(float(dpi[0]), 3),
                "dpi_y": round(float(dpi[1]), 3),
                "png_format": png_format,
                "png_open_check": "PASS",
                "svg_parse_check": "PASS",
                "svg_content_matches_original_excluding_canvas_header": svg_content_match,
                "source_sha256_matches_original": source_match,
                "png_bytes": png.stat().st_size,
                "svg_bytes": svg.stat().st_size,
            }
            records.append(record)
            if width != PNG_W or height != PNG_H:
                failures.append(f"{stem}: unexpected dimensions {width}×{height}")
            if max(width, height) < 6000:
                failures.append(f"{stem}: long edge below 6000 px")
            if min(float(dpi[0]), float(dpi[1])) < 600:
                failures.append(f"{stem}: embedded DPI below 600")
            if png_format != "PNG":
                failures.append(f"{stem}: not a PNG")
            if not source_match:
                failures.append(f"{stem}: regenerated source table differs from original")
            if not svg_content_match:
                failures.append(f"{stem}: SVG drawing content differs from original")
        except Exception as exc:
            failures.append(f"{stem}: {exc}")

    unexpected_jpeg = sorted(
        path.name for path in OUT.iterdir() if path.suffix.casefold() in {".jpg", ".jpeg"}
    )
    if unexpected_jpeg:
        failures.append(f"JPEG files present: {unexpected_jpeg}")

    result: dict[str, object] = {
        "status": "PASS" if not failures else "FAIL",
        "figure_count": len(records),
        "png_count": len(list(OUT.glob("*_uhd.png"))),
        "svg_count": len(list(OUT.glob("*_uhd.svg"))),
        "native_scale_factor": SCALE,
        "expected_pixel_dimensions": [PNG_W, PNG_H],
        "embedded_png_dpi": PNG_DPI,
        "bbox_inches": "tight",
        "bbox_implementation": "tracked content bounds must lie fully inside the native UHD canvas",
        "jpeg_count": len(unexpected_jpeg),
        "chart_logic_source": BASE_SCRIPT.relative_to(ROOT).as_posix(),
        "records": records,
        "failures": failures,
    }
    (OUT / "uhd_validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (OUT / "figure_manifest.json").write_text(json.dumps({
        "version": "exploratory-analysis-v0.2-ultra-hd",
        "figure_count": len(stems),
        "formats": ["png", "svg"],
        "png_dimensions": [PNG_W, PNG_H],
        "png_dpi": PNG_DPI,
        "native_scale_factor": SCALE,
        "bbox_inches": "tight",
        "content_changes": "none",
        "generator": "scripts/fear-temperature/generate_eda_figures_uhd.py",
        "figures": [f"{stem}_uhd" for stem in stems],
    }, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise RuntimeError("; ".join(failures))
    return result


def main() -> None:
    stems = render_all()
    result = validate(stems)
    print(json.dumps({
        "status": result["status"],
        "figure_count": result["figure_count"],
        "png_dimensions": result["expected_pixel_dimensions"],
        "png_dpi": result["embedded_png_dpi"],
        "output_dir": OUT.relative_to(ROOT).as_posix(),
    }, indent=2))


if __name__ == "__main__":
    main()
