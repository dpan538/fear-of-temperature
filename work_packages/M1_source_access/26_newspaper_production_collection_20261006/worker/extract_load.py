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
exec(compile(_source, str(_previous), 'exec'))
import indaily
ADAPTERS['indaily']=indaily.FRAME
_retained_parse=parse
def parse(raw,sid,url,metadata=None):
 return indaily.parse(raw,url,metadata) if sid=='indaily' else _retained_parse(raw,sid,url,metadata)
