"""Freeze actual continuation outcomes; no raw reread, HTTP or formal DB query."""
import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent;OWNER=HERE.parent;ROOT=OWNER.parents[3];WP=ROOT/'work_packages/M1_source_access'
OLD_B=WP/'18_bounded_supplementation_execution_20261005/02_eu_staging'
OLD_A=OLD_B.parent/'01_downloader_and_originals'
CONTROL=OWNER.parent/'control'
RELEASE_SHA='56acd7de09d6116cc332ca82637158dcfc8e6f53a0dca74a1cac9e9c5e1442b9'
CODE_SHA='73e5bd472a98c690971638c88237ab73d30761143f587eab9e68090dfae4f47c'
INTERVAL=['1988-01-01','2026-09-21']


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def load(p):return json.loads(Path(p).read_text())


def read(p):
    with Path(p).open() as f:return list(csv.DictReader(f))


def csvout(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def save(name,obj):(HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')


def main():
    timestamp=datetime.now(timezone.utc).isoformat()
    assert sha(CONTROL/'GOV_CONTINUATION_RELEASE.json')==RELEASE_SHA and sha(OWNER/'transport_continuation.py')==CODE_SHA
    release=load(CONTROL/'GOV_CONTINUATION_RELEASE.json')
    assert release['fixed_publication_interval']==INTERVAL
    bindings={'input_manifest_sha256':OWNER/'INPUT_MANIFEST.json','input_ready_sha256':OWNER/'GOV_CLOSEOUT_INPUT_READY.json',
              'old_a_stop_sha256':OLD_A/'SHARED_HTTP_STATE.json','old_b_stop_sha256':OLD_B/'PHASE_HTTP_STATE.json',
              'old_eu_release_sha256':OLD_B.parent/'control/EU_STAGING_RELEASE.json',
              'old_b_result_sha256':OLD_B/'EXECUTION_RESULT.json'}
    assert all(sha(p)==release[k] for k,p in bindings.items())
    b=load(HERE/'B_CORRECTED/RESULT.json');au=load(HERE/'AU_ORIGINALS/RESULT.json');new_check=load(HERE/'CHANGED_ITEM_CHECK.json')
    old_shapes=read(OWNER/'CHANGED_ITEM_TEXT_SHAPE.csv');new_shapes=read(HERE/'CHANGED_ITEM_TEXT_SHAPE.csv')
    assert len(old_shapes)==20 and len(new_shapes)==27 and new_check['new_raw_bytes_rechecked']==13210928
    shapes=[{**r,'tranche':'prior20','sequence_native':r['sequence']} for r in old_shapes]
    shapes += [{**r,'tranche':'continuation27','sequence_native':r['sequence_new']} for r in new_shapes]
    assert len({r['item_uri'] for r in shapes})==47 and sum(int(r['raw_bytes']) for r in shapes)==22231574
    assert all(r['parent_statistics_eligible']=='False' for r in shapes)
    csvout('ALL_SAVED_ITEM_TEXT_SHAPE.csv',shapes)
    old_ledger={r['item_uri']:r for r in read(OLD_B/'B_STATUS_LEDGER.csv')};final=[]
    for r in b['outcomes']:
        prior=old_ledger[r['item_uri']]
        cp=(HERE/'B_CORRECTED/requests'/f"{hashlib.sha256(r['request_url'].encode()).hexdigest()}.json")
        if r['status']=='verified_local_reuse':cp=ROOT/prior['checkpoint_path']
        request=load(cp) if cp.exists() else {}
        raw_path=r.get('raw_path','')
        if raw_path and Path(raw_path).is_absolute():raw_path=str(Path(raw_path).relative_to(ROOT))
        final.append({'parent_id':r['parent_id'],'expression_uri':r['expression_uri'],'manifestation_uri':r['manifestation_uri'],
          'item_uri':r['item_uri'],'publication_dates':r['publication_dates'],'publication_month':r['publication_dates'][:7],
          'request_url':r['request_url'],'format':r['format'],'latest_status':r['status'],
          'prior_B_status':prior['status'],'prior_checkpoint_path':prior.get('checkpoint_path',''),
          'continuation_HTTP_attempted':r['status'] in {'downloaded_candidate_original','failed'},
          'latest_http_status':request.get('http_status',''),'latest_request_accept':request.get('request_headers',{}).get('Accept',''),
          'latest_checkpoint_path':str(cp.relative_to(ROOT)) if cp.exists() else '',
          'latest_checkpoint_sha256':sha(cp) if cp.exists() else '',
          'raw_path':raw_path,'raw_sha256':r.get('sha256',''),'raw_bytes':r.get('byte_count',0),
          'latest_error':request.get('error',r.get('error','')),
          'body_check':'prior20accepted Item-level check' if r['status']=='verified_local_reuse' else
                       ('continuation27Item-level check' if r['status']=='downloaded_candidate_original' else 'no new readable original obtained'),
          'complete_Work':'not established','new_parent_created':False,'formal_ingestion_performed':False,
          'automatic_retry_authorized':False})
    counts=Counter(r['latest_status'] for r in final)
    assert len(final)==979 and counts=={'verified_local_reuse':20,'downloaded_candidate_original':27,'failed':1,'not_attempted_after_stop':931}
    csvout('FINAL_B_STATUS_LEDGER.csv',final);csvout('FINAL_B_REMAINING_TARGETS.csv',[r for r in final if r['latest_status'] in {'failed','not_attempted_after_stop'}])
    bymonth=defaultdict(Counter)
    for r in final:bymonth[r['publication_month']][r['latest_status']]+=1
    coverage=[]
    for r in read(OLD_B/'B_COVERAGE_EXPECTED_VS_OBSERVED.csv'):
        c=bymonth[r['month']]
        coverage.append({'month':r['month'],'enumerated_Works':r['enumerated_Works'],
          'frozen_selected_Item_targets':r['frozen_selected_Item_targets'],'no_link_Works':r['no_link_Works'],
          'prior_saved_Items_reused':c['verified_local_reuse'],'continuation_new_saved_Items':c['downloaded_candidate_original'],
          'total_saved_selected_Items':c['verified_local_reuse']+c['downloaded_candidate_original'],
          'current_failed':c['failed'],'current_unattempted':c['not_attempted_after_stop'],
          'new_selected_Item_text_layer_checked':c['verified_local_reuse']+c['downloaded_candidate_original'],
          'complete_Work_verification':'not established','scope':'frozen2015Workframe; Item presence/text layer not complete independent Work'})
    csvout('FINAL_B_MONTH_DISPOSITIONS.csv',coverage)
    au_cp=list((HERE/'AU_ORIGINALS/requests').glob('*.json'));au_by={load(p)['unit_id']:(p,load(p)) for p in au_cp}
    a=[]
    for r in read(OLD_A/'A_DISPOSITIONS.csv'):
        current=au_by.get(r['unit_id']);is_au=r['unit_id'].startswith('doc:')
        a.append({**r,'legacy_A_terminal_status':r['terminal_status'],'legacy_A_evidence_retained':True,
          'current_followup_status':'landing_read_timeout' if current else ('unattempted_after_AU_stop' if is_au else 'legacy_Hansard_stop_retained_no_request'),
          'continuation_requests':1 if current else 0,'continuation_http_status':current[1].get('http_status','') if current else '',
          'continuation_error':current[1].get('error','') if current else '',
          'continuation_checkpoint_path':str(current[0].relative_to(ROOT)) if current else '',
          'continuation_checkpoint_sha256':sha(current[0]) if current else '',
          'candidate_PDF_followup_status':'unattempted_after_landing_failure' if current else ('unattempted_after_AU_stop' if is_au else 'not applicable'),
          'new_original_obtained':False,'new_raw_bytes':0,'original_publication_date_final':'unknown for AU; Hansard baseline day retained, body mapping unresolved',
          'CMS_date_role':'not original issue date','author_legal_publisher_issuer_final':'unverified for two AU targets; host not author',
          'automatic_retry_authorized':False})
    csvout('FINAL_A_DISPOSITIONS.csv',a)
    gaps=read(OWNER/'CURRENT_GAPS.csv')
    for r in gaps:
        key=r['gap_id']
        if key=='B:HTTP406':
            r.update(affected_count=1,evidence_path=str((HERE/'B_CORRECTED/PHASE_HTTP_STATE.json').relative_to(ROOT)),
              unresolved_need='new Item818145b6... .0006.01/DOC_1 generic-PDF request returned406; prior failed Item3df58e03 recovered once',
              status='new persistentBstop; no second wildcard request authorized',bounded_next_action='retain stop; no new transport attempt in this closeout')
        elif key=='B:UNATTEMPTED':r.update(affected_count=931,evidence_path='FINAL_B_REMAINING_TARGETS.csv',status='unattempted after new406',bounded_next_action='retain named incomplete queue; no restart/replacement')
        elif key=='B:PRINTED_DAY_CONFLICT':r.update(affected_count=2,evidence_path='ALL_SAVED_ITEM_TEXT_SHAPE.csv',unresolved_need='oldcredit-rating and newCiliegiadiVignola:CDM2015-01-30 vs printed2015-01-31; same month')
        elif key=='B:MULTI_NOTICE':r.update(affected_count=7,count_unit='selected Items with multi-notice first pages; two byte-identical old/new pairs overlap',evidence_path='ALL_SAVED_ITEM_TEXT_SHAPE.csv')
        elif key=='B:SELECTED_MANIFESTATION_MULTIPLE_ITEMS':r.update(affected_count=10,evidence_path='ALL_SAVED_ITEM_TEXT_SHAPE.csv')
        elif key=='B:VERSION_AND_COMPLETENESS':r.update(affected_count=47,evidence_path='ALL_SAVED_ITEM_TEXT_SHAPE.csv',status='all selectedItemhash/textlayer/firstpage checks; fullWork/historicalversion unestablished')
        elif key.startswith('A:doc:7c7006'):r.update(status='newlandingReadTimeout90s; primaryPDFnotattempted',evidence_path='FINAL_A_DISPOSITIONS.csv',bounded_next_action='retain original-date/identity/author/publisher uncertainty; no automaticretry')
        elif key.startswith('A:doc:bc634'):r.update(status='unattempted after newAUstop',evidence_path='FINAL_A_DISPOSITIONS.csv',bounded_next_action='retain unknownavailability/date; noautomaticretry')
    gaps.append({'gap_id':'B:IDENTICAL_RENDITIONS','source_frame':'EU selected changedItems','affected_count':2,
       'count_unit':'cross-Work identical raw rendition groups,4Itemidentities','evidence_path':'CROSS_WORK_IDENTICAL_ITEM_GROUPS.csv',
       'unresolved_need':'shared physical rendition/notice ownership; different Work/Item identity does not prove distinct full text',
       'status':'identicalSHAobserved; preserved allraw/lineage','bounded_next_action':'saved reference/relationship review, no delete/downsample',
       'progression_gate':'not universal source-inclusion/media progression gate','semantic_exclusion_authorized':False})
    csvout('FINAL_CURRENT_GAPS.csv',gaps)
    frames=read(OWNER/'GOV_FRAME_REGISTER.csv')
    for r in frames:
        r.update(prior_frame_register_sha256=sha(OWNER/'GOV_FRAME_REGISTER.csv'),continuation_addition_scope='none for this frame')
        if r['source_id']=='EU_CELLAR_COM':
            r.update(continuation_addition_scope='27savedItemversions; prior20retained;47selectedItemcandidates,all2015-01;0formalnewparent',
              source_text_presence_level='old19,114Itemversions/19,085operationalstatesunchanged;47new-stagingselectedItemswithtextlayersun-ingested',
              verification_status='oldmetadata/WEMIretained;27newhash/signature/pages/textandfirstpagescheckedonce,20priorchecksreused',
              conflicting_or_pending='2printed-dayconflicts;7multi-noticefirstpageItems;10selectedManifestationsmultiItem;2identicalrenditiongroups;fullWorkpending',
              coverage_limits='2015selectedqueue47saved,1new406failed,931unattempted;30no-linkWorks;nohistoricalcoverageupdate',
              observed_at_or_checkpoint_utc=r['observed_at_or_checkpoint_utc']+'; continuationBstop2026-10-04T19:41:06.876623+00:00')
        if r['source_id']=='au_dcceew_current_catalogue_2026_snapshot':
            r.update(continuation_addition_scope='0neworiginals;firstAUlandingReadTimeout90s;secondAUunattempted',
                     conflicting_or_pending='twoissue-date/primary-filechecks unresolved;CMS2026-09-17/22notissue-dateproof')
    csvout('FINAL_GOV_FRAME_REGISTER.csv',frames)
    spec=importlib.util.spec_from_file_location('accepted',OWNER/'transport_continuation.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    contract=load(mod.OLD_HERE/'ACQUISITION_CONTRACT.json')
    with mod.locks():
        storage=mod.budget(contract,reserve_remaining=True)  # raw stat and disk only; not release/DB check
        assert storage['raw_bytes']==22231574 and storage['partial_bytes']==0
        st=(ROOT/release['post_checkpoint']['path']).stat()
        assert st.st_size==release['post_checkpoint']['bytes'] and st.st_mtime_ns==release['post_checkpoint']['mtime_ns']
    b_state=load(HERE/'B_CORRECTED/PHASE_HTTP_STATE.json');a_state=load(HERE/'AU_ORIGINALS/PHASE_HTTP_STATE.json')
    assert b_state['request_count']==28 and a_state['request_count']==1 and b_state['halted'] and a_state['halted']
    corrected=next(r for r in final if r['item_uri']==mod.FAILED_URI)
    assert corrected['latest_status']=='downloaded_candidate_original' and corrected['latest_request_accept']=='*/*'
    failure=next(r for r in final if r['latest_status']=='failed')
    assert failure['latest_http_status']==406 and failure['latest_request_accept']=='application/pdf'
    save('EXECUTION_RECEIPT.json',{'native_exec_session':94311,'native_process_exit_code':0,
      'command':'.venv/bin/python '+str((OWNER/'transport_continuation.py').relative_to(ROOT))+' --execute --release-sha256 '+RELEASE_SHA,
      'release_sha256':RELEASE_SHA,'code_sha256':CODE_SHA,'new_B_http_calls':28,'new_AU_http_calls':1,
      'corrected_old_failed_Item':corrected,'new_failed_Item':failure,
      'run_finished_at_utc':au['finished_at_utc'],'raw_accounting':{'prior_B_bytes':9020646,'new_B_bytes':13210928,'new_AU_bytes':0,'total_bytes':22231574,'partial_bytes':0},
      'old20_execution_reuse':'accepted runner rechecked hashes/signatures for reuse; no download or repeat text/visual audit',
      'database_read_scope':'accepted per-request targeted read-only repair_runs gate; no full corpus scan',
      'formal_database_writes':0,'production_extraction_started':False,'automatic_restarts':0,'approval_rejection':False})
    files=[CONTROL/'GOV_CONTINUATION_RELEASE.json',CONTROL/'GOV_CONTINUATION_ACCEPTANCE.json',OWNER/'transport_continuation.py',
      OWNER/'INPUT_MANIFEST.json',OWNER/'GOV_CLOSEOUT_INPUT_READY.json',OWNER/'GOV_FRAME_REGISTER.csv',OWNER/'CHANGED_ITEM_TEXT_SHAPE.csv',
      OWNER/'CHANGED_ITEM_CHECK.json',OWNER/'BOUNDED_PARENT_EXPORT_REQUEST.json',OLD_B/'PHASE_HTTP_STATE.json',OLD_A/'SHARED_HTTP_STATE.json',
      HERE/'B_CORRECTED/RESULT.json',HERE/'AU_ORIGINALS/RESULT.json',HERE/'B_CORRECTED/PHASE_HTTP_STATE.json',HERE/'AU_ORIGINALS/PHASE_HTTP_STATE.json']
    files+=list((OWNER/'inputs').glob('*.csv'))+list((HERE/'B_CORRECTED/requests').glob('*.json'))+au_cp
    files += [HERE/n for n in ['CHANGED_ITEM_CHECK.json','AUTOMATED_CHANGED_ITEM_CHECK.json','CHANGED_ITEM_TEXT_SHAPE.csv','ALL_SAVED_ITEM_TEXT_SHAPE.csv',
      'CHANGED_PDF_PAGE_SHAPE.csv','CHANGED_ITEM_IDENTITY_DATE.csv','CROSS_WORK_IDENTICAL_ITEM_GROUPS.csv','FINAL_B_STATUS_LEDGER.csv',
      'FINAL_B_REMAINING_TARGETS.csv','FINAL_B_MONTH_DISPOSITIONS.csv','FINAL_A_DISPOSITIONS.csv','FINAL_CURRENT_GAPS.csv',
      'FINAL_GOV_FRAME_REGISTER.csv','EXECUTION_RECEIPT.json','check_new_items.py','annotate_first_pages.py','finalize_inputs.py']]
    files+=list((HERE/'evidence').glob('*'))
    save('FINAL_INPUT_MANIFEST.json',{'frozen_at_utc':timestamp,'fixed_publication_interval':INTERVAL,'partial_month':'2026-09',
      'status':'usableinputfrozenafteroneauthorizedcombinedcontinuationstop','source_snapshots_not_synchronous':True,
      'accepted_release_sha256':RELEASE_SHA,'accepted_code_sha256':CODE_SHA,
      'evidence_files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],
      'raw_files':[{'parent_id':r['parent_id'],'item_uri':r['item_uri'],'path':r['raw_path'],'bytes':int(r['raw_bytes']),
                    'sha256':r['raw_sha256'],'tranche':r['tranche'],'verification_scope':'saved Item version; not complete Work'} for r in shapes],
      'old20check_reused_not_rerun':True,'new27rawchecked_once':True,'rawhash_not_reread_in_finalizer':True,
      'formal_database_checkpoint_stat_only':release['post_checkpoint'],'body_DB_query_or_write_in_finalizer':False,
      'independent_evaluator_or_credentials_accessed':False,'source_frame_counts_not_pooled_independent_total':True,
      'historical465monthpresence':'unchangedpriorcheckpoint,notrecalculated',
      'storage':storage})
    result={'status':'bounded_continuation_and_changed_input_delivery_complete_with_real_gaps','finished_at_utc':timestamp,
      'fixed_publication_interval':INTERVAL,'native_process_exit_code':0,'government_acquisition_complete':False,
      'B_frozen_selected_targets':979,'B_population_Works':1009,'B_no_link_Works':30,
      'prior_B_saved_Items':20,'continuation_B_new_saved_Items':27,'total_saved_selected_Items':47,
      'total_saved_selected_Work_IDs_with_Item_candidates':47,'complete_Work_count':'not established',
      'current_B_failed':1,'current_B_unattempted':931,'new_B_requests':28,'new_AU_requests':1,
      'AU_originals_obtained':0,'AU_first_status':'landingReadTimeout90s','AU_second_status':'unattemptedafterAUstop',
      'new_raw_bytes':13210928,'cumulative_government_raw_bytes':22231574,'partial_bytes':0,
      'new_pdf_pages':257,'prior_pdf_pages':135,'cumulative_pdf_pages':392,
      'printed_day_matches':45,'printed_day_conflicts':2,'all_observed_printed_dates_in2015January':True,
      'new_first_pages_inspected':27,'all_pdf_pages_visually_checked':False,
      'multi_notice_firstpage_Item_rows':7,'selected_manifestation_multiple_Item_rows':10,
      'distinct_raw_sha256':45,'cross_Work_identical_rendition_groups':2,
      'certified_parent_length_rows':0,'source_frames':23,'formal_database_writes':0,'production_extraction_started':False,
      'new_verification_database_queries':0,'old20_text_visual_audit_repeated':False,
      'corrected_single_Item_validation':'HTTP200PDFsaved; genericAcceptcause remains unproven',
      'remaining_HTTP_stops':'newB406 and AUtimeout persistent; oldHansard403 and oldB406 unchanged',
      'continuation_restart_authorized':False,'semantic_labels_or_exclusions':False,'sealed_evaluator_access':False,
      'independent_review_input_ready':True,'pooled_source_presence_refreshed':False,'storage':storage,
      'handoff_path':'HANDOFF_zh.md','log_entry_path':'LOG_ENTRY.md'}
    save('RESULT.json',result)
    save('FINAL_INPUT_READY.json',{'ready':True,'issuer':'Task4inputowner;notHTTPorformal-ingestionrelease',
      'status':'ready_for_coordinator_independent_analysis_after_bounded_stop','frozen_at_utc':timestamp,
      'fixed_publication_interval':INTERVAL,'final_input_manifest_sha256':sha(HERE/'FINAL_INPUT_MANIFEST.json'),
      'final_B_ledger_rows':979,'final_A_disposition_rows':5,'source_frame_rows':23,
      'prior_saved_Items':20,'new_saved_Items':27,'all_saved_Item_rows':47,'complete_Work_acceptance':'not established',
      'newraw_checked_once':True,'old20checks_reused':True,'newfirstpages_checked':27,
      'full_queue_complete':False,'remaining_B_failed':1,'remaining_B_unattempted':931,'no_link_Works':30,
      'AU_originals_obtained':0,'two_AU_case_dispositions_complete':True,'parent_length_certified_rows':0,
      'new_B_and_AU_stops_persistent':True,'old_stops_preserved':True,'next_HTTP_automatically_authorized':False,
      'formal_database_writes_authorized':False,'semantic_filtering_performed':False,'independent_audit_executed_here':False})
    print(json.dumps({'status':result['status'],'total_Items':47,'new_Items':27,'remaining_B':932,'AU_originals':0,'source_frames':23,
                      'new_pages':257,'cumulative_pages':392,'raw_bytes':22231574,'body_rereads_in_finalizer':0}))


if __name__=='__main__':main()
