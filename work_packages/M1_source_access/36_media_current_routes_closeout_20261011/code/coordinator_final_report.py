#!/usr/bin/env python3
"""Frozen metadata only. Never import collectors or read their stores/bodies/raw."""
import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

INTERVAL = ["1988-01-01", "2026-09-21"]
TECHNICAL = 613617
SOCIAL_BASELINE = 988701
MONTHS = [f"{y:04}-{m:02}" for y in range(1988, 2027) for m in range(1, 13)
          if f"{y:04}-{m:02}" <= "2026-09"]
DIMENSIONS = ["stream", "frame", "snapshot", "unit", "geography_scope", "source_id",
              "carrier", "genre", "year", "era", "source_country", "source_region"]
ALIASES = {
    "source_id": ["source_id"], "carrier": ["carrier", "carrier_frame"],
    "genre": ["genre", "source_purpose_frame", "native_genre_basis"],
    "year": ["year", "publication_year", "publication_date", "publication_at"],
    "source_country": ["source_context_country", "source_country"],
    "source_region": ["source_context_region", "source_region", "stratum"],
    "frame": ["frame", "analytical_subframe"],
    "author_country": ["author_country"], "author_country_status": ["author_country_status"],
    "month": ["month", "publication_month"],
}


def integer(value):
    if value is None or str(value).strip() == "":
        return None
    number = int(str(value))
    if number < 0:
        raise ValueError("Negative acquisition count")
    return number


class Inputs:
    def __init__(self):
        self.cache, self.references, self.missing = {}, {}, set()

    def read(self, path, label=None):
        p = Path(path).resolve()
        if p.suffix in {".db", ".sqlite", ".sqlite3"} or any(
                x in {"raw", "bodies", "receipts"} for x in p.parts):
            raise ValueError("Only explicit finalized metadata inputs are permitted")
        if p not in self.cache:
            data = p.read_bytes()
            self.cache[p] = data
            self.references[str(p)] = {"label": label or p.name, "bytes": len(data),
                                      "sha256": hashlib.sha256(data).hexdigest()}
        return self.cache[p]

    def json(self, path, label=None):
        value = json.loads(self.read(path, label))
        if not isinstance(value, dict):
            raise ValueError("Summary/contract input must be a JSON object")
        return value

    def rows(self, spec):
        data = self.read(spec["path"], spec.get("label"))
        if spec["path"].endswith(".gz"):
            data = gzip.decompress(data)
        return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))

    def field(self, row, spec, name, default="unmeasured"):
        if name in spec.get("constants", {}):
            return str(spec["constants"][name])
        names = spec.get("columns", {}).get(name, ALIASES.get(name, [name]))
        if isinstance(names, str):
            names = [names]
        for key in names:
            if row.get(key) not in (None, ""):
                return str(row[key])
        self.missing.add(f"{spec.get('label', Path(spec['path']).name)}: {name} unavailable")
        return default


def value(summary, key):
    aliases = {"current_newspaper_complete_IDs": "resulting_regular_article_IDs"}
    return integer(summary.get(key, summary.get(aliases.get(key, ""))))


