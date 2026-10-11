"""Public documented WP collection batches; each original post stays one article."""
import json,re
from urllib.parse import urlencode,urlsplit
from bs4 import BeautifulSoup
import elt,broaden,extract_load

def raw_status_map():
 p=elt.OWN/'NATIVE_BATCH_UNIT_STATUS.json';return json.loads(p.read_text()) if p.exists() else {}

def status_map():
 o=raw_status_map()
 named_path=elt.OWN/'NAMED_NATIVE_TRANSPORT_RECOVERY.json'
 named=json.loads(named_path.read_text()).get('entries',{}) if named_path.exists() else {}
 def still_blocks(aid,v):
  if v.get('request_id') in elt.TRANSPORT_REOPENS and v.get('status') in ['pending_batch_interrupted_pending','pending_native_batch_interrupted_pending']:return False
  entry=named.get(aid)
  if entry and v.get('status')==entry['original_status']=='pending_batch_transport_error' and v.get('request_id')==entry['original_request_id']:
   return False # Specific alternative self representation; original failed row retained.
  return True
 return {aid:v for aid,v in o.items() if still_blocks(aid,v)}

def representation(obj,sid,target,rec,index):
 adapter=extract_load.ADAPTERS[sid];pid=obj.get('id');url=obj.get('link');day=(obj.get('date') or '')[:10]
 assert pid==target['native_post_id'] and url and elt.canon(url)==elt.canon(target['article_url'])
 node=BeautifulSoup(obj.get('content',{}).get('rendered',''),'html.parser')
 for n in node.select('script,style,form,svg,.sharedaddy,.related-posts'):n.decompose()
 body=elt.renderer.normalise(elt.renderer.render(node));title=BeautifulSoup(obj.get('title',{}).get('rendered',''),'html.parser').get_text(' ',strip=True)
 record=dict(article_id=sid+':post:'+str(pid),source_id=sid,source=adapter['title'],source_url=url,raw_source_url=target['url'],url_aliases=[url,target['url']],title=title,publication_date=day,date_field='Publisher native public JSON date, site timezone',publisher_timestamp=obj.get('date'),content_version_time=obj.get('modified'),source_native_post_id=pid,stratum=adapter['stratum'],country=adapter['country'],edition=adapter['edition'],source_frame=adapter['frame'],raw_reference=rec['raw_reference'],raw_sha256=rec['raw_sha256'],retrieved_at_utc=rec['finished_at_utc'],request_id=rec['target_id'],native_target_reference='targets/'+rec['target_id']+'.json',native_batch_item_id=pid,native_batch_item_index=index,native_listing_month=target.get('month'),body_boundary='Entire matching native post content.rendered within public collection response; one article per persistent post ID',article_boundary_evidence='Observed public collection and queued native self ID/permalink/date match; batch transport is a container, not an article or extra parent',paragraph_count=len(node.select('p')),embedded_resources_present=bool(node.select('iframe,object,embed')),embedded_media_content_collected=False,provenance='direct publisher native original article representation; quoted/reproduced origins separate',historical_body_equivalence='unknown; current archive rendition',semantic_labels_executed=False,length_filter_used=False)
 status=elt.native_article_unit_status(obj) or ('confirmed_complete' if body and title and elt.eligible(day) else 'pending_empty_identity_or_date_body')
 return record,body,status

