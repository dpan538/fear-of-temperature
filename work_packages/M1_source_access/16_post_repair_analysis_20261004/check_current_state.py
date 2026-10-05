"""One read-only UK metadata aggregate plus bounded saved-ledger reconciliation.

No network calls, text scan, validator rerun, formal writes or acquisition.
"""
import collections
import csv
import fcntl
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'work_packages/M1_source_access'
TASKS = BASE / '15_targeted_repairs_and_supplementation_20261004'
REPAIR = TASKS / '03_existing_data_repair'
PLAN = TASKS / '04_targeted_supplementation'
AUDIT = BASE / '13_parallel_data_audit_20261004/02_distribution'


def rows(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def save_csv(name, values, fields=None):
    fields = fields or list(values[0])
    with (HERE / name).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(values)


def main():
    release_path = TASKS / 'control/REPAIR_READY.json'
    release = json.loads(release_path.read_text())
    db = ROOT / release['authority']
    checkpoint = lambda: {'bytes': db.stat().st_size, 'mtime_ns': db.stat().st_mtime_ns}
    before = checkpoint()
    expected = {k: release['post_checkpoint'][k] for k in before}
    if before != expected:
        raise RuntimeError('Release checkpoint moved; do not reuse the repair claims as current')
    sql = """
    SELECT source_id, content_type AS genre, analysis_month,
           count(*) AS parent_count,
           count(*) FILTER (WHERE exact_day_eligible) AS exact_day_parents,
           count(*) FILTER (WHERE date_interval_start IS NOT NULL) AS interval_parents,
           count(*) FILTER (WHERE parent_origin = 'recovered_saved_original') AS locally_derived_additional_parents,
           count(*) FILTER (WHERE current_technical_state IS NOT NULL) AS state_annotation_parents,
           count(*) FILTER (WHERE publication_date < DATE '1988-01-01'
                             OR publication_date > DATE '2026-09-21'
                             OR date_interval_start < DATE '1988-01-01'
                             OR date_interval_end > DATE '2026-09-21') AS outside_fixed_interval,
           count(*) FILTER (WHERE publication_date IS NULL AND date_interval_start IS NULL) AS no_supported_date
    FROM repair_current_documents
    GROUP BY source_id, content_type, analysis_month
    ORDER BY source_id, content_type, analysis_month
    """
    (HERE / 'uk_metadata_aggregate.sql').write_text(sql.strip() + ';\n')
    lock_path = BASE / '14_structural_validation_20261004/control/heavy_io.lock'
    with lock_path.open('a+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            connection = duckdb.connect(str(db), read_only=True,
                                        config={'threads': 1, 'memory_limit': '1GB'})
            try:
                result = connection.execute(sql)
                columns = [x[0] for x in result.description]
                aggregate = [dict(zip(columns, row)) for row in result.fetchall()]
            finally:
                connection.close()
            after = checkpoint()
            if before != after:
                raise RuntimeError('Checkpoint changed during read')
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
    save_csv('uk_effective_month_source_genre.csv', aggregate)
    total = lambda field: sum(x[field] for x in aggregate)
    assert total('parent_count') == release['post_effective_parent_count'] == 248319
    assert total('interval_parents') == 124
    assert total('locally_derived_additional_parents') == 284
    assert total('outside_fixed_interval') == 0
    assert total('no_supported_date') == 0
    assert sum(x['parent_count'] for x in aggregate if x['analysis_month'] is None) == 51

    baseline = rows(AUDIT / 'monthly_source_genre_counts.csv')
    labels = {x['source_id']: x['source_label'] for x in baseline}
    old = {(x['source_id'], x['genre'], x['month']): int(x['parent_count'])
           for x in baseline if x['source_id'] in labels}
    deltas = []
    composition = collections.defaultdict(lambda: collections.Counter())
    for x in aggregate:
        month = x['analysis_month'] or 'UNASSIGNED_CROSS_MONTH_INTERVAL'
        legacy = old.get((x['source_id'], x['genre'], month), 0)
        if x['parent_count'] != legacy:
            deltas.append({'source_id': x['source_id'], 'source_label': labels[x['source_id']],
                           'genre': x['genre'], 'month': month, 'legacy_audit_parents': legacy,
                           'effective_parents': x['parent_count'], 'delta': x['parent_count'] - legacy,
                           'additional_locally_derived_parents': x['locally_derived_additional_parents'],
                           'interval_parents': x['interval_parents']})
        key = (x['source_id'], x['genre'])
        for field in ('parent_count', 'exact_day_parents', 'interval_parents',
                      'locally_derived_additional_parents', 'state_annotation_parents'):
            composition[key][field] += x[field]
        if x['analysis_month'] is not None:
            composition[key]['month_assignable_parents'] += x['parent_count']
    assert sum(x['delta'] for x in deltas) == 284
    assert len([x for x in deltas if x['month'] != 'UNASSIGNED_CROSS_MONTH_INTERVAL']) == 9
    save_csv('uk_changed_month_comparison.csv', deltas)
    source_counts = [{'source_id': k[0], 'source_label': labels[k[0]], 'genre': k[1], **dict(v)}
                     for k, v in composition.items()]
    save_csv('uk_effective_source_genre.csv', source_counts,
             ['source_id', 'source_label', 'genre', 'parent_count', 'exact_day_parents',
              'interval_parents', 'locally_derived_additional_parents',
              'state_annotation_parents', 'month_assignable_parents'])

    requests = rows(REPAIR / 'missing_original_requests.csv')
    unresolved = rows(REPAIR / 'unresolved_cases.csv')
    assert len(requests) == 5 and len({x['unit_id'] for x in requests}) == 5
    assert len(unresolved) == 318 and len({x['unit_id'] for x in unresolved}) == 165
    exception_summary = []
    for (source, category), count in collections.Counter((x['source'], x['category']) for x in unresolved).items():
        units = {x['unit_id'] for x in unresolved if x['source'] == source and x['category'] == category}
        exception_summary.append({'source': source, 'category': category, 'issue_instances': count,
                                  'distinct_units_within_category': len(units),
                                  'unit_counts_additive_across_categories': False})
    save_csv('remaining_exception_summary.csv', exception_summary)

    manifest = rows(PLAN / 'frozen_acquisition_manifest.csv')
    population = rows(PLAN / 'source_frame_population.csv')
    relationships = rows(PLAN / 'selected_work_item_relationships.csv')
    contract = json.loads((PLAN / 'ACQUISITION_CONTRACT.json').read_text())
    assert digest(PLAN / 'frozen_acquisition_manifest.csv') == contract['manifest_sha256']
    assert len(manifest) == len({x['parent_id'] for x in manifest}) == 979
    assert len(population) == len({x['parent_id'] for x in population}) == 1009
    assert len(relationships) == 8409
    assert len({x['month'] for x in manifest}) == 12
    links = collections.defaultdict(list)
    for x in relationships:
        links[x['parent_id']].append(x)
    multiplicity = []
    for x in manifest:
        group = links[x['parent_id']]
        selected_siblings = {y['item_uri'] for y in group if y['manifestation_uri'] == x['manifestation_uri']}
        same_format = {y['item_uri'] for y in group if y['format'] == x['format']}
        all_items = {y['item_uri'] for y in group}
        assert int(x['unique_item_alternatives']) == len(all_items)
        multiplicity.append({'parent_id': x['parent_id'], 'month': x['month'],
                             'selected_format': x['format'], 'all_distinct_item_alternatives': len(all_items),
                             'selected_manifestation_distinct_items': len(selected_siblings),
                             'selected_format_distinct_items': len(same_format),
                             'component_roles': 'unresolved from saved relationship metadata alone'})
    save_csv('eu_selected_item_multiplicity.csv', multiplicity)
    # Load definitions without creating a pycache or invoking main()/network code.
    source = PLAN / 'stage_frozen_items.py'
    namespace = {'__file__': str(source), '__name__': 'read_only_inspection'}
    exec(compile(source.read_text(), str(source), 'exec'), namespace)
    preflight = namespace['preflight'](contract, digest(release_path))
    assert preflight['repair_gate_passes'] is False
    assert preflight['status'] == 'release_content_not_recognised_as_committed_checked_checkpoint_with_request_paths'
    save_json('task4_read_only_preflight.json', preflight)
    summary = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'fixed_publication_interval': ['1988-01-01', '2026-09-21'],
        'database_checkpoint_matches_release': True, 'checkpoint_before': before, 'checkpoint_after': after,
        'effective_UK_parents': total('parent_count'), 'UK_month_assignable_parents': total('parent_count') - 51,
        'UK_exact_day_parents': total('exact_day_parents'), 'interval_parents': total('interval_parents'),
        'cross_month_unassigned_parents': 51, 'locally_derived_additional_parents': 284,
        'UK_month_parent_net_change': sum(x['delta'] for x in deltas if x['month'] != 'UNASSIGNED_CROSS_MONTH_INTERVAL'),
        'calendar_months_changed': 9, 'outside_fixed_interval': total('outside_fixed_interval'),
        'no_supported_date': total('no_supported_date'), 'unresolved_issue_instances': len(unresolved),
        'unresolved_units': len({x['unit_id'] for x in unresolved}), 'final_original_requests': len(requests),
        'EU_population_works': len(population), 'EU_selected_item_targets': len(manifest),
        'EU_no_link_works': len(population) - len(manifest),
        'EU_selected_works_multiple_item_alternatives': sum(x['all_distinct_item_alternatives'] > 1 for x in multiplicity),
        'EU_selected_works_multiple_selected_manifestation_items': sum(x['selected_manifestation_distinct_items'] > 1 for x in multiplicity),
        'EU_selected_works_multiple_selected_format_items': sum(x['selected_format_distinct_items'] > 1 for x in multiplicity),
        'EU_new_downloads_in_this_analysis': 0, 'aggregate_queries': 1,
        'aggregate_scope': 'UK effective document metadata only; no text scan or pooled readable-text recalculation',
        'pooled_465_month_text_presence': 'historical checkpoint; not freshly calculated',
        'task4_script_gate_compatible_with_release': False, 'storage_gate_passes_at_check': preflight['storage_gate_passes'],
        'figure_count': 0,
    }
    assert summary['EU_selected_works_multiple_item_alternatives'] == 973
    save_json('CHECKED_STATE.json', summary)
    inputs = [release_path, REPAIR/'REPORT.md', REPAIR/'RESULT.json', REPAIR/'changed_tranche_month_counts.csv',
              REPAIR/'missing_original_requests.csv', REPAIR/'unresolved_cases.csv',
              REPAIR/'FINAL_SAVED_TRANCHE_CHECKS.json', REPAIR/'REQUEST_RECONCILIATION.json',
              PLAN/'REPORT.md', PLAN/'SOURCE_FRAME_PLAN.md', PLAN/'ACQUISITION_CONTRACT.json',
              PLAN/'frozen_acquisition_manifest.csv', PLAN/'source_frame_population.csv',
              PLAN/'selected_work_item_relationships.csv', PLAN/'source_composition_2015.csv',
              PLAN/'coverage_expected_vs_observed.csv', source,
              AUDIT/'INPUT_MANIFEST.json', AUDIT/'monthly_source_genre_counts.csv', AUDIT/'REPORT.md']
    save_json('INPUT_MANIFEST.json', {'generated_at_utc': summary['checked_at_utc'],
              'database': {'path': release['authority'], **before, 'whole_database_hash': 'not performed'},
              'saved_inputs': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
                                'sha256': digest(p)} for p in inputs],
              'formal_database_writes': 0, 'network_body_downloads': 0,
              'heavy_io_lock': str(lock_path.relative_to(ROOT)), 'lock_file_unlinked': False})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
