"""Saved partial date frames and inspected article boundaries, never topic filters."""
import hashlib, json, re
from datetime import datetime
from urllib.parse import urlsplit,urljoin,urldefrag
from bs4 import BeautifulSoup
import transport as t
def canonical(url):
    u=urlsplit(urldefrag(url)[0]);return u._replace(query='',fragment='').geturl().rstrip('/')
def dated_search_inventory(text,hosts,month):
    """Metadata inventory from saved rendered search; no article-body certification."""
    candidates=[]
    for block in re.split(r'-{20,}',text):
        block=block.strip()
        match=re.match(r'[^\n]+ \((https://[^\s)]+)\)',block)
        if not match or urlsplit(match.group(1)).hostname not in hosts:continue
        stamp=re.search(r'Published:\s+([A-Z][a-z]+ \d{1,2}, \d{4})',block)
        if not stamp:continue
        day=datetime.strptime(stamp.group(1),'%B %d, %Y').date().isoformat()
        if day[:7]==month:candidates.append(dict(url=canonical(match.group(1)),date=day,date_basis='Explicit publication day in saved search response; primary body/date verification separate'))
    return candidates
def freeze_frame(source, month, candidates, evidence, route, notes):
    s=t.read(t.SCOPE)
    cat=next(x for x in t.read(t.OUT/'control/CANDIDATES.json')['candidates'] if x['source_id']==source)
    if month not in s['original_months'] or int(month[:4])<cat['founded_year']: raise RuntimeError('Frame outside source era or frozen design')
    # A date archive's next-page URL is navigation, not an article identity.
    if any(re.search(r'/page/\d+/?$',urlsplit(x['url']).path) for x in candidates):
        raise RuntimeError('Navigation URL in article frame; inspect and remove before freezing')
    unique={canonical(x['url']):dict(x,url=canonical(x['url'])) for x in candidates}
    ordered=sorted(unique.values(),key=lambda x:(x.get('date') or month+'-99',x['url']))
    for x in ordered:t.validate_url(x['url'],cat['hosts'])
    p=t.OUT/'media/frames'/f'{source}_{month}.json'
    if p.exists():raise RuntimeError('Frozen frame immutable; no refill')
    receipt=dict(frame_id=f'frame22:{source}:{month}', source_id=source,stratum=cat['stratum'],month=month,receipt_path=str(p.relative_to(t.OUT)),frozen_at_utc=t.now().isoformat(),route=route,frame_state='bounded_partial_observation',frame_count=len(ordered),candidates=ordered,selected=ordered[:5],selection='publication day when evidenced, then native URL; first5; no refill',monthly_denominator=None,inclusion_probability=None,evidence=evidence,notes=notes,topic_filter=None,length_filter=None,affect_filter=None,original_source_success=False)
    t.save(p,receipt);return receipt
def article_nodes(soup):
    found=[]
    def walk(v):
        if isinstance(v,list):
            for x in v:walk(x)
        elif isinstance(v,dict):
            types=v.get('@type',[]);types=[types] if isinstance(types,str) else types
            if any(x in {'Article','NewsArticle','ReportageNewsArticle','OpinionNewsArticle','BlogPosting'} for x in types):found.append(v)
            if '@graph' in v:walk(v['@graph'])
    for n in soup.find_all('script',type='application/ld+json'):
        try:walk(json.loads(n.get_text()))
        except (ValueError,TypeError):pass
    return found
def date(value):
    if not isinstance(value,str):return dict(raw=value,valid=False,timezone=None)
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        return dict(raw=value,valid=True,local_day=d.date().isoformat(),month=value[:7],timezone=d.strftime('%z') if d.tzinfo else None,precision='timestamp' if 'T' in value else 'day')
    except ValueError:return dict(raw=value,valid=False,timezone=None)
