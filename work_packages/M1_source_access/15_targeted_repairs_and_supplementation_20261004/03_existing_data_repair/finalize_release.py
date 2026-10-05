#!/usr/bin/env python3
"""Atomic release of the verified committed checkpoint, not a staged plan."""
import json
import shutil
import duckdb
import repair_cli as r

def main():
    required=['REPORT.md','SUMMARY_zh.md','RESULT.json','INPUT_MANIFEST.json','LOG_ENTRY.md','APPLIED.json','ACCEPTANCE.json','FINAL_SAVED_TRANCHE_CHECKS.json','TEST_RESULTS.json','IDEMPOTENCY.json','EU_CURRENT_STATE_ADDENDUM.json','REQUEST_RECONCILIATION.json','missing_original_requests.csv','source_composition_needs.csv']
    for f in required:
        if not (r.HERE/f).is_file():raise RuntimeError('Missing required deliverable: '+f)
    applied=json.loads((r.HERE/'APPLIED.json').read_text());plan=json.loads((r.HERE/'PLAN.json').read_text());result=json.loads((r.HERE/'RESULT.json').read_text());checks=json.loads((r.HERE/'FINAL_SAVED_TRANCHE_CHECKS.json').read_text());tests=json.loads((r.HERE/'TEST_RESULTS.json').read_text())
    if applied['status']!='applied_and_checked' or applied['acceptance']['status']!='passed':raise RuntimeError('No verified committed checkpoint')
    if len(plan['dispositions'])!=3080 or checks['unexpected_conflicts'] or tests['status']!='passed':raise RuntimeError('Incomplete issue/check accounting')
    if checks['final_plan_sha256']!=applied['plan_sha256'] or r.digest((r.HERE/'PLAN.json').read_bytes())!=applied['plan_sha256']:raise RuntimeError('Frozen manifest mismatch')
    with r.locks(writer=True):
        r.writer_preflight()
        if r.stamp(r.DB)!=applied['post_checkpoint']:raise RuntimeError('Committed database checkpoint moved before release')
        for prior in plan['checkpoints'][1:]:
            if r.stamp(r.ROOT/prior['path'])!=prior:raise RuntimeError('Companion database unexpectedly changed')
        con=duckdb.connect(str(r.DB),read_only=True)
        try:
            active=con.execute('SELECT active,plan_sha256 FROM repair_runs WHERE run_id=?',[r.RUN]).fetchone()
            current_addenda=con.execute('SELECT count(*) FROM repair_current_source_state_addenda WHERE run_id=?',[r.RUN]).fetchone()[0]
        finally:con.close()
        if active!=(True,applied['plan_sha256']):raise RuntimeError('Repair run not active at release')
        if current_addenda!=1:raise RuntimeError('Checked named current-state addendum missing')
        marker={'ready':True,'status':'committed_repairs_checked_targeted_acquisition_released','released_at_utc':r.now(),'run_id':r.RUN,'rule_version':r.RULE,'fixed_publication_interval':plan['fixed_interval'],'pre_checkpoint':applied['pre_checkpoint'],'post_checkpoint':applied['post_checkpoint'],'pre_legacy_counts':plan['pre_counts'],'post_legacy_counts':plan['pre_counts'],'post_effective_parent_count':248319,'counts':{k:len(plan[k]) for k in ['repairs','dates','states','new_parents','annotations','dispositions','requests']},'unresolved_issue_rows':318,'unresolved_distinct_units':165,'named_frozen_adapter_limit_parent_checks':37,'fixture_tests_passed':tests['tests_run'],'acceptance_path':str((r.HERE/'ACCEPTANCE.json').relative_to(r.ROOT)),'result_path':str((r.HERE/'RESULT.json').relative_to(r.ROOT)),'change_manifest_path':str((r.HERE/'CHANGE_MANIFEST.json').relative_to(r.ROOT)),'missing_original_requests_path':str((r.HERE/'missing_original_requests.csv').relative_to(r.ROOT)),'source_composition_needs_path':str((r.HERE/'source_composition_needs.csv').relative_to(r.ROOT)),'unresolved_cases_path':str((r.HERE/'unresolved_cases.csv').relative_to(r.ROOT)),'plan_sha256':applied['plan_sha256'],'free_bytes_at_release':shutil.disk_usage(r.ROOT).free,'collector_floor_bytes':15*1024**3,'authority':str(r.DB.relative_to(r.ROOT)),'consumer_interface':['repair_current_documents','repair_current_parent_segments','repair_current_document_content_objects','repair_current_provenance_annotations'],'compatibility':'Legacy tables are frozen extraction history. The committed effective views include all repairs and 284 newly derived parent identities. Do not ingest an already represented identity by checking documents alone; use repair_parent_inventory. Copied UK09 tables are not an additional corpus.','task4_conditions':'Only the predeclared targeted manifest and storage checks are released. Task4 stages separately; it cannot write formal databases. No original ZIP redownload, blanket uncheckable-row queue, endpoint extension or semantic filtering.'}
        marker['counts']['requests']=len(r.csvread(r.HERE/'missing_original_requests.csv'))
        marker['counts']['source_state_addenda']=1
        marker['last_formal_write_at_utc']=applied['last_formal_write_at_utc']
        marker['request_reconciliation_path']=str((r.HERE/'REQUEST_RECONCILIATION.json').relative_to(r.ROOT))
        marker['consumer_interface'].append('repair_current_source_state_addenda')
        if marker['free_bytes_at_release']<marker['collector_floor_bytes']:raise RuntimeError('Storage below original acquisition floor')
        r.atomic(r.STAGE/'control/REPAIR_READY.json',marker)
        result.update(status='complete_with_named_unresolved_cases',repair_ready=True,release_marker=str((r.STAGE/'control/REPAIR_READY.json').relative_to(r.ROOT)),released_at_utc=marker['released_at_utc'],free_gib_at_release=round(marker['free_bytes_at_release']/1024**3,3))
        r.atomic(r.HERE/'RESULT.json',result)
    print(r.dump({'ready':True,'released_at_utc':marker['released_at_utc'],'free_gib':round(marker['free_bytes_at_release']/1024**3,3),'marker':str(r.STAGE/'control/REPAIR_READY.json')}))
if __name__=='__main__':main()
