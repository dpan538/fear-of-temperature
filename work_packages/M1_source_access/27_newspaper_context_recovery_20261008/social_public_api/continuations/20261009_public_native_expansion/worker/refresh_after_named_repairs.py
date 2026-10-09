"""Refresh derived metadata after named repair; accepted terminal checks reused."""
import ast,json
import transport as t,entities as e
from closeout import export,calendar
from finalize_dated_coverage import finalize

def refresh():
 out=t.WORK/'summaries';m=t.read_json(out/'collection_manifest.json')
 tree=ast.parse((t.WORK/'closeout.py').read_text());queries=next(ast.literal_eval(node.value) for node in ast.walk(tree) if isinstance(node,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='queries' for x in node.targets))
 with t.shared(t.footprint(0,24*1048576)):
  c=e.db()
  for name,sql in queries.items():
   item=export(c,name,sql);m['files']=[x for x in m['files'] if x['path']!=item['path']]+[item]
  calendar(c,t.read_json(t.WORK/'source_registry.json'))
  m['counts']={table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in m['counts']}
  m['new_qualified_native_units']=m['counts']['posts']-1566
  m['qualified_by_source']=[dict(zip(['source_id','qualified_native_units'],row)) for row in c.execute('SELECT source_id,COUNT(*) FROM posts GROUP BY source_id')]
  m['complete_independently_authored_body_entities']=c.execute('SELECT COUNT(DISTINCT v.entity_id) FROM entity_versions v JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id WHERE a.independently_authored_body=1').fetchone()[0]
  m['known_native_original_publication_keys']=c.execute('SELECT COUNT(DISTINCT p.publication_key) FROM publication_memberships p JOIN entity_versions v ON v.entity_id=p.entity_id JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id WHERE a.independently_authored_body=1').fetchone()[0]
  c.close();m['changed_tranche_check']['named_native_post_type_repair']=t.read_json(t.WORK/'NATIVE_POST_TYPE_REPAIR.json');m['changed_tranche_check']['raw_body_checks_reused_after_metadata_refresh']=True
  # Final source documentation excludes individual runtime/probe receipts and
  # copied legal text; original evidence remains in the local raw envelope.
  registry=t.read_json(t.WORK/'source_registry.json');keep={'source_id','title','platform','base_url','frame','stratum','author_country_inference','api_documentation','policy_urls','public_read','collection_retention','retention_basis','content_license','open_content','redistribution','geographic_evidence','existence_at','historical_scope','status','existence_basis','public_beta_at','launch_at','era_evidence','audience','geographic_verification','retention_scope','platform_public_start_month','platform_start_evidence','instance_start_unresolved','platform_not_before_month','platform_start_lower_bound_basis','app_evidenced_by_publication_date','app_evidence_content_version_limit','native_api_version','native_site_record_created_at','native_site_record_time_basis','licence_scope_note'}
  final=[]
  for source in registry:
   record={k:v for k,v in source.items() if k in keep}
   if 'native_source_conditions' in source:record['native_source_conditions']={k:source['native_source_conditions'].get(k) for k in ['private_instance','federation_enabled','registration_mode','registration_not_used']}
   final.append(record)
  p=out/'source_registry_final.json';t.atomic(p,final);m['files'].append({'path':str(p.relative_to(t.WORK)),'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())});t.atomic(out/'collection_manifest.json',m)
 finalize()
if __name__=='__main__':
 with t.writer():refresh()
