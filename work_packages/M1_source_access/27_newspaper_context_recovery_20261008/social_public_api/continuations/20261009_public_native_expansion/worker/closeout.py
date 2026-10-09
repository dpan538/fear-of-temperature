"""One terminal changed-tranche check and non-body export; predecessor reused."""
import csv,datetime as dt,gzip,json,sqlite3,time
from pathlib import Path
import transport as t,entities as e
from enrich_relations import enrich
from finalize_metadata import finalize
from raw_catalog import catalog
OUT=t.WORK/'summaries'
def export(c,name,sql,params=()):
 cur=c.execute(sql,params);p=OUT/name
 with p.open('w',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow([x[0] for x in cur.description]);w.writerows(cur)
 return {'path':str(p.relative_to(t.WORK)),'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())}
def calendar(c,registry):
 months=[]
 for y in range(1988,2027):
  for m in range(1,13):
   if y==2026 and m>9:break
   months.append(f'{y}-{m:02}')
 observed={(s,m):n for s,m,n in c.execute("SELECT source_id,substr(native_created_at,1,7),COUNT(*) FROM posts GROUP BY source_id,substr(native_created_at,1,7)")}
 lower={'se_sustainability':('2013-01','documented_beta'), 'se_earthscience':('2014-04','documented_beta; earlier_native_day_conflicts_retained'), 'python_discourse':('2018-09','native_installation_date'),**{s:('2016-10','platform_lower_bound; instance_era_unknown') for s in ['mastodon_ie','mastodon_uk','mastodon_au','mastodon_us','mastodon_nz']},'bluesky':('2019-01','project_lower_bound; public_app_and_actor_eras_unknown')}
 title_evidence={(sid,month):n for sid,month,n in c.execute("SELECT n.source_id,substr(n.native_created_at,1,7),COUNT(DISTINCT n.entity_id) FROM native_entities n JOIN entity_versions v ON v.entity_id=n.entity_id WHERE v.content_state='native_title_only_text' AND v.fixed_interval_state='inside_fixed_interval' GROUP BY n.source_id,substr(n.native_created_at,1,7)")}
 p=OUT/'source_month_calendar.csv';pooled=set()
 with p.open('w',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow(['source_id','source_stratum','month','complete_native_body_units','native_title_only_evidence','state','era_basis','september_partial'])
  for s in registry:
   sid=s['source_id'];bound,basis=lower.get(sid,(None,'founding_era_unknown; installation/import_dates_not_assumed_source_inception'))
   for month in months:
    n=observed.get((sid,month),0)
    if n:state='observed_complete_text';pooled.add(month)
    elif title_evidence.get((sid,month),0):state='observed_title_only_evidence_not_complete_body_coverage'
    elif bound and month<bound:state='structurally_inapplicable_under_conservative_lower_bound'
    elif s.get('collection_retention') not in ('permitted',):state='access_or_source_condition_blocked_or_unresolved'
    elif bound and sid.startswith('se_') or sid=='python_discourse' and bound and month>=bound:state='applicable_unobserved'
    else:state='historical_scope_unknown'
    w.writerow([sid,s.get('stratum','GLOBAL'),month,n,title_evidence.get((sid,month),0),state,basis,int(month=='2026-09')])
 return len(pooled),len(months)
def closeout():
 started=time.monotonic();timings={}
 OUT.mkdir(exist_ok=True)
 enrich();timings['explicit_new_relation_derivation_seconds']=time.monotonic()-started
 before=time.monotonic();finalize();timings['native_metadata_finalization_seconds']=time.monotonic()-before
 with t.shared(t.footprint(0,24*1048576)) as budget:
  c=e.db();assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall()
  new_versions=0;accepted_hashes_reused=0
  for vid,sha,body,text,core,oldref,accepted_sha in c.execute("SELECT v.entity_version_id,v.body_sha256,CASE WHEN b.first_retrieved_at<'2026-10-09T02:41:51.640855+00:00' THEN NULL ELSE COALESCE(b.body_original,v.body_original) END,CASE WHEN b.first_retrieved_at<'2026-10-09T02:41:51.640855+00:00' THEN NULL ELSE COALESCE(b.body_text,v.body_text) END,v.core_body_version_id,CASE WHEN b.first_retrieved_at<'2026-10-09T02:41:51.640855+00:00' THEN 1 ELSE 0 END,b.body_sha256 FROM entity_versions v JOIN native_entities n ON n.entity_id=v.entity_id LEFT JOIN versions b ON b.body_version_id=v.core_body_version_id WHERE n.inherited=0 OR v.first_retrieved_at>='2026-10-09T02:41:51.640855+00:00'"):
   if oldref:
    assert sha==accepted_sha;accepted_hashes_reused+=1;continue
   if body:assert t.sha(body.encode())==sha,(vid,'body_hash')
   elif sha:raise AssertionError((vid,'bodyless_hash_conflict'))
   if core:assert body and text,(vid,'qualified_body_readability')
   new_versions+=1
  before=time.monotonic();raw_stats,raw_files=catalog(c,OUT);timings['new_raw_hash_and_native_mapping_check_seconds']=time.monotonic()-before
  raw_count=raw_stats['saved_raw_responses'];transport_count=raw_stats['transport_receipts']
  baseline=json.loads((t.WORK/'before_preview_type_repair/MIGRATION_RECEIPT.json').read_text())
  legacy=[x[0] for x in c.execute("SELECT persistent_post_id FROM native_identities WHERE identity_basis='established_ID_preserved' AND source_id LIKE 'se_%' ORDER BY persistent_post_id")]
  assert t.sha(json.dumps(legacy).encode())==baseline['legacy_mapping_digest']
  assert c.execute('SELECT COUNT(*) FROM native_entities WHERE inherited=1').fetchone()[0]==1566
  st=t.state();assert st['requests']>=138 and len(st['returned_object_ids'])>=1671
  files=raw_files
  queries={
   'native_entities_manifest.csv':"SELECT n.*,COUNT(DISTINCT v.entity_version_id) entity_versions,MAX(v.readable_native_unit) complete_readable_native_unit,MAX(COALESCE(a.independently_authored_body,v.independently_authored_body)) independently_authored_body FROM native_entities n LEFT JOIN entity_versions v ON v.entity_id=n.entity_id LEFT JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id GROUP BY n.entity_id",
   'content_versions_manifest.csv':"SELECT entity_version_id,entity_id,core_body_version_id,body_sha256,native_edited_at,native_revision,content_state,fixed_interval_state,readable_native_unit,independently_authored_body,content_license,licence_basis,flags_json,first_retrieved_at FROM entity_versions",
   'observations_manifest.csv':"SELECT * FROM entity_observations",
   'relations_manifest.csv':"SELECT * FROM native_edges",
   'attachments_manifest.csv':"SELECT attachment_id,entity_version_id,native_attachment_id,attachment_type,source_url,availability FROM native_attachments",
   'responses_manifest.csv':"SELECT * FROM responses",
   'acquisition_frames.csv':"SELECT * FROM acquisition_frames",
   'native_identity_map.csv':"SELECT * FROM native_identities",
   'native_aliases.csv':"SELECT * FROM native_aliases",
   'publication_memberships.csv':"SELECT * FROM publication_memberships",
   'source_provenance_annotations.csv':"SELECT * FROM entity_quality_annotations",
   'native_original_publication_counts.csv':"SELECT n.source_id,COUNT(DISTINCT m.publication_key) original_publication_keys FROM native_entities n JOIN entity_versions v ON v.entity_id=n.entity_id JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id JOIN publication_memberships m ON m.entity_id=n.entity_id WHERE a.independently_authored_body=1 AND v.fixed_interval_state='inside_fixed_interval' GROUP BY n.source_id",
   'structural_corrections.csv':"SELECT * FROM structural_corrections",
   'quality_by_source.csv':"SELECT n.source_id,COUNT(DISTINCT n.entity_id) native_entities,COUNT(DISTINCT CASE WHEN n.inherited=0 THEN n.entity_id END) new_entities,COUNT(DISTINCT CASE WHEN v.readable_native_unit=1 THEN n.entity_id END) complete_readable_units,COUNT(DISTINCT CASE WHEN COALESCE(a.independently_authored_body,v.independently_authored_body)=1 THEN n.entity_id END) independently_authored_bodies,COUNT(DISTINCT CASE WHEN n.native_unit='context_container' THEN n.entity_id END) context_containers,COUNT(DISTINCT CASE WHEN n.native_unit='repost_wrapper' THEN n.entity_id END) repost_wrappers,COUNT(DISTINCT CASE WHEN n.author_id IS NOT NULL AND COALESCE(a.independently_authored_body,v.independently_authored_body)=1 THEN n.author_id END) observed_distinct_authors,COUNT(DISTINCT v.entity_version_id) entity_versions,MIN(CASE WHEN v.readable_native_unit=1 THEN n.native_created_at END) first_qualified_creation,MAX(CASE WHEN v.readable_native_unit=1 THEN n.native_created_at END) last_qualified_creation FROM native_entities n LEFT JOIN entity_versions v ON v.entity_id=n.entity_id LEFT JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id GROUP BY n.source_id",
   'content_states.csv':"SELECT n.source_id,v.content_state,v.fixed_interval_state,COUNT(DISTINCT n.entity_id) entities,COUNT(*) observed_versions FROM native_entities n JOIN entity_versions v ON v.entity_id=n.entity_id GROUP BY n.source_id,v.content_state,v.fixed_interval_state",
   'core_month_counts.csv':"SELECT source_id,substr(native_created_at,1,7) month,native_unit,COUNT(*) native_units FROM posts GROUP BY source_id,month,native_unit",
   'licence_summary.csv':"SELECT p.source_id,v.content_license,COUNT(DISTINCT p.persistent_post_id) native_units,COUNT(*) body_versions FROM posts p JOIN versions v ON v.persistent_post_id=p.persistent_post_id GROUP BY p.source_id,v.content_license",
   'role_summary.csv':"SELECT source_id,author_role,COALESCE(author_country,'unknown') author_country,COUNT(*) native_units FROM posts GROUP BY source_id,author_role,author_country",
   'exact_body_overlap_groups.csv':"SELECT body_sha256,COUNT(DISTINCT entity_id) entities,COUNT(*) entity_versions FROM entity_versions WHERE body_sha256 IS NOT NULL GROUP BY body_sha256 HAVING COUNT(DISTINCT entity_id)>1"}
  for name,sql in queries.items():files.append(export(c,name,sql))
  registry=t.read_json(t.WORK/'source_registry.json');pooled,months=calendar(c,registry)
  p=OUT/'source_month_calendar.csv';files.append({'path':str(p.relative_to(t.WORK)),'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())})
  counts={table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['posts','versions','native_entities','entity_versions','native_edges','native_attachments','responses']}
  newcore=c.execute('SELECT COUNT(*) FROM posts p JOIN native_entities n ON n.entity_id=p.persistent_post_id WHERE n.inherited=0').fetchone()[0]
  sourcecounts=[dict(zip(['source_id','qualified_native_units'],row)) for row in c.execute('SELECT source_id,COUNT(*) FROM posts GROUP BY source_id')]
  independent=c.execute("SELECT COUNT(DISTINCT n.entity_id) FROM native_entities n JOIN entity_versions v ON v.entity_id=n.entity_id JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id WHERE a.independently_authored_body=1").fetchone()[0]
  publication_keys=c.execute("SELECT COUNT(DISTINCT m.publication_key) FROM publication_memberships m JOIN entity_versions v ON v.entity_id=m.entity_id JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id WHERE a.independently_authored_body=1").fetchone()[0]
  c.close()
  # Transport quality includes retained stops and saved responses; raw/body text stays local.
  p=OUT/'api_return_quality.csv'
  with p.open('w',newline='',encoding='utf8') as f:
   w=csv.writer(f);w.writerow(['source_id','request_id','purpose','status','http_status','raw_bytes','started_at','retrieved_at','raw_sha256','raw_reference','api_quota_remaining','api_backoff','error'])
   for q in sorted((t.WORK/'receipts').glob('*.json')):
    r=json.loads(q.read_text());w.writerow([r.get(k) for k in ['source_id','request_id','purpose','status','http_status','raw_bytes','started_at','retrieved_at','raw_sha256','raw_reference','api_quota_remaining','api_backoff','error']])
  files.append({'path':str(p.relative_to(t.WORK)),'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())})
  snap={'snapshot_at_utc':t.utc(),'publication_interval':['1988-01-01','2026-09-21'],'september_partial':True,'counts':counts,'new_qualified_native_units':newcore,'complete_independently_authored_body_entities':independent,'known_native_original_publication_keys':publication_keys,'lifetime_charged_requests':st['requests'],'lifetime_distinct_returned_objects':len(st['returned_object_ids']),'continuation_charged_requests':st['requests']-138,'continuation_distinct_returned_objects':len(st['returned_object_ids'])-1671,'pooled_observed_months':pooled,'full_calendar_months':months,'qualified_by_source':sourcecounts,'changed_tranche_check':{'sqlite_integrity':'ok','foreign_keys':'ok','new_entity_versions_body_checked':new_versions,'accepted_body_hash_references_reused':accepted_hashes_reused,'new_saved_raw_responses_checked':raw_count,'new_transport_receipts':transport_count,'old_ids_and_versions_reused':1566,'legacy_50_mapping_digest_preserved':True,'old_raw_or_body_reaudit':False},'stop':{k:v for k,v in t.read_json(t.WORK/'RUN_STOP.json').items() if k!='pid'},'budget_at_closeout':budget,'files':files}
  timings['terminal_processing_seconds']=time.monotonic()-started;snap['terminal_operation_timings']=timings;snap['changed_tranche_check']['new_native_mapping_check']=raw_stats
  snap['implementation_hashes']={p.name:t.sha(p.read_bytes()) for p in t.WORK.glob('*.py')};snap['implementation_hashes'].update({p.name:t.sha(p.read_bytes()) for p in t.WORK.glob('schema*.sql')})
  t.atomic(OUT/'collection_manifest.json',snap);t.atomic(t.WORK/'CLOSED.json',{'at_utc':t.utc(),'manifest_sha256':t.sha((OUT/'collection_manifest.json').read_bytes()),'snapshot':snap});print(json.dumps({k:snap[k] for k in ['snapshot_at_utc','counts','new_qualified_native_units','lifetime_charged_requests','lifetime_distinct_returned_objects','pooled_observed_months','stop']}))
if __name__=='__main__':
 with t.writer():closeout()
