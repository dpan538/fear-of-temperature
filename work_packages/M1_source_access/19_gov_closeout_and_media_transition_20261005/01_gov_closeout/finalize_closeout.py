"""Freeze this window's usable input and explicit gaps; never self-release HTTP."""
import csv
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];WP=ROOT/'work_packages/M1_source_access'
B=WP/'18_bounded_supplementation_execution_20261005/02_eu_staging'
A=WP/'18_bounded_supplementation_execution_20261005/01_downloader_and_originals'
P=WP/'15_targeted_repairs_and_supplementation_20261004'
INTERVAL=['1988-01-01','2026-09-21']


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def read(p):
    with Path(p).open() as f:return list(csv.DictReader(f))


def save(name,x): (HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')


def gaps():
    rows=[]
    def row(id,source,count,unit,evidence,need,status,action):
        rows.append({'gap_id':id,'source_frame':source,'affected_count':count,'count_unit':unit,
            'evidence_path':evidence,'unresolved_need':need,'status':status,'bounded_next_action':action,
            'progression_gate':'not a universal source-acquisition or media-transition gate',
            'semantic_exclusion_authorized':False})
    for r in read(A/'A_DISPOSITIONS.csv'):
        hansard=r['unit_id'].startswith('doc_')
        row('A:'+r['unit_id'],r['source_id'],1,'existing parent requiring original evidence',r['evidence_path'],
            'section/contribution/statement identity original' if hansard else 'primary file, issue date, author/host/legal publisher/issuer',
            'one route HTTP403' if r['actually_attempted']=='true' else 'unattempted after inherited A stop',
            'no Hansard request without new feasible-route evidence' if hansard else 'two named AU landing/PDF checks in merged new coordinator release')
    base=str(B.relative_to(ROOT))
    row('B:HTTP406','EU COM frozen2015',1,'selected Item',base+'/requests/857251ccc1e5593056fbf490ff87c569d31eb81d8b68aa151af03c8a544ecc4f.json',
        'exact stream transport; generic Accept constraint is candidate cause, not proven', 'persistent historical B stop',
        'one same-Item wildcard Accept validation only after new release; failure stops new B phase')
    row('B:UNATTEMPTED','EU COM frozen2015',958,'selected Items, one selected target per Work',base+'/B_REMAINING_TARGETS.csv',
        'saved original bytes absent', 'not attempted after406', 'same original queue only if one corrected validation succeeds; no replacements')
    row('B:NO_LINK','EU COM frozen2015',30,'enumerated Works',base+'/B_NO_LINK_WORKS.csv',
        'no English digital Item in saved relation frame', 'no-link source outcome', 'retain; no sibling/class/format expansion in this bundle')
    row('B:PRINTED_DAY_CONFLICT','EU COM selected changed Items',1,'selected Item (sequence17)', 'CHANGED_ITEM_IDENTITY_DATE.csv',
        'CDM2015-01-30 versus OJ2015-01-31; same month, day mapping unresolved', 'derived conflict annotation; raw and CDM day unchanged',
        'coordinator reviews identity/reference/date purpose before any date correction; no automatic rebin')
    row('B:MULTI_NOTICE','EU COM selected changed Items',4,'Items with at least two first-page notices', 'CHANGED_ITEM_IDENTITY_DATE.csv',
        'selected Work text boundary may share physical rendition with another notice', 'structural segmentation pending',
        'saved first-page reference mapping; do not split pages into parents or use entire PDF as Work length')
    row('B:SELECTED_MANIFESTATION_MULTIPLE_ITEMS','EU COM selected changed Items',6,'selected Manifestations with multiple saved relation Items', 'CHANGED_ITEM_TEXT_SHAPE.csv',
        'component roles/required annexes unknown; only one Item observed per Work', 'not complete Work acceptance',
        'inspect saved relation and content-boundary evidence; no all-sibling acquisition authorized')
    row('B:VERSION_AND_COMPLETENESS','EU COM selected changed Items',20,'saved Item versions', 'CHANGED_ITEM_TEXT_SHAPE.csv',
        'later HTTP version is not original historical wording; full Work and all-page visual readability unestablished',
        'text layer and first pages checked, raw preserved', 'keep passage/Item scope, edition/version metadata and completeness pending')
    row('UK:INTERVALS_AND_ADAPTERS','UK effective parents','124;51;37','interval parents; cross-month subset; separate HTML adapter limits',
        'work_packages/M1_source_access/16_post_repair_analysis_20261004/CHECKED_STATE.json',
        'exact days absent for124;51 cross-month unassigned;37 adapter limits;119 local/UTC convention differences',
        'accepted named limitations', 'retain separate buckets; no universal pass or repeated full repair')
    row('UK:MIRRORS_SHARED_REPLIES','UK source routes','unknown','cross-source independent utterance denominator',
        'work_packages/M1_source_access/16_post_repair_analysis_20261004/uk_effective_source_genre.csv',
        'mirror/route overlap and shared reply text; UK09 historical copy not additive', 'source-specific inventory available',
        'independent reviewer uses official/mirror sensitivity; no automatic deletion')
    row('US:HISTORICAL_FRAME','US EPA/DOE 1988-1993','unknown','independent rules/Works',
        'work_packages/M1_source_access/09_us_au_government_acquisition/reports/acquisition_progress_snapshot.md',
        'index tokens4,844/pages4,385/issue dates1,325 are finding aids; six bounded article samples not population denominator',
        'official historical evidence available, denominator unknown', 'no bulk issue downloads; bounded article enumeration only for a named later window')
    row('US:BODY_DEPTH','US EPA/DOE 1994..cutoff','33,544 metadata;18,590 status','parents vs operational extraction/status/version checkpoint',
        'work_packages/M1_source_access/13_parallel_data_audit_20261004/02_distribution/RESULT.json',
        'incomplete body acquisition and readable historical-version acceptance', 'saved source checkpoint retained',
        'no restart here; use saved availability, not a new coverage denominator')
    row('AU:DATE_AND_HOST','AU catalogue','821;819;7','catalogue candidates; missing main-table day; overlapping originals',
        'work_packages/M1_source_access/16_post_repair_analysis_20261004/CURRENT_STATE.md',
        'current host/CMS time not historical issuer or issue day; five month/day originals and two year-only',
        'source/date/rights precision separated', 'two named originals only; keep other unknowns; no CMS cutoff exclusion')
    row('IE:NATIVE_UNIT','IE all-department written index',684809,'summed question index counts across171partitions',
        'inputs/IE_WRITTEN_QUESTION_MONTH_INDEX.csv', 'index is not independent ministerial answer count;2012-09 shared answers',
        '171 bounded query receipts available', 'retain query zeros and independent-answer uncertainty; no wholesale harvesting')
    row('NZ:NATIVE_UNIT','NZ saved2025portfolio index',536,'displayed currently-answered question records',
        'inputs/NZ_2025_PORTFOLIO_QUESTION_MONTH_INDEX.csv', 'answer received dates, historic status and independent response units unknown',
        '12positive savedUI bins', 'retain original portfolio frame; no topic-based new exclusion')
    row('ENTRANCES:UNENUMERATED','AU Parliament / IE government / NZ MfE-Beehive / EU EP','unknown','entrance observations',
        'GOV_FRAME_REGISTER.csv', 'no comparable historical population denominator; named access challenges',
        'routes and access states retained', 'progress with usable pooled evidence; no exhaustive-country prerequisite')
    row('INPUT:PARENT_LENGTH_ORGMAP','all government frames','unknown','qualified parent-length / department map rows',
        'BOUNDED_PARENT_EXPORT_REQUEST.json', 'saved aggregates omit per-parent complete-text length and verified institution crosswalk',
        '20 Item text-shape rows available, zero certified parent-length rows', 'optional ONE2015source×date export from accepted stored views; no full raw/text rescan')
    with (HERE/'CURRENT_GAPS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return rows


def main():
    timestamp=datetime.now(timezone.utc).isoformat(); gap_rows=gaps()
    check=json.loads((HERE/'CHANGED_ITEM_CHECK.json').read_text())
    ledger=read(B/'B_STATUS_LEDGER.csv');frame=read(HERE/'GOV_FRAME_REGISTER.csv');shape=read(HERE/'CHANGED_ITEM_TEXT_SHAPE.csv')
    assert len(ledger)==979 and len(shape)==20 and len(frame)==23
    assert sum(r['status']=='downloaded_candidate_original' for r in ledger)==20
    assert sum(r['status']=='failed' for r in ledger)==1
    assert sum(r['status']=='not_attempted_after_stop' for r in ledger)==958
    assert check['all_raw_hashes_match'] and check['raw_bytes_rechecked']==9020646 and check['pages']==135
    assert sum(r['issue_date_comparison']=='conflict_one_day_same_month' for r in shape)==1
    assert all(r['parent_statistics_eligible']=='False' for r in shape)
    assert 'Ran 16 tests' in (HERE/'TRANSPORT_TESTS.log').read_text() and (HERE/'TRANSPORT_TESTS.log').read_text().strip().endswith('OK')
    incoming=[
      (P/'04_targeted_supplementation/stage_frozen_items.py','acceptedV3 preserved'),
      (P/'04_targeted_supplementation/frozen_acquisition_manifest.csv','frozen979targets, no changes'),
      (P/'04_targeted_supplementation/selected_work_item_relationships.csv','WEMI relation and selected component accounting'),
      (P/'04_targeted_supplementation/ACQUISITION_CONTRACT.json','original caps/source frame'),
      (P/'03_existing_data_repair/missing_original_requests.csv','final five original requests'),
      (P/'control/REPAIR_READY.json','old committed repair release, not modified'),
      (B.parent/'control/EU_STAGING_RELEASE.json','old signed B release, not modified'),
      (B/'EXECUTION_RESULT.json','original stopped run, known downloads_started reporting defect retained'),
      (B/'RESULT.json','derived actual run result'),(B/'PHASE_HTTP_STATE.json','old406persistent stop'),
      (B/'STAGING_INGESTION_HANDOFF.csv','20raw provenance/checkpoint inputs'),(B/'B_STATUS_LEDGER.csv','full979status ledger'),
      (B/'B_REMAINING_TARGETS.csv','959remaining'),(B/'B_NO_LINK_WORKS.csv','30no-link within1009Workpopulation'),
      (A/'SHARED_HTTP_STATE.json','oldHansard403persistent stop'),(A/'A_DISPOSITIONS.csv','A5dispositions'),
      (A/'A_ACCOUNTING.json','prior A raw0 terminal accounting'),
      (WP/'09_us_au_government_acquisition/reports/au_attachment_candidates.csv','previous link candidates, not fetched originals'),
      (WP/'09_us_au_government_acquisition/reports/au_candidate_outcomes.csv','prior catalogue/source-date outcomes'),
      (WP/'13_parallel_data_audit_20261004/02_distribution/RESULT.json','prior non-synchronous source checkpoint facts only'),
      (WP/'13_parallel_data_audit_20261004/02_distribution/monthly_source_genre_counts.csv','saved old monthly source data only; no evaluator code'),
      (WP/'16_post_repair_analysis_20261004/CHECKED_STATE.json','accepted UK effective checkpoint'),
      (WP/'16_post_repair_analysis_20261004/uk_effective_month_source_genre.csv','UK latest effective aggregates'),
      (WP/'16_post_repair_analysis_20261004/uk_effective_source_genre.csv','UK current11source/genre totals'),
      (WP/'08_cross_region_government_coverage/reports/source_register.csv','historical route frame register, annotations supersede stale EU entrance row'),
      (WP/'08_cross_region_government_coverage/ie_written_question_month_index.csv','IE171question index receipts'),
      (WP/'08_cross_region_government_coverage/nz_parliament_climate_answered_2025_month_index.csv','NZ12UIquestion index receipts'),
      (ROOT/'docs/research/2026-09-26-ie-eu-nz-source-sufficiency-review.md','saved bounded source/answer-unit evidence')]
    evidence=[]
    for path,purpose in incoming:
        evidence.append({'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path),'purpose':purpose})
    for path in sorted((HERE/'inputs').glob('*.csv')):
        evidence.append({'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path),'purpose':'frozen reviewer input; native units and old availability caveats in frame register'})
    for name in ['CHANGED_ITEM_TEXT_SHAPE.csv','CHANGED_ITEM_IDENTITY_DATE.csv','PDF_PAGE_SHAPE.csv','CHANGED_ITEM_CHECK.json',
                 'AU_ORIGINAL_CHECK_PLAN.csv','GOV_FRAME_REGISTER.csv','CURRENT_GAPS.csv','BOUNDED_PARENT_EXPORT_REQUEST.json',
                 'transport_continuation.py','test_transport_continuation.py','TRANSPORT_TESTS.log','TRANSPORT_DIAGNOSIS_zh.md',
                 'evidence/FIRST_PAGE_IDENTITY.json','evidence/FIRST_PAGES_01.png','evidence/FIRST_PAGES_02.png']:
        path=HERE/name;evidence.append({'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path),'purpose':'this window derived evidence / offline tested candidate'})
    sidecars=[]
    for r in ledger[:21]:
        p=ROOT/r['checkpoint_path'];sidecars.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
    prior=json.loads((WP/'13_parallel_data_audit_20261004/02_distribution/RESULT.json').read_text())
    dbs=[]
    for key,old in prior['input_checkpoint'].items():
        p=ROOT/old['path'];st=p.stat()
        dbs.append({'source':key,'path':old['path'],'prior_snapshot':old,
                    'current_file_stat_only':{'bytes':st.st_size,'mtime_ns':st.st_mtime_ns},
                    'sha256':'not computed; no whole-database hash/read','current_database_queried':False})
    save('INPUT_MANIFEST.json',{'frozen_at_utc':timestamp,'fixed_publication_interval':INTERVAL,'partial_month':'2026-09',
      'input_status':'usable source-specific frozen input; no synchronized pooled independent-parent total',
      'source_snapshots_not_synchronous':True,'evidence_files':evidence,'staging_request_sidecars':sidecars,
      'changed_raw_files':[{'path':r['raw_path'],'bytes':int(r['raw_bytes']),'sha256':r['raw_sha256_rechecked'],
                            'verified_once_at_utc':check['checked_at_utc'],'unit':'saved selected Item version'} for r in shape],
      'database_checkpoints':dbs,'current_UK_effective_checkpoint':json.loads((WP/'16_post_repair_analysis_20261004/CHECKED_STATE.json').read_text()),
      'receipt_scope':'named evidence/data only; no sealed audit code or credentials located/read/probed',
      'current_run_network_source_requests':0,'current_run_database_queries':0,'current_run_database_writes':0,
      'historical_pooled_465_month_presence':'preserved prior checkpoint only, not recalculated'})
    budget=json.loads((P/'04_targeted_supplementation/ACQUISITION_CONTRACT.json').read_text())['budget']
    raw=9020646;free=shutil.disk_usage(HERE).free
    reserve=(budget['aggregate_new_raw_cap_bytes']-raw)+sum(budget[k] for k in ['inflight_object_reserve_bytes','checkpoint_error_reserve_bytes','repair_other_activity_reserve_bytes'])
    storage={'checked_at_utc':timestamp,'free_bytes':free,'old_A_B_raw_bytes':raw,'partial_bytes':0,
             'aggregate_government_raw_cap_bytes':2*2**30,'remaining_raw_cap_bytes':2*2**30-raw,
             'original_reserve_bytes_including_remaining_raw':reserve,'projected_free_bytes':free-reserve,
             'collector_floor_bytes':15*2**30,'gate_passes':free-reserve>15*2**30,
             'media128MiB':'inside original1GiBother reserve, not new allowance','shared_heavy_io_lock_preserved':True}
    save('GOV_CLOSEOUT_INPUT_READY.json',{'ready':True,'issuer':'Task4 source/input owner; not coordinator HTTP release',
      'status':'usable_input_frozen_with_named_gaps_and_offline_continuation_candidate',
      'frozen_at_utc':timestamp,'fixed_publication_interval':INTERVAL,'input_manifest_sha256':sha(HERE/'INPUT_MANIFEST.json'),
      'frame_rows':23,'changed_Item_rows':20,'changed_pdf_pages':135,'raw_bytes':9020646,
      'changed_raw_verified_once':True,'all_pages_have_nonempty_text_layers':True,
      'first_pages_visually_checked':20,'all_pages_visually_checked':False,
      'printed_issue_day_conflicts':1,'full_Work_verified_count':'not established','parent_length_rows_certified':0,
      'new_body_count_must_not_be_added_to_old_complete_Work_count':True,
      'old_B_terminal_for_this_run':True,'frozen_queue_complete':False,
      'remaining_B':{'failed406':1,'unattempted':958,'no_link_outside979_targets':30},
      'A_originals_obtained':0,'source_frame_statistics_not_pooled_independent_total':True,
      'independent_review_input_ready':True,'independent_audit_executed_here':False,
      'continuation_requires_one_new_coordinator_acceptance':True,'new_continuation_HTTP_executed':False,
      'transport_candidate_root_cause_proven':False,'transport_candidate_network_fixture_tests':16,
      'storage':storage,'formal_database_writes':0,'proposal_edits':0,'semantic_labelling_or_exclusion':False,
      'PROJECT_LOG_directly_edited':False,'other_chats_messaged':False})
    spec=importlib.util.spec_from_file_location('continuation',HERE/'transport_continuation.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    ready={'ready':True,'status':'offline_candidate_ready_for_one_merged_coordinator_review','version':mod.VERSION,
           'code_path':str((HERE/'transport_continuation.py').relative_to(ROOT)),'code_sha256':sha(HERE/'transport_continuation.py'),
           'accepted_v3_path':str(mod.V3.relative_to(ROOT)),'accepted_v3_sha256':mod.V3_SHA,
           'root_cause_status':'generic Accept constraint candidate; official direct-Item wildcard route supported; live causality unproven',
           'diagnosis_path':'TRANSPORT_DIAGNOSIS_zh.md','test_command':'.venv/bin/python '+str((HERE/'test_transport_continuation.py').relative_to(ROOT)),
           'test_count':16,'test_status':'passed with socket connect forbidden; no real HTTP',
           'test_log_sha256':sha(HERE/'TRANSPORT_TESTS.log'),'new_release_created_by_this_window':False,
           'same_Item_validation_bound':1,'queue_continuation_after_corrected_success_only':True,
           'AU_plan':'AU_ORIGINAL_CHECK_PLAN.csv','old_stops_and_releases_preserved':True,
           'new_phase_stops_and_partials_persist':True,'storage':storage,'formal_database_writes':False}
    save('TRANSPORT_PATCH_READY.json',ready)
    repair=json.loads((P/'control/REPAIR_READY.json').read_text())
    save('CONTINUATION_RELEASE_TEMPLATE.json',{'ready':False,'issuer':'coordinator must review and sign; template only',
          'status':'template_not_authorization','authorized_phases':['B_CORRECTED','AU_ORIGINALS'],
          'post_checkpoint':repair['post_checkpoint'],**mod.expected_bindings()})
    save('RESULT.json',{'status':'input_owner_delivery_complete_with_explicit_acquisition_gaps',
      'finished_at_utc':timestamp,'fixed_publication_interval':INTERVAL,
      'usable_input_ready':True,'government_acquisition_complete':False,'independent_audit_pending':True,
      'changed_tranche':check,'frame_rows':23,'gap_rows':len(gap_rows),'candidate_transport_ready_offline':True,
      'continuation_HTTP_attempts':0,'A_new_originals':0,'B_new_downloads_this_closeout':0,
      'B_retained_from_previous_run':20,'remaining_B':{'failed':1,'unattempted':958},
      'AU_new_plan_targets':2,'new_source_requests':0,'official_documentation_review':'web-reader only; not source Item/AU body requests',
      'formal_database_reads':0,'formal_database_writes':0,'sealed_evaluator_access':False,
      'pooled_coverage_refreshed':False,'semantic_labelling_or_exclusion':False,'storage':storage,
      'one_coordinator_decision':'accept usable frozen input and either release bundled one406/AU continuation or retain named transport/access gaps',
      'handoff_path':'HANDOFF_zh.md','log_entry_path':'LOG_ENTRY.md'})
    print(json.dumps({'status':'usable_input_ready','frames':23,'changed_items':20,'gap_rows':len(gap_rows),
                      'offline_transport_tests':16,'new_http':0,'storage_gate_passes':storage['gate_passes']}))


if __name__=='__main__':main()
