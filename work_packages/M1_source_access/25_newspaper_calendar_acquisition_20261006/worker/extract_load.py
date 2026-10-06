"""Simple source-aware structural extraction and immediate durable Load."""
import datetime as dt,json,re,pathlib,collections,csv
from bs4 import BeautifulSoup
import elt
ADAPTERS={
 'mit_tech':dict(title='The Tech',country='US',stratum='US',edition='MIT English student newspaper; native digital article frame',frame='US student newspaper supplement',selectors=['main.container > article.article'],exclude=['script','style','form','svg','.article-meta','h1','h2','.article-share','.article-actions','.share-menu','.tags']),
 'green_left':dict(title='Green Left Weekly / Green Left',country='AU',stratum='AU',edition='English Australian political advocacy weekly',frame='Australian advocacy newspaper supplement; 1991 onward',selectors=['article.node--type-article .field--name-field-body'],exclude=['script','style','form','svg']),
 'trinity_news':dict(title='Trinity News',country='IE',stratum='EU/Europe excluding UK',edition='English Trinity College Dublin student newspaper',frame='Irish student newspaper supplement',selectors=['.entry-content'],exclude=['script','style','form','svg','.sharedaddy','.jp-relatedposts','.related-posts','.author-bio']),
 'mancunion':dict(title='The Mancunion',country='UK',stratum='UK',edition='English University of Manchester student newspaper',frame='UK student newspaper supplement; observed archive from 2010',selectors=['.uk-panel.uk-text-large.uk-margin','.entry-content'],exclude=['script','style','form','svg','.sharedaddy','.related-posts','.author-bio']),
 'beaver':dict(title='The Beaver',country='UK',stratum='UK',edition='English London School of Economics student newspaper',frame='UK student newspaper supplement; current site frame from 2014',selectors=['.elementor-widget-theme-post-content'],exclude=['script','style','form','svg','.sharedaddy','.related-posts']),
 'otago_daily_times':dict(title='Otago Daily Times',country='NZ',stratum='NZ',edition='English New Zealand regional daily',frame='NZ regional daily public web article frame',selectors=['#article-body'],exclude=['script','style','form','svg','.share-links','.advertisement','.ads','.related-content'])}
def date(soup,sid):
 values=[]
 for sel,attr in [('meta[property="article:published_time"]','content'),('meta[name="date"]','content'),('time[datetime]','datetime')]:
  for n in soup.select(sel):values.append((sel,n.get(attr)))
 for n in soup.select('script[type="application/ld+json"]'):
  try:obj=json.loads(n.string or n.get_text());objects=obj if isinstance(obj,list) else obj.get('@graph',[obj])
  except Exception:continue
  for o in objects:
   if isinstance(o,dict) and o.get('datePublished'):values.append(('JSON-LD datePublished',o['datePublished']))
 if sid=='mit_tech':
  n=soup.select_one('article.article .article-meta .timestamp')
  m=re.search(r'([A-Za-z]+)\.?\s+(\d{1,2}),\s*(\d{4})',n.get_text(' ',strip=True) if n else '')
  if m:
   month={dt.date(2000,i,1).strftime('%b').lower():i for i in range(1,13)}[m[1][:3].lower()];return dt.date(int(m[3]),month,int(m[2])).isoformat(),'native displayed article timestamp',n.get_text(' ',strip=True),values
 for field,value in values:
  if value and re.match(r'^\d{4}-\d{2}-\d{2}',value):return value[:10],field,value,values
 return None,None,None,values