def acquire(sid,items,known):
 profile=next((p for p in broaden.profiles() if p['source_id']==sid and broaden.approved(p)),None)
 v=broaden._state().get(sid,{})
 if not profile or profile.get('interface_type')=='publisher_native_sitemap' or not v.get('collection_url'):return None
 state=elt.state();done=status_map()
 chosen=[t for t in items if t.get('representation')=='publisher_wp_article_json' and sid+':post:'+str(t['native_post_id']) not in done and not state.get('native_http_hops',{}).get(elt.sha((sid+'|article|'+elt.canon(t['article_url'])).encode())[:24],0)][:25]
 if not chosen:return None
 by_id={int(t['native_post_id']):t for t in chosen};ids=list(by_id)
 url=v['collection_url']+('&' if '?' in v['collection_url'] else '?')+urlencode({'include':','.join(map(str,ids)),'per_page':len(ids),'orderby':'include','context':'view','_fields':'id,date,modified,link,title,content,status,type,categories'})
 if not broaden._permitted(v,url):return None
 named_path=elt.OWN/'NAMED_NATIVE_TRANSPORT_RECOVERY.json'
 named=json.loads(named_path.read_text()).get('entries',{}) if named_path.exists() else {}
 if any(sid+':post:'+str(pid) in named for pid in ids):return None
 if elt.canon(url) in elt.OLD_STOPS and not elt.transport_reopen_allowed(sid,'article',url):return None
 # Previously charged native participants cannot exceed their inherited four-hop budget.
 state=elt.state();keys={pid:elt.sha((sid+'|article|'+elt.canon(t['article_url'])).encode())[:24] for pid,t in by_id.items()}
 if any(state.get('native_http_hops',{}).get(key,0) for key in keys.values()):return None
 rec=elt.fetch(url,sid,profile['stratum'],'article',{'public_collection_observed_in':v.get('schema_receipt'),'documentation':'https://developer.wordpress.org/rest-api/reference/posts/','native_post_IDs_requested':ids,'source_retention_limit':profile['retention_limit'],'whole_original_article_units':True},extra={'native_target_identity':url,'kind':'public_native_article_batch','native_post_IDs':ids})
 state=elt.state();unit_status=raw_status_map();hops=len(rec.get('hops',[]))
 for pid,key in keys.items():
  state.setdefault('native_http_hops',{})[key]=state.get('native_http_hops',{}).get(key,0)+hops
  if key not in state.setdefault('charged_native_targets',[]):state['charged_native_targets'].append(key)
 state.setdefault('additional_batch_native_units_requested',{}).setdefault(profile['stratum'],0);state['additional_batch_native_units_requested'][profile['stratum']]+=len(ids)
 for pid in ids:unit_status[sid+':post:'+str(pid)]={'status':'saved_batch_item_Load_pending' if rec['status']=='saved' else 'pending_batch_'+rec['status'],'request_id':rec['target_id']}
 elt.save('NATIVE_BATCH_UNIT_STATUS.json',unit_status)
 elt.save('TRANSPORT_STATE.json',state)
 if rec['status']!='saved':
  for pid in ids:unit_status[sid+':post:'+str(pid)]={'status':'pending_batch_'+rec['status'],'request_id':rec['target_id']}
  elt.load({'source_id':sid,'source_url':url,'native_post_IDs_requested':ids,'raw_reference':rec.get('raw_reference'),'raw_sha256':rec.get('raw_sha256'),'request_id':rec['target_id'],'transport_reference':'receipts/'+rec['target_id']+'.json'},'','pending_native_batch_'+rec['status']);elt.save('NATIVE_BATCH_UNIT_STATUS.json',unit_status)
  return {'attempted_native_units':len(ids),'qualified_native_units':0,'transport_status':rec['status']}
 objects=json.loads(elt.read_payload(rec['raw_reference']));assert isinstance(objects,list);seen=set();qualified=0
 for index,obj in enumerate(objects):
  pid=obj.get('id')
  if pid not in by_id or pid in seen:raise ValueError('Public batch returned unrequested or duplicate native post ID')
  seen.add(pid);record,body,status=representation(obj,sid,by_id[pid],rec,index);result=elt.load(record,body,status);aid=sid+':post:'+str(pid)
  unit_status[aid]={'status':result.get('load_status',status),'request_id':rec['target_id'],'body_sha256':result.get('body_sha256'),'version_id':result.get('version_id')}
  if result.get('load_status')=='confirmed_complete':known.add(elt.canon(result['source_url']));qualified+=1
 for pid in set(ids)-seen:unit_status[sid+':post:'+str(pid)]={'status':'pending_missing_native_batch_item','request_id':rec['target_id']}
 elt.save('NATIVE_BATCH_UNIT_STATUS.json',unit_status);elt.append('NATIVE_BATCH_TRANSPORT_EVIDENCE.jsonl',dict(at_utc=elt.utc(),source_id=sid,stratum=profile['stratum'],request_id=rec['target_id'],raw_reference=rec['raw_reference'],raw_sha256=rec['raw_sha256'],native_units_requested=len(ids),native_units_returned=len(seen),qualified_whole_articles=qualified,body_transfer_targets=1,source_article_units_are_not_transport_containers=True))
 return {'attempted_native_units':len(ids),'qualified_native_units':qualified,'transport_status':rec['status']}


def resume_saved(known,target_reader):
 """Load any saved batch participants left by a controlled interruption, with no new HTTP."""
 eligible=status_map();statuses=raw_status_map();pending=[(aid,v) for aid,v in eligible.items() if v.get('status')=='saved_batch_item_Load_pending']
 if not pending:return 0
 request_id=pending[0][1]['request_id'];rec=elt._receipt(request_id)
 if rec['status']!='saved':return 0
 sid=rec['source_id'];profile=next((p for p in broaden.profiles() if p['source_id']==sid and broaden.approved(p)),None)
 if not profile or sid not in broaden.active_ids(profile['stratum']):raise ValueError('Saved batch source no longer passes its original public newspaper frame')
 matches={int(t['native_post_id']):t for t in target_reader(sid) if t.get('native_post_id')}
 objects=json.loads(elt.read_payload(rec['raw_reference']));indices={o['id']:i for i,o in enumerate(objects)};done=0
 for aid,v in pending:
  if v['request_id']!=request_id:continue
  pid=int(aid.rsplit(':',1)[1])
  if pid not in matches or pid not in indices:
   statuses[aid]={'status':'pending_saved_batch_native_target_or_item_mapping','request_id':request_id};continue
  target=matches[pid]
  if elt.canon(target['article_url']) in known:
   statuses[aid]={'status':'already_committed_before_controlled_restart','request_id':request_id};continue
  index=indices[pid];record,body,status=representation(objects[index],sid,target,rec,index);result=elt.load(record,body,status)
  statuses[aid]={'status':result.get('load_status',status),'request_id':request_id,'body_sha256':result.get('body_sha256'),'version_id':result.get('version_id'),'saved_batch_recovery_without_new_HTTP':True}
  if result.get('load_status') in ['confirmed_complete','already_retained_identity']:known.add(elt.canon(result['source_url']))
  done+=1
 elt.save('NATIVE_BATCH_UNIT_STATUS.json',statuses);elt.append('SAVED_BATCH_RECOVERY.jsonl',{'at_utc':elt.utc(),'request_id':request_id,'saved_native_units_processed':done,'new_HTTP':False,'counters_not_reset':True})
 return max(1,done)
