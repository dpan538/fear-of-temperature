"""Nine named processed issue locators without article queues; old flags retained."""
import json,re,collections
import elt,production,focused_repair
from green_left_issue_candidates import issue_candidates
from fear_temperature.media_planning.core import Opportunity
FILE='NAMED_GL_ISSUE_ROUTE_STATE.json'

def prepare():
 p=elt.OWN/FILE
 if p.exists():return
 issues=json.loads((elt.OWN/'GL_ISSUE_QUEUE.json').read_text())
 flags=set(json.loads((elt.OWN/'GL_ISSUES_PROCESSED.json').read_text()))
 rows={i['url']:dict(issue=i,phase='named_directory_reconciliation',original_processed_flag=i['url'] in flags,body_exhaustion=False) for i in issues if i['month'] in {'1999-09','1999-10'} and re.fullmatch(r'https://www.greenleft.org.au/issue/(37[4-9]|38[0-2])',i['url'])}
 assert len(rows)==9
 elt.save(FILE,rows)

def options(aged):
 rows=json.loads((elt.OWN/FILE).read_text());groups=collections.defaultdict(list)
 for url,row in rows.items():
  if row['phase']=='named_directory_reconciliation':groups[row['issue']['month']].append(row)
 ops=[];payload={}
 for month,items in groups.items():
  issue=min(items,key=lambda r:r['issue']['publication_date'])['issue'];key='focused_issue:'+month
  ops.append(Opportunity(key,'named_missing_issue_reconciliation','green_left',month,month,'Named processed issue374–382 has no path-matched article queue; original flags preserved',wait_rounds=aged[key],need_priority=0));payload[key]=issue
 return ops,payload

def perform(issue):
 rows=json.loads((elt.OWN/FILE).read_text());row=rows[issue['url']]
 assert row['phase']=='named_directory_reconciliation'
 flags_before=(elt.OWN/'GL_ISSUES_PROCESSED.json').read_bytes()
 rec=elt.fetch(issue['url'],'green_left','AU','discovery',{'named_processed_without_article_queue':True,'dated_issue_locator':issue,'no_blanket_reset':True})
 row.update(at_utc=elt.utc(),transport_status=rec['status'],receipt_id=rec.get('target_id'),raw_reference=rec.get('raw_reference'),raw_sha256=rec.get('raw_sha256'),original_processed_flag_changed=False)
 if rec['status']!='saved':row.update(phase='transport_unavailable',HTTP_success_is_not_directory_success=True)
 else:
  result=issue_candidates(elt.read_payload(rec['raw_reference']),issue['url']);items=[];pending=[]
  for candidate in result['candidates']:
   path=re.match(r'^/(\d{4})/(\d+)/',elt.urlsplit(candidate['url']).path)
   if candidate['issue_relation']!='path_issue_matches' or not path or path[1]!=issue['publication_date'][:4]:pending.append(candidate);continue
   items.append(dict(source_id='green_left',url=candidate['url'],month=issue['month'],native_evidence=dict(title=candidate['title'],dated_native_issue=issue,named_issue_reconciliation_receipt=rec.get('target_id'),native_issue_relation=candidate['issue_relation'],publication_date_assignment='Pending independent article page date, locator supplies validation only')))
  production.queue('green_left',items);focused_repair.add_candidates(issue,items,rec)
  row.update(phase='native_article_candidates_ready' if items else ('observed_empty' if result['status']=='observed_empty_issue_directory' else 'pending_identity_or_year_issue_relation'),parser_status=result['status'],queued_path_year_matched_candidates=len(items),pending_candidates=pending,whole_archive_exhaustion=False)
 assert (elt.OWN/'GL_ISSUES_PROCESSED.json').read_bytes()==flags_before
 elt.append('NAMED_GL_ISSUE_RECONCILIATION_RESULTS.jsonl',dict(issue_url=issue['url'],**row));elt.save(FILE,rows)
 return row