def parse(raw,sid,url,metadata=None):
 adapter=ADAPTERS[sid];soup=BeautifulSoup(raw,'html.parser');title=soup.select_one('h1');title=title.get_text(' ',strip=True) if title else '';day,df,stamp,fields=date(soup,sid);canonical_node=soup.select_one('link[rel="canonical"]');canonical=canonical_node.get('href') if canonical_node else url
 record=dict(article_id=elt.article_id(sid,canonical),source_id=sid,source=adapter['title'],source_url=canonical,raw_source_url=url,url_aliases=sorted({url,canonical}),title=title,publication_date=day,date_field=df,publisher_timestamp=stamp,observed_date_fields=fields,stratum=adapter['stratum'],country=adapter['country'],edition=adapter['edition'],source_frame=adapter['frame'],provenance='direct publisher newspaper utterance; wire/reproduced/quoted origins retained separately',historical_body_equivalence='unknown; retrieved archive rendition',semantic_labels_executed=False,length_filter_used=False)
 if metadata:record.update(metadata)
 nodes=[];selector=None
 for sel in adapter['selectors']:
  ns=soup.select(sel)
  if len(ns)==1:nodes=ns;selector=sel;break
 if not nodes:return record,'','pending_missing_or_nonunique_body'
 node=nodes[0];header_text=node.get_text(' ',strip=True);record['body_boundary']=selector
 for n in node.select(','.join(adapter['exclude'])):n.decompose()
 body=elt.renderer.normalise(elt.renderer.render(node));paragraphs=node.select('p');h3=[n.get_text(' ',strip=True) for n in node.select('h3') if n.get_text(' ',strip=True)]
 record.update(paragraph_count=len(paragraphs),table_count=len(node.select('table')),native_subheadings=h3)
 if sid=='mancunion':
  leads=soup.select('.uk-panel.uk-text-lead')
  if len(leads)==1:
   lead=leads[0].get_text(' ',strip=True)
   if re.sub(r'\s+','',lead) not in re.sub(r'\s+','',body):body=lead+'\n\n'+body;record['simple_cleanup']='unique native standfirst restored before same article body'
 if sid=='beaver':
  body=re.sub(r'\n\n(?:Post Views:|View count:)[^\n]*','',body);record['simple_cleanup']='publisher view-counter widget excluded where present'
 url_day=re.search(r'/(\d{4})/(\d{2})/(\d{2})/',url);url_day='-'.join(url_day.groups()) if url_day else None
 record['url_date']=url_day
 if not body.strip():return record,body,'pending_empty_body'
 if not title or title.lower()=='headline':return record,body,'pending_placeholder_identity'
 if all(p.strip().lower()=='text' for p in body.split('\n\n') if p.strip()):return record,body,'pending_placeholder_body'
 if not elt.eligible(day):return record,body,'pending_date_or_outside_fixed_interval'
 if url_day and url_day[:7]!=day[:7]:return record,body,'pending_cross_month_date_conflict'
 if url_day and url_day!=day:record['date_limit']='native displayed day and URL day differ within supported month'
 if title.strip().lower()=='table' or (record['table_count'] and not len(paragraphs)):return record,body,'non_article_table_component'
 if sid=='green_left' and title.strip().lower()=='radio highlights':return record,body,'non_article_radio_schedule'
 if sid=='green_left' and title.strip().lower()=='write on':return record,body,'pending_compiled_letters_original_boundaries'
 if sid=='trinity_news' and title=='TN: Looking for Applications':return record,body,'non_article_publisher_recruitment_notice'
 if sid=='mit_tech':
  if title.strip().lower()=='corrections':return record,body,'non_article_publisher_errata'
  if re.search(r'\bnews\s+in\s+short\b',header_text,re.I):return record,body,'non_article_unrelated_notices'
  if re.search(r'(?:rush events|graduate student orientation|^fraternities$|^activities midway$)',title,re.I):return record,body,'non_article_schedule_or_component'
  if re.fullmatch('in short',title.strip(),re.I) and len([p for p in paragraphs if not p.get_text().startswith('Send news')])>1:return record,body,'non_article_unrelated_notices'
  if title.strip().lower()=='news briefs' and len(h3)>1:return record,body,'pending_multiple_original_article_boundaries'
  if title.lower()=='police log':return record,body,'pending_compiled_log_article_unit'
  if 'excerpt' in title.lower():return record,body,'pending_explicit_excerpt'
  if title.endswith(' G') or urlsplit_path(url).endswith('-info-v127-n34'):return record,body,'pending_biographical_component'
  if re.search('this web update was published on',body,re.I):
   m=re.search(r'published on ([A-Za-z]+) (\d+), (\d{4})',body,re.I)
   if m:
    try:
     internal=dt.datetime.strptime(' '.join(m.groups()),'%B %d %Y').date().isoformat();record['original_publication_body_date']=internal
     if internal[:7]!=day[:7]:return record,body,'pending_cross_month_version_mapping'
    except ValueError:pass
 if node.select('.paywall,.subscription-wall,.article-preview'):return record,body,'pending_visible_preview_or_paywall'
 record['article_boundary_evidence']='Unique complete native article-content container and publisher title/date; full source paragraph order retained. Printed continuations require separate mapping, not arbitrary chunks.'
 return record,body,'confirmed_complete'
