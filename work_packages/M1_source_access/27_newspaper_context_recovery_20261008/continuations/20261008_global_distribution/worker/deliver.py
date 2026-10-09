"""One bounded changed-tranche closeout, metadata distribution and source-frontier export."""
import ast,collections,csv,fcntl,io,json,os,re,sqlite3
from pathlib import Path
import elt
MONTHS=[f'{y:04d}-{m:02d}' for y in range(1988,2027) for m in range(1,13) if f'{y:04d}-{m:02d}'<='2026-09']
def lines(p):return [json.loads(x) for x in p.read_text().split('\n') if x] if p.exists() else []
def write_csv(name,rows,fields=None):
 fields=fields or list(dict.fromkeys(k for r in rows for k in r)) or ['empty_register']
 out=io.StringIO();w=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows);b=out.getvalue().encode()
 elt.preflight(len(b)*2+65536);p=elt.OWN/name;p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.pending');t.write_bytes(b);t.replace(p)
def digest(p):
 h=elt.hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 close=json.loads((elt.OWN/'COLLECTION_CLOSE_RECEIPT.json').read_text());assert close['writer_exit_observed'] and close['no_active_writer']
 try:os.kill(close['last_writer_pid'],0)
 except ProcessLookupError:pass
 else:raise RuntimeError('Writer process still exists')
 with (elt.REPO/elt.SCOPE['newspaper_writer_mutex']).open('a+b') as owner:
  fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB);return deliver(close)
