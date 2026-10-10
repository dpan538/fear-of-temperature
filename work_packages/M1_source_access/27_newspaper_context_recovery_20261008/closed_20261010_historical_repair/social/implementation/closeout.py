"""One terminal changed-tranche check; metadata exports and accepted baseline reuse."""
import collections,csv,datetime as dt,gzip,json,os,time,re
from pathlib import Path
import transport as t,entities as e
from raw_catalog import catalog
from finalize_metadata import finalize
OUT=t.WORK/'summaries'

def export(c,name,sql,params=(),compressed=False):
 cur=c.execute(sql,params);p=OUT/(name+'.gz' if compressed else name)
 opener=gzip.open if compressed else open
 with opener(p,'wt',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow([x[0] for x in cur.description]);w.writerows(cur)
 return {'path':str(p.relative_to(t.WORK)),'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())}

def reconcile_saved(begin):
 """Complete only already acquired bounded responses; never issue HTTP."""
 loaded={json.loads(l)['request_id'] for l in (t.WORK/'LOADS.jsonl').read_text().splitlines()}
 sources={x['source_id']:x for x in t.read_json(t.WORK/'source_registry.json')};fronts=t.read_json(t.WORK/'FRONTIERS.json');results=[]
 import collect,lemmy_adapter
 for p in sorted((t.WORK/'receipts').glob('*.json')):
  rec=t.read_json(p)
  if rec.get('status')!='saved' or rec.get('purpose')!='content' or rec['request_id'] in loaded:continue
  sid=rec['source_id'];source=sources[sid];assert source['collection_retention']=='permitted'
  try:
   import archive_adapter
   if sid in ('python_list_archive','w3_wwwtalk'):
    raw=t.payload(rec)
    if raw.startswith(b'\x1f\x8b'):raw=gzip.decompress(raw)
    data={}
    rows=archive_adapter.mbox_records(raw,sid,rec['url']) if sid=='python_list_archive' else archive_adapter.w3_records(raw,rec['url'],sid) if re.search(r'/[0-9]{4}\.html$',rec['url']) else []
   else:data=t.json_payload(rec)
   if sid in ('python_list_archive','w3_wwwtalk'):pass
   elif sid=='hackernews':rows=archive_adapter.hn_records(data,sid,rec['url'].rsplit('/',1)[-1].split('.')[0])
   elif sid.startswith('se_'):rows=e.se(data,sid)
   elif sid.startswith('mastodon_'):rows=e.mastodon(data,sid)
   elif sid=='bluesky':rows=e.bluesky(data)
   elif sid in ('lemmy_nz','aussie_zone','feddit_org','midwest_social'):rows=lemmy_adapter.records(data,sid,source['base_url'])
   else:rows=e.discourse(data,sid,source['base_url'],source.get('content_license','version_specific_license_unresolved'))
   found=None
   for f in fronts:
    if f['source']!=sid:continue
    try:
     if collect.job(f)[0]==rec['url']:found=f;break
    except Exception:pass
   frame=found['frame'] if found else sid+':saved_response_terminal_reconciliation'
   with t.shared(t.footprint(),inflight_at=rec['started_at']):
    c=e.db();e.register(c,source,collect.frame_definition(found) if found else {'frame_id':frame,'frame_type':'saved_native_response','selection_rule':'Already fetched source-native response at original request URL; original cursor lookup pending'});c.close()
   result=e.load(rows,rec,frame);results.append({'request_id':rec['request_id'],'state':'already_acquired_response_loaded','new_entities':result['new_entities'],'new_core_bodies':result['new_qualified_posts']})
  except Exception as exc:results.append({'request_id':rec['request_id'],'state':'explicit_saved_response_mapping_pending','error':type(exc).__name__+': '+str(exc)})
 t.atomic(t.WORK/'TERMINAL_SAVED_RESPONSE_RECONCILIATION.json',{'at_utc':t.utc(),'source_requests':0,'results':results,'original_deadline_preserved':True})
 return results

def main():
 t.TERMINAL_OPERATION=True
 start=time.monotonic();scope=t.read_json(t.SCOPE_PATH);begin=scope['earliest_network_and_load_start_at_utc']
 stop=t.read_json(t.WORK/'RUN_STOP.json');assert stop
 OUT.mkdir(exist_ok=True)
 with t.writer():
  reconciled=reconcile_saved(begin)
  finalize()
  # Changed raw validation may make narrow derived quality corrections. Scale accepted compressed metadata by native
  # entity growth and add a conservative auxiliary-feed amplification for changed exports.
  assert t.read_json(t.WORK/'TERMINAL_METADATA_REGRESSION.json')['passed']
  terminal_state=t.state();baseline=t.read_json(t.WORK/'INHERITED_BASELINE.json')
  growth=max(1,(baseline['counts']['native_entities']+terminal_state.get('new_entities',0))/baseline['counts']['native_entities'])
  prior=t.read_json(t.REPO/scope['predecessor_worker_reference']/'summaries/delivery_file_manifest.json')
  accepted_export_bytes=sum(x['bytes'] for x in prior['files'])
  # Direct compressed exports do not clone the current feed or whole database.
  # Reserve twice the measured accepted export footprint scaled by actual catalog
  # growth, plus metadata/gzip/receipt margins. Record the operation estimate.
  export_pending_bytes=int(accepted_export_bytes*growth*2)+64*1048576
  t.atomic(t.WORK/'TERMINAL_EXPORT_RESERVE.json',{'at_utc':t.utc(),'pending_bytes':export_pending_bytes,'native_entity_growth':growth,'accepted_predecessor_export_bytes':accepted_export_bytes,'journal_or_full_database_copy':False,'auxiliary_feed_copy':False,'scope':'read-only changed-tranche validation and direct compressed metadata exports; no source requests or corpus copy'})
  t.atomic(t.WORK/'TERMINAL_IMPLEMENTATION_RECEIPT.json',{'at_utc':t.utc(),'implementation_hashes':{p.name:t.sha(p.read_bytes()) for p in t.WORK.glob('*.py')},'terminal_regression_passed':True,'original_deadline_preserved':True})
  with t.shared(export_pending_bytes,inflight_at=begin) as budget:
   c=e.db();assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall()
   check={'terminal_saved_response_reconciliation':reconciled,'sqlite_integrity':'ok','foreign_keys':'ok','new_version_bodies_checked':0,'accepted_body_hash_references_reused':0,'old_raw_or_body_reaudit':False}
   rows=c.execute('''SELECT v.entity_version_id,v.body_sha256,CASE WHEN b.first_retrieved_at<? THEN NULL ELSE COALESCE(b.body_original,v.body_original) END,CASE WHEN b.first_retrieved_at<? THEN NULL ELSE COALESCE(b.body_text,v.body_text) END,v.core_body_version_id,CASE WHEN b.first_retrieved_at<? THEN 1 ELSE 0 END,b.body_sha256 FROM entity_versions v LEFT JOIN versions b ON b.body_version_id=v.core_body_version_id WHERE v.first_retrieved_at>=?''',(begin,begin,begin,begin))
   for vid,sha,body,text,core,oldref,accepted_sha in rows:
    if oldref:assert sha==accepted_sha;check['accepted_body_hash_references_reused']+=1;continue
    if body:assert t.sha(body.encode())==sha,(vid,'body_digest')
    elif sha:raise AssertionError((vid,'bodyless_hash_conflict'))
    if core:assert body and text,(vid,'core_readability')
    check['new_version_bodies_checked']+=1
   raw_stats,files=catalog(c,OUT);check['new_raw_mapping']=raw_stats
   tables=['posts','versions','native_entities','entity_versions','entity_observations','native_edges','native_attachments','responses']
   counts={table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in tables}
   original=t.read_json(t.WORK/'START_RECEIPT.json')['baseline'];st=t.state()
   assert counts['posts']==original['posts']+st.get('new_core_bodies',0)
   assert counts['native_entities']==original['native_entities']+st.get('new_entities',0)
   assert counts['entity_versions']==original['entity_versions']+st.get('new_entity_versions',0)
   # Check only immutable ID metadata against the accepted map, never old bodies.
   import hashlib
   legacy=[x[0] for x in c.execute("SELECT persistent_post_id FROM native_identities WHERE identity_basis='established_ID_preserved' AND source_id LIKE 'se_%' ORDER BY persistent_post_id")]
   check['legacy_50_mapping_digest_preserved']=t.sha(json.dumps(legacy).encode())==t.read_json(t.WORK/'MIGRATION_RECEIPT.json')['legacy_mapping_digest'];assert check['legacy_50_mapping_digest_preserved']
   for name,sql in {
    'native_entities_manifest.csv':'SELECT entity_id,source_id,native_namespace,native_id,source_url,native_unit,native_created_at,date_precision,author_id,author_role,author_country,first_retrieved_at FROM native_entities',
    'changed_content_versions_manifest.csv':'SELECT entity_version_id,entity_id,core_body_version_id,body_sha256,native_edited_at,native_revision,content_state,fixed_interval_state,readable_native_unit,independently_authored_body,content_license,licence_basis,flags_json,first_retrieved_at FROM entity_versions WHERE first_retrieved_at>=?',
    'changed_observations_manifest.csv':'SELECT * FROM entity_observations WHERE retrieved_at>=?',
    'changed_relations_manifest.csv':'SELECT edge_id,source_entity_id,relation_type,target_source_id,target_namespace,target_native_id,target_entity_id,target_url,resolution_state,first_request_id,first_retrieved_at FROM native_edges WHERE first_retrieved_at>=?',
    'acquisition_frames.csv':'SELECT * FROM acquisition_frames',
    'native_aliases.csv':'SELECT * FROM native_aliases',
    'source_registry_catalog.csv':'SELECT source_id,base_url,source_region,public_access,local_retention,redistribution,policy_evidence_json FROM acquisition_sources',
    'source_interface_catalog.csv':'SELECT * FROM acquisition_interfaces',
    'changed_source_provenance.csv':'SELECT * FROM entity_quality_annotations WHERE annotated_at>=?',
    'changed_structural_corrections.csv':'SELECT * FROM structural_corrections WHERE corrected_at>=?'
   }.items():files.append(export(c,name,sql,(begin,) if '?' in sql else (),compressed=True))
   files.append(export(c,'source_native_type_counts.csv','SELECT source_id,native_namespace,native_unit,COUNT(*) entities FROM native_entities GROUP BY source_id,native_namespace,native_unit'))
   files.append(export(c,'content_states.csv','SELECT n.source_id,v.content_state,v.fixed_interval_state,COUNT(DISTINCT n.entity_id) entities,COUNT(*) versions FROM native_entities n JOIN entity_versions v ON v.entity_id=n.entity_id GROUP BY n.source_id,v.content_state,v.fixed_interval_state'))
   files.append(export(c,'role_summary.csv',"SELECT source_id,author_role,COALESCE(author_country,'unknown') author_country,COUNT(*) core_texts FROM posts GROUP BY source_id,author_role,author_country"))
   files.append(export(c,'publication_memberships.csv','SELECT * FROM publication_memberships',compressed=True))
   registry=t.read_json(t.WORK/'source_registry.json');sources={s['source_id']:s for s in registry}
   months=[f'{y}-{m:02}' for y in range(1988,2027) for m in range(1,13) if (y,m)<=(2026,9)]
   observed=collections.Counter();qualified=collections.Counter();pending=[];independent=0
   for eid,sid,date,authored,prebeta in c.execute("SELECT p.persistent_post_id,p.source_id,p.native_created_at,MAX(COALESCE(a.independently_authored_body,v.independently_authored_body)),MAX(COALESCE(json_extract(v.flags_json,'$.source_creation_before_documented_site_beta'),0)) FROM posts p JOIN entity_versions v ON v.entity_id=p.persistent_post_id LEFT JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id GROUP BY p.persistent_post_id"):
    observed[sid,date[:7]]+=1;independent+=bool(authored)
    issue='native_record_createdAt_before_platform_project_lower_bound' if sid=='bluesky' and date<'2019-01-01' else 'native_creation_before_documented_site_beta; migration_mapping_pending' if sid=='se_earthscience' and prebeta else None
    if issue:pending.append((eid,sid,date,issue))
    elif authored:qualified[sid,date[:7]]+=1
   p=OUT/'native_date_mapping_limits.csv'
   with p.open('w',newline='',encoding='utf8') as f:
    w=csv.writer(f);w.writerow(['entity_id','source_id','native_reported_created_at','issue','retention']);w.writerows([(*r,'original_raw_body_identity_and_reported_time_preserved') for r in pending])
   lower={'se_sustainability':'2013-01','se_earthscience':'2014-04','python_discourse':'2018-09','bluesky':'2019-01',**{s:'2016-10' for s in sources if s.startswith('mastodon_')}}
   p=OUT/'source_month_calendar.csv'
   with p.open('w',newline='',encoding='utf8') as f:
    w=csv.writer(f);w.writerow(['source_id','source_opportunity_stratum','month','retained_core_texts','usable_dated_independent_bodies','state','september_partial'])
    for sid in sorted(sources):
     for m in months:
      q=qualified[sid,m];bound=lower.get(sid)
      state='observed_usable_dated_body' if q else 'structurally_inapplicable_under_documented_platform_or_site_lower_bound' if bound and m<bound else 'applicable_unobserved' if sid.startswith('se_') or sid=='python_discourse' else 'historical_scope_unknown'
      if sources[sid].get('collection_retention')!='permitted' and not (bound and m<bound):state='source_access_blocked_or_unresolved'
      w.writerow([sid,sources[sid].get('stratum','GLOBAL'),m,observed[sid,m],q,state,int(m=='2026-09')])
   p=OUT/'adjacent_month_flags.csv'
   with p.open('w',newline='',encoding='utf8') as f:
    w=csv.writer(f);w.writerow(['source_id','month','core_texts','preceding_following_three_month_mean','available_calendar_neighbor_bins','calendar_boundary_incomplete','flag','acquisition_effect','event_attribution'])
    for sid in sorted({s for s,m in observed}):
     for i,m in enumerate(months):
      context=[observed[sid,months[j]] for j in range(max(0,i-3),min(len(months),i+4)) if j!=i];n=observed[sid,m];mean=sum(context)/len(context) if context else 0
      if n and (mean==0 or n>3*mean):w.writerow([sid,m,n,mean,len(context),int(len(context)<6),'nonblocking_high_or_isolated_count','retained_without_downsampling','unassessed; independent_dated_evidence_required'])
   for name in ['native_date_mapping_limits.csv','source_month_calendar.csv','adjacent_month_flags.csv']:
    p=OUT/name;files.append(dict(path=str(p.relative_to(t.WORK)),bytes=p.stat().st_size,sha256=t.sha(p.read_bytes())))
   files.append(export(c,'changed_date_resolution_limits.csv','SELECT n.entity_id,n.source_id,n.native_namespace,n.native_id,n.source_url,n.native_created_at,v.content_state,v.fixed_interval_state,v.flags_json,v.first_retrieved_at FROM native_entities n JOIN entity_versions v ON v.entity_id=n.entity_id WHERE v.first_retrieved_at>=? AND (n.native_created_at IS NULL OR v.fixed_interval_state!=\'inside_fixed_interval\' OR json_extract(v.flags_json,\'$.observed_identity_date_or_unit_conflict\') IS NOT NULL)',(begin,),compressed=True))
   c.close();usable_months={m for (sid,m),n in qualified.items() if n};stopreason=stop['reason']
   p=OUT/'round_source_year_deltas.csv'
   with p.open('w',newline='',encoding='utf8') as f:
    writer=csv.writer(f);writer.writerow(['source_id','native_publication_year','new_core_bodies','not_an_acquisition_target'])
    for key,value in sorted(st.get('source_year_deltas',{}).items()):sid,year=key.rsplit('|',1);writer.writerow([sid,year,value,1])
   files.append(dict(path=str(p.relative_to(t.WORK)),bytes=p.stat().st_size,sha256=t.sha(p.read_bytes())))
   p=OUT/'historical_route_summary.csv'
   with p.open('w',newline='',encoding='utf8') as f:
    writer=csv.writer(f);writer.writerow(['source_id','frame_id','native_route','status','oldest_returned_publication_at','round_new_core_bodies','inventory_denominator_state','next_native_cursor'])
    for frontier in t.read_json(t.WORK/'FRONTIERS.json'):
     if frontier.get('historical_route') or frontier.get('status')=='active':
      cursor={k:frontier.get(k) for k in ['max_id','before','cursor','next_id','native_next_url'] if frontier.get(k) is not None}
      for field in ['archive_queue','message_queue','period_queue']:
       if frontier.get(field):cursor[field+'_next']=frontier[field][0]
      writer.writerow([frontier['source'],frontier['frame'],frontier['kind'],frontier['status'],frontier.get('oldest_returned_publication_at'),frontier.get('new_core_bodies',0),'unknown full historical denominator',json.dumps(cursor)])
   files.append(dict(path=str(p.relative_to(t.WORK)),bytes=p.stat().st_size,sha256=t.sha(p.read_bytes())))
   snap={'snapshot_at_utc':t.utc(),'owner_thread_id':t.OWNER,'scope_version':scope['version'],'hard_deadline_at_utc':scope['hard_deadline_at_utc'],'publication_interval':['1988-01-01','2026-09-21'],'september_partial':True,'counts':counts,'new_core_texts':st.get('new_core_bodies',0),'new_entities':st.get('new_entities',0),'new_entity_versions':st.get('new_entity_versions',0),'complete_independently_authored_body_entities':independent,'publication_month_qualified_independent_body_entities':sum(qualified.values()),'pooled_observed_months':len(usable_months),'full_calendar_months':465,'pending_source_era_date_mappings':len(pending),'inherited_returned_keys_without_catalog_entities':t.read_json(t.WORK/'INHERITED_BASELINE.json')['current_returned_key_catalog_difference'],'inherited_returned_key_baseline_preserved':True,'current_returned_key_catalog_difference':len(st['returned_object_ids'])-counts['native_entities'],'lifetime_charged_requests':st['requests'],'lifetime_distinct_returned_objects':len(st['returned_object_ids']),'continuation_charged_requests':st['requests']-t.read_json(t.WORK/'INHERITED_BASELINE.json')['lifetime_charged_requests'],'continuation_distinct_returned_objects':len(st['returned_object_ids'])-t.read_json(t.WORK/'INHERITED_BASELINE.json')['lifetime_distinct_returned_objects'],'changed_tranche_check':check,'stop_reason':stopreason,'actual_capacity_at_terminal_start':budget,'terminal_footprint_calibration':t.read_json(t.WORK/'TERMINAL_FOOTPRINT_CALIBRATION.json'),'complete_operation_tail_accounting':t.read_json(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json'),'implementation_hashes':{q.name:t.sha(q.read_bytes()) for q in t.WORK.glob('*.py')},'files':files,'terminal_seconds':time.monotonic()-start,'counts_are_not_completion':True,'climate_affect_fear_labels_executed':False}
   code_source_files=[{'path':p.name,'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())} for p in sorted(t.WORK.iterdir()) if p.is_file() and (p.suffix=='.py' or p.name in ('schema_legacy.sql','schema_v2.sql','source_registry.json','HISTORICAL_SCHEMA_AND_RUNTIME.md'))]
   t.atomic(OUT/'implementation_source_manifest.json',{'at_utc':t.utc(),'files':code_source_files,'runtime_controls_queues_raw_receipts_stores_excluded':True})
   manifest_path=OUT/'implementation_source_manifest.json';files.append({'path':str(manifest_path.relative_to(t.WORK)),'bytes':manifest_path.stat().st_size,'sha256':t.sha(manifest_path.read_bytes())})
   t.atomic(OUT/'collection_manifest.json',snap)
   older=sum(value for key,value in st.get('source_year_deltas',{}).items() if int(key.rsplit('|',1)[1])<2026)
   recent=sum(value for key,value in st.get('source_year_deltas',{}).items() if key.endswith('|2026'))
   report=f"""# Closed four-hour social historical acquisition and structural repair

The one fixed release stopped for `{stopreason}` at its original deadline or a recorded genuine operational boundary. It adds {snap['new_core_texts']:,} retained core text identities and {snap['new_entities']:,} typed native entities. The existing store has {counts['posts']:,} core texts, {independent:,} independently authored bodies and {snap['publication_month_qualified_independent_body_entities']:,} usable dated bodies across {len(usable_months)}/465 observed study months. These counts establish observed source presence, not complete archives or representative public speech. Dated views use reported native creation/sent dates; these do not independently prove first historical public availability.

The publication interval remains **1988-01-01 through 2026-09-21**, with September partial. The exact execution interval is {scope['earliest_network_and_load_start_at_utc']} to {scope['hard_deadline_at_utc']}; the snapshot is {snap['snapshot_at_utc']}. Publication/native sent time, reception, native edit, archive version, retrieval and report time remain separate. Later retrieved bodies are not certified as their historical versions.

## Historical gains and source frames

New core bodies decompose into {older:,} with native dates before 2026 and {recent:,} in 2026. `round_source_year_deltas.csv` and `historical_route_summary.csv` report actual source/year changes, oldest returned dates, source-state limits and remaining native cursors. These are observations, not density/year-share/coverage/source-count targets. Natural peaks remain intact and adjacent-month flags do not remove or downsample records or attribute events.

Newly admitted **W3C www-talk**, **Python-list public mailing archives** and **Hacker News' official native API** address concrete older-era/public-expression gaps. The W3C source index leads to native messages from October 1991; restricted mboxes are unused. Python's observed downloadable index starts in February 1999. HN preserves its reported native creation times, item IDs and reply/link relations; title/link-only submissions remain typed native evidence and do not become external articles or complete authored bodies. Mailing-list archival reproductions remain distinct from modern platform posts and campus/newspaper frames. None establishes whole-public coverage or author geography/role. No source aliases were confirmed and no raw, entity or version was deleted.

Existing forum sources continue documented oldest-created topic inventories, real more_topics_url links and full topic/post streams. Saved backward Mastodon cursors and already unfinished Bluesky/forum/context routes remain preserved. Current-account Bluesky graph growth does not displace actionable historical routes. First pages, first successful Loads, two loaded bodies and inherited project request/object/source milestones are not completion.

## Confirmed repairs, date evidence and remaining limits

`BUG_REPAIR_LEDGER.md` links actual code/state causes and tests. Recursive compact-state restoration now includes every predecessor key journal and old receipt chain, preserving the original 6,489 requests / 268,386 returned keys. The accepted social scheduler already had no prospective coverage2 stop; the two-body / extra-native-inventory regression continues, and no claim is made that all sparse historical source months were repaired merely because counts increased. The oldest-first forum route repairs recent-first truncation. A native Python mail archive exposed undecodable header bytes: derived UTF-8 metadata is repaired and flagged, original raw bytes remain intact, and its saved response replays without another HTTP request. An exact Mailman attachment-removal notice is retained as source-native evidence rather than authored text. The named linked attachment returned HTTP200, but its escaped HTML has an empty DIV and no rendered authored text; its 2019 Last-Modified value is not substituted for the 2002 native message Date. During the single changed-raw check, {raw_stats.get("archive_notice_only_version_corrections",0)} notice-only version mappings receive explicit derived-quality corrections, while original IDs/bodies/versions/counters remain. Authored text accompanied by a notice stays retained as authored. Round-only HTTP/Load telemetry is separated from inherited times. Terminal annotation/alias work uses bounded changed-metadata transactions with recorded actual journal peaks; no full database/feed copy or server migration occurs. A 200-record native-metadata calibration measured 258,048 bytes of SQLite growth and 168,776 bytes peak journal without changing body/entity/version counts. Preflight now includes outstanding metadata and the accepted compressed-export footprint, scaled by actual native catalog growth; terminal work consumes that reservation within the unchanged cumulative caps. A capacity-blocked source route does not stop smaller viable routes. Two completed native-metadata durability flushes consume estimated reservations as actual bytes without new source requests; the first permits same-interval acquisition to resume, while the final recheck remains capacity-blocked. Committed Load journals reconcile route counts and advance only already-durable archive bookmarks. Metadata performance claims are bounded by the recorded diagnostic erratum; sequential selection is validated, and measured accounting overhead motivates at-most1000-record flush transactions.

The selected four inherited Mastodon last batches still returned 2026 creation timestamps. Continuing max_id progress supports recent-first traversal as a collection-composition cause; complete instance eras, federation/cache horizons and historical author activity remain unknown. The Irish timeout remains recorded, including its proximity to the old deadline; it is not promoted to a proven historical archive limit. No publication/edit/retrieval date substitution or forced 2026 correction is justified by this inspection. Actual later older returns are reported when observed.

All six named Bluesky 2001/2006 records still return those values in both createdAt and indexedAt; repeating native values is not independent historical publication proof. The three named EarthScience mappings remain pending after source HTTP 403; API daily-quota and site-access stops remain separate. {len(pending)} inherited source-era mappings remain explicit. `changed_date_resolution_limits.csv.gz` separately preserves new missing/out-of-interval/conflicting native mappings. No date override was made to force a preferred period. Unknown denominators and unavailable eras remain unknown; pre-foundation modern-platform periods are not zero public expression.

## Operations and verification

Lifetime charged requests/returned keys are {st['requests']:,}/{len(st['returned_object_ids']):,}; this round adds {snap['continuation_charged_requests']:,}/{snap['continuation_distinct_returned_objects']:,}. The inherited accepted key/catalog difference is 43 (the earlier initial difference was 45); the current difference is {snap['current_returned_key_catalog_difference']}. Original counters and baseline discrepancies stay preserved rather than being reported as newly lost data. Raw, bodyless/noisy/multilingual/short/quoted/context material, complete bodies and immutable versions remain separately typed.

Cumulative 30 GB shared / 8 GB social, both active leases, shared heavy-I/O lock, 15 GiB floor / 48 MiB recovery / 64 KiB receipt margin, real operation peaks, documented provider backoff and source prohibitions remain enforced. No private/undocumented interface, login bypass, account/application, third-party message, government/reviewer access or Git/shared-log/control edit was used. Coordinator owns canonical lease closure and publication.

The terminal check covers SQLite integrity/foreign keys and this tranche's new body/raw/native identity/date/content mapping once, reusing accepted old hashes/checks. It is not truth verification or universal date correctness. Original native utterances, archival reproductions, federation and unresolved provenance stay explicit; an API returning a statement does not establish that statement's truth. Public access, local collection/retention, content licence and redistribution are separate registry facts, with no open-content/corpus-redistribution grant inferred.

The four evidence levels remain distinct: **dated source presence/readable original text** is reported here; climate/warming relevance/similarity is deferred; validated affect/risk/future-harm/responsibility associations are later and not automatically fear; fear-specific interpretation requires traceable passages and checked holder/target/horizon/quotation/negation. No semantic exclusion, corpus-wide topic/emotion labelling or fear-time-series gate ran.

Code/source/schema documentation, finalized metadata/manifests and this English report form the consolidated acquisition delivery. Runtime controls, progress, queues, owner/lease state, receipts, raw and stores remain local.
"""
   (OUT/'COLLECTION_REPORT.md').write_text(report)
   files.append(dict(path='summaries/COLLECTION_REPORT.md',bytes=(OUT/'COLLECTION_REPORT.md').stat().st_size,sha256=t.sha((OUT/'COLLECTION_REPORT.md').read_bytes())))
   t.atomic(OUT/'delivery_file_manifest.json',{'at_utc':t.utc(),'files':files,'collection_manifest_sha256':t.sha((OUT/'collection_manifest.json').read_bytes())})
   t.atomic(t.WORK/'CLOSED.json',{'at_utc':t.utc(),'manifest_sha256':t.sha((OUT/'collection_manifest.json').read_bytes()),'snapshot':snap})
  t.atomic(t.WORK/'WRITER_EXIT_OBSERVATION.json',{'at_utc':t.utc(),'collector_pid':stop['pid'],'collector_exited_before_closeout':True,'closeout_pid':os.getpid(),'deadline_unchanged':True})
 t.atomic(t.WORK/'LEASE_RELEASE_REQUEST.json',{'at_utc':t.utc(),'owner_thread_id':t.OWNER,'writer_mutex_released':True,'coordinator_owns_canonical_coordination_file':True,'request':'close only this owner lease; preserve accounting and all other leases'})
 print(json.dumps({k:snap[k] for k in ['snapshot_at_utc','counts','new_core_texts','lifetime_charged_requests','lifetime_distinct_returned_objects','pooled_observed_months','stop_reason']}))
if __name__=='__main__':main()
