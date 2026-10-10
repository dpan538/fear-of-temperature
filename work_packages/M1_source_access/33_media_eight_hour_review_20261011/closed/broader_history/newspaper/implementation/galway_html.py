"""Whole Galway original HTML from complete entries in a saved partial sitemap."""
import datetime,json,re,xml.etree.ElementTree as ET
from urllib.parse import urlsplit,urlunsplit
from bs4 import BeautifulSoup
import elt

HOST='www.advertiser.ie'
PREFIX='/galway/article/'

def native_id(url):
 u=urlsplit(url)
 if u.hostname!=HOST or u.scheme not in ['http','https']:return None
 m=re.match(r'^/galway/article/(\d+)(?:/[^?#]*)?$',u.path)
 return int(m[1]) if m else None

def prefix_targets(data,p,receipt,permitted):
 """Only complete XML url elements survive; trailing partial XML is not repaired."""
 items=[];seen=set()
 for fragment in re.findall(rb'<url>\s*.*?\s*</url>',data,re.S):
  try:node=ET.fromstring(fragment)
  except ET.ParseError:continue
  locs=node.findall('loc');loc=locs[0].text if len(locs)==1 else None
  pid=native_id(loc or '')
  if pid is None or pid in seen:continue
  u=urlsplit(loc);request=urlunsplit(('https',HOST,u.path,'',''))
  if not permitted(request):continue
  seen.add(pid);last=node.find('lastmod')
  items.append(dict(source_id=p['source_id'],url=request,representation='publisher_galway_native_html',month='',native_evidence=dict(native_article_id=pid,native_sitemap_url=loc,native_lastmod_observed=last.text if last is not None else None,native_sitemap_receipt=receipt['target_id'],native_sitemap_raw_reference=receipt['raw_reference'],native_index_is_partial_prefix=True,native_entry_complete=True,request_scheme_basis='Same publisher HTTPS origin verified by saved ordinary root and original article. Exact per-page native ID/date/canonical mapping required before qualification; no global alias inference.',publication_date_assignment='Pending original displayed byline; lastmod and source snapshot never assign publication time')))
 return items

def discover(p,v,queue,fetch,permitted,policy):
 stage=v.get('stage','robots')
 if stage=='robots':policy(p,v);return 1
 if stage=='native_root':
  rec=fetch(p,p['root_url'],{'native_newspaper_frame':p['title_classification_reference'],'ordinary_HTML_interface_only':True})
  if rec['status']!='saved':v.update(stage='blocked',blocked_reason='Public publisher root '+rec['status'])
  else:v.update(stage='saved_partial_sitemap_prefix',native_root_receipt=rec['target_id'])
  return 1
 if stage=='saved_partial_sitemap_prefix':
  rec=json.loads((elt.OWN/p['saved_sitemap_receipt']).read_text())
  assert rec['source_id']==p['source_id'] and rec['status']=='object_cap_stop' and rec['partial'] and rec.get('raw_reference')
  items=prefix_targets(elt.read_payload(rec['raw_reference']),p,rec,lambda u:permitted(v,u))
  for url in p.get('additional_observed_article_URLs',[]):
   if native_id(url) is not None and permitted(v,url):items.append(dict(source_id=p['source_id'],url=url,representation='publisher_galway_native_html',month='',native_evidence=dict(native_article_id=native_id(url),original_structure_receipt=p['original_structure_receipt'],publication_date_assignment='Pending original displayed byline; no index-assigned date')))
  queue(p['source_id'],items)
  v.update(stage='observed_public_frontier_consumed',queued_native_article_URLs=[t['url'] for t in items],observed_native_prefix_entries=len(items),partial_index_receipt=rec['target_id'],attempted_pages=1,native_inventory_population='Complete Galway XML entries in a retained2MiB truncated native sitemap prefix plus one observed original article; unknown complete archive denominator',reason='Saved prefix enumerated without raising the response cap, retrying the stopped route, guessing private APIs or claiming full archive exhaustion')
  return 1
 return 0

def recovered_native_evidence(evidence,sid,requested_url):
 """Resolve a compact frozen locator to its exact retained metadata entry."""
 if evidence.get('native_article_id') is not None:return evidence,None
 ref=evidence.get('frozen_queue_reference');index=evidence.get('entry_index')
 if not ref or not isinstance(index,int):return evidence,None
 path=(elt.REPO/ref).resolve()
 allowed={(root/'queues'/(sid+'.json')).resolve() for root in elt.QUEUE_ROOTS}
 if path not in allowed:return evidence,None
 payload=path.read_bytes();entries=json.loads(payload)
 if index<0 or index>=len(entries):return evidence,None
 original=entries[index]
 if original.get('source_id')!=sid or elt.canon(original.get('url',''))!=elt.canon(requested_url):return evidence,None
 recovered=original.get('native_evidence') or {}
 if recovered.get('native_article_id')!=native_id(requested_url):return evidence,None
 return dict(evidence,**recovered),dict(basis='Exact retained frozen queue entry matches source/request URL and native numeric ID; no guessed alias/date',reference=ref,entry_index=index,metadata_file_sha256=elt.sha(payload))

