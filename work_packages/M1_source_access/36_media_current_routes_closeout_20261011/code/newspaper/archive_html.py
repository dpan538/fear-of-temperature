"""Evidenced public HTML archive traversal; article date independently parsed."""
import json,re,datetime as dt
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
import elt

def discover(p,v,queue,fetch,permitted,policy):
 if v.get('stage','robots')=='robots':policy(p,v);return 1
 routes=v.setdefault('archive_routes',list(p.get('archive_start_urls',[])));done=v.setdefault('archive_consumed',[])
 todo=[u for u in routes if u not in done]
 if not todo:v.update(stage='observed_public_frontier_consumed',reason='Observed HTML inventory links consumed; article bodies remain distinct work; historical population unknown');return 1
 url=min(todo);done.append(url)
 if not permitted(v,url):v.setdefault('unpermitted_routes',[]).append(url);return 1
 rec=fetch(p,url,{'source_verified_archive_inventory':p['source_access_reference'],'observed_HTML_route':True,'no_PDF_allocation':True})
 if rec['status']!='saved':v.setdefault('archive_access_limits',[]).append({'url':url,'status':rec['status']});return 1
 soup=BeautifulSoup(elt.read_payload(rec['raw_reference']),'html.parser');region=soup.select_one(p.get('inventory_selector','body'))
 if not region:v.setdefault('archive_access_limits',[]).append({'url':url,'status':'missing_inventory_region'});return 1
 items=[]
 for a in region.select('a[href]'):
  u=urljoin(url,a['href']);h=urlsplit(u)
  if h.scheme!='https' or h.hostname!=urlsplit(p['root_url']).hostname or not permitted(v,u):continue
  if re.search(p['inventory_link_pattern'],h.path):
   if u not in routes:routes.append(u)
  elif re.search(p['article_link_pattern'],h.path):
   loc=re.search(r'/(\d{4})/(\d{2})(?:/|(\d{2})/)',h.path);year=re.search(r'/(\d{4})/',h.path)
   month=loc[1]+'-'+loc[2] if loc else ''
   if year and not '1988'<=year[1]<='2026':continue
   items.append(dict(source_id=p['source_id'],url=u,representation='publisher_evidenced_archive_HTML',month=month,native_evidence={'title':a.get_text(' ',strip=True),'native_inventory_receipt':rec['target_id'],'native_inventory_URL':url,'locator_date_not_publication_date':True}))
 queue(p['source_id'],items);v.update(stage='native_archive_HTML',attempted_pages=v.get('attempted_pages',0)+1,last_inventory_receipt=rec['target_id']);return 1

def parse(raw,sid,url,metadata=None):
 import broaden,extract_load
 p=next(p for p in broaden.profiles() if p['source_id']==sid);adapter=extract_load.ADAPTERS[sid];soup=BeautifulSoup(raw,'html.parser');title=soup.select(p.get('title_selector','h1'));title=title[0].get_text(' ',strip=True) if len(title)==1 else None;day=None;date_fields=[]
 if p.get('date_method')=='MIA_source_publication':
  info=soup.select(p['source_metadata_selector']);text=' '.join(n.get_text(' ',strip=True) for n in info);m=re.search(r'Source:\s*Militant\s*\(([A-Za-z]+\s+\d{1,2},\s*\d{4})\)',text)
  if m:
   try:day=dt.datetime.strptime(m[1],'%B %d, %Y').date().isoformat();date_fields=[['archival Source Militant publication date',m[1]]]
   except ValueError:pass
  source_version=None
 else:
  day,field,stamp,date_fields=extract_load.date(soup,sid);source_version=None
 record=dict(article_id=elt.article_id(sid,url),source_id=sid,source=adapter['title'],source_url=url,raw_source_url=url,url_aliases=[url],title=title,publication_date=day,date_field=date_fields[0][0] if date_fields else None,observed_date_fields=date_fields,content_version_time=source_version,archive_source_metadata=(text if p.get('date_method')=='MIA_source_publication' else None),archive_transcription_year=(int(re.search(r'Transcription:.*?(\d{4})',text)[1]) if p.get('date_method')=='MIA_source_publication' and re.search(r'Transcription:.*?(\d{4})',text) else None),stratum=adapter['stratum'],country=adapter['country'],edition=adapter['edition'],source_frame=adapter['frame'],provenance=p.get('provenance','direct publisher archived newspaper original HTML; quotation origins separate'),historical_body_equivalence='unknown; retrieved rendition; archival transcription/markup details retained separately',retention_limit=p['retention_limit'],semantic_labels_executed=False,length_filter_used=False)
 if metadata:record.update(metadata)
 nodes=soup.select(p['body_selector'])
 if not nodes or (p.get('single_body_container',True) and len(nodes)!=1):return record,'','pending_missing_or_nonunique_original_article_body'
 for node in nodes:
  for n in node.select('script,style,form,svg,nav,aside,.related-posts,.sharedaddy'):n.decompose()
 body=elt.renderer.normalise('\n\n'.join(elt.renderer.render(n) for n in nodes));record['body_boundary']=p['body_selector'];record['article_boundary_evidence']='Source-specific original article body/title/date mapping; entire prose order retained, archive/index/metadata/navigation excluded'
 if any(n.select('.paywall,.subscription-wall,.article-preview') for n in nodes):return record,body,'pending_visible_source_preview_or_paywall'
 if not title or not body.strip():return record,body,'pending_empty_original_body_or_identity'
 if not elt.eligible(day):return record,body,'pending_missing_or_outside_publication_date'
 if re.search(r'\b(?:excerpt|extract from)\b',p.get('explicit_completeness_limit',''),re.I):return record,body,'pending_explicit_archival_excerpt'
 return record,body,'confirmed_complete'
