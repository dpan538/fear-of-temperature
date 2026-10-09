import json,copy
import elt,broaden,production,native_batches,extract_load
elt.assert_release();checks=[]
def check(name,value):assert value,name;checks.append({'name':name,'passed':True})
for name in ['production.py','native_batches.py']:compile((elt.OWN/name).read_text(),name,'exec')
check('Existing 16 startup and19 batch/HTML checks reused',all(json.loads((elt.OWN/name).read_text())['all_passed'] for name in ['CHANGED_CODE_CHECK.json','BATCH_HTML_EXTENSION_CHECK.json']))
actual_state=broaden._state
broaden._state=lambda:{'camden_new_journal':{'stage':'native_xml'}}
check('Observed HTML archive routes prioritized before undated current bodies',production.public_html_frontier_needs_discovery('camden_new_journal'))
broaden._state=lambda:{'camden_new_journal':{'stage':'observed_public_frontier_consumed'}}
check('Observed public frontier end releases queued bodies without claiming archive completeness',not production.public_html_frontier_needs_discovery('camden_new_journal'))
check('Unrelated approved public WP production unchanged',not production.public_html_frontier_needs_discovery('montpelier_bridge'))
broaden._state=actual_state
resource=elt.preflight(elt.operation_footprint())
# Pure recovery fixture verifies already committed identity plus one untouched saved item, no HTTP.
profile=next(p for p in broaden.profiles() if p['source_id']=='montpelier_bridge');extract_load.ADAPTERS[profile['source_id']]={'title':profile['title'],'stratum':profile['stratum'],'country':profile['country'],'edition':profile['edition'],'frame':profile['source_frame']}
objects=[{'id':i,'link':'https://thebridgevt.org/2014/10/24/fixture-'+str(i)+'/','date':'2014-10-24T00:00:00','modified':'2026-09-20T00:00:00','status':'publish','type':'post','title':{'rendered':'Article '+str(i)},'content':{'rendered':'<p>Short original prose '+str(i)+'.</p>','protected':False}} for i in [1,2]]
targets=[{'native_post_id':o['id'],'article_url':o['link'],'url':'https://thebridgevt.org/wp-json/wp/v2/posts/'+str(o['id']),'month':'2014-10'} for o in objects];statuses={'montpelier_bridge:post:'+str(i):{'status':'saved_batch_item_Load_pending','request_id':'fixture'} for i in [1,2]};saved={};loaded=[]
native_batches.status_map=lambda:copy.deepcopy(statuses);broaden.active_ids=lambda *args:['montpelier_bridge'];elt._receipt=lambda tid:{'target_id':'fixture','source_id':'montpelier_bridge','status':'saved','raw_reference':'fixture.json','raw_sha256':'fixture','finished_at_utc':'2026-10-09T03:00:00Z','target':{'extra':{}}};elt.read_payload=lambda ref:json.dumps(objects).encode();elt.fetch=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('Recovery must not perform HTTP'));elt.save=lambda name,value:saved.update({name:copy.deepcopy(value)});elt.append=lambda *args:None
elt._parent_scoped_load=lambda record,body,status:(loaded.append(record) or dict(record,load_status=status,body_sha256='fixture',version_id='fixture:2'))
known={elt.canon(objects[0]['link'])};processed=native_batches.resume_saved(known,lambda sid:targets)
check('Saved batch recovery skips already committed identity and loads remaining whole item once',processed==1 and len(loaded)==1 and loaded[0]['article_id']=='montpelier_bridge:post:2' and len(known)==2)
check('Recovery records preserved source/raw/native mapping without a new HTTP target',saved['NATIVE_BATCH_UNIT_STATUS.json']['montpelier_bridge:post:2']['saved_batch_recovery_without_new_HTTP'])
elt.preparation_save('HTML_FRONTIER_AND_BATCH_RECOVERY_CHECK.json',dict(at_utc=elt.utc(),all_passed=True,checks=checks,reused_start_checks=16,reused_batch_HTML_checks=19,same_deadline=elt.SCOPE['hard_deadline_at_utc'],resource=resource,no_test_HTTP_or_database_write=True))
print(json.dumps({'all_passed':True,'focused_new_checks':len(checks),'deadline_unchanged':elt.SCOPE['hard_deadline_at_utc']}))
