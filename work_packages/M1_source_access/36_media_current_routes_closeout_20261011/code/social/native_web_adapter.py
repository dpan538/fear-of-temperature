"""Native self-hosted WordPress post identities; structural, not semantic selection."""
import urllib.parse,hashlib,pathlib
LOADED_CODE_SHA256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()

def evidence(actor,source):
 keys=('cohort_id','site_id','carrier','genre','source_context_country','source_context_region','source_context_evidence_ref','source_context_observed_at','community_context_scope','author_country','author_country_status','author_country_evidence_type','author_country_evidence_ref','author_country_observed_at')
 result={k:actor.get(k) for k in keys}
 result.update(role_status=actor['role_status'],role_evidence_ref=actor['profile_raw_reference'])
 return result

def wp2_records(data,source,actor):
 rows=[]
 for p in data if isinstance(data,list) else [data]:
  if not isinstance(p,dict) or p.get('type')!='post' or not p.get('id') or not p.get('link'):continue
  if urllib.parse.urlsplit(p['link']).hostname!=urllib.parse.urlsplit(source['base_url']).hostname:continue
  content=p.get('content') or {};protected=bool(content.get('protected')) or p.get('status')!='publish'
  body=content.get('rendered') or ''
  meta={k:v for k,v in p.items() if k not in ('content','excerpt')}
  has_history=source['source_id']=='wp_mochilados' or bool(source.get('documented_migration_history'))
  meta.update(source_expansion_evidence=evidence(actor,source),publication_gmt=p.get('date_gmt'),modified_gmt=p.get('modified_gmt'),source_reports_author_controlled_migration_history=has_history,current_version_migration_and_historical_equivalence='source history documented; each historical body/version not independently verified' if has_history else 'migration history unmeasured; historical body/version not independently verified',permission_raw_reference=source['permission_raw_reference'])
  rows.append({'source_id':source['source_id'],'native_namespace':'wp_native_post','native_post_id':str(p['id']),'source_url':p['link'],'native_unit':'personal_weblog_post','native_created_at':p.get('date'),'native_edited_at':p.get('modified'),'author_id':str(p['author']) if p.get('author') is not None else None,'author_role':'personal_blog_native_author_identity_to_site_owner_pending','body_original':'' if protected else body,'body_format':'html','content_state':'password_protected_preview' if protected else 'complete_native_text' if body else 'bodyless_native_entity','content_license':source['content_license'],'license_basis':'current author text licence; third-party rights excluded; '+source['permission_raw_reference'],'thread_id':source['source_id']+':'+str(p['id']),'flags':{'source_native_WordPress_post':True,'current_body_not_verified_historical_version':True,'migration_same_work_not_new_publication':has_history,'third_party_and_comments_not_covered_by_author_licence':True},'native_fields':meta,'edges':[],'attachments':[]})
  if source.get('licensed_native_author_id') and rows[-1]['author_id']!=source['licensed_native_author_id']:rows[-1].update(body_original='',content_state='native_guest_author_permission_mapping_unresolved')
 return rows
