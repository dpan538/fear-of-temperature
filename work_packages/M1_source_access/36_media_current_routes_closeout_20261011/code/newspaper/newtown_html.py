"""Observed Newtown public archive hrefs and explicit original publication fields."""
import datetime as dt
import re
from urllib.parse import urljoin, urlsplit, parse_qs
from bs4 import BeautifulSoup
import elt

HOST = 'www.newtownbee.com'

def targets(raw, url, receipt):
    soup = BeautifulSoup(raw, 'html.parser')
    result = {}; bucket = parse_qs(urlsplit(url).query).get('month', [None])[0]
    for a in soup.select('a[href]'):
        u = urljoin(url, a['href']); part = urlsplit(u)
        if part.scheme != 'https' or part.hostname != HOST or part.query or not re.fullmatch(r'/\d{8}/[^/]+/', part.path):
            continue
        result[u] = dict(source_id='newtown_bee', url=u, representation='publisher_newtown_native_html', month='', native_evidence=dict(title=a.get_text(' ', strip=True), native_index_receipt=receipt['target_id'], native_archive_bucket=bucket, publication_date_assignment='Pending displayed article publication or verified original archive header; URL/archive bucket is not publication time'))
    return list(result.values())

def discover(p, v, queue, fetch, permitted, policy):
    stage = v.get('stage', 'robots')
    if stage == 'robots':
        policy(p, v); return 1
    if stage == 'native_root':
        rec = fetch(p, p['root_url'], {'purpose': 'Re-use ordinary publisher root; observe archive href only'})
        if rec['status'] != 'saved':
            v.update(stage='blocked', blocked_reason='Public root ' + rec['status']); return 1
        soup = BeautifulSoup(elt.read_payload(rec['raw_reference']), 'html.parser')
        urls = [urljoin(p['root_url'], a['href']) for a in soup.select('a[href]') if urlsplit(urljoin(p['root_url'], a['href'])).hostname == HOST and urlsplit(urljoin(p['root_url'], a['href'])).path == '/article-archive/']
        if not urls:
            v.update(stage='blocked', blocked_reason='No observed public archive href'); return 1
        v.update(stage='archive_index', archive_index_url=urls[0]); return 1
    if stage == 'archive_index':
        url = v['archive_index_url']
        if not permitted(v, url):
            v.update(stage='blocked', blocked_reason='Declared agent archive index disallowed'); return 1
        rec = fetch(p, url, {'purpose': 'Observe public archive month hrefs; buckets never assign publication dates'})
        if rec['status'] != 'saved':
            v.update(stage='blocked', blocked_reason='Archive index ' + rec['status']); return 1
        soup = BeautifulSoup(elt.read_payload(rec['raw_reference']), 'html.parser'); routes = set()
        for a in soup.select('a[href]'):
            u = urljoin(url, a['href']); part = urlsplit(u); month = parse_qs(part.query).get('month', [''])[0]
            if part.hostname == HOST and part.path == '/article-archive/' and re.fullmatch(r'\d{6}', month) and permitted(v, u):
                routes.add(u)
        v.update(stage='native_archive_pages', archive_routes=sorted(routes, key=lambda u: parse_qs(urlsplit(u).query)['month'][0]), archive_consumed=[], queued_native_article_URLs=[], archive_index_receipt=rec['target_id'], population_limit='Observed native HTML archive buckets; imported original dates and mixed original publications require per-article checks, complete historical denominator unknown')
        return 1
    if stage == 'native_archive_pages':
        todo = [u for u in v['archive_routes'] if u not in v['archive_consumed']]
        if not todo:
            v.update(stage='observed_public_frontier_consumed', reason='All observed month/pagination hrefs consumed; not whole-archive completeness'); return 1
        url = todo[0]; v['archive_consumed'].append(url)
        if not permitted(v, url):
            v.setdefault('unpermitted_archive_routes', []).append(url); return 1
        rec = fetch(p, url, {'purpose': 'Observed chronological public archive/pagination href; no private interface or date guessing'})
        if rec['status'] != 'saved':
            v.setdefault('archive_access_limits', []).append(dict(url=url, status=rec['status'])); return 1
        raw = elt.read_payload(rec['raw_reference']); items = targets(raw, url, rec); queue(p['source_id'], items)
        v['queued_native_article_URLs'] = sorted(set(v['queued_native_article_URLs']) | {t['url'] for t in items})
        soup = BeautifulSoup(raw, 'html.parser'); bucket = parse_qs(urlsplit(url).query).get('month', [''])[0]
        for a in soup.select('a[href]'):
            u = urljoin(url, a['href']); part = urlsplit(u); q = parse_qs(part.query)
            if part.hostname == HOST and part.path == '/article-archive/' and q.get('month', [''])[0] == bucket and q.get('start') and ('next' in a.get_text(' ', strip=True).lower() or a.get('rel') == ['next']) and u not in v['archive_routes'] and permitted(v, u):
                v['archive_routes'].insert(v['archive_routes'].index(url) + 1, u)
        v['attempted_pages'] = v.get('attempted_pages', 0) + 1; return 1
    return 0

def original_header(paragraphs):
    if not paragraphs or not re.match(r'^Date:\s*', paragraphs[0]):
        return None, None, None, None
    marker = next((i for i, s in enumerate(paragraphs) if s.strip() == 'Full Text:'), None)
    if marker is None:
        return None, None, None, 'pending_legacy_original_body_boundary'
    header = paragraphs[:marker]; dates = [s for s in header if s.startswith('Date:')]; publications = [s.split(':', 1)[1].strip() for s in header if s.startswith('Publication:')]
    if len(dates) != 1 or len(publications) != 1:
        return None, None, marker, 'pending_legacy_original_identity_date_fields'
    match = re.fullmatch(r'Date:\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{2}-[A-Za-z]{3}-\d{4})', dates[0])
    day = None
    if match:
        try:
            value = dt.datetime.strptime(match[2], '%d-%b-%Y').date()
            if value.strftime('%a') == match[1]: day = value.isoformat()
        except ValueError: pass
    status = 'pending_other_original_publication_frame' if publications[0] != 'Bee' else ('pending_legacy_original_date_conflict' if day is None else None)
    return day, publications[0], marker, status

