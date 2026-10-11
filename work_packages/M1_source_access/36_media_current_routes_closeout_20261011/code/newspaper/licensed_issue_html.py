"""Ordinary licensed About Time HTML issues -> complete native text, one writer."""
import json,re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
import elt,broaden,publication_precision
from fear_temperature.media_planning.core import Opportunity
SID='about_time';STATE='ABOUT_TIME_HTML_STATE.json';HOST='www.abouttime.org.au'
def profile():return next((p for p in broaden.profiles() if p['source_id']==SID and p.get('acquisition_adapter')=='licensed_issue_html' and broaden.approved(p)),None)
def state():
 p=elt.OWN/STATE;return json.loads(p.read_text()) if p.exists() else {'issues':{},'articles':{},'entry_attempted':False}
def rules():
 p=elt.OWN/'ABOUT_TIME_PARSER_RULES.json';return json.loads(p.read_text()) if p.exists() else {}
def rule_digest():return elt.sha(json.dumps(rules(),sort_keys=True).encode())
def needs_entry():
 s=state()
 return not s['entry_attempted'] or bool(rules().get('body_selector') and any(v['stage']=='pending_named_public_HTML_article_boundary' and v.get('parser_rule_digest')!=rule_digest() for v in s['articles'].values()))
def save(s):
 elt.save(STATE,s)
 o=broaden._state();o[SID]=dict(stage='licensed_native_HTML_issue_frontier',queued_native_article_IDs=sorted(s['articles']),issue_stage_counts={stage:sum(v['stage']==stage for v in s['issues'].values()) for stage in {v['stage'] for v in s['issues'].values()}},no_API_or_PDF_route=True,publication_precision='month retained; partial cutoff month unresolved without day evidence');broaden._save(o)
