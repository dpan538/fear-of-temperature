"""Contract tests use synthetic records in temporary stores, never the live acquisition."""

import json
import sqlite3
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import collect as core  # noqa: E402


def test_bom_release_header_not_event_table_or_render_date():
    parse = core.official_pages.bom_date
    assert (
        parse(
            BeautifulSoup(
                '<p class="dateline">Wednesday 29 January 2025 - Annual Climate Summary 2024</p>'
                '<td class="date">5 February 1988</td>',
                "html.parser",
            )
        )
        == "2025-01-29"
    )
    assert (
        parse(BeautifulSoup('<p class="date">Issued 4 January 2012</p>', "html.parser"))
        == "2012-01-04"
    )
    assert (
        parse(
            BeautifulSoup(
                '<h1>Annual climate 1998</h1><td class="date">1 January 1998</td>'
                "<footer>created 20 October 2026</footer>",
                "html.parser",
            )
        )
        is None
    )


def test_qld_public_search_visits_every_government_term(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "EXTENDED_TERMS", {"heatwave"})
    visited = []

    class Client:
        def get(self, url):
            params = core.urllib.parse.parse_qs(core.urllib.parse.urlparse(url).query)
            if "t" in params:
                assert params["FromDate"] == ["01/01/1988"]
                assert params["ToDate"] == ["21/09/2026"]
                visited.append(params["t"][0])
            return (
                '<select name="t">'
                + "".join(f'<option value="{i}">{i}</option>' for i in range(1, 14))
                + "</select>"
            ).encode()

    store = core.Store(tmp_path)
    core.official_pages.collect_qld_statements(store, Client())
    assert visited == [str(i) for i in range(1, 14)]


@pytest.mark.parametrize(
    "headline",
    [
        "Heatwave policy",
        "CLASSIFIED PUBLICATIONS - Weekly gazette report for week ending 03/09/93",
    ],
)
def test_trove_public_gazette_range_in_publisher_and_idempotent_pages(tmp_path, headline):
    terms = sorted(core.EXTENDED_TERMS)
    pages = [
        [i, 0, 1 if t == "heatwave" else 0, [123] if t == "heatwave" else [], None]
        for i, t in enumerate(terms)
    ]
    manifest = dict(
        version="fixture",
        interval=[core.START, core.END],
        terms=terms,
        completed_terms=terms,
        pages=pages,
    )
    (tmp_path / "trove_web_discovery.json").write_text(json.dumps(manifest))
    visits = []

    class Client:
        def get(self, url):
            visits.append(url)
            return (
                f'<meta property="og:title" content="{headline} - '
                'Government Gazette (Sydney : 1901 - 2001) - 27 Jun 1997">'
                '<div id="fulltextContents"><div class="line"><div class="read">'
                "Heatwave policy and heat stress</div></div></div>"
            ).encode()

    store = core.Store(tmp_path)
    core.official_pages.collect_trove_web(store, Client())
    core.official_pages.collect_trove_web(store, Client())
    row = store.db.execute("SELECT * FROM source_documents").fetchone()
    assert row["publication_date"] == "1997-06-27"
    assert row["author_speaker"] == "Government Gazette (Sydney : 1901 - 2001)"
    assert row["title"] == headline
    assert row["excerpt_text"] == "Heatwave policy and heat stress"
    assert len(visits) == 1
    assert store.cursor("trove_web:all_discovery_documents")["state"] == "exhausted"
    manifest["pages"][terms.index("heatwave")][2] = 2
    (tmp_path / "trove_web_discovery.json").write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError, match="total/page count mismatch"):
        core.official_pages.collect_trove_web(store, Client())


@pytest.mark.parametrize(
    ("value", "status", "month"),
    [
        ("1987-12-31", "outside_fixed_interval", "1987-12"),
        ("1988-01-01", "inside_fixed_interval", "1988-01"),
        ("2026-09-21", "inside_fixed_interval", "2026-09"),
        ("2026-09-22", "outside_fixed_interval", "2026-09"),
        ("2026-09", "pending_boundary_precision", "2026-09"),
        ("2026", "pending_boundary_precision", None),
        ("1998", "inside_fixed_interval", None),
        (None, "pending_publication_date", None),
        ("2001-02-30", "invalid_source_date", None),
    ],
)
def test_date_contract(value, status, month):
    result = core.publication(value)
    assert result["date_status"] == status
    assert result["publication_month"] == month
    if value in {"1998", "2026-09", "2026", None}:
        assert result["publication_date"] is None


def test_year_placeholder_is_not_january_activity():
    result = core.publication("2000-01-01", january_placeholder=True)
    assert result["date_granularity"] == "year"
    assert result["publication_month"] is None
    assert result["publication_date_raw"] == "2000-01-01"


