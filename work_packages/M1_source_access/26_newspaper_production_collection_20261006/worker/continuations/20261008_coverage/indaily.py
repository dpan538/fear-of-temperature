"""InDaily's evidenced news subframe, kept separate from other site titles."""
import json,re,urllib.robotparser
from bs4 import BeautifulSoup
import elt

FRAME=dict(title='InDaily',country='AU',stratum='AU',edition='South Australian newspaper-brand digital successor; Independent Weekly print/digital break retained',frame='InDaily regional digital newspaper successor; CityMag, SALIFE and InReview excluded',selectors=[],exclude=[])
NEWS=re.compile(r'^https://www\.indailysa\.com\.au/news/[^/]+/(\d{4})/(\d{2})/(\d{2})/[^/?]+/?$')
INDEX=elt.BASE/'raw/df815679c432d1431d915a46.bin'
POLICIES=elt.REPO/'work_packages/M1_source_access/22_real_payload_acquisition_20261005/media/raw'

def permitted(url):
 host=elt.urlsplit(url).hostname
 if host=='www.indailysa.com.au' and NEWS.fullmatch(url):rid='5b677aaa0f09e7d820f2e856'
 elif host=='assets.indailysa.com.au' and re.fullmatch(r'/sitemaps/news-indailysa/posts/post-\d+\.xml',elt.urlsplit(url).path):rid='37fc8a77a36a6e560ca0ae76'
 else:return False
 robot=urllib.robotparser.RobotFileParser();robot.parse((POLICIES/(rid+'.bin')).read_text().splitlines())
 return robot.can_fetch('FearOfTemperatureResearch/1.0',url)

def parse(raw,url,metadata=None):
 soup=BeautifulSoup(raw,'html.parser');h=soup.find('h1');title=h.get_text(' ',strip=True) if h else ''
 canonical=soup.select_one('link[rel="canonical"]');canonical=canonical.get('href') if canonical else url
 pub=soup.select_one('meta[property="article:published_time"]');mod=soup.select_one('meta[property="article:modified_time"]')
 stamp=pub.get('content') if pub else None;day=stamp[:10] if stamp else None
 match=NEWS.fullmatch(url);url_day='-'.join(match.groups()) if match else None
 sidebar=soup.select_one('[data-location="article-sidebar"]')
 names=sidebar.select('a.block[href*="/contributor/"]') if sidebar else []
 record=dict(article_id=elt.article_id('indaily',canonical),source_id='indaily',source='InDaily',source_url=canonical,raw_source_url=url,url_aliases=sorted({url,canonical}),title=title,publication_date=day,date_field='meta article:published_time',publisher_timestamp=stamp,content_version_time=mod.get('content') if mod else None,url_date=url_day,stratum='AU',country='AU',edition=FRAME['edition'],source_frame=FRAME['frame'],byline=';'.join(dict.fromkeys(n.get_text(' ',strip=True) for n in names)),publisher_sidebar_metadata=sidebar.get_text(' ',strip=True) if sidebar else '',genre=elt.urlsplit(url).path.split('/')[2] if match else None,provenance='direct evidence of InDaily newspaper-brand publication; quotations and syndicated origins separately recorded',historical_body_equivalence='unknown; current archive rendition may include later publisher updates',retention='bounded local research evidence; copyright retained; no open grant or public raw redistribution assumed',semantic_labels_executed=False,length_filter_used=False)
 if metadata:record.update(metadata)
 containers={}
 for p in soup.select('p.mb-4'):
  node=p.find_parent('div',class_='relative')
  if node and 'overflow-hidden' in node.get('class',[]):containers[id(node)]=node
 if len(containers)!=1:return record,'','pending_missing_or_nonunique_body'
 node=next(iter(containers.values()))
 if node.select('.paywall,.subscription-wall,.article-preview'):return record,'','pending_visible_preview_or_paywall'
 lead=h.find_next_sibling('div') if h else None
 for child in list(node.find_all('div',recursive=False)):
  if ('border-y' in child.get('class',[]) and child.get_text(' ',strip=True).startswith('You might like')) or (child.find('form') and child.find('h1')):child.decompose()
 for child in node.select('script,style,svg,form'):child.decompose()
 body=elt.renderer.normalise((elt.renderer.render(lead) if lead else '')+'\n\n'+elt.renderer.render(node))
 record.update(body_boundary='headline-adjacent standfirst plus unique native div.relative.overflow-hidden article prose; observed related/newsletter modules removed',paragraph_count=len(node.select('p')),table_count=len(node.select('table')),syndication_notices=[p.get_text(' ',strip=True) for p in node.select('p') if re.search(r'first published|republished',p.get_text(),re.I)])
 if not permitted(url) or not NEWS.fullmatch(canonical) or elt.canon(url)!=elt.canon(canonical):return record,body,'pending_news_subframe_or_identity_mapping'
 if not title or not body:return record,body,'pending_empty_body_or_identity'
 if not elt.eligible(day):return record,body,'pending_date_or_outside_fixed_interval'
 if url_day and url_day[:7]!=day[:7]:return record,body,'pending_cross_month_date_conflict'
 if url_day!=day:record['date_limit']='Native date and URL day differ within the same supported month'
 record['article_boundary_evidence']='One native headline/date/permalink mapped to the entire unique article prose container and standfirst in source order; observed related/newsletter modules removed; no length or topic gate'
 return record,body,'confirmed_complete'