def quantities(contract, newspaper, social, inp):
    known = social.get("technical_list_retained_dated_numerator") == TECHNICAL
    for key in ["technical_list_new_requests", "technical_list_new_bodies"]:
        if social.get(key) not in (None, 0):
            raise ValueError("Technical-list acquisition conflicts with current scope")
        if key not in social:
            inp.missing.add(f"Social manifest: {key} not supplied")
    if not known:
        inp.missing.add("Social manifest: retained technical numerator not independently supplied")
    rows = [
        ("newspaper_regular_all_regions", "complete_article_ids", 30704,
         value(newspaper, "current_newspaper_complete_IDs"), "常规报纸（全部地区）"),
        ("newspaper_regular_original_five", "complete_article_ids", 30704, None, "原五地区常规报纸"),
        ("newspaper_wider_english", "complete_article_ids", 0, None, "新增英语地区报纸"),
        ("newspaper_supplement", "complete_article_ids", 34, None, "增刊（单列）"),
        ("newspaper_family_original", "complete_article_ids", 30738, None, "原范围报纸家族"),
        ("newspaper_titles_original_five", "contributing_title_ids", 30, None, "原五地区实际贡献报纸"),
        ("newspaper_titles_wider_english", "contributing_title_ids", 0, None, "新增地区实际贡献报纸"),
        ("campus", "retained_article_ids", 9249, value(newspaper, "historical_campus_IDs_preserved"), "校园刊物（单列）"),
        ("social_dated", "dated_authored_body_rows", SOCIAL_BASELINE,
         value(social, "usable_dated_body_total"), "社会文本：已定日期正文"),
        ("social_core", "retained_core_texts", 988717, value(social, "retained_core_total"), "社会文本：保留核心文本"),
        ("technical_list", "dated_authored_body_rows", TECHNICAL, TECHNICAL if known else None, "技术邮件列表（保留）"),
        ("creative_current_additions", "dated_native_body_rows", 0, None, "本轮创作项目文本"),
        ("social_new_contributing_sites", "contributing_site_units", 0,
         value(social, "new_site_count"), "本轮实际贡献站点"),
        ("social_new_native_author_units", "source_qualified_native_author_units", 0,
         value(social, "contributing_native_author_units"), "本轮来源内作者标识"),
        ("social_current_contributing_sources", "contributing_source_registry_ids", 0,
         len(social["contributing_source_ids"]) if isinstance(social.get("contributing_source_ids"), list) else None,
         "本轮实际贡献来源标识"),
        ("social_current_ordinary_account_units", "source_qualified_self_presented_account_units", 0,
         value(social, "contributing_ordinary_self_presented_account_units"), "本轮自述普通账号标识"),
        ("social_current_historical_author_country_unmeasured", "dated_authored_body_rows", 0,
         value(social, "historical_author_country_at_publication_unmeasured_bodies"), "本轮历史作者国别未测量"),
        ("newspaper_regular_observed_months", "observed_study_months", 461,
         value(newspaper, "regular_frame_observed_months"), "常规报纸有文本月份"),
        ("newspaper_family_observed_months", "observed_study_months", 465,
         value(newspaper, "amended_family_observed_months"), "报纸家族有文本月份"),
        ("social_observed_months", "observed_study_months", 343,
         value(social, "pooled_observed_months"), "社会文本有文本月份"),
        ("social_verified_named_actors", "verified_named_actor_families", None, None, "已核实具名作者家族"),
    ]
    result = {r[0]: dict(frame=r[0], unit=r[1], before=r[2], after=r[3], label_zh=r[4]) for r in rows}
    for explicit in contract.get("quantities", []):
        r = dict(explicit)
        for key in ["before", "after"]:
            r[key] = integer(r.get(key))
        result[r["frame"]] = {**result.get(r["frame"], {}), **r}
    for r in result.values():
        r["delta"] = r["after"] - r["before"] if None not in (r["before"], r["after"]) else None
        if r["after"] is None:
            inp.missing.add(f"Quantity: {r['frame']} final value unavailable; no aggregate invented")
    return list(result.values())


