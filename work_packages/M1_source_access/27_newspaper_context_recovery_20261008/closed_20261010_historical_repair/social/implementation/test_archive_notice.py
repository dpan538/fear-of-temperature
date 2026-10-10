"""Source-generated Mailman notice typing and derived quality correction."""
import csv,gzip,json,sqlite3,tempfile
from pathlib import Path
from unittest.mock import patch
import archive_adapter as a,entities as e,transport as t
from raw_catalog import catalog
checks=[]
notice='\n-------------- next part --------------\nAn HTML attachment was scrubbed...\nURL: <http://public.example/attachment.html>\n\n'
def mbox(text):return ('From archive Tue Jul 2 00:00:00 2002\nMessage-ID: <native-fixture@example>\nDate: Tue, 2 Jul 2002 09:23:48 +0800\nFrom: Fixture\nContent-Type: text/plain\n\n'+text).encode()
raw=mbox(notice);r=a.mbox_records(raw,'python_list_archive','https://public.example/2002-July.txt')[0];prep=e.prepare(r)
assert prep['body_original']==notice and prep['content_state']=='archive_generated_attachment_notice' and prep['independently_authored_body']==0 and prep['native_created_at']=='2002-07-02T01:23:48+00:00'
assert prep['attachments'][0]['url']=='http://public.example/attachment.html'
checks.append('exact_server_notice_preserved_as_native_evidence_without_authored_body_count')
ordinary=e.prepare(a.mbox_records(mbox('A native author sentence.\n'+notice),'python_list_archive','https://public.example/2002-July.txt')[0]);assert ordinary['independently_authored_body']==1
checks.append('message_with_authored_text_and_attachment_notice_stays_authored')
with tempfile.TemporaryDirectory(dir=t.WORK) as d:
 w=Path(d);(w/'receipts').mkdir();out=w/'out';out.mkdir();p=w/'native.bin.gz';p.write_bytes(gzip.compress(raw,mtime=0));at='2026-10-10T02:00:00+00:00'
 rec={'request_id':'fixture-request','source_id':'python_list_archive','purpose':'content','url':'https://public.example/2002-July.txt','retrieved_at':at,'status':'saved','raw_reference':str(p),'raw_sha256':t.sha(raw),'stored_sha256':t.sha(p.read_bytes()),'raw_bytes':len(raw),'stored_bytes':p.stat().st_size,'http_status':200}
 t.atomic(w/'receipts'/'fixture-request.json',rec);t.atomic(w/'source_registry.json',[{'source_id':'python_list_archive'}]);(w/'LOADS.jsonl').write_text(json.dumps({'request_id':'fixture-request'})+'\n');scope=w/'scope.json';t.atomic(scope,{'earliest_network_and_load_start_at_utc':'2026-10-10T01:00:00+00:00'})
 c=sqlite3.connect(':memory:')
 c.executescript('CREATE TABLE native_entities(entity_id,source_id,native_namespace,native_id,native_created_at);CREATE TABLE entity_versions(entity_version_id,entity_id,body_sha256,flags_json);CREATE TABLE entity_observations(request_id,entity_version_id,retrieved_at);CREATE TABLE entity_quality_annotations(entity_version_id PRIMARY KEY,independently_authored_body,directness,native_mapping_basis,original_external_body_checked,temporal_limitations_json,annotated_at);CREATE TABLE structural_corrections(correction_id PRIMARY KEY,entity_id,field,prior_value,derived_value,evidence_json,corrected_at);')
 c.execute('INSERT INTO native_entities VALUES (?,?,?,?,?)',('stable-id','python_list_archive','message_id',r['native_post_id'],r['native_created_at']));c.execute('INSERT INTO entity_versions VALUES (?,?,?,?)',('immutable-version','stable-id',prep['body_sha256'],'{}'));c.execute('INSERT INTO entity_observations VALUES (?,?,?)',('fixture-request','immutable-version',at));c.execute('INSERT INTO entity_quality_annotations VALUES (?,?,?,?,?,?,?)',('immutable-version',1,'historical-adapter','native',0,'{}',at));c.commit()
 with patch.object(t,'WORK',w),patch.object(t,'SCOPE_PATH',scope):
  stats,files=catalog(c,out)
  assert stats['mapping_issues']==0 and stats['archive_notice_only_version_corrections']==1
  assert c.execute('SELECT independently_authored_body FROM entity_quality_annotations').fetchone()[0]==0
  assert c.execute('SELECT entity_id,body_sha256 FROM entity_versions').fetchone()==('stable-id',prep['body_sha256'])
  assert c.execute('SELECT COUNT(*) FROM structural_corrections').fetchone()[0]==1
 checks.append('terminal_changed_raw_check_corrects_only_derived_quality_and_preserves_ids_and_body_versions')
t.atomic(t.WORK/'ARCHIVE_NOTICE_REGRESSION.json',{'at_utc':t.utc(),'passed':True,'checks':checks,'source_requests':0,'real_corpus_writes':0})
print(json.dumps({'passed':True,'checks':len(checks)}))