def parse(data,url,month,selector,boundary_spec=None):
    soup=BeautifulSoup(data,'html.parser')
    c=soup.find('link',rel='canonical');cu=canonical(urljoin(url,c['href'])) if c and c.get('href') else canonical(url)
    title=soup.find('h1');title=title.get_text(' ',strip=True) if title else None
    nodes=article_nodes(soup);matching=[]
    for n in nodes:
        refs=[n.get('url'),n.get('@id'),n.get('mainEntityOfPage')]
        refs=[r.get('@id') or r.get('url') if isinstance(r,dict) else r for r in refs]
        if cu in [canonical(urljoin(url,r)) for r in refs if isinstance(r,str)]:matching.append(n)
    # One unbound article node can supply date evidence but remains a separately
    # inspected identity mapping, never an automatic canonical JSONLD match.
    n=matching[0] if len(matching)==1 else nodes[0] if len(nodes)==1 else {}
    published=n.get('datePublished');modified=n.get('dateModified')
    modified_meta=[x.get('content') for x in soup.find_all('meta',property='article:modified_time') if x.get('content')]
    if not modified and len(set(modified_meta))==1:modified=modified_meta[0]
    if not published:
        meta=soup.find('meta',property='article:published_time') or soup.find('meta',attrs={'name':'date'})
        if meta:published=meta.get('content')
    d=date(published)
    paywall=n.get('isAccessibleForFree') in [False,'false','False'] or bool(soup.select('[data-testid="paywall"],.article-paywall,.paywall-overlay,.gh-post-upgrade-cta'))
    selected=soup.select(selector) if selector else []
    body=None;parts=[];removed=[]
    if len(selected)==1 and not t.challenge(data) and not paywall:
        b=BeautifulSoup(str(selected[0]),'html.parser')
        if boundary_spec and boundary_spec.get('exclude_selectors'):
            for x in b.select(','.join(boundary_spec['exclude_selectors'])):
                if x.attrs is not None:removed.append(x.get('class') or x.name);x.decompose()
        if boundary_spec and boundary_spec.get('mode')=='between_direct_separators':
            root=b.select_one(selector)
            children=root.find_all(recursive=False)
            separators=[i for i,x in enumerate(children) if x.name=='hr']
            left=separators[boundary_spec['after_separator_index']];right=separators[boundary_spec['before_separator_index']]
            if left>=right:raise RuntimeError('Body boundary order invalid')
            b=BeautifulSoup(''.join(str(x) for x in children[left+1:right]),'html.parser')
        for x in b.select('script,style,nav,aside,form,footer,.related-posts,.related-articles,.social-share,.newsletter-signup,.jeg_post_tags,.post-tags'):
            if x.attrs is None:continue
            removed.append(x.get('class') or x.name);x.decompose()
        # Tables can carry substantive article sections (observed InDaily events).
        # Keep each outer table once, including cell text without paragraph tags.
        blocks=['p','h2','h3','h4','li','blockquote','figcaption','table']
        parts=[x.get_text(' ',strip=True) for x in b.select(','.join(blocks)) if x.get_text(' ',strip=True) and not x.find_parent(blocks)]
        # Outer blockquotes may repeat paragraphs; preserve the visible container
        # text for body and use the parts only as a boundary-inspection aid.
        body='\n'.join(parts)
    return dict(canonical_url=cu,request_identity_match=canonical(url)==cu,same_publisher_host=urlsplit(cu).hostname==urlsplit(url).hostname,title=title,first_publication=d,date_modified=date(modified),date_modified_meta_values=modified_meta,eligible_month=bool(d.get('valid') and d.get('month')==month and '1988-01-01'<=d['local_day']<='2026-09-21'),jsonld_identity='canonical_match' if len(matching)==1 else 'single_unbound_requires_inspection' if len(nodes)==1 else 'ambiguous_or_absent',author=n.get('author'),publisher=n.get('publisher'),genre=n.get('@type'),article_license=n.get('license'),paywall_or_preview=paywall,challenge=t.challenge(data),body_selector=selector,body_selector_matches=len(selected),body_boundary_spec=boundary_spec,body_text=body,inspection_parts=parts,removed_boilerplate=removed,visible_body_verified=False,historical_version_equivalence='not_established; later retrieval and stated modification time retained separately')
