"""Owner-evidenced publisher template rules; require subsequent native-body match."""
import json,hashlib,re
from pathlib import Path
from bs4 import Comment,ProcessingInstruction
RULE_FILE=Path(__file__).resolve().parent/'TEMPLATE_CLEANUP_RULES.json'
WIDGET_CLASSES={'meta-tags','herald-share-content','herald-da'}
def clean(dom,facts):
 raw=RULE_FILE.read_bytes();rules=json.loads(raw);rule=rules['rules'].get(facts['source_id'])
 if not rule:return
 nodes=dom.select(rule.get('body_selector','.entry-content.herald-entry-content'))
 if len(nodes)!=1:return
 body=nodes[0]
 if rule.get('decode_public_contact_email'):
  for node in body.select('[data-cfemail]'):
   try:
    encoded=bytes.fromhex(node['data-cfemail']);decoded=bytes(b^encoded[0] for b in encoded[1:]).decode('utf-8')
   except (ValueError,UnicodeDecodeError):continue
   if decoded.count('@')!=1 or any(c.isspace() for c in decoded):continue
   node.string=decoded;facts['published_contact_email_presentation_decoded']=facts.get('published_contact_email_presentation_decoded',0)+1
   facts['public_contact_decode_scope']='Published contact display only; unchanged native whole-body match required; no access boundary bypass'
 facts['template_rule_version']=rules['version'];facts['template_rule_file_sha256']=hashlib.sha256(raw).hexdigest();facts['template_rule_evidence']=rule.get('named_evidence') or rule.get('primary_saved_response_proofs')
 for widget_rule in rule.get('widget_rules',[]):
  widgets=body.select(widget_rule['selector'])
  if len(widgets)!=1:continue
  widget=widgets[0];text=' '.join(widget.get_text(' ',strip=True).split());digest=hashlib.sha256(text.encode()).hexdigest()
  if digest!=widget_rule['normalized_text_sha256']:continue
  widget.decompose();facts['theme_widget_nodes_removed']=facts.get('theme_widget_nodes_removed',0)+1
  facts.setdefault('named_widget_signatures_removed',[]).append(dict(selector=widget_rule['selector'],normalized_text_sha256=digest))
 headings=[h for h in body.select(':scope > '+rule['heading_tag']) if h.get_text(' ',strip=True)==rule['heading_text']] if rule.get('heading_tag') else []
 if len(headings)==1:
  h=headings[0];parts=[];n=h
  while n:
   if getattr(n,'name',None)=='div' and set(n.get('class',[]))&WIDGET_CLASSES:break
   parts.append(n);n=n.next_sibling
  text=' '.join(' '.join(n.get_text(' ',strip=True).split()) for n in parts if getattr(n,'name',None));text=' '.join(text.split());digest=hashlib.sha256(text.encode()).hexdigest();previous=h.find_previous_sibling()
  if digest==rule['normalized_block_sha256'] and previous and previous.name=='hr':
   previous.decompose()
   for n in parts:n.extract()
   facts['site_donation_blocks_removed']=1;facts['site_donation_block_signature']=digest
 for n in body.select(':scope > .herald-da,:scope > .meta-tags,:scope > .herald-share-content'):
  n.decompose();facts['theme_widget_nodes_removed']=facts.get('theme_widget_nodes_removed',0)+1
 for n in body.find_all(string=True):
  ad_comment=isinstance(n,Comment) and (re.fullmatch(r'\s*Error, Ad \(\d+\) is not available at this time due to schedule/budgeting/geolocation/mobile restrictions!\s*',str(n)) or re.fullmatch(r'\s*Error, Advert is not available at this time due to schedule/geolocation restrictions!\s*',str(n)))
  ad_instruction=isinstance(n,ProcessingInstruction) and re.fullmatch(r'php echo adrotate_ad\(\d+\); \?',str(n))
  if ad_comment or ad_instruction:n.extract();facts['adrotate_labels_removed']=facts.get('adrotate_labels_removed',0)+1