def parse(raw,sid,url,metadata=None):
 import extract_load
 p=extract_load.ADAPTERS[sid];s=BeautifulSoup(raw,'html.parser');heads=s.select('article header h1#editheadline');bylines=s.select('article header p.byline span');nodes=s.select('article #article-body');canonical=s.select('link[rel="canonical"][href]')
 title=heads[0].get_text(' ',strip=True) if len(heads)==1 else None
 stamp=bylines[0].get_text(' ',strip=True) if len(bylines)==1 else None
 native=canonical[0]['href'] if len(canonical)==1 else url;pid=native_id(url);identity_ok=pid is not None and native_id(native)==pid
 requested_url=url;alias_urls={url,native};expected_pid=pid;evidence_recovery=None
 if metadata and metadata.get('request_id'):
  try:receipt=elt._receipt(metadata['request_id'])
  except ValueError:identity_ok=False
  else:
   requested_url=receipt.get('url') or '';evidence=receipt.get('target',{}).get('native_evidence') or {};evidence,evidence_recovery=recovered_native_evidence(evidence,sid,requested_url);expected_pid=evidence.get('native_article_id')
   identity_ok &= receipt.get('source_id')==sid and expected_pid==pid and native_id(requested_url)==pid and native_id(receipt.get('final_url') or '')==pid
   for alias in [requested_url,evidence.get('native_sitemap_url')]:
    if alias and native_id(alias)==pid:alias_urls.add(alias)
 canonical_https=urlunsplit(('https',HOST,urlsplit(native).path,'','')) if identity_ok else url
 day=None;m=re.fullmatch(r'Galway Advertiser,\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})',stamp or '')
 if m:
  try:
   d=datetime.datetime.strptime(' '.join(m.groups()[1:]),'%b %d %Y').date()
   if d.strftime('%a')==m[1]:day=d.isoformat()
  except ValueError:pass
 key='https://'+HOST+PREFIX+str(pid) if pid is not None else url
 alias_urls.add(canonical_https)
 record=dict(article_id=elt.article_id(sid,key),source_id=sid,source=p['title'],source_url=canonical_https,raw_source_url=requested_url,url_aliases=sorted(alias_urls),source_native_article_id=pid,expected_native_request_article_id=expected_pid,title=title,publication_date=day,date_field='Unique original Galway Advertiser byline weekday/month/day/year',publisher_timestamp=stamp,observed_date_fields=[['native article header p.byline span',stamp]],content_version_time=None,stratum=p['stratum'],country=p['country'],edition=p['edition'],source_frame=p['frame'],provenance='direct publisher original newspaper web article; reporting/quotation origins and claim truth separate',historical_body_equivalence='unknown; current retrieved archive rendition',semantic_labels_executed=False,length_filter_used=False,retention_limit=p['retention_limit'],native_canonical_url=native,canonical_mapping_status='same publisher native numeric ID matched on initial request, returned HTML and unique canonical' if identity_ok else 'conflicting native article identity',request_scheme_mapping_scope='Exact retrieved page only; historical rendition equivalence not established')
 if metadata:record.update(metadata)
 if evidence_recovery:record['native_identity_evidence_recovery']=evidence_recovery
 if len(nodes)!=1:return record,'','pending_missing_or_nonunique_original_article_body'
 node=nodes[0]
 for e in node.select('script,style,form,svg,nav,aside'):e.decompose()
 body=elt.renderer.normalise(elt.renderer.render(node));record.update(body_boundary='Unique article #article-body; full original paragraph order',article_boundary_evidence='Unique native Galway article title/byline/body and matching native numeric canonical identity; page copyright and generation time are not publication dates',paragraph_count=len(node.select('p')))
 if not identity_ok:return record,body,'pending_conflicting_native_article_identity'
 if node.select('.paywall,.subscription-wall,.article-preview'):return record,body,'pending_visible_source_preview_or_paywall'
 if not body or not title:return record,body,'pending_empty_original_body_or_identity'
 if not any(c.isalnum() for c in node.get_text(' ',strip=True)):return record,body,'pending_image_original_TEXT_or_article_boundary'
 readable=BeautifulSoup(str(node),'html.parser');tables=readable.select('table')
 for t in tables:t.decompose()
 if tables and not any(c.isalnum() for c in readable.get_text(' ',strip=True)):return record,body,'pending_table_only_original_article_boundary'
 if not elt.eligible(day):return record,body,'pending_missing_conflicting_or_outside_fixed_publication_date'
 return record,body,'confirmed_complete'
