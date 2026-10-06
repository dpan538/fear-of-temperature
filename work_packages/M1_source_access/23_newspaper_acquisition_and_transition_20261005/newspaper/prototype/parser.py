"""New derivative parser. Eligibility/completeness require adapter evidence and review.

Inline nodes concatenate exactly as the DOM does; only block boundaries insert newlines.
No request-ID completion whitelist, topic filter, or minimum-length admission rule.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit, parse_qs
from bs4 import BeautifulSoup, NavigableString, Tag

BLOCKS = {'p','div','section','article','header','footer','h1','h2','h3','h4','h5','h6',
          'ul','ol','li','blockquote','figure','figcaption','table','thead','tbody','tr'}
SKIP = {'script','style','noscript','template'}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def parser_digest() -> str:
    return digest(Path(__file__).read_bytes())

def render(node) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag) or node.name in SKIP:
        return ''
    if node.name == 'br':
        return '\n'
    text = ''.join(render(child) for child in node.children)
    if node.name in {'td','th'}:
        return text + '\t'
    return '\n' + text + '\n' if node.name in BLOCKS else text

def normalise(text: str) -> str:
    # Preserve explicit table-cell separators and paragraph/line boundaries.
    lines = [re.sub(r'[^\S\n\t]+', ' ', s).strip(' \r') for s in text.split('\n')]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()

def extract(html: bytes, *, selector: str, remove=(), boundary_evidence: str,
            unit_kind='article') -> dict:
    if not boundary_evidence:
        raise ValueError('An adapter requires recorded boundary evidence')
    soup = BeautifulSoup(html, 'html.parser')
    nodes = soup.select(selector)
    if len(nodes) != 1:
        return {'state':'unresolved_boundary','node_count':len(nodes), 'body':''}
    root = nodes[0]
    for css in remove:
        for node in root.select(css):
            node.decompose()
    body = normalise(render(root))
    preview = bool(soup.select('[class*="paywall"], [class*="subscriber-only"], [data-paywall]'))
    state = ('container_only' if unit_kind != 'article' else
             'preview_or_access_marker' if preview else
             'structural_candidate' if body else 'empty_extraction')
    return {'state':state,'body':body,'body_sha256':digest(body.encode()),
            'raw_sha256':digest(html),'parser_sha256':parser_digest(),
            'adapter_sha256':digest(json.dumps({'selector':selector,'remove':list(remove),
                 'boundary_evidence':boundary_evidence,'unit_kind':unit_kind},sort_keys=True).encode()),
            'selector':selector,'removed_selectors':list(remove),
            'boundary_evidence':boundary_evidence,'unit_kind':unit_kind,
            'prose_completeness':'unverified_until_adapter_review',
            'semantic_labels_executed':False}

def native_identity(url: str, family: str) -> str:
    """Only documented public URL families; container identities remain containers."""
    parts = urlsplit(url)
    if family == 'trove_article':
        match = re.fullmatch(r'/newspaper/article/(\d+)/?', parts.path)
        if not match:
            raise ValueError('Not a Trove article URL')
        return match.group(1)
    if family == 'veridian_article':
        q = parse_qs(parts.query)
        value = q.get('d', [''])[0]
        if q.get('a') != ['d'] or not re.fullmatch(r'[A-Za-z0-9_-]+\.\d+\.\d+', value):
            raise ValueError('Not an evidenced Veridian article-shaped identifier')
        return value
    if family == 'publisher_canonical':
        return parts.netloc.lower() + parts.path.rstrip('/')
    raise ValueError('Unsupported identity family')

def enumerate_links(html: bytes, base_url: str, href_pattern: str) -> dict:
    """Native DOM order; deduplicate links, not articles from different editions.

    One bounded page is not a complete month. The caller records date filters,
    verifies dates, preserves pagination and freezes a frame before any bodies.
    """
    soup = BeautifulSoup(html, 'html.parser')
    seen, links = set(), []
    for a in soup.select('a[href]'):
        url = urljoin(base_url, a['href'])
        if re.search(href_pattern, url) and url not in seen:
            seen.add(url)
            links.append({'native_order':len(links)+1,'url':url})
    nxt = soup.select_one('a[rel~="next"]')
    return {'links':links,'next_url':urljoin(base_url,nxt['href']) if nxt else None,
            'frame_complete':False,'order':'native_DOM','topic_query':None,
            'unknown_eligible_denominator':True,'html_sha256':digest(html)}