def deliver(close):
 elt.preflight(32*1024**2);snap=json.loads((elt.OWN/'INPUT_SNAPSHOT.json').read_text());accepted=json.loads((elt.PREDECESSOR/'DELIVERY_FILE_RECEIPTS.json').read_text());dbkey=str(elt.DB.relative_to(elt.REPO));old_db=accepted['files'][dbkey]
 baseline=list(csv.DictReader((elt.PREDECESSOR/'CUMULATIVE_ARTICLE_REGISTER.csv').open()));frozen={r['article_id']:r for r in baseline};assert len(frozen)==snap['baseline_complete_IDs']
 old_dispositions={r['article_id']:r['disposition'] for r in csv.DictReader((elt.PREVIOUS/'ARTICLE_REGISTER.csv').open()) if r['disposition']!='confirmed_complete'}
 for r in json.loads((elt.PREDECESSOR/'NEW_DATE_CONFLICT_RECLASSIFICATIONS.json').read_text())['records']:old_dispositions[r['article_id']]='pending_issue_article_date_conflict'
 history=lines(elt.OWN/'REQUESTS.jsonl');requests=list({r['target_id']:r for r in history}.values());receipt_by_raw={r['raw_reference']:r for r in requests if r.get('raw_reference')}
 print_base=elt.REPO/'work_packages/M1_source_access/23_newspaper_acquisition_and_transition_20261005/transition_research/acquisition_followthrough_20261005';accepted_print={str((print_base/r['raw_path']).relative_to(elt.REPO)):r for r in lines(print_base/'REQUESTS.jsonl') if r.get('status')=='saved' and r.get('raw_path')}
 new=[];pending=[];preserved=True;body_ok=True;raw_ok=True;print_ok=True;errors=[];native_date_ok=True
 with elt.LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);c=elt.connect();c.row_factory=sqlite3.Row
  q=c.execute('SELECT a.*,CASE WHEN v.loaded_at>? THEN v.provenance_json ELSE NULL END AS provenance_json,v.body_reference,v.raw_reference,v.body_sha256,CASE WHEN v.loaded_at>? THEN length(v.body_text) END AS chars,CASE WHEN v.loaded_at>? THEN length(CAST(v.body_text AS BLOB)) END AS bytes FROM articles a JOIN article_versions v ON v.version_id=a.latest_version_id LEFT JOIN article_dispositions d ON d.article_id=a.article_id WHERE d.article_id IS NULL',(snap['at_utc'],)*3).fetchall()
  seen=set()
  for row in q:
   aid=row['article_id'];seen.add(aid)
   if aid in frozen:
    old=frozen[aid];preserved &= row['publication_date']==old['publication_date'] and row['source_url']==old['source_url'] and row['body_sha256']==old['body_sha256'] and row['work_family_id']==old['work_family_id'] and row['latest_version_id']==old['version_id'];continue
   r=json.loads(row['provenance_json']);r.update(article_id=aid,publication_date=row['publication_date'],source_url=row['source_url'],stratum=row['stratum'],work_family_id=row['work_family_id'],version_id=row['latest_version_id'],body_sha256=row['body_sha256'],disposition='confirmed_complete',whole_TEXT_characters=row['chars'],whole_TEXT_bytes=row['bytes'])
   bp=elt.REPO/row['body_reference'] if row['body_reference'] else None;rp=elt.REPO/row['raw_reference'] if row['raw_reference'] else None
   bok=bool(bp and bp.exists() and bp.stat().st_size==row['bytes'] and row['chars']>0 and elt.eligible(row['publication_date']) and row['source_url'].startswith('https://'));body_ok &= bok
   if r.get('raw_encoding')=='original_pdf':
    rec=accepted_print.get(row['raw_reference']);mp=elt.REPO/r['mapping_reference'];mapping=json.loads(mp.read_text()) if mp.exists() else {};rok=bool(rec and not rec.get('partial') and rp and rp.exists() and rp.stat().st_size==rec['raw_bytes'] and rec['raw_sha256']==r['raw_sha256'] and mapping.get('complete_article_visually_traced') and mapping.get('date_visually_confirmed') and mapping.get('publication_date')==row['publication_date']);print_ok &= rok;r['actual_raw_transport_target_id']='inherited_complete_original:'+r['request_id']
   else:
    rec=receipt_by_raw.get(row['raw_reference'])
    if rec is None and r.get('request_id'):
     try:rec=elt._receipt(r['request_id'])
     except ValueError:pass
    rok=bool(rec and rec['status']=='saved' and rp and rp.exists() and rp.stat().st_size==rec.get('stored_bytes') and rec.get('raw_encoding')=='gzip' and rec.get('raw_sha256')==r.get('raw_sha256') and rec.get('stored_sha256')==r.get('stored_sha256') and rec.get('raw_bytes',0)<=(elt.SCOPE['historical_pdf_raw_cap_bytes'] if r.get('historical_original_print') and rec.get('target',{}).get('extra',{}).get('kind')=='historical_pdf' else elt.SCOPE['default_raw_object_cap_bytes']));r['actual_raw_transport_target_id']=rec['target_id'] if rec else None
   if r.get('historical_original_print'):
    mp=elt.REPO/r['mapping_reference'];mapping=json.loads(mp.read_text()) if mp.exists() else {};pok=bool(mapping.get('complete_article_visually_traced') and mapping.get('date_visually_confirmed') and mapping.get('publication_date')==row['publication_date']);print_ok &= pok;rok &= pok
   if r.get('source_native_post_id') and r['source_id'] not in ['beaver','mancunion']:
    nok=aid==r['source_id']+':post:'+str(r['source_native_post_id']);native_date_ok &= nok
    if not nok:errors.append({'article_id':aid,'native_ID_mapping':False})
   raw_ok &= rok
   if not(bok and rok):errors.append({'article_id':aid,'body_mapping':bok,'raw_receipt_mapping':rok})
   new.append(r)
  preserved &= set(frozen)<=seen
  counts=dict(article_rows_retained=c.execute('SELECT count(*) FROM articles').fetchone()[0],currently_qualified_article_rows=len(q),whole_text_versions=c.execute('SELECT count(*) FROM article_versions').fetchone()[0],separate_pending_or_component_records=c.execute('SELECT count(*) FROM evidence').fetchone()[0],reclassified_retained_article_rows=c.execute('SELECT count(*) FROM article_dispositions').fetchone()[0],baseline_metadata_rows=c.execute('SELECT count(*) FROM baseline').fetchone()[0])
  old_articles=c.execute('SELECT count(*) FROM articles WHERE first_loaded_at<=?',(snap['at_utc'],)).fetchone()[0];old_versions=c.execute('SELECT count(*) FROM article_versions WHERE loaded_at<=?',(snap['at_utc'],)).fetchone()[0]
  disp={r['article_id']:r['status'] for r in c.execute('SELECT article_id,status FROM article_dispositions')}
  dispositions=[dict(r) for r in c.execute('SELECT * FROM article_dispositions')]
  versions=[dict(r) for r in c.execute('SELECT version_id,article_id,body_sha256,raw_reference,raw_sha256,body_reference,loaded_at FROM article_versions')]
  for row in c.execute('SELECT * FROM evidence WHERE loaded_at>?',(snap['at_utc'],)):
   r=json.loads(row['metadata_json']);pending.append(dict(evidence_id=row['evidence_id'],source_id=row['source_id'],source_url=row['source_url'],status=row['status'],publication_date=r.get('publication_date'),raw_reference=r.get('raw_reference'),body_reference=r.get('body_reference'),loaded_at_utc=row['loaded_at']))
  integrity=c.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall();latest_ok=c.execute('SELECT count(*) FROM articles a LEFT JOIN article_versions v ON v.version_id=a.latest_version_id WHERE v.version_id IS NULL OR v.article_id<>a.article_id').fetchone()[0]==0;c.close()
 combined=baseline+new;fields=list(dict.fromkeys(list(baseline[0])+[k for r in new for k in r]));write_csv('ADDITIONAL_ARTICLE_REGISTER.csv',new,fields);write_csv('CUMULATIVE_ARTICLE_REGISTER.csv',combined,fields)
 write_csv('NEW_PENDING_OR_COMPONENT_REGISTER.csv',pending,['evidence_id','source_id','source_url','status','publication_date','raw_reference','body_reference','loaded_at_utc']);write_csv('RETAINED_DISPOSITION_REGISTER.csv',dispositions,['article_id','status','reason','updated_at_utc']);write_csv('ARTICLE_VERSION_REGISTER.csv',versions,['version_id','article_id','body_sha256','raw_reference','raw_sha256','body_reference','loaded_at'])
 reclassified=json.loads((elt.OWN/'NEW_DATE_CONFLICT_RECLASSIFICATIONS.json').read_text())['records'] if (elt.OWN/'NEW_DATE_CONFLICT_RECLASSIFICATIONS.json').exists() else []
 write_csv('NEW_RECLASSIFIED_DATE_CONFLICT_REGISTER.csv',reclassified,['article_id','source_url','article_page_publication_date','native_issue_month','request_id','body_reference','action'])
 structural=json.loads((elt.OWN/'NEW_STRUCTURAL_UNIT_RECLASSIFICATIONS.json').read_text())['records'] if (elt.OWN/'NEW_STRUCTURAL_UNIT_RECLASSIFICATIONS.json').exists() else []
 write_csv('NEW_RECLASSIFIED_NATIVE_UNIT_REGISTER.csv',structural,['article_id','source_id','source_url','publication_date','status','body_reference','raw_reference','request_id','action'])
 families=collections.defaultdict(set);ids=collections.defaultdict(set)
 for r in combined:
  for g in ['pooled',r['stratum']]:families[g,r['publication_date'][:7]].add(r['work_family_id']);ids[g,r['publication_date'][:7]].add(r['article_id'])
 coverage={};gaps=[];lf=['month','stratum','complete_native_article_IDs','complete_independent_articles','months_at_minimum_coverage','additional_articles_required','partial_publication_month']
 for geo in ['pooled']+elt.SCOPE['strata']:
  rows=[dict(month=m,stratum=geo,complete_native_article_IDs=len(ids[geo,m]),complete_independent_articles=len(families[geo,m]),months_at_minimum_coverage=len(families[geo,m])>=2,additional_articles_required=max(0,2-len(families[geo,m])),partial_publication_month=m=='2026-09') for m in MONTHS];gaps.extend(r for r in rows if not r['months_at_minimum_coverage']);write_csv('coverage/MONTHLY_'+geo.replace('/','_').replace(' ','_')+'.csv',rows,lf)
  coverage[geo]=dict(months_at_minimum_coverage=sum(r['months_at_minimum_coverage'] for r in rows),one_article_months=sum(r['complete_independent_articles']==1 for r in rows),zero_article_months=sum(r['complete_independent_articles']==0 for r in rows),article_count_distribution=dict(collections.Counter(r['complete_independent_articles'] for r in rows)))
 write_csv('RESIDUAL_MONTHS.csv',gaps,lf)
 inventory=collections.Counter((r['source_id'],r['publication_date'][:4]) for r in combined);write_csv('ACQUIRED_SOURCE_YEAR_INVENTORY.csv',[dict(source_id=s,year=y,complete_native_article_IDs=n,archive_population='Unknown; acquired originals only') for (s,y),n in sorted(inventory.items())])
 group=collections.defaultdict(list)
 for r in combined:group[(r['publication_date'][:7],r['stratum'],r['source_id'],r.get('genre') or 'unrecorded')].append(r)
 write_csv('MONTH_SOURCE_GENRE_DISTRIBUTION.csv',[dict(month=m,stratum=g,source_id=s,recorded_genre=genre,native_article_IDs=len({r['article_id'] for r in rs}),known_work_families=len({r['work_family_id'] for r in rs}),canonical_URLs=len({elt.canon(r['source_url']) for r in rs}),genre_basis='Only recorded native/source metadata; no inferred topic or affect') for (m,g,s,genre),rs in sorted(group.items())])
 aliases=[]
 for r in combined:
  vals=r.get('url_aliases') or []
  if isinstance(vals,str):
   try:vals=json.loads(vals)
   except ValueError:
    try:vals=ast.literal_eval(vals)
    except (ValueError,SyntaxError):vals=[]
   if not isinstance(vals,list) or not all(isinstance(v,str) for v in vals):vals=[]
  if r.get('raw_source_url'):vals=list(vals)+[r['raw_source_url']]
  for u in sorted(set(vals+[r['source_url']])):aliases.append(dict(article_id=r['article_id'],source_id=r['source_id'],canonical_source_url=r['source_url'],alias_url=u,version_id=r['version_id']))
 write_csv('ARTICLE_URL_ALIAS_REGISTER.csv',aliases,['article_id','source_id','canonical_source_url','alias_url','version_id'])
 digest_groups=collections.defaultdict(list)
 for r in combined:digest_groups[r['body_sha256']].append(r)
 overlaps=[dict(body_sha256=h,article_id=r['article_id'],source_id=r['source_id'],source_url=r['source_url'],publication_date=r['publication_date'],work_family_id=r['work_family_id'],group_native_IDs=len(rs),relation='Exact normalized TEXT overlap candidate; native records retained, common origin/independence may remain unresolved') for h,rs in digest_groups.items() if len(rs)>1 for r in rs]
 write_csv('EXACT_BODY_OVERLAP_REVIEW_REGISTER.csv',overlaps,['body_sha256','article_id','source_id','source_url','publication_date','work_family_id','group_native_IDs','relation'])
 write_csv('RAW_OBJECT_MANIFEST.csv',[{k:r.get(k) for k in ['target_id','source_id','purpose','status','raw_reference','raw_sha256','raw_bytes','raw_encoding','stored_sha256','stored_bytes','partial','finished_at_utc']} for r in requests if r.get('raw_reference')])
 write_csv('NEW_PENDING_TRANSPORT.csv',[dict(target_id=r['target_id'],source_id=r['source_id'],source_url=r['url'],status=r['status'],receipt_reference='receipts/'+r['target_id']+'.json') for r in requests if r['status']!='saved'],['target_id','source_id','source_url','status','receipt_reference'])
 import broaden
 new_profiles={p['source_id']:p for p in broaden.profiles()}
 quality=[]
 for r in combined:
  provenance=str(r.get('provenance') or '')
  archival=bool(r.get('historical_original_print') in [True,1,'True','true','1'] or r.get('raw_encoding')=='original_pdf' or 'archival' in provenance.lower())
  first_clause=provenance.split(';')[0].lower()
  directness='archival_reproduction' if archival else ('mixed' if re.search(r'\bmixed\b',first_clause) else ('indirect_secondary' if re.search(r'\b(?:indirect|secondary)\b',first_clause) else ('direct_original_publisher_representation' if re.search(r'\bdirect\b',first_clause) else 'unresolved')))
  quality.append(dict(article_id=r['article_id'],source_id=r['source_id'],source_url=r['source_url'],publication_date=r['publication_date'],content_version_time=r.get('content_version_time') or 'unrecorded',retrieved_at_utc=r.get('retrieved_at_utc') or 'unrecorded',directness_relative_to_recorded_newspaper_utterance=directness,identity_date_content_mapping='Accepted printed article mapping' if archival else ('Matched native public post ID/date/permalink/full content representation' if r.get('source_native_post_id') else 'Accepted publisher article-page title/date/whole-body mapping'),pending_checks='Historical body equivalence unknown; independently quoted/wire/underlying-work origin and claim truth not established universally',conflicting_provenance='Known exact-body relationship retained' if r.get('known_exact_body_copy_of') else 'No recorded conflict; absence of conflicts not universally proved',access_limits=new_profiles.get(r['source_id'],{}).get('retention_limit','Inherited accepted source restrictions and stop register apply; no blanket open-license assertion'),raw_reference=r.get('raw_reference'),mapping_reference=r.get('mapping_reference')))
 write_csv('PROVENANCE_AND_VERIFICATION_REGISTER.csv',quality)
 parent_ids={sid:sid for sid in {r['source_id'] for r in combined}}
 parent_ids.update({sid:p.get('parent_family_id',sid) for sid,p in new_profiles.items()})
 write_csv('SOURCE_PARENT_IDENTITY_REGISTER.csv',[dict(source_id=sid,acquisition_parent_family_id=family,parent_level='Source/API/publisher acquisition parent; independent article work-family IDs are separate') for sid,family in sorted(parent_ids.items())])
 source_months=collections.defaultdict(list)
 for r in combined:source_months[(r['publication_date'][:7],r['stratum'],r['source_id'],parent_ids[r['source_id']])].append(r)
 write_csv('MONTH_SOURCE_PARENT_DISTRIBUTION.csv',[dict(month=m,stratum=g,source_id=s,acquisition_parent_family_id=parent,native_article_IDs=len({r['article_id'] for r in rs}),known_article_work_families=len({r['work_family_id'] for r in rs}),canonical_URLs=len({elt.canon(r['source_url']) for r in rs})) for (m,g,s,parent),rs in sorted(source_months.items())])
 state=elt.state();attempts={g:dict(cumulative_native_article_targets=state['strata'][g]['article'],effective_cumulative_discovery_targets=elt.effective_count(state,g,'discovery'),article_ceiling=6000,discovery_ceiling=1000) for g in elt.SCOPE['strata']}
 write_csv('HOST_STOP_REGISTER.csv',[dict(host=h,stop=json.dumps(v,ensure_ascii=False),scope='Inherited or observed publisher/access stop') for h,v in state['access_stops'].items()])
 import production,broaden
 cursors=json.loads((elt.OWN/'NATIVE_CURSORS.json').read_text());frontier=[]
 for g,sids in production.SOURCES.items():
  for sid in sids:
   ts=production.targets(sid);touched=set(state['targets']);queued={elt.sha((sid+'|article|'+elt.canon(t['url'])).encode())[:24] for t in ts};stopped=any(t['source_id']==sid and t['status']!='saved' for t in requests)
   key={'trinity_news':'trinity','mancunion':'manc','mit_tech':'tech','green_left':'gl'}.get(sid);remaining=len(cursors['routes'][key])-cursors['cursors'][key] if key else None
   frontier.append(dict(source_id=sid,stratum=g,frontier_state='blocked_inherited_policy' if sid=='otago_daily_times' else 'retained_native_opportunities',queued_native_article_targets=len(queued),transport_touched_queued_targets=len(queued&touched),unattempted_queued_targets=len(queued-touched),remaining_index_routes=remaining,observed_new_transport_stop=stopped,native_inventory_population='Unknown; retained queues/index route evidence only',references='NATIVE_CURSORS.json; inherited frozen queues; REQUESTS.jsonl'))
 broadstate=json.loads((elt.OWN/'BROADEN_CURSORS.json').read_text()) if (elt.OWN/'BROADEN_CURSORS.json').exists() else {}
 for p in broaden.profiles():
  v=broadstate.get(p['source_id'],{});ts=production.targets(p['source_id']);queued={elt.sha((p['source_id']+'|article|'+elt.canon(t['url'])).encode())[:24] for t in ts};touched=set(state['targets']);frontier.append(dict(source_id=p['source_id'],stratum=p['stratum'],frontier_state=v.get('stage','unattempted'),queued_native_article_targets=len(queued),transport_touched_queued_targets=len(queued&touched),unattempted_queued_targets=len(queued-touched),attempted_metadata_pages=v.get('attempted_pages',0),observed_native_total_posts=v.get('observed_native_total_posts'),observed_native_total_pages=v.get('observed_native_total_pages'),blocked_reason=v.get('blocked_reason'),references='BROADEN_PROFILES.json; BROADEN_CURSORS.json; SOURCE_FRONTIER_STATE.json',native_inventory_population='Publisher observed public post inventory; not all posts verified as newspaper articles'))
 if (elt.OWN/'BROADER_CANDIDATE_DISPOSITIONS.json').exists():
  for r in json.loads((elt.OWN/'BROADER_CANDIDATE_DISPOSITIONS.json').read_text())['records']:frontier.append(dict(source_id=r['source_id'],stratum=r['stratum'],frontier_state=r['frontier_state'],blocked_reason=r['reason'],queued_native_article_targets=0,transport_touched_queued_targets=0,unattempted_queued_targets=0,references=r['use_reference']))
 write_csv('SOURCE_FRONTIER_REGISTER.csv',frontier)
 opp=collections.Counter((r['stratum'],r['planned_lane']) for r in lines(elt.OWN/'OPPORTUNITY_LOG.jsonl'));elt.preparation_save('OPPORTUNITY_SUMMARY.json',dict(at_utc=elt.utc(),planned_production_fraction=.7,planned_broader_fraction=.2,planned_recovery_fraction=.1,counts=[dict(stratum=g,recovery=opp[g,'recovery'],production=opp[g,'production'],broader=opp[g,'broader']) for g in elt.SCOPE['strata']],scope='Opportunities, not article sampling weights or equal observed yields'))
 resource=elt.resource();start=json.loads((elt.OWN/'SUCCESSOR_START_RECEIPT.json').read_text());startseal=all(digest(elt.REPO/p)==h for p,h in start['frozen_predecessor_file_hashes'].items())
 checks=dict(changed_code_checks=all(json.loads((elt.OWN/f).read_text())['all_passed'] for f in ['CHANGED_CODE_CHECK.json','PUBLIC_NATIVE_ADAPTER_CHANGE_CHECK.json','NATIVE_UNIT_CHANGE_CHECK.json','MONITOR_APPEND_TAIL_CHECK.json']),new_native_component_dispositions_excluded=all(r['article_id'] not in seen and disp.get(r['article_id'])==r['status'] for r in structural),SQLite_quick_and_foreign_key_check=integrity,latest_version_mapping=latest_ok,predecessor_article_rows_preserved=old_articles==snap['baseline_article_rows'],predecessor_versions_preserved=old_versions==snap['baseline_versions'],predecessor_qualified_ID_date_body_digest_metadata_preserved=preserved,predecessor_dispositions_preserved=len(old_dispositions)==snap['baseline_dispositions'] and all(disp.get(a)==s for a,s in old_dispositions.items()),predecessor_final_files_hashes_preserved=startseal,new_TEXT_date_link_sidecar_sizes=body_ok,new_or_inherited_complete_raw_receipt_mapping=raw_ok,new_source_persistent_native_IDs=native_date_ok,print_date_whole_article_mapping=print_ok,six_465_month_ledgers=len(coverage)==6 and len(MONTHS)==465,fixed_cutoff=elt.SCOPE['publication_interval']==['1988-01-01','2026-09-21'],regional_cumulative_ceilings=all(r['cumulative_native_article_targets']<=6000 and r['effective_cumulative_discovery_targets']<=1000 for r in attempts.values()),native_hops_at_most_four=all(n<=4 for n in state.get('native_http_hops',{}).values()),no_in_progress_transport=all(v!='in_progress' for v in state['targets'].values()),ODT_policy_stop_preserved='www.odt.co.nz' in state['access_stops'],InDaily_asset_stop_preserved='assets.indailysa.com.au' in state['access_stops'],no_semantic_or_length_exclusion=all(r.get('semantic_labels_executed') is False and r.get('length_filter_used') is False for r in new),media_cap=resource['cumulative_bytes']<5000000000,writer_exit_verified=True,no_baseline_consolidation_recount=not any(r.get('baseline_TEXT_consolidation') for r in lines(elt.OWN/'TRANSACTION_RECEIPTS.jsonl')))
 dimensions={k:dict(collections.Counter(str(r.get(k) or 'unrecorded') for r in combined)) for k in ['source_id','stratum','source_frame','genre','provenance']}
 summary=dict(at_utc=elt.utc(),status='bounded_global_distribution_tranche_delivered',publication_interval=elt.SCOPE['publication_interval'],deadline_unchanged=elt.SCOPE['hard_deadline_at_utc'],collection_close=close,baseline_complete_IDs=snap['baseline_complete_IDs'],baseline_pooled_minimum_months=snap['baseline_pooled_floor_months'],additional_qualified_IDs=len(new),additional_source_mix=dict(collections.Counter(r['source_id'] for r in new)),cumulative_selected_complete_IDs=len(combined),whole_TEXT_database_counts=counts,coverage=coverage,cumulative_metadata_dimensions=dimensions,cumulative_attempt_counts=attempts,new_distinct_transport_target_receipts=len(requests),new_HTTP_hops=sum(len(r.get('hops',[])) for r in requests),new_transport_statuses=dict(collections.Counter(r['status'] for r in requests)),new_pending_or_component_records=len(pending),new_reclassified_date_conflict_articles=len(reclassified),new_reclassified_native_component_rows=len(structural),inherited_print_original_articles_recovered=sum(r.get('raw_encoding')=='original_pdf' for r in new),new_print_original_articles_recovered=sum(bool(r.get('historical_original_print')) for r in new),baseline_TEXT_consolidated=0,exact_body_overlap_native_IDs=len(overlaps),source_frontier=frontier,resource_at_delivery=resource,checks=checks,all_changed_tranche_checks_passed=all(checks.values()),mapping_errors=errors,accepted_pre_append_database_snapshot=old_db,old_body_raw_hash_sweep=False,final_database_hash_once=True,verification_scope='Changed date/identity/body/reference/receipt mapping; one store check and frozen metadata preservation. No universal historical-version, source-claim truth or quotation-origin assertion',independence_limit='Native identity and known exact-body families; unresolved wire/syndication/mirrored works remain',fear_or_topic_labels_executed=False)
 elt.preparation_save('DELIVERY_SUMMARY.json',summary);table='\n'.join('| '+g+' | '+str(v['months_at_minimum_coverage'])+' | '+str(v['one_article_months'])+' | '+str(v['zero_article_months'])+' |' for g,v in coverage.items())
 report=f'''# Newspaper global extraction and distribution — 8 October 2026

This fixed same-chat tranche adds **{len(new):,} qualified complete article IDs**, bringing the cumulative whole-TEXT store to **{len(combined):,} IDs**. Pooled months at the two-known-work-family floor: **{snap['baseline_pooled_floor_months']} → {coverage['pooled']['months_at_minimum_coverage']} /465**. Two is a minimum; eligible surplus continued through the same ELT pipeline.

Collection stopped for **{close['reason']}**, with writer exit and the lifetime mutex verified. The prospective fixed end remained **2026-10-08T15:15:14.896978Z / 9 October 01:15:14 Brisbane**. This tranche used the existing owner, without a new chat or rolling extension. The accepted {snap['baseline_complete_IDs']:,}-ID predecessor and its final tables/manifests remain frozen. Counters, native cursors, source stops, PDF ceilings and cumulative allocation were carried forward without resetting. No full-body queue or database copy was created.

| Stratum | Months at the floor | One-article months | Zero-confirmed months |
| --- | ---: | ---: | ---: |
{table}

The publication interval remains **1988-01-01 through 2026-09-21**, including partial September. Report snapshot time is {summary['at_utc']}. Individual retrieval/extraction and source content-version times remain in record-level provenance; later retrieval does not establish end-of-day completeness or historical-body equivalence. Zero-confirmed months are observed gaps, not absence of discourse. Acquired native IDs, known work families and canonical URLs are separately counted by month/source/stratum/recorded genre. Genre remains unrecorded where publisher evidence does not establish it. Source acquisition parents are separately mapped from independent article work families. The provenance/verification register distinguishes direct publisher utterances and archival reproductions from unresolved origin questions, identity/date/content mapping, pending checks, conflicts and access limits; it does not rank sources using a confidence score or establish the truth of their claims. Exact-body overlap candidates preserve every native record; family mapping does not establish all syndication or mirrored-work independence.

Regular ELT extracted eligible whole articles, performed structural cleanup and immediately Loaded TEXT with persistent article IDs, source links, date/version fields and raw provenance. The new public WordPress sources require a publisher-advertised interface, documented API schema and public unprotected native post identity. Their IDs use the publisher post ID, while URL aliases and body versions remain separate. Source-specific use/publication limits are retained; public reachability is not an open-license assertion. The Portugal News body frame remains blocked by unresolved retention under its published copying limits. Native source inventory totals describe posts, not qualified article counts.

The 70% continuing-production /20% broader-newspaper /10% targeted-recovery opportunity schedule is not a weighting scheme. Student/specialist/advocacy frames remain visible alongside broader community/regional sources; pooled presence does not certify countries, representative title populations, complete archives or sufficient production density. See source frontier states for attempted, unattempted, blocked and exhausted opportunities. Policy stops, finite source inventory, native counters and the fixed time/resource envelope constrain observed volumes.

The inherited **36 historical PDF issues /184,103,804 raw bytes** still consume their allowance; {summary['new_print_original_articles_recovered']} qualified articles were restored from mapped inherited print inputs. No new historical issue allowance was opened. ODT/Allied and InDaily asset-host stops remain. Conflicting date fields, unresolved article boundaries, transport failures and components remain in separate evidence/disposition registers. {len(structural)} new Northern Rivers image/heading/embedded-edition units were reclassified with original rows, bodies and versions preserved; future counterparts enter pending evidence directly. Dates are not inferred or overridden to fill gaps.

The one changed-tranche closeout passed: **{all(checks.values())}**. SQLite quick/foreign-key/latest-version checks ran after writer exit. Metadata checks preserve {snap['baseline_article_rows']:,} predecessor article rows, {snap['baseline_versions']:,} versions, {snap['baseline_complete_IDs']:,} qualified IDs and {snap['baseline_dispositions']} dispositions. New TEXT/date/link/sidecar/raw-receipt mappings were checked once. No old body/raw hash sweep ran. Remaining mapping errors: **{len(errors)}**. The final database hash records this append-store snapshot and does not freeze future authorized appends.

Cumulative retained bytes: **{resource['cumulative_bytes']:,} /5,000,000,000** decimal. Live free bytes: **{resource['free_bytes']:,}**. Physical headroom after the protected 15 GiB floor, 48 MiB recovery allowance and live leases/pending operation: **{resource['physical_headroom']:,}**. Per-operation checks included the separate active owner's lease; that owner's data were not read. No floor waiver, evidence deletion or allowance reset occurred.

Registers, six monthly ledgers, source/year and month/source/genre distributions, native/canonical/alias/version/work-family tables, exact-body overlap review, pending/disposition/transport/source-frontier registers and manifests accompany this report. Changes are confined to this worker subtree and serial appends in the existing newspaper database. Coordinator controls, shared logs and Git remain coordinator-owned. No social/government acquisition, sealed evaluator access, further chat, subagent, automatic successor, recurring automation or third-party messages were used.

| Evidence level | Status in this acquisition delivery |
| --- | --- |
| 1. Dated source presence and readable original text | Native whole-TEXT identity/date/body mappings and pending limits reported above. Historical body equivalence remains unproved. |
| 2. Climate/warming relevance and similarity | Deferred; requires a defined unit and source frame. No corpus-wide topic or semantic exclusion was executed. |
| 3. Affect, risk, future harm or responsibility association | Deferred until validation; these associations are not automatically fear. |
| 4. Fear-specific interpretation | Deferred; needs traceable original passages with speaker/holder, target, time horizon, quotation and negation checked. Quantification requires supported annotation and measurement. |

Coverage and collection volume do not establish emotion prevalence or a comparable three-role time series. Neutral and routine eligible discourse remains retained; fear words or scores were not source, cleaning, inclusion or success gates.
'''
 elt.preflight(len(report.encode())*2);(elt.OWN/'DELIVERY_REPORT.md').write_text(report);elt.preparation_save('WORKER_COMPLETION.json',dict(at_utc=elt.utc(),status=summary['status'],additional_qualified_IDs=len(new),no_active_background_worker=True,all_changed_tranche_checks_passed=all(checks.values()),control_reconciliation='Coordinator owned; no controls edited'))
 current=dict(at_utc=elt.utc(),status='collection_closed_and_changed_tranche_delivered',latest_qualified_whole_TEXT_IDs=len(combined),new_qualified_complete_article_IDs=len(new),coverage={g:dict(months_at_floor=v['months_at_minimum_coverage'],one_article_months=v['one_article_months'],zero_confirmed_months=v['zero_article_months'],below_floor_months=v['one_article_months']+v['zero_article_months']) for g,v in coverage.items()},pooled_gap_months=[r['month'] for r in gaps if r['stratum']=='pooled'],resource_receipt=resource,writer=dict(pid=close['last_writer_pid'],writer_exit_observed=True,no_active_writer=True),collection_close=close,final_summary_reference='DELIVERY_SUMMARY.json',final_report_reference='DELIVERY_REPORT.md',all_changed_tranche_checks_passed=all(checks.values()))
 tx=lines(elt.OWN/'TRANSACTION_RECEIPTS.jsonl')
 if tx:current['last_committed_Load']={k:tx[-1].get(k) for k in ['at_utc','article_id','version_id','status','body_sha256']}
 elt.preparation_save('CURRENT_STATUS.json',current)
 paths=[p for p in elt.OWN.rglob('*') if p.is_file() and p.suffix not in ['.gz','.png','.txt'] and 'DELIVERY_FILE_RECEIPTS' not in p.name and '__pycache__' not in p.parts and 'tmp' not in p.relative_to(elt.OWN).parts]
 hashes={str(p.relative_to(elt.OWN)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in paths};hashes[dbkey]=dict(sha256=digest(elt.DB),bytes=elt.DB.stat().st_size)
 elt.preparation_save('DELIVERY_FILE_RECEIPTS.json',dict(at_utc=elt.utc(),files=hashes,raw_body_hash_sweep=False,final_database_hashed_once=True,accepted_pre_append_database_receipt=old_db));print(json.dumps({k:summary[k] for k in ['status','additional_qualified_IDs','cumulative_selected_complete_IDs','all_changed_tranche_checks_passed']}))
if __name__=='__main__':main()
