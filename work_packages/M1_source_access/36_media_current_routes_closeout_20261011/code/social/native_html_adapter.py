"""Source-specific complete HTML units; index wrappers/comments stay separate."""
import datetime as dt,re,urllib.parse
from html.parser import HTMLParser
import transport as t
from native_web_adapter import evidence
LOADED_CODE_SHA256=t.sha(__import__('pathlib').Path(__file__).read_bytes())
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

class Tree(HTMLParser):
 def __init__(self,raw):
  super().__init__(convert_charrefs=False);self.raw=raw;self.offsets=[0];self.nodes=[];self.stack=[]
  self.offsets.extend(m.end() for m in re.finditer('\n',raw))
  self.feed(raw)
 def pos(self):
  line,col=self.getpos();return self.offsets[line-1]+col
 def handle_starttag(self,tag,attrs):
  n={'tag':tag,'attrs':dict(attrs),'start':self.pos(),'inner':self.pos()+len(self.get_starttag_text()),'end':None,'parent':self.stack[-1] if self.stack else None}
  self.nodes.append(n)
  if tag not in VOID:self.stack.append(n)
  else:n['end']=n['inner']
 def handle_startendtag(self,tag,attrs):
  self.handle_starttag(tag,attrs)
  if tag not in VOID:self.handle_endtag(tag)
 def handle_endtag(self,tag):
  idx=next((i for i in range(len(self.stack)-1,-1,-1) if self.stack[i]['tag']==tag),None)
  if idx is None:return
  for n in self.stack[idx:]:n['end']=self.pos()
  del self.stack[idx:]
 def inside(self,n,parent):return n['start']>=parent['inner'] and n['start']<(parent['end'] or 0)
 def body(self,n):return self.raw[n['inner']:n['end']] if n['end'] is not None else ''

def classes(n):return set(n['attrs'].get('class','').split())
def canonical(url):
 p=urllib.parse.urlsplit(url);return urllib.parse.urlunsplit(('https',p.netloc,p.path,p.query,''))
def native_links(raw,url,kind):
 tree=Tree(raw);out=[];host=urllib.parse.urlsplit(url).hostname
 if kind=='siyach':
  for n in tree.nodes:
   if n['tag']=='article' and 'node-blog' in classes(n) and n['attrs'].get('about'):
    u=canonical(urllib.parse.urljoin(url,n['attrs']['about']))
    if urllib.parse.urlsplit(u).hostname==host and re.fullmatch(r'/node/\d+',urllib.parse.urlsplit(u).path):out.append({'url':u,'route_type':'permalink'})
 for n in tree.nodes:
  if n['tag']!='a' or not n['attrs'].get('href'):continue
  u=canonical(urllib.parse.urljoin(url,n['attrs']['href']));p=urllib.parse.urlsplit(u)
  if p.hostname!=host:continue
  if kind=='emergentkiwi':
   # Only source-published archive/permalink paths. No search or pagination guesses.
   if not p.path.startswith('/archive/') or p.query or p.path in ('/archive/about-me/',):continue
   route='index' if re.fullmatch(r'/archive/\d{4}/\d{2}/(?:page/\d+/)?',p.path) else 'permalink'
  elif kind=='elsewhere':
   if not p.path.startswith('/posts/') or p.query:continue
   route='permalink'
  elif kind=='bulltown':
   parent=n['parent'];in_archive=False
   while parent:
    if parent['tag']=='yearlist':in_archive=True;break
    parent=parent['parent']
   if not in_archive:continue
   route='permalink'
  elif kind=='wp_html':
   parent=n['parent'];article=None
   while parent:
    if parent['tag']=='article' and re.fullmatch(r'post-\d+',parent['attrs'].get('id','')):article=parent;break
    parent=parent['parent']
   if p.query:
    # Source-rendered share links expose their own original post path. Strip
    # only that named share parameter; numeric path must match its article.
    q=urllib.parse.parse_qs(p.query)
    if not article or set(q)!={'share'} or 'sd-button' not in classes(n) or p.path.rstrip('/').split('/')[-1]!=article['attrs']['id'][5:]:continue
    u=urllib.parse.urlunsplit((p.scheme,p.netloc,p.path,'',''));route='permalink'
   elif 'page-numbers' in classes(n) or re.fullmatch(r'(?:/author/[^/]+)?/page/\d+/',p.path):route='index'
   elif article and ('bookmark' in n['attrs'].get('rel','').split() or n['parent'] and 'entry-title' in classes(n['parent'])):route='permalink'
   else:continue
  elif kind=='bear_project':
   parent=n['parent'];in_main=False
   while parent:
    if parent['tag']=='main':in_main=True;break
    parent=parent['parent']
   if not in_main or p.query or p.path in ('/','/blog/','/my-character-sheet/','/the-party/') or p.path.rstrip('/')==urllib.parse.urlsplit(url).path.rstrip('/'):continue
   route='permalink'
  elif kind=='rukavina':
   if p.query:continue
   if p.path.startswith('/content/'):route='permalink'
   elif re.fullmatch(r'/archive(?:/\d{4}(?:/\d{6})?)?/?',p.path):route='index'
   else:continue
  elif kind=='laktek':
   if p.query or p.path in ('/','/now','/archive','/feeds/rss.xml'):continue
   parent=n['parent'];in_main=False
   while parent:
    if parent['tag']=='main':in_main=True;break
    parent=parent['parent']
   if not in_main:continue
   route='permalink'
  elif kind=='siyach':
   if not urllib.parse.unquote(p.path).startswith('/front-page-list') or set(urllib.parse.parse_qs(p.query))-{'page'}:continue
   route='index'
  elif kind=='sivers':
   if p.query or not n['parent'] or n['parent']['tag']!='li':continue
   if not any(x['tag']=='time' and tree.inside(x,n['parent']) for x in tree.nodes):continue
   route='permalink'
  elif kind=='wand3r':
   times=[x for x in tree.nodes if x['tag']=='time' and x['attrs'].get('datetime')]
   if len(times)!=1 or not times[0]['attrs']['datetime'].startswith('2024-') or p.query or not p.path.startswith('/blog/'):continue
   parent=n['parent'];in_navigation=False
   while parent:
    if 'links-nextprev' in classes(parent):in_navigation=True;break
    parent=parent['parent']
   if not in_navigation:continue
   route='permalink'
  else:continue
  out.append({'url':u,'route_type':route})
 return list({(x['url'],x['route_type']):x for x in out}.values())

