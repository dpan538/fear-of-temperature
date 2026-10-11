"""Named source-era reconciliation and bounded real article operations."""
import csv,json,re,collections,pathlib,datetime as dt
import elt,production,extract_load
from fear_temperature.media_planning.core import Opportunity
W=elt.OWN
EVIDENCE=elt.REPO/'work_packages/M1_source_access/27_newspaper_context_recovery_20261008/control/20261010_source_frame_redesign/MONTH_REPAIR_EVIDENCE.csv'
REPAIR_ROWS=list(csv.DictReader(EVIDENCE.open()))
MONTHS={r['month'] for r in REPAIR_ROWS if json.loads(r['source_id_counts'])=={'green_left':2}}
_baseline_months={r['publication_date'][:7] for r in production.BASELINE if r['source_id'] not in elt.EXCLUDED}
ZEROS={f'{y:04d}-{m:02d}' for y in range(1988,2027) for m in range(1,13) if f'{y:04d}-{m:02d}'<='2026-09'}-_baseline_months
_month_overlay={};_ready={};_replay={};_replay_done=set();_last_dispatch={}

def expected_month(record,receipt):
 original=receipt.get('target',{}).get('extra',{}).get('month')
 if record.get('source_id')!='green_left':return original
 url=elt.canon(record.get('raw_source_url') or record.get('source_url',''))
 entry=_month_overlay.get(url)
 if not entry:return original
 record.update(original_receipt_month_hint=original,expected_month_overlay_version='native-issue-month-v1',expected_month_overlay_reference=str((W/'EXPECTED_MONTH_OVERLAY.json').relative_to(elt.REPO)),expected_month_overlay_evidence=entry,publication_date_not_overridden=True)
 return entry['expected_month']

def replay_allowed(tid):
 return tid in _replay and tid not in _replay_done

