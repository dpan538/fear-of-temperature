"""Whole original articles from native anchored newspaper-issue transcriptions."""
import json,re,datetime as dt
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup,Tag
import elt

def issue_queue():
 p=elt.OWN/'ARCHIVE_ISSUE_QUEUE.json';return json.loads(p.read_text()) if p.exists() else []
def issue_state():
 p=elt.OWN/'ARCHIVE_ISSUE_STATE.json';return json.loads(p.read_text()) if p.exists() else {}

def parse_issue(raw,url,expected_date=None):
 soup=BeautifulSoup(raw,'html.parser');head=soup.find('h1');identity=head.get_text(' ',strip=True) if head else '';anchors=[a for a in soup.select('a[name]') if re.fullmatch(r'article\d+',a['name'])];day=None;date_values=[]
 if not head or 'Workers' not in identity or 'Advocate' not in identity:return {'status':'pending_native_issue_identity','units':[]}
 for n in head.next_siblings:
  if isinstance(n,Tag) and (n.name in ['table','hr'] or n.find('table')):break
  text=n.get_text(' ',strip=True) if isinstance(n,Tag) else str(n)
  m=re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',text)
  if m:
   try:date_values.append(dt.datetime.strptime(' '.join(m.groups()),'%B %d %Y').date().isoformat())
   except ValueError:pass
 if len(set(date_values))==1:day=date_values[0]
 status='confirmed_native_issue_metadata' if elt.eligible(day) else 'pending_native_issue_date'
 if expected_date and day and expected_date[:7]!=day[:7]:status='pending_native_issue_index_masthead_date_conflict'
 units=[];seen=set()
 for anchor in anchors:
  name=anchor['name']
  if name in seen:raise ValueError('Duplicate original newspaper article anchor in one native issue')
  seen.add(name);parts=[];ended=False
  for node in anchor.next_siblings:
   if isinstance(node,Tag) and node.name=='a' and re.fullmatch(r'article\d+',node.get('name','')):break
   if isinstance(node,Tag) and any(a.get('href')=='#top' and 'Back to Top' in a.get_text(' ',strip=True) for a in node.select('a[href]')):ended=True;break
   parts.append(str(node))
  dom=BeautifulSoup(''.join(parts),'html.parser');titles=dom.select('h3,h4');title=re.sub(r'\s+',' ',titles[0].get_text(' ',strip=True)) if titles else None
  if titles:titles[0].decompose()
  for n in dom.select('script,style,form,svg,nav,aside,h2'):n.decompose()
  body=elt.renderer.normalise(elt.renderer.render(dom));unit_status='confirmed_complete' if title and body.strip() and ended and status=='confirmed_native_issue_metadata' else ('pending_native_article_boundary' if status=='confirmed_native_issue_metadata' else status)
  units.append({'native_article_anchor':name,'title':title,'body':body,'publication_date':day,'status':unit_status,'original_native_terminator_verified':ended,'expected_native_index_date':expected_date,'native_masthead_date':day,'native_date_limit':'index and masthead day differ within same month; original values preserved' if expected_date and day and day!=expected_date else None})
 return {'status':status,'publication_date':day,'masthead':identity,'units':units,'raw_issue_is_container_not_article':True}

def discover(p,v,queue,fetch,permitted,policy):
 if v.get('stage','robots')=='robots':policy(p,v);return 1
 url=p['archive_index_url']
 if not permitted(v,url):v.update(stage='blocked',blocked_reason='Declared-agent archival index policy');return 1
 rec=fetch(p,url,{'source_identity_and_native_dated_issue_inventory':True,'no_PDF_acquisition':True})
 if rec['status']!='saved':v.update(stage='blocked',blocked_reason='Native archival newspaper index '+rec['status']);return 1
 soup=BeautifulSoup(elt.read_payload(rec['raw_reference']),'html.parser');old=issue_queue();seen={x['url'] for x in old};pdf=0
 for a in soup.select('a[href]'):
  target=urljoin(url,a['href']);u=urlsplit(target);text=a.get_text(' ',strip=True);m=re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',text)
  if not m:continue
  try:day=dt.datetime.strptime(' '.join(m.groups()),'%B %d %Y').date().isoformat()
  except ValueError:continue
  if not elt.eligible(day):continue
  if u.path.lower().endswith('.pdf'):pdf+=1;continue
  if u.scheme!='https' or u.hostname!=urlsplit(p['root_url']).hostname or not re.fullmatch(r'/history/erol/ncm-1/workers-advocate/\d+-\d+\.html',u.path) or not permitted(v,target):continue
  if target not in seen:
   item={'source_id':p['source_id'],'url':target,'publication_date_hint':day,'month':day[:7],'native_inventory_receipt':rec['target_id']}
   for line in (elt.OWN/'SOURCE_PREPARATION_RESULTS.jsonl').read_text().splitlines():
    saved=json.loads(line)
    if saved.get('url')==target and saved.get('status')=='saved':item['saved_request_id']=saved['receipt_reference'].split('/')[-1].removesuffix('.json')
   old.append(item);seen.add(target)
 old.sort(key=lambda x:(x['publication_date_hint'],x['url']));elt.save('ARCHIVE_ISSUE_QUEUE.json',old);v.update(stage='observed_public_frontier_consumed',attempted_pages=v.get('attempted_pages',0)+1,native_HTML_issue_candidates=len(old),ineligible_PDF_routes=pdf,reason='Dated observed HTML issue inventory materialized; body/article work remains independently open; PDF allocation exhausted; unknown complete archive denominator');return 1

