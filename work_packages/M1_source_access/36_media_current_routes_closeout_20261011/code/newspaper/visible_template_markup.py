"""Exact saved publisher DOM artefacts; preserve original HTML bytes."""
import re
from bs4 import BeautifulSoup,Comment
import elt
VERSION='publisher-visible-template-20261011-v3'
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
 import publisher_template_rules
 publisher_template_rules.clean(dom,facts)
 facts['raw_HTML_changed']=any(facts.get(k,0) for k in ['hidden_featured_blocks_removed','template_comment_labels_removed','related_widgets_removed','site_donation_blocks_removed','theme_widget_nodes_removed','adrotate_labels_removed','published_contact_email_presentation_decoded'])
 cleaned=str(dom).encode();facts['derived_markup_sha256']=elt.sha(cleaned);facts['original_raw_sha256']=elt.sha(raw)
 return cleaned,facts


def access_boundary(raw,selectors):
 dom=BeautifulSoup(raw,'html.parser')
 for selector in selectors:
  nodes=dom.select(selector)
  if not nodes:continue
  if len(nodes)!=1:return None
  body=nodes[0]
  box=body.select_one('#iteras-paywall-box.iteras-paywall-box[data-snippet-size]');truncated=body.select_one('.iteras-content-truncated.iteras-no-pass');page_body=dom.select_one('body.no-access')
  if box and truncated and page_body and box.select_one('a[href*="/login/"]'):return dict(kind='publisher_Iteras_no_access_truncated_article_and_subscription_login',body_selector=selector,snippet_size=box.get('data-snippet-size'),article_original_complete_body_unverified=True,login_or_account_attempted=False)
  forms=body.select('form#mepr_loginform');markers=body.select('.mepr-unauthorized-excerpt,.mepr-unauthorized-message')
  if forms and markers:return dict(kind='publisher_MemberPress_unauthorized_article_excerpt_and_login_form',body_selector=selector,form_action= forms[0].get('action'),form_method=forms[0].get('method'),article_original_complete_body_unverified=True,login_or_account_attempted=False)
  return None
 return None
