#!/usr/bin/env python3
"""One named current-state addendum; preserve failed-history review annotations."""
import json
import shutil
import duckdb
import repair_cli as r

WORK='http://publications.europa.eu/resource/cellar/509beb66-6809-4935-81bd-e56e439eb40b'
ITEM=WORK+'.0004.02/DOC_1'
def main():
    if (r.HERE/'EU_CURRENT_STATE_ADDENDUM.json').exists():
        print('Current-state addendum already committed; no write.');return
    applied=json.loads((r.HERE/'APPLIED.json').read_text());before=applied['post_checkpoint']
    with r.locks(writer=True):
        r.writer_preflight()
        if r.stamp(r.DB)!=before:raise RuntimeError('Formal checkpoint moved before named addendum')
        eu=duckdb.connect(str(r.EUDB),read_only=True)
        try:versions=r.rows(eu,'SELECT * FROM eu_content_versions WHERE work_uri=? AND item_uri=?',[WORK,ITEM])
        finally:eu.close()
        if len(versions)!=1:raise RuntimeError('Ambiguous current selected-Item version')
        v=versions[0];path=r.BASE/'10_eu_cellar_acquisition'/v['raw_path']
        data=path.read_bytes()
        if not data.startswith(b'%PDF') or len(data)!=v['bytes'] or r.digest(data)!=v['sha256'] or v['http_status']!=200 or v['extraction_status']!='text_extracted' or not v['text_characters']:raise RuntimeError('Current saved Item availability preconditions failed')
        evidence={'work_uri':WORK,'item_uri':ITEM,'publication_date':'2002-11-08','current_technical_state':'saved_original_present_with_extracted_text_metadata','saved_version':v,'raw_input':r.stamp(path,True),'historical_disposition':'selected_item_failed','historical_disposition_preserved':True,'reason':'The very same selected Item later has a saved HTTP200 PDF with matching size/hash and 9,683 registered extracted characters. Historical failure is not current absence. Full layout/completeness remains unverified; this is an availability addendum only.','no_new_download':True,'checked_at_utc':r.now()}
        free=shutil.disk_usage(r.ROOT).free
        if free-64*1024**2<15*1024**3:raise RuntimeError('Named metadata addendum/storage reserve would breach retained floor')
        con=duckdb.connect(str(r.DB));con.execute('BEGIN TRANSACTION')
        try:
            con.execute('''CREATE TABLE repair_source_state_addenda(run_id VARCHAR,unit_id VARCHAR,source_id VARCHAR,rule_version VARCHAR,current_technical_state VARCHAR,evidence_json VARCHAR,PRIMARY KEY(run_id,unit_id,rule_version))''')
            values=[r.RUN,WORK,'eu_cellar_com_preparatory_en_v1','named_current_state_v1_20261004',evidence['current_technical_state'],r.dump(evidence)]
            con.execute('INSERT INTO repair_source_state_addenda VALUES (?,?,?,?,?,?)',values)
            con.execute('''CREATE VIEW repair_current_source_state_addenda AS SELECT a.* FROM repair_source_state_addenda a JOIN repair_runs r USING(run_id) WHERE r.active''')
            if tuple(con.execute('SELECT * FROM repair_current_source_state_addenda WHERE unit_id=?',[WORK]).fetchone())!=tuple(values):raise RuntimeError('Named addendum transaction acceptance failed')
            con.execute('COMMIT')
            if con.execute('SELECT current_technical_state FROM repair_current_source_state_addenda WHERE unit_id=?',[WORK]).fetchone()[0]!=evidence['current_technical_state']:raise RuntimeError('Named addendum post-commit check failed')
        except Exception:
            try:con.execute('ROLLBACK')
            except duckdb.TransactionException:pass
            raise
        finally:con.close()
        evidence['formal_pre_checkpoint']=before;evidence['formal_post_checkpoint']=r.stamp(r.DB);evidence['acceptance']='passed_transaction_and_postcommit';evidence['reserved_bytes']=64*1024**2;evidence['free_bytes_after']=shutil.disk_usage(r.ROOT).free
        r.atomic(r.HERE/'EU_CURRENT_STATE_ADDENDUM.json',evidence)
        shutil.copy2(r.HERE/'APPLIED.json',r.HERE/'APPLIED.primary_commit.json')
        applied['post_checkpoint']=evidence['formal_post_checkpoint'];applied['named_current_state_addendum_path']='EU_CURRENT_STATE_ADDENDUM.json';applied['last_formal_write_at_utc']=r.now();r.atomic(r.HERE/'APPLIED.json',applied)
        manifest=json.loads((r.HERE/'CHANGE_MANIFEST.json').read_text());manifest['primary_commit_post_checkpoint']=manifest['post_checkpoint'];manifest['post_checkpoint']=applied['post_checkpoint'];manifest['additive_current_source_states']=1;manifest['named_addendum']='EU_CURRENT_STATE_ADDENDUM.json';r.atomic(r.HERE/'CHANGE_MANIFEST.json',manifest)
        requests=r.csvread(r.HERE/'missing_original_requests.csv');shutil.copy2(r.HERE/'missing_original_requests.csv',r.HERE/'missing_original_requests.pre_eu_reconciliation.csv')
        final=[q for q in requests if q['unit_id']!=WORK]
        if len(requests)-len(final)!=1:raise RuntimeError('Named request reconciliation mismatch')
        r.csvwrite(r.HERE/'missing_original_requests.csv',final,['unit_id','source_id','source_date','canonical_url','requested_original','why_existing_evidence_insufficient','existing_evidence','request_type','priority'])
        r.atomic(r.HERE/'REQUEST_RECONCILIATION.json',{'prior_requests':6,'current_requests':5,'withdrawn_unit_id':WORK,'reason':'Exact selected original is already saved; current availability verified from HTTP/version/size/hash and registered extracted-text metadata. No download. Layout completeness remains an annotation/review need.','evidence_path':'EU_CURRENT_STATE_ADDENDUM.json'})
    print(r.dump({'status':'committed_checked_named_current_state','current_requests':5,'post_checkpoint':applied['post_checkpoint']}))
if __name__=='__main__':main()