def aggregate_tables(contract, inp):
    totals, authors, seen = collections.Counter(), collections.Counter(), set()
    for spec in contract.get("tables", []):
        if spec["kind"] not in {"source_genre_era_country", "author_country"}:
            raise ValueError("Unsupported finalized table kind")
        identity = (str(Path(spec["path"]).resolve()), spec["kind"])
        if identity in seen:
            raise ValueError("Duplicate explicit table/kind input")
        seen.add(identity)
        ids = set()
        joins = []
        for join in spec.get("joins", []):
            index = {}
            for item in inp.rows(join):
                key = item[join["on"]]
                if key in index:
                    raise ValueError("Duplicate metadata join key; no ambiguous identity merge")
                index[key] = item
            joins.append((join, index))
        for row in inp.rows(spec):
            row = dict(row)
            for join, index in joins:
                match = index.get(row.get(join["on"]))
                if match is None:
                    inp.missing.add(f"{spec.get('label', Path(spec['path']).name)}: metadata join missing")
                else:
                    for canonical, field in join.get("columns", {}).items():
                        if match.get(field) not in (None, ""):
                            row[canonical] = match[field]
            if spec.get("id_column"):
                key = row[spec["id_column"]]
                if key in ids:
                    raise ValueError("Duplicate row-unit ID in finalized input")
                ids.add(key)
            count = integer(row.get(spec.get("count_column", "")))
            if count is None and spec.get("row_unit"):
                count = 1
            if count is None:
                raise ValueError("Explicit count_column or row_unit is required")
            context = [inp.field(row, spec, x, "unspecified") for x in DIMENSIONS[:5]]
            if spec["kind"] == "author_country":
                key = (*context, inp.field(row, spec, "author_country"),
                       inp.field(row, spec, "author_country_status"))
                authors[key] += count
                continue
            year = inp.field(row, spec, "year")[:4]
            era = "unmeasured"
            if year.isdigit() and 1988 <= int(year) <= 2026:
                era = ("1988-1999" if int(year) < 2000 else "2000-2009" if int(year) < 2010
                       else "2010-2019" if int(year) < 2020 else "2020-2026 (September partial)")
            key = (*context, inp.field(row, spec, "source_id"), inp.field(row, spec, "carrier"),
                   inp.field(row, spec, "genre"), year, era,
                   inp.field(row, spec, "source_country"), inp.field(row, spec, "source_region"))
            totals[key] += count
    if not authors:
        inp.missing.add("No current author-country table supplied; source country is never substituted")
    if not totals:
        inp.missing.add("No source/genre/era/country table supplied; those rollups remain empty")
    return totals, authors


def monthly(spec, inp):
    counts = collections.Counter()
    for row in inp.rows(spec):
        if row.get("source_id") in spec.get("exclude_sources", []):
            continue
        if any(str(row.get(k)) != str(v) for k, v in spec.get("equals", {}).items()):
            continue
        month = inp.field(row, spec, "month", "")[:7]
        if month not in MONTHS:
            raise ValueError("Calendar row outside fixed study months or missing month")
        count = integer(row.get(spec["count_column"]))
        if count is None:
            raise ValueError("Calendar count missing")
        counts[month] += count
    return counts


def calendars(contract, inp):
    panels = {}
    for stream, specs in contract.get("calendars", {}).items():
        before = monthly(specs["before"], inp)
        if stream == "social":
            if sum(before.values()) != SOCIAL_BASELINE:
                raise ValueError("Consolidated social baseline must equal 988701; do not add A+B again")
            if "after" in specs or "baseline_deltas" in specs:
                raise ValueError("Social accepts one consolidated baseline plus current delta only")
            if Path(specs["before"]["path"]).resolve() == Path(specs["delta"]["path"]).resolve():
                raise ValueError("Baseline and current delta cannot be the same input")
            after = before + monthly(specs["delta"], inp)
        elif "delta" in specs:
            delta = monthly(specs["delta"], inp)
            if "expected_delta_total" in specs and sum(delta.values()) != integer(specs["expected_delta_total"]):
                raise ValueError("Declared current newspaper delta does not reconcile")
            after = before + delta
        else:
            after = monthly(specs["after"], inp)
        for key, observed in [("expected_before_total", sum(before.values())),
                              ("expected_after_total", sum(after.values()))]:
            if key in specs and integer(specs[key]) != observed:
                raise ValueError("Declared frozen calendar total does not reconcile")
        panels[stream] = (before, after, specs.get("missing_months_mean_zero", False),
                          specs.get("label_zh", "范围未声明"), specs.get("geography_scope", "unspecified"))
    return panels