def test_baseline_extended_and_incremental_are_not_double_counted():
    assert len(core.BASELINE_TERMS) == 26
    assert len(core.EXTENDED_TERMS) == 33
    assert core.BASELINE_TERMS < core.EXTENDED_TERMS
    assert core.matrix_membership(["heatwave"]) == {
        "baseline26": True,
        "extended33_union": True,
        "extended_only": False,
    }
    assert core.matrix_membership(["global warming"]) == {
        "baseline26": False,
        "extended33_union": True,
        "extended_only": True,
    }
    assert core.matrix_membership(["global warming", "heatwave"])["extended_only"] is False
    assert "greenhouse gas" in {r[1] for r in core.matches("greenhouse gases")}


def test_matrix_variants_and_verbatim_excerpt():
    text = "x " * 200 + "HEAT-RELATED HEALTH and hot nights; heatwaves" + " z" * 500
    hits = core.matches(text)
    assert {h[1] for h in hits} == {"heat-related health", "hot night", "heatwave"}
    excerpt, locator = core.snippet(text, hits)
    assert len(excerpt) <= 500
    _, lower, upper = locator.split(":", 2)
    assert excerpt == text[int(lower) : int(upper.split(";")[0])]


def test_retries_queries_and_versions_do_not_add_native_rows(tmp_path):
    store = core.Store(tmp_path)
    for term in ["heatwave", "extreme heat", "heatwave"]:
        store.save(
            "fixture",
            "native-1",
            "Heatwave",
            "heatwave and extreme heat " * 60,
            "2000-03-04",
            "https://example.org/1",
            tier="fixture",
            unit="publication_metadata",
            provider_terms=[term],
            extra={"original": "native-1"},
        )
    store.db.commit()
    assert store.db.execute("SELECT count(*) FROM source_documents").fetchone()[0] == 1
    row = store.db.execute("SELECT * FROM source_documents").fetchone()
    assert len(row["excerpt_text"]) <= 500
    assert set(json.loads(row["query_matched"])) == {"heatwave", "extreme heat"}
    assert json.loads(row["related_work_ids"]) == []
    assert json.loads(row["source_context_json"])["original"] == "native-1"
    assert (
        json.loads(row["source_context_json"])["query_matrix_run"]
        == core.COLLECTION_MATRIX["version"]
    )
    assert store.db.execute("SELECT count(*) FROM event_claims").fetchone()[0] == 0
    store.save(
        "fixture",
        "native-1",
        "Revised heatwave record",
        "hot nights",
        "2000-03-04",
        "https://example.org/1",
        tier="fixture",
        unit="publication_metadata",
        version="revision-2",
    )
    revised = store.db.execute("SELECT * FROM source_documents").fetchone()
    history = json.loads(revised["metadata_version_history"])
    assert len(history) == 1
    assert history[0]["title"] == "Heatwave"
    assert set(json.loads(revised["query_dimensions"])) == {"acute_thermal", "chronic_warming"}


def test_metadata_only_hit_is_pending_not_fabricated_excerpt(tmp_path):
    store = core.Store(tmp_path)
    store.save(
        "fixture",
        "1",
        None,
        None,
        None,
        "https://example.org/1",
        tier="fixture",
        unit="dataset_catalogue_metadata",
        provider_terms=["heat stress"],
    )
    row = store.db.execute("SELECT * FROM source_documents").fetchone()
    assert row["excerpt_text"] is None
    assert row["query_match_basis"] == "provider_search_hit_local_phrase_unconfirmed"
    assert row["date_status"] == "pending_publication_date"


def test_known_source_date_conflict_keeps_raw_date_pending(tmp_path):
    store = core.Store(tmp_path)
    store.save(
        "hansard_federal_rapid",
        "fixture",
        "Heatwave",
        "heatwave",
        "2010-03-09",
        "https://example.org/2010-02-23",
        tier="federal",
        unit="parliamentary_procedural_unit",
        parent="4891",
    )
    row = store.db.execute("SELECT * FROM source_documents").fetchone()
    assert row["date_status"] == "pending_source_date_conflict"
    assert row["publication_date_raw"] == "2010-03-09"
    assert row["publication_month"] is None


def test_all_ckan_pages_above_1000_are_traversed(tmp_path, monkeypatch):
    monkeypatch.setitem(core.COLLECTION_MATRIX, "dimensions", {"acute_thermal": ["heatwave"]})
    visited = []

    class Client:
        def get(self, url):
            params = core.urllib.parse.parse_qs(core.urllib.parse.urlparse(url).query)
            start = int(params["start"][0])
            visited.append(start)
            rows = [
                dict(
                    id=str(i),
                    name=str(i),
                    title="Heatwave inventory",
                    notes="heatwave",
                    extras=[dict(key="publication_date", value="2000-02-03")],
                )
                for i in range(start, min(start + 100, 1251))
            ]
            return json.dumps(dict(success=True, result=dict(count=1251, results=rows))).encode()

    store = core.Store(tmp_path)
    core.collect_qld(store, Client())
    assert visited == [*range(0, 1251, 100), 1251]
    assert store.db.execute("SELECT count(*) FROM source_documents").fetchone()[0] == 1251
    core.collect_qld(store, Client())
    assert len(visited) == 14  # Includes terminal empty page; saved state is reused.