def available():
 states=issue_state();st=elt.state();out=[]
 for issue in issue_queue():
  v=states.get(issue['url'],{})
  if v.get('stage') in ['native_articles_processed','access_stop','pending_native_issue_identity','pending_native_issue_date','pending_native_issue_index_masthead_date_conflict']:continue
  if urlsplit(issue['url']).hostname in st['access_stops'] or elt.canon(issue['url']) in elt.OLD_STOPS:continue
  out.append(issue)
 return sorted(out,key=lambda i:(i['publication_date_hint'],i['url']))

def acquire(issue):
 import broaden
 p=next(p for p in broaden.profiles() if p['source_id']==issue['source_id']);states=issue_state();v=states.setdefault(issue['url'],{'stage':'unfetched','units':{}})
 if v.get('request_id'):rec=elt._receipt(v['request_id'])
 elif issue.get('saved_request_id'):rec=elt._receipt(issue['saved_request_id'])
 else:rec=elt.fetch(issue['url'],issue['source_id'],p['stratum'],'article',{'native_issue_inventory':issue,'unit':'original newspaper articles from explicitly anchored HTML transcription; issue is not a countable article','no_PDF_acquisition':True})
 v['request_id']=rec['target_id']
 if rec['status']!='saved':v.update(stage='access_stop',transport_status=rec['status']);elt.save('ARCHIVE_ISSUE_STATE.json',states);return {'status':rec['status'],'qualified':0}
 parsed=parse_issue(elt.read_payload(rec['raw_reference']),issue['url'],issue['publication_date_hint']);v.update(stage=parsed['status'],publication_date=parsed.get('publication_date'),native_unit_anchors=[u['native_article_anchor'] for u in parsed['units']]);elt.save('ARCHIVE_ISSUE_STATE.json',states)
 if not parsed['units']:
  elt.append('ARCHIVE_ISSUE_EVIDENCE.jsonl',{'at_utc':elt.utc(),'issue':issue,'raw_reference':rec['raw_reference'],'status':parsed['status'],'article_units':0});return {'status':parsed['status'],'qualified':0}
 count=0;issue_key=urlsplit(issue['url']).path.rsplit('/',1)[-1].removesuffix('.html')
 for u in parsed['units']:
  anchor=u['native_article_anchor'];aid=issue['source_id']+':issue:'+issue_key+':'+anchor
  if anchor in v['units']:continue
  record=dict(article_id=aid,source_id=issue['source_id'],source=p['title'],source_url=issue['url']+'#'+anchor,raw_source_url=issue['url'],url_aliases=[issue['url']+'#'+anchor],original_issue_url=issue['url'],native_article_anchor=anchor,title=u['title'],publication_date=u['publication_date'],date_field='Native original issue masthead date; explicitly anchored individual newspaper article',native_masthead_date=u['native_masthead_date'],expected_native_index_date=u['expected_native_index_date'],native_date_limit=u['native_date_limit'],stratum=p['stratum'],country=p['country'],edition=p['edition'],source_frame=p['source_frame'],provenance='archival reproduction/transcription of original Workers Advocate newspaper article; quoted/reprinted origins separate',content_version_time=None,archive_transcription_time='unreported in observed HTML; not publication time',retrieved_at_utc=rec['finished_at_utc'],raw_reference=rec['raw_reference'],raw_sha256=rec['raw_sha256'],request_id=rec['target_id'],retention_limit=p['retention_limit'],body_boundary='Native named article anchor '+anchor+' through its verified Back to Top terminator; table of contents, issue masthead and later section heading excluded',article_boundary_evidence='Explicit native article anchor, original article headline and end-navigation; full continuous prose/subheadings retained across original printed-page continuations; original issue is a container',original_native_terminator_verified=u['original_native_terminator_verified'],semantic_labels_executed=False,length_filter_used=False)
  if u['body']:
   bp=elt.OWN/'bodies'/(aid.replace(':','_')+'_'+elt.sha(u['body'].encode())[:12]+'.txt')
   with elt.LOCK.open('a+b') as lock:
    elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);elt.preflight(len(u['body'].encode())*3+1048576);bp.parent.mkdir(exist_ok=True);bp.write_text(u['body'])
   record['body_reference']=str(bp.relative_to(elt.REPO))
  result=elt.load(record,u['body'],u['status']);v['units'][anchor]={'article_id':aid,'status':result['load_status'],'body_sha256':result.get('body_sha256'),'version_id':result.get('version_id')};elt.save('ARCHIVE_ISSUE_STATE.json',states)
  if result['load_status']=='confirmed_complete':count+=1
 v['stage']='native_articles_processed';elt.save('ARCHIVE_ISSUE_STATE.json',states);elt.append('ARCHIVE_ISSUE_EVIDENCE.jsonl',{'at_utc':elt.utc(),'issue_url':issue['url'],'publication_date':parsed['publication_date'],'raw_reference':rec['raw_reference'],'native_anchored_units':len(parsed['units']),'new_qualified_whole_articles':count,'original_issue_not_counted_as_article':True,'processed_unit_metadata':v['units']});return {'status':v['stage'],'qualified':count}