def inspect_request(receipt,month,selector,boundary_spec=None,source_timezone=None,observed_local_day=None,source_date_evidence=None):
    if receipt['status']!='saved':raise RuntimeError('No complete raw payload to inspect')
    raw=t.OUT/receipt['raw_path']
    if t.digest(raw)!=receipt['sha256']:raise RuntimeError('Raw bytes differ')
    result=parse(raw.read_bytes(),receipt['final_url'],month,selector,boundary_spec)
    if source_date_evidence:
        soup=BeautifulSoup(raw.read_bytes(),'html.parser');nodes=soup.select(source_date_evidence['selector'])
        if len(nodes)!=1 or nodes[0].get_text(' ',strip=True)!=source_date_evidence['visible_text']:raise RuntimeError('Visible publication date evidence differs')
        text=re.sub(r'(\d+)(?:st|nd|rd|th)',r'\1',source_date_evidence['visible_text'].split(':',1)[-1].strip())
        local_day=datetime.strptime(text,'%B %d, %Y').date().isoformat()
        result['first_publication_native_timestamp']=result['first_publication']
        result['first_publication']={**date(local_day),'raw_visible_text':source_date_evidence['visible_text'],'evidence_selector':source_date_evidence['selector'],'assignment_basis':'Actual visible publisher publication day; timestamp absent, timezone unproven'}
        result['eligible_month']=local_day[:7]==month and '1988-01-01'<=local_day<='2026-09-21'
    if source_timezone and observed_local_day:
        from zoneinfo import ZoneInfo
        raw_date=result['first_publication'];instant=datetime.fromisoformat(raw_date['raw'].replace('Z','+00:00'))
        if instant.tzinfo is None:raise RuntimeError('Timezone conversion requires an offset-bearing timestamp')
        local=instant.astimezone(ZoneInfo(source_timezone))
        if local.date().isoformat()!=observed_local_day:raise RuntimeError('Displayed date/timestamp timezone mapping conflicts')
        result['first_publication_native_timestamp']=raw_date
        result['first_publication']={**raw_date,'local_day':observed_local_day,'month':observed_local_day[:7],'source_timezone':source_timezone,'source_local_timestamp':local.isoformat(),'assignment_basis':'Visible publisher date equals timestamp converted to evidenced source timezone; original timestamp preserved'}
        result['eligible_month']=observed_local_day[:7]==month and '1988-01-01'<=observed_local_day<='2026-09-21'
    result.update(request_id=receipt['request_id'],source_id=receipt['source_id'],raw_path=receipt['raw_path'],raw_sha256=receipt['sha256'],raw_bytes=receipt['byte_count'],retrieved_at_utc=receipt['finished_at_utc'],publication_month=month,content_version_time=result['date_modified'],boundary_status='pending_actual_passage_and_DOM_inspection',parser_sha256=t.digest(__file__))
    p=t.OUT/'media/parsed'/f"{receipt['request_id']}.json";t.save(p,result)
    return result
def certify(request_id,review):
    p=t.OUT/'media/parsed'/f'{request_id}.json';a=t.read(p)
    required=['identity_verified','publication_verified','source_edition_verified','complete_visible_body','no_continuation_missing','no_preview','rights_reviewed']
    if not all(review.get(k) is True for k in required):raise RuntimeError('Explicit inspected boundary/date/source/rights checks required')
    if not a['eligible_month'] or not a['request_identity_match'] or not a['body_text'] or a['paywall_or_preview'] or a['challenge']:raise RuntimeError('Article cannot be certified')
    if review.get('first_body_line')!=a['body_text'].splitlines()[0] or review.get('last_body_line')!=a['body_text'].splitlines()[-1]:raise RuntimeError('Actual start/end evidence differs')
    body=a['body_text'].encode();bp=t.OUT/'media/bodies'/f'{request_id}.txt'
    with t.lock():
        t.budget(len(body));bp.parent.mkdir(parents=True,exist_ok=True)
        if bp.exists():raise RuntimeError('Body version already saved')
        bp.write_bytes(body)
    a.update(body_path=str(bp.relative_to(t.OUT)),body_sha256=t.digest(bp),body_bytes=len(body),body_chars=len(a['body_text']),visible_body_verified=True,boundary_status='inspected_complete_visible_article_at_retrieval',review=review,reviewed_at_utc=t.now().isoformat(),original_source_success=False)
    t.save(p,a);t.save(t.OUT/'media/checks'/f'{request_id}.json',dict(request_id=request_id,**review,raw_sha256=a['raw_sha256'],body_sha256=a['body_sha256'],historical_version_equivalence=a['historical_version_equivalence']))
    return a
