"""One changed-tranche export after actual writer exit; current newspaper frame separate."""
import collections,csv,fcntl,io,json,sqlite3,hashlib,ast,gzip
import elt
from bs4 import BeautifulSoup
MONTHS=[f'{y:04d}-{m:02d}' for y in range(1988,2027) for m in range(1,13) if f'{y:04d}-{m:02d}'<='2026-09']
def lines(p):return [json.loads(x) for x in p.read_text().split('\n') if x] if p.exists() else []
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def csv_save(name,rows,fields=None):
 fields=fields or list(dict.fromkeys(k for r in rows for k in r)) or ['empty_register'];out=io.StringIO();w=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows);b=out.getvalue().encode()
 with elt.LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);elt.preflight(len(b)*2+65536);p=elt.OWN/name;p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.pending');t.write_bytes(b);t.replace(p)
def main():
 close=json.loads((elt.OWN/'COLLECTION_CLOSE_RECEIPT.json').read_text());assert close['writer_exit_observed'] and close['no_active_writer']
 observed=json.loads((elt.OWN/close['writer_exit_observation_reference']).read_text())
 assert digest(elt.OWN/close['writer_exit_observation_reference'])==close['writer_exit_observation_sha256']
 assert observed['host_reported_session_finished'] and observed['writer_pid']==close['last_writer_pid']
 with (elt.REPO/elt.SCOPE['newspaper_writer_mutex']).open('a+b') as owner:
  fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB);return deliver(close)
