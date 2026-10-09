import json
import elt,broaden
elt.assert_release();checks=[]
def check(name,value):assert value,name;checks.append({'name':name,'passed':True})
for name in ['broaden.py','production.py']:compile((elt.OWN/name).read_text(),name,'exec')
fetch=elt.fetch
elt.fetch=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('Known policy checks must not issue HTTP'))
for path in ['/about-us','/feed','/archive/archive.html','/posts/merging-senior-schools-need-more-cash-union']:
 allowed,policy=broaden.metadata_permission({'url':'https://www.alicespringsnews.com.au'+path,'source_id':'alice_springs_news','stratum':'AU'})
 check('Saved Alice rule prevents later source document '+path,not allowed and policy.get('robots_receipt')=='7172732a8a98cb5357570c33')
allowed,_=broaden.metadata_permission({'url':'https://www.fcnp.com/','source_id':'falls_church_news_press','stratum':'US'});check('Source-specific allowed declared-agent metadata route remains usable',allowed)
allowed,_=broaden.metadata_permission({'url':'https://www.alicespringsnews.com.au/robots.txt','source_id':'alice_springs_news','stratum':'AU'});check('Robots bootstrap itself stays readable without agent impersonation',allowed)
receipt=elt._receipt;elt._receipt=lambda tid:{'target_id':'fixture','status':'http_stop','hops':[{'status':404}]}
allowed,_=broaden.metadata_permission({'url':'https://example.org/terms','source_id':'fixture','stratum':'US'});check('Ordinary missing robots404 retains accepted default treatment',allowed)
elt._receipt=lambda tid:{'target_id':'fixture','status':'http_stop','hops':[{'status':403}]}
allowed,_=broaden.metadata_permission({'url':'https://example.org/terms','source_id':'fixture','stratum':'US'});check('Unavailable or denied robots prevents further source document access',not allowed)
elt._receipt=receipt;elt.fetch=fetch
elt.preparation_save('METADATA_ROBOTS_GUARD_CHECK.json',dict(at_utc=elt.utc(),all_passed=True,checks=checks,reuses_prior_start_body_batch_and_frontier_checks=True,no_test_HTTP_or_database_write=True,same_declared_research_identity='FearOfTemperatureResearch/1.0',same_deadline=elt.SCOPE['hard_deadline_at_utc'],resource=elt.preflight(elt.operation_footprint())))
print(json.dumps({'all_passed':True,'focused_metadata_policy_checks':len(checks),'no_test_HTTP_or_database_write':True}))
