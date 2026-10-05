"""Validate named local delivery receipts; do not reopen source PDF bodies."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];WP=ROOT/'work_packages/M1_source_access'


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def load(p): return json.loads(Path(p).read_text())


def rows(p):
    with Path(p).open() as f:return list(csv.DictReader(f))


def main():
    checks=[]
    def check(name,condition):
        checks.append({'check':name,'passed':bool(condition)})
    manifest=load(HERE/'INPUT_MANIFEST.json');ready=load(HERE/'GOV_CLOSEOUT_INPUT_READY.json')
    for e in manifest['evidence_files']+manifest['staging_request_sidecars']:
        p=ROOT/e['path'];check('receipt:'+e['path'],p.is_file() and p.stat().st_size==e['bytes'] and sha(p)==e['sha256'])
    check('ready binds exact input manifest',ready['input_manifest_sha256']==sha(HERE/'INPUT_MANIFEST.json'))
    shape=rows(HERE/'CHANGED_ITEM_TEXT_SHAPE.csv');page=rows(HERE/'PDF_PAGE_SHAPE.csv');frame=rows(HERE/'GOV_FRAME_REGISTER.csv')
    check('20distinct unchanged Item hashes',len(shape)==20 and len({r['item_uri'] for r in shape})==20
          and all(r['sha256_matches']=='True' and r['raw_sha256']==r['raw_sha256_rechecked'] for r in shape))
    check('raw total9020646',sum(int(r['raw_bytes']) for r in shape)==9020646)
    check('135page rows and no empty layers',len(page)==135 and all(r['empty_text']=='False' for r in page))
    check('page counts sum135',sum(int(r['pdf_page_count']) for r in shape)==135)
    check('19printed-day matches and1conflict',sum(r['issue_date_comparison']=='agrees_with_saved_Work_day' for r in shape)==19
          and sum(r['issue_date_comparison']=='conflict_one_day_same_month' for r in shape)==1)
    check('7COM13OJ printed body genres',sum(r['printed_component_role']=='COM proposal PDF' for r in shape)==7)
    check('4first-page multi-notice Items',sum(r['first_page_multiple_notice_refs']=='True' for r in shape)==4)
    check('6multiple selectedManifestation Items',sum(int(r['selected_manifestation_distinct_items'])>1 for r in shape)==6)
    check('no Item promoted to complete parent length',all(r['parent_statistics_eligible']=='False' and r['formal_ingestion_performed']=='False' for r in shape))
    check('23native source frames',len(frame)==23 and all(r['source_route_is_department']=='False' for r in frame))
    check('UK248319effective parents',sum(int(r['known_inventory_count']) for r in frame if r['region']=='UK')==248319)
    check('US33544selected metadata parents',sum(int(r['known_inventory_count']) for r in frame if r['region']=='US')==33544)
    check('IE684809question indices',sum(int(r['official_index_count']) for r in rows(HERE/'inputs/IE_WRITTEN_QUESTION_MONTH_INDEX.csv'))==684809)
    check('NZ536question indices',sum(int(r['displayed_count']) for r in rows(HERE/'inputs/NZ_2025_PORTFOLIO_QUESTION_MONTH_INDEX.csv'))==536)
    au=rows(HERE/'AU_ORIGINAL_CHECK_PLAN.csv');check('AU2cases4requests54MiBmaximum',len(au)==2
        and sum(int(r['maximum_requests']) for r in au)==4
        and sum(int(r['landing_cap_bytes'])+int(r['pdf_cap_bytes']) for r in au)==54*2**20)
    check('one merged pending release, never self-authorized',load(HERE/'CONTINUATION_RELEASE_TEMPLATE.json')['ready'] is False
          and not (HERE.parent/'control/GOV_CONTINUATION_RELEASE.json').exists()
          and not (HERE/'continuation').exists())
    b=WP/'18_bounded_supplementation_execution_20261005/02_eu_staging'
    old=load(b/'OUTPUT_RECEIPT.json')
    check('all oldBoutputs intact',all(sha(b/name)==e['sha256'] for name,e in old['artifacts'].items()))
    release=load(b.parent/'control/EU_STAGING_RELEASE.json')
    check('oldA403stop intact',sha(b.parent/'01_downloader_and_originals/SHARED_HTTP_STATE.json')==release['a_http_state_sha256'])
    check('oldV3 code unchanged',sha(WP/'15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation/stage_frozen_items.py')
          =='f6f2bda93e9745c56ff9fd438be8071af2b40ee65b5f5b625d30f2d1c5e28bb2')
    repair=load(WP/'15_targeted_repairs_and_supplementation_20261004/control/REPAIR_READY.json')
    db=ROOT/repair['post_checkpoint']['path'];st=db.stat()
    check('UKfile stat still releasedcheckpoint',st.st_size==repair['post_checkpoint']['bytes'] and st.st_mtime_ns==repair['post_checkpoint']['mtime_ns'])
    check('16offline tests passed', 'Ran 16 tests' in (HERE/'TRANSPORT_TESTS.log').read_text()
          and (HERE/'TRANSPORT_TESTS.log').read_text().strip().endswith('OK'))
    check('fixed interval maintained',ready['fixed_publication_interval']==['1988-01-01','2026-09-21']==manifest['fixed_publication_interval'])
    required=['HANDOFF_zh.md','LOG_ENTRY.md','CURRENT_GAPS.csv','RESULT.json','TRANSPORT_PATCH_READY.json','BOUNDED_PARENT_EXPORT_REQUEST.json']
    check('allrequiredartifacts present',all((HERE/n).is_file() for n in required))
    failures=[r for r in checks if not r['passed']]
    value={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'status':'passed' if not failures else 'failed',
           'checks':checks,'failures':failures,'raw_PDF_rereads_in_delivery_check':0,'database_queries':0,
           'new_source_requests':0,'sealed_evaluator_access':False}
    (HERE/'DELIVERY_CHECK.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    assert not failures, failures
    paths=[p for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='OUTPUT_RECEIPT.json']
    receipt={'created_at_utc':value['checked_at_utc'],'status':'input_owner_delivery_verified',
             'artifacts':{str(p.relative_to(HERE)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths},
             'scope':'derived inputs/evidence/code/notes only; raw saved outside this directory unchanged',
             'delivery_checks':len(checks),'formal_database_writes':0,'new_source_HTTP':0,
             'continuation_release':'pending coordinator; template ready=false'}
    (HERE/'OUTPUT_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':value['status'],'checks':len(checks),'artifacts':len(paths),'new_HTTP':0,'raw_rechecks':0}))


if __name__=='__main__':main()