def deliver(close):
 snap=json.loads((elt.OWN/'INPUT_SNAPSHOT.json').read_text());baseline=list(csv.DictReader((elt.PREDECESSOR/'CUMULATIVE_ARTICLE_REGISTER.csv').open()));frozen={r['article_id']:r for r in baseline};assert len(frozen)==snap['baseline_complete_IDs']
 newspaper_baseline=[r for r in baseline if r['source_id'] not in elt.EXCLUDED];campus=[r for r in baseline if r['source_id'] in elt.EXCLUDED];assert len(newspaper_baseline)==3085 and len(campus)==9249
 import broaden,extract_load,native_html
 profiles_before={p['source_id']:p for p in broaden.profiles()}
 for sid,p in profiles_before.items():extract_load.ADAPTERS[sid]={'title':p['title'],'country':p['country'],'stratum':p['stratum'],'edition':p['edition'],'frame':p['source_frame'],'retention_limit':p['retention_limit']}
 old_dispositions={r['article_id']:r['status'] for r in csv.DictReader((elt.PREDECESSOR/'RETAINED_DISPOSITION_REGISTER.csv').open())}
 requests=list({r['target_id']:r for r in lines(elt.OWN/'REQUESTS.jsonl')}.values());by_request={r['target_id']:r for r in requests};new=[];pending=[];errors=[];preserved=True;seen=set();raw_cache={}
 with elt.LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);c=sqlite3.connect('file:'+str(elt.DB)+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
  q=c.execute('SELECT a.*,v.body_sha256,v.raw_reference,v.raw_sha256,v.body_reference,CASE WHEN a.first_loaded_at>? THEN v.body_text END AS new_body,CASE WHEN a.first_loaded_at>? THEN v.provenance_json END AS new_provenance FROM articles a JOIN article_versions v ON v.version_id=a.latest_version_id LEFT JOIN article_dispositions d ON d.article_id=a.article_id WHERE d.article_id IS NULL',(snap['at_utc'],)*2).fetchall()
  for row in q:
   aid=row['article_id'];seen.add(aid)
   if aid in frozen:
    old=frozen[aid];preserved &= row['publication_date']==old['publication_date'] and row['source_url']==old['source_url'] and row['body_sha256']==old['body_sha256'] and row['work_family_id']==old['work_family_id'] and row['latest_version_id']==old['version_id'];continue
   r=json.loads(row['new_provenance']);body=row['new_body'];r.update(article_id=aid,publication_date=row['publication_date'],source_url=row['source_url'],stratum=row['stratum'],work_family_id=row['work_family_id'],version_id=row['latest_version_id'],body_sha256=row['body_sha256'],disposition='confirmed_complete',whole_TEXT_characters=len(body),whole_TEXT_bytes=len(body.encode()),collection_frame='newspaper_current_noncampus')
   rec=by_request.get(r.get('request_id'));rp=elt.REPO/row['raw_reference'] if row['raw_reference'] else None
   body_ok=bool(body and hashlib.sha256(body.encode()).hexdigest()==row['body_sha256'] and elt.eligible(row['publication_date']) and row['source_url'].startswith('https://') and row['source_id'] not in elt.EXCLUDED)
   raw_ok=bool(rec and rec['status']=='saved' and not rec.get('partial') and rp and rp.exists() and rp.stat().st_size==rec.get('stored_bytes') and rec.get('raw_sha256')==r.get('raw_sha256') and rec.get('stored_sha256')==r.get('stored_sha256') and rec.get('raw_bytes',0)<=elt.SCOPE['default_raw_object_cap_bytes'])
   ref=row['raw_reference']
   if raw_ok and ref not in raw_cache:
    stored=rp.read_bytes();payload=gzip.decompress(stored) if rp.suffix=='.gz' else stored
    raw_cache[ref]={'payload':payload,'raw_ok':hashlib.sha256(stored).hexdigest()==rec['stored_sha256'] and hashlib.sha256(payload).hexdigest()==rec['raw_sha256']==row['raw_sha256'] and len(payload)==rec['raw_bytes']}
   raw_ok &= bool(ref in raw_cache and raw_cache[ref]['raw_ok'])
   native_ok=True
   if r.get('source_native_post_id') and raw_ok:
    native_ok=aid==r['source_id']+':post:'+str(r['source_native_post_id'])
    if 'object' not in raw_cache[ref]:raw_cache[ref]['object']=json.loads(raw_cache[ref]['payload'])
    objects=raw_cache[ref]['object']
    obj=objects[r['native_batch_item_index']] if r.get('native_batch_item_id') else objects
    native_ok &= obj['id']==r['source_native_post_id'] and elt.canon(obj['link'])==elt.canon(row['source_url']) and obj['date'][:10]==row['publication_date'] and obj.get('status')=='publish' and obj.get('type')=='post' and not obj.get('content',{}).get('protected')
    if r.get('native_batch_item_id'):native_ok &= obj['id']==r['native_batch_item_id']
    node=BeautifulSoup(obj.get('content',{}).get('rendered',''),'html.parser')
    for n in node.select('script,style,form,svg,.sharedaddy,.related-posts'):n.decompose()
    native_body=elt.renderer.normalise(elt.renderer.render(node));native_title=BeautifulSoup(obj.get('title',{}).get('rendered',''),'html.parser').get_text(' ',strip=True)
    native_ok &= hashlib.sha256(native_body.encode()).hexdigest()==row['body_sha256'] and native_title==r['title']
   if r['source_id']=='camden_new_journal' and raw_ok:
    native_record,native_body,native_status=native_html.parse(raw_cache[ref]['payload'],r['source_id'],row['source_url'])
    native_ok &= native_status=='confirmed_complete' and native_record['publication_date']==row['publication_date'] and native_record['title']==r['title'] and hashlib.sha256(native_body.encode()).hexdigest()==row['body_sha256']
   elif not r.get('source_native_post_id') and raw_ok:
    native_record,native_body,native_status=extract_load.parse(raw_cache[ref]['payload'],r['source_id'],r.get('raw_source_url') or row['source_url'])
    native_ok &= native_status=='confirmed_complete' and native_record['publication_date']==row['publication_date'] and native_record['title']==r['title'] and hashlib.sha256(native_body.encode()).hexdigest()==row['body_sha256']
   if not(body_ok and raw_ok and native_ok):errors.append({'article_id':aid,'body':body_ok,'raw_mapping':raw_ok,'native_ID_date_item_mapping':native_ok})
   r['TEXT_storage']='SQLite article_versions.body_text; optional sidecar reference is not a separate article';r['actual_raw_transport_target_id']=rec['target_id'] if rec else None;new.append(r)
  counts={'retained_article_rows':c.execute('SELECT count(*) FROM articles').fetchone()[0],'qualified_store_IDs':len(q),'whole_TEXT_versions':c.execute('SELECT count(*) FROM article_versions').fetchone()[0],'pending_evidence_rows':c.execute('SELECT count(*) FROM evidence').fetchone()[0],'retained_dispositions':c.execute('SELECT count(*) FROM article_dispositions').fetchone()[0]}
  old_articles=c.execute('SELECT count(*) FROM articles WHERE first_loaded_at<=?',(snap['at_utc'],)).fetchone()[0];old_versions=c.execute('SELECT count(*) FROM article_versions WHERE loaded_at<=?',(snap['at_utc'],)).fetchone()[0]
  dispositions=[dict(r) for r in c.execute('SELECT * FROM article_dispositions')];disp={r['article_id']:r['status'] for r in dispositions};versions=[dict(r) for r in c.execute('SELECT version_id,article_id,body_sha256,raw_reference,raw_sha256,body_reference,loaded_at FROM article_versions')]
  for row in c.execute('SELECT * FROM evidence WHERE loaded_at>?',(snap['at_utc'],)):
   r=json.loads(row['metadata_json']);pending.append(dict(evidence_id=row['evidence_id'],source_id=row['source_id'],source_url=row['source_url'],status=row['status'],publication_date=r.get('publication_date'),raw_reference=r.get('raw_reference'),native_post_IDs_requested=r.get('native_post_IDs_requested'),body_reference=r.get('body_reference'),loaded_at_utc=row['loaded_at']))
  integrity=c.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall();latest_ok=c.execute('SELECT count(*) FROM articles a LEFT JOIN article_versions v ON v.version_id=a.latest_version_id WHERE v.version_id IS NULL OR v.article_id<>a.article_id').fetchone()[0]==0;c.close()
 preserved &= set(frozen)<=seen
 current=newspaper_baseline+new;combined=baseline+new;fields=list(dict.fromkeys(list(baseline[0])+[k for r in new for k in r]));csv_save('ADDITIONAL_ARTICLE_REGISTER.csv',new,fields);csv_save('CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv',current,fields);csv_save('CUMULATIVE_ARTICLE_REGISTER.csv',combined,fields);csv_save('HISTORICAL_CAMPUS_PRESERVATION_REGISTER.csv',[dict(article_id=r['article_id'],source_id=r['source_id'],publication_date=r['publication_date'],version_id=r['version_id'],body_sha256=r['body_sha256'],body_reference=r.get('body_reference'),raw_reference=r.get('raw_reference'),frame_disposition='Historical campus evidence retained in place; excluded from current newspaper analysis frame; no copy to social store') for r in campus])
 csv_save('NEW_PENDING_OR_COMPONENT_REGISTER.csv',pending);csv_save('RETAINED_DISPOSITION_REGISTER.csv',dispositions);csv_save('ARTICLE_VERSION_REGISTER.csv',versions)
 ids=collections.defaultdict(set);families=collections.defaultdict(set)
 for r in current:
  for g in ['pooled',r['stratum']]:ids[g,r['publication_date'][:7]].add(r['article_id']);families[g,r['publication_date'][:7]].add(r['work_family_id'])
 coverage={};gaps=[]
 for geo in ['pooled']+elt.SCOPE['strata']:
  rows=[dict(month=m,stratum=geo,complete_native_article_IDs=len(ids[geo,m]),complete_independent_articles=len(families[geo,m]),months_at_minimum_coverage=len(families[geo,m])>=2,additional_articles_required=max(0,2-len(families[geo,m])),partial_publication_month=m=='2026-09',collection_frame='newspaper_current_noncampus') for m in MONTHS]
  csv_save('coverage/MONTHLY_'+geo.replace('/','_').replace(' ','_')+'.csv',rows);gaps.extend(r for r in rows if not r['months_at_minimum_coverage']);coverage[geo]={'months_at_minimum_coverage':sum(r['months_at_minimum_coverage'] for r in rows),'one_article_months':sum(r['complete_independent_articles']==1 for r in rows),'zero_article_months':sum(r['complete_independent_articles']==0 for r in rows),'article_count_distribution':dict(collections.Counter(r['complete_independent_articles'] for r in rows))}
 csv_save('RESIDUAL_MONTHS.csv',gaps)
 import broaden,production
 profiles={p['source_id']:p for p in broaden.profiles()};parents={sid:p.get('parent_family_id',sid) for sid,p in profiles.items()};group=collections.defaultdict(list)
 for r in current:group[r['publication_date'][:7],r['stratum'],r['source_id'],r.get('genre') or 'unrecorded',parents.get(r['source_id'],r['source_id'])].append(r)
 csv_save('MONTH_SOURCE_GENRE_PARENT_DISTRIBUTION.csv',[dict(month=m,stratum=g,source_id=s,recorded_genre=genre,acquisition_parent_family_id=parent,native_article_IDs=len({r['article_id'] for r in rs}),known_independent_article_work_families=len({r['work_family_id'] for r in rs}),canonical_URLs=len({elt.canon(r['source_url']) for r in rs}),genre_basis='Recorded native/source metadata only; unrecorded stays unrecorded') for (m,g,s,genre,parent),rs in sorted(group.items())])
 yearly=collections.Counter((r['source_id'],r['publication_date'][:4]) for r in current);csv_save('ACQUIRED_SOURCE_YEAR_INVENTORY.csv',[dict(source_id=s,year=y,complete_native_article_IDs=n,archive_population='Unknown; acquired originals only') for (s,y),n in sorted(yearly.items())])
 csv_save('SOURCE_PARENT_IDENTITY_REGISTER.csv',[dict(source_id=sid,acquisition_parent_family_id=parents.get(sid,sid),parent_level='Publisher/source/interface parent; independent article work family separate') for sid in sorted({r['source_id'] for r in current})])
 quality=[];aliases=[];digest_groups=collections.defaultdict(list)
 for r in current:
  provenance=str(r.get('provenance') or '');clause=provenance.split(';')[0].lower();archival=r.get('historical_original_print') in [True,1,'True','true','1'] or r.get('raw_encoding')=='original_pdf' or 'archival' in clause
  directness='archival_reproduction' if archival else ('mixed' if 'mixed' in clause else ('indirect_secondary' if 'indirect' in clause or 'secondary' in clause else ('direct_original_publisher_representation' if 'direct' in clause else 'unresolved')))
  quality.append(dict(article_id=r['article_id'],source_id=r['source_id'],source_url=r['source_url'],publication_date=r['publication_date'],retrieved_at_utc=r.get('retrieved_at_utc') or 'unrecorded',content_version_time=r.get('content_version_time') or 'unrecorded',directness_relative_to_recorded_utterance=directness,identity_date_content_mapping='Accepted complete print mapping' if archival else ('Native public post ID/date/permalink/full content mapping' if r.get('source_native_post_id') else 'Publisher original title/date/whole-body mapping'),pending_checks='Historical body equivalence, all quotation/underlying-work origins and claim truth not universally established',conflicting_provenance='Known exact-body copy relation retained' if r.get('known_exact_body_copy_of') else 'No recorded conflict; universal absence not established',access_limits=profiles.get(r['source_id'],{}).get('retention_limit','Inherited accepted source-specific limits and stops remain; no open-license assertion'),raw_reference=r.get('raw_reference')))
  vals=r.get('url_aliases') or []
  if isinstance(vals,str):
   try:vals=json.loads(vals)
   except ValueError:
    try:vals=ast.literal_eval(vals)
    except (ValueError,SyntaxError):vals=[]
  if not isinstance(vals,list) or not all(isinstance(u,str) for u in vals):vals=[]
  for u in sorted(set(vals+[r['source_url']]+([r['raw_source_url']] if r.get('raw_source_url') else []))):aliases.append(dict(article_id=r['article_id'],source_id=r['source_id'],canonical_source_url=r['source_url'],alias_url=u,version_id=r['version_id']))
  digest_groups[r['body_sha256']].append(r)
 csv_save('PROVENANCE_AND_VERIFICATION_REGISTER.csv',quality);csv_save('ARTICLE_URL_ALIAS_REGISTER.csv',aliases)
 overlaps=[dict(body_sha256=h,article_id=r['article_id'],source_id=r['source_id'],source_url=r['source_url'],publication_date=r['publication_date'],work_family_id=r['work_family_id'],group_native_IDs=len(rs),relation='Exact normalized TEXT overlap candidate; native originals retained and syndication/independence may remain unresolved') for h,rs in digest_groups.items() if len(rs)>1 for r in rs];csv_save('EXACT_BODY_OVERLAP_REVIEW_REGISTER.csv',overlaps)
 csv_save('RAW_OBJECT_MANIFEST.csv',[{k:r.get(k) for k in ['target_id','source_id','purpose','status','raw_reference','raw_sha256','raw_bytes','raw_encoding','stored_sha256','stored_bytes','partial','finished_at_utc']} for r in requests if r.get('raw_reference')]);csv_save('NEW_PENDING_TRANSPORT.csv',[dict(target_id=r['target_id'],source_id=r['source_id'],source_url=r['url'],status=r['status'],receipt_reference='receipts/'+r['target_id']+'.json') for r in requests if r['status']!='saved'])
 access_exceptions=json.loads((elt.OWN/'METADATA_ACCESS_EXCEPTION_REGISTER.json').read_text());csv_save('METADATA_ACCESS_EXCEPTION_REGISTER.csv',access_exceptions['records'])
 state=elt.state();attempts={g:dict(cumulative_article_transport_targets=state['strata'][g]['article'],additional_native_units_requested_in_batches=state.get('additional_batch_native_units_requested',{}).get(g,0),effective_cumulative_discovery_targets=elt.effective_count(state,g,'discovery'),article_target_cap=None,discovery_ceiling=2000) for g in elt.SCOPE['strata']}
 csv_save('HOST_STOP_REGISTER.csv',[dict(host=h,stop=json.dumps(v,ensure_ascii=False),scope='Inherited or actual observed host stop; no bypass retry') for h,v in state['access_stops'].items()])
 batch_status=json.loads((elt.OWN/'NATIVE_BATCH_UNIT_STATUS.json').read_text()) if (elt.OWN/'NATIVE_BATCH_UNIT_STATUS.json').exists() else {};csv_save('NATIVE_BATCH_UNIT_REGISTER.csv',[dict(article_id=aid,**v) for aid,v in batch_status.items()]);csv_save('NATIVE_BATCH_TRANSPORT_REGISTER.csv',lines(elt.OWN/'NATIVE_BATCH_TRANSPORT_EVIDENCE.jsonl'))
 broadstate=json.loads((elt.OWN/'BROADEN_CURSORS.json').read_text());frontier=[]
 for g,sids in production.SOURCES.items():
  for sid in list(sids)+[p['source_id'] for p in profiles.values() if p['stratum']==g and p['source_id'] not in sids]:
   ts=production.targets(sid);eligible=production.eligible(ts,production.KNOWN,set(state['targets']),{},g,'production');v=broadstate.get(sid,{})
   frontier.append(dict(source_id=sid,stratum=g,frontier_state=v.get('stage','retained_native_opportunities'),retained_native_target_metadata=len({elt.canon(t['url']) for t in ts}),eligible_unattempted_native_targets=len({elt.canon(t['url']) for t in eligible}),attempted_metadata_pages=v.get('attempted_pages',0),observed_native_total_posts=v.get('observed_native_total_posts'),observed_native_total_pages=v.get('observed_native_total_pages'),blocked_reason=v.get('blocked_reason'),native_inventory_population='Observed public posts/links only; neither all qualified articles nor complete historical archive',references='NATIVE_CURSORS.json; BROADEN_CURSORS.json; own and frozen metadata queues; no body queue copies'))
 for name in ['BROADER_CANDIDATE_DISPOSITIONS.json','NEW_BROADER_CANDIDATE_DISPOSITIONS.json']:
  p=elt.OWN/name
  if p.exists():
   o=json.loads(p.read_text());rs=o.get('records',o if isinstance(o,list) else []) if isinstance(o,dict) else o
   frontier.extend(rs)
 csv_save('SOURCE_FRONTIER_REGISTER.csv',frontier)
 opp=collections.Counter((r['stratum'],r['planned_lane']) for r in lines(elt.OWN/'OPPORTUNITY_LOG.jsonl'));elt.preparation_save('OPPORTUNITY_SUMMARY.json',dict(at_utc=elt.utc(),planned_production_fraction=.65,planned_broader_fraction=.25,planned_recovery_fraction=.10,counts=[dict(stratum=g,production=opp[g,'production'],broader=opp[g,'broader'],recovery=opp[g,'recovery']) for g in elt.SCOPE['strata']],scope='Opportunity shares only; not article output quotas, inclusion weights or equal observed yields'))
 resource=elt.resource();start=json.loads((elt.OWN/'SUCCESSOR_START_RECEIPT.json').read_text());seal=all(digest(elt.REPO/p)==h for p,h in start['frozen_predecessor_file_hashes'].items());ledger=json.loads((elt.OWN/'PARENT_FAMILY_LEDGER.json').read_text())
 checks=dict(accepted_start_and_extension_checks=all(json.loads((elt.OWN/f).read_text())['all_passed'] for f in ['CHANGED_CODE_CHECK.json','BATCH_HTML_EXTENSION_CHECK.json','HTML_FRONTIER_AND_BATCH_RECOVERY_CHECK.json','METADATA_ROBOTS_GUARD_CHECK.json']),SQLite_quick_and_foreign_key_check=integrity,latest_version_mapping=latest_ok,predecessor_article_rows_preserved=old_articles==snap['baseline_article_rows'],predecessor_versions_preserved=old_versions==snap['baseline_versions'],predecessor_qualified_ID_date_body_hash_metadata_preserved=preserved,predecessor_dispositions_preserved=len(old_dispositions)==snap['baseline_dispositions'] and all(disp.get(a)==s for a,s in old_dispositions.items()),predecessor_frozen_input_hashes_preserved=seal,new_TEXT_identity_date_raw_and_batch_item_mapping=not errors,campus_IDs_preserved_but_no_new_campus_collection=len(campus)==9249 and all(r['source_id'] not in elt.EXCLUDED for r in new),six_465_month_current_newspaper_ledgers=len(coverage)==6 and len(MONTHS)==465,fixed_publication_cutoff=elt.SCOPE['publication_interval']==['1988-01-01','2026-09-21'],discovery_and_parent_ceilings=all(r['effective_cumulative_discovery_targets']<=2000 for r in attempts.values()) and all(len(set(v))<=4 for v in ledger['families'].values()),native_hops_at_most_four=all(n<=4 for n in state.get('native_http_hops',{}).values()),no_in_progress_transport=all(v!='in_progress' for v in state['targets'].values()),inherited_host_stops_preserved='www.odt.co.nz' in state['access_stops'] and 'assets.indailysa.com.au' in state['access_stops'],no_semantic_or_length_exclusion=all(r.get('semantic_labels_executed') is False and r.get('length_filter_used') is False for r in new),no_Alice_article_qualification=not any(r['source_id']=='alice_springs_news' for r in new),metadata_access_exceptions_explicit=access_exceptions['qualified_newspaper_articles']==0,media_cap=resource['cumulative_bytes']<15000000000,physical_floor_and_recovery_preserved=resource['physical_headroom']>=0,writer_exit_verified=True)
 summary=dict(at_utc=elt.utc(),status='bounded_open_newspaper_production_delivered',publication_interval=elt.SCOPE['publication_interval'],deadline_unchanged=elt.SCOPE['hard_deadline_at_utc'],collection_close=close,baseline_complete_IDs=12334,baseline_current_newspaper_IDs=3085,historical_campus_IDs_preserved=9249,baseline_pooled_minimum_months=262,additional_qualified_IDs=len(new),additional_source_mix=dict(collections.Counter(r['source_id'] for r in new)),current_newspaper_complete_IDs=len(current),cumulative_selected_complete_IDs=len(combined),whole_TEXT_database_counts=counts,coverage=coverage,cumulative_attempt_counts=attempts,new_distinct_transport_target_receipts=len(requests),new_HTTP_hops=sum(len(r.get('hops',[])) for r in requests),new_transport_statuses=dict(collections.Counter(r['status'] for r in requests)),new_pending_or_component_records=len(pending),pre_guard_source_metadata_access_exceptions=len(access_exceptions['records']),source_frontier=frontier,resource_at_delivery=resource,checks=checks,all_changed_tranche_checks_passed=all(checks.values()),mapping_errors=errors,old_body_raw_hash_sweep=False,final_database_hash_once=True,fear_or_topic_labels_executed=False,verification_scope='New body hash/date/identity/receipt/batch-item mapping once; predecessor metadata preservation; one final store check. Historical rendition equivalence and claim truth remain unproved.')
 elt.preparation_save('DELIVERY_SUMMARY.json',summary)
 table='\n'.join('| '+g+' | '+str(v['months_at_minimum_coverage'])+' | '+str(v['one_article_months'])+' | '+str(v['zero_article_months'])+' |' for g,v in coverage.items())
 report=f'''# Newspaper continuing production — 9 October 2026

This same-owner release added **{len(new):,} qualified complete newspaper article IDs**, raising the current newspaper frame from **3,085 to {len(current):,}**. Pooled months at the two-known-work-family coverage floor rose from **262 to {coverage['pooled']['months_at_minimum_coverage']} /465**. The **9,249 historical campus IDs** remain unchanged in the continuing store, excluded from this current newspaper frame and never copied into the social store. Total historically retained qualified store IDs: **{len(combined):,}**. Frozen earlier mixed-frame reports are preserved, and their counts are not the current newspaper baseline.

Collection closed for **{close['reason']}**. Actual writer exit and the single-writer mutex were verified. The fixed prospective end remained **2026-10-09T06:41:51.640855Z / 9 October 16:41:51 Brisbane**. No article-target quota or output milestone stopped production. Two articles per month remained a coverage floor. The controlled implementation restarts preserved the original bindings, state and deadline; it did not create a new window or reset counters.

| Stratum | Months at floor | One-article months | Zero-confirmed months |
| --- | ---: | ---: | ---: |
{table}

Publication eligibility remains **1988-01-01 through 2026-09-21**, with partial September. The delivery snapshot is {summary['at_utc']}. Publication, individual retrieval/extraction, content-version and report times remain separate. Later archive retrieval does not prove historical body equivalence or end-of-day completeness. Zero-confirmed months are observed acquisition gaps, not zero discourse. The source/year and month/source/genre/parent distributions retain legitimate volume differences; no peaks were deleted, flattened or pre-attributed to climate events.

The ELT pipeline retained entire native articles after structural cleanup and immediately committed their TEXT, persistent identity and provenance. Documented public WordPress include batches transport several distinct native posts; each post retains its own ID, date, permalink, full body, raw-item reference and version. Batch containers are neither articles nor independent parents. Transport-request counters and distinct requested native batch participants are separately reported. Cambridge/other article-page dates were never inferred from index snapshots, URL lastmod or founding dates. Camden's native HTML uses its unique displayed publication date and original title/content container. Public access, source use, retention limits and redistribution are separate: no open full-text license is asserted, paid/private routes are excluded, and the recorded declared research-agent robots rule does not erase separately named crawler prohibitions.

Continuing noncampus production, broader newspaper preparation and targeted historical recovery shared one pipeline. Planned opportunity shares were **65% /25% /10%**, not output quotas, source weights or equal observed counts. Source parent families, source-specific use restrictions, native inventory observations, actual HTTP stops, unattempted queues and observed frontier ends accompany this report. Consuming an observed public frontier does not certify an entire historical archive. No broadcaster, general commentary network or campus source was renamed as a current newspaper merely to balance geography.

Structural pending cases preserve their original raw evidence: inconsistent date fields, missing or nonunique body boundaries, protected responses, image/heading/table-only units, embedded-only editions and failed/partial transfers remain explicit. Short prose and prose with supporting media remain eligible without length, climate, emotion or fear thresholds. Known exact-body copies remain retained and visible through work-family and overlap registers; native identity does not prove all syndication independence. Directness is relative to the recorded newspaper utterance, while quotation origins and claim truth remain separate. The provenance register distinguishes direct original, archival reproduction, indirect/secondary, mixed and unresolved evidence, and separately reports verified mappings, pending checks, conflicts and access limits.

Alice's saved robots rule denies the actual declared research collector, while separately permitting named archival/search/GPT bots. The collector identity was not changed. A metadata-job defect allowed {len(access_exceptions['records'])} source documents after the robots receipt was saved; these bytes remain explicit in the metadata-access exception register, with no Alice article qualification or TEXT Load. The corrected guard blocks later source documents before HTTP. This exception is separate from article mapping and durability checks.

The changed-tranche closeout passed **{all(checks.values())}**, with **{len(errors)} mapping errors**. One post-exit SQLite quick/foreign-key/latest-version check and the new TEXT/raw-item mapping checks were performed. All {snap['baseline_article_rows']:,} predecessor article rows, {snap['baseline_versions']:,} versions, 12,334 previously qualified IDs and 60 dispositions were preserved. No old raw/body hash sweep, full-body queue copy or database copy ran. The final database digest records this append-store snapshot; it is not a prohibition on future separately authorized appends.

Cumulative retained media bytes: **{resource['cumulative_bytes']:,} /15,000,000,000** decimal. The protected **15 GiB physical floor** and **48 MiB recovery rule** remained in force. Live leases and actual complete-operation footprints were reread under the shared lock. The inherited **36 PDF issues /184,103,804 raw bytes** remain charged and no new PDF allowance was opened. The ODT/Allied, InDaily asset and later actual host stops remain preserved. The separate owner's lease was accounted for without reading its store. No evidence deletion, floor waiver, government collection or sealed evaluator access occurred. The Alice metadata access exception is reported separately above.

The accompanying tables include the additional and current newspaper registers, historical campus preservation references, total historical store metadata, versions, URL aliases, raw and batch manifests, pending dispositions, six full-calendar monthly ledgers, residual months, distribution/provenance/parent/overlap registers and source frontier limits. Agent dispatch state, live execution controls, queues and individual receipts stay local. Shared logs, coordinator controls and publication on main remain coordinator-owned; this worker did not edit them, launch a new chat/subagent, message anyone or create a successor/automation.

| Evidence level | Acquisition status |
| --- | --- |
| 1. Dated source presence and readable original text | Complete native articles and explicit structural/access limits reported; historical rendition equivalence remains unknown. |
| 2. Climate/warming relevance and similarity | Deferred until the analysis stage under a defined unit and source frame. |
| 3. Affect, risk, future-harm or responsibility association | Deferred until validation; these associations are not automatically fear. |
| 4. Fear-specific interpretation | Deferred; traceable passages require speaker/holder, target, time horizon, quotation and negation checks, and supported measurement. |

Coverage, query hits and collection volume do not establish emotion prevalence or comparable three-role time series. Neutral and routine discourse remains retained; source inclusion and acquisition success never depend on explicit fear.
'''
 report=report.replace('Cambridge/other article-page dates','Publisher article-page dates');p=elt.OWN/'DELIVERY_REPORT.md'
 with elt.LOCK.open('a+b') as shared:
  fcntl.flock(shared,fcntl.LOCK_EX);elt.preflight(len(report.encode())*2+65536);p.write_text(report)
 elt.preparation_save('WORKER_COMPLETION.json',dict(at_utc=elt.utc(),status=summary['status'],additional_qualified_IDs=len(new),current_newspaper_IDs=len(current),historical_campus_IDs_preserved=9249,no_active_background_writer=True,all_changed_tranche_checks_passed=all(checks.values())))
 elt.preparation_save('CURRENT_STATUS.json',dict(at_utc=elt.utc(),status='collection_closed_and_changed_tranche_delivered',new_qualified_newspaper_IDs=len(new),current_newspaper_IDs=len(current),historical_campus_IDs_preserved=9249,total_store_qualified_IDs=len(combined),coverage=coverage,collection_close=close,all_changed_tranche_checks_passed=all(checks.values()),final_summary_reference='DELIVERY_SUMMARY.json',final_report_reference='DELIVERY_REPORT.md'))
 released_code=set(start['implementation_hashes'])|{'deliver.py','close_receipt.py'}
 released_metadata={'DELIVERY_SUMMARY.json','OPPORTUNITY_SUMMARY.json','BROADEN_PROFILES.json','BROADER_CANDIDATE_DISPOSITIONS.json','NEW_BROADER_CANDIDATE_DISPOSITIONS.json'}
 paths=[p for p in elt.OWN.rglob('*') if p.is_file() and ('/bindings/' not in str(p)) and (p.suffix=='.csv' or p.name in released_code or p.name in released_metadata or p.name=='DELIVERY_REPORT.md')]
 with elt.LOCK.open('a+b') as shared:
  fcntl.flock(shared,fcntl.LOCK_EX);elt.preflight(1024*1024)
  hashes={str(p.relative_to(elt.OWN)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in paths};dbkey=str(elt.DB.relative_to(elt.REPO));hashes[dbkey]=dict(sha256=digest(elt.DB),bytes=elt.DB.stat().st_size)
 old_db=json.loads((elt.PREDECESSOR/'DELIVERY_FILE_RECEIPTS.json').read_text())['files'][dbkey]
 elt.preparation_save('DELIVERY_FILE_RECEIPTS.json',dict(at_utc=elt.utc(),files=hashes,raw_body_hash_sweep=False,final_database_hashed_once=True,accepted_pre_append_database_receipt=old_db,publication_boundary='Final collection code/tables/manifests/research summary only. Owner dispatch, live controls, queues, interim checkpoints and individual receipts remain local with preserved bytes/bindings.'));print(json.dumps({k:summary[k] for k in ['status','additional_qualified_IDs','current_newspaper_complete_IDs','cumulative_selected_complete_IDs','all_changed_tranche_checks_passed']}))
if __name__=='__main__':main()
