"""Named publisher migration wrapper that does not establish an original body."""
import re
from bs4 import BeautifulSoup
def clean(dom,sid):
 facts=dict(source_id=sid,generated_teaser_removed=False,original_text_removed=False)
 if sid!='haringey_community_press':return facts,None
 first=dom.find('strong')
 if not first or first.find('author') is None:return facts,None
 marker=re.search(r'\[\u2026\]By(?:\s|$)',first.get_text(' ',strip=True))
 if not marker:return facts,None
 paragraph=first.find_parent('p')
 if not paragraph:return facts,'pending_publisher_migrated_teaser_original_body_mapping'
 prefix=first.get_text(' ',strip=True)[:marker.start()]
 tail=BeautifulSoup(str(dom),'html.parser');copy=tail.find('strong').find_parent('p');copy.decompose()
 remaining=re.sub(r'\s+','',tail.get_text(' ',strip=True));prefix=re.sub(r'\s+','',prefix)
 if not prefix or not remaining.startswith(prefix):
  facts['generated_teaser_prefix_absent_from_remaining_body']=True
  return facts,'pending_publisher_migrated_teaser_original_body_mapping'
 paragraph.decompose();facts.update(generated_teaser_removed=True,full_current_original_prefix_restored_from_publisher_text=True,scope='Exact leading publisher teaser wrapper and author tag; intact original remainder begins with the complete pre-truncation prefix')
 return facts,None
def disposition(obj,sid):
 return clean(BeautifulSoup(obj.get('content',{}).get('rendered',''),'html.parser'),sid)[1]