def parse(raw, sid, url, metadata=None):
    import extract_load
    p = extract_load.ADAPTERS[sid]; soup = BeautifulSoup(raw, 'html.parser'); articles = soup.select('article.article-page'); nodes = soup.select('article.article-page .article-restofcontent'); heads = soup.select('article.article-page h1.article__headline'); dates = soup.select('article.article-page .article-pubdate'); canon = soup.select('link[rel="canonical"][href]')
    uuid = articles[0].get('data-uuid') if len(articles) == 1 else None
    canonical = canon[0]['href'] if len(canon) == 1 else None
    title = heads[0].get_text(' ', strip=True) if len(heads) == 1 else None; stamp = dates[0].get_text(' ', strip=True) if len(dates) == 1 else None; site_day = None
    match = re.match(r'^Published:\s*([A-Za-z]+ \d{1,2}, \d{4})\b', stamp or '')
    if match:
        for fmt in ['%b %d, %Y', '%B %d, %Y']:
            try: site_day = dt.datetime.strptime(match[1], fmt).date().isoformat(); break
            except ValueError: pass
    identity_ok = bool(uuid and re.fullmatch(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}', uuid) and canonical and urlsplit(canonical).hostname == HOST and elt.canon(canonical) == elt.canon(url))
    record = dict(article_id=sid + ':uuid:' + uuid if identity_ok else elt.article_id(sid, url), source_id=sid, source=p['title'], source_url=canonical if identity_ok else url, raw_source_url=url, url_aliases=sorted({url, canonical} - {None}), source_native_article_uuid=uuid, title=title, source_display_title=title, publication_date=site_day, date_field='Unique publisher displayed Published field', publisher_timestamp=stamp, site_archive_display_date=site_day, content_version_time=None, stratum=p['stratum'], country=p['country'], edition=p['edition'], source_frame=p['frame'], retention_limit=p['retention_limit'], provenance='direct publisher newspaper web utterance; historical archive rendition and quoted origins separately recorded', historical_body_equivalence='unknown; current retrieved publisher archive rendition', semantic_labels_executed=False, length_filter_used=False)
    if metadata: record.update(metadata)
    if not identity_ok: return record, '', 'pending_native_uuid_or_canonical_identity'
    if len(nodes) != 1: return record, '', 'pending_missing_or_nonunique_original_body'
    node = nodes[0]
    for n in node.select('script,style,form,svg,nav,aside'): n.decompose()
    body = elt.renderer.normalise(elt.renderer.render(node)); paragraphs = [n.get_text(' ', strip=True) for n in node.select('p')]
    day, publication, marker, status = original_header(paragraphs)
    legacy_signal = bool((title or '').startswith('Date:') or (any(s.startswith('Publication:') for s in paragraphs) and 'Full Text:' in paragraphs))
    if marker is None and legacy_signal:
        record.update(publication_date=None, date_field='Legacy original publication unresolved; website/archive Published field retained separately')
        status = status or 'pending_legacy_original_identity_date_fields'
    if marker is not None:
        record.update(original_publication_code=publication, original_archive_header=paragraphs[:marker], original_header_day=day, publication_date=day, date_field='Explicit original Date field with weekday validation within publisher archive body', observed_date_fields=[['site displayed archive Published', stamp], ['original archive Date', paragraphs[0]]], provenance='publisher-hosted archival reproduction of original newspaper utterance; website/archive time distinct from original publication')
        title_lines = [s for s in paragraphs[marker + 1:] if s and not s.startswith('(')]
        if title_lines: record['title'] = title_lines[0]; record['title_scope'] = 'First explicit original body headline line; complete source display title/header retained separately'
    record.update(body_boundary='Unique article.article-page .article-restofcontent; full source paragraph order and archive header retained', paragraph_count=len(paragraphs), article_boundary_evidence='One stable source UUID, exact native canonical permalink, unique source title/date/content container; native archive is not a page or issue fragment')
    if status: return record, body, status
    if marker is not None and title and title.startswith('Date:') and title != paragraphs[0]: return record, body, 'pending_legacy_title_header_date_conflict'
    readable = BeautifulSoup(str(node), 'html.parser')
    if marker is not None:
        # Original archive metadata is retained, but is not original article TEXT.
        for n in readable.select('p')[:marker + 1]: n.decompose()
    for n in readable.select('table,h1,h2,h3,h4,h5,h6,iframe,object,embed'): n.decompose()
    if not any(c.isalnum() for c in readable.get_text(' ', strip=True)): return record, body, 'pending_missing_original_text_after_legacy_header' if marker is not None else 'pending_nontext_original_or_component_body'
    if paragraphs and paragraphs[0].startswith('Date:') and marker is None: return record, body, 'pending_legacy_original_body_boundary'
    if not body or not title: return record, body, 'pending_empty_original_body_or_title'
    if node.select('.paywall,.subscription-wall,.article-preview,.subscriber-only'): return record, body, 'pending_visible_preview_or_paywall'
    if not elt.eligible(record['publication_date']): return record, body, 'pending_original_date_outside_fixed_interval_or_missing'
    return record, body, 'confirmed_complete'