def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def render_png(out, metrics, panels, contract, qa_dir, qa_python):
    if not panels:
        return {"status": "not_rendered", "reason": "No frozen final calendars supplied"}
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib import font_manager, ft2font
    if not qa_dir:
        return {"status": "not_rendered", "reason": "Supply figure QA scripts directory before rendering"}
    qa = Path(qa_dir).resolve()
    sys.path.insert(0, str(qa))
    from audit_panel_alignment import require_matplotlib_panel_alignment
    font_path = contract.get("plot", {}).get("font_path")
    candidates = [font_path] if font_path else [f.fname for f in font_manager.fontManager.ttflist
                  if f.name in {"PingFang SC", "Arial Unicode MS", "Noto Sans CJK SC", "SimHei", "Hiragino Sans GB"}]
    sample = "采集前后数量月度分布常规报纸技术邮件列表保留社会文本已定日期正文研究期新增来源未提供冻结日历"
    selected = next((p for p in candidates if p and all(ord(c) in ft2font.FT2Font(p).get_charmap()
                                                      for c in sample)), None)
    if not selected:
        return {"status": "not_rendered", "reason": "No verified Chinese font; supply plot.font_path"}
    font_manager.fontManager.addfont(selected)
    plt.rcParams.update({"font.family": "sans-serif",
                         "font.sans-serif": [font_manager.FontProperties(fname=selected).get_name(), "DejaVu Sans"],
                         "font.size": 9, "axes.unicode_minus": False, "pdf.fonttype": 42,
                         "svg.fonttype": "none", "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.2))
    fig.subplots_adjust(left=.15, right=.96, bottom=.10, top=.88, wspace=.48, hspace=.58)
    colors = ["#aab5c1", "#376783"]
    for ax, stream, letter in [(axes[0, 0], "newspaper", "a"), (axes[0, 1], "social", "b")]:
        prefix = "newspaper" if stream == "newspaper" else "social"
        selected_frames = contract.get("plot", {}).get(stream + "_quantity_frames")
        rows = [r for r in metrics if (r["frame"].startswith(prefix) or
                (stream == "newspaper" and r["frame"] == "campus") or
                (stream == "social" and r["frame"] == "technical_list")) and
                (not selected_frames or r["frame"] in selected_frames) and
                r.get("unit") in {"complete_article_ids", "dated_authored_body_rows", "retained_core_texts",
                                  "retained_article_ids", "retained_creative_work_ids"}
                and None not in (r.get("before"), r.get("after"))][:6]
        for i, r in enumerate(rows):
            ax.barh(i + .16, r["before"] / 1000, height=.29, color=colors[0], label="采集前" if i == 0 else None)
            ax.barh(i - .16, r["after"] / 1000, height=.29, color=colors[1], label="采集后" if i == 0 else None)
            ax.text(max(r["before"], r["after"]) / 1000 * 1.02, i,
                    f"{r['before']:,} → {r['after']:,}", va="center", fontsize=7)
        ax.set_yticks(range(len(rows)), [r.get("label_zh", r["frame"]) for r in rows], fontsize=8)
        ax.set_xlabel("千篇 / 千条；不同计量框架单列")
        ax.set_title("报纸数量" if stream == "newspaper" else "社会文本数量", loc="left")
        if rows:
            ax.set_xlim(0, max(max(r["before"], r["after"]) for r in rows) / 1000 * 1.65)
            ax.legend(fontsize=8)
        else:
            ax.text(.5, .5, "未提供可比数量", ha="center", transform=ax.transAxes)
        ax.annotate(letter, (0, 1), xycoords="axes fraction", xytext=(-18, 14),
                    textcoords="offset points", weight="bold", fontsize=11)
    dates = [dt.datetime.strptime(m, "%Y-%m") for m in MONTHS]
    for ax, stream, letter in [(axes[1, 0], "newspaper", "c"), (axes[1, 1], "social", "d")]:
        if stream in panels:
            before, after, zero, label, _ = panels[stream]
            ax.plot(dates, [before.get(m, 0 if zero else None) for m in MONTHS], color=colors[0], lw=.8, label="采集前")
            ax.plot(dates, [after.get(m, 0 if zero else None) for m in MONTHS], color=colors[1], lw=.9, label="采集后")
            ax.set_title(label, loc="left", fontsize=9)
            ax.legend(fontsize=8)
        else:
            ax.text(.5, .5, "未提供冻结日历", ha="center", transform=ax.transAxes)
        ax.set_xlim(dates[0], dates[-1])
        ax.xaxis.set_major_locator(mdates.YearLocator(8))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.set_ylabel("月度数量")
        ax.annotate(letter, (0, 1), xycoords="axes fraction", xytext=(-18, 14),
                    textcoords="offset points", weight="bold", fontsize=11)
    fig.suptitle("当前媒体采集：数量变化与月度分布", fontsize=15, y=.97)
    fig.text(.15, .025, "研究期：1988-01-01—2026-09-21（末月不完整）；计数为冻结元数据，非代表性或情绪测量。", fontsize=8)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig, json_out=str(out / "FIGURE_ALIGNMENT.json"),
        overlay_svg=str(out / "FIGURE_ALIGNMENT.svg"), tolerance_pt=1.5,
        gutter_tolerance_pt=1.5, axes=list(axes.flat), panel_ids=["a", "b", "c", "d"],
        row_groups=[["a", "b"], ["c", "d"]], column_groups=[["a", "c"], ["b", "d"]],
        require_panel_labels=True, strict=True)
    pdf = out / "MEDIA_CLOSEOUT_ZH.pdf"
    fig.savefig(pdf)
    fig.savefig(out / "MEDIA_CLOSEOUT_ZH.svg")
    text_check = subprocess.run([qa_python, str(qa / "audit_pdf_text.py"), str(pdf),
        "--min-pt", "5", "--json"], capture_output=True, text=True)
    (out / "FIGURE_TEXT_QA.json").write_text(text_check.stdout, encoding="utf-8")
    collision = subprocess.run([qa_python, str(qa / "audit_figure_collisions.py"), str(pdf),
        "--json-out", str(out / "FIGURE_COLLISION_QA.json")], capture_output=True, text=True)
    if text_check.returncode or collision.returncode:
        plt.close(fig)
        return {"status": "blocked_by_rendered_QA", "text_exit": text_check.returncode,
                "collision_exit": collision.returncode, "visual_review_required": True}
    fig.savefig(out / "MEDIA_CLOSEOUT_ZH.png", dpi=300)
    plt.close(fig)
    return {"status": "rendered", "dpi": 300, "visual_review_required": True,
            "interpretation": "Observed quantities; no statistical uncertainty or inferred emotions"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--qa-scripts")
    parser.add_argument("--qa-python", help="Python with PyMuPDF for backend-neutral PDF checks")
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    inp = Inputs()
    c = inp.json(args.contract, "Coordinator frozen input contract")
    if not all(c.get(k) is True for k in ["frozen", "writer_exit_verified", "changed_tranche_accepted"]):
        raise ValueError("Require actual frozen metadata, verified writer exit and accepted changed tranche")
    if c.get("publication_interval") != INTERVAL:
        raise ValueError("Fixed publication interval must remain unchanged")
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use an empty new final-artifact output directory; preserve prior reports")
    n = inp.json(c["newspaper_summary"], "Newspaper frozen final summary")
    s = inp.json(c["social_summary"], "Social frozen collection manifest")
    for summary in (n, s):
        if summary.get("publication_interval") != INTERVAL:
            raise ValueError("Final summary publication interval mismatch")
    metrics = quantities(c, n, s, inp)
    totals, authors = aggregate_tables(c, inp)
    panels = calendars(c, inp)
    if "social" in panels and value(s, "usable_dated_body_total") is not None:
        if sum(panels["social"][1].values()) != value(s, "usable_dated_body_total"):
            raise ValueError("Social consolidated baseline plus current delta disagrees with frozen manifest")
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "QUANTITIES_BEFORE_AFTER.csv", ["frame", "unit", "before", "after", "delta", "geography_scope"],
              ([r.get(k) for k in ["frame", "unit", "before", "after", "delta", "geography_scope"]] for r in metrics))
    write_csv(out / "SOURCE_GENRE_ERA_COUNTRY.csv", DIMENSIONS + ["count"], ((*key, count) for key, count in sorted(totals.items())))
    for name, dimensions in [("SOURCE_TOTALS", ["source_id"]), ("GENRE_TOTALS", ["carrier", "genre"]),
                              ("ERA_TOTALS", ["era"]), ("SOURCE_COUNTRY_TOTALS", ["source_country", "source_region"])]:
        columns = DIMENSIONS[:5] + dimensions
        rolled = collections.Counter()
        for key, count in totals.items():
            row = dict(zip(DIMENSIONS, key))
            rolled[tuple(row[k] for k in columns)] += count
        write_csv(out / (name + ".csv"), columns + ["count"], ((*key, count) for key, count in sorted(rolled.items())))
    historical_unknown = value(s, "historical_author_country_at_publication_unmeasured_bodies")
    historical_rows = [] if historical_unknown is None else [
        (*("social", "current_nontechnical_social", "current_delta", "dated_authored_body_rows", "author_country_historical_at_publication"),
         "unmeasured", "historical_at_publication_unmeasured", historical_unknown)]
    write_csv(out / "AUTHOR_COUNTRY_AND_UNKNOWN.csv", DIMENSIONS[:5] + ["author_country", "author_country_status", "count"],
              [(*("social", "accepted_baseline", "before", "dated_authored_body_rows", "author_location_unmeasured"),
                "unmeasured", "unmeasured_in_accepted_baseline", SOCIAL_BASELINE),
               (*("newspaper", "regular_original_five", "before", "complete_article_ids", "author_location_unmeasured"),
                "unmeasured", "unmeasured_in_accepted_baseline", 30704),
               (*("newspaper", "separate_Supplement", "before", "complete_article_ids", "author_location_unmeasured"),
                "unmeasured", "unmeasured_in_accepted_baseline", 34),
               (*("campus", "preserved_campus", "before", "retained_article_ids", "author_location_unmeasured"),
                "unmeasured", "unmeasured_in_accepted_baseline", 9249)] +
              [(*key, count) for key, count in sorted(authors.items())] + historical_rows)
    write_csv(out / "CURRENT_AUTHOR_ROLE_COUNTS.csv", ["snapshot", "unit", "author_role", "count", "evidence_limit"],
              (("current_delta", "dated_authored_body_rows", role, integer(count),
                "Source/profile declaration or metadata attribution; not independently verified people")
               for role, count in sorted(s.get("author_role_new_body_counts", {}).items())))
    write_csv(out / "MONTHLY_DISTRIBUTION.csv", ["stream", "month", "before", "after", "geography_scope", "missing_months_mean_zero"],
              ([stream, m, before.get(m, 0 if zero else None), after.get(m, 0 if zero else None), scope, zero]
               for stream, (before, after, zero, _, scope) in panels.items() for m in MONTHS))
    figure = {"status": "not_requested"}
    if not args.metadata_only:
        try:
            figure = render_png(out, metrics, panels, c, args.qa_scripts,
                                args.qa_python or c.get("plot", {}).get("qa_python") or sys.executable)
        except (ImportError, RuntimeError, OSError) as exc:
            figure = {"status": "not_rendered", "reason": str(exc), "visual_review_required": True}
    total = value(s, "usable_dated_body_total")
    report = ["# Closed media acquisition results", "",
        "The current collection span ran from 12:24:42 to the prospectively amended 19:24:42 AEST deadline on 11 October 2026 (seven hours). "
        "The two existing collectors continued already opened executable routes after the 17:57:07 AEST amendment. "
        "The prospectively amended collection deadline was 19:24:42 AEST / 09:24:42 UTC; delivery target was 19:57:07 AEST / 09:57:07 UTC. "
        "No new route opening, collector, counter reset or budget increase was released.", "",
        f"Publication interval: **1988-01-01 through 2026-09-21**, with September partial. Final snapshot: {c.get('snapshot_at_utc', 'unspecified')}. "
        "Publication, source observation, retrieval and content-version times remain separate.", "",
        "| Frame | Unit | Before | Final | Change |", "| --- | --- | ---: | ---: | ---: |"]
    show = lambda x: "unavailable" if x is None else f"{x:,}"
    report.extend(f"| {r['frame']} | {r['unit']} | {show(r['before'])} | {show(r['after'])} | {show(r['delta'])} |" for r in metrics)
    stops = c.get("production_stops", {})
    social_stop = stops.get("social", {})
    newspaper_stop = stops.get("newspaper", {})
    report += ["", f"Newspaper stop event ({newspaper_stop.get('event_kind', 'production_stop_marker')}): {newspaper_stop.get('at_utc', 'unavailable')}; "
        f"reason: {newspaper_stop.get('reason', n.get('stop_reason', 'unavailable'))}. "
        f"Actual social production stop: {social_stop.get('at_utc', s.get('production_stop_at_utc', 'unavailable'))}; "
        f"reason: {social_stop.get('reason', s.get('production_stop_reason', 'unavailable'))}. "
        "Report snapshot timestamps are not used as production-stop timestamps."]
    report += ["", "Original five-region regular newspapers, wider English additions, Supplement, newspaper family, campus publications and creative projects retain separate units and denominators. "
        "The all-region regular total must not stand for the original five-region geography comparison. Supplement exports can be cumulative. Candidate/prepared sources are not contributing titles or sites.", "",
        f"The retained technical-list numerator is **{TECHNICAL:,}**. Its share of the supplied final dated social total is " +
        (f"{TECHNICAL / total:.4%}." if total else "unavailable.") +
        " Zero new technical-list requests/bodies requires the frozen manifest evidence; no retained technical material is deleted or reclassified.", "",
        "Source-country/community context is separate from author country. The accepted baseline's individual author-country distribution is unmeasured. "
        "Current self-declarations are time-specific; missing values remain explicit. Two Dave Bonta sites are one evidenced named actor. "
        "Native account/site/source-qualified author IDs do not establish independent publishing parents or a global distinct-person total. "
        "The current historical-author-country unmeasured quantity is reported separately from current country declarations.", "",
        f"Current social body-role counts: {json.dumps(s.get('author_role_new_body_counts', {}), sort_keys=True)}. "
        "These body counts and source-qualified account/site units do not establish a global distinct-person denominator. "
        "The contributing-source count can include retained bodies loaded before the route freeze; frozen-route inventory is a different unit.", "",
        "Monthly distributions describe observed source frames. Calendar absence, source pre-foundation inapplicability and unresolved access/archive inventory remain distinct. "
        "No peak smoothing, semantic exclusion, climate-event attribution or emotion measurement was performed by this reporting builder.", "",
        f"Chinese figure status: {figure['status']}; rendered figures require final-size visual review. "
        "Finalized tables retain their declared before/delta/final basis; these bases are not summed together implicitly.", "",
        "Publish this accepted acquisition result, implementation and English project-log entry together in a new sibling package after package35 "
        "(recommended package36, subject to coordinator naming). Preserve package35's frozen geography supplement. "
        "Keep raw material, controls, owner/dispatch state, queues and individual receipts local; curate metadata-only publication files under existing permissions."]
    if inp.missing:
        report += ["", "Missing supplied fields and limitations:", ""] + ["- " + x for x in sorted(inp.missing)]
    (out / "README.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    summary = {"publication_interval": INTERVAL, "snapshot_at_utc": c.get("snapshot_at_utc"),
        "collection_deadline_at_utc": "2026-10-11T09:24:42Z", "delivery_target_at_utc": "2026-10-11T09:57:07Z",
        "technical_list_retained_dated_numerator": TECHNICAL, "figure": figure, "missing_fields": sorted(inp.missing),
        "input_references": list(inp.references.values()), "stores_raw_bodies_read": False,
        "A_B_calendars_reapplied": False, "geography_inferred": False, "semantic_models_executed": False}
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    files = {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(out.iterdir()) if p.is_file()}
    manifest = {"publication_interval": INTERVAL, "files": files, "file_bytes_excluding_this_manifest": sum(x["bytes"] for x in files.values()),
                "accounting": "Charge all publication files, this manifest and the largest atomic companion in shared/social accounting as applicable."}
    (out / "FINAL_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "figure_status": figure["status"], "missing_fields": len(inp.missing)}))


if __name__ == "__main__":
    main()