def discover(o,queue):
 # This source's asset host has an inherited 403. Retained discovery metadata
 # can supply unused links without retrying the stopped network interface.
 if 'assets.indailysa.com.au' in elt.state()['access_stops']:
  if 'indaily_retained_sitemaps' not in o['routes']:
   rows=[json.loads(s) for s in (elt.BASE/'REQUESTS.jsonl').read_text().splitlines() if s]
   o['routes']['indaily_retained_sitemaps']=[{k:r[k] for k in ['url','raw_path','raw_sha256','request_id']} for r in rows if r['purpose']=='au_sitemap' and r['status']=='saved' and permitted(r['url'])]
   o['cursors']['indaily_retained_sitemaps']=0
   elt.save('INDAILY_ACTIVATION.json',dict(at_utc=elt.utc(),source_id='indaily',stratum='AU',additional_parent_families_activated=1,acquisition_parent='https://www.indailysa.com.au/news',scope=FRAME['frame'],blocked_asset_host_preserved=True,retained_sitemap_count=len(o['routes']['indaily_retained_sitemaps']),retained_metadata_only=True,new_sitemap_HTTP_requests=0,full_period_archive_claim=False,successor_registry_reference=str((elt.BASE/'SOURCE_REGISTRY_SUCCESSOR.json').relative_to(elt.REPO))))
  key='indaily_retained_sitemaps';i=o['cursors'][key]
  if i>=len(o['routes'][key]):return 0
  r=o['routes'][key][i];items=[]
  for n in BeautifulSoup((elt.BASE/r['raw_path']).read_bytes(),'xml').find_all('loc'):
   u=n.get_text();m=NEWS.fullmatch(u)
   if m and permitted(u) and elt.eligible('-'.join(m.groups())):items.append(dict(source_id='indaily',url=u,month='-'.join(m.groups())[:7],native_evidence={'frozen_native_sitemap_reference':str((elt.BASE/r['raw_path']).relative_to(elt.REPO)),'raw_sha256_reused':r['raw_sha256'],'URL_date':'-'.join(m.groups()),'retained_discovery_request_id':r['request_id']}))
  queue('indaily',items);o['cursors'][key]+=1
  return 1
 if 'indaily' not in o['routes']:
  soup=BeautifulSoup(INDEX.read_bytes(),'xml')
  o['routes']['indaily']=[n.get_text() for n in soup.find_all('loc') if permitted(n.get_text())]
  o['cursors']['indaily']=0
  elt.save('INDAILY_ACTIVATION.json',dict(at_utc=elt.utc(),source_id='indaily',stratum='AU',additional_parent_families_activated=1,acquisition_parent='https://assets.indailysa.com.au/sitemaps/news-indailysa/sitemap.xml',retained_index_reference=str(INDEX.relative_to(elt.REPO)),retained_index_sha256='69546bad2bce3f2fef4d36f45e576ef37389dbd705586b402aea7afab19d4785',observed_sitemap_routes=len(o['routes']['indaily']),robots_references=[str((POLICIES/(r+'.bin')).relative_to(elt.REPO)) for r in ['5b677aaa0f09e7d820f2e856','37fc8a77a36a6e560ca0ae76']],source_registry_reference=elt.SCOPE['source_registry_reference'],successor_registry_reference=str((elt.BASE/'SOURCE_REGISTRY_SUCCESSOR.json').relative_to(elt.REPO)),scope=FRAME['frame'],full_period_archive_claim=False,old_sitemap_selection_limits_reused=False))
 i=o['cursors']['indaily'];routes=o['routes']['indaily']
 if i>=len(routes):return 0
 url=routes[i];o['cursors']['indaily']+=1
 rec=elt.fetch(url,'indaily','AU','discovery',{'observed_native_index_reference':str(INDEX.relative_to(elt.REPO)),'native_route_index':i})
 if rec['status']=='saved':
  items=[]
  for n in BeautifulSoup(elt.read_payload(rec['raw_reference']),'xml').find_all('loc'):
   u=n.get_text();m=NEWS.fullmatch(u)
   if m and permitted(u) and elt.eligible('-'.join(m.groups())):items.append(dict(source_id='indaily',url=u,month='-'.join(m.groups())[:7],native_evidence={'native_sitemap_reference':rec['raw_reference'],'URL_date':'-'.join(m.groups()),'discovery_target_id':rec['target_id']}))
  queue('indaily',items)
 return 1
