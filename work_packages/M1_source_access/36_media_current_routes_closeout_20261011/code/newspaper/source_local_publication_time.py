"""Exact source-provided local timestamp / UTC publication-instant equivalence."""
import datetime as dt,re
from bs4 import BeautifulSoup
import elt

def iso(value):
 try:return dt.datetime.fromisoformat(value.replace('Z','+00:00'))
 except (ValueError,AttributeError):return None

def reconcile(record,parsed,raw):
 """Correct a UTC-prefix parser day only with explicit same-source clock proof."""
 if parsed.get('publication_date')==record.get('publication_date'):return False
 api=iso(record.get('publisher_timestamp'))
 if not api or api.date().isoformat()!=record.get('publication_date'):return False
 soup=BeautifulSoup(raw,'html.parser');canonical=soup.select('link[rel="canonical"][href]')
 if len(canonical)!=1 or elt.canon(canonical[0]['href'])!=elt.canon(record['source_url']):return False
 machine=soup.select('meta[property="article:published_time"][content]')
 if len(machine)!=1:return False
 published=iso(machine[0]['content'])
 if not published or published.tzinfo is None or parsed.get('publication_date')!=published.date().isoformat():return False
 matches=[]
 for node in soup.select('time[datetime]'):
  if any('latest-posts' in str(c) or 'related' in str(c) for c in node.get('class',[])):continue
  local=iso(node['datetime'])
  if not local or local.tzinfo is None:continue
  if local.replace(tzinfo=None)!=api.replace(tzinfo=None):continue
  if local.astimezone(dt.timezone.utc)!=published.astimezone(dt.timezone.utc):continue
  if api.tzinfo is not None and api.astimezone(dt.timezone.utc)!=published.astimezone(dt.timezone.utc):continue
  matches.append((node,local))
 if len(matches)!=1:return False
 node,local=matches[0]
 record.update(public_HTML_original_parser_publication_date=parsed['publication_date'],public_HTML_source_local_timestamp=node['datetime'],public_HTML_visible_publication_line=node.get_text(' ',strip=True),public_HTML_UTC_publication_timestamp=machine[0]['content'],public_HTML_source_local_date_equivalence_verified=True,public_HTML_date_mapping_basis='Unique canonical source page; original article:published_time and unique explicit-offset time represent the same instant; time wall-clock equals native API publication timestamp exactly; no country/rerun/lastmod inference')
 parsed['publication_date']=local.date().isoformat()
 record['public_HTML_publication_date']=parsed['publication_date']
 return True
