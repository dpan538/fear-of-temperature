"""Read existing ledgers and render one bounded government coverage snapshot."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "work_packages/M1_source_access"
UK_CSV = BASE / "07_historical_government_acquisition/zero_month_policy_recovery/reports/monthly_reference_availability_corrected.csv"
UK_DB = BASE / "06_government_content_acquisition/fear_temperature_government_content.duckdb"
US_CSV = BASE / "09_us_au_government_acquisition/reports/monthly_progress.csv"
US_METRICS = BASE / "09_us_au_government_acquisition/reports/quality_metrics.json"
EU_CSV = BASE / "10_eu_cellar_acquisition/reports/eu_monthly_status.csv"
EU_LEDGER = BASE / "10_eu_cellar_acquisition/reports/eu_work_dispositions.csv"
EU_LOG = BASE / "10_eu_cellar_acquisition/manifests/item_supervisor.log"
EU_STATE = BASE / "10_eu_cellar_acquisition/manifests/item_supervisor_state.json"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def number(value: str | None) -> int:
    return int(value) if value and value.isdigit() else 0


def shifted(year: int, month: int, offset: int) -> str:
    index = year * 12 + month - 1 + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def main() -> None:
    uk_count: Counter[str] = Counter()
    uk_text: Counter[str] = Counter()
    for record in rows(UK_CSV):
        month = record["year_month"]
        uk_count[month] += number(record["record_count"])
        uk_text[month] += number(record["text_record_count"])

    us_usable_stratum_hits: Counter[str] = Counter()
    for record in rows(US_CSV):
        if record["jurisdiction"] == "US_federal":
            us_usable_stratum_hits[record["year_month"]] += number(
                record["n_usable_parents"]
            )

    eu_months = {record["year_month"]: record for record in rows(EU_CSV)}
    eu_extracted_ids: dict[str, set[str]] = {}
    for record in rows(EU_LEDGER):
        if record["disposition"] == "source_text_extracted_relevance_unreviewed":
            eu_extracted_ids.setdefault(record["year_month"], set()).add(
                record["work_uri"]
            )
    # The dated disposition report trails the live supervisor. A month strictly before
    # the active month has been completed; merge its saved/extracted Work outcomes.
    current_eu_month = json.loads(EU_STATE.read_text())["month"]
    with EU_LOG.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            month = event.get("month", "")
            if (
                month
                and month < current_eu_month
                and event.get("status") == "downloaded"
                and event.get("extraction") == "text_extracted"
                and event.get("work")
            ):
                eu_extracted_ids.setdefault(month, set()).add(event["work"])
    eu_extracted_work = Counter(
        {month: len(ids) for month, ids in eu_extracted_ids.items()}
    )

    months = sorted(uk_count)
    output_rows = []
    for month in months:
        uk = uk_text[month] > 0
        us = us_usable_stratum_hits[month] > 0
        eu = eu_extracted_work[month] > 0
        output_rows.append(
            {
                "year_month": month,
                "uk_independent_records": uk_count[month],
                "uk_records_with_text": uk_text[month],
                "us_usable_agency_genre_hits": us_usable_stratum_hits[month],
                "eu_enumerated_works": number(eu_months[month]["enumerated_works"]),
                "eu_works_with_extracted_text": eu_extracted_work[month],
                "pooled_government_text_present": int(uk or us or eu),
                "climate_relevance_assessed": "no",
                "media_text_present": "not_collected",
                "public_text_present": "not_collected",
            }
        )
    with (OUT / "monthly_government_presence.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    data = np.array(
        [
            [int(uk_text[month] > 0) for month in months],
            [int(us_usable_stratum_hits[month] > 0) for month in months],
            [int(eu_extracted_work[month] > 0) for month in months],
            [record["pooled_government_text_present"] for record in output_rows],
        ],
        dtype=int,
    )
    fig, ax = plt.subplots(figsize=(14, 4.2))
    fig.subplots_adjust(left=0.15, right=0.99, top=0.78, bottom=0.29)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f0f2f4")
    lane_colors = ["#244d6b", "#a45b25", "#605285", "#187c75"]
    for lane, color in enumerate(lane_colors):
        masked = np.ma.masked_where(data[lane] == 0, data[lane])
        ax.imshow(
            masked[np.newaxis, :],
            extent=(-0.5, len(months) - 0.5, lane - 0.38, lane + 0.38),
            cmap=ListedColormap([color]),
            vmin=0,
            vmax=1,
            aspect="auto",
            interpolation="nearest",
        )
    for event, label in [("1997-12", "Kyoto"), ("2015-12", "Paris")]:
        index = months.index(event)
        ax.axvline(index, color="#8a99a4", linestyle="--", linewidth=0.9, zorder=0)
        ax.text(index + 1.5, -0.62, label, fontsize=8, color="#536474", va="top")
    years = [year for year in range(1988, 2027) if year % 4 == 0]
    ax.set_xticks([months.index(f"{year}-01") for year in years])
    ax.set_xticklabels([str(year) for year in years], fontsize=8, color="#435466")
    ax.set_yticks(range(4))
    ax.set_yticklabels(
        ["UK", "US EPA/DOE", "EU Commission", "Pooled government"],
        fontsize=9,
        color="#253443",
    )
    ax.set_ylim(3.6, -0.9)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.suptitle(
        "Government text observed by month, 1988–September 2026",
        x=0.15,
        y=0.94,
        ha="left",
        fontsize=14,
        fontweight="bold",
        color="#182b38",
    )
    fig.text(
        0.15,
        0.08,
        "Saved and extracted text; grey = no text in this snapshot. Presence does not establish climate relevance, response or historical completeness.",
        fontsize=7.7,
        color="#526372",
    )
    fig.savefig(OUT / "government_temporal_presence.png", dpi=220, facecolor="white")
    plt.close(fig)

    connection = duckdb.connect(str(UK_DB), read_only=True)
    uk_period = dict(
        connection.execute(
            """SELECT CASE WHEN publication_date < '1994-01-01' THEN '1988–1993'
                       WHEN publication_date < '2003-01-01' THEN '1994–2002'
                       WHEN publication_date < '2014-01-01' THEN '2003–2013'
                       ELSE '2014–2026' END, count(*)
                FROM documents GROUP BY 1"""
        ).fetchall()
    )
    shape = {
        table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in [
            "documents",
            "content_objects",
            "document_content_objects",
            "content_versions",
            "text_segments",
        ]
    }
    genres = dict(
        connection.execute(
            "SELECT content_type, count(*) FROM documents GROUP BY 1"
        ).fetchall()
    )
    connection.close()

    periods = [
        ("1988–1993", "1988-01", "1993-12"),
        ("1994–2002", "1994-01", "2002-12"),
        ("2003–2013", "2003-01", "2013-12"),
        ("2014–2026*", "2014-01", "2026-09"),
    ]
    period_table = []
    for label, first, last in periods:
        selected = [r for r in output_rows if first <= r["year_month"] <= last]
        period_table.append(
            (
                label,
                len(selected),
                sum(r["uk_records_with_text"] > 0 for r in selected),
                sum(r["us_usable_agency_genre_hits"] > 0 for r in selected),
                sum(r["eu_works_with_extracted_text"] > 0 for r in selected),
                sum(r["pooled_government_text_present"] for r in selected),
                uk_period[label.rstrip("*")],
                sum(r["eu_enumerated_works"] for r in selected),
            )
        )

    def window(year: int, month: int) -> tuple[int, list[str]]:
        selected = {
            shifted(year, month, offset)
            for offset in range(-24, 25)
        }
        missing = [
            r["year_month"]
            for r in output_rows
            if r["year_month"] in selected
            and not r["pooled_government_text_present"]
        ]
        return 49 - len(missing), missing

    kyoto, kyoto_missing = window(1997, 12)
    paris, paris_missing = window(2015, 12)
    uk_no_text = [month for month in months if not uk_text[month]]
    missing = [r["year_month"] for r in output_rows if not r["pooled_government_text_present"]]
    us_metrics = json.loads(US_METRICS.read_text())
    stamps = {
        label: datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
        for label, path in [
            ("UK monthly", UK_CSV),
            ("US monthly", US_CSV),
            ("EU monthly", EU_CSV),
            ("EU text disposition", EU_LEDGER),
            ("EU supervisor log", EU_LOG),
        ]
    }
    report = [
        "# International government corpus: temporal coverage and data shape",
        "",
        "Snapshot assembled 27 September 2026 from existing read-only ledgers. Data sources have different update times and ongoing US/EU collection; this is a lower-bound view of saved text presence, not a final corpus freeze.",
        "",
        "## Coverage",
        "",
        f"- Study months: **{len(months)}** (1988-01 through 2026-09, final month partial). UK extracted text in **{sum(bool(uk_text[m]) for m in months)}**; EU extracted text in **{sum(bool(eu_extracted_work[m]) for m in months)}**; US usable text in **{sum(bool(us_usable_stratum_hits[m]) for m in months)}** months in the source snapshots.",
        f"- Pooled government text presence: **{sum(r['pooled_government_text_present'] for r in output_rows)}/{len(months)}**. Months still lacking saved text in this snapshot: **{', '.join(missing)}**. The UK alone has **{len(uk_no_text)}** text-absent months.",
        f"- EU source Work enumeration is positive in **{sum(int(eu_months[m]['enumerated_works']) > 0 for m in months)}/{len(months)}** months. Enumeration is broader than downloaded and extracted text.",
        "- This is government-role evidence only. Media/public corpora and validated warming/fear relevance are not yet represented in these acquisition ledgers. Time presence does not establish a real event response.",
        "",
        "![Monthly government text presence](government_temporal_presence.png)",
        "",
        "## Period distribution",
        "",
        "| Period | Months | UK text months | US text months | EU text months | Pooled text months | UK independent records | EU enumerated Works |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for entry in period_table:
        label, total, uk, us, eu, pooled, uk_records, eu_works = entry
        report.append(
            f"| {label} | {total} | {uk} | {us} | {eu} | {pooled} | {uk_records:,} | {eu_works:,} |"
        )
    report.extend(
        [
            "",
            "*2026 ends on 21 September. UK records and EU Works are different source units. US monthly counts are agency/genre stratum hits, so their sum can double-count a few cross-agency parents; month presence is unaffected. Do not add unlike record counts as an experiment sample size.*",
            "",
            "## Event-window availability (government text only)",
            "",
            f"- Kyoto adoption, December 1997: **{kyoto}/49** months from December 1995 through December 1999; absent: {', '.join(kyoto_missing) if kyoto_missing else 'none'}. This is monthly text presence, not demonstrated climate-event response.",
            f"- Paris adoption, December 2015: **{paris}/49** months from December 2013 through December 2017; absent: {', '.join(paris_missing) if paris_missing else 'none'}. The live US/EU queues may change this snapshot.",
            "- An event in 1988 cannot have 24 observed pre-event months within a study starting in January 1988.",
            "",
            "## Current data shape",
            "",
            f"- UK 06 database: **{shape['documents']:,}** document parents; **{shape['content_objects']:,}** content objects; **{shape['document_content_objects']:,}** parent/object links; **{shape['content_versions']:,}** saved versions; **{shape['text_segments']:,}** extracted text segments. These are different storage levels, not additive documents.",
            f"- UK genres: written answers **{genres['ministerial_written_answer']:,}** ({100*genres['ministerial_written_answer']/shape['documents']:.2f}%); written statements **{genres['ministerial_written_statement']:,}**; policy records **{genres['policy_paper']+genres['guidance']:,}**. The pooled government series would otherwise be dominated by answers.",
            f"- US selected parent denominator: **{us_metrics['US_enumerated_unique']:,}** unique EPA/DOE rulemaking records from 1994 onward; the 08:34 UTC audited report had **{us_metrics['US_downloaded_verified']:,}** downloaded bodies. A later committed checkpoint reported 17,305, but it is not used to recalculate the older monthly CSV.",
            f"- EU selected source denominator: **{sum(int(r['enumerated_works']) for r in eu_months.values()):,}** unique Commission preparatory Works; **{sum(eu_extracted_work.values()):,}** distinct Works had extracted text in the dated disposition ledger plus completed-month supervisor log. The active {current_eu_month} month is excluded until completion.",
            f"- Australia: **{us_metrics['AU_catalogue_unique']:,}** catalogue landing candidates; **{us_metrics['versions_by_series']['au_dcceew_current_catalogue_2026_snapshot']}** saved content versions in the dated 09 report. Candidate landings and alternate versions are not verified independent monthly policy Works; exclude them from pooled text-presence counting here.",
            "- Database `body_status` on older GOV.UK parents remains a historical ingestion-state field; the source content-version/segment and reviewed monthly ledgers supply the text-presence counts here. Do not interpret `blocked_pending_ethics_route` on those parent rows as proof that the later authorised content acquisition did not occur.",
            "",
            "## Ledger timestamps",
            "",
        ]
    )
    report.extend(f"- {label}: {stamp}" for label, stamp in stamps.items())
    report.append("\nThe monthly CSV carries exact-month source presence and the evidence boundary for every study month. No full database re-import or fresh download was performed for this snapshot.\n")
    (OUT / "README.md").write_text("\n".join(report), encoding="utf-8")
    print(f"pooled={sum(r['pooled_government_text_present'] for r in output_rows)}/{len(months)} missing={missing}")
    print(f"uk_documents={shape['documents']} eu_works={sum(int(r['enumerated_works']) for r in eu_months.values())} us_enumerated={us_metrics['US_enumerated_unique']}")


if __name__ == "__main__":
    main()
