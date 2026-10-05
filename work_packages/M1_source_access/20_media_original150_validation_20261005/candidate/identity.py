import hashlib,json
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
PARENT_ID_RULE="source_edition_native_v2"
def require(c,msg):
 if not c:raise RuntimeError(msg)
def canonical(url):
 p=urlsplit(url);query=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}]
 return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path,urlencode(query),''))
def native_identity_key(url,native=None,issue_native=None):
 # Preserve native article identity; namespace IDs that are only unique per issue.
 if issue_native is not None:
  require(bool(native) and bool(issue_native),'Issue-scoped identity requires native issue and article IDs')
  return json.dumps(['issue_article',str(issue_native),str(native)],ensure_ascii=False,separators=(',',':'))
 if native is not None:
  require(bool(str(native)),'Empty provider native ID is not identity evidence')
  value=['native_article',str(native)]
 else:
  require(bool(url),'Native identity or canonical URL required');value=['canonical_url',canonical(url)]
 return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def parent_from_identity_key(source,edition,key):
 require(bool(source) and bool(edition),'Source and declared edition scope required')
 token=json.dumps([PARENT_ID_RULE,source,edition,key],ensure_ascii=False,separators=(',',':'))
 return 'article:v2:'+hashlib.sha256(token.encode()).hexdigest()[:32]
def native_parent(source,edition,url,native=None,issue_native=None):
 return parent_from_identity_key(source,edition,native_identity_key(url,native,issue_native))
def native_issue(source,edition,issue_native):
 require(bool(source) and bool(edition) and bool(issue_native),'Source, edition and provider issue ID required')
 token=json.dumps(['source_edition_issue_v2',source,edition,str(issue_native)],ensure_ascii=False,separators=(',',':'))
 return 'issue:v2:'+hashlib.sha256(token.encode()).hexdigest()[:32]
