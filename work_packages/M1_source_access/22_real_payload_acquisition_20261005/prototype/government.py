"""Exactly one historical failure and ten frozen new targets; no DB or old raw."""
import csv, json
from pathlib import Path
import transport as t
WP=t.ROOT/'work_packages/M1_source_access'
OLD=WP/'19_gov_closeout_and_media_transition_20261005/01_gov_closeout/continuation'
FROZEN=WP/'15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation/frozen_acquisition_manifest.csv'
def rows(p):
    with Path(p).open(newline='') as f: return list(csv.DictReader(f))
def prepare():
    ledger=rows(OLD/'FINAL_B_STATUS_LEDGER.csv'); frozen=rows(FROZEN)
    by={r['item_uri']:r for r in ledger}
    if len(by)!=979 or len(frozen)!=979: raise RuntimeError('Frozen target denominator differs')
    failed=[r for r in ledger if r['latest_status']=='failed']
    pending=[r for r in frozen if by[r['item_uri']]['latest_status']=='not_attempted_after_stop']
    if len(failed)!=1 or len(pending)!=931 or failed[0]['latest_http_status']!='406': raise RuntimeError('Sealed stop counts differ')
    row=next(r for r in frozen if r['item_uri']==failed[0]['item_uri'])
    targets=[row]+pending[:10]
    cp=t.ROOT/failed[0]['latest_checkpoint_path']
    if t.digest(cp)!=failed[0]['latest_checkpoint_sha256']: raise RuntimeError('Historical406 receipt differs')
    value=dict(prepared_at_utc=t.now().isoformat(), historical_saved=47,historical_failed=1,historical_unattempted=931,no_link_works_outside_denominator=30, prior406=failed[0], prior406_sha256=t.digest(cp), frozen_manifest_sha256=t.digest(FROZEN), final_ledger_sha256=t.digest(OLD/'FINAL_B_STATUS_LEDGER.csv'), transport_accept='*/*', max_new_requests=11, first_failure_stops=True, targets=targets, formal_database_reads=0,formal_database_writes=0,old_raw_reads=0)
    t.save(t.OUT/'government/TARGET_SEQUENCE.json',value)
    return value
def event(value):
    p=t.OUT/'government/OWNER_EVENTS.jsonl';p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a') as f: f.write(json.dumps(dict(at_utc=t.now().isoformat(),**value),ensure_ascii=False)+'\n')
def execute():
    sequence=t.read(t.OUT/'government/TARGET_SEQUENCE.json')
    existing=list((t.OUT/'government/requests').glob('*.json')) if (t.OUT/'government/requests').exists() else []
    if existing: raise RuntimeError('Government run already attempted; no automatic restart')
    outcome=[]
    for index,row in enumerate(sequence['targets']):
        r=t.fetch('eu_cellar',row['request_url'],'selected_Item','consistent_exact_uri',lane='government',hosts=['publications.europa.eu'])
        r.update(item_uri=row['item_uri'], parent_id=row['parent_id'], publication_dates=row['publication_dates'], historical406_receipt=sequence['prior406']['latest_checkpoint_path'] if index==0 else None)
        t.save(t.OUT/'government/attempts'/f'{index+1:02}.json',r)
        event({'event':'new_exact_uri_attempt','sequence_index':index,'item_uri':row['item_uri'],'http_status':r['http_status'],'status':r['status'],'bytes':r['byte_count'],'accept':'*/*','old406_preserved':True})
        outcome.append(r)
        if r['status']!='saved': break
    t.save(t.OUT/'government/RESULT.json',dict(finished_at_utc=t.now().isoformat(),requests=len(outcome),new_pdf_items=sum(x['status']=='saved' for x in outcome),unattempted_authorised_targets=11-len(outcome),complete_works_verified=0,new_originals=0,historical_baseline_unchanged=True,formal_database_access=False,outcomes=outcome))
    return outcome
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--execute',action='store_true');a=p.parse_args()
    if a.prepare: print(json.dumps({'prepared_targets':len(prepare()['targets'])}))
    if a.execute: execute()
