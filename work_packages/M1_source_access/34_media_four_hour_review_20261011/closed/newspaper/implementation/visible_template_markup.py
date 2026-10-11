"""Exact saved publisher DOM artefacts; preserve original HTML bytes."""
import re
from bs4 import BeautifulSoup,Comment
import elt
VERSION='publisher-visible-template-20261011-v1'
def clean(raw,sid):
 dom=BeautifulSoup(raw,'html.parser');facts=dict(version=VERSION,source_id=sid,hidden_featured_blocks_removed=0,template_comment_labels_removed=0,related_widgets_removed=0,raw_HTML_changed=False,article_narrative_removed=False)
 if sid in ['castlemaine_mail','gippsland_times']:
  nodes=dom.select('.td-post-content');styles='\n'.join(n.get_text() for n in dom.select('style'))
  rules=re.findall(r'\.td-post-featured-image\s*\{([^{}]*)\}',styles)
  hidden=bool(rules) and all(re.search(r'(?:^|;)\s*display\s*:\s*none\s*(?:;|$)',r) for r in rules)
  if len(nodes)==1 and hidden:
   for n in nodes[0].select(':scope > .td-post-featured-image'):n.decompose();facts['hidden_featured_blocks_removed']+=1
  if len(nodes)==1:
   for n in nodes[0].find_all(string=lambda n:isinstance(n,Comment) and str(n).strip() in ['image','content']):n.extract();facts['template_comment_labels_removed']+=1
 if sid=='chester_telegraph':
  for n in dom.select('.post .entry #jp-relatedposts'):n.decompose();facts['related_widgets_removed']+=1
 cleaned=str(dom).encode();facts['derived_markup_sha256']=elt.sha(cleaned);facts['original_raw_sha256']=elt.sha(raw)
 return cleaned,facts


def access_boundary(raw,selectors):
 dom=BeautifulSoup(raw,'html.parser')
 for selector in selectors:
  nodes=dom.select(selector)
  if not nodes:continue
  if len(nodes)!=1:return None
  body=nodes[0];forms=body.select('form#mepr_loginform');markers=body.select('.mepr-unauthorized-excerpt,.mepr-unauthorized-message')
  if forms and markers:return dict(kind='publisher_MemberPress_unauthorized_article_excerpt_and_login_form',body_selector=selector,form_action= forms[0].get('action'),form_method=forms[0].get('method'),article_original_complete_body_unverified=True,login_or_account_attempted=False)
  return None
 return None