def parsed_month(text):
 import datetime as dt
 found=re.findall(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b',text,re.I)
 values={dt.datetime.strptime(month.title()+' '+year,'%B %Y').strftime('%Y-%m') for month,year in found}
 return next(iter(values)) if len(values)==1 else None
def prepare():
 if not profile():return
 s=state()
 if s['issues']:return
 rec=elt._receipt('686df1a19bb368935365cb88');assert rec['source_id']==SID and rec['status']=='saved';soup=BeautifulSoup(elt.read_payload(rec['raw_reference']),'html.parser')
 for a in soup.select('a[href]'):
  if not a.get_text(' ',strip=True).startswith('Website View'):continue
  parent=a.find_parent(class_='w-dyn-item')
  if not parent:continue
  month=parsed_month(parent.get_text(' ',strip=True));url=urljoin(rec['url'],a['href'])
  if urlsplit(url).hostname!=HOST or not month:continue
  low,high=publication_precision.bounds(month);stage='queued' if publication_precision.LOW<=low<=high<=publication_precision.HIGH else 'partial_or_outside_fixed_interval'
  s['issues'][url]=dict(url=url,month=month,stage=stage,index_request_id=rec['target_id'],index_raw_reference=rec['raw_reference'],index_raw_sha256=rec['raw_sha256'],issue_container_not_article=True)
 # Exact saved first issue supersedes only its HTTP/HTTPS interface alias.
 first='https://www.abouttime.org.au/past-editions/issue-no-1'
 for url in list(s['issues']):
  if urlsplit(url).path.rstrip('/')==urlsplit(first).path:s['issues'][first]=dict(s['issues'].pop(url),url=first)
 save(s)
def collect_issue(entry):
 s=state();url=entry['url'];allowed,policy=broaden.metadata_permission(dict(source_id=SID,stratum='AU',url=url))
 if not allowed:s['issues'][url].update(stage='blocked',access_limit=policy);save(s);return
 rec=elt.fetch(url,SID,'AU','discovery',{'purpose':'Publisher-native licensed newspaper issue inventory; individual links and printed sections, not one article or a PDF','observed_index_request_id':entry['index_request_id']})
 if rec['status']!='saved':s['issues'][url].update(stage='blocked',receipt_id=rec['target_id'],reason=rec['status']);save(s);return
 soup=BeautifulSoup(elt.read_payload(rec['raw_reference']),'html.parser');months={parsed_month(n.get_text(' ',strip=True)) for n in soup.select('.at-h3-martina-caps,.at-h3-martina-mobile-header-allcaps')};months.discard(None)
 if months!={entry['month']}:s['issues'][url].update(stage='pending_native_issue_date_mapping',observed_months=sorted(months),receipt_id=rec['target_id']);save(s);return
 genre=None
 for n in soup.find_all(['h2','a']):
  if n.name=='h2' and 'at-h2-rom-sectionheadings' in n.get('class',[]):genre=n.get_text(' ',strip=True)
  if n.name!='a' or not n.get('href') or not n.find_parent(class_='w-dyn-item') or not n.find(['h1','h2','h3','h4']):continue
  if not any(c.startswith('at-header-link') for c in n.get('class',[])):continue
  link=urljoin(rec.get('final_url',url),n['href']);title=n.get_text(' ',strip=True)
  if urlsplit(link).hostname!=HOST or urlsplit(link).path.startswith(('/past-editions','/issue-no-')):continue
  aid=elt.article_id(SID,link);proof=dict(publisher_issue_url=url,publisher_issue_request_id=rec['target_id'],publisher_issue_raw_reference=rec['raw_reference'],publisher_issue_raw_sha256=rec['raw_sha256'],observed_publication_month=entry['month'])
  if aid in s['articles']:
   s['articles'][aid].setdefault('additional_issue_links',[]).append(proof);continue
  s['articles'][aid]=dict(article_id=aid,url=link,title=title,month=entry['month'],publisher_native_genre=genre,publication_date_reference=proof,stage='queued')
 s['issues'][url].update(stage='inventory_saved',receipt_id=rec['target_id'],raw_reference=rec['raw_reference']);save(s)
def acquire(entry):
 p=profile();s=state();allowed,policy=broaden.metadata_permission(dict(source_id=SID,stratum='AU',url=entry['url']))
 if not allowed:s['articles'][entry['article_id']].update(stage='blocked',access_limit=policy);save(s);return
 rec=elt.fetch(entry['url'],SID,'AU','article',{'publisher_issue_month':entry['month'],'publisher_issue_evidence':entry['publication_date_reference'],'ordinary_original_HTML_no_assets_API_accounts_or_PDF':True})
 if rec['status']!='saved':s['articles'][entry['article_id']].update(stage='blocked',request_id=rec['target_id'],reason=rec['status']);save(s);return
 soup=BeautifulSoup(elt.read_payload(rec['raw_reference']),'html.parser');cfg=rules();canonical=soup.select_one('link[rel="canonical"][href]');titles=[n for n in soup.select(cfg.get('title_selector','h1,h2,h3')) if n.get_text(' ',strip=True)==entry['title']]
 nodes=soup.select(cfg['body_selector']) if cfg.get('body_selector') else [];status='confirmed_complete';body='';author=None
 if not canonical or elt.canon(canonical['href'])!=elt.canon(entry['url']) or not titles:status='pending_native_HTML_title_identity_mapping'
 elif len(nodes)!=1:status='pending_named_public_HTML_article_boundary'
 else:
  node=BeautifulSoup(str(nodes[0]),'html.parser')
  for n in node.select('script,style,form,svg'):n.decompose()
  body=node.get_text('\n',strip=True)
  content=BeautifulSoup(str(nodes[0]),'html.parser')
  for n in content.select('script,style,form,svg,h1,h2,h3,h4,h5,h6,figure,picture,table'):n.decompose()
  if not any(c.isalnum() for c in content.get_text()):status='pending_image_heading_or_nontext_native_unit'
 if cfg.get('author_selector'):
  author='; '.join(dict.fromkeys(n.get_text(' ',strip=True) for n in soup.select(cfg['author_selector']) if n.get_text(' ',strip=True))) or None
 if status=='confirmed_complete':
  months={parsed_month(n.get_text(' ',strip=True)) for n in soup.select(cfg.get('publication_month_selector','.__owner_mapping_required__'))};months.discard(None)
  if months!={entry['month']}:status='pending_native_article_issue_month_or_version_mapping'
  if not author:status='pending_published_author_attribution_mapping'
 low,high=publication_precision.bounds(entry['month']);record=dict(article_id=entry['article_id'],source_id=SID,source=p['title'],source_url=entry['url'],raw_source_url=rec['url'],title=entry['title'],publication_date=entry['month'],publication_date_precision='month',publication_date_lower_bound=low,publication_date_upper_bound=high,publication_date_reference=entry['publication_date_reference'],date_field='Explicit native newspaper issue month; article title/event month not used; no day imputation',observed_author=author,author_country='unknown',publisher_native_genre=entry.get('publisher_native_genre'),publisher_genre_basis='Printed section heading on saved native issue HTML; no semantic model',stratum='AU',country='AU',edition='Specialized prison newspaper native HTML issue-linked article',source_frame=p['source_frame'],raw_reference=rec['raw_reference'],raw_sha256=rec['raw_sha256'],request_id=rec['target_id'],retrieved_at_utc=rec['finished_at_utc'],body_boundary=cfg.get('body_selector'),article_boundary_evidence='Distinct native article permalink/title linked from dated publisher issue; issue and header/footer are separate',provenance='direct publisher newspaper representation; individually credited reprints/quoted origins remain separate',content_version_time=None,historical_body_equivalence='unknown; current retrieved representation',retention_limit=p['retention_limit'],text_licence='CC BY-NC-ND 4.0 publisher text grant; images excluded',text_licence_URL='https://www.abouttime.org.au/republishing-us',required_republication_notice='This work is republished under a Creative Commons BY-NC-ND 4.0 licence from About Time.',original_HTML_preserved=True,body_derivation='Local structural HTML-to-text; immutable original retained separately; no public derived-text redistribution',semantic_labels_executed=False)
 if not publication_precision.eligible_record(record):status='pending_month_precision_fixed_cutoff'
 result=elt.load(record,body,status);s['articles'][entry['article_id']].update(stage=result['load_status'],request_id=rec['target_id'],raw_reference=rec['raw_reference'],parser_rule_digest=rule_digest());s['entry_attempted']=True;save(s)
def enter_one():
 if not profile():return 0
 prepare();s=state()
 if s['entry_attempted']:
  pending=[v for v in s['articles'].values() if v['stage']=='pending_named_public_HTML_article_boundary' and v.get('parser_rule_digest')!=rule_digest()]
  if rules().get('body_selector') and pending:acquire(pending[0]);return 1
  return 0
 queued=[x for x in s['articles'].values() if x['stage']=='queued']
 if queued:acquire(min(queued,key=lambda x:(x['month'],x['url'])));return 1
 issues=[x for x in s['issues'].values() if x['stage']=='queued']
 if issues:collect_issue(min(issues,key=lambda x:(x['month'],x['url'])));return 1
 return 0
def options(aged):
 if not profile():return [],{}
 s=state();choices=[];payload={}
 if rules().get('body_selector'):
  rows=[x for x in s['articles'].values() if x['stage']=='queued' or (x['stage']=='pending_named_public_HTML_article_boundary' and x.get('parser_rule_digest')!=rule_digest())]
  if rows:
   row=min(rows,key=lambda x:(x['month'],x['url']));key=SID+':licensed_body';choices.append(Opportunity(key,'historical_native',SID,row['month'],row['month'],'Explicit licensed newspaper native HTML, preserved month precision',wait_rounds=aged[key],need_priority=2));payload[key]=row
 issues=[x for x in s['issues'].values() if x['stage']=='queued']
 if issues:
  row=min(issues,key=lambda x:(x['month'],x['url']));key=SID+':licensed_issue';choices.append(Opportunity(key,'frontier',SID,row['month'],row['month'],'Observed Website View link and issue month; no PDF',wait_rounds=aged[key],need_priority=2,action_kind='route_resolution'));payload[key]=row
 return choices,payload
