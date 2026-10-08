"""Single changed-tranche acceptance and final receipt after verified writer exit."""
import collections,csv,fcntl,io,json,os,sqlite3
from pathlib import Path
import elt
MONTHS=[f'{y:04d}-{m:02d}' for y in range(1988,2027) for m in range(1,13) if f'{y:04d}-{m:02d}'<='2026-09']
def lines(path):return [json.loads(v) for v in path.read_text().split('\n') if v] if path.exists() else []
def write_csv(name,rows,fields=None):
 fields=fields or list(dict.fromkeys(k for r in rows for k in r))
 out=io.StringIO();w=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows);b=out.getvalue().encode();elt.preflight(len(b)*2+65536)
 p=elt.OWN/name;p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.pending');t.write_bytes(b);t.replace(p)
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
 # The lifetime mutex also prevents an overlapping newspaper writer.
 with (elt.PREDECESSOR/'NEWSPAPER_OWNER_MUTEX.lock').open('a+b') as owner:
  fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB);return deliver(close)
def deliver(close):
 elt.preflight(32*1024**2);snap=json.loads((elt.OWN/'INPUT_SNAPSHOT.json').read_text());accepted=json.loads((elt.PREDECESSOR/'DELIVERY_FILE_RECEIPTS.json').read_text());dbkey=str(elt.DB.relative_to(elt.REPO));old_db=accepted['files'][dbkey]
 baseline=list(csv.DictReader((elt.PREDECESSOR/'CUMULATIVE_ARTICLE_REGISTER.csv').open()));frozen={r['article_id']:r for r in baseline};assert len(frozen)==2806
 old_dispositions={r['article_id']:r['disposition'] for r in csv.DictReader((elt.PREVIOUS/'ARTICLE_REGISTER.csv').open()) if r['disposition']!='confirmed_complete'}
 history=lines(elt.OWN/'REQUESTS.jsonl');requests=list({r['target_id']:r for r in history}.values());receipt_by_raw={r['raw_reference']:r for r in requests if r.get('raw_reference')}
 print_base=elt.REPO/'work_packages/M1_source_access/23_newspaper_acquisition_and_transition_20261005/transition_research/acquisition_followthrough_20261005';accepted_print={str((print_base/r['raw_path']).relative_to(elt.REPO)):r for r in lines(print_base/'REQUESTS.jsonl') if r.get('status')=='saved' and r.get('raw_path')}
 new=[];pending=[];preserved=True;body_ok=True;raw_ok=True;print_ok=True;errors=[]
 with elt.LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);c=elt.connect();c.row_factory=sqlite3.Row
  q=c.execute('SELECT a.*,v.provenance_json,v.body_reference,v.raw_reference,v.body_sha256,length(v.body_text) AS chars,length(CAST(v.body_text AS BLOB)) AS bytes FROM articles a JOIN article_versions v ON v.version_id=a.latest_version_id LEFT JOIN article_dispositions d ON d.article_id=a.article_id WHERE d.article_id IS NULL').fetchall()
  seen=set()
  for row in q:
   aid=row['article_id'];seen.add(aid)
   if aid in frozen:
    old=frozen[aid];preserved &= row['publication_date']==old['publication_date'] and row['source_url']==old['source_url'] and row['body_sha256']==old['body_sha256'] and row['work_family_id']==old['work_family_id']
    continue
   r=json.loads(row['provenance_json']);r.update(article_id=aid,publication_date=row['publication_date'],source_url=row['source_url'],stratum=row['stratum'],work_family_id=row['work_family_id'],version_id=row['latest_version_id'],body_sha256=row['body_sha256'],disposition='confirmed_complete',whole_TEXT_characters=row['chars'],whole_TEXT_bytes=row['bytes'])
   bp=elt.REPO/row['body_reference'] if row['body_reference'] else None;rp=elt.REPO/row['raw_reference'] if row['raw_reference'] else None
   bok=bool(bp and bp.exists() and bp.stat().st_size==row['bytes'] and row['chars']>0 and elt.eligible(row['publication_date']) and row['source_url'].startswith('https://'));body_ok &= bok
   if r.get('raw_encoding')=='original_pdf':
    rec=accepted_print.get(row['raw_reference']);mp=elt.REPO/r['mapping_reference'];mapping=json.loads(mp.read_text()) if mp.exists() else {}
    rok=bool(rec and not rec.get('partial') and rp and rp.exists() and rp.stat().st_size==rec['raw_bytes'] and rec['raw_sha256']==r['raw_sha256'] and mapping.get('complete_article_visually_traced') and mapping.get('date_visually_confirmed') and mapping.get('publication_date')==row['publication_date']);print_ok &= rok
    r['actual_raw_transport_target_id']='inherited_complete_original:'+r['request_id']
   else:
    rec=receipt_by_raw.get(row['raw_reference']);rok=bool(rec and rec['status']=='saved' and rp and rp.exists() and rp.stat().st_size==rec.get('stored_bytes') and rec.get('raw_encoding')=='gzip' and rec.get('raw_sha256')==r.get('raw_sha256') and rec.get('stored_sha256')==r.get('stored_sha256') and rec.get('raw_bytes',0)<=(elt.SCOPE['historical_pdf_raw_cap_bytes'] if r.get('historical_original_print') and rec.get('target',{}).get('extra',{}).get('kind')=='historical_pdf' else elt.SCOPE['default_raw_object_cap_bytes']));r['actual_raw_transport_target_id']=rec['target_id'] if rec else None
   if r.get('historical_original_print'):
    mp=elt.REPO/r['mapping_reference'];mapping=json.loads(mp.read_text()) if mp.exists() else {};pok=bool(mapping.get('complete_article_visually_traced') and mapping.get('date_visually_confirmed') and mapping.get('publication_date')==row['publication_date']);print_ok &= pok;rok &= pok
   raw_ok &= rok
   if not(bok and rok):errors.append({'article_id':aid,'body_mapping':bok,'raw_receipt_mapping':rok})
   new.append(r)
  preserved &= set(frozen)<=seen
  counts=dict(article_rows_retained=c.execute('SELECT count(*) FROM articles').fetchone()[0],currently_qualified_article_rows=len(q),whole_text_versions=c.execute('SELECT count(*) FROM article_versions').fetchone()[0],separate_pending_or_component_records=c.execute('SELECT count(*) FROM evidence').fetchone()[0],reclassified_retained_article_rows=c.execute('SELECT count(*) FROM article_dispositions').fetchone()[0],baseline_metadata_rows=c.execute('SELECT count(*) FROM baseline').fetchone()[0])
  old_articles=c.execute('SELECT count(*) FROM articles WHERE first_loaded_at<=?',(snap['at_utc'],)).fetchone()[0];old_versions=c.execute('SELECT count(*) FROM article_versions WHERE loaded_at<=?',(snap['at_utc'],)).fetchone()[0]
  disp={r['article_id']:r['status'] for r in c.execute('SELECT article_id,status FROM article_dispositions')}
  for row in c.execute('SELECT * FROM evidence WHERE loaded_at>?',(snap['at_utc'],)):
   r=json.loads(row['metadata_json']);pending.append(dict(evidence_id=row['evidence_id'],source_id=row['source_id'],source_url=row['source_url'],status=row['status'],publication_date=r.get('publication_date'),raw_reference=r.get('raw_reference'),body_reference=r.get('body_reference'),loaded_at_utc=row['loaded_at']))
  integrity=c.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall();latest_ok=c.execute('SELECT count(*) FROM articles a LEFT JOIN article_versions v ON v.version_id=a.latest_version_id WHERE v.version_id IS NULL OR v.article_id<>a.article_id').fetchone()[0]==0;c.close()
 combined=baseline+new;fields=list(dict.fromkeys(list(baseline[0])+[k for r in new for k in r]));write_csv('ADDITIONAL_ARTICLE_REGISTER.csv',new,fields);write_csv('CUMULATIVE_ARTICLE_REGISTER.csv',combined,fields)
 write_csv('NEW_PENDING_OR_COMPONENT_REGISTER.csv',pending,['evidence_id','source_id','source_url','status','publication_date','raw_reference','body_reference','loaded_at_utc'])
 families=collections.defaultdict(set);ids=collections.defaultdict(set)
 for r in combined:
  for g in ['pooled',r['stratum']]:families[g,r['publication_date'][:7]].add(r['work_family_id']);ids[g,r['publication_date'][:7]].add(r['article_id'])
 coverage={};gaps=[];lf=['month','stratum','complete_native_article_IDs','complete_independent_articles','months_at_minimum_coverage','additional_articles_required','partial_publication_month']
 for geo in ['pooled']+elt.SCOPE['strata']:
  rows=[dict(month=m,stratum=geo,complete_native_article_IDs=len(ids[geo,m]),complete_independent_articles=len(families[geo,m]),months_at_minimum_coverage=len(families[geo,m])>=2,additional_articles_required=max(0,2-len(families[geo,m])),partial_publication_month=m=='2026-09') for m in MONTHS]
  gaps.extend(r for r in rows if not r['months_at_minimum_coverage']);write_csv('coverage/MONTHLY_'+geo.replace('/','_').replace(' ','_')+'.csv',rows,lf)
  coverage[geo]=dict(months_at_minimum_coverage=sum(r['months_at_minimum_coverage'] for r in rows),one_article_months=sum(r['complete_independent_articles']==1 for r in rows),zero_article_months=sum(r['complete_independent_articles']==0 for r in rows),article_count_distribution=dict(collections.Counter(r['complete_independent_articles'] for r in rows)))
 write_csv('RESIDUAL_MONTHS.csv',gaps,lf)
 inventory=collections.Counter((r['source_id'],r['publication_date'][:4]) for r in combined);write_csv('ACQUIRED_SOURCE_YEAR_INVENTORY.csv',[dict(source_id=s,year=y,complete_native_article_IDs=n,archive_population='Unknown; observed acquired originals only') for (s,y),n in sorted(inventory.items())])
 write_csv('RAW_OBJECT_MANIFEST.csv',[{k:r.get(k) for k in ['target_id','source_id','purpose','status','raw_reference','raw_sha256','raw_bytes','raw_encoding','stored_sha256','stored_bytes','partial','finished_at_utc']} for r in requests if r.get('raw_reference')])
 write_csv('NEW_PENDING_TRANSPORT.csv',[dict(target_id=r['target_id'],source_id=r['source_id'],source_url=r['url'],status=r['status'],receipt_reference='receipts/'+r['target_id']+'.json') for r in requests if r['status']!='saved'],['target_id','source_id','source_url','status','receipt_reference'])
 state=elt.state();attempts={g:dict(cumulative_native_article_targets=state['strata'][g]['article'],effective_cumulative_discovery_targets=elt.effective_count(state,g,'discovery'),article_ceiling=6000,discovery_ceiling=1000) for g in elt.SCOPE['strata']}
 write_csv('HOST_STOP_REGISTER.csv',[dict(host=h,stop=json.dumps(v,ensure_ascii=False),scope='Preserved inherited or newly observed access/publisher stop') for h,v in state['access_stops'].items()])
 opp=collections.Counter((r['stratum'],r['planned_lane']) for r in lines(elt.OWN/'OPPORTUNITY_LOG.jsonl'));elt.preparation_save('OPPORTUNITY_SUMMARY.json',dict(at_utc=elt.utc(),planned_recovery_fraction=0.7,counts=[dict(stratum=g,recovery=opp[g,'recovery'],production=opp[g,'production']) for g in elt.SCOPE['strata']],scope='Prospective opportunities including unavailable frames; not article weights or equal realised yields'))
 resource=elt.resource();checks=dict(changed_code_checks=json.loads((elt.OWN/'CHANGED_CODE_CHECK.json').read_text())['all_passed'],SQLite_quick_and_foreign_key_check=integrity,latest_version_mapping=latest_ok,old_2814_article_rows_preserved=old_articles==2814,old_2816_versions_preserved=old_versions==2816,old_qualified_ID_date_body_digest_metadata_preserved=preserved,old_eight_dispositions_preserved=len(old_dispositions)==8 and all(disp.get(a)==s for a,s in old_dispositions.items()),new_TEXT_date_link_sidecar_sizes=body_ok,new_or_inherited_complete_raw_receipt_mapping=raw_ok,print_date_whole_article_mapping=print_ok,six_465_month_ledgers=len(coverage)==6 and len(MONTHS)==465,fixed_cutoff=elt.SCOPE['publication_interval']==['1988-01-01','2026-09-21'],regional_cumulative_ceilings=all(r['cumulative_native_article_targets']<=6000 and r['effective_cumulative_discovery_targets']<=1000 for r in attempts.values()),native_hops_at_most_four=all(n<=4 for n in state.get('native_http_hops',{}).values()),no_in_progress_transport=all(v!='in_progress' for v in state['targets'].values()),ODT_policy_stop_preserved='www.odt.co.nz' in state['access_stops'],InDaily_asset_stop_preserved='assets.indailysa.com.au' in state['access_stops'],no_semantic_or_length_exclusion=all(r.get('semantic_labels_executed') is False and r.get('length_filter_used') is False for r in new),media_cap=resource['cumulative_bytes']<5000000000,writer_exit_verified=True,no_baseline_consolidation_recount=not any(r.get('baseline_TEXT_consolidation') for r in lines(elt.OWN/'TRANSACTION_RECEIPTS.jsonl')))
 dimensions={k:dict(collections.Counter(str(r.get(k) or 'unrecorded') for r in combined)) for k in ['source_id','stratum','source_frame','genre','provenance']}
 summary=dict(at_utc=elt.utc(),status='bounded_coverage_continuation_delivered',publication_interval=elt.SCOPE['publication_interval'],deadline_unchanged=elt.SCOPE['hard_deadline_at_utc'],collection_close=close,baseline_complete_IDs=2806,baseline_pooled_minimum_months=239,additional_qualified_IDs=len(new),additional_source_mix=dict(collections.Counter(r['source_id'] for r in new)),cumulative_selected_complete_IDs=len(combined),whole_TEXT_database_counts=counts,coverage=coverage,cumulative_metadata_dimensions=dimensions,cumulative_attempt_counts=attempts,new_distinct_transport_target_receipts=len(requests),new_HTTP_hops=sum(len(r.get('hops',[])) for r in requests),new_transport_statuses=dict(collections.Counter(r['status'] for r in requests)),new_pending_or_component_records=len(pending),inherited_print_original_articles_recovered=sum(r.get('raw_encoding')=='original_pdf' for r in new),new_print_original_articles_recovered=sum(bool(r.get('historical_original_print')) for r in new),baseline_TEXT_consolidated=0,resource_at_delivery=resource,checks=checks,all_changed_tranche_checks_passed=all(checks.values()),mapping_errors=errors,accepted_pre_append_database_snapshot=old_db,old_body_raw_hash_sweep=False,final_database_hash_once=True,verification_scope='Changed date/identity/body/reference/receipt mapping; one store check and bounded frozen metadata preservation. No universal historical-version, quotation-origin or claim-truth assertion',independence_limit='Native piece identity and known exact-body families; unresolved wire/syndication/mirrored works remain',newspaper_source_limit='Observed archive coverage includes student and advocacy newspapers and digital successor frames. Pooled presence does not certify countries, title populations or each stratum',fear_or_topic_labels_executed=False)
 elt.preparation_save('DELIVERY_SUMMARY.json',summary);table='\n'.join('| '+g+' | '+str(v['months_at_minimum_coverage'])+' | '+str(v['one_article_months'])+' | '+str(v['zero_article_months'])+' |' for g,v in coverage.items())
 report=f'''# Newspaper coverage continuation — 8 October 2026

The human requested continued acquisition with coverage as the priority. This bounded successor began {snap['at_utc']} and retained its absolute deadline {elt.SCOPE['hard_deadline_at_utc']} (8 October 15:39:42 Brisbane). Actual collection closure: {close['reason']}; writer exit was observed. The prior package 26 delivery remains frozen. New derivative artifacts are confined to this successor subtree; the existing newspaper SQLite store was appended by one writer.

This tranche adds **{len(new)} complete independent-piece IDs** beyond the accepted 2,806-ID input; the cumulative qualified register and TEXT store now have **{len(combined)} IDs**. The earlier 141 accepted TEXT consolidations are inherited and are not recounted as new acquisition. Pooled months meeting the recorded two-original-piece floor increased **239 → {coverage['pooled']['months_at_minimum_coverage']} /465**. Third and later eligible pieces were retained. The prospective schedule is 70% recovery and 30% production; it is not a realised article weighting rule.

| Stratum | Months at the floor | One-piece months | Zero-confirmed months |
| --- | ---: | ---: | ---: |
{table}

All six ledgers retain January 1988 through September 2026. Publication eligibility remains 1988-01-01 through 2026-09-21. September is partial; the day cutoff does not establish end-of-day completeness. Zero-confirmed means no qualified original in this observed snapshot, not absence of discourse. Full-period acquisition remains incomplete. Pooled presence does not establish every stratum or complete newspaper archives; recoverable eras, digitisation and access differ by title.

Early-calendar recovery reused already accepted complete The Tech print scans, with visual masthead checks, ordered column coordinates, independent piece boundaries and traced continuations. {summary['inherited_print_original_articles_recovered']} complete pieces were Loaded from inherited originals without a new download. The 1988 scan's old 2 MiB partial stop and later accepted complete download both remain preserved; this was a local object-cap history, not evidence of a publisher refusal. Native OCR spelling and spacing limitations remain explicit. An additional {summary['new_print_original_articles_recovered']} complete print pieces were recovered from newly transferred originals with separately recorded 8 MiB per-object, 36-issue and 256 MiB aggregate ceilings. Unmapped original issues remain pending and do not count as article coverage. Signed columns, editorials and any published letters retain separate genre/author metadata. A published letter records its author's expression within a newspaper publication frame; it does not become journalist emotion or representative public discourse.

Native article IDs, issue/PDF targets, body-transfer targets, discovery charges, HTTP hops, saved originals, pending components and complete TEXT records are separate. Whole-article release requires observed date and original boundary/content mapping. Metadata/index hits do not count as acquired articles. Exact-body copy families are retained; broader syndicated/mirrored-work independence remains unresolved. Registers retain source, stratum, genre, parent, date, retrieval, content-version and provenance metadata. Today's archive body does not universally prove historical-version equality or claim truth. Directness is relative to the recorded newspaper utterance; print originals are archival reproduction.

Inherited publisher/access limits remain. ODT/Allied automation/database prohibitions observed in [platform terms](https://alliedmedia.co.nz/platform-terms-of-use/) dated 23 July 2026 preserve the stopped hosts and pre-stop evidence. InDaily's asset-host 403 remains stopped; accepted retained sitemap links can supply eligible article routes. No stop was bypassed, no new acquisition-parent family was activated and no counters/cap/deadline were reset. The initial print-dispatch exact-stop error, correction, own-writer restart and saved-payload recovery remain in named receipts. All formal Loads were serialised in the existing store.

Final checks passed: **{all(checks.values())}**. The old 2,814 retained article rows, 2,816 versions, 2,806 qualified IDs and eight dispositions are checked through bounded metadata, without rereading or rehashing old raw/body collections. Changed whole-TEXT dates/links/reference sizes and original receipt mappings are checked once. SQLite quick/foreign-key and latest-version checks are performed once after writer exit. One final database hash records this snapshot. Validation is structural acquisition evidence, not universal quotation, historical equivalence or truth verification.

The cumulative cap remains exactly **5,000,000,000 bytes decimal** across the same five disjoint accounting roots, including preceding media. Delivery accounted bytes: **{resource['cumulative_bytes']:,}**; actual free bytes: **{resource['free_bytes']:,}**; headroom after the protected 15 GiB floor, 48 MiB recovery allowance, operation footprint and actual live leases: **{resource['physical_headroom']:,}**. No budget reset, deleted-evidence credit or lease/floor waiver occurred.

Article/issue manifests, six calendar ledgers, residual months, pending and stop registers, transaction/process/restart receipts, original mapping sidecars and final file receipts accompany this delivery. Coordinator controls/PROJECT_LOG, government baseline, hidden reviewer/evaluator code, social-media stores and prior frozen reports were not edited. No new chats, agents, automation, third-party messages or Git actions were used.

These results concern dated source presence and readable original text. Later climate relevance/similarity, validated affect/risk/future-harm association and fear-specific passage attribution remain separate stages. Coverage and volume do not establish emotion prevalence or a comparable three-role fear series.
'''
 elt.preflight(len(report.encode())*2);(elt.OWN/'DELIVERY_REPORT.md').write_text(report);elt.preparation_save('WORKER_COMPLETION.json',dict(at_utc=elt.utc(),status=summary['status'],additional_qualified_IDs=len(new),no_active_background_worker=True,all_changed_tranche_checks_passed=all(checks.values()),control_reconciliation='Coordinator owned; no control edited'))
 paths=[p for p in elt.OWN.rglob('*') if p.is_file() and p.suffix not in ['.gz','.png','.txt'] and 'DELIVERY_FILE_RECEIPTS' not in p.name and '__pycache__' not in p.parts and 'tmp' not in p.relative_to(elt.OWN).parts]
 hashes={str(p.relative_to(elt.OWN)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in paths};hashes[dbkey]=dict(sha256=digest(elt.DB),bytes=elt.DB.stat().st_size)
 elt.preparation_save('DELIVERY_FILE_RECEIPTS.json',dict(at_utc=elt.utc(),files=hashes,raw_body_hash_sweep=False,final_database_hashed_once=True,accepted_pre_append_database_receipt=old_db));print(json.dumps({k:summary[k] for k in ['status','additional_qualified_IDs','cumulative_selected_complete_IDs','all_changed_tranche_checks_passed','coverage']}))
if __name__=='__main__':main()
