"""Read-only month × role snapshot from committed government-source databases.

This is acquisition coverage, not topical relevance or an RQ1/RQ2 result.
Run only between US single-writer batches so DuckDB can open the 09 database.
"""

import csv
from collections import defaultdict
from pathlib import Path

import duckdb


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE.parent
UK_DB = SOURCE_ROOT / "06_government_content_acquisition/fear_temperature_government_content.duckdb"
US_AU_DB = HERE / "fear_temperature_us_au_v1.duckdb"
EU_DB = SOURCE_ROOT / "10_eu_cellar_acquisition/eu_stage.duckdb"
OUT = HERE / "reports/pooled_month_role_coverage_2026-09-27.csv"


def months():
    for year in range(1988, 2027):
        for month in range(1, 13):
            if year == 2026 and month > 9:
                return
            yield f"{year:04d}-{month:02d}"


def keyed(rows):
    return {row[0]: tuple(row[1:]) for row in rows}


def main():
    uk = duckdb.connect(str(UK_DB), read_only=True)
    us_au = duckdb.connect(str(US_AU_DB), read_only=True)
    eu = duckdb.connect(str(EU_DB), read_only=True)
    try:
        uk_by_month = keyed(uk.execute("""
            SELECT strftime(publication_date, '%Y-%m'), count(*),
                   count(*) FILTER (WHERE body_status = 'downloaded_and_extracted')
            FROM documents
            WHERE publication_date BETWEEN '1988-01-01' AND '2026-09-21'
            GROUP BY 1
        """).fetchall())
        us_by_month = keyed(us_au.execute("""
            SELECT strftime(d.publication_date, '%Y-%m'), count(*),
                   count(*) FILTER (WHERE d.body_status = 'source_extracted_and_cleaned')
            FROM documents d JOIN sources s USING (source_id)
            WHERE s.source_name LIKE 'Federal Register EPA/DOE%'
              AND d.publication_date BETWEEN '1988-01-01' AND '2026-09-21'
            GROUP BY 1
        """).fetchall())
        # Catalogue CMS dates are excluded. Only original day/month evidence is
        # eligible for a calendar bin; year-only originals stay outside this view.
        au_by_month = defaultdict(lambda: [0, 0])
        au_outcomes = defaultdict(int)
        for date, precision, source_status, body_status in us_au.execute("""
            SELECT e.date_value, e.date_precision, e.source_status, d.body_status
            FROM documents d JOIN sources s USING (source_id)
            JOIN us_au_record_evidence e USING (document_id)
            WHERE s.source_name LIKE 'DCCEEW%'
              AND e.date_precision IN ('day', 'month')
        """).fetchall():
            au_outcomes[(precision, source_status, body_status)] += 1
            if not date or not ('1988-01' <= date[:7] <= '2026-09'):
                continue
            if source_status != 'original_verified':
                continue
            au_by_month[date[:7]][0] += 1
            if body_status == 'source_extracted_and_cleaned':
                au_by_month[date[:7]][1] += 1

        eu_by_month = keyed(eu.execute("""
            SELECT first_seen_month, count(*) FROM eu_works GROUP BY 1
        """).fetchall())
        placeholders = {work for (work,) in eu.execute("""
            SELECT DISTINCT v.work_uri
            FROM eu_source_blocks b JOIN eu_content_versions v USING (version_id)
            WHERE b.source_text LIKE '%>TABLE>%'
        """).fetchall()}
        eu_text = defaultdict(int)
        eu_ocr = defaultdict(int)
        eu_scan = defaultdict(int)
        for month, work, status, characters in eu.execute("""
            SELECT w.first_seen_month, v.work_uri, v.extraction_status,
                   v.text_characters
            FROM eu_content_versions v JOIN eu_works w USING (work_uri)
        """).fetchall():
            if status == 'text_extracted' and (characters or 0) > 0 and work not in placeholders:
                eu_text[month] += 1
            elif status == 'ocr_candidate_text_extracted':
                eu_ocr[month] += 1
            elif status == 'scanned_or_empty_text_layer':
                eu_scan[month] += 1

        fields = [
            'year_month', 'role', 'uk_dated_parents', 'uk_extracted_parents',
            'eu_dated_works', 'eu_source_text_parents', 'eu_ocr_review_candidates',
            'eu_scan_ocr_pending', 'us_dated_parents', 'us_cleaned_parents',
            'au_original_month_parents', 'au_cleaned_parents',
            'source_parent_sum_observed', 'source_parent_sum_readable',
            'validated_relevant_parents', 'coverage_state', 'paris_2015_window_offset',
        ]
        summary = defaultdict(int)
        missing_government = []
        with OUT.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fields)
            writer.writeheader()
            for month in months():
                ukn, ukr = uk_by_month.get(month, (0, 0))
                eun = eu_by_month.get(month, (0,))[0]
                usn, usr = us_by_month.get(month, (0, 0))
                aun, aur = au_by_month.get(month, (0, 0))
                observed = ukn + eun + usn + aun
                readable = ukr + eu_text[month] + usr + aur
                offset = (int(month[:4]) - 2015) * 12 + int(month[5:]) - 12
                event_offset = offset if -24 <= offset <= 24 else ''
                writer.writerow({
                    'year_month': month, 'role': 'government',
                    'uk_dated_parents': ukn, 'uk_extracted_parents': ukr,
                    'eu_dated_works': eun, 'eu_source_text_parents': eu_text[month],
                    'eu_ocr_review_candidates': eu_ocr[month],
                    'eu_scan_ocr_pending': eu_scan[month],
                    'us_dated_parents': usn, 'us_cleaned_parents': usr,
                    'au_original_month_parents': aun, 'au_cleaned_parents': aur,
                    'source_parent_sum_observed': observed,
                    'source_parent_sum_readable': readable,
                    'validated_relevant_parents': '',
                    'coverage_state': 'readable_parent_present' if readable else 'no_readable_parent',
                    'paris_2015_window_offset': event_offset,
                })
                summary['uk_observed'] += ukn
                summary['uk_readable'] += ukr
                summary['eu_observed'] += eun
                summary['eu_readable'] += eu_text[month]
                summary['us_observed'] += usn
                summary['us_readable'] += usr
                summary['au_observed'] += aun
                summary['au_readable'] += aur
                summary['government_months_observed'] += observed > 0
                summary['government_months_readable'] += readable > 0
                summary['paris_government_months_readable'] += event_offset != '' and readable > 0
                summary['eu_fills_uk_unreadable_months'] += ukr == 0 and eu_text[month] > 0
                summary['us_fills_uk_eu_unreadable_months'] += ukr == 0 and eu_text[month] == 0 and usr > 0
                if readable == 0:
                    missing_government.append(month)
                for role in ('media', 'public'):
                    writer.writerow({
                        'year_month': month, 'role': role,
                        'coverage_state': 'not_acquired_or_audited',
                        'paris_2015_window_offset': event_offset,
                    })
        print('output:', OUT)
        print('summary:', dict(summary))
        print('AU precise outcomes:', dict(au_outcomes))
        print('EU placeholders excluded:', len(placeholders))
        print('government months without readable parent:', missing_government)
    finally:
        uk.close()
        us_au.close()
        eu.close()


if __name__ == '__main__':
    main()
