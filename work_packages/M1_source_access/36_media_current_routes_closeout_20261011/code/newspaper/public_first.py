"""A subscription source must expose complete public HTML before native body fetch."""
import elt,broaden,public_visibility,native_batches
def acquire(target,original):
 sid=target['source_id'];profile=next(p for p in broaden.profiles() if p['source_id']==sid and broaden.approved(p));url=target['article_url'];native=target['native_evidence'];pid=target['native_post_id'];aid=sid+':post:'+str(pid)
 record=dict(source_id=sid,article_id=aid,source_native_post_id=pid,source_url=url,raw_source_url=target['url'],publication_date=native['native_date'][:10],title=native['title'],stratum=profile['stratum'],country=profile['country'],source_frame=profile['source_frame'],edition=profile['edition'],native_listing_month=target['month'],public_HTML_first=True,subscription_or_private_content_requested=False)
 state=broaden._state()[sid]
 if not broaden._permitted(state,url):status='pending_public_original_HTML_access_mapping'
 else:
  try:rec=elt.fetch(url,sid,profile['stratum'],'article',{'purpose':'Public original HTML first: explicit subscription source; no native full-body until current complete unprotected original is mapped','native_post_ID':pid},extra={'native_target_identity':url,'kind':'public_HTML_before_native_body'})
  except ValueError as error:record['public_HTML_mapping_status']=str(error);status='pending_public_original_HTML_access_mapping'
  else:
   record.update(request_id=rec['target_id'],public_HTML_request_id=rec['target_id'],raw_reference=rec.get('raw_reference'),raw_sha256=rec.get('raw_sha256'),retrieved_at_utc=rec.get('finished_at_utc'))
   if rec['status']!='saved':status='pending_public_original_HTML_access_mapping'
   else:
    parsed,visible,status=public_visibility.parse_visible(elt.read_payload(rec['raw_reference']),sid,rec['final_url'],record)
    if status=='confirmed_complete':
     if elt.canon(parsed['source_url'])!=elt.canon(url) or parsed['publication_date']!=record['publication_date'] or parsed['title']!=record['title']:status='pending_public_HTML_native_identity_title_date_mapping'
     else:
      result=original(target);elt.append('PUBLIC_HTML_FIRST_RESULTS.jsonl',dict(at_utc=elt.utc(),article_id=aid,public_HTML_request_id=rec['target_id'],public_HTML_status='complete_current_unprotected_original',native_body_requested=True,load_status=(result or {}).get('load_status'),fixed_source_native_hop_budget_preserved=True));return result
 record['original_article_completeness_not_established']=True;record['native_full_body_not_requested']=True
 result=elt.load(record,'',status);statuses=native_batches.raw_status_map();statuses[aid]=dict(status=result['load_status'],request_id=record.get('request_id'),public_HTML_first=True,native_full_body_not_requested=True);elt.save('NATIVE_BATCH_UNIT_STATUS.json',statuses)
 elt.append('PUBLIC_HTML_FIRST_RESULTS.jsonl',dict(at_utc=elt.utc(),article_id=aid,public_HTML_status=status,native_body_requested=False,load_status=result['load_status'],no_API_body_bypass=True));return result
