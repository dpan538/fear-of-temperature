import json,copy,hashlib,urllib.robotparser
import elt,broaden,extract_load,native_batches,native_html
checks=[]
def check(name,condition):
 assert condition,name
 checks.append({'name':name,'passed':True})
for p in elt.OWN.glob('*.py'):compile(p.read_text(),str(p),'exec')
check('All own Python syntax valid',True)
elt.assert_release()
check('Original accepted 16 checks reused; same owner and scope/deadline',json.loads((elt.OWN/'CHANGED_CODE_CHECK.json').read_text())['all_passed'])
check('No article-count quota introduced',elt.SCOPE['article_distinct_target_attempts_per_stratum'] is None)
check('Source and PDF ceilings inherited',elt.SCOPE['max_additional_acquisition_parents_per_stratum']==4 and elt.SCOPE['discovery_distinct_targets_per_stratum']==2000)
def obj(pid,html):return {'id':pid,'link':'https://thebridgevt.org/2014/10/24/item-'+str(pid)+'/','date':'2014-10-24T10:00:00','modified':'2026-09-20T00:00:00','status':'publish','type':'post','title':{'rendered':'Original '+str(pid)},'content':{'rendered':html,'protected':False}}
check('Short native prose retained without length threshold',elt.native_article_unit_status(obj(1,'<div>A brief statement.</div>')) is None)
check('Prose with embedded supporting media retained',elt.native_article_unit_status(obj(1,'<p>Article prose.</p><iframe src="https://example.org/media"></iframe>')) is None)
for html in ['<img src="image.png">','<h2>Heading only</h2>','<iframe src="issue.pdf"></iframe>','<table><tr><td>A table alone</td></tr></table>']:
 check('Original article boundary pending: '+html,elt.native_article_unit_status(obj(1,html)) is not None)
protected=obj(1,'<p>Preview</p>');protected['content']['protected']=True
check('Protected public response pending',elt.native_article_unit_status(protected)=='pending_protected_or_nonpublic_native_body')
profile=next(p for p in broaden.profiles() if p['source_id']=='camden_new_journal');extract_load.ADAPTERS[profile['source_id']]={'title':profile['title'],'country':profile['country'],'stratum':profile['stratum'],'edition':profile['edition'],'frame':profile['source_frame'],'retention_limit':profile['retention_limit']}
r=elt._receipt('16aa647caa52af47e346512b');record,body,status=native_html.parse(elt.read_payload(r['raw_reference']),'camden_new_journal',r['final_url'])
check('Observed Camden whole article has unique displayed date/title/body boundary',status=='confirmed_complete' and record['publication_date']=='2025-05-01' and record['paragraph_count']==47 and len(body)>0)
robot_receipt=elt._receipt('6eb5c9e92bee2da063e23143');robot=urllib.robotparser.RobotFileParser();robot.parse(elt.read_payload(robot_receipt['raw_reference']).decode().splitlines())
check('Declared actual research agent permitted; named GPT restrictions separately preserved',robot.can_fetch('FearOfTemperatureResearch/1.0',profile['root_url']) and not robot.can_fetch('GPTBot',profile['root_url']) and not robot.can_fetch('ChatGPT-User',profile['root_url']))
root=elt._receipt('8f5901b4699bb22084230922');items=native_html.article_targets(elt.read_payload(root['raw_reference']),profile,profile['root_url'],root)
check('HTML index does not manufacture article publication dates',items and all(t['month']=='' for t in items))
# Pure in-memory batch contract check: no network, database write or old corpus body reads.
bridge=next(p for p in broaden.profiles() if p['source_id']=='montpelier_bridge');extract_load.ADAPTERS['montpelier_bridge']={'title':bridge['title'],'country':bridge['country'],'stratum':bridge['stratum'],'edition':bridge['edition'],'frame':bridge['source_frame']}
objects=[obj(i,'<p>Original article '+str(i)+'.</p>') for i in range(1,26)]
queue=[{'source_id':'montpelier_bridge','native_post_id':o['id'],'article_url':o['link'],'url':'https://thebridgevt.org/wp-json/wp/v2/posts/'+str(o['id']),'month':'2014-10','representation':'publisher_wp_article_json'} for o in objects]
state={'strata':{'US':{'article':0,'discovery':0}},'native_http_hops':{},'charged_native_targets':[]};saved={};loaded=[];calls=[]
elt.state=lambda:copy.deepcopy(state)
def save(name,value):
 saved[name]=copy.deepcopy(value)
 if name=='TRANSPORT_STATE.json':state.update(copy.deepcopy(value))
elt.save=save;elt.append=lambda *args:None
broaden._state=lambda:{'montpelier_bridge':{'collection_url':'https://thebridgevt.org/wp-json/wp/v2/posts','schema_receipt':'observed-public-schema'}};broaden._permitted=lambda *args:True
rec={'target_id':'fixture','status':'saved','raw_reference':'fixture.json','raw_sha256':'rawfixture','finished_at_utc':'2026-10-09T03:00:00Z','hops':[{'status':200}]}
def fetch(url,*args,**kwargs):calls.append(url);return rec
elt.fetch=fetch;elt.read_payload=lambda ref:json.dumps(objects).encode();native_batches.status_map=lambda:saved.get('NATIVE_BATCH_UNIT_STATUS.json',{})
# Retain actual new load wrapper and intercept only durable parent to verify per-ID list selection.
elt._receipt=lambda tid:{'target':{'extra':{}}}
def durable(record,body,status):
 loaded.append((record,body,status));return dict(record,load_status=status,body_sha256=hashlib.sha256(body.encode()).hexdigest(),version_id='fixture:'+str(record['source_native_post_id']))
elt._parent_scoped_load=durable
known=set();result=native_batches.acquire('montpelier_bridge',queue,known)
check('One documented transport contains 25 independently mapped complete articles',len(calls)==1 and len(loaded)==25 and result['qualified_native_units']==25 and len({r[0]['article_id'] for r in loaded})==25)
check('Batch article ID/date/body and raw-item selection remain separate',all(r[0]['article_id']=='montpelier_bridge:post:'+str(i) and r[0]['native_batch_item_id']==i and r[0]['publication_date']=='2014-10-24' and r[2]=='confirmed_complete' for i,r in enumerate(loaded,1)))
check('Every participant consumes its own inherited hop budget once',len(state['native_http_hops'])==25 and set(state['native_http_hops'].values())=={1} and state['additional_batch_native_units_requested']['US']==25)
check('Consumed batch IDs cannot trigger single fallback or duplicate replay',native_batches.acquire('montpelier_bridge',queue,known) is None)
# Finish receipt using original preparation writer, not monkeypatched save.
resource=elt.resource(elt.operation_footprint());check('Actual operation capacity and shared active leases reread',min(resource['physical_headroom'],resource['allocation_headroom'])>0)
elt.preparation_save('BATCH_HTML_EXTENSION_CHECK.json',{'at_utc':elt.utc(),'all_passed':True,'checks':checks,'unchanged_start_checks_reused':16,'same_hard_deadline':elt.SCOPE['hard_deadline_at_utc'],'resource':resource,'no_test_HTTP_or_database_write':True,'observed_new_HTML_evidence_checked_once':True})
print(json.dumps({'all_passed':True,'checks':len(checks),'resource':resource}))
