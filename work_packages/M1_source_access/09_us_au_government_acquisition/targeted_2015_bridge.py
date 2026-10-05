"""Frozen EPA final-rule bridge for the April/May 2015 source-text gap.

Uses only the already enumerated Federal Register parents. The full gap-month
denominators and the validation sample are fixed before any new request.
"""
import argparse
import csv
import fcntl
import hashlib
import json
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from acquire import (HERE, ROOT, US_CSV, save_fetch, us_fallback_path, us_path,
                     us_raw_url, us_rows, verified_meta)
from us_govinfo_fallback import fetch as fetch_govinfo, url_for as govinfo_url


OUT = HERE / 'reports/targeted_2015_bridge'
MANIFEST = OUT / 'selected_parents.csv'
FRAME = OUT / 'metadata_frame_2012_2019.csv'
STATE = OUT / 'acquisition_state.json'
GAP_MONTHS = ('2015-04', '2015-05')
SAMPLE_MONTHS = ('2013-12', '2014-04', '2014-05', '2015-03',
                 '2015-06', '2016-04', '2016-05', '2017-12')
MIN_FREE_BYTES = 15_000_000_000


def stamp():
    return datetime.now(timezone.utc).isoformat()


def selected_source_rows():
    return [r for r in us_rows()
            if '2012-01' <= r['publication_date'][:7] <= '2019-12'
            and r['genre'] == 'final_rule'
            and 'EPA' in r['agency_strata'].split(';')]


def month_rows(rows):
    out = defaultdict(list)
    for row in rows:
        out[row['publication_date'][:7]].append(row)
    for month in out:
        out[month].sort(key=lambda r: (r['publication_date'],
                                       r['document_number'], r['canonical_url']))
    return out


def selection(rows):
    by_month = month_rows(rows)
    answer = []
    for month in GAP_MONTHS:
        for row in by_month[month]:
            answer.append({**row, 'selection_role': 'full_gap_month',
                           'selection_rank': ''})
    for month in SAMPLE_MONTHS:
        ordered = by_month[month]
        if len(ordered) < 3:
            raise RuntimeError(f'not enough frozen candidates for {month}')
        for q in (1, 5, 9):
            index = (len(ordered) - 1) * q // 10
            answer.append({**ordered[index], 'selection_role': 'continuity_sample',
                           'selection_rank': f'{q}/10'})
    if len({r['canonical_url'] for r in answer}) != len(answer):
        raise RuntimeError('selection contains a duplicate canonical parent')
    return answer


def write_csv_once(path, fields, rows):
    from io import StringIO
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore',
                            lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    content = stream.getvalue()
    if path.exists() and path.read_text(encoding='utf-8') != content:
        raise RuntimeError(f'frozen output changed: {path}')
    if not path.exists():
        path.write_text(content, encoding='utf-8')


def prepare():
    OUT.mkdir(exist_ok=True)
    rows = selected_source_rows()
    by_month = month_rows(rows)
    paris = [f'{year:04d}-{month:02d}' for year in range(2013, 2018)
             for month in range(1, 13)
             if '2013-12' <= f'{year:04d}-{month:02d}' <= '2017-12']
    if len(paris) != 49 or any(not by_month[month] for month in paris):
        raise RuntimeError('EPA final-rule metadata is not positive in all Paris bins')
    chosen = selection(rows)
    if len(chosen) != 125 or (len(by_month['2015-04']), len(by_month['2015-05'])) != (63, 38):
        raise RuntimeError('frozen bridge denominator or sample size changed')
    manifest_fields = list(chosen[0])
    write_csv_once(MANIFEST, manifest_fields, chosen)
    scheduled = Counter(r['publication_date'][:7] for r in chosen)
    frame = []
    for year in range(2012, 2020):
        for month in range(1, 13):
            key = f'{year:04d}-{month:02d}'
            members = by_month[key]
            frame.append({
                'year_month': key,
                'source_id': 'us_fr_epa_doe_rules_1994',
                'agency_rule': 'EPA_in_official_agency_strata',
                'genre_rule': 'final_rule',
                'date_basis': 'Federal_Register_official_publication_day',
                'eligible_unique_parent_count': len(members),
                'epa_doe_cross_agency_parent_count': sum('DOE' in r['agency_strata'].split(';') for r in members),
                'scheduled_full_gap_count': len(members) if key in GAP_MONTHS else 0,
                'scheduled_validation_sample_count': scheduled[key] if key in SAMPLE_MONTHS else 0,
                'metadata_status': 'verified_zero_in_frozen_series' if not members else 'enumerated',
            })
    write_csv_once(FRAME, list(frame[0]), frame)
    print(json.dumps({
        'frozen_us_manifest_sha256': hashlib.sha256(US_CSV.read_bytes()).hexdigest(),
        'selected_manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        'metadata_months_positive_2012_2019': sum(x['eligible_unique_parent_count'] > 0 for x in frame),
        'metadata_months_positive_paris_49': 49,
        'total_eligible_2012_2019': len(rows),
        'total_eligible_paris_49': sum(len(by_month[m]) for m in paris),
        'gap_targets': {m: len(by_month[m]) for m in GAP_MONTHS},
        'validation_targets': 24,
        'total_selected': len(chosen),
    }, indent=2))


