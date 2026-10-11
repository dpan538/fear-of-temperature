"""Publisher-evidenced native HTML/sitemaps for the Cambridge newspaper theme."""
import re,json,xml.etree.ElementTree as ET
from urllib.parse import urlsplit,urljoin
from bs4 import BeautifulSoup,Comment
import elt

def native_article_url(p,url):
 u=urlsplit(url);m=re.fullmatch(r'/(\d{4})/(\d{2})/([^/]+)/',u.path)
 return u.scheme=='https' and u.hostname==urlsplit(p['root_url']).hostname and bool(m) and '1988-01'<=m[1]+'-'+m[2]<='2026-09'

def targets(p,urls,rec):
 return [dict(source_id=p['source_id'],url=u,article_url=u,representation='publisher_evidenced_wp_theme_HTML',month=urlsplit(u).path[1:8].replace('/','-'),native_evidence=dict(native_inventory_receipt=rec['target_id'],original_body_mapping_reference=p['native_mapping_receipt'],publication_time_assignment='Article native displayed/meta and matching source Article JSON-LD dates required; sitemaplastmod is not publication date')) for u in dict.fromkeys(urls) if native_article_url(p,u)]

def discover(p,v,queue,fetch,permitted,policy):
 stage=v.get('stage','robots')
 if stage=='robots':policy(p,v);return 1
 if stage=='native_root':
  rec=fetch(p,p['root_url'],{'verified_original_newspaper_frame':p['title_classification_reference'],'publisher_native_HTML_not_guessed_API':True})
  if rec['status']!='saved':v.update(stage='blocked',blocked_reason='Observed native root '+rec['status']);return 1
  soup=BeautifulSoup(elt.read_payload(rec['raw_reference']),'html.parser');queue(p['source_id'],targets(p,[urljoin(p['root_url'],a['href']) for a in soup.select('a[href]')],rec))
  text=elt.read_payload(v['robots_raw_reference']).decode('utf8',errors='replace') if v.get('robots_raw_reference') else ''
  routes=re.findall(r'^Sitemap:\s*(https://\S+)',text,re.M|re.I)
  v.update(stage='native_sitemap',xml_routes=list(dict.fromkeys(routes)),xml_consumed=[],queued_native_article_URLs=[],native_root_receipt=rec['target_id'],whole_archive_exhaustion=False)
  if not routes:v.update(stage='observed_public_frontier_consumed',reason='No advertised public sitemap; no hidden routes guessed')
  return 1
 if stage=='native_sitemap':
  todo=[u for u in v['xml_routes'] if u not in v['xml_consumed']]
  if not todo:v.update(stage='observed_public_frontier_consumed',reason='Observed publisher sitemap hrefs consumed; article surplus remains queued, historical population unknown',whole_archive_exhaustion=False);return 1
  url=todo[0];v['xml_consumed'].append(url)
  if urlsplit(url).hostname!=urlsplit(p['root_url']).hostname or not permitted(v,url):v.setdefault('source_access_limits',[]).append(dict(url=url,status='declared_agent_route_disallowed'));return 1
  rec=fetch(p,url,{'publisher_advertised_native_sitemap':True,'publication_date_not_inferred_from_lastmod':True,'standard':'https://www.sitemaps.org/protocol.html'})
  if rec['status']!='saved':v.setdefault('source_access_limits',[]).append(dict(url=url,status=rec['status']));return 1
  try:tree=ET.fromstring(elt.read_payload(rec['raw_reference']))
  except ET.ParseError:v.setdefault('source_access_limits',[]).append(dict(url=url,status='not_native_sitemap_XML'));return 1
  urls=[n.text for n in tree.findall('.//{*}loc') if n.text]
  if tree.tag.split('}')[-1]=='sitemapindex':
   for u in urls:
    if urlsplit(u).hostname==urlsplit(p['root_url']).hostname and '/post-sitemap' in urlsplit(u).path and u not in v['xml_routes']:v['xml_routes'].append(u)
  elif tree.tag.split('}')[-1]=='urlset':
   items=targets(p,urls,rec);queue(p['source_id'],items);v['queued_native_article_URLs']=sorted(set(v['queued_native_article_URLs'])|{t['url'] for t in items})
  else:v.setdefault('source_access_limits',[]).append(dict(url=url,status='not_sitemapindex_or_urlset'))
  v['attempted_pages']=v.get('attempted_pages',0)+1;return 1
 return 0

