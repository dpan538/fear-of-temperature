"""One post-exit changed-tranche verification and final metadata export."""
import pathlib,json,csv,collections,sqlite3,hashlib,gzip,datetime as dt,fcntl,os
import elt,archive_issues,incremental_exports
from bs4 import BeautifulSoup

def payload(ref):
 p=REPO/ref;data=p.read_bytes();return gzip.decompress(data) if p.suffix==".gz" else data

OWN=pathlib.Path(__file__).resolve().parent;REPO=OWN.parents[5];SCOPE=json.loads((OWN/'EXECUTION_SCOPE.json').read_text());DB=REPO/SCOPE['newspaper_durable_database'];EXCLUDED=set(SCOPE['excluded_newspaper_analysis_source_ids'])
def sha(data):return hashlib.sha256(data).hexdigest()
save=incremental_exports.save
csvwrite=incremental_exports.csvwrite
def monthly(rows):
 c=collections.Counter((r['source_id'],r['stratum'],r['publication_date'][:7]) for r in rows);out=[]
 for (sid,geo,m),n in sorted(c.items()):out.append(dict(source_id=sid,stratum=geo,publication_month=m,complete_article_IDs=n))
 return out

def close():
 assert (OWN/'EXECUTION_STOP.json').exists()
 terminal=json.loads((OWN/'TERMINAL_WRITER_EXIT.json').read_text());start_receipt=json.loads((OWN/'START_RECEIPT.json').read_text());stop_evidence=json.loads((OWN/'EXECUTION_STOP.json').read_text())
 assert terminal['host_reported_session_finished'] and terminal['PID_absence_verified'] and terminal['lifetime_mutex_available']
 assert terminal['collector_pid']==start_receipt['pid']
 if stop_evidence['reason']=='controlled_owner_interrupt_same_deadline':
  # The runtime preserves its generic KeyboardInterrupt label. A deadline
  # watchdog interruption is classified only from actual matching exit proof.
  watch=json.loads((OWN/'DEADLINE_WATCHDOG_RESULT.json').read_text())
  assert watch['action']=='SIGINT' and watch['collector_pid']==start_receipt['pid']
  assert watch['fixed_deadline']==SCOPE['hard_deadline_at_utc']
  assert dt.datetime.fromisoformat(watch['at_utc'])>=dt.datetime.fromisoformat(SCOPE['hard_deadline_at_utc'])
  assert terminal.get('terminal_reason')=='fixed_deadline_watchdog_interrupt'
 for name,digest in start_receipt['implementation_hashes'].items():assert sha((OWN/name).read_bytes())==digest
 for name,digest in start_receipt['frozen_predecessor_file_hashes'].items():assert sha((REPO/name).read_bytes())==digest

 with (REPO/SCOPE['newspaper_writer_mutex']).open('a+b') as m:
  fcntl.flock(m,fcntl.LOCK_EX|fcntl.LOCK_NB)
  save('WRITER_EXIT_OBSERVATION.json',dict(at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),host_reported_session_finished=True,mutex_available=True,source_network_stopped=True))
  with (REPO/SCOPE['shared_heavy_io_lock']).open('a+b') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   # Reserve the real metadata/export peak before one bounded final read.
   export_peak=incremental_exports.read_peak(OWN)
   final_capacity_before=elt.preflight(export_peak)
   c=sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
   qc=[r[0] for r in c.execute('PRAGMA quick_check')];fk=list(c.execute('PRAGMA foreign_key_check'))
   rows=[dict(r) for r in c.execute('SELECT a.* FROM articles a LEFT JOIN article_dispositions d ON d.article_id=a.article_id WHERE d.article_id IS NULL')]
   logs=[json.loads(x) for x in (OWN/'LOAD_LOG.jsonl').read_text().splitlines() if x];new={r['article_id']:r for r in logs if r.get('load_status')=='confirmed_complete'}
   versions={r['article_id']:dict(r) for r in c.execute('SELECT a.article_id,v.* FROM articles a JOIN article_versions v ON a.latest_version_id=v.version_id WHERE v.loaded_at>=?',(SCOPE['earliest_network_and_load_start_at_utc'],))};counts={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['articles','article_versions','evidence','article_dispositions']};disposition_versions={r['article_id']:dict(r) for r in c.execute('SELECT a.article_id,a.source_id,a.source_url,v.version_id,v.body_sha256,v.raw_reference,v.raw_sha256 FROM articles a JOIN article_versions v ON a.latest_version_id=v.version_id WHERE a.article_id IN (SELECT article_id FROM articles WHERE article_id=?)',('cambridge_news_nz:article:194',))};c.close()
  baseline=list(csv.DictReader((OWN/'BASELINE_METADATA.csv').open()));by={r['article_id']:r for r in rows};errors=[]
  for old in baseline:
   now=by.get(old['article_id'])
   if not now or any(str(now[k])!=old[k] for k in ['source_id','source_url','publication_date','stratum','work_family_id','latest_version_id']):errors.append({'kind':'baseline_identity_membership_changed','article_id':old['article_id']})
  disposition_path=OWN/'DERIVED_STRUCTURAL_UNIT_DISPOSITIONS.json'
  unit_dispositions=json.loads(disposition_path.read_text())['units'] if disposition_path.exists() else {}
  for aid,d in unit_dispositions.items():
   inherited=aid not in new
   r=disposition_versions.get(aid) if inherited else new.get(aid);v=disposition_versions.get(aid) if inherited else versions.get(aid)
   if inherited:
    if not r or d.get('countable_complete_article') is not False or any(d.get(k)!=r.get(k) for k in ['article_id','source_id','source_url','version_id','body_sha256','raw_reference','raw_sha256']):errors.append({'kind':'inherited_named_structural_disposition_SQL_mapping_mismatch','article_id':aid})
    continue
   if not r or not v or d.get('countable_complete_article') is not False or any(d.get(k)!=r.get(k) for k in ['article_id','source_id','source_url','request_id','version_id','body_sha256','raw_reference','raw_sha256']):errors.append({'kind':'named_structural_disposition_Load_mapping_mismatch','article_id':aid})
   elif any(d.get(k)!=v.get(k) for k in ['version_id','body_sha256','raw_reference','raw_sha256']):errors.append({'kind':'named_structural_disposition_SQL_version_mapping_mismatch','article_id':aid})
  qualified_new={aid:r for aid,r in new.items() if aid not in unit_dispositions}
  with (REPO/SCOPE['shared_heavy_io_lock']).open('a+b') as final_read_lock:
   fcntl.flock(final_read_lock,fcntl.LOCK_EX)
   final_read_capacity=elt.preflight(export_peak)
   raw_seen={};mapping=[];parsed_issues={} ;provenance_register=[]
   requests=[json.loads(x) for x in (OWN/'REQUESTS.jsonl').read_text().splitlines() if x]
   stored_seen={};raw_request_count=0
   # Verify this window's saved source documents once, including unused/pending
   # carriers and policy records. This does not reopen predecessor raw data.
   for receipt in requests:
    ref=receipt.get('raw_reference')
    if not ref:continue
    raw_request_count+=1
    if ref not in stored_seen:
     rp=REPO/ref;stored=rp.read_bytes();data=gzip.decompress(stored) if rp.suffix=='.gz' else stored
     stored_seen[ref]=sha(stored);raw_seen[ref]=sha(data)
    if raw_seen[ref]!=receipt['raw_sha256'] or stored_seen[ref]!=receipt['stored_sha256']:errors.append({'kind':'own_saved_request_raw_or_stored_hash_mismatch','target_id':receipt['target_id']})
   # Re-parse with the same admitted profile used by the exited collector.
   # Register in memory only; do not run acquisition or update parent ledgers.
   import extract_load
   profiles=json.loads((OWN/'BROADEN_PROFILES.json').read_text())
   import broaden,berkeley_html,native_batches
   for p in profiles:
    if broaden.approved(p):extract_load.ADAPTERS[p['source_id']]=dict(title=p['title'],country=p['country'],stratum=p['stratum'],edition=p['edition'],frame=p['source_frame'],selectors=p.get('selectors',['.entry-content']),exclude=['script','style','form','svg','.sharedaddy','.related-posts','.author-bio'],retention_limit=p['retention_limit'])
   profile_by={p['source_id']:p for p in profiles};native_cache={};genre_rows=[];native_mapping_counts=collections.Counter()
   for aid,r in new.items():
    v=versions.get(aid)
    if not v:errors.append({'kind':'new_latest_version_missing','article_id':aid});continue
    if sha(v['body_text'].encode())!=v['body_sha256']:errors.append({'kind':'new_TEXT_hash_mismatch','article_id':aid})
    body_ref=r.get('body_reference')
    if body_ref:
     if not (REPO/body_ref).is_file() or sha((REPO/body_ref).read_bytes())!=v['body_sha256']:errors.append({'kind':'new_retained_local_body_SQL_hash_mismatch','article_id':aid})
    elif not r.get('source_native_post_id') or v.get('body_reference'):
     errors.append({'kind':'new_expected_body_sidecar_reference_missing_or_conflicting','article_id':aid})
    ref=v['raw_reference']
    if ref and ref not in raw_seen:
     p=REPO/ref;stored=p.read_bytes();raw=gzip.decompress(stored) if p.suffix=='.gz' else stored;raw_seen[ref]=sha(raw);verified_raw_reference=ref
    if ref and raw_seen[ref]!=v['raw_sha256']:errors.append({'kind':'new_raw_hash_mismatch','article_id':aid})
    if not SCOPE['publication_interval'][0]<=r['publication_date']<=SCOPE['publication_interval'][1]:errors.append({'kind':'new_date_outside_fixed_interval','article_id':aid})
    provenance=json.loads(v['provenance_json'])
    native_genre='unresolved original article genre';categories=[]
    if provenance.get('source_native_post_id'):
     if ref not in native_cache:
      obj=json.loads(payload(ref));native_cache[ref]={o['id']:o for o in obj} if isinstance(obj,list) else {obj['id']:obj}
     pid=provenance['source_native_post_id'];obj=native_cache[ref].get(pid)
     if not obj:errors.append({'kind':'new_native_post_ID_missing_from_saved_body','article_id':aid})
     else:
      node=BeautifulSoup(obj.get('content',{}).get('rendered',''),'html.parser')
      for n in node.select('script,style,form,svg,.sharedaddy,.related-posts'):n.decompose()
      body=elt.renderer.normalise(elt.renderer.render(node));title=BeautifulSoup(obj.get('title',{}).get('rendered',''),'html.parser').get_text(' ',strip=True)
      if (elt.native_article_unit_status(obj) or sha(body.encode())!=v['body_sha256'] or (obj.get('date') or '')[:10]!=r['publication_date'] or elt.canon(obj.get('link',''))!=elt.canon(r['source_url']) or aid!=r['source_id']+':post:'+str(pid) or title!=r['title']):errors.append({'kind':'native_post_identity_date_complete_body_mapping_mismatch','article_id':aid})
      categories=obj.get('categories',[]);native_genre='publisher native category IDs; names and genre mapping unresolved';native_mapping_counts['publisher_native_post']+=1
     if profile_by.get(r['source_id'],{}).get('public_HTML_visibility_required'):
      href=provenance.get('public_HTML_raw_reference')
      if not href:errors.append({'kind':'required_public_HTML_mapping_missing','article_id':aid})
      else:
       hdata=payload(href);parse_markup=hdata
       import visible_template_markup
       access_boundary=visible_template_markup.access_boundary(hdata,extract_load.ADAPTERS[r['source_id']]['selectors'])
       if access_boundary and aid not in unit_dispositions:errors.append({'kind':'article_membership_preview_in_complete_qualification_view','article_id':aid})
       if aid=='gippsland_times:post:8980' and access_boundary!=unit_dispositions[aid].get('derived_access_boundary'):errors.append({'kind':'named_membership_preview_source_boundary_not_reproducible','article_id':aid})
       if provenance.get('public_HTML_structural_cleanup'):
        import visible_template_markup
        parse_markup,cleanup_facts=visible_template_markup.clean(hdata,r['source_id'])
        if cleanup_facts!=provenance['public_HTML_structural_cleanup']:errors.append({'kind':'public_HTML_structural_cleanup_not_reproducible','article_id':aid})
       hrecord,hbody,hstatus=extract_load._retained_parse(parse_markup,r['source_id'],r['source_url'])
       if provenance.get('public_HTML_source_local_date_equivalence_verified'):
        import source_local_publication_time
        if not source_local_publication_time.reconcile(dict(r),hrecord,hdata):errors.append({'kind':'source_local_UTC_publication_instant_equivalence_not_reproducible','article_id':aid})
       if sha(hdata)!=provenance.get('public_HTML_raw_sha256') or hstatus!='confirmed_complete' or hrecord.get('publication_date')!=r['publication_date'] or elt.canon(hrecord.get('source_url',''))!=elt.canon(r['source_url']) or ' '.join(hrecord.get('title','').split())!=' '.join(r['title'].split()) or sha(hbody.encode())!=v['body_sha256'] or provenance.get('subscription_bypass_used') is not False:errors.append({'kind':'public_HTML_native_JSON_identity_date_fullbody_mapping_mismatch','article_id':aid})
       native_mapping_counts['matching_public_HTML_native_JSON']+=1
    elif profile_by.get(r['source_id'],{}).get('interface_type')=='publisher_evidenced_wp_theme_HTML':
     import cambridge_html
     native,body,status=cambridge_html.parse(payload(ref),r['source_id'],r['source_url'])
     if status!='confirmed_complete' or native.get('article_id')!=aid or native.get('publication_date')!=r['publication_date'] or sha(body.encode())!=v['body_sha256']:errors.append({'kind':'native_WP_theme_HTML_original_ID_date_complete_body_mapping_mismatch','article_id':aid})
     native_mapping_counts['publisher_native_WP_theme_HTML']+=1;native_genre=native.get('publisher_native_genre') or 'unresolved publisher native genre'
    elif r['source_id']=='berkeley_daily_planet':
     key=(ref,provenance.get('native_carrier_url') or r['source_url'])
     if key not in native_cache:
      data=payload(ref)
      if '/article/' in key[1]:units,soup=berkeley_html.parse_single(data,key[1],profile_by[r['source_id']]['single_article_mapping'])
      else:units,soup=berkeley_html.parse(data,key[1])
      native_cache[key]={u['article_id']:u for u in units}
     u=native_cache[key].get(aid)
     if not u or u['status']!='confirmed_complete' or u['publication_date']!=r['publication_date'] or sha(u['body'].encode())!=v['body_sha256'] or elt.canon(u['source_url'])!=elt.canon(r['source_url']):errors.append({'kind':'Berkeley_native_article_identity_date_complete_body_mapping_mismatch','article_id':aid})
     native_mapping_counts['Berkeley_original_native_story']+=1;native_genre=u.get('publisher_native_genre') if u else 'unresolved publisher native genre'
    elif profile_by.get(r['source_id'],{}).get('article_template')=='Article__container' or r['source_id'] in ['green_left','indaily','alice_springs_news']:
     native,body,status=extract_load.parse(payload(ref),r['source_id'],r['source_url'])
     if status!='confirmed_complete' or native.get('publication_date')!=r['publication_date'] or sha(body.encode())!=v['body_sha256'] or elt.canon(native.get('source_url',''))!=elt.canon(r['source_url']):errors.append({'kind':'publisher_HTML_native_date_fullbody_mapping_mismatch','article_id':aid,'parser_status':status})
     native_mapping_counts['publisher_original_HTML']+=1
    genre_rows.append(dict(article_id=aid,source_id=r['source_id'],publication_year=r['publication_date'][:4],source_purpose_frame=profile_by.get(r['source_id'],{}).get('source_frame') or provenance.get('source_frame') or 'unresolved',native_genre_basis=native_genre,native_category_IDs=categories,semantic_genre_model_executed=False))
    if r['source_id']=='newtown_bee':
     import newtown_html
     if locals().get('verified_raw_reference')==ref:data=raw
     else:
      raw_path=REPO/ref;data=raw_path.read_bytes();data=gzip.decompress(data) if raw_path.suffix=='.gz' else data
     native,body,status=newtown_html.parse(data,'newtown_bee',r['source_url'])
     if status!='confirmed_complete' or native['article_id']!=aid or native['publication_date']!=r['publication_date'] or sha(body.encode())!=v['body_sha256']:
      errors.append({'kind':'newtown_native_uuid_original_date_complete_body_mapping_mismatch','article_id':aid,'native_status':status})
    if r['source_id']=='workers_advocate':
     issue_url=provenance['original_issue_url'];anchor=provenance['native_article_anchor']
     if ref not in parsed_issues:
      raw_path=REPO/ref;data=raw_path.read_bytes();data=gzip.decompress(data) if raw_path.suffix=='.gz' else data
      parsed_issues[ref]={u['native_article_anchor']:u for u in archive_issues.parse_issue(data,issue_url,provenance['expected_native_index_date'],provenance.get('edition_key'))['units']}
     u=parsed_issues[ref].get(anchor)
     if not u or u['status']!='confirmed_complete' or u['publication_date']!=r['publication_date'] or sha(u['body'].encode())!=v['body_sha256'] or issue_url+'#'+anchor!=r['source_url']:
      errors.append({'kind':'native_issue_article_identity_date_body_mapping_mismatch','article_id':aid})
    provenance_register.append(dict(article_id=aid,source_id=r['source_id'],source_url=r['source_url'],publication_date=r['publication_date'],retrieved_at_utc=provenance.get('retrieved_at_utc'),publication_date_basis=provenance.get('date_field'),publisher_timestamp=provenance.get('publisher_timestamp'),site_archive_display_date=provenance.get('site_archive_display_date'),original_header_day=provenance.get('original_header_day'),original_publication_code=provenance.get('original_publication_code'),observed_date_fields=provenance.get('observed_date_fields'),native_masthead_date=provenance.get('native_masthead_date'),expected_native_index_date=provenance.get('expected_native_index_date'),content_version_time=provenance.get('content_version_time'),public_HTML_source_local_timestamp=provenance.get('public_HTML_source_local_timestamp'),public_HTML_UTC_publication_timestamp=provenance.get('public_HTML_UTC_publication_timestamp'),public_HTML_visible_publication_line=provenance.get('public_HTML_visible_publication_line'),public_HTML_source_local_date_equivalence_verified=provenance.get('public_HTML_source_local_date_equivalence_verified'),public_HTML_structural_cleanup=provenance.get('public_HTML_structural_cleanup'),archive_transcription_time=provenance.get('archive_transcription_time'),archive_transcription_year=provenance.get('archive_transcription_year'),source_directness='archival reproduction' if r['source_id'] in ['workers_advocate','militant_uk_archive'] or provenance.get('original_archive_header') else 'original publisher representation',identity_date_content_mapping='verified changed-tranche hash/date mapping; named native issue boundaries re-parsed where applicable',provenance_statement=provenance.get('provenance'),origin_or_quoted_speaker_mapping='Separate embedded reprints/quotations/letters require later passage-level provenance checks; archival mapping does not establish claim truth',access_limit=provenance.get('retention_limit'),body_boundary=provenance.get('body_boundary'),native_date_limit=provenance.get('native_date_limit')))
    mapping.append(dict(analytical_subframe=provenance.get('analytical_subframe','current_regular_newspaper'),edition_key=provenance.get('edition_key'),source_frame_relation=provenance.get('source_frame_relation'),independent_conventional_newspaper_title=provenance.get('independent_conventional_newspaper_title',True),article_id=aid,source_id=r['source_id'],publication_date=r['publication_date'],version_id=v['version_id'],body_sha256=v['body_sha256'],raw_reference=ref,raw_sha256=v['raw_sha256'],source_url=r['source_url'],native_unit_mapping=r.get('article_boundary_evidence') or r.get('body_boundary'),original_issue_url=r.get('original_issue_url'),native_article_anchor=r.get('native_article_anchor'),provenance=r.get('provenance'),work_family_id=r.get('work_family_id',aid)))
  check=dict(at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),all_passed=qc==['ok'] and not fk and not errors,SQLite_quick_check=qc,foreign_key_errors=len(fk),baseline_metadata_IDs_preserved=len(baseline),new_complete_IDs_checked=len(qualified_new),new_retained_Load_IDs_checked=len(new),named_structural_nonarticle_units_preserved=len(unit_dispositions),new_unique_raw_objects_checked=len(raw_seen),errors=errors,verification_scope='All new retained Load SQL TEXT/raw mappings and declared sidecars, named derived structural dispositions and immutable baseline identity/date/version memberships; no old body/raw sweep')
  check['changed_tranche_raw_body_read_serialized_under_shared_heavy_io_lock']=True
  check['final_read_capacity']=final_read_capacity
  save('CHANGED_TRANCHE_FINAL_CHECK.json',check)
  supplementary=[r for r in rows if r['article_id'].startswith('workers_advocate:supplement:issue:')];supplement_ids={r['article_id'] for r in supplementary};regular_new={aid:r for aid,r in qualified_new.items() if aid not in supplement_ids}
  current=[r for r in rows if r['source_id'] not in EXCLUDED and r['article_id'] not in unit_dispositions and r['article_id'] not in supplement_ids];before=[r for r in baseline if r['source_id'] not in EXCLUDED];campus=[r for r in rows if r['source_id'] in EXCLUDED]
  genre_rows=[r for r in genre_rows if r['article_id'] in qualified_new];provenance_register=[r for r in provenance_register if r['article_id'] in qualified_new]
  csvwrite('STRUCTURAL_UNIT_DISPOSITION_REGISTER.csv',list(unit_dispositions.values()));csvwrite('NEW_SOURCE_PURPOSE_GENRE_ERA_REGISTER.csv',genre_rows);csvwrite('SOURCE_PROVENANCE_AND_DATE_REGISTER.csv',provenance_register);csvwrite('ADDITIONAL_ARTICLE_REGISTER.csv',[r for r in mapping if r['article_id'] in qualified_new]);csvwrite('CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv',current);csvwrite('NEWSPAPER_SUPPLEMENT_ARTICLE_REGISTER.csv',[r for r in mapping if r['article_id'] in supplement_ids]);csvwrite('SUPPLEMENT_MONTH_SOURCE_COUNTS.csv',monthly(supplementary));csvwrite('HISTORICAL_CAMPUS_PRESERVATION_REGISTER.csv',campus);csvwrite('MONTH_SOURCE_COUNTS_BEFORE.csv',monthly(before));csvwrite('MONTH_SOURCE_COUNTS_AFTER.csv',monthly(current))
  months=[f'{y}-{m:02d}' for y in range(1988,2027) for m in range(1,13) if (y,m)<=(2026,9)];bc=collections.Counter(r['publication_date'][:7] for r in before);ac=collections.Counter(r['publication_date'][:7] for r in current);delta=[]
  for mo in months:delta.append(dict(publication_month=mo,before_complete_article_IDs=bc[mo],after_complete_article_IDs=ac[mo],new_IDs=ac[mo]-bc[mo],observed_sources=len({r['source_id'] for r in current if r['publication_date'].startswith(mo)}),partial_boundary=mo=='2026-09'))
  sc=collections.Counter(r['publication_date'][:7] for r in supplementary)
  csvwrite('COMBINED_FAMILY_MONTHLY_PRESENCE.csv',[dict(publication_month=m,regular_complete_article_IDs=ac[m],supplement_complete_article_IDs=sc[m],combined_family_article_IDs=ac[m]+sc[m],regular_frame_gap=ac[m]==0,does_not_change_regular_frame=True) for m in months]);csvwrite('SUPPLEMENT_SOURCE_YEAR_DELTA.csv',[dict(source_id=s,publication_year=y,new_complete_IDs=n) for (s,y),n in sorted(collections.Counter((r['source_id'],r['publication_date'][:4]) for r in supplementary).items())])
  csvwrite('MONTHLY_BEFORE_AFTER.csv',delta);csvwrite('RESIDUAL_EMPTY_MONTHS.csv',[r for r in delta if r['after_complete_article_IDs']==0]);csvwrite('SOURCE_YEAR_DELTA.csv',[dict(source_id=s,publication_year=y,new_complete_IDs=n) for (s,y),n in sorted(collections.Counter((r['source_id'],r['publication_date'][:4]) for r in regular_new.values()).items())])
  peaks=[]
  for i,mo in enumerate(months):
   near=[ac[months[j]] for j in range(max(0,i-3),min(len(months),i+4)) if j!=i];mean=sum(near)/len(near) if near else None
   if mean is not None and ac[mo]>max(near,default=0):peaks.append(dict(publication_month=mo,article_IDs=ac[mo],preceding_following_available_month_counts=near,neighbor_mean=mean,boundary_context_incomplete=i<3 or i>=len(months)-3,action='diagnostic_only; retain all records; no event attribution'))
  csvwrite('MONTH_PEAK_CONTEXT_FLAGS.csv',peaks)
  transport=json.loads((OWN/'TRANSPORT_STATE.json').read_text());requests=[json.loads(x) for x in (OWN/'REQUESTS.jsonl').read_text().splitlines() if x];stop=json.loads((OWN/'EXECUTION_STOP.json').read_text());start=json.loads((OWN/'INPUT_SNAPSHOT.json').read_text())
  csvwrite('HOST_STOP_REGISTER.csv',[dict(host=h,stop=s,scope='Inherited/actual source access evidence; no bypass') for h,s in transport['access_stops'].items()]);csvwrite('RAW_OBJECT_MANIFEST.csv',[{k:r.get(k) for k in ['target_id','source_id','url','status','raw_reference','raw_sha256','raw_bytes','stored_sha256','stored_bytes','finished_at_utc']} for r in requests if r.get('raw_reference')]);csvwrite('PENDING_DISPOSITION_REGISTER.csv',[dict(r,original_event_preserved=True,later_complete_ID_in_same_window=r.get('article_id') in new) for r in logs if r.get('load_status')!='confirmed_complete'])
  frontier=json.loads((OWN/'BROADEN_CURSORS.json').read_text())
  frontier_rows=[dict(source_id=s,stage=v.get('stage'),attempted_metadata_pages=v.get('attempted_pages'),next_url=v.get('next_url'),reason=v.get('blocked_reason') or v.get('reason'),native_inventory_denominator='observed interface only; historical population unknown') for s,v in frontier.items()]
  for p in profiles:
   sid=p['source_id']
   if sid not in frontier:frontier_rows.append(dict(source_id=sid,stage='admitted_profile_no_generic_cursor',reason='Native adapter state separately retained; profile alone is not contribution',native_inventory_denominator='historical population unknown'))
  bdf=berkeley_html.state()
  bdf_inventory=dict(source_id='berkeley_daily_planet',stage=bdf.get('stage'),frontier_contexts=len(bdf.get('frontier_queue',[])),seen_indexes=len(bdf.get('seen_indexes',[])),native_units_by_status=dict(collections.Counter(v.get('status','unresolved') for v in bdf.get('units',{}).values())),context_history_count=len(bdf.get('context_history',[])),native_inventory_denominator='Observed original story/carrier frontier; complete historical editions unknown')
  frontier_rows.append(bdf_inventory);csvwrite('SOURCE_FRONTIER_REGISTER.csv',frontier_rows)
  queue_inventory={}
  for name in ['FOCUSED_NATIVE_SOURCE_RESUME.json','MISSING_MONTH_ROUTE_LEDGER.json','NATIVE_CURSORS.json','GL_ISSUE_QUEUE.json','GL_ISSUES_PROCESSED.json','BERKELEY_NATIVE_FRONTIER.json']:
   path=OWN/name
   if path.exists():
    value=json.loads(path.read_text());queue_inventory[name]=dict(retained_file=name,sha256=sha(path.read_bytes()),top_level_entries=len(value),type=type(value).__name__)
  # Frozen named issues and own Load metadata, without reopening active cursors or old raw.
  evidence=list(csv.DictReader((REPO/'work_packages/M1_source_access/27_newspaper_context_recovery_20261008/control/20261010_source_frame_redesign/MONTH_REPAIR_EVIDENCE.csv').open()));legacy={r['month'] for r in evidence if json.loads(r['source_id_counts'])=={'green_left':2}};zeros={m for m in months if bc[m]==0}
  legacy_new=collections.Counter(r['publication_date'][:7] for r in qualified_new.values() if r['source_id']=='green_left' and r['publication_date'][:7] in legacy);before_sources={r['source_id'] for r in before};after_sources={r['source_id'] for r in current};native_hops=transport.get('native_http_hops',{})
  focused=dict(legacy_GL_affected_months=len(legacy),legacy_GL_months_with_real_surplus=len(legacy_new),named_legacy_new_IDs=sum(legacy_new.values()),named_legacy_month_new_IDs=dict(legacy_new),baseline_empty_months=len(zeros),newly_present_baseline_empty_months=sorted(m for m in zeros if ac[m]>0),remaining_baseline_empty_months=sorted(m for m in zeros if ac[m]==0),before_contributing_title_IDs=len(before_sources),after_contributing_title_IDs=len(after_sources),new_contributing_title_ids=sorted(after_sources-before_sources),admitted_profiles_are_not_contributions=True,exactly_two_before=sum(bc[m]==2 for m in months),exactly_two_after=sum(ac[m]==2 for m in months),counts_and_source50_are_not_runtime_gates=True)
  csvwrite('LEGACY_AFFECTED_MONTH_BEFORE_AFTER.csv',[dict(publication_month=m,before_GL_complete_IDs=sum(r['source_id']=='green_left' and r['publication_date'].startswith(m) for r in before),new_GL_complete_IDs=legacy_new[m],after_total_complete_IDs=ac[m],original_processed_directory_flags_preserved=True,observed_queued_inventory_exhaustion_not_claimed=True) for m in sorted(legacy)])
  # One post-exit metadata inventory of named queued surplus. No bodies, queue
  # statuses or original issue processed flags are changed by this report.
  import production
  queue_bytes=sum(q.stat().st_size for root in elt.QUEUE_ROOTS for q in [root/'queues/green_left.json'] if q.exists())
  with elt.LOCK.open('a+b') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);elt.preflight(export_peak+4*queue_bytes+65536)
  queued={elt.canon(t['url']):t for t in production.targets('green_left')}
  issue_metadata=json.loads((OWN/'GL_ISSUE_QUEUE.json').read_text());processed=set(json.loads((OWN/'GL_ISSUES_PROCESSED.json').read_text()));overlay=json.loads((OWN/'EXPECTED_MONTH_OVERLAY.json').read_text())['entries'];known=production.KNOWN;touched=set(transport['targets']);surplus=[]
  for m in sorted(legacy):
   ts=[t for url,t in queued.items() if overlay.get(url,{}).get('expected_month',t.get('month'))==m];locators=[i for i in issue_metadata if i['month']==m]
   committed=sum(elt.canon(t.get('article_url') or t['url']) in known for t in ts)
   unattempted=sum(elt.canon(t.get('article_url') or t['url']) not in known and elt.transport_target_id('green_left','article',t['url']) not in touched for t in ts)
   pending=sum(elt.canon(t.get('article_url') or t['url']) not in known and elt.transport_target_id('green_left','article',t['url']) in touched for t in ts)
   surplus.append(dict(publication_month=m,dated_issue_locators=len(locators),issue_locators_marked_processed=sum(i['url'] in processed for i in locators),unique_native_queued_URLs=len(ts),committed_alias_URLs=committed,untouched_uncommitted_candidate_URLs=unattempted,touched_uncommitted_URLs=pending,body_exhaustion_claimed=False,remaining_candidates_not_complete_articles=True,original_flags_preserved=True))
  csvwrite('LEGACY_TERMINAL_QUEUE_INVENTORY.csv',surplus)
  focused['terminal_untouched_uncommitted_candidate_URLs']=sum(r['untouched_uncommitted_candidate_URLs'] for r in surplus);focused['terminal_touched_uncommitted_URLs']=sum(r['touched_uncommitted_URLs'] for r in surplus)
  canonical_status=json.loads((OWN/'NATIVE_BATCH_UNIT_STATUS.json').read_text());baseline_status=json.loads((elt.PREDECESSOR/'NATIVE_BATCH_UNIT_STATUS.json').read_text());named_transport=json.loads((OWN/'NAMED_NATIVE_TRANSPORT_RECOVERY.json').read_text())['entries']
  check['baseline_native_status_IDs_preserved']=set(baseline_status)<=set(canonical_status);check['exact_named_transport_original_rows_preserved']=all(canonical_status.get(a,{}).get('status')==v['original_status'] and canonical_status.get(a,{}).get('request_id')==v['original_request_id'] for a,v in named_transport.items());check['named_transport_cases']=len(named_transport)
  check['all_passed']=check['all_passed'] and check['baseline_native_status_IDs_preserved'] and check['exact_named_transport_original_rows_preserved']
  # Coordinator-named fresh directory batches: check against changed-tranche
  # SQL/Load results. Export compact issue rows; individual evidence stays local.
  fresh_proof=json.loads((OWN/'HOUR2_FRESH_ISSUE_REAL_LOAD.json').read_text());fresh_state=json.loads((OWN/'FRESH_ISSUE_ARTICLE_CURSORS.json').read_text());fresh_rows=[];fresh_errors=[]
  for issue in ['293','294','295']:
   locator=next(i for i in issue_metadata if i['url'].rsplit('/',1)[-1]==issue);year=locator['publication_date'][:4]
   candidates={u for u in queued if elt.urlsplit(u).path.startswith('/'+year+'/'+issue+'/')};v=fresh_state['issues'][issue];actual=fresh_proof['issues'].get(issue,{}).get('actual_results',[])
   complete={r['article_id'] for r in actual if r.get('load_status')=='confirmed_complete'}
   for r in actual:
    if elt.canon(r['source_url']) not in candidates or r.get('dated_issue_publication_date')!=locator['publication_date']:fresh_errors.append(dict(issue=issue,kind='fresh_issue_locator_mapping_mismatch',request_id=r.get('request_id')))
    if r.get('load_status')=='confirmed_complete' and (r.get('article_id') not in regular_new or regular_new[r['article_id']]['publication_date']!=r.get('publication_date')):fresh_errors.append(dict(issue=issue,kind='fresh_issue_result_SQL_Load_mismatch',article_id=r.get('article_id')))
   if not set(map(elt.canon,v['attempted_URLs']))<=candidates or not 0<=v['next_cursor']<=len(candidates):fresh_errors.append(dict(issue=issue,kind='fresh_issue_cursor_inventory_mismatch'))
   touched_uncommitted=sum(elt.transport_target_id('green_left','article',u) in touched and u not in known for u in candidates);untouched=sum(elt.transport_target_id('green_left','article',u) not in touched and u not in known for u in candidates)
   fresh_rows.append(dict(issue=issue,dated_issue_url=locator['url'],native_issue_publication_date=locator['publication_date'],unique_native_candidate_URLs=len(candidates),actual_recorded_article_results=len(actual),real_new_complete_article_IDs=len(complete),pending_result_events=sum(r.get('load_status')!='confirmed_complete' for r in actual),touched_uncommitted_candidate_URLs=touched_uncommitted,untouched_uncommitted_candidate_URLs=untouched,next_cursor=v['next_cursor'],completed_bounded_operations=v['completed_bounded_operations'],body_exhaustion_claimed=False,operation_bound_not_issue_quota=True))
  check['fresh_issue_real_result_errors']=fresh_errors;check['fresh_issue_real_results_SQL_Load_verified']=not fresh_errors;check['all_passed']=check['all_passed'] and not fresh_errors
  csvwrite('FRESH_ISSUE_TERMINAL_REGISTER.csv',fresh_rows)
  check['own_saved_request_raw_records_checked']=raw_request_count;check['own_saved_request_unique_stored_objects_checked']=len(stored_seen)
  baseline_ids={r['article_id'] for r in baseline};SQL_new_ids=set(by)-baseline_ids-(set(unit_dispositions)-set(new))
  check['unlogged_new_SQL_article_IDs']=sorted(SQL_new_ids-set(new));check['logged_complete_IDs_missing_from_SQL_delta']=sorted(set(new)-SQL_new_ids)
  check['own_Load_ID_SQL_conservation']=set(new)==SQL_new_ids and not set(new)&baseline_ids;check['native_HTTP_hops_max']=max(native_hops.values(),default=0);check['native_four_hop_ceiling_preserved']=check['native_HTTP_hops_max']<=SCOPE['max_http_hops_per_target'];check['native_mapping_checked_counts']=dict(native_mapping_counts);check['all_passed']=check['all_passed'] and check['own_Load_ID_SQL_conservation'] and check['native_four_hop_ceiling_preserved'];save('CHANGED_TRANCHE_FINAL_CHECK.json',check)
  summary=dict(at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),status='closed',publication_interval=SCOPE['publication_interval'],hard_deadline_at_utc=SCOPE['hard_deadline_at_utc'],stop_reason=stop['reason'],baseline_current_newspaper_IDs=len(before),additional_qualified_IDs=len(new),current_newspaper_complete_IDs=len(current),historical_campus_IDs_preserved=len(campus),observed_study_months=sum(ac[m]>0 for m in months),remaining_empty_months=sum(ac[m]==0 for m in months),new_source_year_mix={s:{y:n for (sid,y),n in collections.Counter((r['source_id'],r['publication_date'][:4]) for r in new.values()).items() if sid==s} for s in sorted({r['source_id'] for r in new.values()})},new_distinct_transport_target_receipts=len(requests),new_recorded_HTTP_request_attempts=sum(r.get('HTTP_request_attempts_recorded',0) for r in requests),new_HTTP_response_hops=sum(len(r.get('hops',[])) for r in requests),cumulative_transport_targets=len(transport['targets']),cumulative_native_targets=len(transport['charged_native_targets']),baseline_cumulative_transport_targets=start['cumulative_distinct_transport_targets'],baseline_cumulative_native_targets=start['cumulative_native_targets'],database_counts=counts,checks=check,source_frontier=frontier,semantic_labels_executed=False,parent_metrics_used_for_control=False,old_body_raw_sweep=False)
  # Keep large URL arrays in local cursors rather than duplicate them in final summary.
  summary['source_frontier']={s:{k:len(v) if isinstance(v,list) else v for k,v in q.items()} for s,q in frontier.items()}
  with elt.LOCK.open('a+b') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);summary['final_resource_capacity']=elt.resource(0)
  summary['final_resource_capacity_before_export']=final_capacity_before
  summary['focused_repair_priorities']=focused;summary['source_use_stops']=json.loads((OWN/'FOCUSED_SOURCE_USE_STOPS.json').read_text());summary['terminal_writer_exit']=terminal
  summary['original_writer_stop_reason']=stop['reason'];summary['stop_reason']=terminal.get('terminal_reason') or stop['reason']
  progress=json.loads((OWN/'PROGRESS.json').read_text())
  summary['earliest_authorized_network_and_load_start_at_utc']=SCOPE['earliest_network_and_load_start_at_utc']
  summary['new_recorded_HTTP_request_attempts_from_complete_receipts']=summary['new_recorded_HTTP_request_attempts']
  summary['new_recorded_HTTP_request_attempts']=max(summary['new_recorded_HTTP_request_attempts'],progress['new_HTTP_request_attempts_recorded'])
  summary['new_HTTP_response_hops_from_complete_receipts']=summary['new_HTTP_response_hops'];summary['new_HTTP_response_hops']=max(summary['new_HTTP_response_hops'],progress['new_HTTP_response_hops'])
  summary['counter_limit']='Preserved runtime high-water includes interrupted instrumentation; receipt sums separately retained, no reset'
  summary['first_last_real_activity']={k:progress.get(k) for k in ['first_successful_HTTP_at_utc','last_successful_HTTP_at_utc','first_successful_Load_at_utc','last_successful_Load_at_utc']}
  summary['current_2026_source_counts']=dict(collections.Counter(r['source_id'] for r in current if r['publication_date'].startswith('2026-')))
  summary['current_2026_IDs']=sum(summary['current_2026_source_counts'].values())
  summary['Berkeley_native_frontier_inventory']=bdf_inventory;summary['retained_queue_inventory']=queue_inventory
  summary['Workers_Advocate_native_issue_mapping_checks']=len(parsed_issues)
  summary['retained_record_counts_are_not_independent_work_counts']=True
  summary['source_admission_and_limits']=json.loads((OWN/'SOURCE_ADMISSION_AND_LIMITS.json').read_text())
  summary['additional_retained_Load_IDs']=len(new);summary['additional_qualified_IDs']=len(qualified_new);summary['additional_regular_newspaper_IDs']=len(regular_new);summary['additional_supplementary_edition_IDs']=len(supplementary);summary['separate_supplementary_month_counts']=dict(sc);summary['combined_family_observed_months']=sum(ac[m]+sc[m]>0 for m in months);summary['frame_separation']=json.loads((OWN/'FRAME_SEPARATION.json').read_text());summary['new_title_admission_evidence']=json.loads((OWN/'NEW_TITLE_ADMISSION_EVIDENCE.json').read_text());summary['new_title_public_visibility_required']=sorted(p['source_id'] for p in profiles if p.get('public_HTML_visibility_required'));summary['saved_source_interface_projection']=dict(results=[json.loads(x) for x in (OWN/'SOURCE_INTERFACE_PROJECTION_RESULTS.jsonl').read_text().splitlines()] if (OWN/'SOURCE_INTERFACE_PROJECTION_RESULTS.jsonl').exists() else [],body_or_SQL_Load=False,standard_robots_and_adapters=True)
  summary['named_structural_unit_dispositions']=unit_dispositions
  summary['derived_qualification_basis']='Current SQL accepted rows minus exact evidenced named publisher-template and membership-preview units; all original SQL rows, IDs, versions, Load logs, counters and raw remain preserved'
  summary['new_source_year_mix']={s:{y:n for (sid,y),n in collections.Counter((r['source_id'],r['publication_date'][:4]) for r in qualified_new.values()).items() if sid==s} for s in sorted({r['source_id'] for r in qualified_new.values()})}
  summary['baseline_2026_concentration_diagnostic']=dict(source='Current bound BASELINE_METADATA.csv; earlier diagnostics remain frozen',baseline_2026_current_IDs=sum(r['publication_date'].startswith('2026-') for r in before),source_counts=dict(collections.Counter(r['source_id'] for r in before if r['publication_date'].startswith('2026-'))),automatic_date_or_volume_correction=False)
  summary['new_regular_source_year_mix']={s:{y:n for (sid,y),n in collections.Counter((r['source_id'],r['publication_date'][:4]) for r in regular_new.values()).items() if sid==s} for s in sorted({r['source_id'] for r in regular_new.values()})}
  summary['fresh_issue_bridge']={'issues':fresh_rows,'proof_reference_local_only':'HOUR2_FRESH_ISSUE_REAL_LOAD.json','cursor_reference_local_only':'FRESH_ISSUE_ARTICLE_CURSORS.json','same_hard_deadline':SCOPE['hard_deadline_at_utc'],'actual_new_complete_IDs':sum(r['real_new_complete_article_IDs'] for r in fresh_rows),'pending_result_events':sum(r['pending_result_events'] for r in fresh_rows),'counts_not_completion_gates':True}
  summary['visible_template_saved_recovery']=[json.loads(x) for x in (OWN/'VISIBLE_TEMPLATE_RECOVERY_RESULTS.jsonl').read_text().splitlines()] if (OWN/'VISIBLE_TEMPLATE_RECOVERY_RESULTS.jsonl').exists() else []
  summary['visible_template_recovery_current_qualified_IDs']=sum(r['load_status']=='confirmed_complete' and r['article_id'] in qualified_new for r in summary['visible_template_saved_recovery'])
  summary['membership_preview_qualification_correction']={'article_id':'gippsland_times:post:8980','historical_SQL_Load_preserved':True,'countable_complete_article':False,'whole_original_access_unverified':True,'current_derived_unit_disposition':unit_dispositions['gippsland_times:post:8980'],'other_six_recovered_Gippsland_articles_remain_qualified':True,'18_prior_pending_cases_remain_pending':True}
  summary['visible_template_recovery_fixture']=json.loads((OWN/'VISIBLE_TEMPLATE_COMPLETE_RECOVERY_CHECK.json').read_text())
  summary['batch_status_preservation_repair']=json.loads((OWN/'BATCH_STATUS_RESTORATION_AND_NAMED_KILKENNY_CHECK.json').read_text())
  summary['source_local_time_saved_recovery']=[json.loads(x) for x in (OWN/'SOURCE_LOCAL_TIME_RECOVERY_RESULTS.jsonl').read_text().splitlines()] if (OWN/'SOURCE_LOCAL_TIME_RECOVERY_RESULTS.jsonl').exists() else []
  save('DELIVERY_SUMMARY.json',summary);save('LEASE_RELEASE_REQUEST.json',dict(at_utc=summary['at_utc'],owner_thread_id=SCOPE['owner_thread_id'],lease_id=SCOPE['lease_id'],writer_exited=True,mutex_available=True,stop_reason=summary['stop_reason'],original_writer_stop_reason=stop['reason'],coordinator_action='Release canonical lease; worker has not edited coordination',original_deadline_unchanged=True))
  import final_post_review_report
  incremental_exports.write(OWN/'DELIVERY_REPORT.md',final_post_review_report.report(summary,genre_rows,frontier_rows,[r for r in logs if r.get('load_status')!='confirmed_complete']))
  save('WORKER_COMPLETION.json',dict(at_utc=summary['at_utc'],status='completed' if check['all_passed'] else 'closed_with_verification_issues',all_changed_tranche_checks_passed=check['all_passed'],new_complete_IDs=len(qualified_new),new_retained_Load_IDs=len(new),fixed_deadline_preserved=True,writer_exited=True))
  manifest={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in OWN.iterdir() if p.is_file() and p.name in ['FRESH_ISSUE_TERMINAL_REGISTER.csv','LEGACY_TERMINAL_QUEUE_INVENTORY.csv','NEWSPAPER_SUPPLEMENT_ARTICLE_REGISTER.csv','SUPPLEMENT_MONTH_SOURCE_COUNTS.csv','SUPPLEMENT_SOURCE_YEAR_DELTA.csv','COMBINED_FAMILY_MONTHLY_PRESENCE.csv','FRAME_SEPARATION.json','NEW_TITLE_ADMISSION_EVIDENCE.json','NAMED_NATIVE_TRANSPORT_RECOVERY.json','STRUCTURAL_UNIT_DISPOSITION_REGISTER.csv','DERIVED_STRUCTURAL_UNIT_DISPOSITIONS.json','NEW_SOURCE_PURPOSE_GENRE_ERA_REGISTER.csv','LEGACY_AFFECTED_MONTH_BEFORE_AFTER.csv','RESIDUAL_EMPTY_MONTHS.csv','HOST_STOP_REGISTER.csv','PENDING_DISPOSITION_REGISTER.csv','MONTH_SOURCE_COUNTS_BEFORE.csv','MONTH_SOURCE_COUNTS_AFTER.csv','MONTH_PEAK_CONTEXT_FLAGS.csv','DELIVERY_SUMMARY.json','DELIVERY_REPORT.md','CHANGED_TRANCHE_FINAL_CHECK.json','ADDITIONAL_ARTICLE_REGISTER.csv','CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv','MONTHLY_BEFORE_AFTER.csv','SOURCE_YEAR_DELTA.csv','RAW_OBJECT_MANIFEST.csv','SOURCE_FRONTIER_REGISTER.csv','HISTORICAL_CAMPUS_PRESERVATION_REGISTER.csv','SOURCE_PROVENANCE_AND_DATE_REGISTER.csv']};save('DELIVERY_FILE_RECEIPTS.json',manifest)
  print(json.dumps({k:summary[k] for k in ['status','additional_qualified_IDs','current_newspaper_complete_IDs','observed_study_months','remaining_empty_months','stop_reason']}),flush=True)

if __name__=='__main__':close()