def prepare():
 global _month_overlay,_ready,_replay,_replay_done,_last_dispatch
 metadata_paths=[q for root in elt.QUEUE_ROOTS for q in [root/'queues/green_left.json',root/'LOAD_LOG.jsonl'] if q.exists()]
 with elt.LOCK.open('a+b') as lock:
  elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);elt.preflight(4*sum(q.stat().st_size for q in metadata_paths)+32*1024*1024)
 elt.expected_article_month=expected_month;elt.named_saved_replay_allowed=replay_allowed
 issues=json.loads((W/'GL_ISSUE_QUEUE.json').read_text());processed=set(json.loads((W/'GL_ISSUES_PROCESSED.json').read_text()))
 indexed={elt.urlsplit(i['url']).path.rsplit('/',1)[-1]:i for i in issues}
 touched=set(elt.state()['targets']);items=production.targets('green_left')
 _ready=collections.defaultdict(list);_month_overlay={};seen=set()
 for t in items:
  url=elt.canon(t['url']);match=re.match(r'^/(\d{4})/(\d+)/',elt.urlsplit(url).path)
  issue=indexed.get(match[2]) if match else None
  if not issue or issue['publication_date'][:4]!=match[1] or url in seen:continue
  seen.add(url);t=dict(t,month=issue['month']);_ready[issue['month']].append(t)
  _month_overlay[url]=dict(expected_month=issue['month'],dated_issue_url=issue['url'],dated_issue_publication_date=issue['publication_date'],original_issue_processed=issue['url'] in processed,frozen_native_queue_reference=(t.get('native_evidence') or {}).get('frozen_queue_reference'),frozen_native_queue_entry=(t.get('native_evidence') or {}).get('entry_index'),relation='Exact year/issue URL matches dated native locator; article page supplies publication date independently')
 alias_rows=[]
 baseline_ids={r['article_id'] for r in production.BASELINE}
 latest={}
 # Source-specific metadata only. The named affected saved responses are
 # parsed individually later; no old raw/body tree is traversed here.
 for root in elt.QUEUE_ROOTS:
  q=root/'LOAD_LOG.jsonl'
  if not q.exists():continue
  with q.open() as f:
   for line in f:
    if not line.strip():continue
    r=json.loads(line)
    if r.get('source_id')!='green_left':continue
    if r.get('article_id') in baseline_ids and r.get('load_status')=='confirmed_complete':
     urls=sorted(set([r.get('raw_source_url'),r.get('source_url')]+r.get('url_aliases',[]))-{None})
     production.KNOWN.update(elt.canon(u) for u in urls)
     alias_rows.append(dict(article_id=r['article_id'],urls=urls,metadata_log_reference=str(q.relative_to(elt.REPO)),action='Preserve already committed identity; no merge or new Load'))
    if r.get('request_id'):latest[r['request_id']]=r
 for month,targets in _ready.items():
  for t in targets:
   tid=elt.transport_target_id('green_left','article',t['url'])
   if tid not in touched or elt.canon(t['url']) in production.KNOWN:continue
   r=latest.get(tid)
   if not r or r.get('load_status')!='pending_issue_article_date_conflict':continue
   receipt=elt._receipt(tid)
   if receipt.get('status')!='saved' or not receipt.get('raw_reference'):continue
   if r.get('publication_date','')[:7]!=month:continue
   _replay[tid]=dict(source_id='green_left',url=t['url'],original_status=r['load_status'],original_receipt_month_hint=receipt.get('target',{}).get('extra',{}).get('month'),article_page_publication_date=r['publication_date'],expected_month=month,raw_reference=receipt['raw_reference'],raw_sha256=receipt['raw_sha256'],HTTP_replay_allowed=False,reason='Named saved whole article native date agrees with dated URL issue; preserved receipt hint conflicts')
 for entry in json.loads((W/'INTERRUPTED_SAVED_ARTICLE_RECOVERY.json').read_text()) if (W/'INTERRUPTED_SAVED_ARTICLE_RECOVERY.json').exists() else []:
  tid=entry['saved_request_id'];receipt=elt._receipt(tid)
  if elt.canon(entry['url']) in production.KNOWN or tid in latest:continue
  assert receipt['status']=='saved' and receipt['raw_sha256']==entry['raw_sha256'] and receipt['source_id']==entry['source_id']=='green_left'
  assert _month_overlay[elt.canon(entry['url'])]['expected_month']==entry['native_publication_date'][:7]==entry['expected_month']
  _replay[tid]=dict(entry,original_status='own_saved_interrupted_before_Load',original_receipt_month_hint=receipt.get('target',{}).get('extra',{}).get('month'),article_page_publication_date=entry['native_publication_date'])
 if (W/'SAVED_REPLAY_DONE.json').exists():_replay_done=set(json.loads((W/'SAVED_REPLAY_DONE.json').read_text()))
 if (W/'FOCUSED_REAL_LOAD_RESULTS.jsonl').exists():
  with (W/'FOCUSED_REAL_LOAD_RESULTS.jsonl').open() as f:
   for line in f:
    if line.strip():
     r=json.loads(line);_last_dispatch[r['expected_month']]=r['at_utc']
 elt.save('EXPECTED_MONTH_OVERLAY.json',dict(version='native-issue-month-v1',entries=_month_overlay,old_receipts_changed=False,publication_dates_changed=False))
 elt.save('NAMED_SAVED_REPLAY.json',_replay)
 elt.save('COMMITTED_GL_ALIAS_PRESERVATION.json',alias_rows)
 reconciliation=[]
 for month in sorted(MONTHS):
  ts=_ready.get(month,[]);locators=[i for i in issues if i['month']==month]
  reconciliation.append(dict(month=month,dated_locators=len(locators),locators_marked_processed=sum(i['url'] in processed for i in locators),native_queued_URLs=len(ts),committed_alias_URLs=sum(elt.canon(t['url']) in production.KNOWN for t in ts),unattempted_URLs=sum(elt.transport_target_id('green_left','article',t['url']) not in touched and elt.canon(t['url']) not in production.KNOWN for t in ts),named_saved_replay=sum(replay_allowed(elt.transport_target_id('green_left','article',t['url'])) for t in ts),issue_processed_is_body_exhaustion=False))
 elt.save('LEGACY_ISSUE_QUEUE_ID_RECONCILIATION.json',dict(at_utc=elt.utc(),affected_exactly_two_GL_months=len(MONTHS),rows=reconciliation,source_URLs_are_candidates_not_complete_articles=True,old_flags_counters_and_receipts_preserved=True))
 routes=[]
 for month in sorted(ZEROS):
  locators=[i for i in issues if i['month']==month]
  conventional=['limerick_post','falls_church_news_press','galway_advertiser','camden_new_journal'] if month>='2007-01' else (['newtown_bee'] if month>='1997-01' else [])
  routes.append(dict(month=month,green_left_dated_locators=locators,queued_GL_URLs=len(_ready.get(month,[])),conventional_source_routes=conventional,opening_historical_route='Trove Canberra Times official dated HTML access/retention preparation; Workers Advocate named pending boundaries preserved' if month<'1991-01' else None,status='native_body_ready' if _ready.get(month) else ('native_issue_ready' if locators else 'conventional_or_early_route_preparation'),no_topic_or_fear_filter=True))
 elt.save('MISSING_MONTH_ROUTE_LEDGER.json',dict(at_utc=elt.utc(),months=routes,not_a_count_or_completeness_gate=True))
 return reconciliation

def options(aged,reserved_urls=None):
 st=elt.state();touched=set(st['targets']);options=[];payload={};years=collections.defaultdict(dict)
 for month,items in sorted(_ready.items()):
  if month not in MONTHS|ZEROS:continue # Generic body fallback covers other exact dated issues.
  candidates=production.eligible(items,production.KNOWN,touched,{},'AU','historical_native')
  if reserved_urls:candidates=[t for t in candidates if elt.canon(t['url']) not in reserved_urls]
  if not candidates:continue
  years[month[:4]][month]=candidates
 for year,months in years.items():
  month=min(months,key=lambda m:(_last_dispatch.get(m,''),m));key='focused_gl:'+year
  priority=0 if month in ZEROS else 1
  options.append(Opportunity(key,'named_legacy_source_era','green_left',month,month,'Ready year frontier rotates observed month routes by last dispatch; no body quota',wait_rounds=aged[key],need_priority=priority))
  payload[key]=months[month]
 return options,payload