def parse(raw,sid,url,metadata=None):
 import extract_load
 p=extract_load.ADAPTERS[sid];soup=BeautifulSoup(raw,'html.parser');nodes=soup.select('main .single-post > .entry');titles=soup.select('main .single-post > h1');canonical=soup.select('link[rel="canonical"]');dates=soup.select('meta[property="article:published_time"]');postids=[re.fullmatch(r'postid-(\d+)',x)[1] for x in (soup.body.get('class',[]) if soup.body else []) if re.fullmatch(r'postid-(\d+)',x)]
 record=dict(source_id=sid,source=p['title'],source_url=url,raw_source_url=url,url_aliases=[url],stratum=p['stratum'],country=p['country'],edition=p['edition'],source_frame=p['frame'],retention_limit=p['retention_limit'],provenance='direct original newspaper publisher HTML representation; source reprints/quotations separate',content_version_time=None,historical_body_equivalence='unknown; current retrieved archive rendition',semantic_labels_executed=False,length_filter_used=False)
 if metadata:record.update(metadata)
 if any(len(x)!=1 for x in [nodes,titles,canonical,dates,postids]):return record,'','pending_missing_or_nonunique_native_article_mapping'
 title=titles[0].get_text(' ',strip=True);stamp=dates[0].get('content','');day=stamp[:10];link=canonical[0].get('href');objects=[]
 for node in soup.select('script[type="application/ld+json"]'):
  try:obj=json.loads(node.string or node.get_text());objects+=obj if isinstance(obj,list) else obj.get('@graph',[obj])
  except ValueError:continue
 articles=[o for o in objects if isinstance(o,dict) and o.get('@type')=='Article' and o.get('@id')==url+'#article']
 record.update(article_id=sid+':article:'+postids[0],source_native_article_id=postids[0],native_identity_basis='Unique publisher HTML body postid-class and matching canonical/permalink/Article JSON-LD identity',title=title,publication_date=day,publisher_timestamp=stamp,date_field='Unique original article:published_time agrees with matching canonical source Article JSON-LD datePublished and permalink month',body_boundary='Unique main .single-post > .entry contains complete native copy and captions; site navigation/sidebar/header excluded',article_boundary_evidence='Named original title, one complete original entry container and persistent publisher native ID/date/canonical binding',observed_author=articles[0].get('author') if len(articles)==1 else None,publisher_native_genre=articles[0].get('articleSection') if len(articles)==1 else None)
 node=nodes[0]
 for n in node.find_all(string=lambda t:isinstance(t,Comment)):n.extract()
 for n in node.select('script,style,form,svg,nav,aside'):n.decompose()
 body=elt.renderer.normalise(elt.renderer.render(node));record['paragraph_count']=len(node.select('p'))
 if not title or not body:return record,body,'pending_missing_native_headline_or_body'
 if len(articles)!=1 or articles[0].get('headline')!=title or articles[0].get('datePublished')!=stamp or elt.canon(link or '')!=elt.canon(url) or urlsplit(url).path[1:8].replace('/','-')!=day[:7]:return record,body,'pending_conflicting_native_identity_date_mapping'
 if node.select('.paywall,.subscription-wall,.article-preview'):return record,body,'pending_visible_preview_or_paywall'
 if not elt.eligible(day):return record,body,'pending_publication_date_outside_fixed_interval'
 return record,body,'confirmed_complete'
