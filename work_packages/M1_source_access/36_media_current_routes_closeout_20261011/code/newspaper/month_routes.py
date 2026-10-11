"""Executable named gap routes through already advertised public interfaces."""
import json,calendar,datetime as dt,collections,re
from urllib.parse import urlencode,urlsplit
from bs4 import BeautifulSoup
import elt,production,broaden,native_batches,extract_load
from fear_temperature.media_planning.core import Opportunity
W=elt.OWN;FILE=W/'MISSING_MONTH_EXECUTABLE_STATE.json'
def state():return json.loads(FILE.read_text()) if FILE.exists() else {}
def save(o):elt.save(FILE.name,o)
def prepare():
 import focused_repair as focus
 o=state();cursors=broaden._state()
 for month in sorted(focus.ZEROS):
  if month<'2007-01':continue
  for sid in ['limerick_post','falls_church_news_press']:
   key='focused_month:'+sid+':'+month
   if key in o:continue
   profile=next(p for p in broaden.profiles() if p['source_id']==sid and broaden.approved(p));v=cursors[sid]
   assert v.get('collection_url') and v.get('schema_receipt')
   year,mo=map(int,month.split('-'));start=dt.datetime(year,mo,1)-dt.timedelta(seconds=1);end=dt.datetime(year+(mo==12),mo%12+1,1)
   args=dict(after=start.isoformat(),before=end.isoformat(),orderby='date',order='asc',per_page=50,_fields='id,date,modified,link,title,_links,status,type,categories')
   url=v['collection_url']+'?'+urlencode(args)
   o[key]=dict(source_id=sid,month=month,phase='listing',next_url=url,targets=[],schema_receipt=v['schema_receipt'],collection_url=v['collection_url'],documentation=profile['public_API_documentation_reference'],title_classification=profile['title_classification_reference'],permitted_query_checked=broaden._permitted(v,url),scope='Named missing month; returned publication dates checked independently; month becoming present never stops surplus')
 save(o);return o
def options(aged):
 o=state();choices=[];payload={};touched=set(elt.state()['targets'])
 for key,r in o.items():
  if r['phase']=='body':
   geo=extract_load.ADAPTERS[r['source_id']]['stratum'];items=production.eligible(r['targets'],production.KNOWN,touched,{},geo,'historical_native')
   if not items:
    r['phase']='listing' if r.get('next_url') else 'observed_bounded_frontier_consumed';save(o)
   else:payload[key]=items
  if r['phase'] not in ['listing','body']:continue
  choices.append(Opportunity(key,'named_missing_month',r['source_id'],r['month'],r['month'],'Source-advertised public month query; existing policy, provider and native ID guards',wait_rounds=aged[key],need_priority=0))
 return choices,payload
def perform(key):
 o=state();r=o[key];sid=r['source_id'];profile=next(p for p in broaden.profiles() if p['source_id']==sid and broaden.approved(p));v=broaden._state()[sid]
 if r['phase']=='listing':
  url=r['next_url']
  if not broaden._permitted(v,url):r.update(phase='blocked_declared_agent',reason='Actual saved source rules deny this public query');save(o);return
  try:rec=elt.fetch(url,sid,profile['stratum'],'discovery',{'purpose':'Named missing-month native metadata; not topic filtered','source_advertised_collection':r['collection_url'],'schema_receipt':r['schema_receipt']})
  except ValueError as e:r.update(phase='blocked_preserved_source',reason=str(e));save(o);return
  if rec['status']!='saved':r.update(phase='pending_transport',transport_status=rec['status'],request_id=rec['target_id']);save(o);return
  posts=json.loads(elt.read_payload(rec['raw_reference']));assert isinstance(posts,list);items=[]
  for post in posts:
   day=(post.get('date') or '')[:10];pid=post.get('id');article=post.get('link');self_url=next((x['href'] for x in post.get('_links',{}).get('self',[]) if x.get('href')),None)
   if not (pid and article and self_url and elt.eligible(day) and day[:7]==r['month']):continue
   if urlsplit(self_url).hostname!=urlsplit(v['api_root']).hostname or urlsplit(article).hostname!=urlsplit(profile['root_url']).hostname or not broaden._permitted(v,self_url):continue
   items.append(dict(source_id=sid,url=self_url,article_url=article,native_post_id=pid,representation='publisher_wp_article_json',month=day[:7],native_evidence=dict(title=BeautifulSoup(post.get('title',{}).get('rendered',''),'html.parser').get_text(' ',strip=True),native_date=post.get('date'),native_modified=post.get('modified'),native_list_receipt={'target_id':rec['target_id'],'raw_reference':rec['raw_reference']},publisher_API_documentation=r['documentation'],source_classification=r['title_classification'],source_specific_retention_limit=profile['retention_limit'],focused_missing_month=True)))
  production.queue(sid,items);headers=rec.get('hops',[{}])[-1];link=headers.get('link') or '';match=re.search(r'<([^>]+)>;\s*rel="next"',link)
  r.update(targets=items,metadata_receipt=rec['target_id'],next_url=match[1] if match and broaden._permitted(v,match[1]) else None,phase='body' if items else ('listing' if match else 'observed_empty_bounded_response'),whole_archive_exhaustion=False)
  elt.append('MISSING_MONTH_NATIVE_RESULTS.jsonl',dict(at_utc=elt.utc(),source_id=sid,month=r['month'],request_id=rec['target_id'],native_candidates=len(items),phase=r['phase'],article_or_source_count_stop=False));save(o)
 elif r['phase']=='body':
  items=production.eligible(r['targets'],production.KNOWN,set(elt.state()['targets']),{},profile['stratum'],'historical_native')
  if not items:return
  if not native_batches.acquire(sid,items,production.KNOWN):
   result=extract_load.acquire(items[0])
   if result and result.get('load_status') in ['confirmed_complete','already_retained_identity']:production.KNOWN.add(elt.canon(result['source_url']))
  elt.append('MISSING_MONTH_BODY_OPERATIONS.jsonl',dict(at_utc=elt.utc(),source_id=sid,month=r['month'],eligible_native_transport_batch=True,no_minimum_count_completion=True))
