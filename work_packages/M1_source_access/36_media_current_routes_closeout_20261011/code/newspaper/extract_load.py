"""Reuse accepted article-boundary parsers; decode new raw storage at the reader."""
import pathlib
import elt
_previous = elt.PREVIOUS / 'extract_load.py'
_source = _previous.read_text()
_source = _source[:_source.index('def cache_recovery():')]
_needle = "raw=elt.REPO/rec['raw_reference']"
assert _source.count(_needle) == 1
_source = _source.replace(_needle, "raw=elt.PayloadPath(elt.REPO/rec['raw_reference'])")
_needle = "(elt.REPO/api_rec['raw_reference']).read_text()"
assert _source.count(_needle) == 1
_source = _source.replace(_needle, "elt.read_payload(api_rec['raw_reference']).decode('utf-8')")
_source=_source.replace("try:rec=elt.fetch(target['url']","try:rec=elt._receipt(target['saved_request_id']) if target.get('saved_request_id') else elt.fetch(target['url']")
_source=_source.replace("body=elt.renderer.normalise(elt.renderer.render(node));assert url","__import__('migrated_title_boundary').clean(node,sid);body=elt.renderer.normalise(elt.renderer.render(node));assert url")
exec(compile(_source, str(_previous), 'exec'))
import indaily
ADAPTERS['indaily']=indaily.FRAME
_retained_parse=parse
def parse(raw,sid,url,metadata=None):
 import broaden
 profile=next((p for p in broaden.profiles() if p['source_id']==sid),{})
 if profile.get('interface_type')=='publisher_evidenced_wp_theme_HTML':
  import cambridge_html
  return cambridge_html.parse(raw,sid,url,metadata)
 if sid=='newtown_bee':
  import newtown_html
  return newtown_html.parse(raw,sid,url,metadata)
 if profile.get('interface_type')=='publisher_evidenced_archive_HTML':
  import archive_html
  return archive_html.parse(raw,sid,url,metadata)
 if sid=='galway_advertiser':
  import galway_html
  return galway_html.parse(raw,sid,url,metadata)
 if sid=='camden_new_journal' or (profile.get('interface_type')=='publisher_native_sitemap' and profile.get('article_template')=='Article__container'):
  import native_html
  return native_html.parse(raw,sid,url,metadata)
 return indaily.parse(raw,url,metadata) if sid=='indaily' else _retained_parse(raw,sid,url,metadata)

_current_acquire=acquire
def acquire(target):
 import broaden
 profile=next((p for p in broaden.profiles() if p['source_id']==target['source_id'] and broaden.approved(p)),{})
 if target['source_id']=='copenhagen_post' or profile.get('public_HTML_first_required'):
  import public_first
  return public_first.acquire(target,_current_acquire)
 return _current_acquire(target)
