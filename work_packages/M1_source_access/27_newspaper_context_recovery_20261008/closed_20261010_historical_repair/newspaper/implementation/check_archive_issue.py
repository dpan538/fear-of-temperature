import sys,json
import elt,archive_issues
checks=[]
def test(name,x):assert x,name;checks.append({'test':name,'passed':True})
r=next(json.loads(x) for x in (elt.OWN/'SOURCE_PREPARATION_RESULTS.jsonl').read_text().splitlines() if json.loads(x)['job_id']=='wa_native_1988_issue');rec=elt._receipt(r['receipt_reference'].split('/')[-1].removesuffix('.json'));raw=elt.read_payload(rec['raw_reference']);p=archive_issues.parse_issue(raw,r['url'],'1988-02-01');by={u['native_article_anchor']:u for u in p['units']}
test('actual native1988 issue metadata and45 named units retained independently of issue container',p['publication_date']=='1988-02-01' and len(by)==45 and p['raw_issue_is_container_not_article'])
test('actual missing end-navigation remains pending without forcing article completeness',by['article2932']['status']=='pending_native_article_boundary' and not by['article2932']['original_native_terminator_verified'])
test('actual short article stops before following Strikes section header',by['article2931']['status']=='confirmed_complete' and 'Strikes and workplace news' not in by['article2931']['body'] and 'UAW and GM bosses' not in by['article2931']['body'])
test('index date conflict cannot force publication into2026 or admit an unverified original',archive_issues.parse_issue(raw,r['url'],'2026-02-01')['units'][0]['status']=='pending_native_issue_index_masthead_date_conflict')
queue_fn,state_fn=archive_issues.issue_queue,archive_issues.issue_state
try:
 archive_issues.issue_queue=lambda:[{'url':r['url'],'publication_date_hint':'1988-02-01'}]
 archive_issues.issue_state=lambda:{r['url']:{'stage':'confirmed_native_issue_metadata','units':{'article2924':{},'article2925':{}}}}
 test('two loaded native articles do not complete an issue or consume its remaining whole-article queue',len(archive_issues.available())==1)
finally:archive_issues.issue_queue,archive_issues.issue_state=queue_fn,state_fn
out=json.loads((elt.OWN/'CHANGED_CHAIN_CHECK.json').read_text());out['checks']+=checks;out['all_passed']=all(c['passed'] for c in out['checks']);elt.preparation_save('CHANGED_CHAIN_CHECK.json',out);print(json.dumps({'all_passed':True,'checks':len(out['checks']),'actual_native_units':len(by),'statuses':{s:sum(u['status']==s for u in p['units']) for s in set(u['status'] for u in p['units'])}}))