def frozen_selected():
    with MANIFEST.open(newline='', encoding='utf-8') as handle:
        frozen = list(csv.DictReader(handle))
    expected = selection(selected_source_rows())
    if [(r['canonical_url'], r['selection_role']) for r in frozen] != [
            (r['canonical_url'], r['selection_role']) for r in expected]:
        raise RuntimeError('frozen selected parents differ from current enumerated metadata')
    return frozen


def latest_selected_429(rows):
    latest = None
    for row in rows:
        path = us_path(row)
        checkpoint = path.with_suffix(path.suffix + '.request.json')
        if not checkpoint.exists():
            continue
        meta = json.loads(checkpoint.read_text())
        if meta.get('http_status') == 429:
            when = datetime.fromisoformat(meta['retrieved_at_utc'].replace('Z', '+00:00'))
            latest = max(latest, when) if latest else when
    return latest


def acquire(not_before):
    rows = frozen_selected()
    now = datetime.now(timezone.utc)
    eligible = datetime.fromisoformat(not_before.replace('Z', '+00:00'))
    last_429 = latest_selected_429(rows)
    if last_429:
        eligible = max(eligible, last_429 + timedelta(hours=1))
    if now < eligible:
        raise RuntimeError(f'official 429 cooldown active until {eligible.isoformat()}')
    lock_paths = [HERE / 'checkpoints/us_polite_resume.lock',
                  HERE / 'checkpoints/supervisor.lock']
    locks = [path.open('r+') for path in lock_paths]
    try:
        for lock in locks:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        supervisor = json.loads((HERE / 'checkpoints/supervisor_state.json').read_text())
        if supervisor.get('status') != 'blocked_access_or_no_progress':
            raise RuntimeError(f'US supervisor is not stopped: {supervisor.get("status")}')
        attempted = 0
        fetched = 0
        failed = 0
        transport_failures = 0
        stop_reason = ''
        last_request = 0.0
        for row in rows:
            if verified_meta(us_path(row)) or verified_meta(us_fallback_path(row)):
                continue
            if shutil.disk_usage(HERE).free < MIN_FREE_BYTES:
                stop_reason = 'storage_floor'
                break
            path = us_path(row)
            checkpoint = path.with_suffix(path.suffix + '.request.json')
            old = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
            if old.get('http_status') in (404, 410):
                request_kind = 'official_govinfo_html_fallback'
            else:
                request_kind = 'federalregister_raw_text'
            delay = 1.0 - (time.monotonic() - last_request)
            if delay > 0:
                time.sleep(delay)
            if request_kind == 'federalregister_raw_text':
                meta = save_fetch(us_raw_url(row), path, expected='us_text')
                last_request = time.monotonic()
                attempted += 1
                if meta['http_status'] in (404, 410):
                    delay = 1.0 - (time.monotonic() - last_request)
                    if delay > 0:
                        time.sleep(delay)
                    meta = fetch_govinfo(row, checkpoint)
                    last_request = time.monotonic()
                    attempted += 1
                    request_kind = 'official_govinfo_html_fallback'
            else:
                meta = fetch_govinfo(row, checkpoint)
                last_request = time.monotonic()
                attempted += 1
            fetched += meta['status'] == 'downloaded'
            failed += meta['status'] != 'downloaded'
            transport_failures = transport_failures + 1 if meta['http_status'] == 0 else 0
            if attempted % 10 == 0 or meta['status'] != 'downloaded':
                print(json.dumps({'attempted': attempted, 'month': row['publication_date'][:7],
                                  'document_number': row['document_number'], 'route': request_kind,
                                  'http_status': meta['http_status'], 'status': meta['status'],
                                  'free_bytes': shutil.disk_usage(HERE).free}), flush=True)
            STATE.write_text(json.dumps({'updated_at_utc': stamp(), 'attempted_requests': attempted,
                                         'fetched_parents_this_run': fetched, 'failed_parents_this_run': failed,
                                         'last_document_number': row['document_number'],
                                         'stop_reason': stop_reason}, indent=2) + '\n')
            if meta['http_status'] in (403, 429, 503) or transport_failures >= 3:
                stop_reason = f'official_http_{meta["http_status"]}_or_transport_limit'
                break
        print(json.dumps({'fetch_done': True, 'attempted_requests': attempted,
                          'fetched_parents_this_run': fetched, 'failed_parents_this_run': failed,
                          'stop_reason': stop_reason or 'selection_processed'}), flush=True)
        # Existing insertion path is idempotent and keeps the canonical parent,
        # original date, version and source/clean mappings intact.
        command = [sys.executable, str(HERE / 'acquire.py'), 'ingest-us',
                   '--limit', str(len(rows) + 10)]
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            raise RuntimeError(f'targeted US ingestion failed: exit {result.returncode}')
        STATE.write_text(json.dumps({'updated_at_utc': stamp(), 'attempted_requests': attempted,
                                     'fetched_parents_this_run': fetched, 'failed_parents_this_run': failed,
                                     'stop_reason': stop_reason or 'selection_processed',
                                     'ingestion_exit_code': result.returncode}, indent=2) + '\n')
    finally:
        for lock in reversed(locks):
            lock.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare', 'acquire'])
    parser.add_argument('--not-before', default='2026-09-27T12:27:03.393039+00:00')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
    else:
        acquire(args.not_before)


if __name__ == '__main__':
    main()
