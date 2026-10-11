"""Author-published Blogger HTML/Atom identities; whole native post bodies only."""
import json,re,urllib.parse,xml.etree.ElementTree as ET
from html.parser import HTMLParser
import transport as t
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
class Posts(HTMLParser):
 def __init__(self,raw):
  super().__init__(convert_charrefs=False);self.raw=raw;self.offsets=[0];self.depth=0;self.current=None;self.outer=None;self.body_depth=None;self.body_start=None;self.posts=[]
  self.offsets.extend(m.end() for m in re.finditer('\n',raw))
  self.feed(raw)
 def pos(self):
  line,col=self.getpos();return self.offsets[line-1]+col
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);cls=set((a.get('class') or '').split())
  if tag not in VOID:self.depth+=1
  if tag=='div' and {'post','hentry'}<=cls:
   self.current={'post_id':None,'publication_at':None,'updated_at':None,'source_url':None,'body_original':None,'author_id':None,'preview':False};self.outer=self.depth
  if self.current is None:return
  p=self.current
  if tag=='meta':
   field=a.get('itemprop');value=a.get('content')
   if field=='postId':p['post_id']=value
   elif field=='datePublished':p['publication_at']=value
   elif field=='dateModified':p['updated_at']=value
   elif field=='url':p['source_url']=value
  if tag=='abbr' and 'published' in cls and a.get('title'):p['publication_at']=a['title']
  if tag=='time' and a.get('datetime') and ('published' in cls or a.get('itemprop')=='datePublished'):p['publication_at']=a['datetime']
  if tag=='a' and (a.get('rel')=='bookmark' or a.get('class')=='timestamp-link') and a.get('href'):p['source_url']=a['href']
  if tag=='a' and a.get('href') and ('author' in (a.get('rel') or '').split() or 'fn' in cls):
   match=re.fullmatch(r'https?://www\.blogger\.com/profile/(\d+)',a['href'])
   if match:p['author_id']=match.group(1)
  if 'jump-link' in cls:p['preview']=True
  if tag=='div' and 'post-body' in cls:
   self.body_depth=self.depth;self.body_start=self.pos()+len(self.get_starttag_text())
   match=re.fullmatch(r'post-body-(\d+)',a.get('id',''))
   if match:
    if p['post_id'] and p['post_id']!=match.group(1):p['identity_conflict']=True
    p['post_id']=match.group(1)
 def handle_startendtag(self,tag,attrs):
  self.handle_starttag(tag,attrs)
  if tag not in VOID:self.handle_endtag(tag)
 def handle_endtag(self,tag):
  if tag in VOID:return
  if tag=='div' and self.current is not None and self.body_depth==self.depth and self.body_start is not None:
   self.current['body_original']=self.raw[self.body_start:self.pos()];self.body_depth=None;self.body_start=None
  if tag=='div' and self.current is not None and self.outer==self.depth:
   self.posts.append(self.current);self.current=None;self.outer=None
  self.depth=max(0,self.depth-1)

def permalink_records(raw,source,actor,requested_url):
 rows=[]
 for p in Posts(raw).posts:
  if not p['post_id']:continue
  url=p['source_url'] or requested_url
  host=urllib.parse.urlsplit(url).hostname
  if host!=urllib.parse.urlsplit(source['base_url']).hostname:continue
  meta={k:actor.get(k) for k in ('cohort_id','source_context_country','source_context_region','source_context_evidence_ref','source_context_observed_at','community_context_scope','author_country','author_country_status','author_country_evidence_type','author_country_evidence_ref','author_country_observed_at')}
  meta.update(carrier='personal_blog',genre='personal_weblog',role_status=actor['role_status'],role_evidence_ref=actor['profile_raw_reference'])
  rows.append({'source_id':source['source_id'],'native_namespace':'blogger_post','native_post_id':p['post_id'],'source_url':url,'native_unit':'personal_weblog_post','native_created_at':p['publication_at'],'native_edited_at':p['updated_at'],'author_id':p['author_id'],'author_role':'ordinary_public_self_presentation' if p['author_id'] and p['author_id']==actor.get('actor_id') else 'public_native_blog_author_role_unverified','body_original':p['body_original'],'body_format':'html','content_state':'index_preview' if p['preview'] else 'native_identity_conflict' if p.get('identity_conflict') else 'complete_native_text' if p['body_original'] else 'bodyless_native_entity','content_license':source['content_license'],'license_basis':'source-own-material permission saved; quotation/guest rights remain separate','context_status':'native_permalink_post; comments_not_collected','flags':{'source_published_HTML_post':True,'native_blog_post_ID_matched_body_container':True,'preview_only':p['preview'],'identity_date_truth_not_independently_verified':True,'source_own_material_permission_does_not_extend_to_all_quotes_guests_or_comments':True},'native_fields':{'source_expansion_evidence':meta,'permission_raw_reference':source['permission_raw_reference'],'native_permalink_reported':url,'native_published_at':p['publication_at'],'native_updated_at':p['updated_at'],'request_url':requested_url,'source_published_HTML_body_container':'post hentry / post-body; no synthetic article segmentation'},'edges':[],'attachments':[]})
 return rows

def atom_metadata(raw):
 root=ET.fromstring(raw);a='{http://www.w3.org/2005/Atom}'
 entries=[]
 for e in root.findall(a+'entry'):
  entries.append({'native_entry_id':e.findtext(a+'id'),'publication_at':e.findtext(a+'published'),'updated_at':e.findtext(a+'updated'),'permalink':next((l.get('href') for l in e.findall(a+'link') if l.get('rel')=='alternate' and l.get('type')=='text/html'),None)})
 return {'native_feed_id':root.findtext(a+'id'),'entries':entries,'next_url':next((l.get('href') for l in root.findall(a+'link') if l.get('rel')=='next'),None),'body_completeness':'not inferred from feed configuration; native permalink body required'}

def native_links(raw,base):
 class Links(HTMLParser):
  def __init__(self):super().__init__();self.urls=[]
  def handle_starttag(self,tag,attrs):
   a=dict(attrs)
   if tag=='a' and a.get('href'):
    u=urllib.parse.urljoin(base,a['href']);p=urllib.parse.urlsplit(u)
    if p.hostname==urllib.parse.urlsplit(base).hostname and re.fullmatch(r'/\d{4}/\d{2}/[^/]+\.html',p.path):
     self.urls.append(urllib.parse.urlunsplit(('https',p.netloc,p.path,'','')))
 parser=Links();parser.feed(raw);return list(dict.fromkeys(parser.urls))
