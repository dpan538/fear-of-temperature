"""Read-only, selected-parent acceptance and monthly coverage for the 2015 bridge."""
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import duckdb

from acquire import DB, HERE, ROOT, US_SOURCE, us_fallback_path, us_path, verified_meta
from targeted_2015_bridge import selected_source_rows


OUT = HERE / 'reports/targeted_2015_bridge'
BASELINE = ROOT / 'docs/research/coverage_snapshot_2026-09-27/monthly_government_presence.csv'


def load(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def save(path, fields, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def original_header(path, row):
    if not path:
        return {'header_date': '', 'header_document_number': '',
                'header_action': '', 'header_subtype': '', 'header_date_match': 0,
                'header_document_number_match': 0,
                'header_rules_section': 0, 'header_epa_marker': 0}
    source = path.read_bytes()[:15000].decode('utf-8', 'replace')
    date_match = re.search(
        r'\[Federal Register Volume[^\]]*\((?:Monday|Tuesday|Wednesday|Thursday|Friday), '
        r'([A-Z][a-z]+ \d{1,2}, \d{4})\)\]', source)
    date = datetime.strptime(date_match.group(1), '%B %d, %Y').date().isoformat() if date_match else ''
    number_match = re.search(r'\[FR Doc No:\s*([^\]]+)\]', source)
    number = number_match.group(1).strip() if number_match else ''
    action_match = re.search(r'^ACTION:\s*(.+)$', source, flags=re.M)
    action = action_match.group(1).strip() if action_match else ''
    action_lower = action.lower()
    subtype = ('cfr_correction' if 'CFR Correction' in source[:4000] else
               'withdrawal' if 'withdrawal' in action_lower or 'withdrawing' in action_lower else
               'direct_final_rule' if 'direct final rule' in action_lower else
               'final_rule_or_amendment' if 'final rule' in action_lower else
               'other_action_in_rules_section' if action else
               'unspecified_action')
    return {
        'header_date': date,
        'header_document_number': number,
        'header_action': action,
        'header_subtype': subtype,
        'header_date_match': int(date == row['publication_date']),
        'header_document_number_match': int(number == row['document_number']),
        'header_rules_section': int('[Rules and Regulations]' in source),
        'header_epa_marker': int('ENVIRONMENTAL PROTECTION AGENCY' in source.upper()),
    }


def main():
    selected = load(OUT / 'selected_parents.csv')
    frame = load(OUT / 'metadata_frame_2012_2019.csv')
    baseline = load(BASELINE)
    urls = {r['canonical_url'] for r in selected}
    c = duckdb.connect(str(DB), read_only=True)
    try:
        # These source rows are a bounded slice of the existing 09 database.
        documents = {row[0]: row[1:] for row in c.execute("""
            SELECT canonical_url, document_id, source_id, CAST(publication_date AS VARCHAR),
                   content_type, body_status
            FROM documents
            WHERE source_id=? AND publication_date BETWEEN '2012-01-01' AND '2019-12-31'
        """, [US_SOURCE]).fetchall()}
        missing_metadata = urls - documents.keys()
        if missing_metadata:
            raise RuntimeError(f'{len(missing_metadata)} frozen selected parents missing from 09 DB')
        placeholders = ','.join('?' for _ in urls)
        version_rows = c.execute(f"""
            SELECT d.canonical_url, v.content_version_id, v.content_sha256,
                   v.raw_path, v.status_code, v.mime_type,
                   x.relationship_type, x.content_object_id
            FROM documents d JOIN document_content_objects x USING (document_id)
            JOIN content_versions v USING (content_object_id)
            WHERE d.canonical_url IN ({placeholders})
        """, list(urls)).fetchall()
        by_url = defaultdict(list)
        for row in version_rows:
            by_url[row[0]].append(row[1:])
        version_ids = [row[1] for row in version_rows]
        text_by_version = {}
        if version_ids:
            placeholders = ','.join('?' for _ in version_ids)
            for version_id, source_segments, source_characters, cleaned_segments in c.execute(f"""
                SELECT content_version_id,
                       count(*) FILTER (WHERE representation_kind='source_extracted'),
                       coalesce(sum(length(segment_text)) FILTER
                           (WHERE representation_kind='source_extracted'),0),
                       count(*) FILTER (WHERE representation_kind='cleaned')
                FROM text_segments
                WHERE content_version_id IN ({placeholders})
                GROUP BY 1
            """, version_ids).fetchall():
                text_by_version[version_id] = (source_segments, source_characters, cleaned_segments)
    finally:
        c.close()

    acceptance = []
    for row in selected:
        url = row['canonical_url']
        did, source, date, genre, body = documents[url]
        source_identity_ok = (source == US_SOURCE and date == row['publication_date']
                              and genre == 'final_rule')
        versions = by_url[url]
        raw_path = us_path(row)
        raw_meta = verified_meta(raw_path)
        fallback_path = us_fallback_path(row)
        fallback_meta = verified_meta(fallback_path) if not raw_meta else None
        verified = raw_meta or fallback_meta
        primary_checkpoint = raw_path.with_suffix(raw_path.suffix + '.request.json')
        fallback_checkpoint = fallback_path.with_suffix(fallback_path.suffix + '.request.json')
        if verified:
            request_meta = verified
        elif fallback_checkpoint.exists():
            request_meta = json.loads(fallback_checkpoint.read_text())
        elif primary_checkpoint.exists():
            request_meta = json.loads(primary_checkpoint.read_text())
        else:
            request_meta = {}
        source_path = raw_path if raw_meta else fallback_path if fallback_meta else None
        header = original_header(source_path, row)
        header_ok = all(header[key] for key in (
            'header_date_match', 'header_document_number_match',
            'header_rules_section', 'header_epa_marker'))
        accepted_version = None
        for version in versions:
            version_id, digest, stored_path, status, mime, relationship, obj = version
            if (verified and digest == verified['sha256'] and
                    stored_path == verified['raw_path'] and 200 <= status < 300):
                accepted_version = version
                break
        source_segments, source_characters, cleaned_segments = (
            text_by_version.get(accepted_version[0], (0, 0, 0)) if accepted_version else (0, 0, 0))
        state = ('source_text_extracted' if source_identity_ok and header_ok and accepted_version and source_characters > 0
                 else 'source_text_identity_review' if accepted_version and source_characters > 0
                 else 'committed_no_source_text' if accepted_version else
                 'downloaded_pending_insert' if verified else 'metadata_only_or_request_failed')
        acceptance.append({
            'year_month': row['publication_date'][:7], 'selection_role': row['selection_role'],
            'selection_rank': row['selection_rank'], 'canonical_url': url,
            'document_number': row['document_number'], 'publication_date': row['publication_date'],
            'document_id': did, 'source_id': source, 'genre': genre,
            'source_identity_date_genre_ok': int(source_identity_ok),
            **header,
            'verified_original': int(bool(verified)),
            'source_route': ('federalregister_raw_text' if raw_meta else
                             'official_govinfo_html_fallback' if fallback_meta else ''),
            'raw_sha256': verified['sha256'] if verified else '',
            'raw_path': verified['raw_path'] if verified else '',
            'request_url': request_meta.get('request_url', ''),
            'resolved_url': request_meta.get('final_url', ''),
            'last_http_status': request_meta.get('http_status', ''),
            'last_request_status': request_meta.get('status', ''),
            'last_request_error': request_meta.get('error', ''),
            'committed_content_version_id': accepted_version[0] if accepted_version else '',
            'source_segments': source_segments, 'source_characters': source_characters,
            'cleaned_segments': cleaned_segments, 'body_status': body, 'acceptance_state': state,
        })
    if len(acceptance) != 125:
        raise RuntimeError('selected parent acceptance does not contain 125 rows')
    save(OUT / 'parent_acceptance.csv', list(acceptance[0]), acceptance)

    selected_by_month = defaultdict(list)
    for row in acceptance:
        selected_by_month[row['year_month']].append(row)
    eligible_by_month = defaultdict(list)
    for row in selected_source_rows():
        eligible_by_month[row['publication_date'][:7]].append(row['canonical_url'])
    source_rows = []
    for row in frame:
        month = row['year_month']
        selected_month = selected_by_month[month]
        eligible = int(row['eligible_unique_parent_count'])
        downloaded = sum(int(x['verified_original']) for x in selected_month)
        committed = sum(bool(x['committed_content_version_id']) for x in selected_month)
        extracted = sum(x['acceptance_state']=='source_text_extracted' for x in selected_month)
        committed_status_count = sum(documents[url][4]=='source_extracted_and_cleaned'
                                     for url in eligible_by_month[month])
        state = ('verified_zero_in_frozen_series' if eligible == 0 else
                 'metadata_only_not_requested' if not selected_month else
                 'full_gap_month_source_text_extracted' if len(selected_month) == eligible and extracted == eligible else
                 'selected_source_text_partial' if extracted else
                 'downloaded_pending_or_unextractable' if downloaded or committed else
                 'selected_request_pending_or_failed')
        source_rows.append({**row,
            'selected_parent_count': len(selected_month),
            'selected_verified_original_count': downloaded,
            'selected_committed_version_count': committed,
            'selected_nonempty_source_text_count': extracted,
            'committed_extracted_parent_status_count': committed_status_count,
            'metadata_only_or_unverified_parent_count': eligible - committed_status_count,
            'unselected_eligible_parent_count': eligible - len(selected_month),
            'coverage_state': state,
        })
    save(OUT / 'monthly_source_coverage_2012_2019.csv', list(source_rows[0]), source_rows)

    new_text = Counter(x['year_month'] for x in acceptance if x['acceptance_state']=='source_text_extracted')
    global_rows = []
    for row in baseline:
        month = row['year_month']
        before = int(row['pooled_government_text_present'])
        after = int(bool(before or new_text[month]))
        global_rows.append({**row,
            'targeted_us_epa_final_rule_source_text_parents': new_text[month],
            'pooled_government_text_present_updated': after,
            'presence_change_due_to_bridge': after - before,
        })
    save(OUT / 'updated_monthly_government_presence.csv', list(global_rows[0]), global_rows)
    print({
        'selected': len(acceptance),
        'source_text_parents': sum(x['acceptance_state']=='source_text_extracted' for x in acceptance),
        'full_gap': {m: sum(x['acceptance_state']=='source_text_extracted' for x in selected_by_month[m])
                     for m in ('2015-04', '2015-05')},
        'continuity_sample': {m: sum(x['acceptance_state']=='source_text_extracted' for x in selected_by_month[m])
                              for m in ('2013-12','2014-04','2014-05','2015-03','2015-06','2016-04','2016-05','2017-12')},
        'pooled_before': sum(int(x['pooled_government_text_present']) for x in global_rows),
        'pooled_after': sum(int(x['pooled_government_text_present_updated']) for x in global_rows),
    })


if __name__ == '__main__':
    main()
