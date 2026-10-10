import pathlib,json,gzip,collections
import elt,broaden,archive_html,native_batches,production
checks=[]
def test(name,condition):assert condition,name;checks.append({'test':name,'passed':True})
q=json.loads((elt.OWN/'queues/militant_uk_archive.json').read_text())[0];broaden.active_ids();rec=elt._receipt(q['saved_request_id']);r,body,status=archive_html.parse(elt.read_payload(rec['raw_reference']),q['source_id'],q['url'])
test('actual1988 Militant article boundary yields complete dated archival text',status=='confirmed_complete' and r['publication_date']=='1988-07-01' and body.endswith('Long live Militant!'))
test('actual delivered date does not replace newspaper publication',r['publication_date']!='1988-06-19' and r['content_version_time'] is None and r['archive_transcription_year']==2007)
manifest=elt.TRANSPORT_REOPENS;old='e17674c95f39d445a4fe3acf';item=manifest[old]
test('expired zeroHTTP batch receives new transport identity preserving native original',elt.transport_target_id(item['source_id'],item['purpose'],item['url'])==item['retry_target_id'] and item['retry_target_id']!=old)
original=elt._receipt(old);test('reopened actual batch has zero response/body and fixed-deadline evidence',not original['hops'] and original['raw_bytes']==0 and original['error']=='fixed_deadline')
test('real recorded source HTTP stop is not reopened',not elt.transport_reopen_allowed('financial_mirror','article','https://www.financialmirror.com/wp-json/wp/v2/posts/2068'))
with elt.LOCK.open('a+b') as lock:
 elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);legacy=elt._R_GLOB_CUMULATIVE();fast=elt.cumulative()
test('exact faster accounting equals inherited file-size accounting under shared lock',fast==legacy)
out=json.loads((elt.OWN/'CHANGED_CHAIN_CHECK.json').read_text());out['checks']+=checks;out['all_passed']=all(r['passed'] for r in out['checks']);out['actual_raw_checks_are_named_source_only']=True;(elt.OWN/'CHANGED_CHAIN_CHECK.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'all_passed':True,'checks':len(out['checks']),'actual_article_date':r['publication_date'],'exact_cumulative_bytes':fast}))
