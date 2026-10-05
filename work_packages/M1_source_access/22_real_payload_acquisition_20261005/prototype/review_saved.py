"""Apply this round's explicit inspected-unit decisions, never approve new targets."""
import re
from bs4 import BeautifulSoup
import media, transport as t
APPROVED_IDS=set('''015f71a71aa7780421b6a34b 09d91bd1f1cf3dcad5f1ff95 1582bb864dabd034feb94781 1f5d9a6c0d775718bb890e57 2f42c07b84580b63427f7e6f 36ad17d41dde6e25550a31f6 483328ea5fb44cd0ec1d938d 49ca3e5952c69a77a5319fdc 4a33964c784265dddf5e09ee 5df79929d5b9164f3bb039df 61e487450e1cedfaa1fe7555 7063d3483565ab9c0a316193 7b5af79ffa0226ce4536a59b 81e9f63a130c6d382a265fab a23105d7990db800c92cf9af a2dc8ed704671f6226f293d1 b94defddae6edeff2be50661 ba3f9e20b1673f3a0e377047 bc9ec630e70c35c18509be2e ca1698af14973f0b5c0ba528 d2840e410428b1a288765b1e d57278a7245de10d4cd6d0e8 d742d1d7d66a431c1bd00831 e59c717371eb5608131ca8ee fa1741a1f0153ee7131f1b34'''.split())
PARTIAL={
 '22e9e8260422720d86ba69f7':('linked_editorial_summary','One paragraph with external story link; complete publisher summary, linked original not acquired. Do not count as complete underlying article.'),
 '7c2cb761bde98e3f3400570c':('linked_editorial_summary','One paragraph linked to Denver Post. Readable publisher summary, original not acquired.'),
 '9f3176f2f52cabddd258b6ae':('partner_review_excerpt','Kirkus partner review ends with explicit full-review link. Preserve excerpt, not full review.'),
 'f5652920086e8cb57473001b':('wire_partner_excerpt','Tanya Eiserer/WFAA-TV byline and explicit read-more WFAA link. Underlying full article not acquired.'),
 '11d2cfb8bd268084f49d0741':('podcast_landing_text','Four paragraphs introduce a podcast; episode/transcript not acquired. Landing prose readable, full episode narrative unavailable.'),
 'cec0974178f7e9336c367e5e':('image_component_pending','Narrative includes two updates followed by images of provider statements; image bytes/OCR not acquired. Full statement component unavailable.')}
BYLINE={'015f71a71aa7780421b6a34b':'Helen Karakulak','5df79929d5b9164f3bb039df':'The Conversation; Alison Reeve credited in standfirst','a23105d7990db800c92cf9af':'Savannah Meacham, AAP','b94defddae6edeff2be50661':'David Simmons; Helena Snelling','7b5af79ffa0226ce4536a59b':'Owen Dahlkamp; Emily Foxhall contributor credit outside narrative separators','81e9f63a130c6d382a265fab':'Stephen Simpson','ba3f9e20b1673f3a0e377047':'Martha Pskowski, Inside Climate News','ca1698af14973f0b5c0ba528':'Aman Batheja','d57278a7245de10d4cd6d0e8':'Julie Appleby, KFF Health News'}
RIGHTS={
 'texastribune':'Saved primary public republication guidelines, per-page attribution/CC notice and2019terms limited reproduction licence; copyright/third-party providers separate. No public raw/text redistribution.',
 'spinoff':'Copyright retained; public robots observation. Primary Our Story verifies2014foundation and NZ edition; October2026Use of AI concerns publisher production, not a grant for corpus reuse. Research retention/redistribution licence unresolved; local bounded evidence only.',
 'indaily':'Copyright retained; saved publisher terms pointer currently leads to privacy/cookie material. General research retention grant unresolved; no open licence invented. Conversation article carries its own CC republication notice with version unspecified. No public raw/text redistribution.',
 'canary':'Copyright retained; saved robots permits observed research/AI-agent paths with5seconddelay. No open licence asserted; research retention grant unresolved. UK market/native en-GB edition verified, legal HQ verification pending.'}