def acquire(target):
 tid=elt.transport_target_id('green_left','article',target['url']);saved=replay_allowed(tid)
 if saved:
  receipt=elt._receipt(tid);assert receipt['status']=='saved' and receipt['raw_reference']==_replay[tid]['raw_reference']
 result=extract_load.acquire(target)
 if result:
  _last_dispatch[target['month']]=elt.utc()
  if result.get('load_status') in ['confirmed_complete','already_retained_identity']:production.KNOWN.add(elt.canon(result['source_url']))
  elt.append('FOCUSED_REAL_LOAD_RESULTS.jsonl',dict(at_utc=elt.utc(),target_url=target['url'],expected_month=target['month'],publication_date=result.get('publication_date'),article_id=result.get('article_id'),load_status=result.get('load_status'),request_id=tid,saved_response_replay=saved,new_HTTP_requested=not saved,issue_directory_reset=False))
  if saved:
   _replay_done.add(tid);elt.save('SAVED_REPLAY_DONE.json',sorted(_replay_done))
 return result

def acquire_batch(targets,operation_bound=8):
 """Bound an operation; each original article keeps its own checks and Load."""
 results=[]
 for target in targets[:operation_bound]:
  # Re-evaluate committed/touched state before each article. An interruption
  # does not pre-mark the rest of this bounded list as requested or exhausted.
  if not production.eligible([target],production.KNOWN,set(elt.state()['targets']),{},'AU','historical_native'):continue
  results.append(acquire(target))
 return results

def snapshot():
 new={}
 with (W/'LOAD_LOG.jsonl').open() as f:
  for line in f:
   if line.strip():
    r=json.loads(line)
    if r.get('load_status')=='confirmed_complete':new[r['article_id']]=r
 baseline_ids={r['article_id'] for r in production.BASELINE}
 structural_path=W/'DERIVED_STRUCTURAL_UNIT_DISPOSITIONS.json'
 structural_ids=set(json.loads(structural_path.read_text())['units']) if structural_path.exists() else set()
 new={a:r for a,r in new.items() if a not in baseline_ids and a not in structural_ids}
 supplementary={a:r for a,r in new.items() if r.get('analytical_subframe')=='newspaper_supplement_archive'}
 new={a:r for a,r in new.items() if a not in supplementary}
 gl=collections.Counter(r['publication_date'][:7] for r in new.values() if r['source_id']=='green_left' and r['publication_date'][:7] in MONTHS)
 sources={r['source_id'] for r in production.BASELINE}
 return dict(current_newspaper_new_IDs=len(new),separate_supplementary_new_IDs=len(supplementary),separate_supplementary_month_counts=dict(collections.Counter(r['publication_date'][:7] for r in supplementary.values())),regular_frame_empty_months_not_closed_by_supplementary_editions=True,legacy_GL_affected_months=len(MONTHS),named_legacy_new_IDs=sum(gl.values()),named_legacy_month_new_IDs=dict(gl),named_saved_replay_inspected=len(_replay_done),named_saved_replay_pending=len(set(_replay)-_replay_done),newly_present_baseline_empty_months=sorted({r['publication_date'][:7] for r in new.values()}&ZEROS),remaining_baseline_empty_months=sorted(ZEROS-{r['publication_date'][:7] for r in new.values()}),new_contributing_title_ids=sorted({r['source_id'] for r in new.values()}-sources),source_year_new_IDs=dict(collections.Counter(r['source_id']+'|'+r['publication_date'][:4] for r in new.values())),source50_is_development_goal_only=True,counts_not_runtime_gates=True)

def add_candidates(issue,items,receipt):
 """Extend the named ready frontier without re-reading old raw or resetting flags."""
 assert issue['month']==issue['publication_date'][:7] and elt.eligible(issue['publication_date'])
 seen={elt.canon(t['url']) for t in _ready.get(issue['month'],[])}
 for t in items:
  url=elt.canon(t['url']);match=re.match(r'^/(\d{4})/(\d+)/',elt.urlsplit(url).path)
  assert match and match[1]==issue['publication_date'][:4] and match[2]==issue['url'].rsplit('/',1)[-1]
  if url not in seen:_ready.setdefault(issue['month'],[]).append(dict(t));seen.add(url)
  _month_overlay[url]=dict(expected_month=issue['month'],dated_issue_url=issue['url'],dated_issue_publication_date=issue['publication_date'],named_issue_reconciliation_receipt=receipt['target_id'],relation='Exact path year/issue relation; article supplies publication date independently',original_issue_processed=True)
 elt.save('EXPECTED_MONTH_OVERLAY.json',dict(version='native-issue-month-v1',entries=_month_overlay,old_receipts_changed=False,publication_dates_changed=False))
