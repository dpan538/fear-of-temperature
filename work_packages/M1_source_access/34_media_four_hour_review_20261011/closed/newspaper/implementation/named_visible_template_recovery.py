"""Named saved article recovery after evidenced visible-template correction."""
import json
from bs4 import BeautifulSoup
import elt,production,public_visibility
FIELDS=['source_id','source_url','publication_date','publisher_timestamp','raw_reference','raw_sha256','public_HTML_request_id','public_HTML_raw_reference','public_HTML_raw_sha256','title','source_native_post_id']
def perform():
 path=elt.OWN/'NAMED_VISIBLE_TEMPLATE_RECOVERY.json'
 if not path.exists():return 0
 manifest=json.loads(path.read_text());assert manifest['new_HTTP_released'] is False
 done_path=elt.OWN/'VISIBLE_TEMPLATE_RECOVERY_DONE.json';done=set(json.loads(done_path.read_text())) if done_path.exists() else set();logs=[json.loads(x) for x in (elt.OWN/'LOAD_LOG.jsonl').read_text().splitlines()];performed=0
 for entry in manifest['entries']:
  aid=entry['article_id']
  if aid in done:continue
  elt.assert_release()
  if elt.canon(entry['source_url']) in production.KNOWN:done.add(aid);elt.save(done_path.name,sorted(done));continue
  old=next(r for r in logs if r.get('article_id')==aid and r['load_status']==entry['original_status'] and r['request_id']==entry['original_request_id'])
  assert entry['source_id'] in ['castlemaine_mail','chester_telegraph','gippsland_times'] and all(old[k]==entry[k] for k in FIELDS)
  raw=elt.read_payload(entry['raw_reference']);assert elt.sha(raw)==entry['raw_sha256'];objects=json.loads(raw);objects=objects if isinstance(objects,list) else [objects];obj=next(o for o in objects if o['id']==old['source_native_post_id'])
  assert aid==old['source_id']+':post:'+str(obj['id']) and obj['date']==old['publisher_timestamp'] and obj['date'][:10]==old['publication_date'] and elt.canon(obj['link'])==elt.canon(old['source_url']) and not elt.native_article_unit_status(obj)
  assert BeautifulSoup(obj['title']['rendered'],'html.parser').get_text(' ',strip=True)==old['title']
  node=BeautifulSoup(obj['content']['rendered'],'html.parser')
  for n in node.select('script,style,form,svg,.sharedaddy,.related-posts'):n.decompose()
  body=elt.renderer.normalise(elt.renderer.render(node));assert elt.sha(body.encode())==entry['native_body_sha256']
  html=elt.read_payload(entry['public_HTML_raw_reference']);assert elt.sha(html)==entry['public_HTML_raw_sha256'];record=dict(old)
  parsed,visible,status=public_visibility.parse_visible(html,old['source_id'],old['source_url'],record);status=public_visibility.evaluate(record,body,parsed,visible,status,html)
  before=elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED;result=None
  if status=='confirmed_complete':
   for k in ['load_status','loaded_at_utc','evidence_id','body_reference','body_sha256','version_id']:record.pop(k,None)
   result=elt.load(record,body,'confirmed_complete')
   if result.get('load_status') in ['confirmed_complete','already_retained_identity']:production.KNOWN.add(elt.canon(result['source_url']))
  assert elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED==before
  performed+=1;done.add(aid);elt.save(done_path.name,sorted(done));elt.append('VISIBLE_TEMPLATE_RECOVERY_RESULTS.jsonl',dict(at_utc=elt.utc(),article_id=aid,source_id=entry['source_id'],original_request_id=entry['original_request_id'],load_status=(result or {}).get('load_status',status),new_HTTP_attempts=0,publication_date=old['publication_date'],original_pending_evidence_preserved=True,original_native_batch_status_rows_changed=False,public_HTML_structural_cleanup=record.get('public_HTML_structural_cleanup')))
 return performed
