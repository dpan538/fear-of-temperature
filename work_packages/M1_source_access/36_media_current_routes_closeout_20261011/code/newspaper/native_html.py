"""Observed Camden publisher HTML and public sitemap/category frontiers; no private API."""
import json,re,datetime,xml.etree.ElementTree as ET
from urllib.parse import urlsplit,urljoin
from bs4 import BeautifulSoup
import elt

def article_targets(data,p,url,receipt):
 soup=BeautifulSoup(data,'html.parser');items=[];seen=set()
 for a in soup.select('a[href]'):
  target=urljoin(url,a['href']);u=urlsplit(target)
  if u.scheme!='https' or u.hostname!=urlsplit(p['root_url']).hostname or not u.path.startswith('/article/') or target in seen:continue
  seen.add(target);items.append(dict(source_id=p['source_id'],url=target,representation='publisher_camden_native_html',month='',native_evidence=dict(title=a.get_text(' ',strip=True),native_index_receipt=receipt.get('target_id'),publication_date_assignment='Pending independent native displayed article date; index snapshot and lastmod are not publication dates')))
 return items

def discover(p,v,queue,fetch,permitted,policy):
 stage=v.get('stage','robots')
 if stage=='robots':policy(p,v);return 1
 if stage=='native_root':
  rec=fetch(p,p['root_url'],{'native_newspaper_frame':p['title_classification_reference'],'public_HTML_interface':True})
  if rec['status']!='saved':v.update(stage='blocked',blocked_reason='Public publisher root '+rec['status']);return 1
  data=elt.read_payload(rec['raw_reference']);soup=BeautifulSoup(data,'html.parser');queue(p['source_id'],article_targets(data,p,p['root_url'],rec))
  routes=[]
  if v.get('robots_raw_reference'):
   text=elt.read_payload(v['robots_raw_reference']).decode('utf-8',errors='replace')
   routes+=re.findall(r'^Sitemap:\s*(https://\S+)',text,re.M|re.I)
  routes += [urljoin(p['root_url'],n['href']) for n in soup.select('link[rel="sitemap"][href]')]
  if not routes:routes=[urljoin(p['root_url'],'sitemap.xml')]
  v.update(stage='native_xml',native_root_receipt=rec['target_id'],xml_routes=list(dict.fromkeys(routes)),xml_consumed=[],category_routes=list(dict.fromkeys(urljoin(p['root_url'],a['href']) for a in soup.select('a[href]') if urlsplit(urljoin(p['root_url'],a['href'])).hostname==urlsplit(p['root_url']).hostname and urlsplit(urljoin(p['root_url'],a['href'])).path.startswith('/category/'))),category_consumed=[],queued_native_article_URLs=[],native_sitemap_standard='https://www.sitemaps.org/protocol.html',standard_sitemap_probe_is_not_a_private_API=True)
  return 1
 if stage=='native_xml':
  todo=[u for u in v['xml_routes'] if u not in v['xml_consumed']]
  if not todo:v['stage']='native_categories';return 1
  url=todo[0];v['xml_consumed'].append(url)
  if urlsplit(url).hostname!=urlsplit(p['root_url']).hostname or not permitted(v,url):v.setdefault('unpermitted_xml_routes',[]).append(url);return 1
  rec=fetch(p,url,{'public_native_sitemap':True,'standard':v['native_sitemap_standard'],'publication_time_not_inferred_from_lastmod':True})
  if rec['status']!='saved':v.setdefault('xml_access_limits',[]).append({'url':url,'status':rec['status']});return 1
  try:tree=ET.fromstring(elt.read_payload(rec['raw_reference']))
  except ET.ParseError:v.setdefault('xml_access_limits',[]).append({'url':url,'status':'not_native_sitemap_XML'});return 1
  items=[]
  if tree.tag.split('}')[-1]=='sitemapindex':
   for loc in tree.findall('.//{*}loc'):
    if loc.text and urlsplit(loc.text).hostname==urlsplit(p['root_url']).hostname and loc.text not in v['xml_routes']:v['xml_routes'].append(loc.text)
  elif tree.tag.split('}')[-1]=='urlset':
   for node in tree.findall('{*}url'):
    loc=node.find('{*}loc');last=node.find('{*}lastmod');u=loc.text if loc is not None else None
    if not u or urlsplit(u).scheme!='https' or urlsplit(u).hostname!=urlsplit(p['root_url']).hostname or not urlsplit(u).path.startswith('/article/'):continue
    items.append(dict(source_id=p['source_id'],url=u,representation='publisher_camden_native_html',month='',native_evidence=dict(native_sitemap_receipt=rec['target_id'],native_lastmod_observed=last.text if last is not None else None,publication_date_assignment='Pending source displayed article date; lastmod retained as version metadata only')))
   queue(p['source_id'],items);v['queued_native_article_URLs']=sorted(set(v['queued_native_article_URLs'])|{t['url'] for t in items})
  else:v.setdefault('xml_access_limits',[]).append({'url':url,'status':'not_sitemapindex_or_urlset'})
  v['attempted_pages']=v.get('attempted_pages',0)+1;return 1
 if stage=='native_categories':
  todo=[u for u in v['category_routes'] if u not in v['category_consumed']]
  if not todo:v.update(stage='observed_public_frontier_consumed',reason='Observed public native sitemap/category href frontier consumed; not certified archive exhaustion or private pagination permission');return 1
  url=todo[0];v['category_consumed'].append(url)
  if not permitted(v,url):v.setdefault('unpermitted_categories',[]).append(url);return 1
  rec=fetch(p,url,{'observed_native_category_href':True,'no_hidden_or_private_pagination_guessed':True})
  if rec['status']=='saved':
   data=elt.read_payload(rec['raw_reference']);items=article_targets(data,p,url,rec);queue(p['source_id'],items);v['queued_native_article_URLs']=sorted(set(v['queued_native_article_URLs'])|{t['url'] for t in items})
   soup=BeautifulSoup(data,'html.parser')
   for n in soup.select('a[rel="next"][href]'):
    next_url=urljoin(url,n['href'])
    if urlsplit(next_url).hostname==urlsplit(p['root_url']).hostname and next_url not in v['category_routes']:v['category_routes'].append(next_url)
  else:v.setdefault('category_access_limits',[]).append({'url':url,'status':rec['status']})
  v['attempted_pages']=v.get('attempted_pages',0)+1;return 1
 return 0

