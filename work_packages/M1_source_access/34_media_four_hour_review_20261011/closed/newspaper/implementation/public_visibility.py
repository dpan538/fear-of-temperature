"""New subscription-capable titles: bind native JSON to visible original HTML."""
import elt,broaden,extract_load

def verify(record,body,profile):
 """Keep uncertain representations pending; never bypass a source access stop."""
 url=record['source_url'];sid=record['source_id'];state=broaden._state().get(sid,{})
 if not broaden._permitted(state,url):
  record['public_HTML_mapping_status']='Declared research-agent original article route is unavailable'
  return 'pending_public_original_HTML_access_mapping'
 try:
  receipt=elt.fetch(url,sid,record['stratum'],'article',{'purpose':'Current unprotected public original HTML visibility, native ID/date/body mapping','native_post_ID':record['source_native_post_id'],'JSON_request_id':record['request_id'],'no_account_subscription_or_private_interface':True},extra={'native_target_identity':url,'kind':'original_public_HTML_visibility'})
 except ValueError as error:
  record['public_HTML_mapping_status']=str(error)
  return 'pending_public_original_HTML_access_mapping'
 record.update(public_HTML_request_id=receipt['target_id'],public_HTML_raw_reference=receipt.get('raw_reference'),public_HTML_raw_sha256=receipt.get('raw_sha256'))
 if receipt['status']!='saved':
  record['public_HTML_mapping_status']=receipt['status']
  return 'pending_public_original_HTML_access_mapping'
 raw=elt.read_payload(receipt['raw_reference']);parsed,visible,status=parse_visible(raw,sid,receipt['final_url'],record)
 return evaluate(record,body,parsed,visible,status,raw)

def parse_visible(raw,sid,url,record):
 import visible_template_markup
 boundary=visible_template_markup.access_boundary(raw,extract_load.ADAPTERS[sid]['selectors'])
 cleaned,facts=visible_template_markup.clean(raw,sid)
 record['public_HTML_structural_cleanup']=facts
 parsed,visible,status=extract_load._retained_parse(cleaned,sid,url)
 if boundary:
  record['public_HTML_access_boundary']=boundary
  status='pending_public_original_HTML_membership_access_limit'
 return parsed,visible,status

def evaluate(record,body,parsed,visible,status,raw):
 url=record['source_url']
 record.update(public_HTML_mapping_parser_status=status,public_HTML_publication_date=parsed.get('publication_date'),public_HTML_body_sha256=elt.sha(visible.encode()),public_HTML_body_boundary=parsed.get('body_boundary') or parsed.get('article_boundary_evidence'))
 if status=='pending_public_original_HTML_membership_access_limit':return status
 if status!='confirmed_complete':return 'pending_public_original_HTML_identity_date_or_boundary'
 if elt.canon(parsed['source_url'])!=elt.canon(url):return 'pending_public_HTML_native_identity_date_conflict'
 if parsed.get('publication_date')!=record.get('publication_date'):
  import source_local_publication_time
  if not source_local_publication_time.reconcile(record,parsed,raw):return 'pending_public_HTML_native_identity_date_conflict'
 if ' '.join((parsed.get('title') or '').split())!=' '.join((record.get('title') or '').split()):
  return 'pending_public_HTML_native_title_mapping'
 if elt.sha(visible.encode())!=elt.sha(body.encode()):
  return 'pending_public_HTML_native_body_version_mapping'
 record.update(public_HTML_mapping_status='Verified matching full currently visible original HTML and native JSON article body',subscription_bypass_used=False,historical_body_equivalence='unknown; current public representations agree, historical body version not established')
 return 'confirmed_complete'
