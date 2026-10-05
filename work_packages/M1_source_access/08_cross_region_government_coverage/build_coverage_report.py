"""Audit bounded cross-region government-source enumeration without database writes.

The output is a source-coverage ledger, not a new corpus. Counts with different
record boundaries are deliberately kept in separate units.
"""

import calendar
import collections
import csv
import html
import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import mistune


HERE = Path(__file__).resolve().parent
OUT = HERE / "reports"
OUT.mkdir(exist_ok=True)
CUTOFF = date(2026, 9, 21)


def read_csv(name):
    with (HERE / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name, fields, rows):
    with (OUT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def months():
    for year in range(1988, 2027):
        for month in range(1, 13):
            if (year, month) > (2026, 9):
                return
            yield year, month, f"{year:04d}-{month:02d}"


def source_register():
    rows = [
        ("uk_06_frozen", "UK", "Existing 06 database", "DEFRA policy_paper query plus separately scoped House of Commons written answers/statements", "See 07 work package source filters; not re-enumerated here", "policy publication / ministerial answer / ministerial statement", "document_id, official identifier, source URL", "publication / answer / statement date", "document; attachments separately linked", "document stable ID; shared attachments linked, not counted as new documents", "existing frozen comparator", "Existing 06 evidence; no new response", "N/A"),
        ("us_fr_rules", "US", "Federal Register API", "conditions[agencies][]=environmental-protection-agency OR energy-department; conditions[type][]=RULE OR PRORULE; publication_date 1994-01-01..2026-09-21", "Agency hierarchy IDs EPA=145, Energy Department=136; no climate keyword filter", "final rule / proposed rule", "document_number plus publication_date; canonical html_url", "publication_date, day", "Federal Register document", "Deduplicate cross-agency hits by canonical URL; document_number alone collides twice", "132/132 year×agency×genre partitions enumerated; 33,544 unique canonical URLs", "https://www.federalregister.gov/api/v1/documents.json", "Official public API; full-text reuse terms to review separately"),
        ("au_dcceew_catalogue", "Australia", "DCCEEW publication listing", "Current Department of Climate Change, Energy, the Environment and Water; all /about/publications pages 0..82", "Website's current department listing; no climate topic restriction; historical predecessor coverage not assured", "mixed publications, reports and landing pages", "landing_url", "catalogue_created_at is CMS timestamp, not verified original publication date", "boundary_unknown: listing row or landing page may point to attachments", "Collapse duplicate landing URLs; inspect each landing page and attachments before document count", "83/83 listing pages fetched; 821 unique landing URLs, 2 after cutoff", "https://www.dcceew.gov.au/about/publications", "Public listing; rights per linked publication need review"),
        ("au_parliament_questions", "Australia", "Australian Parliament questions in writing", "House Notice Paper / Parlinfo entry", "No department filter or year partition established", "written question and answer", "not established", "not established", "boundary_unknown", "Question is not government answer; no count or dedup claim", "current entry HTTP 403; not enumerated", "https://www.aph.gov.au/housenp", "Access restriction respected"),
        ("ie_oireachtas_questions", "Ireland", "Oireachtas API /questions", "qtype=written; date_start/date_end monthly 2012-07..2026-09-21", "No department or chamber filter in queried Swagger parameters; sample `question.to.showAs` is metadata, not a query filter", "written parliamentary question, not automatically ministerial answer", "question.uri; debateSection URI and answerText linked when present", "question context date, day; answer date requires separate check", "question/answer pair; one indexed question may have distinct answer text", "Deduplicate by question.uri; preserve question vs government answer; departmental and chamber subsets not enumerated", "171/171 month index partitions; 684,809 all-department question index count, not fetched records", "https://api.oireachtas.ie/v1/questions", "Official open API; reuse terms and answer attribution to check"),
        ("ie_government_publications", "Ireland", "gov.ie departmental publications", "Department of Climate, Energy and the Environment publication entrance", "No frozen machine-readable all-publication pagination/filter yet", "policy and publication mix", "not established", "published vs updated date displayed separately", "boundary_unknown: page versus attached policy", "Cross-link by official publication identity before counting", "entrance verified; not enumerated", "https://www.gov.ie/en/organisation/department-of-the-environment-climate-and-communications/", "Public site; linked-file rights to check"),
        ("eu_cellar", "EU institutions", "EU Publications Office CELLAR", "SPARQL Work/Expression/Manifestation hierarchy; institution and document-type filters not frozen", "Commission versus Parliament versus Council issuer must be explicit", "legal/policy publication mix", "CELLAR Work URI and identifiers", "work document date; later manifestation dates separate", "Work is candidate document; language Expression is not new Work", "Deduplicate by Work; attach EN expressions and manifestations", "official route verified; no denominator enumerated", "https://publications.europa.eu/webapi/rdf/sparql", "Open metadata; per-file reuse to check"),
        ("eu_ep_questions", "EU institutions", "European Parliament Open Data API", "/api/v2/parliamentary-questions probe only", "Parliament is question issuer; Commission/Council responder must be checked per answer", "MEP question with linked answer", "ELI Work URI and question identifier", "question date versus answer date separate", "question Work; answer and language distributions are linked objects", "Do not count question, answer and EN manifestation as separate government documents", "one original Work response checked; no year partitions enumerated", "https://data.europarl.europa.eu/api/v2/parliamentary-questions", "Open data; licensing on dataset page to check"),
        ("nz_mfe_publications", "New Zealand", "Ministry for the Environment publications", "current publications entrance", "No full catalogue filter/year partitions established", "mixed official publications", "not established", "not established", "boundary_unknown", "No source or document total claimed", "HTTP 200 anti-bot challenge; not enumerated", "https://environment.govt.nz/publications/", "Challenge not bypassed"),
        ("nz_parliament_questions", "New Zealand", "NZ Parliament written questions", "official questions/answers entrance and historical Hansard Supplement route", "Department/person filters not frozen", "written question and ministerial reply", "not established", "question and answer dates separate", "boundary_unknown", "Do not merge question with government answer; pre-2003 supplement is separate route", "entrance verified; not enumerated", "https://www3.parliament.nz/en/get-involved/features/hundreds-of-written-questions-asked-every-week-even-when-parliament-isn-t-meeting/", "Official public website"),
    ]
    fields = ["source_id", "region", "official_source", "exact_scope_and_filter_fields", "institution_filter_caveat", "genre", "official_stable_id_or_candidate", "date_basis_and_precision", "record_boundary", "overlap_and_dedup_rule", "enumeration_result", "canonical_entry", "access_and_rights"]
    tiers = {
        "uk_06_frozen": ("publisher original / official archive / verified mirror mixed", "See frozen 07 coverage audit", "day where validated", "varies by type; original files retained"),
        "us_fr_rules": ("issuing official publication service", "132/132 selected API partitions; 1994 onward only", "day", "high for rule document URL; document_number alone insufficient"),
        "au_dcceew_catalogue": ("publisher catalogue only", "83/83 current pages; historical predecessor completeness unknown", "CMS timestamp only; original date unknown", "low for document/file; landing URL only"),
        "au_parliament_questions": ("official entrance; blocked", "unknown", "unknown", "unknown"),
        "ie_oireachtas_questions": ("official index only", "171/171 all-department month indexes; target department/answer completeness unknown", "question day; answer date unknown", "high for question URI, unknown for response"),
        "ie_government_publications": ("publisher catalogue entrance only", "unknown", "original and updated dates distinct; not enumerated", "unknown"),
        "eu_cellar": ("official archive metadata entrance", "unknown; no institution/genre denominator", "Work date candidate; manifestation dates distinct", "Work hierarchy defined; selected series untested"),
        "eu_ep_questions": ("official Parliament API sample", "unknown; one Work checked", "question year from ID; exact date unverified in sample", "question Work high, answer boundary unverified"),
        "nz_mfe_publications": ("publisher entrance; challenge response", "unknown", "unknown", "unknown"),
        "nz_parliament_questions": ("official Parliament entrance only", "unknown", "question and answer dates must be separated", "unknown"),
    }
    extended = fields + ["provenance_tier", "coverage_completeness", "date_precision", "record_boundary_confidence"]
    write_csv("source_register.csv", extended,
              (dict(zip(extended, row + tiers[row[0]])) for row in rows))


def main():
    us_parts = read_csv("us_fr_partitions.csv")
    us_rows = read_csv("us_fr_records.csv")
    au_pages = read_csv("au_dcceew_catalogue_pages.csv")
    au_rows = read_csv("au_dcceew_catalogue_rows.csv")
    ie_months = read_csv("ie_written_question_month_index.csv")
    assert len(us_parts) == 132 and len(au_pages) == 83 and len(ie_months) == 171
    assert all(int(r["official_count"]) == int(r["records_enumerated"]) for r in us_parts)
    assert sum(int(r["official_count"]) for r in us_parts) == len(us_rows)
    assert all(r["http_status"] == "200" for r in au_pages + ie_months)
    assert sum(int(r["listing_rows"]) for r in au_pages) == len(au_rows)
    assert all(int(r["official_index_count"]) < 10000 for r in ie_months)
    assert len({r["year_month"] for r in ie_months}) == 171
    assert all(r["publication_date"] <= CUTOFF.isoformat() for r in us_rows)

    us_by_partition = collections.defaultdict(list)
    for row in us_rows:
        us_by_partition[(row["agency_stratum"], row["genre"], row["publication_date"][:4])].append(row)
    part_audit = []
    for part in us_parts:
        key = (part["agency"], part["genre"], part["year"])
        subset = us_by_partition[key]
        urls = [r["canonical_url"] for r in subset]
        ids = [r["document_number"] for r in subset]
        assert len(subset) == int(part["official_count"])
        assert len(urls) == len(set(urls))
        assert int(part["pages_expected"]) == int(part["pages_obtained"])
        part_audit.append({"agency": key[0], "genre": key[1], "year": key[2],
                           "official_count": len(subset), "unique_canonical_urls": len(set(urls)),
                           "unique_document_numbers": len(set(ids)),
                           "status": "verified_by_canonical_url",
                           "note": "document_number collision; use URL and date" if len(set(ids)) < len(ids) else ""})
    write_csv("us_fr_partition_identity_audit.csv", list(part_audit[0]), part_audit)

    by_url = collections.defaultdict(list)
    by_number = collections.defaultdict(list)
    for row in us_rows:
        by_url[row["canonical_url"]].append(row)
        by_number[row["document_number"]].append(row)
    unique_us = []
    for url, variants in sorted(by_url.items()):
        first = variants[0]
        unique_us.append({"canonical_url": url, "document_number": first["document_number"],
                          "publication_date": first["publication_date"], "title": first["title"],
                          "genre": first["genre"], "agency_strata": ";".join(sorted({r["agency_stratum"] for r in variants})),
                          "agency_names_from_api": first["agency_names"], "pdf_url": first["pdf_url"],
                          "stratum_hit_count": len(variants)})
    write_csv("us_fr_unique_documents.csv", list(unique_us[0]), unique_us)
    dup = []
    for number, variants in sorted(by_number.items()):
        urls = {r["canonical_url"] for r in variants}
        if len(urls) > 1:
            dup.append({"issue": "same_document_number_distinct_canonical_url", "identifier": number,
                        "hit_count": len(variants), "unique_url_count": len(urls),
                        "dates": ";".join(sorted({r["publication_date"] for r in variants})),
                        "canonical_urls": ";".join(sorted(urls))})
    for url, variants in sorted(by_url.items()):
        if len(variants) > 1:
            dup.append({"issue": "same_document_cross_agency_strata", "identifier": variants[0]["document_number"],
                        "hit_count": len(variants), "unique_url_count": 1,
                        "dates": variants[0]["publication_date"], "canonical_urls": url})
    au_by_url = collections.Counter(r["landing_url"] for r in au_rows)
    for url, count in sorted(au_by_url.items()):
        if count > 1:
            dup.append({"issue": "same_au_listing_url_multiple_cards", "identifier": url,
                        "hit_count": count, "unique_url_count": 1, "dates": "CMS date only", "canonical_urls": url})
    write_csv("overlap_and_identity_issues.csv", ["issue", "identifier", "hit_count", "unique_url_count", "dates", "canonical_urls"], dup)

    # Identity classes are evidence counts, not deletion commands. A shared
    # event/topic or title never establishes a mirror of a source publication.
    number_collisions = [x for x in dup if x["issue"] == "same_document_number_distinct_canonical_url"]
    exact_groups = [x for x in dup if x["issue"] in ("same_document_cross_agency_strata", "same_au_listing_url_multiple_cards")]
    identity_status = [
        {"status": "exact_duplicate", "verified_group_count": len(exact_groups),
         "unit": "identical canonical URL repeated in selected metadata rows", "example": "US FR 95-14725 in EPA and DOE strata; AU DCCEEW state-and-territory-greenhouse-gas-inventories-2018 card repeated", "action": "Collapse stratum/listing hit for union count; preserve agency/listing relationships"},
        {"status": "verified_mirror", "verified_group_count": 0,
         "unit": "same original file independently hosted with official ID/version or checked content hash and provenance", "example": "None verified; only response-body hashes, not publication-file hashes, were collected", "action": "Do not merge across hosts"},
        {"status": "near_duplicate_candidate", "verified_group_count": len(number_collisions),
         "unit": "document-number collision with distinct date and URL; relationship unresolved", "example": "FR 95-24211 original/republication; C1-2014-16556 two dated URLs", "action": "Preserve both dated records; candidate relationship only, no automatic deletion"},
        {"status": "same_event_distinct_voice", "verified_group_count": 0,
         "unit": "cross-jurisdiction original publications linked to one independently identified event", "example": "No verified cross-jurisdiction event pair in this metadata tranche; Paris Agreement national statements would remain separate voices", "action": "Never merge on month, title similarity, shared event or topic"},
    ]
    write_csv("identity_relationship_status.csv", list(identity_status[0]), identity_status)

    identity_examples = [
        {"classification": "exact_duplicate", "jurisdiction": "US", "institution": "EPA; DOE", "genre": "final rule", "official_id": "95-14725", "edition": "unknown", "original_issue_date": "1995-06-26", "portal_upload_date": "unknown", "language": "English presumed; original not downloaded", "canonical_url": "https://www.federalregister.gov/documents/1995/06/26/95-14725/nonprocurement-debarment-and-suspension", "content_hash": "not acquired", "parent_original_relationship": "one FR document, two agency-filter hits", "provenance_tier": "official publication API", "coverage_completeness": "selected FR partition verified", "date_precision": "day", "record_boundary_confidence": "high by canonical URL", "rights_access": "public metadata; full-text rights not audited"},
        {"classification": "near_duplicate_candidate", "jurisdiction": "US", "institution": "EPA", "genre": "final rule", "official_id": "95-24211", "edition": "republication candidate", "original_issue_date": "1995-11-13", "portal_upload_date": "unknown", "language": "English presumed; original not downloaded", "canonical_url": "https://www.federalregister.gov/documents/1995/11/13/95-24211/technical-amendments-to-test-rules-and-consent-orders-republication", "content_hash": "not acquired", "parent_original_relationship": "possible relation to 1995-09-29 same-number item; not merged", "provenance_tier": "official publication API", "coverage_completeness": "selected FR partition verified", "date_precision": "day", "record_boundary_confidence": "high by dated canonical URL", "rights_access": "public metadata; full-text rights not audited"},
        {"classification": "exact_duplicate", "jurisdiction": "Australia", "institution": "DCCEEW", "genre": "publication catalogue card", "official_id": "not supplied", "edition": "unknown", "original_issue_date": "unknown", "portal_upload_date": "CMS created timestamp in listing", "language": "English listing", "canonical_url": "https://www.dcceew.gov.au/climate-change/publications/state-and-territory-greenhouse-gas-inventories-2018", "content_hash": "not acquired", "parent_original_relationship": "same landing URL listed twice; child files unknown", "provenance_tier": "publisher catalogue", "coverage_completeness": "83/83 current listing pages; historical unknown", "date_precision": "CMS timestamp only", "record_boundary_confidence": "boundary_unknown for document", "rights_access": "public listing; files not audited"},
        {"classification": "not_classified_as_government_response", "jurisdiction": "Ireland", "institution": "Oireachtas; addressed to Children minister", "genre": "MP written question with answer field", "official_id": "https://data.oireachtas.ie/ie/oireachtas/question/2023-03-30/pq_10", "edition": "unknown", "original_issue_date": "2023-03-30 question date", "portal_upload_date": "unknown", "language": "English sample", "canonical_url": "https://data.oireachtas.ie/ie/oireachtas/question/2023-03-30/pq_10", "content_hash": "not acquired for original XML", "parent_original_relationship": "question/answer and debateSection linked; answer issuer/date unverified", "provenance_tier": "official API", "coverage_completeness": "index only; all departments", "date_precision": "question day", "record_boundary_confidence": "high for question, unknown for government response", "rights_access": "public API"},
    ]
    write_csv("record_identity_examples.csv", list(identity_examples[0]), identity_examples)

    source_register()
    ie_by_month = {r["year_month"]: r for r in ie_months}
    us_by_month_genre = collections.Counter((r["publication_date"][:7], r["genre"]) for r in unique_us)
    au_by_cms_month = collections.Counter(r["catalogue_created_at"][:7] for r in au_rows if r["within_cutoff"] == "True")
    series = [
        ("uk_06_frozen", "UK 06: frozen comparator"),
        ("us_fr_final", "US FR: EPA/DOE final rules"),
        ("us_fr_proposed", "US FR: EPA/DOE proposed rules"),
        ("au_dcceew_catalogue", "AU DCCEEW: listing"),
        ("au_parliament_questions", "AU Parliament: questions"),
        ("ie_oireachtas_questions", "IE Oireachtas: written questions"),
        ("ie_government_publications", "IE gov.ie: publications"),
        ("eu_cellar", "EU CELLAR: publications"),
        ("eu_ep_questions", "EU EP: Q&A"),
        ("nz_mfe_publications", "NZ MfE: publications"),
        ("nz_parliament_questions", "NZ Parliament: Q&A"),
    ]
    coverage = []
    for year, month, ym in months():
        for sid, label in series:
            status, count, unit, note = "not_enumerated", "", "", "No frozen, verified month denominator"
            if sid == "uk_06_frozen":
                status, note = "frozen_comparator", "See UK 07 coverage ledger; not reaudited here"
            elif sid in ("us_fr_final", "us_fr_proposed"):
                if year < 1994:
                    status, note = "api_period_unavailable", "FederalRegister.gov API starts in 1994; not US-government zero"
                else:
                    genre = "final_rule" if sid.endswith("final") else "proposed_rule"
                    status, count, unit = "verified_enumerated", us_by_month_genre[(ym, genre)], "unique canonical FR document URL"
                    note = "EPA/DOE agency hierarchy only; final/proposed rule only"
                    if count == 0:
                        status = "verified_zero_within_scope"
            elif sid == "au_dcceew_catalogue":
                status, count, unit = ("catalogue_snapshot_boundary_unknown" if ym == "2026-09" else "not_enumerated"), au_by_cms_month[ym], "listing URL by CMS-created month"
                note = "83-page current snapshot observed Sep 2026; CMS-created month is not historical publication coverage; attachment boundary unknown"
            elif sid == "au_parliament_questions":
                status = "access_blocked" if ym == "2026-09" else "not_enumerated"
                note = "Current official entry returned HTTP 403 in Sep 2026; historical month status unknown"
            elif sid == "ie_oireachtas_questions":
                if ym < "2012-07":
                    status, note = "api_period_unavailable", "Official API question metadata begins in July 2012; earlier Dáil archives separate"
                else:
                    row = ie_by_month[ym]
                    count, unit = int(row["official_index_count"]), "all-department written question index count"
                    status = "verified_zero_within_scope" if count == 0 else "index_only_unfiltered"
                    note = "No department query filter; answer presence and minister issuer not enumerated"
            elif sid == "nz_mfe_publications":
                status = "access_blocked" if ym == "2026-09" else "not_enumerated"
                note = "Current publications entry returned HTTP 200 challenge in Sep 2026; historical month status unknown"
            coverage.append({"source_series": sid, "display_label": label, "year_month": ym,
                             "period_end": min(date(year, month, calendar.monthrange(year, month)[1]), CUTOFF).isoformat(),
                             "coverage_status": status, "observed_count": count, "count_unit": unit,
                             "scope_note": note})
    write_csv("monthly_source_coverage_status.csv", list(coverage[0]), coverage)

    checks = [
        {"source": "us_fr_rules", "kind": "ordinary_document", "official_id": "2014-30630", "canonical_url": "https://www.federalregister.gov/documents/2014/12/31/2014-30630/oil-and-natural-gas-sector-reconsideration-of-additional-provisions-of-new-source-performance",
         "evidence": "us_fr_records.csv; original JSON partition", "boundary_risk": "Federal Register document is a rule, not a UK-style policy paper"},
        {"source": "us_fr_rules", "kind": "document_number_collision", "official_id": "95-24211", "canonical_url": "https://www.federalregister.gov/documents/1995/11/13/95-24211/technical-amendments-to-test-rules-and-consent-orders-republication",
         "evidence": "1995 EPA final-rule API partition", "boundary_risk": "Same number also appears on 1995-09-29; number alone would falsely merge two dated publications"},
        {"source": "us_fr_rules", "kind": "cross_agency_hit", "official_id": "95-14725", "canonical_url": "https://www.federalregister.gov/documents/1995/06/26/95-14725/nonprocurement-debarment-and-suspension",
         "evidence": "EPA and DOE 1995 final-rule partitions", "boundary_risk": "One URL hit in two agency strata; count once in union"},
        {"source": "au_dcceew_catalogue", "kind": "listing_duplicate", "official_id": "landing URL only", "canonical_url": "https://www.dcceew.gov.au/climate-change/publications/state-and-territory-greenhouse-gas-inventories-2018",
         "evidence": "83-page listing, two rows", "boundary_risk": "Landing page may have multiple files; no original publication date from index"},
        {"source": "ie_oireachtas_questions", "kind": "question_answer_structure", "official_id": "https://data.oireachtas.ie/ie/oireachtas/question/2023-03-30/pq_10", "canonical_url": "https://data.oireachtas.ie/ie/oireachtas/question/2023-03-30/pq_10",
         "evidence": "raw_probe/ie_written_2023_03.json", "boundary_risk": "Question by MP; `to.showAs=Children`; answerText separate; not selected environmental department"},
        {"source": "eu_ep_questions", "kind": "work_sample_only", "official_id": "E-10-2024-001357", "canonical_url": "https://data.europarl.europa.eu/eli/dl/doc/E-10-2024-001357",
         "evidence": "raw_probe/ep_questions_api.json (RDF/XML)", "boundary_risk": "MEP question Work is not itself a Commission/Council answer; no enumeration total"},
    ]
    write_csv("source_to_record_spot_checks.csv", list(checks[0]), checks)

    # A year-scale visual stays legible; the CSV above retains every month and its exact state.
    palette = [
        ("verified_enumerated", "#2A6F70", "Verified in bounded series"),
        ("verified_zero_within_scope", "#75A9A2", "Verified zero within scope"),
        ("index_only_unfiltered", "#C69A3B", "Index count; institution filter unresolved"),
        ("catalogue_snapshot_boundary_unknown", "#5C82A7", "Catalogue snapshot; original-date boundary unknown"),
        ("not_enumerated", "#D9D9D7", "Not enumerated"),
        ("access_blocked", "#A65B55", "Current entrance blocked"),
        ("api_period_unavailable", "#EFEEE9", "Chosen API period unavailable"),
        ("frozen_comparator", "#625F69", "Frozen UK comparator; see separate audit"),
    ]
    code = {state: i for i, (state, _, _) in enumerate(palette)}
    colors = [color for _, color, _ in palette]
    by_series_year = collections.defaultdict(list)
    for row in coverage:
        by_series_year[(row["source_series"], int(row["year_month"][:4]))].append(row["coverage_status"])
    grid = []
    for sid, _ in series:
        arr = []
        for year in range(1988, 2027):
            states = by_series_year[(sid, year)]
            if sid == "ie_oireachtas_questions" and year == 2012:
                state = "index_only_unfiltered"
            elif len(set(states)) == 1:
                state = states[0]
            elif "index_only_unfiltered" in states:
                state = "index_only_unfiltered"
            elif "catalogue_snapshot_boundary_unknown" in states:
                state = "catalogue_snapshot_boundary_unknown"
            elif "access_blocked" in states:
                state = "access_blocked"
            elif "verified_enumerated" in states:
                state = "verified_enumerated"
            else:
                state = states[0]
            arr.append(code[state])
        grid.append(arr)
    fig, ax = plt.subplots(figsize=(15, 5.6))
    ax.imshow(grid, cmap=ListedColormap(colors), vmin=-0.5, vmax=len(colors)-0.5, aspect="auto", interpolation="nearest")
    ax.set_yticks(range(len(series)), [label for _, label in series], fontsize=8.5)
    ax.set_xticks([y-1988 for y in range(1988, 2027, 2)], [str(y) for y in range(1988, 2027, 2)], fontsize=8)
    ax.tick_params(axis="both", length=0)
    ax.set_title("Cross-region government-source coverage evidence, 1988–21 Sep 2026", loc="left", fontsize=12, fontweight="bold", pad=14)
    ax.set_xlabel("Year — 2026 ends 21 September; exact monthly status in companion CSV", fontsize=9)
    ax.set_xticks([x-0.5 for x in range(1, 39)], minor=True)
    ax.set_yticks([x-0.5 for x in range(1, len(series))], minor=True)
    ax.grid(which="minor", color="white", linewidth=0.45)
    ax.tick_params(which="minor", bottom=False, left=False)
    fig.legend(handles=[Patch(facecolor=c, label=label) for _, c, label in palette], loc="lower center",
               bbox_to_anchor=(0.5, 0.015), ncol=2, fontsize=7.5, frameon=False)
    fig.subplots_adjust(left=0.22, right=0.99, top=0.87, bottom=0.29)
    fig.savefig(OUT / "cross_region_coverage_matrix.png", dpi=180)
    fig.savefig(OUT / "cross_region_coverage_matrix.svg")
    plt.close(fig)

    au_cutoff = [r for r in au_rows if r["within_cutoff"] == "True"]
    ie_total = sum(int(r["official_index_count"]) for r in ie_months)
    ie_zero = sum(int(r["official_index_count"]) == 0 for r in ie_months)
    fr_overlap = sum(len(v)-1 for v in by_url.values())
    report = f"""# Cross-region government-source coverage reconnaissance

Cutoff: **21 September 2026**. This is a metadata-enumeration tranche, not a merged international corpus and not a claim of historical completeness. The UK 06 database was read only and remains a frozen comparator: 248,035 documents (1,054 `policy_paper` + 1 `guidance`, 244,229 ministerial written answers, 2,751 written statements) and 3,668,275 text segments. Those genres are not interchangeable.

![Year-scale source evidence matrix](cross_region_coverage_matrix.png)

## Verified bounded enumerations

| Source and exact scope | Planned partitions | Reconciled evidence | Unit and limit |
|---|---:|---:|---|
| US Federal Register API: EPA/DOE agency hierarchy × final/proposed rules, 1994–cutoff | 132 year×agency×genre | 132/132; {len(us_rows):,} stratum hits, {len(unique_us):,} unique canonical document URLs | Rule/proposed-rule records, **not** all US policy or climate publications. {fr_overlap} cross-agency duplicate hits. Two document-number collisions require URL+date identity. |
| Australian DCCEEW current all-publications listing | 83 pages | 83/83; {len(au_rows):,} cards, {len(au_by_url):,} unique landing URLs; {len(au_cutoff):,} cards have CMS-created date by cutoff | Landing pages, **not** unique full-text policy files. Earliest CMS timestamp {min(r['catalogue_created_at'][:10] for r in au_rows)}; original dates and attachment boundaries unknown. |
| Irish Oireachtas `/questions`: `qtype=written`, all departments, Jul 2012–cutoff | 171 months | 171/171 successful monthly index queries; {ie_total:,} indexed questions; {ie_zero} months with verified index zero | Question-index counts only. Annual API counts cap at 10,000, so monthly sub-10,000 counts were used. No API department filter; no full record/answer enumeration. |

All response bodies and per-request URL, final URL, status, timestamp, MIME type and SHA-256 are in `evidence/`; filters and counts are in the CSVs. The US selected series begins in the API in 1994; 1988–1993 are **not supported by that route**, not years with no US government material. The Australian 83-page snapshot was observed on 23 September 2026 and includes two cards after the research cutoff; its CMS timestamps must not be presented as original publication dates. Irish zero months are zeros for the **all-department written-question index**, not for government answers or the target environmental departments.

## Sources not yet denominator-ready

EU: [CELLAR](https://op.europa.eu/en/web/cellar/cellar-data/metadata/knowledge-graph) provides an official Work–Expression–Manifestation route, but institutional and genre filters have not been frozen or enumerated. The [European Parliament API](https://data.europarl.europa.eu/en/developer-corner/opendata-api) yielded one original question Work in RDF/XML; a question is not a Commission/Council answer, and the sample cannot be turned into a count. Ireland's [gov.ie department publications](https://www.gov.ie/en/organisation/department-of-the-environment-climate-and-communications/) entrance is verified but not enumerated. New Zealand's [MfE publications](https://environment.govt.nz/publications/) returned an HTTP-200 challenge page, not publication data; Parliament's written-question entrance is verified but not enumerated. The current Australian House questions entrance returned HTTP 403. No access control was bypassed and none of these were assigned a zero count.

## Record boundaries and comparability

The [source register](source_register.csv) records exact institution filter fields/values, genre, stable or candidate ID, date precision, record boundary, dedup scheme, provenance tier, coverage completeness, record-boundary confidence and rights/access separately—there is no opaque authenticity score. The [spot checks](source_to_record_spot_checks.csv) show an ordinary US rule, a Federal Register document-number collision (1995 `95-24211` has different dated canonical pages), a single rule hit in both EPA and DOE strata, a duplicated Australian landing URL, an Irish MP question with a separate answer field, and an EP question Work. US canonical URL is the union key; the `document_number` alone is unsafe. AU page/file boundaries remain `boundary_unknown`. For EU, EN-language manifestations must not inflate Work counts. Question, answer and attachment are separate roles, even when an API wraps them together.

The [identity status ledger](identity_relationship_status.csv) records **{len(exact_groups)} exact metadata-hit duplicate groups**, **0 verified mirrors**, **{len(number_collisions)} near-duplicate relationship candidates**, and **0 observed same-event/distinct-voice pairs** in this bounded metadata tranche. “Zero observed” for the latter two verified classes is not evidence of absence in governments' output. The [record-level identity examples](record_identity_examples.csv) preserve jurisdiction, institution, genre, ID, edition, original/portal dates, language, URL, content-hash availability and parent/original relationship. We collected no publication-file hashes; response-body SHA-256 values prove retrieval integrity, not document identity. A shared Paris Agreement event, same month, similar title or topic would **not** license collapsing country-specific policy voices. Unlinked cross-site resemblance remains a candidate, never an automatic deletion.

The source composition is **not yet balanced** for cross-region time-series comparison. US rulemaking is a narrower administrative genre, Australian cards are a current-department catalogue snapshot, Ireland's counts cover parliamentary questions with neither department nor chamber query restriction rather than government answers, and EU/NZ are not enumerated. Department succession, migration dates and historical completeness need series-specific checks before a common window is claimed. Germany/France and other non-English candidates remain language/comparability candidates, not members of this English-core denominator. Official discourse is evidence of an institution's position or wording, not a claim that its factual assertions are objectively true.

## Decision for the next tranche

Use the verified US rule series as a bounded **source-specific** coverage candidate from 1994 to the cutoff. Do not combine its counts with the UK policy or ministerial-answer series. For AU, resolve original publication date, landing-page/file relationship and predecessor-department coverage before counting policy documents by year. For Ireland, retrieve bounded question/answer metadata and verify responder department and answer date; pre-July-2012 written replies require a separate archival route. Freeze EU CELLAR institutional/genre filters and EP answer-issuer filters before enumeration; resolve NZ/Australian parliamentary official access via ordinary alternative routes. None of these pending work items justifies an all-region coverage percentage now.

Companion files: [monthly source status](monthly_source_coverage_status.csv), [US partition identity audit](us_fr_partition_identity_audit.csv), [deduplicated US records](us_fr_unique_documents.csv), [overlap/collision ledger](overlap_and_identity_issues.csv), and raw source CSVs in the parent directory. A count is supplied only with its source, filter, unit and denominator.
"""
    (OUT / "coverage_report.md").write_text(report, encoding="utf-8")
    body = mistune.html(report)
    style = "body{font:16px/1.55 system-ui,sans-serif;color:#202b33;max-width:1100px;margin:2rem auto;padding:0 1rem}h1,h2{color:#173e4a}table{border-collapse:collapse;width:100%;font-size:.88rem}th,td{border-bottom:1px solid #d7dfdf;padding:.55rem;vertical-align:top;text-align:left}th{background:#eef3f2}img{max-width:100%}code{background:#eef3f2;padding:.1rem .25rem}a{color:#245f72}"
    (OUT / "coverage_report.html").write_text(f"<!doctype html><html lang='en'><meta charset='utf-8'><title>Cross-region source coverage</title><style>{style}</style><body>{body}</body></html>", encoding="utf-8")
    print(json.dumps({"us_partitions": len(us_parts), "us_stratum_hits": len(us_rows), "us_unique_urls": len(unique_us),
                      "us_cross_stratum_hits": fr_overlap, "us_document_number_collisions": sum(x["issue"] == "same_document_number_distinct_canonical_url" for x in dup),
                      "au_pages": len(au_pages), "au_cards": len(au_rows), "au_unique_urls": len(au_by_url),
                      "ie_months": len(ie_months), "ie_question_index_total": ie_total, "monthly_status_rows": len(coverage)}, indent=2))


if __name__ == "__main__":
    main()