def parse(raw,sid,url,metadata=None):
 import extract_load
 p=extract_load.ADAPTERS[sid];soup=BeautifulSoup(raw,'html.parser');titles=soup.select('article.Article__container h1');dates=soup.select('article.Article__container .ArticlePublishInfo');nodes=soup.select('article.Article__container .Article__content')
 title=titles[0].get_text(' ',strip=True) if len(titles)==1 else None;stamp=dates[0].get_text(' ',strip=True) if len(dates)==1 else None;day=None
 match=re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})\b',stamp or '')
 if match:
  try:
   value=datetime.datetime.strptime(' '.join(match.groups()[1:]),'%d %B %Y').date()
   if value.strftime('%A')==match[1]:day=value.isoformat()
  except ValueError:pass
 record=dict(article_id=elt.article_id(sid,url),source_id=sid,source=p['title'],source_url=url,raw_source_url=url,url_aliases=[url],title=title,publication_date=day,date_field='Unique original ArticlePublishInfo displayed weekday/day/month/year',publisher_timestamp=stamp,observed_date_fields=[['native ArticlePublishInfo',stamp]],content_version_time=None,stratum=p['stratum'],country=p['country'],edition=p['edition'],source_frame=p['frame'],provenance='direct publisher original newspaper web article; quotation origins and claim truth separate',historical_body_equivalence='unknown; current retrieved archive representation',semantic_labels_executed=False,length_filter_used=False,retention_limit=p.get('retention_limit'))
 if metadata:record.update(metadata)
 if len(nodes)!=1:return record,'','pending_missing_or_nonunique_original_article_body'
 node=nodes[0]
 for n in node.select('script,style,form,svg,nav,aside'):n.decompose()
 body=elt.renderer.normalise(elt.renderer.render(node));record.update(body_boundary='Unique article.Article__container .Article__content; entire source paragraph order',article_boundary_evidence='Unique native newspaper article title, full content container and displayed publication date; site headings and index snapshot dates excluded',paragraph_count=len(node.select('p')))
 if node.select('.paywall,.subscription-wall,.article-preview'):return record,body,'pending_visible_source_preview_or_paywall'
 if not body or not title:return record,body,'pending_empty_original_body_or_identity'
 if not elt.eligible(day):return record,body,'pending_missing_conflicting_or_outside_fixed_publication_date'
 return record,body,'confirmed_complete'
