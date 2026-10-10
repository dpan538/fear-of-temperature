"""Finalize advisory outputs; never access stores, controls, bodies or network."""
import csv
import hashlib
import json
import shutil
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent
PIN=OUT/'worker/pinned'

def read(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))

def csvwrite(path,rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    diag=json.loads((OUT/'DIAGNOSTICS.json').read_text())
    named=json.loads((OUT/'worker/NAMED_NEWSPAPER_RECORD_CHECKS.json').read_text())
    parent=json.loads((OUT/'worker/NAMED_PRIMARY_PARENT_EVIDENCE.json').read_text())
    original=json.loads((OUT/'worker/INPUT_PIN_MANIFEST.json').read_text())
    rec=read(OUT/'2026_RECORD_MARKS.csv');checks={r['article_id']:r for r in named['rows']}
    for row in rec:
        row['native_raw_identity_date_link_status']='unreviewed'
        row['native_content_pair_status']='unreviewed'
        if row['record_id'] in checks:
            c=checks[row['record_id']]
            assert c['id_date_link_mapping_matches'],c
            row['native_original_body_read']=True
            row['review_scope']='named_saved_native_JSON_ID_date_link_content_check'
            row['native_raw_identity_date_link_status']='confirmed_for_saved_observation'
            row['reason_codes']+=';NAMED_NATIVE_ID_DATE_LINK_CONFIRMED'
            row['evidence_locator']+='|worker/NAMED_NEWSPAPER_RECORD_CHECKS.json#article_id='+row['record_id']
            row['recommended_next_action']='link_alias_candidate' if row['counterpart_ids'] else 'retain'
        if row['counterpart_ids']:
            row['reason_codes']+=';WORK_LINK_CANDIDATE_NOT_CONFIRMED_ENTITY_ALIAS'
            other=checks.get(row['counterpart_ids'])
            if row['record_id'] in checks and other:
                c=checks[row['record_id']]
                if c['content_rendered_sha256']==other['content_rendered_sha256']:
                    row['native_content_pair_status']='identical_saved_native_rendered_content_distinct_native_ID_date_or_link'
                    row['reason_codes']+=';NAMED_NATIVE_REPEAT_CONTENT_CONFIRMED_WORK_RELATION_CANDIDATE'
                elif c['plain_rendered_whitespace_sha256']==other['plain_rendered_whitespace_sha256']:
                    row['native_content_pair_status']='identical_visible_normalized_native_text_rendered_HTML_differs_distinct_ID_date_or_link'
                    row['reason_codes']+=';NAMED_VISIBLE_TEXT_REPEAT_CONFIRMED_WORK_RELATION_CANDIDATE'
    baseline=OUT/'worker/metadata_mark_base';baseline.mkdir(exist_ok=False)
    (OUT/'2026_RECORD_MARKS.csv').rename(baseline/'2026_RECORD_MARKS.csv')
    csvwrite(OUT/'2026_RECORD_MARKS.csv',rec)
    month=read(OUT/'2026_SOURCE_MONTH_MARKS.csv')
    npmeta=read(PIN/'np9_2026_metadata.csv');hashes=Counter(r['body_sha256'] for r in npmeta)
    repeats=Counter((r['source_id'],r['publication_date'][:7]) for r in npmeta if hashes[r['body_sha256']]>1)
    for row in month:
        n=repeats[row['source_id'],row['month']] if row['stream']=='newspaper' else 0
        row['recorded_exact_hash_candidate_IDs']=n
        if n:
            row['reason_codes']+=';EXACT_BODY_REPEAT_WORK_CANDIDATES'
            row['recommended_next_action']='link_alias_candidate'
            row['evidence_status']='supported_candidate'
    (OUT/'2026_SOURCE_MONTH_MARKS.csv').rename(baseline/'2026_SOURCE_MONTH_MARKS.csv')
    csvwrite(OUT/'2026_SOURCE_MONTH_MARKS.csv',month)
    # Preserve exact snapshot semantics and expose an explicit schema/codebook.
    limits={'review_completed_at_utc':datetime.now(timezone.utc).isoformat(),
            'publication_interval':['1988-01-01','2026-09-21'],'september_partial':True,
            'snapshot_times_utc':diag['snapshots'],
            'snapshot_time_semantics':{'np9_closed':'delivery at_utc; not a publication or retrieval time',
                                       's9_closed':'closed export snapshot_at_utc',
                                       's4_closed_pre_resume':'closed early capacity-stop export snapshot_at_utc'},
            'cross_source_timezone_harmonization_validated':False,
            'snapshots_not_simultaneous':True,'append_after_s4_closed_snapshot_reviewed':False,
            'newspaper_current_live_store_reviewed':False,'sealed_prior_evaluator_accessed':False,
            'all_2026_contributing_source_parents_researched':14,'parent_dimensions_per_source':7,
            'parent_assertion_rows':98,'publisher_operator_platform_software_instance_community_not_interchangeable':True,
            'source_month_aggregate_rows':len(month),'newspaper_2026_metadata_IDs_checked':837,
            'newspaper_named_native_records_checked':named['records_checked'],
            'newspaper_named_saved_batches_read':named['saved_batches_read'],
            'social_native_endpoint_metadata_records_checked':24,
            'social_sample_within_study_day_interval':17,'social_sample_after_fixed_cutoff':7,
            'social_sample_is_qualified_body_sample':False,'social_native_original_bodies_checked':0,
            'named_source_primary_metadata_reads':parent['named_reads'],
            'named_primary_source_compressed_input_bytes':parent['compressed_input_bytes'],
            'named_newspaper_raw_compressed_input_bytes':named['compressed_input_bytes'],
            'database_reads':0,'full_raw_body_tree_scans':0,'corpus_writes':0,'collector_modifications':0,
            'source_quality':'source-native route; current operator evidence; record-level quotation/reproduction and historical validity often unresolved; no opaque score',
            'sampling':'purposeful source endpoints, July newspaper endpoints and three already named hash pairs; not random; no prevalence extrapolation',
            'unreviewed':['all other native newspaper bodies; all native social bodies','social ID/date/URL outside 24 metadata endpoints',
                          'whole-social-work/cross-instance/repost duplication','historical corporate/ownership continuity',
                          'all child-community membership inventories','archive-native denominator/completeness',
                          'natural-event attribution','semantic climate/emotion/fear content','later resume/append and newspaper new closeout'],
            'inherited_non2026_date_limits':{'count':9,'independent_new_record_verification':False,
                                            'evidence':'worker/pinned/s9_native_date_mapping_limits.csv and s4_named_date.json',
                                            '2026_count_correction_from_these_issues':0},
            'reason_status_semantics':{'confirmed':'stated bounded descriptive check/assertion supported, not blanket record validity',
                                      'supported_candidate':'diagnostic/work/mapping candidate needing evidence before repair',
                                      'unresolved':'not decided or source access/evidence insufficient'},
            'actions_are_advisory':True,'deletion_or_replacement_authorized_or_executed':False,
            'future_exclusion_or_replacement_candidates_confirmed':0,
            'retain_with_context_semantics':'retain observation and diagnostic context; no event cause implied',
            'adjacent_rule':'same-source count / mean of available +/-3 study months; ratio>=3 is an advisory flag only; missing future context explicit; zero observations not inferred zero expression',
            'no_composite_quality_score':True,'no_metrics_as_acquisition_controls':True,
            'latest_annual_share_and_mechanism_clarification':{'annual_share_enters_comparison_sensitivity':True,
                         'native_summary_checks':'NATIVE_MECHANISM_REVIEW.csv and NATIVE_MECHANISM_LIMITS.json',
                         'bot_automation_markers':'unknown; fields not present in pinned schemas',
                         '2026_specific_thread_degree_or_federation_work_join_reviewed':False,
                         'native_type_summaries_are_semantic_noise_labels':False},
            'physical_floor_bytes':16106127360,'recovery_allowance_bytes':50331648,
            'physical_free_at_pin_bytes':original['physical_free_before_bytes'],
            'shared_cap_bytes':30000000000,
            'accounting':'All package30 local/final/interim/evidence/code bytes remain charged inside shared media accounting. Existing counters/leases untouched. Output byte inventory supplied for coordinator settlement; no new allocation or simultaneous live cumulative-usage claim.'}
    with (OUT/'REVIEW_LIMITS.json').open('x') as f:f.write(json.dumps(limits,indent=2)+'\n')
    # Reuse accepted frozen report/collector checks while validating our own metadata relations.
    expected=json.loads((PIN/'p29_input_manifest.json').read_text())
    checked=[]
    for r in original['input_files']:
        if r['path'] in expected:
            assert r['sha256']==expected[r['path']]
            checked.append(r['path'])
    delivery_checks=[]
    for label,fragment in [('s9','/20261009_nine_hour_social/worker/'),('s4','/20261010_four_hour_historical_repair/worker/')]:
        manifest=json.loads((PIN/(label+'_delivery_file_manifest.json')).read_text())
        expected_files={r['path']:r['sha256'] for r in manifest['files']}
        for item in original['input_files']:
            if fragment not in item['path']:continue
            relative=item['path'].split(fragment,1)[1]
            if relative in expected_files:
                assert item['sha256']==expected_files[relative],item
                delivery_checks.append(item['path'])
    assert len(month)==234 and len(rec)==861 and len(checks)==12
    assert all(r['invalidity_confirmed']=='False' for r in rec)
    assert sum(r['native_original_body_read'] is True for r in rec)==12
    assertions=read(OUT/'PARENT_SOURCE_EVIDENCE.csv')
    assert len(assertions)==98 and len({r['source_id'] for r in assertions})==14
    verification={'input_hashes_matching_frozen_package29_manifest':checked,'record_mark_rows':len(rec),
                  'input_hashes_matching_closed_social_delivery_manifests':delivery_checks,
                  'source_month_mark_rows':len(month),'parent_dimension_rows':len(assertions),
                  'named_native_checks_passed':12,'metadata_numbers_reconciled':True,
                  'corpus_invalidity_or_deletion_claims':0,'checks_passed':True}
    with (OUT/'VERIFICATION.json').open('x') as f:f.write(json.dumps(verification,indent=2)+'\n')
    print(json.dumps({'limits':limits,'verification':verification},indent=2))

if __name__=='__main__':main()
