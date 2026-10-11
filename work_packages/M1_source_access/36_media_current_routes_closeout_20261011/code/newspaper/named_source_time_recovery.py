"""One exact six-unit saved-evidence recovery; original pending rows remain."""
import json
from bs4 import BeautifulSoup
import elt,production,source_local_publication_time

def perform():
 path=elt.OWN/'NAMED_SOURCE_LOCAL_TIME_RECOVERY.json'
 if not path.exists():return 0
 manifest=json.loads(path.read_text());assert manifest['new_HTTP_released'] is False
 done_path=elt.OWN/'SOURCE_LOCAL_TIME_RECOVERY_DONE.json';done=set(json.loads(done_path.read_text())) if done_path.exists() else set();logs=[json.loads(x) for x in (elt.OWN/'LOAD_LOG.jsonl').read_text().splitlines()];performed=0
 for entry in manifest['entries']:
  aid=entry['article_id']
  if aid in done:continue
  elt.assert_release()
  old=next(r for r in logs if r.get('article_id')==aid and r['load_status']==entry['original_status'] and r['request_id']==entry['original_request_id'])
  assert entry['original_status']=='pending_public_HTML_native_identity_date_conflict' and entry['source_id']=='midland_express'
  for key in ['source_id','source_url','publication_date','publisher_timestamp','raw_reference','raw_sha256','public_HTML_request_id','public_HTML_raw_reference','public_HTML_raw_sha256']:assert old[key]==entry[key]
  raw=elt.read_payload(entry['raw_reference']);assert elt.sha(raw)==entry['raw_sha256'];objects=json.loads(raw);objects=objects if isinstance(objects,list) else [objects];pid=old['source_native_post_id'];obj=next(o for o in objects if o['id']==pid)
  assert aid==old['source_id']+':post:'+str(pid) and (obj['date'])[:10]==old['publication_date'] and obj['date']==old['publisher_timestamp'] and elt.canon(obj['link'])==elt.canon(old['source_url']) and not elt.native_article_unit_status(obj)
  node=BeautifulSoup(obj.get('content',{}).get('rendered',''),'html.parser')
  for n in node.select('script,style,form,svg,.sharedaddy,.related-posts'):n.decompose()
  body=elt.renderer.normalise(elt.renderer.render(node));assert elt.sha(body.encode())==entry['body_sha256']
  html=elt.read_payload(entry['public_HTML_raw_reference']);assert elt.sha(html)==entry['public_HTML_raw_sha256'];record=dict(old);parsed={'publication_date':old['public_HTML_publication_date']};assert source_local_publication_time.reconcile(record,parsed,html)
  for key in ['load_status','loaded_at_utc','evidence_id']:record.pop(key,None)
  before=elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED
  result=elt.load(record,body,'confirmed_complete');performed+=1
  assert elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED==before
  if result.get('load_status') in ['confirmed_complete','already_retained_identity']:done.add(aid);production.KNOWN.add(elt.canon(result['source_url']))
  elt.append('SOURCE_LOCAL_TIME_RECOVERY_RESULTS.jsonl',dict(at_utc=elt.utc(),article_id=aid,original_request_id=entry['original_request_id'],load_status=result.get('load_status'),new_HTTP_attempts=0,publication_date=old['publication_date'],original_pending_evidence_preserved=True,original_batch_status_rows_changed=False));elt.save(done_path.name,sorted(done))
 return performed
