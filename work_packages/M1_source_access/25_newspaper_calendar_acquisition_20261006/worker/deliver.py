"""One consolidated changed-tranche delivery; no old body rescan or model labels."""
import collections,csv,datetime as dt,json,pathlib,sqlite3
import elt

MONTHS=[f'{y:04d}-{m:02d}' for y in range(1988,2027) for m in range(1,13) if f'{y:04d}-{m:02d}'<='2026-09']
FIELDS=['article_id','disposition','source_id','source','source_url','raw_source_url','title','publication_date','stratum','country','edition','source_frame','genre','work_family_id','version_id','body_reference','body_sha256','raw_reference','raw_sha256','retrieved_at_utc','content_version_time','provenance','article_boundary_evidence','sidecar_reference','qualification_reason','origin_package']

def write_csv(name,rows,fields):
 p=elt.OWN/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def indexed(rows):
 out=collections.defaultdict(set)
 for r in rows:
  if r['disposition']=='confirmed_complete':
   out[('pooled',r['publication_date'][:7])].add(r['work_family_id']);out[(r['stratum'],r['publication_date'][:7])].add(r['work_family_id'])
 return out

def main():
 # Only the accepted selected register is reused; no old raw/body audit or import.
 baseline=[json.loads(x) for x in (elt.OLD24/'article_baseline_v1/ARTICLE_REGISTER.jsonl').read_text().splitlines() if x]
 before=[]
 for r in baseline:
  if r['disposition']=='confirmed_complete':
   q=dict(r,origin_package='accepted_package24_selected_baseline');q['source_id']=q.get('source_id') or q.get('source');q['body_reference']=q.get('complete_body_reference');q['body_sha256']=q.get('body_version_sha256');before.append(q)
 with elt.LOCK.open('a+b') as lock:
  elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);resource=elt.preflight(16*1048576);c=elt.connect();c.row_factory=sqlite3.Row
  rows=c.execute('SELECT a.*,v.body_reference,v.body_sha256,v.raw_reference,v.raw_sha256,v.provenance_json,d.status AS current_status,d.reason AS current_reason FROM articles a JOIN article_versions v ON v.version_id=a.latest_version_id LEFT JOIN article_dispositions d ON d.article_id=a.article_id').fetchall()
  fresh=[]
  for row in rows:
   r=json.loads(row['provenance_json']);r.update(article_id=row['article_id'],publication_date=row['publication_date'],stratum=row['stratum'],work_family_id=row['work_family_id'],source_url=row['source_url'],version_id=row['latest_version_id'],body_reference=row['body_reference'],body_sha256=row['body_sha256'],raw_reference=row['raw_reference'],raw_sha256=row['raw_sha256'],disposition=row['current_status'] or 'confirmed_complete',qualification_reason=row['current_reason'],origin_package='package25_durable_ELT');fresh.append(r)
  by_id={r['article_id']:r for r in before};by_id.update({r['article_id']:r for r in fresh if r['disposition']=='confirmed_complete'});combined=list(by_id.values());before_ids={r['article_id'] for r in before};new=[r for r in fresh if r['disposition']=='confirmed_complete' and r['article_id'] not in before_ids]
  db_counts={'article_rows_retained':len(fresh),'currently_qualified_article_rows':sum(r['disposition']=='confirmed_complete' for r in fresh),'new_qualified_ids_beyond_accepted_baseline':len(new),'already_accepted_ids_loaded_by_current_representation':sum(r['disposition']=='confirmed_complete' and r['article_id'] in before_ids for r in fresh),'whole_text_versions':c.execute('SELECT count(*) FROM article_versions').fetchone()[0],'separate_pending_or_component_records':c.execute('SELECT count(*) FROM evidence').fetchone()[0],'reclassified_retained_article_rows':sum(r['disposition']!='confirmed_complete' for r in fresh),'baseline_metadata_rows':c.execute('SELECT count(*) FROM baseline').fetchone()[0]}
  qualified=[r for r in fresh if r['disposition']=='confirmed_complete']
  dimensions={key:dict(collections.Counter(str(r.get(key) or 'unrecorded') for r in qualified)) for key in ['source_id','stratum','source_frame','genre','provenance']}
  checks={}
  checks['SQLite_quick_check']=c.execute('PRAGMA quick_check').fetchone()[0]=='ok';checks['foreign_keys']=not c.execute('PRAGMA foreign_key_check').fetchall();checks['qualified_current_latest_TEXT_nonempty']=not c.execute('SELECT a.article_id FROM articles a LEFT JOIN article_dispositions d ON d.article_id=a.article_id JOIN article_versions v ON v.version_id=a.latest_version_id WHERE d.article_id IS NULL AND trim(v.body_text)=""').fetchall();checks['qualified_current_dates_and_links']=all(elt.eligible(r['publication_date']) and r['source_url'] and r['article_id'] for r in fresh if r['disposition']=='confirmed_complete');checks['qualified_current_body_references_exist']=all(r.get('body_reference') and (elt.REPO/r['body_reference']).is_file() for r in fresh if r['disposition']=='confirmed_complete');checks['no_duplicate_current_article_IDs']=len({r['article_id'] for r in fresh})==len(fresh);checks['fixed_calendar_465_months']=len(MONTHS)==465;checks['one_latest_version_per_retained_article']=len(rows)==len(fresh)
  checks['latest_version_exists_and_belongs_to_article']=not c.execute('SELECT a.article_id FROM articles a LEFT JOIN article_versions v ON v.version_id=a.latest_version_id WHERE v.version_id IS NULL OR v.article_id<>a.article_id').fetchall()
  version_refs=[dict(row) for row in c.execute('SELECT version_id,body_reference,body_sha256,raw_reference,raw_sha256 FROM article_versions')]
  checks['all_retained_version_body_references_exist']=all(r['body_reference'] and (elt.REPO/r['body_reference']).is_file() and len(r['body_sha256'])==64 for r in version_refs)
  # Reuse digests already produced during ingestion; no payload hash sweep.
  # The close checks paths and sizes, while the database holds original TEXT.
  checked_files={};failures=[]
  for r in version_refs:
   for field,hfield in [('body_reference','body_sha256'),('raw_reference','raw_sha256')]:
    ref=r.get(field);expected=r.get(hfield)
    if not ref or not expected:continue
    p=elt.REPO/ref
    if not str(p).startswith(str(elt.OWN)+ '/'):
     continue
    if ref not in checked_files:
     checked_files[ref]={'recorded_sha256':expected,'hash_reused_from_ELT':True,'rehash_executed':False,'exists':p.is_file(),'bytes':p.stat().st_size if p.exists() else None}
     if not p.is_file() or len(expected)!=64:failures.append(ref)
  for r in fresh:
   ref=r.get('sidecar_reference')
   if ref and not (elt.REPO/ref).is_file():failures.append(ref)
  checks['changed_article_raw_and_body_references']=not failures
  transport=[json.loads(row[0]) for row in c.execute('SELECT receipt_json FROM transport')];c.close()
  for r in transport:
   ref=r.get('raw_reference');expected=r.get('raw_sha256')
   if not ref or not expected:continue
   p=elt.REPO/ref
   if not str(p).startswith(str(elt.OWN)+'/'):continue
   checked_files.setdefault(ref,{'recorded_sha256':expected,'hash_reused_from_ELT':True,'rehash_executed':False,'exists':p.is_file(),'bytes':p.stat().st_size if p.exists() else None,'role':'changed transport raw/partial'})
   if not p.is_file() or len(expected)!=64 or p.stat().st_size!=r.get('raw_bytes'):failures.append(ref)
  checks['changed_article_and_transport_references_and_raw_sizes']=not failures
  checks['no_unresolved_in_progress_transport']=not any(v=='in_progress' for v in elt.state()['targets'].values())
  import ast
  checks['changed_python_syntax']=True
  for name in ['elt.py','extract_load.py','calendar_run.py','deliver.py','map_selected_print.py']:ast.parse((elt.OWN/name).read_text())
  checks['HTTP_native_target_hop_ceiling']=all(n<=elt.SCOPE['max_http_hops_per_target'] for n in elt.state().get('native_http_hops',{}).values())
  before_index=indexed(before);after_index=indexed(combined);summaries={};residual=[];new_months=[]
  for geo in ['pooled']+elt.SCOPE['strata']:
   ledger=[]
   for month in MONTHS:
    b=len(before_index[(geo,month)]);a=len(after_index[(geo,month)]);entry={'month':month,'stratum':geo,'before_distinct_complete_articles':b,'after_distinct_complete_articles':a,'before_state':'2_or_more' if b>=2 else str(b),'after_state':'2_or_more' if a>=2 else str(a),'meets_hard_two_article_minimum':a>=2,'newly_passing':b<2 and a>=2,'additional_articles_required':max(0,2-a),'partial_publication_month':month=='2026-09'};ledger.append(entry)
    if a<2:residual.append(entry)
    if entry['newly_passing']:new_months.append(entry)
   slug='pooled' if geo=='pooled' else {'EU/Europe excluding UK':'EU_Europe_excluding_UK','UK':'UK','AU':'AU','US':'US','NZ':'NZ'}[geo]
   write_csv('coverage/MONTHLY_'+slug+'.csv',ledger,list(ledger[0]));summaries[geo]={'before_passing':sum(r['before_distinct_complete_articles']>=2 for r in ledger),'after_passing':sum(r['after_distinct_complete_articles']>=2 for r in ledger),'after_one':sum(r['after_distinct_complete_articles']==1 for r in ledger),'after_zero':sum(r['after_distinct_complete_articles']==0 for r in ledger),'newly_passing':sum(r['newly_passing'] for r in ledger),'remaining_article_slots':sum(r['additional_articles_required'] for r in ledger)}
  checks['six_465_row_ledgers']=len(summaries)==6
  state=elt.state();external=elt.external_discovery_counts();initial=collections.Counter(r['stratum'] for r in json.loads((elt.OWN/'EXTERNAL_DISCOVERY_RECEIPT.json').read_text())['web_queries']);counters={g:dict(native_distinct_article_targets=state['strata'][g]['article'],direct_transport_discovery_targets=sum(r['stratum']==g and r['purpose']=='discovery' for r in transport),initial_external_discovery_charged_in_state=initial[g],later_external_discovery_targets=external[g],total_external_discovery_targets=initial[g]+external[g],state_discovery_counter=state['strata'][g]['discovery'],effective_discovery_targets=state['strata'][g]['discovery']+external[g],article_ceiling=400,discovery_ceiling=200) for g in elt.SCOPE['strata']};checks['five_regional_attempt_ceiling']=all(r['native_distinct_article_targets']<=400 and r['effective_discovery_targets']<=200 for r in counters.values())
  checks['discovery_charges_reconcile']=all(r['direct_transport_discovery_targets']+r['initial_external_discovery_charged_in_state']==r['state_discovery_counter'] for r in counters.values())
  write_csv('ARTICLE_REGISTER.csv',combined+[r for r in fresh if r['disposition']!='confirmed_complete'],FIELDS);write_csv('NEW_ARTICLE_REGISTER.csv',new,FIELDS);write_csv('RESIDUAL_MONTHS.csv',residual,list(residual[0]) if residual else ['month','stratum']);write_csv('NEWLY_PASSING_MONTHS.csv',new_months,list(new_months[0]) if new_months else ['month','stratum'])
  evidence_lines=[]
  c=elt.connect();c.row_factory=sqlite3.Row
  for row in c.execute('SELECT evidence_id,source_id,source_url,status,metadata_json,loaded_at FROM evidence'):
   r=dict(row);r['metadata_reference']='newspaper_elt.sqlite3:evidence:'+r['evidence_id'];r.pop('metadata_json');evidence_lines.append(r)
  c.close();write_csv('PENDING_AND_COMPONENT_REGISTER.csv',evidence_lines,['evidence_id','source_id','source_url','status','loaded_at','metadata_reference'])
  close=json.loads((elt.OWN/'COLLECTION_CLOSE_REASON.json').read_text());summary={'snapshot_at_utc':elt.utc(),'fixed_publication_interval':elt.SCOPE['publication_interval'],'September2026_partial':True,'hard_minimum':2,'calendar_months':465,'baseline_scope':'142 accepted complete articles from a bounded selected register, not all historical saved input','database':str(elt.DB.relative_to(elt.REPO)),'database_counts':db_counts,'coverage':summaries,'attempt_counts':counters,'transport_status_counts':dict(collections.Counter(r['status'] for r in transport)),'resource_before_delivery':resource,'collection_close':close,'checks':checks,'all_changed_tranche_checks_passed':all(checks.values()),'semantic_labels_executed':False,'raw_old_corpus_rescanned':False,'source_completion_or_national_representativeness_claimed':False}
  summary['current_qualified_metadata_dimensions']=dimensions
  summary['genre_scope']='Only already recorded genre metadata is tallied; unrecorded is retained, with no corpus-wide genre or semantic labeling.'
  summary['verification_scope']='Checks cover stored identity/date/link/body references, native article boundaries and named source mappings. They do not establish universal historical body equivalence, attribution of every quotation, or truth of reported claims.'
  (elt.OWN/'DELIVERY_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');(elt.OWN/'CHANGED_REFERENCE_RECEIPT.json').write_text(json.dumps({'at_utc':elt.utc(),'scope':'All retained current-tranche article-version references, current sidecar references, transport references and raw sizes only; existing ingestion SHA256 receipts reused; no old body rescan or payload hash sweep','files':checked_files,'failures':failures},indent=2)+'\n')
  pooled=summaries['pooled'];report=f'''# Newspaper calendar acquisition: package25 delivery\n\nSnapshot: {summary['snapshot_at_utc']}. Publication interval remains 1988-01-01 through 2026-09-21; September2026 is partial. The absolute task deadline remains {elt.SCOPE['hard_deadline_at_utc']}.\n\nThe accepted selected baseline had142 complete articles and43 passing pooled months. This tranche adds {len(new)} qualified persistent IDs beyond that baseline. The durable store retains {db_counts['article_rows_retained']} article rows and {db_counts['whole_text_versions']} whole TEXT versions; {db_counts['currently_qualified_article_rows']} current rows qualify, with {db_counts['reclassified_retained_article_rows']} original rows separately reclassified and preserved. Pending/components remain in a separate evidence table. The combined selected register has {len(combined)} complete IDs.\n\nPooled passing months rise from43 to {pooled['after_passing']}/465; {pooled['newly_passing']} months newly pass, {pooled['after_one']} have one and {pooled['after_zero']} have zero. Remaining pooled deficit: {pooled['remaining_article_slots']} article slots. Surplus is retained and does not transfer between months. The six465-row ledgers preserve regional gaps; pooled presence does not certify regional or archive completeness.\n\n'''
  report+='| Stratum | Before passing | After passing | One | Zero |\n|---|---:|---:|---:|---:|\n'+''.join(f'|{g}|{s["before_passing"]}|{s["after_passing"]}|{s["after_one"]}|{s["after_zero"]}|\n' for g,s in summaries.items())
  report+='\nCurrent qualified source counts: '+', '.join(f'{key}: {n}' for key,n in dimensions['source_id'].items())+'. Recorded source-frame, genre and provenance dimensions are in DELIVERY_SUMMARY.json. Unrecorded article genre is retained, rather than inferred.\n'
  report+='''\nWhole articles load immediately into newspaper_elt.sqlite3. Stable article IDs and actual publisher/PDF links are distinct from retrieval IDs, raw hashes and body versions. Printed continuations join into one original article with coordinate sidecars; tables, notices, schedules, incomplete liveblogs and unresolved compilations do not supply article slots. Named structural corrections preserve their original rows/text.\n\nHTML/public JSON are direct evidence of the recorded publisher utterance. Explicit wire/quoted origins remain visible in original text and require attribution at later analysis. Publisher print scans are archival reproductions of original newspaper articles. Current retrieval and version timestamps do not establish historical body equivalence or truth of reported claims. Student/advocacy titles retain their source frames; this is no claim of nationally representative media.\n\nConcrete residual routes: Green Left is evidenced from1991 onward; pre1991 AU requires another newspaper frame. The Tech's native digital articles cover observed later issue eras, with bounded selected early scans and named OCR/continuation limits. Mancunion/Beaver/Trinity retain their evidenced site eras and current API/sitemap boundaries. ODT public dated articles have native-text/date and migration limitations; query hits alone never count. Crimson retention remains prior-permission pending; Guardian key/retention and conflicting archive-start evidence remain unresolved; NZETC Salient through1979 supplies no1988 article evidence. No publisher outreach occurred.\n\nAccess refusals, Retry-After, exact previous stops and interrupted attempts remain preserved. Discovery targets, distinct article-target attempts, HTTP hops and actual complete articles are counted separately. Effective discovery ceilings include external date-only source searches. No social corpus, government/other formal database, hidden evaluator, source-semantic labeling, Git operation, third-party message or new automation occurred.\n\nThe before/after evidence concerns dated original text and coverage. Climate relevance is deferred. Affect/risk association and fear interpretation remain unmeasured. Neither coverage nor article counts establish a comparable emotion series.\n\nOne consolidated changed-tranche check is recorded in DELIVERY_SUMMARY.json and CHANGED_FILE_HASH_CHECK.json. Accepted old input hashes and metadata are reused. The original package24 stops and outputs remain frozen. This delivery closes the bounded continuation; no automatic next tranche is released.\n'''
  report+=f'\nAcquisition stopped at 2026-10-06T11:01:45.892979Z on actual physical headroom, before the deadline. Free bytes 16,173,236,224 minus the 15 GiB floor, 48 MiB recovery allowance and 33,619,968 bytes of own lease/receipt reserve yielded -16,842,752 bytes. Cumulative retention was 268,671,967 bytes and allocation headroom 771,449,889 bytes: the 1 GiB allowance was not exhausted. Later live headroom supported closing already saved/prepared inputs only; no network acquisition resumed. Four interrupted receipts were reconciled with their pre-close originals retained, and native attempt counters were not reset. Seven existing transport raw/partial files were linked to missing receipt references, preserving original receipts and stop status. The closing checkpoint records the cumulative +128 MiB crossing interrupted by the physical stop.\n'
  report+='\nEarly-period result: eight complete original print articles, two per issue/month, were restored for April 1988, October 1988, May 1989 and April 1990. Continuations and photo/table references remain in sidecars/raw/renders. One May 1989 FinBoard continuation has severe native OCR and remains outside the complete count; an alternative whole reporting article was used. A page 13 continuation misread as 3 was corrected from the printed source, with the unused derivative preserved. Two small headline artefact corrections produced new body versions under unchanged article IDs.\n'
  report=report.replace('CHANGED_FILE_HASH_CHECK.json','CHANGED_REFERENCE_RECEIPT.json')
  for old_text,new_text in [('had142','had 142'),('and43','and 43'),('the1GiB','the 1 GiB'),('the15GiB','the 15 GiB'),('48MiB','48 MiB'),('September2026','September 2026'),('from1991','from 1991'),('pre1991','pre-1991'),('through1979','through 1979'),('no1988','no 1988'),('six465-row','six 465-row'),('forApril1988','for April 1988'),('October1988','October 1988'),('May1989','May 1989'),('April1990','April 1990'),('page13','page 13'),('as3','as 3'),('from43','from 43'),('bytes16173236224','bytes 16173236224')]:report=report.replace(old_text,new_text)
  (elt.OWN/'DELIVERY_REPORT.md').write_text(report)
  receipt_paths=['DELIVERY_REPORT.md','DELIVERY_SUMMARY.json','ARTICLE_REGISTER.csv','NEW_ARTICLE_REGISTER.csv','RESIDUAL_MONTHS.csv','NEWLY_PASSING_MONTHS.csv','PENDING_AND_COMPONENT_REGISTER.csv','CHANGED_REFERENCE_RECEIPT.json','COLLECTION_CLOSE_REASON.json','CLOSE_TRANSPORT_RECONCILIATION.json','CLOSE_PARTIAL_REFERENCE_REPAIRS.json','CHECKPOINT.json','CHECKPOINT_HISTORY.jsonl','CACHE_RECOVERY_CHECKPOINT.json','CACHE_SELECTION.json','NEW_PDF_ISSUES.json','STARTUP_CHECK.json','TRANSPORT_STATE.json','WORKER_PROCESS.json','README.md','elt.py','extract_load.py','calendar_run.py','deliver.py','map_selected_print.py']+[str(p.relative_to(elt.OWN)) for p in (elt.OWN/'coverage').glob('*.csv')]
  receipts={name:{'sha256':elt.sha((elt.OWN/name).read_bytes()),'bytes':(elt.OWN/name).stat().st_size} for name in receipt_paths};receipts['newspaper_elt.sqlite3']={'sha256':elt.sha(elt.DB.read_bytes()),'bytes':elt.DB.stat().st_size};(elt.OWN/'DELIVERY_FILE_RECEIPTS.json').write_text(json.dumps({'at_utc':elt.utc(),'files':receipts},indent=2)+'\n')
 print(json.dumps({'DELIVERED':True,'pooled':pooled,'new_ids':len(new),'database_counts':db_counts,'checks':checks,'resource':elt.preflight()},indent=2))

if __name__=='__main__':main()