def test_premature_empty_ckan_is_failure():
    with pytest.raises(RuntimeError, match="before advertised total"):
        core.ckan_page(dict(success=True, result=dict(count=1001, results=[])), 100)


def test_oai_resume_and_publication_vs_update_dates(tmp_path):
    visited = []

    def page(native, publication, token):
        return f"""<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
          xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:m="http://www.openarchives.org/OAI/2.0/oai_dc/">
          <ListRecords><record><header><identifier>{native}</identifier>
          <datestamp>2026-10-20T00:00:00Z</datestamp></header><metadata><m:dc>
          <dc:title>Heatwave</dc:title><dc:description>extreme heat</dc:description>
          <dc:date>{publication}</dc:date><dc:identifier>https://espace.library.uq.edu.au/view/{native}</dc:identifier>
          </m:dc></metadata></record><resumptionToken>{token}</resumptionToken></ListRecords></OAI-PMH>""".encode()

    class Client:
        def get(self, url):
            visited.append(url)
            if "resumptionToken" not in url:
                return page("UQ:1", "1998-02-03", "continue-2")
            return page("UQ:2", "2026-09-22", "")

    store = core.Store(tmp_path)
    core.collect_uq(store, Client())
    assert len(visited) == 2
    assert all("until=" not in url for url in visited)
    assert (
        store.db.execute(
            "SELECT publication_date FROM source_documents WHERE native_id='UQ:1'"
        ).fetchone()[0]
        == "1998-02-03"
    )
    assert (
        store.db.execute(
            "SELECT date_status FROM source_documents WHERE native_id='UQ:2'"
        ).fetchone()[0]
        == "outside_fixed_interval"
    )


def test_unreviewed_claim_cannot_default_to_verified(tmp_path):
    store = core.Store(tmp_path)
    store.save(
        "fixture",
        "1",
        "Heatwave",
        "heatwave",
        "2000-03-04",
        "https://example.org/1",
        tier="fixture",
        unit="publication_metadata",
    )
    doc = store.db.execute("SELECT doc_id FROM source_documents").fetchone()[0]
    store.db.execute(
        "INSERT INTO event_claims(event_id,doc_id,event_type,evidence_excerpt,evidence_locator) "
        "VALUES(?,?,?,?,?)",
        ("claim-1", doc, "reported_temperature", "source words", "p.2"),
    )
    assert store.db.execute("SELECT verification_status FROM event_claims").fetchone()[0] == "draft"
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("UPDATE event_claims SET verification_status='verified'")


def test_months_and_exhaustion_report_actual_zero(tmp_path):
    store = core.Store(tmp_path)
    report = core.audit(store)
    assert len(report["zero_observed_months"]) == 465
    assert report["unique_in_interval_metadata_rows"] == 0
    assert len(report["warnings"]) == 1
    assert report["all_sources_complete"] is False
    assert not any("threshold" in key for key in report)
    store.job("source_status:hansard_federal_rapid", "hansard_federal_rapid", "exhausted")
    report = core.audit(store)
    assert report["exhaustion_status"]["hansard_federal_rapid"] == "COMPLETED_LAST_PAGE"
    assert report["page_traversal_complete"]["hansard_federal_rapid"] is True
    assert report["all_sources_complete"] is False
    assert report["calendar_validated"] is False


def test_audit_counts_share_snapshot_while_other_worker_appends(tmp_path):
    store = core.Store(tmp_path)
    other = core.Store(tmp_path)
    store.save(
        "fixture",
        "1",
        "Heatwave",
        "heatwave",
        "2000-03-04",
        "https://example.org/1",
        tier="fixture",
        unit="publication_metadata",
    )
    store.db.commit()
    connection = store.db

    class Hook:
        fired = False

        def __getattr__(self, key):
            return getattr(connection, key)

        def execute(self, sql, *args):
            if sql.startswith("SELECT source_channel,query_matched") and not self.fired:
                self.fired = True
                other.save(
                    "fixture",
                    "2",
                    "Heatwave",
                    "heatwave",
                    "2000-03-04",
                    "https://example.org/2",
                    tier="fixture",
                    unit="publication_metadata",
                )
                other.db.commit()
            return connection.execute(sql, *args)

    store.db = Hook()
    result = core.audit(store)
    assert result["unique_in_interval_metadata_rows"] == 1
    assert result["matrix_comparison_in_interval_unique_ids"]["extended33_union"] == 1
    assert other.db.execute("SELECT count(*) FROM source_documents").fetchone()[0] == 2
