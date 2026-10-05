"""Final named-receipt/ledger consistency checks. Never rehash raw PDF bodies."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent;OWNER=HERE.parent;ROOT=OWNER.parents[3];WP=ROOT/'work_packages/M1_source_access'


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def load(p):return json.loads(Path(p).read_text())


def read(p):
    with Path(p).open() as f:return list(csv.DictReader(f))


def main():
    checks=[]
    def check(label,value):checks.append({'check':label,'passed':bool(value)})
    manifest=load(HERE/'FINAL_INPUT_MANIFEST.json');ready=load(HERE/'FINAL_INPUT_READY.json');result=load(HERE/'RESULT.json')
    for e in manifest['evidence_files']:
        p=ROOT/e['path'];check('receipt:'+e['path'],p.is_file() and p.stat().st_size==e['bytes'] and sha(p)==e['sha256'])
    check('ready boundfinalmanifest',sha(HERE/'FINAL_INPUT_MANIFEST.json')==ready['final_input_manifest_sha256'])
    b=read(HERE/'FINAL_B_STATUS_LEDGER.csv');a=read(HERE/'FINAL_A_DISPOSITIONS.csv');shape=read(HERE/'ALL_SAVED_ITEM_TEXT_SHAPE.csv')
    new=read(HERE/'CHANGED_ITEM_TEXT_SHAPE.csv');pages=read(HERE/'CHANGED_PDF_PAGE_SHAPE.csv')
    check('979unique selectedItem statusrows',len(b)==979 and len({r['item_uri'] for r in b})==979)
    check('20reused27new1failed931unattempted',Counter(r['latest_status'] for r in b)=={'verified_local_reuse':20,'downloaded_candidate_original':27,'failed':1,'not_attempted_after_stop':931})
    check('932remaining targets',len(read(HERE/'FINAL_B_REMAINING_TARGETS.csv'))==932)
    check('5Aoriginalcase outcomes',len(a)==5 and len({r['unit_id'] for r in a})==5)
    check('oneAUrequest2ndnotattempted',sum(int(r['continuation_requests']) for r in a)==1
          and sum(r['current_followup_status']=='landing_read_timeout' for r in a)==1
          and sum(r['current_followup_status']=='unattempted_after_AU_stop' for r in a)==1)
    check('47distinct Item identity rows',len(shape)==47 and len({r['item_uri'] for r in shape})==47)
    check('27new onlychangedItem rows',len(new)==27 and all(r['raw_path'].startswith(str(HERE.relative_to(ROOT))+'/B_CORRECTED/raw/') for r in new))
    check('27new257nonempty textpages',len(pages)==257 and all(r['empty_text']=='False' for r in pages))
    check('newPDFpagescount257',sum(int(r['pdf_page_count']) for r in new)==257)
    check('cumulative392PDFpages',sum(int(r['pdf_page_count']) for r in shape)==392)
    check('newraw13210928cumulative22231574',sum(int(r['raw_bytes']) for r in new)==13210928 and sum(int(r['raw_bytes']) for r in shape)==22231574)
    check('45printed-date agreements2conflicts',sum(r['issue_date_comparison']=='agrees_with_saved_Work_day' for r in shape)==45
          and sum(r['issue_date_comparison']=='conflict_one_day_same_month' for r in shape)==2)
    check('allprinted-day andCDMmonths2015January',all(r['publication_dates'][:7]=='2015-01' and r['printed_issue_date'][:7]=='2015-01' for r in shape))
    check('0certified completeparent length rows',all(r['parent_statistics_eligible']=='False' for r in shape))
    check('2identicalrawgroups4Itemidentities',len(read(HERE/'CROSS_WORK_IDENTICAL_ITEM_GROUPS.csv'))==4
          and len({r['raw_sha256'] for r in read(HERE/'CROSS_WORK_IDENTICAL_ITEM_GROUPS.csv')})==2)
    check('47Itemrows45unique bytehashes',len({r['raw_sha256'] for r in shape})==45)
    check('12months1009Work979targets30nolink',len(read(HERE/'FINAL_B_MONTH_DISPOSITIONS.csv'))==12
          and sum(int(r['enumerated_Works']) for r in read(HERE/'FINAL_B_MONTH_DISPOSITIONS.csv'))==1009
          and sum(int(r['frozen_selected_Item_targets']) for r in read(HERE/'FINAL_B_MONTH_DISPOSITIONS.csv'))==979
          and sum(int(r['no_link_Works']) for r in read(HERE/'FINAL_B_MONTH_DISPOSITIONS.csv'))==30)
    check('23native-source frames retained',len(read(HERE/'FINAL_GOV_FRAME_REGISTER.csv'))==23)
    check('currentstops28B1AU persist',load(HERE/'B_CORRECTED/PHASE_HTTP_STATE.json')['halted']
          and load(HERE/'B_CORRECTED/PHASE_HTTP_STATE.json')['request_count']==28
          and load(HERE/'AU_ORIGINALS/PHASE_HTTP_STATE.json')['halted']
          and load(HERE/'AU_ORIGINALS/PHASE_HTTP_STATE.json')['request_count']==1)
    release=load(OWNER.parent/'control/GOV_CONTINUATION_RELEASE.json')
    check('same releasedcode untouched',sha(OWNER/'transport_continuation.py')==release['transport_sha256'])
    for k,p in [('input_manifest_sha256',OWNER/'INPUT_MANIFEST.json'),('input_ready_sha256',OWNER/'GOV_CLOSEOUT_INPUT_READY.json'),
                ('old_a_stop_sha256',WP/'18_bounded_supplementation_execution_20261005/01_downloader_and_originals/SHARED_HTTP_STATE.json'),
                ('old_b_stop_sha256',WP/'18_bounded_supplementation_execution_20261005/02_eu_staging/PHASE_HTTP_STATE.json')]:
        check('oldboundevidencepreserved:'+k,sha(p)==release[k])
    check('fixedintervalunchanged',manifest['fixed_publication_interval']==ready['fixed_publication_interval']==result['fixed_publication_interval']==['1988-01-01','2026-09-21'])
    check('noformalwriteorautomaticrestart',result['formal_database_writes']==0 and result['continuation_restart_authorized'] is False)
    check('releasekeepsnoextraction/fullWorkacceptance',release['formal_database_writes_authorized'] is False
          and release['extraction_or_complete_work_acceptance_authorized'] is False)
    for e in manifest['raw_files']:
        p=ROOT/e['path'];check('rawstatonly:'+e['item_uri'],p.is_file() and p.stat().st_size==e['bytes'])
    check('reports andlogpresent',all((HERE/p).is_file() for p in ['HANDOFF_zh.md','LOG_ENTRY.md','EXECUTION_RECEIPT.json','FINAL_CURRENT_GAPS.csv']))
    failures=[r for r in checks if not r['passed']]
    receipt={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'status':'passed' if not failures else 'failed',
             'checks':checks,'failures':failures,'raw_body_reads_or_hashes':0,'database_queries_or_writes':0,
             'source_requests':0,'private_evaluator_access':False}
    (HERE/'DELIVERY_CHECK.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    assert not failures,failures
    # Runtime raw is listed by already-verified hash; never reread it for output receipts.
    files=[p for p in sorted(HERE.rglob('*')) if p.is_file() and 'raw' not in p.relative_to(HERE).parts
           and '__pycache__' not in p.relative_to(HERE).parts and p.name!='OUTPUT_RECEIPT.json']
    output={'created_at_utc':receipt['checked_at_utc'],'status':'final_input_delivery_verified_after_bounded_stops',
            'artifacts':{str(p.relative_to(HERE)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in files},
            'raw_bodies':'47old/newItemversions referenced by FINAL_INPUT_MANIFEST; excluded from receipt rehash',
            'checks':len(checks),'native_exec_exit_code':0,'acquisition_complete':False,'input_ready':True,
            'new_Items':27,'cumulative_Items':47,'new_AU_originals':0,'current_B_remaining':932,
            'formal_database_writes':0,'automatic_retry_authorized':False}
    (HERE/'OUTPUT_RECEIPT.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'checks':len(checks),'nonraw_artifacts':len(files),'raw_rereads':0,'newrequests':0}))


if __name__=='__main__':main()