def urlsplit_path(url):return elt.urlsplit(url).path
def acquire(target):
 sid=target['source_id'];adapter=ADAPTERS[sid]
 try:rec=elt.fetch(target['url'],sid,adapter['stratum'],'article',target['native_evidence'],extra={'month':target.get('month'),'whole_article_required':True,'native_target_identity':target.get('article_url') or target['url']})
 except (ValueError,RuntimeError) as e:
  elt.append('FRONTIER_STOPS.jsonl',dict(target=target,reason=str(e),at_utc=elt.utc()))
  if isinstance(e,RuntimeError) and ('resource_stop' in str(e) or 'fixed_deadline' in str(e)):raise
  return None
 if rec['status']!='saved':return elt.load({'source_id':sid,'source_url':target['url'],'transport_reference':'receipts/'+rec['target_id']+'.json','native_evidence':target['native_evidence']},'', 'pending_'+rec['status'])
 raw=elt.REPO/rec['raw_reference']
 if target.get('representation')=='publisher_wp_article_json':
  obj=json.loads(raw.read_text());url=obj.get('link');day=(obj.get('date') or '')[:10];title=BeautifulSoup(obj.get('title',{}).get('rendered',''),'html.parser').get_text(' ',strip=True);content=obj.get('content',{}).get('rendered','');node=BeautifulSoup(content,'html.parser')
  for n in node.select('script,style,form,svg,.sharedaddy,.related-posts'):n.decompose()
  body=elt.renderer.normalise(elt.renderer.render(node));assert url and elt.canon(url)==elt.canon(target['article_url']);assert obj.get('id')==target['native_post_id']
  record=dict(article_id=elt.article_id(sid,url),source_id=sid,source=adapter['title'],source_url=url,raw_source_url=target['url'],url_aliases=[url,target['url']],title=title,publication_date=day,date_field='publisher public JSON date',publisher_timestamp=obj.get('date'),content_version_time=obj.get('modified'),source_native_post_id=obj['id'],stratum=adapter['stratum'],country=adapter['country'],edition=adapter['edition'],source_frame=adapter['frame'],raw_reference=rec['raw_reference'],raw_sha256=rec['raw_sha256'],retrieved_at_utc=rec['finished_at_utc'],request_id=rec['target_id'],native_target_reference='targets/'+rec['target_id']+'.json',body_boundary='Publisher native JSON content.rendered for one original post',article_boundary_evidence='Publisher metadata listing supplied original post ID/date/title/permalink and advertised self API; entire matching post content.rendered extracted as one whole body',paragraph_count=len(node.select('p')),provenance='direct publisher native article representation; cited/quoted reporting origins remain separate',historical_body_equivalence='unknown; current archive rendition',semantic_labels_executed=False,length_filter_used=False)
  status='confirmed_complete' if body and title and elt.eligible(day) else 'pending_empty_or_date_body'
  if re.search(r'\[liveblog|\[.*iframe|\[.*embed',body,re.I):status='pending_embedded_component_body'
 else:record,body,status=parse(raw.read_bytes(),sid,rec['final_url'],dict(raw_reference=rec['raw_reference'],raw_sha256=rec['raw_sha256'],retrieved_at_utc=rec['finished_at_utc'],request_id=rec['target_id'],native_target_reference='targets/'+rec['target_id']+'.json'))
 if sid=='mancunion' and status=='pending_missing_or_nonunique_body':
  # Recover the same original article through its explicitly advertised public
  # alternate representation. This is neither a blind HTML retry nor another
  # independent article/attempt. Original missing HTML evidence is retained.
  soup=BeautifulSoup(raw.read_bytes(),'html.parser');api=soup.select_one('link[rel="alternate"][type="application/json"]')
  if api and api.get('href'):
   elt.load(record,body,status)
   try:
    api_rec=elt.fetch(api['href'],sid,adapter['stratum'],'article',{'alternate_link_observed_in':rec['raw_reference'],'same_original_article_url':target['url']},extra={'native_target_identity':target['url'],'representation':'publisher advertised public WordPress article JSON'})
    if api_rec['status']=='saved':
     obj=json.loads((elt.REPO/api_rec['raw_reference']).read_text());api_html=obj.get('content',{}).get('rendered','');api_title=BeautifulSoup(obj.get('title',{}).get('rendered',''),'html.parser').get_text(' ',strip=True);api_link=obj.get('link')
     assert api_link and elt.canon(api_link)==elt.canon(record['source_url']) and api_title==record['title']
     api_dom=BeautifulSoup(api_html,'html.parser')
     for n in api_dom.select('script,style,form,svg,.sharedaddy,.related-posts'):n.decompose()
     recovered=elt.renderer.normalise(elt.renderer.render(api_dom));api_day=(obj.get('date') or '')[:10]
     if recovered and elt.eligible(api_day) and api_day[:7]==record['publication_date'][:7] and not re.search(r'\[liveblog|\[.*iframe|\[.*embed',recovered,re.I) and not re.search(r'^(?:as it happened|live ?blog)',api_title,re.I):
      record.update(raw_reference=api_rec['raw_reference'],raw_sha256=api_rec['raw_sha256'],html_raw_reference=rec['raw_reference'],publication_date=api_day,source_native_post_id=obj.get('id'),body_boundary='Advertised publisher WordPress JSON content.rendered, one native original post',article_boundary_evidence='Saved HTML advertises exact public JSON post; id/title/link/date match original article; entire publisher-native content.rendered loaded as one body',content_version_time=obj.get('modified'),simple_cleanup='HTML renderer omitted original post body; complete native article JSON restored using the observed alternate URL',retrieved_at_utc=api_rec['finished_at_utc']);body=recovered;status='confirmed_complete'
   except Exception as error:record['alternate_route_limit']=repr(error)
 body_hash=elt.sha(body.encode());bp=elt.OWN/'bodies'/(record['article_id'].replace(':','_')+'_'+body_hash[:12]+'.txt')
 if body:
  with elt.LOCK.open('a+b') as lock:
   elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);elt.preflight(len(body.encode())*4+1048576);bp.parent.mkdir(exist_ok=True);bp.write_text(body)
  record['body_reference']=str(bp.relative_to(elt.REPO))
 return elt.load(record,body,status)
