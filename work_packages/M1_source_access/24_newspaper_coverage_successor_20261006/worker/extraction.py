"""Changed-tranche DOM extraction using declared observed source boundaries."""
import datetime as dt,hashlib,importlib.util,json,re
from bs4 import BeautifulSoup
import core
spec=importlib.util.spec_from_file_location('inline_renderer',core.OLD/'prototype/parser.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)

def publish_date(soup):
    fields=[]
    for selector,attr in [('meta[property="article:published_time"]','content'),('meta[name="date"]','content'),('time[datetime]','datetime')]:
        n=soup.select_one(selector)
        if n:fields.append((selector,n.get(attr)))
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            obj=json.loads(script.string or script.get_text());objects=obj if isinstance(obj,list) else obj.get('@graph',[obj])
            for o in objects:
                if isinstance(o,dict) and o.get('datePublished'):fields.append(('publisher JSON-LD datePublished',o['datePublished']))
        except (ValueError,TypeError):pass
    for origin,value in fields:
        if value and re.match(r'^\d{4}-\d{2}-\d{2}',value):return value[:10],origin,value
    return None,None,None

def extract(receipt,adapter):
    if receipt['status']!='saved' or receipt.get('partial'):return None
    raw=core.OWN/receipt['raw_path']
    if core.sha(raw)!=receipt['raw_sha256']:raise ValueError('New raw hash conflict')
    soup=BeautifulSoup(raw.read_bytes(),'html.parser')
    body_nodes=soup.select(adapter['body_selector']);date,origin,stamp=publish_date(soup)
    target=receipt['target'];url_match=re.search(r'/(\d{4})/(\d{2})/(\d{2})/',target['url'])
    url_date='-'.join(url_match.groups()) if url_match else None
    title=soup.select_one(adapter.get('title_selector','h1'))
    record=dict(unit_id=target['url'],url=target['url'],source_id=target['source_id'],source=adapter['title'],stratum=target['stratum'],country=adapter['country'],edition=adapter['edition'],source_frame=adapter['source_frame'],
        unit_kind='native_publication_page',title=title.get_text(' ',strip=True) if title else '',publication_date=date,date_field=origin,publisher_timestamp=stamp,url_date=url_date,
        raw_path=str(raw.relative_to(core.OWN)),raw_sha256=receipt['raw_sha256'],retrieved_at_utc=receipt['finished_at_utc'],request_id=receipt['request_id'],
        extractor_sha256=core.sha(__file__),renderer_sha256=core.sha(core.OLD/'prototype/parser.py'),adapter=adapter,
        adapter_sha256=core.digest(json.dumps(adapter,sort_keys=True).encode()),historical_body_equivalence='unknown; present-day archive rendition',
        independent_original_work_status='unassessed; native publication identity differs from original-story identity',semantic_labels_executed=False,length_filter_used=False,
        state='retained_boundary_date_pending',readable=False,body_sha256=core.digest(b''),body_path=None)
    if target['source_id']=='mit_tech':
        article=soup.select_one('main.container > article.article')
        stamp_node=article.select_one('.article-meta .timestamp') if article else None
        m=re.search(r'([A-Za-z]+)\.?\s+(\d{1,2}),\s*(\d{4})',stamp_node.get_text(' ',strip=True) if stamp_node else '')
        if m:
            months={dt.date(2000,i,1).strftime('%b').lower():i for i in range(1,13)}
            date=dt.date(int(m[3]),months[m[1][:3].lower()],int(m[2])).isoformat()
            record.update(publication_date=date,date_field='native article displayed timestamp',publisher_timestamp=stamp_node.get_text(' ',strip=True))
    if len(body_nodes)!=1:return record
    node=body_nodes[0]
    byline=soup.select_one(adapter.get('byline_selector','[rel="author"]'))
    record['byline']=byline.get_text(' ',strip=True) if byline else None
    for n in node.select(','.join(adapter.get('exclude_selectors',['script','style','form','svg']))):n.decompose()
    body=renderer.normalise(renderer.render(node))
    record.update(body_sha256=core.digest(body.encode()),paragraph_count=len(node.find_all('p')),table_count=len(node.find_all('table')),body_characters=len(body),
        provenance=adapter.get('provenance','direct newspaper publication; quoted/wire origins remain separate'),body_boundary=adapter['body_selector'],body_completeness=adapter.get('body_completeness','visible native boundary reviewed; paywall/preview not inferred fulltext'))
    path=core.OWN/'bodies'/(receipt['request_id']+'_'+record['body_sha256'][:12]+'.txt')
    budget=core.material_check(len(body.encode())+len(json.dumps(record).encode())*3+262144)
    path.parent.mkdir(exist_ok=True)
    if not path.exists():path.write_text(body)
    record.update(body_path=str(path.relative_to(core.OWN)),material_write_budget=budget,
        readable=bool(body) and core.eligible(date) and (not url_date or date==url_date) and (not target.get('month') or date[:7]==target['month']) and adapter.get('boundary_reviewed',False))
    record['state']='saved_readable_native_unit' if record['readable'] else 'retained_boundary_date_or_preview_pending'
    if record['publication_date']:
        added=core.stage(record);record['new_versions_inserted']=added
    core.append('NEW_NATIVE_UNITS.jsonl',record)
    return record