def published_date(value,formats):
 for f in formats:
  try:return dt.datetime.strptime(value.strip(),f).date().isoformat()
  except ValueError:pass
 return None

def visible_text(raw):
 tree=Tree(raw);cuts=[]
 for n in tree.nodes:
  a=n['attrs']
  if n['end'] is not None and (n['tag'] in ('script','style','noscript') or a.get('aria-hidden')=='true' or re.search(r'display\s*:\s*none',a.get('style',''),re.I)):
   cuts.append((n['start'],n['end']+len('</'+n['tag']+'>')))
 for start,end in sorted(cuts,reverse=True):raw=raw[:start]+raw[end:]
 return t.clean(raw)

def records(raw,url,source,actor,kind):
 tree=Tree(raw);containers=[];date=None;author=None;body=None;reported_url=url;flags={};native_id=None;namespace='author_native_permalink';edited=None
 if kind=='emergentkiwi':
  containers=[n for n in tree.nodes if 'blogbody' in classes(n)]
  # A month wrapper is discovery only, even when an individual item is complete.
  if len(containers)!=1 or re.fullmatch(r'/archive/\d{4}/\d{2}/(?:page/\d+/)?',urllib.parse.urlsplit(url).path):return []
  container=containers[0]
  dates=[n for n in tree.nodes if n['tag']=='h2' and 'date' in classes(n) and n['start']<container['start']]
  date=published_date(t.clean(tree.body(dates[-1])),['%A, %B %d, %Y']) if dates else None
  posted=next((n for n in tree.nodes if 'posted' in classes(n) and tree.inside(n,container)),None)
  title=next((n for n in tree.nodes if n['tag']=='h3' and 'title' in classes(n) and tree.inside(n,container)),None)
  if not posted or not title or not date:return []
  links=[n for n in tree.nodes if n['tag']=='a' and n['attrs'].get('href') and tree.inside(n,posted)]
  if not links:return []
  reported_url=canonical(urllib.parse.urljoin(url,links[0]['attrs']['href']))
  if reported_url!=canonical(url):return []
  body=raw[title['end']+len('</h3>'):posted['start']];author='steve' if 'Posted by steve' in t.clean(tree.body(posted)) else None
  flags['comment_container_excluded']=True
 elif kind=='elsewhere':
  containers=[n for n in tree.nodes if n['tag']=='article' and n['attrs'].get('id')=='content']
  if len(containers)!=1:return []
  container=containers[0];dates=[n for n in tree.nodes if n['tag']=='h4' and tree.inside(n,container)]
  if len(dates)!=1:return []
  date=published_date(t.clean(tree.body(dates[0])),['%d %B %Y']);author='giant robot tackler'
  end=next((n['start'] for n in tree.nodes if n['attrs'].get('id')=='nextprev' and tree.inside(n,container)),None)
  if end is None:return []
  body=raw[dates[0]['end']+len('</h4>'):end];flags['navigation_and_disqus_container_excluded']=True
 elif kind=='bulltown':
  containers=[n for n in tree.nodes if n['tag']=='article' and 'h-entry' in classes(n)]
  if len(containers)!=1:return []
  container=containers[0];contents=[n for n in tree.nodes if 'e-content' in classes(n) and tree.inside(n,container)]
  times=[n for n in tree.nodes if n['tag']=='time' and 'dt-published' in classes(n) and tree.inside(n,container)]
  if len(contents)!=1 or len(times)!=1:return []
  date=times[0]['attrs'].get('datetime');body=tree.body(contents[0]);author='joe jenett'
  perm=next((n['attrs'].get('href') for n in tree.nodes if n['tag']=='a' and {'u-url','u-uid'}<=classes(n) and tree.inside(n,container)),None)
  if not perm or canonical(urllib.parse.urljoin(url,perm))!=canonical(url):return []
  flags.update(remix_of_older_work_possible=True,crosspost_work_relationships_unresolved=True)
 elif kind=='wp_html':
  containers=[n for n in tree.nodes if n['tag']=='article' and re.fullmatch(r'post-\d+',n['attrs'].get('id',''))]
  if len(containers)!=1:return []
  container=containers[0];content=next((n for n in tree.nodes if 'entry-content' in classes(n) and tree.inside(n,container)),None)
  times=[n for n in tree.nodes if n['tag']=='time' and 'published' in classes(n) and tree.inside(n,container)]
  byline=next((n for n in tree.nodes if 'byline' in classes(n) and tree.inside(n,container)),None)
  if not content or len(times)!=1 or not byline:return []
  authors=[n for n in tree.nodes if n['tag']=='a' and 'fn' in classes(n) and tree.inside(n,byline)]
  if len(authors)!=1 or t.clean(tree.body(authors[0]))!=source['allowed_author_name']:return []
  author=canonical(urllib.parse.urljoin(url,authors[0]['attrs']['href']))
  if author!=source['allowed_author_url']:return []
  perm=next((n['attrs'].get('href') for n in tree.nodes if n['tag']=='a' and 'bookmark' in n['attrs'].get('rel','') and tree.inside(n,container)),None)
  # The original permalink owns the numeric article identity; related/guest cards do not.
  canonical_meta=next((n['attrs'].get('href') for n in tree.nodes if n['tag']=='link' and n['attrs'].get('rel')=='canonical'),None)
  if canonical_meta and canonical(canonical_meta)!=canonical(url):return []
  if perm and canonical(urllib.parse.urljoin(url,perm))!=canonical(url):return []
  date=times[0]['attrs'].get('datetime');native_id=container['attrs']['id'][5:];namespace='wp_native_post'
  edited=next((n['attrs'].get('content') for n in tree.nodes if n['tag']=='meta' and n['attrs'].get('property')=='article:modified_time'),None)
  end=content['end']
  artifacts=[n['start'] for n in tree.nodes if tree.inside(n,content) and ('sharedaddy' in classes(n) or n['attrs'].get('id')=='jp-relatedposts')]
  if artifacts:end=min(end,*artifacts)
  body=raw[content['inner']:end];flags.update(native_byline_matches_licensed_author=True,comments_share_and_related_widgets_excluded=True,author_source_family=source.get('author_source_family'),migration_history_not_historical_version_verification=True)
 elif kind=='bear_project':
  mains=[n for n in tree.nodes if n['tag']=='main']
  if len(mains)!=1:return []
  container=mains[0];times=[n for n in tree.nodes if n['tag']=='time' and tree.inside(n,container)]
  tags=next((n for n in tree.nodes if 'tags' in classes(n) and tree.inside(n,container)),None)
  if len(times)!=1 or not tags:return []
  tagvalues=[t.clean(tree.body(n)).lstrip('#') for n in tree.nodes if n['tag']=='a' and tree.inside(n,tags)]
  if source['licensed_native_project_tag'] not in tagvalues:return []
  wrapper=times[0]['parent']
  while wrapper and wrapper['tag']!='p':wrapper=wrapper['parent']
  if not wrapper:return []
  date=times[0]['attrs'].get('datetime');author=source['source_author_identity'];body=raw[wrapper['end']+len('</p>'):tags['start']]
  flags.update(licence_limited_to_explicit_native_project_tag=True,not_whole_blog_license=True,comments_upvote_forms_and_tags_excluded=True,source_native_project_tags=tagvalues)
 elif kind=='rukavina':
  containers=[n for n in tree.nodes if n['tag']=='article' and n['attrs'].get('data-history-node-id','').isdigit()]
  if len(containers)!=1:return []
  container=containers[0];region=next((n for n in tree.nodes if 'layout__region--content' in classes(n) and tree.inside(n,container)),None)
  if not region:return []
  direct=[n for n in tree.nodes if n['parent'] is region and n['tag']=='div']
  times=[n for n in tree.nodes if n['tag']=='time' and tree.inside(n,region)]
  authors=[n for n in tree.nodes if 'p-author' in classes(n) and tree.inside(n,region)]
  if len(direct)!=3 or len(times)!=1 or len(authors)!=1 or t.clean(tree.body(authors[0]))!='Peter Rukavina':return []
  cm=next((n['attrs'].get('href') for n in tree.nodes if n['tag']=='link' and n['attrs'].get('rel')=='canonical'),None)
  if not cm or canonical(cm)!=canonical(url):return []
  body=tree.body(direct[0]);date=times[0]['attrs'].get('datetime');author='Peter Rukavina';native_id=container['attrs']['data-history-node-id'];namespace='drupal_native_node'
  flags.update(native_author_verified=True,comments_and_forms_excluded=True,native_node_id_observed=True)
 elif kind=='laktek':
  containers=[n for n in tree.nodes if n['tag']=='article' and 'hentry' in classes(n)]
  if len(containers)!=1:return []
  container=containers[0];times=[n for n in tree.nodes if n['tag']=='time' and 'pubdate' in n['attrs'] and tree.inside(n,container)];contents=[n for n in tree.nodes if 'entry-content' in classes(n) and tree.inside(n,container)]
  if len(times)!=1 or len(contents)!=1:return []
  date=published_date(t.clean(tree.body(times[0])),['%d %B %Y']);body=tree.body(contents[0]);author='Lakshan Perera'
  flags.update(native_pubdate_attribute_observed=True,native_datetime_raw=times[0]['attrs'].get('datetime'),time_updated_class_not_content_modified_proof=True,source_named_author_mapping='source homepage identity; historical legal-person equivalence not independently audited')
 elif kind=='siyach':
  containers=[n for n in tree.nodes if n['tag']=='article' and {'node-blog','node-full'}<=classes(n) and re.fullmatch(r'node-\d+',n['attrs'].get('id',''))]
  if len(containers)!=1:return []
  container=containers[0];contents=[n for n in tree.nodes if 'field-name-body' in classes(n) and tree.inside(n,container)];dates=[n for n in tree.nodes if 'dc:created' in n['attrs'].get('property','').split() and tree.inside(n,container)];authors=[n for n in tree.nodes if 'username' in classes(n) and tree.inside(n,container)]
  if len(contents)!=1 or len(dates)!=1 or len(authors)!=1 or t.clean(tree.body(authors[0]))!='Wessel' or authors[0]['attrs'].get('about')!='/user/1':return []
  reported_url=canonical(urllib.parse.urljoin(url,container['attrs']['about']))
  if reported_url!=canonical(url):return []
  body=tree.body(contents[0]);date=dates[0]['attrs'].get('content');author='https://siyach.org/user/1';native_id=container['attrs']['id'][5:];namespace='drupal_native_node'
  flags.update(native_submitted_timestamp_not_current_version_time=True,native_author_display_and_account_verified=True,comments_print_links_and_forms_excluded=True,source_licence_variants_observed=source.get('source_license_history'))
 elif kind=='sivers':
  containers=[n for n in tree.nodes if n['tag']=='article']
  if len(containers)!=1:return []
  container=containers[0];header=next((n for n in tree.nodes if n['tag']=='header' and tree.inside(n,container)),None);footer=next((n for n in tree.nodes if n['tag']=='footer' and tree.inside(n,container)),None)
  if not header or not footer or 'Derek Sivers' not in t.clean(tree.body(footer)) or 'Copy & share' not in t.clean(tree.body(footer)):return []
  times=[n for n in tree.nodes if n['tag']=='time' and tree.inside(n,header)]
  if len(times)!=1:return []
  date=times[0]['attrs'].get('datetime');body=raw[header['end']+len('</header>'):footer['start']];author='Derek Sivers'
  flags.update(native_article_header_time_verified=True,source_explicit_copy_permission_not_public_domain=True,footer_comments_and_header_audio_excluded=True,book_context_reproduction_not_new_original_publication=True)
  if urllib.parse.urlsplit(url).path in ('/m1','/m2'):
   flags.update(native_date_value_retained=date,historical_first_publication_date_mapping='unresolved for named book-context pages; native header/directory value is not independently verified original publication',source_date_candidate_not_confirmed_historical_date=True)
 elif kind=='wand3r':
  mains=[n for n in tree.nodes if n['tag']=='main' and n['attrs'].get('id')=='skip']
  if len(mains)!=1:return []
  container=mains[0];dates=[n for n in tree.nodes if n['tag']=='time' and tree.inside(n,container)];metadata=next((n for n in tree.nodes if 'post-metadata' in classes(n) and tree.inside(n,container)),None);nav=next((n for n in tree.nodes if 'links-nextprev' in classes(n) and tree.inside(n,container)),None)
  if len(dates)!=1 or not metadata or not nav:return []
  date=dates[0]['attrs'].get('datetime')
  if not date or not date.startswith('2024-'):return []
  body=raw[metadata['end']+len('</ul>'):nav['start']];author='Brandon / WNDR'
  flags.update(licence_scope_explicit_2024_works_only=True,current_2025_footer_no_licence_not_carried_to_new_works=True,story_event_dates_not_publication_date=True,comments_and_navigation_excluded=True)
 if not body or not date:return []
 explicit_exception=bool(re.search(r'(?:not|except|exclud)[^.!?]{0,100}creative commons|not[^.!?]{0,100}(?:reproduc|copied)',t.clean(body),re.I)) if kind=='emergentkiwi' else False
 flags.update(source_published_HTML_post=True,current_body_not_verified_historical_version=True,third_party_and_comments_not_covered_by_author_licence=True,visible_authored_text_present=bool(visible_text(body)))
 state='author_licence_exception_not_qualified' if explicit_exception else 'complete_native_text' if flags['visible_authored_text_present'] else 'bodyless_media_link_only'
 return [{'source_id':source['source_id'],'native_namespace':namespace,'native_post_id':native_id or urllib.parse.urlsplit(reported_url).path.rstrip('/'),'source_url':reported_url,'native_unit':'personal_weblog_post','native_created_at':date,'native_edited_at':edited,'date_precision':'source_day' if len(date)==10 else 'source_timestamp','author_id':author,'author_role':'personal_blog_native_author','body_original':'' if explicit_exception else body,'body_format':'html','content_state':state,'content_license':source['content_license'],'license_basis':'source-owned text only; quotes/guest material independently unresolved; '+source['permission_raw_reference'],'flags':flags,'native_fields':{'source_expansion_evidence':evidence(actor,source),'permission_raw_reference':source['permission_raw_reference'],'native_date_observed_on_original_permalink':True,'historical_author_country_unmeasured':True,'author_source_family':source.get('author_source_family'),'native_migration_history':source.get('documented_migration_history'),'source_license_history':source.get('source_license_history'),'quoted_external_works_not_covered_by_author_license':True},'edges':[],'attachments':[]}]
