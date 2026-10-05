"""Freeze a bounded 2015 CELLAR candidate-Item plan from saved metadata only.

No network, formal database access, raw-body reads, or shared-file writes.
Run once from any directory; verify_plan.py checks the resulting frozen files.
"""
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
WP = ROOT / 'work_packages/M1_source_access'
EU = WP / '10_eu_cellar_acquisition'
DIST = WP / '13_parallel_data_audit_20261004/02_distribution'
TASK1 = WP / '14_structural_validation_20261004/01_archive_split'
CONTROL = OUT.parent / 'control'
PREF = {'pdfa1b': 0, 'pdfa1a': 1, 'pdf': 2, 'pdf1x': 3,
        'html': 4, 'xhtml': 5, 'docx': 6, 'xml': 7}
NOW = datetime.now(timezone.utc).isoformat()
INPUTS = {}


def read(path, kind='text'):
    data = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = {
        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
        'mtime_utc': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}
    if kind == 'json':
        return json.loads(data)
    if kind == 'csv':
        return list(csv.DictReader(data.decode('utf-8').splitlines()))
    return data.decode('utf-8')


def write_csv(name, rows, fields=None):
    fields = fields or list(rows[0])
    with (OUT / name).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    if (OUT / 'frozen_acquisition_manifest.csv').exists():
        raise SystemExit('Plan already frozen. Use verify_plan.py; do not silently re-freeze.')
    for path in [ROOT/'AGENTS.md', ROOT/'docs/PROJECT_DIRECTION.md', ROOT/'docs/PROJECT_LOG.md',
                 OUT.parent/'ACCEPTANCE_AND_SCOPE.md', OUT.parent/'COORDINATION.json',
                 CONTROL/'storage_status.json', EU/'FILTER_CONTRACT.md', EU/'RUNBOOK.md',
                 DIST/'REPORT.md', DIST/'REPAIR_LIST.md', DIST/'anomaly_ledger.csv',
                 TASK1/'RESULT.json', WP/'14_structural_validation_20261004/02_provenance_logic/RESULT.json',
                 WP/'11_paris_readiness_pilot_20260927/SCOPE.md']:
        read(path)
    counts = read(DIST/'monthly_source_genre_counts.csv', 'csv')
    exceptions = read(TASK1/'exceptions.csv', 'csv')
    override_path = EU/'manifests/item_selection_overrides.json'
    overrides = read(override_path, 'json') if override_path.exists() else {}
    population, targets, coverage, relationships = [], [], [], []
    seen_works, seen_items = set(), set()
    for month_no in range(1, 13):
        month = f'2015-{month_no:02d}'
        parent_file = EU/'manifests/months'/f'{month}.csv'
        wemi_file = EU/'manifests/wemi'/f'{month}.csv'
        parents, wemi = read(parent_file, 'csv'), read(wemi_file, 'csv')
        parent_check = read(parent_file.with_suffix('.json'), 'json')
        wemi_check = read(wemi_file.with_suffix('.json'), 'json')
        dates, source_pages, by_work = defaultdict(set), defaultdict(set), defaultdict(list)
        for row in parents:
            dates[row['work_uri']].add(row['date_observed'])
            source_pages[row['work_uri']].add(row['source_page'])
            assert row['date_observed'][:7] == month
        for row in wemi:
            by_work[row['work']].append(row)
        assert parent_check['status'] == 'reconciled'
        assert len(dates) == parent_check['expected_distinct_works'] == parent_check['observed_distinct_works']
        assert wemi_check['status'] == 'complete'
        assert len(dates) == wemi_check['enumerated_works']
        linked, missing, observed_saved, observed_checks = 0, 0, 0, 0
        for work in sorted(dates):
            assert work not in seen_works
            seen_works.add(work)
            candidates = sorted(by_work[work], key=lambda r: (PREF.get(r['format'].lower(),100), r['item']))
            if work in overrides:
                preferred = [r for r in candidates if r['item'] == overrides[work]['item_uri']]
                assert len(preferred) == 1
                candidates = preferred + [r for r in candidates if r['item'] != overrides[work]['item_uri']]
            base = {
                'tranche': 'B', 'source_id': 'EU_CELLAR_COM', 'jurisdiction': 'EU_supranational',
                'discourse_role': 'government', 'issuer': 'COM', 'genre': 'COM act_preparatory',
                'language': 'ENG', 'month': month, 'publication_dates': ';'.join(sorted(dates[work])),
                'date_support': 'saved official CDM work_date_document; Item printed date pending',
                'unit': 'distinct CELLAR Work URI', 'parent_id': work,
                'parent_manifest': str(parent_file.relative_to(ROOT)),
                'work_query_evidence': ';'.join(str((EU/s).relative_to(ROOT)) for s in sorted(source_pages[work])),
                'metadata_checkpoint_utc': parent_check['updated_at_utc'],
                'existing_vs_new': 'existing_enumerated_parent_candidate_new_body',
                'directness_expected': 'official archival reproduction of COM publication; body pending',
                'cross_source_dedup': 'independent institutional publication expected; exact identity/body pending',
                'rights_access': 'public official route; document-specific third-party conditions pending',
                'body_verification': 'not acquired; identity/date/content boundary pending',
            }
            if not candidates:
                missing += 1
                population.append({**base, 'item_uri': '', 'format': '', 'unique_item_alternatives': 0,
                                   'raw_or_checkpoint_present': False, 'route_status': 'no_saved_English_digital_Item_link'})
                continue
            linked += 1
            choice = candidates[0]
            item = choice['item']
            assert item not in seen_items, 'A selected Item is shared across Works; freeze requires adjudication.'
            seen_items.add(item)
            digest = hashlib.sha256(item.encode()).hexdigest()
            local = EU/'raw/items'/digest[:2]/f'{digest}.bin'
            checkpoint = local.with_suffix('.request.json')
            paths = [local, checkpoint]
            external = EU/'raw/items_external'
            if external.is_symlink():
                paths += [external/digest[:2]/f'{digest}.bin', (external/digest[:2]/f'{digest}.bin').with_suffix('.request.json')]
            present = any(p.exists() for p in paths)
            observed_saved += int(local.exists())
            observed_checks += int(checkpoint.exists())
            unique_items = len({r['item'] for r in candidates})
            population.append({**base, 'item_uri': item, 'format': choice['format'],
                               'unique_item_alternatives': unique_items, 'raw_or_checkpoint_present': present,
                               'route_status': 'existing_local_object_requires_reuse' if present else 'saved_route_not_requested_locally'})
            for r in candidates:
                relationships.append({'month': month, 'parent_id': work, 'expression_uri': r['expr'],
                                      'manifestation_uri': r['manif'], 'item_uri': r['item'], 'format': r['format'],
                                      'selected': r['item'] == item,
                                      'evidence_locator': str((EU/r['source_page']).relative_to(ROOT))})
            if present:
                continue
            targets.append({**base, 'expression_uri': choice['expr'], 'manifestation_uri': choice['manif'],
                            'item_uri': item, 'format': choice['format'],
                            'item_relationship_rows': len(candidates), 'unique_item_alternatives': unique_items,
                            'item_route_evidence': str((EU/choice['source_page']).relative_to(ROOT)),
                            'request_url': item.replace('http://','https://',1),
                            'expected_bytes': 1048576, 'expected_bytes_basis': 'planning scenario 1 MiB/Item; not measured Content-Length',
                            'max_object_bytes': 100000000,
                            'local_existing_item_path': str(local.relative_to(ROOT)),
                            'staging_path': f'raw/items/{digest[:2]}/{digest}.bin',
                            'acquisition_status': 'frozen_not_acquired'})
        assert linked == wemi_check['works_with_items']
        assert missing == wemi_check['works_without_items']
        existing_eu_count = [r for r in counts if r['source_label']=='EU CELLAR COM' and r['month']==month]
        assert len(existing_eu_count)==1 and int(existing_eu_count[0]['parent_count'])==len(dates)
        coverage.append({'source_id':'EU_CELLAR_COM','genre':'COM act_preparatory','month':month,
                         'enumerated_parent_works':len(dates),'candidate_item_works':linked,'no_item_link_works':missing,
                         'expected_new_candidate_bodies_upper_bound':linked-observed_saved,
                         'expected_bytes_scenario':(linked-observed_saved)*1048576,
                         'observed_saved_local_raw_files':observed_saved,'observed_local_request_checkpoints':observed_checks,
                         'audit_operational_extracted_status_parents':int(existing_eu_count[0]['extracted_status_parent_count']),
                         'observed_task4_downloads':0,'observed_task4_verified_full_bodies':0,
                         'readable_complete_body_count':'unassessed',
                         'coverage_claim':'enumerated metadata and candidate routes only; no acquisition claim'})
    provisional = []
    for row in exceptions:
        if row['adapter']=='archive_detail_json' and row['status']=='insufficient_evidence' and '/search/' in row['raw_path']:
            provisional.append({'tranche':'A','source_id':row['source_id'],'genre':'ministerial_written_answer',
                                'unit':'existing Hansard answer parent','parent_id':row['document_id'],
                                'external_id':row['external_id'],'publication_date':'',
                                'date_support':'pending Task3 request manifest; no day inferred from identifier',
                                'request_url':f"https://hansard-api.parliament.uk/debates/debate/{row['external_id']}.json",
                                'expected_bytes':262144,'max_object_bytes':2000000,
                                'route_evidence':'existing historical_government_acquisition.py HANSARD_API/debate route; live detail untested',
                                'reason':row['details'],'evidence_locator':row['evidence_locator'],
                                'existing_vs_new':'same recorded utterance; missing detail may strengthen mapping, not independent discourse',
                                'request_status':'provisional_only_wait_for_Task3_missing_original_requests.csv',
                                'fetch_permitted':False})
    write_csv('potential_requests.csv', provisional)
    write_csv('frozen_acquisition_manifest.csv', targets)
    write_csv('source_frame_population.csv', population)
    write_csv('selected_work_item_relationships.csv', relationships)
    write_csv('coverage_expected_vs_observed.csv', coverage)
    composition = [r for r in counts if '2015-01'<=r['month']<='2015-12']
    write_csv('source_composition_2015.csv', composition)
    stats = {'population_works':len(population),'frozen_candidate_item_targets':len(targets),
             'no_item_works':sum(not r['item_uri'] for r in population),
             'selected_formats':dict(Counter(r['format'] for r in targets)),
             'selected_works_multiple_item_alternatives':sum(int(r['unique_item_alternatives'])>1 for r in targets),
             'relationship_rows_preserved':len(relationships), 'provisional_A_parents':len(provisional)}
    contract = {'contract_version':'task4_eu_com_2015_v1','created_at_utc':NOW,
                'study_publication_interval':['1988-01-01','2026-09-21'],
                'tranche_publication_interval':['2015-01-01','2015-12-31'], 'months':12,
                'manifest_sha256':hashlib.sha256((OUT/'frozen_acquisition_manifest.csv').read_bytes()).hexdigest(),
                'stats':stats,'expected_raw_bytes_scenario':len(targets)*1048576,
                'budget':{'collector_floor_bytes':15*2**30,'aggregate_new_raw_cap_bytes':2*2**30,
                          'inflight_object_reserve_bytes':100000000,'checkpoint_error_reserve_bytes':64*2**20,
                          'repair_other_activity_reserve_bytes':1*2**30,
                          'extraction_in_this_download_tranche':False},
                'rate_limit':{'parallel_requests':1,'minimum_request_spacing_seconds':2,
                              'retries':'one attempt per object per invocation; checkpoint failure and stop; no automatic restart'},
                'dedup':'Work URI parent; Item URI + byte SHA256 version; recheck existing target paths before requests',
                'parent_metadata_new_rows':0,'semantic_filters':None,'formal_database_writes':False,
                'repair_request_path':str((OUT.parent/'03_existing_data_repair/missing_original_requests.csv').relative_to(ROOT)),
                'repair_release_path':str((CONTROL/'REPAIR_READY.json').relative_to(ROOT))}
    write_json('ACQUISITION_CONTRACT.json', contract)
    write_json('INPUT_MANIFEST.json', {'generated_at_utc':NOW,'root':str(ROOT),'inputs':INPUTS,
                                     'formal_databases_opened':[],'raw_body_files_read':[],
                                     'heavy_read_attempt':'shared heavy_io.lock busy; 24.6 MB disposition-ledger scan not run',
                                     'bounded_metadata_method':'12 month manifests, 12 WEMI manifests and exception/distribution CSVs; path existence only',
                                     'provenance':'saved metadata checkpoints, not fresh full-text enumeration'})
    free = shutil.disk_usage(ROOT).free
    budget = contract['budget']
    projection = sum(budget[k] for k in ['aggregate_new_raw_cap_bytes','inflight_object_reserve_bytes',
                                        'checkpoint_error_reserve_bytes','repair_other_activity_reserve_bytes'])
    marker = CONTROL/'REPAIR_READY.json'
    write_json('PREFLIGHT.json', {'checked_at_utc':datetime.now(timezone.utc).isoformat(),'free_bytes':free,
                                'free_gib':free/2**30,'floor_bytes':budget['collector_floor_bytes'],
                                'projected_max_footprint_plus_reserves_bytes':projection,
                                'projected_remaining_gib':(free-projection)/2**30,
                                'storage_gate_passes':free-projection>budget['collector_floor_bytes'],
                                'repair_marker_exists':marker.exists(), 'repair_marker_evaluated':False,
                                'status':'waiting_on_repair' if not marker.exists() else 'release_requires_content_review',
                                'downloads_started':False})
    print(json.dumps({'stats':stats,'free_gib':round(free/2**30,3),'release_exists':marker.exists()}))


if __name__ == '__main__':
    main()
