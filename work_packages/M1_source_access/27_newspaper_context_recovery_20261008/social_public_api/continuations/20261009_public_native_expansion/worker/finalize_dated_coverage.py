"""Named source-era conflict correction, metadata only; raw/body checks reused."""
import csv,json,time
import transport as t,entities as e

def finalize():
 started=time.monotonic();out=t.WORK/'summaries'
 with t.shared(t.footprint(0,24*1048576)) as budget:
  c=e.db();conflicts={}
  # Source timestamps can be authentic returned values without proving that the
  # utterance was published on that source before its documented existence.
  for eid,sid,date in c.execute("SELECT persistent_post_id,source_id,native_created_at FROM posts WHERE source_id='bluesky' AND native_created_at<'2019-01-01'"):
   conflicts[eid]=(sid,date,'native_record_createdAt_before_platform_project_lower_bound','2019-01-01','documented project lower bound; public app/actor eras remain unknown')
  for eid,sid,date in c.execute("SELECT DISTINCT p.persistent_post_id,p.source_id,p.native_created_at FROM posts p JOIN entity_versions v ON v.entity_id=p.persistent_post_id WHERE p.source_id='se_earthscience' AND json_extract(v.flags_json,'$.source_creation_before_documented_site_beta')=1"):
   conflicts[eid]=(sid,date,'native_creation_before_documented_site_beta; migration_original_date_mapping_pending','2014-04-15','documented beta day; native migration/original-publication mapping not asserted')
  # A preserved core row from an earlier adapter may describe a native action.
  independent={eid for eid, in c.execute('SELECT DISTINCT v.entity_id FROM entity_versions v JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id WHERE a.independently_authored_body=1')}
  observed={};qualified={};unresolved={};publication_months=set();reported_months=set()
  for eid,sid,date in c.execute('SELECT persistent_post_id,source_id,native_created_at FROM posts'):
   key=(sid,date[:7]);observed[key]=observed.get(key,0)+1;reported_months.add(date[:7])
   if eid in conflicts:unresolved[key]=unresolved.get(key,0)+1
   elif eid in independent:qualified[key]=qualified.get(key,0)+1;publication_months.add(date[:7])
  p=out/'native_date_mapping_limits.csv'
  with p.open('w',newline='',encoding='utf8') as f:
   w=csv.writer(f);w.writerow(['entity_id','source_id','native_reported_created_at','issue','source_lower_bound','evidence_basis','publication_time_mapping','retention'])
   for eid,values in sorted(conflicts.items()):w.writerow([eid,*values,'unresolved_for_source_publication_month','original_raw_body_identity_and_reported_time_preserved'])
  rows=list(csv.DictReader((out/'source_month_calendar.csv').open()))
  fields=list(rows[0])
  if 'publication_month_qualified_independent_bodies' not in fields:fields[fields.index('state'):fields.index('state')]=['publication_month_qualified_independent_bodies','native_date_unresolved_body_units']
  for row in rows:
   key=(row['source_id'],row['month']);row['publication_month_qualified_independent_bodies']=qualified.get(key,0);row['native_date_unresolved_body_units']=unresolved.get(key,0)
   if observed.get(key,0) and not qualified.get(key,0):
    row['state']='source_era_structurally_inapplicable; retained_native_timestamp_conflict_not_historical_presence' if row['source_id']=='bluesky' and row['month']<'2019-01' else 'retained_text_native_date_or_authorship_mapping_pending; no_qualified_dated_source_presence'
  with (out/'source_month_calendar.csv').open('w',newline='',encoding='utf8') as f:
   w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
  # Replace only the affected finalized metadata; no terminal audit repeats.
  with (out/'source_publication_month_counts.csv').open('w',newline='',encoding='utf8') as f:
   w=csv.writer(f);w.writerow(['source_id','native_reported_month','retained_core_text_units','publication_month_qualified_independent_bodies','native_date_unresolved_body_units'])
   for sid,month in sorted(observed):w.writerow([sid,month,observed[sid,month],qualified.get((sid,month),0),unresolved.get((sid,month),0)])
  c.close();original=t.read_json(out/'collection_manifest.json')
  if not (t.WORK/'COLLECTION_MANIFEST_BEFORE_DATE_MAPPING_CORRECTION.json').exists():t.atomic(t.WORK/'COLLECTION_MANIFEST_BEFORE_DATE_MAPPING_CORRECTION.json',original)
  original['pooled_native_reported_timestamp_months']=len(reported_months);original['pooled_observed_months']=len(publication_months);original['dated_source_presence_basis']='complete independent native bodies with named source-era conflicts withheld; record timestamps alone do not certify source publication time'
  original['native_date_mapping_limits']={'body_entities_with_named_pending_date_mapping':len(conflicts),'by_source':{sid:sum(x[0]==sid for x in conflicts.values()) for sid in sorted({x[0] for x in conflicts.values()})},'raw_and_body_audit_repeated':False,'retained_core_records_unchanged':True,'metadata_correction_seconds':time.monotonic()-started}
  original['publication_month_qualified_independent_body_entities']=sum(qualified.values());original['snapshot_at_utc']=t.utc();original['budget_at_metadata_correction']=budget
  for path in [out/'native_date_mapping_limits.csv',out/'source_month_calendar.csv',out/'source_publication_month_counts.csv']:
   original['files']=[x for x in original['files'] if x['path']!=str(path.relative_to(t.WORK))];original['files'].append({'path':str(path.relative_to(t.WORK)),'bytes':path.stat().st_size,'sha256':t.sha(path.read_bytes())})
  original['implementation_hashes'].update({p.name:t.sha(p.read_bytes()) for p in t.WORK.glob('*.py')})
  t.atomic(out/'collection_manifest.json',original);t.atomic(t.WORK/'CLOSED.json',{'at_utc':t.utc(),'manifest_sha256':t.sha((out/'collection_manifest.json').read_bytes()),'snapshot':original})
  print(json.dumps({k:original[k] for k in ['pooled_native_reported_timestamp_months','pooled_observed_months','publication_month_qualified_independent_body_entities','native_date_mapping_limits']}))
if __name__=='__main__':
 with t.writer():finalize()
