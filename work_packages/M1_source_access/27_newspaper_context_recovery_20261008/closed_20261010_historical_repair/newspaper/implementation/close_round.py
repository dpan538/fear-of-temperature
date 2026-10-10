"""One post-exit changed-tranche verification and final metadata export."""
import pathlib,json,csv,collections,sqlite3,hashlib,gzip,datetime as dt,fcntl,os
import elt,archive_issues
OWN=pathlib.Path(__file__).resolve().parent;REPO=OWN.parents[5];SCOPE=json.loads((OWN/'EXECUTION_SCOPE.json').read_text());DB=REPO/SCOPE['newspaper_durable_database'];EXCLUDED=set(SCOPE['excluded_newspaper_analysis_source_ids'])
def sha(data):return hashlib.sha256(data).hexdigest()
def save(name,obj):(OWN/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvwrite(name,rows,fields=None):
 rows=list(rows);fields=fields or list(dict.fromkeys(k for row in rows for k in row))
 with (OWN/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
def monthly(rows):
 c=collections.Counter((r['source_id'],r['stratum'],r['publication_date'][:7]) for r in rows);out=[]
 for (sid,geo,m),n in sorted(c.items()):out.append(dict(source_id=sid,stratum=geo,publication_month=m,complete_article_IDs=n))
 return out

def close():
 assert (OWN/'EXECUTION_STOP.json').exists()
 with (REPO/SCOPE['newspaper_writer_mutex']).open('a+b') as m:
  fcntl.flock(m,fcntl.LOCK_EX|fcntl.LOCK_NB)
  save('WRITER_EXIT_OBSERVATION.json',dict(at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),host_reported_session_finished=True,mutex_available=True,source_network_stopped=True))
  with (REPO/SCOPE['shared_heavy_io_lock']).open('a+b') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   # Reserve the real metadata/export peak before one bounded final read.
   export_peak=sum(x.stat().st_size for x in [DB,OWN/'BASELINE_METADATA.csv',OWN/'LOAD_LOG.jsonl'])+48*1024*1024
   final_capacity_before=elt.preflight(export_peak)
   c=sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
   qc=[r[0] for r in c.execute('PRAGMA quick_check')];fk=list(c.execute('PRAGMA foreign_key_check'))
   rows=[dict(r) for r in c.execute('SELECT a.* FROM articles a LEFT JOIN article_dispositions d ON d.article_id=a.article_id WHERE d.article_id IS NULL')]
   logs=[json.loads(x) for x in (OWN/'LOAD_LOG.jsonl').read_text().splitlines() if x];new={r['article_id']:r for r in logs if r.get('load_status')=='confirmed_complete'}
   versions={r['article_id']:dict(r) for r in c.execute('SELECT a.article_id,v.* FROM articles a JOIN article_versions v ON a.latest_version_id=v.version_id WHERE v.loaded_at>=?',(SCOPE['earliest_network_and_load_start_at_utc'],))};counts={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['articles','article_versions','evidence','article_dispositions']};c.close()
  baseline=list(csv.DictReader((OWN/'BASELINE_METADATA.csv').open()));by={r['article_id']:r for r in rows};errors=[]
  for old in baseline:
   now=by.get(old['article_id'])
   if not now or any(str(now[k])!=old[k] for k in ['source_id','source_url','publication_date','stratum','work_family_id','latest_version_id']):errors.append({'kind':'baseline_identity_membership_changed','article_id':old['article_id']})
  raw_seen={};mapping=[];parsed_issues={} ;provenance_register=[]
  for aid,r in new.items():
   v=versions.get(aid)
   if not v:errors.append({'kind':'new_latest_version_missing','article_id':aid});continue
   if sha(v['body_text'].encode())!=v['body_sha256']:errors.append({'kind':'new_TEXT_hash_mismatch','article_id':aid})
   ref=v['raw_reference']
   if ref and ref not in raw_seen:
    p=REPO/ref;stored=p.read_bytes();raw=gzip.decompress(stored) if p.suffix=='.gz' else stored;raw_seen[ref]=sha(raw)
   if ref and raw_seen[ref]!=v['raw_sha256']:errors.append({'kind':'new_raw_hash_mismatch','article_id':aid})
   if not SCOPE['publication_interval'][0]<=r['publication_date']<=SCOPE['publication_interval'][1]:errors.append({'kind':'new_date_outside_fixed_interval','article_id':aid})
   provenance=json.loads(v['provenance_json'])
   if r['source_id']=='workers_advocate':
    issue_url=provenance['original_issue_url'];anchor=provenance['native_article_anchor']
    if ref not in parsed_issues:
     raw_path=REPO/ref;data=raw_path.read_bytes();data=gzip.decompress(data) if raw_path.suffix=='.gz' else data
     parsed_issues[ref]={u['native_article_anchor']:u for u in archive_issues.parse_issue(data,issue_url,provenance['expected_native_index_date'])['units']}
    u=parsed_issues[ref].get(anchor)
    if not u or u['status']!='confirmed_complete' or u['publication_date']!=r['publication_date'] or sha(u['body'].encode())!=v['body_sha256'] or issue_url+'#'+anchor!=r['source_url']:
     errors.append({'kind':'native_issue_article_identity_date_body_mapping_mismatch','article_id':aid})
   provenance_register.append(dict(article_id=aid,source_id=r['source_id'],source_url=r['source_url'],publication_date=r['publication_date'],retrieved_at_utc=provenance.get('retrieved_at_utc'),content_version_time=provenance.get('content_version_time'),archive_transcription_time=provenance.get('archive_transcription_time'),archive_transcription_year=provenance.get('archive_transcription_year'),source_directness='archival reproduction' if r['source_id'] in ['workers_advocate','militant_uk_archive'] else 'original publisher representation',identity_date_content_mapping='verified changed-tranche hash/date mapping; named native issue boundaries re-parsed where applicable',provenance_statement=provenance.get('provenance'),origin_or_quoted_speaker_mapping='Separate embedded reprints/quotations/letters require later passage-level provenance checks; archival mapping does not establish claim truth',access_limit=provenance.get('retention_limit'),body_boundary=provenance.get('body_boundary'),native_date_limit=provenance.get('native_date_limit')))
   mapping.append(dict(article_id=aid,source_id=r['source_id'],publication_date=r['publication_date'],version_id=v['version_id'],body_sha256=v['body_sha256'],raw_reference=ref,raw_sha256=v['raw_sha256'],source_url=r['source_url'],native_unit_mapping=r.get('article_boundary_evidence') or r.get('body_boundary'),original_issue_url=r.get('original_issue_url'),native_article_anchor=r.get('native_article_anchor'),provenance=r.get('provenance'),work_family_id=r.get('work_family_id',aid)))
  check=dict(at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),all_passed=qc==['ok'] and not fk and not errors,SQLite_quick_check=qc,foreign_key_errors=len(fk),baseline_metadata_IDs_preserved=len(baseline),new_complete_IDs_checked=len(new),new_unique_raw_objects_checked=len(raw_seen),errors=errors,verification_scope='New Load TEXT/raw mapping and immutable baseline identity/date/version memberships only; no old body/raw sweep')
  save('CHANGED_TRANCHE_FINAL_CHECK.json',check)
  current=[r for r in rows if r['source_id'] not in EXCLUDED];before=[r for r in baseline if r['source_id'] not in EXCLUDED];campus=[r for r in rows if r['source_id'] in EXCLUDED]
  csvwrite('SOURCE_PROVENANCE_AND_DATE_REGISTER.csv',provenance_register);csvwrite('ADDITIONAL_ARTICLE_REGISTER.csv',mapping);csvwrite('CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv',current);csvwrite('HISTORICAL_CAMPUS_PRESERVATION_REGISTER.csv',campus);csvwrite('MONTH_SOURCE_COUNTS_BEFORE.csv',monthly(before));csvwrite('MONTH_SOURCE_COUNTS_AFTER.csv',monthly(current))
  months=[f'{y}-{m:02d}' for y in range(1988,2027) for m in range(1,13) if (y,m)<=(2026,9)];bc=collections.Counter(r['publication_date'][:7] for r in before);ac=collections.Counter(r['publication_date'][:7] for r in current);delta=[]
  for mo in months:delta.append(dict(publication_month=mo,before_complete_article_IDs=bc[mo],after_complete_article_IDs=ac[mo],new_IDs=ac[mo]-bc[mo],observed_sources=len({r['source_id'] for r in current if r['publication_date'].startswith(mo)}),partial_boundary=mo=='2026-09'))
  csvwrite('MONTHLY_BEFORE_AFTER.csv',delta);csvwrite('RESIDUAL_EMPTY_MONTHS.csv',[r for r in delta if r['after_complete_article_IDs']==0]);csvwrite('SOURCE_YEAR_DELTA.csv',[dict(source_id=s,publication_year=y,new_complete_IDs=n) for (s,y),n in sorted(collections.Counter((r['source_id'],r['publication_date'][:4]) for r in new.values()).items())])
  peaks=[]
  for i,mo in enumerate(months):
   near=[ac[months[j]] for j in range(max(0,i-3),min(len(months),i+4)) if j!=i];mean=sum(near)/len(near) if near else None
   if mean is not None and ac[mo]>max(near,default=0):peaks.append(dict(publication_month=mo,article_IDs=ac[mo],preceding_following_available_month_counts=near,neighbor_mean=mean,boundary_context_incomplete=i<3 or i>=len(months)-3,action='diagnostic_only; retain all records; no event attribution'))
  csvwrite('MONTH_PEAK_CONTEXT_FLAGS.csv',peaks)
  transport=json.loads((OWN/'TRANSPORT_STATE.json').read_text());requests=[json.loads(x) for x in (OWN/'REQUESTS.jsonl').read_text().splitlines() if x];stop=json.loads((OWN/'EXECUTION_STOP.json').read_text());start=json.loads((OWN/'INPUT_SNAPSHOT.json').read_text())
  csvwrite('HOST_STOP_REGISTER.csv',[dict(host=h,stop=s,scope='Inherited/actual source access evidence; no bypass') for h,s in transport['access_stops'].items()]);csvwrite('RAW_OBJECT_MANIFEST.csv',[{k:r.get(k) for k in ['target_id','source_id','url','status','raw_reference','raw_sha256','raw_bytes','stored_sha256','stored_bytes','finished_at_utc']} for r in requests if r.get('raw_reference')]);csvwrite('PENDING_DISPOSITION_REGISTER.csv',[r for r in logs if r.get('load_status')!='confirmed_complete'])
  frontier=json.loads((OWN/'BROADEN_CURSORS.json').read_text());csvwrite('SOURCE_FRONTIER_REGISTER.csv',[dict(source_id=s,stage=v.get('stage'),attempted_metadata_pages=v.get('attempted_pages'),next_url=v.get('next_url'),reason=v.get('blocked_reason') or v.get('reason'),native_inventory_denominator='observed interface only; historical population unknown') for s,v in frontier.items()]);
  summary=dict(at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),status='closed',publication_interval=SCOPE['publication_interval'],hard_deadline_at_utc=SCOPE['hard_deadline_at_utc'],stop_reason=stop['reason'],baseline_current_newspaper_IDs=len(before),additional_qualified_IDs=len(new),current_newspaper_complete_IDs=len(current),historical_campus_IDs_preserved=len(campus),observed_study_months=sum(ac[m]>0 for m in months),remaining_empty_months=sum(ac[m]==0 for m in months),new_source_year_mix={s:{y:n for (sid,y),n in collections.Counter((r['source_id'],r['publication_date'][:4]) for r in new.values()).items() if sid==s} for s in sorted({r['source_id'] for r in new.values()})},new_distinct_transport_target_receipts=len(requests),new_recorded_HTTP_request_attempts=sum(r.get('HTTP_request_attempts_recorded',0) for r in requests),new_HTTP_response_hops=sum(len(r.get('hops',[])) for r in requests),cumulative_transport_targets=len(transport['targets']),cumulative_native_targets=len(transport['charged_native_targets']),baseline_cumulative_transport_targets=start['cumulative_distinct_transport_targets'],baseline_cumulative_native_targets=start['cumulative_native_targets'],database_counts=counts,checks=check,source_frontier=frontier,semantic_labels_executed=False,parent_metrics_used_for_control=False,old_body_raw_sweep=False)
  # Keep large URL arrays in local cursors rather than duplicate them in final summary.
  summary['source_frontier']={s:{k:len(v) if isinstance(v,list) else v for k,v in q.items()} for s,q in frontier.items()}
  with elt.LOCK.open('a+b') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);summary['final_resource_capacity']=elt.resource(0)
  summary['final_resource_capacity_before_export']=final_capacity_before
  summary['Workers_Advocate_native_issue_mapping_checks']=len(parsed_issues)
  summary['retained_record_counts_are_not_independent_work_counts']=True
  summary['source_admission_and_limits']=json.loads((OWN/'SOURCE_ADMISSION_AND_LIMITS.json').read_text())
  summary['baseline_2026_concentration_diagnostic']=json.loads((OWN/'BASELINE_2026_CONCENTRATION_DIAGNOSTIC.json').read_text())
  save('DELIVERY_SUMMARY.json',summary);save('LEASE_RELEASE_REQUEST.json',dict(at_utc=summary['at_utc'],owner_thread_id=SCOPE['owner_thread_id'],lease_id=SCOPE['lease_id'],writer_exited=True,mutex_available=True,stop_reason=stop['reason'],coordinator_action='Release canonical lease; worker has not edited coordination',original_deadline_unchanged=True))
  report=f'''# Newspaper historical repair — 10 October2026\n\nClosed for **{stop['reason']}** under the original **15:43:58 AEST** deadline. This round adds **{len(new):,} complete article IDs**, reaching **{len(current):,} current non-campus newspaper IDs** in **{sum(ac[m]>0 for m in months)}/465 observed months**. All **{len(campus):,} campus IDs** remain separate.\n\n`BUG_REPAIR_LEDGER.md` identifies the confirmed two-body selector, contaminated Green Left issue/sidebar locator and no-HTTP expired-batch state defects; original code/state/receipts and all raw/IDs/versions are preserved. The derived repair register and bounded regressions do not establish that all152 exactly-two-body months are repaired. `MONTHLY_BEFORE_AFTER.csv` and `SOURCE_YEAR_DELTA.csv` show the actual historical gains.\n\nThe opening 1988–1991 source routes and their real access/era/completeness limits are recorded in `SOURCE_ADMISSION_AND_LIMITS.json` when present. Native inventories retain unknown denominators. Workers’ Advocate is an advocacy-newspaper archival transcription, and Militant is a separately attributed UK archival reproduction; these gains do not certify general-interest or regional representativeness. Units with an unresolved native terminator/date remain pending. Source-unit IDs are not automatically distinct works when duplicate or reprint relationships remain candidates. `SOURCE_PROVENANCE_AND_DATE_REGISTER.csv` separates provenance, dates and remaining checks. The Militant source notice gives a transcription year, not an exact version timestamp; `DERIVED_TIME_FIELD_ASSERTIONS.json` preserves that limitation for its earlier committed metadata scalar. Index completion and body completion remain distinct. No new PDF slot was used; all36 historical slots remain consumed.\n\nThe baseline2026 slice contains Devonport Flagstaff(NZ) and Northern Rivers Times(AU); prior prose saying bothAU is a reporting correction. No automatic date correction, deletion, downsampling, new yearly-share target, flat histogram or climate-event attribution follows. Publication, retrieval, source-version and report times remain separate, and partial September retains the2026-09-21 cutoff.\n\nChanged-tranche verification: **{'passed' if check['all_passed'] else 'FAILED'}**, with **{len(errors)} mapping errors**. One SQLite quick/foreign-key check and new TEXT/raw checks ran after writer exit; all{len(baseline):,} baseline qualified identity/date/version memberships were compared as metadata. No old body/raw sweep or store copy was performed. Transport/request counters retain their historical instrumentation limits.\n\nDated original text/source presence is delivered at evidence level1. Climate/warming relevance and similarity(level2), validated affect/risk/future-harm associations(level3) and fear-specific interpretation(level4) remain deferred. Corpus volume does not establish emotion prevalence, archive completeness or a comparable three-role time series.\n\nWriter exit/mutex release is verified. The lease-release request is local; the worker did not edit coordinator controls, shared logs, Git, government/evaluator stores or the other media stream.\n'''
  (OWN/'DELIVERY_REPORT.md').write_text(report)
  save('WORKER_COMPLETION.json',dict(at_utc=summary['at_utc'],status='completed',all_changed_tranche_checks_passed=check['all_passed'],new_complete_IDs=len(new),fixed_deadline_preserved=True,writer_exited=True))
  manifest={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in OWN.iterdir() if p.is_file() and p.name in ['DELIVERY_SUMMARY.json','DELIVERY_REPORT.md','CHANGED_TRANCHE_FINAL_CHECK.json','ADDITIONAL_ARTICLE_REGISTER.csv','CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv','MONTHLY_BEFORE_AFTER.csv','SOURCE_YEAR_DELTA.csv','RAW_OBJECT_MANIFEST.csv','SOURCE_FRONTIER_REGISTER.csv','HISTORICAL_CAMPUS_PRESERVATION_REGISTER.csv','SOURCE_PROVENANCE_AND_DATE_REGISTER.csv']};save('DELIVERY_FILE_RECEIPTS.json',manifest)
  print(json.dumps({k:summary[k] for k in ['status','additional_qualified_IDs','current_newspaper_complete_IDs','observed_study_months','remaining_empty_months','stop_reason']}),flush=True)

if __name__=='__main__':close()