def author_name(a):
 v=a.get('author');v=v if isinstance(v,list) else [v]
 return '; '.join(x.get('name','') for x in v if isinstance(x,dict) and x.get('name')) or 'Native author reference retained; legal identity unresolved'
def apply_reviews():
 for p in sorted((t.OUT/'media/parsed').glob('*.json')):
  a=t.read(p);rid=a['request_id']
  if a.get('visible_body_verified'):continue
  if rid in PARTIAL:
   unit,note=PARTIAL[rid];a.update(unit_classification=unit,boundary_status='readable_partial_or_secondary_unit_not_complete_article',inspection_note=note,structural_retention='Preserved; no topic/affect/length exclusion');t.save(p,a);continue
  if a['paywall_or_preview']:
   a.update(unit_classification='account_gated_preview',boundary_status='preview_not_complete',inspection_note='Visible publisher account CTA prevents complete DOM body. No registration, login or gate bypass.');t.save(p,a);continue
  if rid not in APPROVED_IDS:raise RuntimeError('No explicit inspected decision for '+rid)
  source=a['source_id'];byline=BYLINE.get(rid,author_name(a));directness='direct publisher media discourse';origin='Named publisher/contributor reporting or commentary; linked/quoted claims remain distinct; no external-provider credit observed'
  if rid in {'ba3f9e20b1673f3a0e377047','d57278a7245de10d4cd6d0e8','a23105d7990db800c92cf9af','5df79929d5b9164f3bb039df'}:
   directness='mixed: direct publisher edition, attributed external-provider adoption';origin={'ba3f9e20b1673f3a0e377047':'Inside Climate News','d57278a7245de10d4cd6d0e8':'KFF Health News','a23105d7990db800c92cf9af':'AAP','5df79929d5b9164f3bb039df':'The Conversation; original link observed, original not fetched'}[rid]
  note='Actual unique DOM article container, complete visible narrative/heading/quote/attribution flow and terminal passage inspected; no account gate or missing next-page control. Images, audio and video are not acquired or transcribed; completeness refers to HTML prose, not all embedded media.'
  if source=='texastribune':note+=' July newsletter/event blocks excluded using the two inspected direct separators; December donation/widget sections excluded. Central displayed day mapped separately from UTC. Provider/adoption credit retained as metadata.'
  if source=='indaily':note+=' Recommendations, newsletters and explicitly sponsored video removed by attributes/ID; substantive event table and authored TOC retained. Visible publication date/canonical/native path agree; en_GB template locale does not reassign AU.'
  if source=='spinoff':note+=' Native header day equals timestamp converted to Pacific/Auckland. Image captions retained; illustrated column has no claimed image-text transcription. Stated2026modification remains separate.'
  if source=='canary':note+=' Native dated URL/Article date/h1/byline align; share/tag widgets removed. Embedded video commentary remains a complete prose article, without the video/transcript.'
  review=dict(identity_verified=True,publication_verified=True,source_edition_verified=True,complete_visible_body=True,no_continuation_missing=True,no_preview=True,rights_reviewed=True,first_body_line=a['body_text'].splitlines()[0],last_body_line=a['body_text'].splitlines()[-1],source_edition=next(x['edition'] for x in t.read(t.OUT/'control/CANDIDATES.json')['candidates'] if x['source_id']==source),publisher_country=next(x['publisher_country'] for x in t.read(t.OUT/'control/CANDIDATES.json')['candidates'] if x['source_id']==source),byline=byline,directness=directness,originality=origin,rights_status=RIGHTS[source],inspection_note=note,historic_version='Later retrieval does not establish historical body equality',redistribution='No public raw/text redistribution',verification_method='Model-assisted direct saved DOM/passage inspection; no independent human second review claimed',media_component_scope='Complete HTML prose only; separate embedded components remain unacquired')
  a=media.certify(rid,review);print(rid,source,a['body_bytes'])
if __name__=='__main__':apply_reviews()