def cache_recovery():
 register=[json.loads(x) for x in (elt.OLD24/'article_baseline_v1/ARTICLE_REGISTER.jsonl').read_text().splitlines()];seen={elt.canon(r['raw_source_url']) for r in register};q=list(csv.DictReader((elt.OLD24.parent/'GAP_QUEUE.csv').open()));months=[r['month'] for r in q if 'cached' in r['queue_state']]
 units=[json.loads(x) for x in (elt.BASE/'PUBLICATION_UNITS.jsonl').read_text().splitlines()];chosen=[];counts=collections.Counter();urls=set()
 for r in units:
  month=r.get('publication_date','')[:7];url=elt.canon(r['url'])
  if month in months and url not in seen and url not in urls and r.get('body_path') and counts[month]<5:
   chosen.append(r);counts[month]+=1;urls.add(url)
 elt.save('CACHE_SELECTION.json',{'frozen_at_utc':elt.utc(),'14_named_months':months,'limit_per_month':5,'native_metadata_order_no_refill':True,'selected_counts':dict(counts),'selected':chosen,'no_additional_saved_uninspected_candidates':[m for m in months if not counts[m]]})
 for r in chosen:
  raw=elt.BASE/r['raw_path'];body_path=elt.BASE/r['body_path'];sid='mit_tech' if r['source']=='The Tech' else 'indaily'
  if sid not in ADAPTERS:continue
  record,body,status=parse(raw.read_bytes(),sid,r['url'],dict(raw_reference=str(raw.relative_to(elt.REPO)),raw_sha256=r['raw_sha256'],retrieved_at_utc=r['retrieved_at_utc'],cache_recovery=True,original_body_reference=str(body_path.relative_to(elt.REPO))))
  bp=elt.OWN/'bodies'/(record['article_id'].replace(':','_')+'_'+elt.sha(body.encode())[:12]+'.txt')
  if body:
   with elt.LOCK.open('a+b') as lock:
    elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);elt.preflight(len(body.encode())*4+1048576);bp.parent.mkdir(exist_ok=True);bp.write_text(body)
   record['body_reference']=str(bp.relative_to(elt.REPO))
  elt.load(record,body,status)
 elt.save('CACHE_RECOVERY_CHECKPOINT.json',{'at_utc':elt.utc(),'inspected_additional_candidates':len(chosen),'per_month':dict(counts),'coverage':{g+':'+m:v for (g,m),v in elt.coverage().items()},'early_1988_1990_route':'The Tech native dated print-issue archive; existing OCR/date/component stops preserved. No additional previously uninspected cached HTML in early months. Crimson retention pending; Guardian licensing/key and NZETC through1979 limitations preserved.'})
 print(json.dumps({'cache_candidates':len(chosen),'complete_articles_in_DB':elt.connect().execute('SELECT count(*) FROM articles').fetchone()[0],'clock':elt.utc()}),flush=True)
if __name__=='__main__':cache_recovery()
