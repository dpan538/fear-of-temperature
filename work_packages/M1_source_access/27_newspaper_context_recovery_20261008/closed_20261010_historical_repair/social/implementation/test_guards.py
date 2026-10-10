"""Isolated successor regression: no live source requests or corpus store."""
import contextlib,datetime as dt,json,tempfile,urllib.request,time
from pathlib import Path
import transport as t,collect as c
checks=[]
assert t.below_optional_limit(1109,None) and t.below_optional_limit(999999,None)
assert t.within_optional_limit(51672,None) and t.within_optional_limit(1000000,None)
assert not t.below_optional_limit(200,200) and not t.within_optional_limit(2001,2000)
checks += ['null_request_cap_not_zero_or_substitute','beyond_51671_native_objects_allowed','numeric_provider_bounds_still_enforced']
front={'source':'se_earthscience','kind':'se_questions','year':2020,'page':25,'context_queue':[],'frame':'fixture','status':'active'}
c.advance(front,{'items':[{'question_id':1,'creation_date':1600000000}],'has_more':True},'se_questions')
assert front['status']=='active' and front['page']==1 and front['partition_from']==1600000000
front['context_queue']=[]
url,route=c.job(front);assert 'fromdate=1600000000' in url
checks.append('provider_25_page_limit_repartitions_chronology_inclusively')
front={'source':'se_sustainability','kind':'se_questions','year':2026,'page':1,'context_queue':[],'frame':'fixture','status':'active'}
c.advance(front,{'items':[{'question_id':7,'creation_date':1780000000}],'has_more':False},'se_questions')
assert front['questions_exhausted'] and front['status']=='active' and len(front['context_queue'])==2
url,route=c.job(front);assert '/questions/7/answers?' in url
c.advance(front,{'items':[],'has_more':False},'se_context');assert front['status']=='active'
c.advance(front,{'items':[],'has_more':False},'se_context');assert front['status']=='native_frontier_exhausted'
checks.append('final_eligible_question_page_drains_all_child_context_before_exhaustion')
front={'source':'bluesky','kind':'bluesky','cursor':'a','status':'active'}
c.advance(front,{'cursor':'b'},'bluesky');assert front['status']=='active' and front['cursor']=='b'
c.advance(front,{'cursor':'b'},'bluesky');assert front['status']=='native_author_feed_exhausted'
checks += ['real_advancing_native_cursor_continues','nonadvancing_native_cursor_evidenced_stop']
# Parent-specific documented comment routes preserve provider paging boundaries.
with tempfile.TemporaryDirectory(dir=t.WORK) as fixture_dir:
 saved_work=t.WORK;t.WORK=Path(fixture_dir)
 front={'source':'lemmy_nz','base':'https://lemmy.nz','kind':'lemmy_comments','parent_queue':['1','2'],'page':1,'status':'active'}
 url,route=c.job(front);assert 'post_id=1' in url and 'type_=Local' in url and 'limit=50' in url
 c.advance(front,{'comments':[]},route);assert front['parent_queue']==['2'] and front['page']==1 and front['status']=='active'
 checks.append('documented_parent_comment_route_and_native_empty_context_end')
 front['page']=100;c.advance(front,{'comments':[{'comment':{'id':5}}]},route)
 assert not front['parent_queue'] and front['status']=='native_parent_context_catalog_drained'
 assert 'provider_parent_page_100_bound' in (t.WORK/'PARENT_CONTEXT_ROUTE_LIMITS.jsonl').read_text()
 checks.append('parent_specific_provider_page_bound_never_issues_page_101')
 t.WORK=saved_work
old_work=t.WORK;old_release=t.release;old_shared=t.shared;old_builder=urllib.request.build_opener
class Response:
 status=200;headers={'Content-Type':'application/json'}
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self,n):return b'{"items": [], "quota_remaining": 0, "backoff": 3}'
class Opener:
 def open(self,*args,**kw):return Response()
@contextlib.contextmanager
def lock(*args,**kw):yield {}
with tempfile.TemporaryDirectory(dir=old_work) as d:
 t.WORK=Path(d);(t.WORK/'receipts').mkdir()
 t.atomic(t.WORK/'STATE.json',dict(requests=5109,hosts={},attempts={},blocked_hosts={},returned_object_ids=[],object_ids=[]))
 t.atomic(t.WORK/'source_registry.json',[dict(source_id='se_test',collection_retention='permitted',api_documentation=['fixture'])])
 t.release=lambda **kw:dict(default_raw_object_cap_bytes=2097152,max_http_requests_including_access_and_policy_probes=None,hard_deadline_at_utc=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),minimum_host_spacing_seconds=0)
 t.shared=lock;urllib.request.build_opener=lambda *a,**kw:Opener()
 rec=t.fetch('https://api.stackexchange.com/2.3/questions?site=test','se_test','content')
 assert rec['status']=='saved' and t.state()['requests']==5110
 assert t.state()['blocked_hosts']['api.stackexchange.com']['reason']=='quota_exhausted'
 assert t.state()['backoff_methods']
 checks += ['transport_charges_beyond_old_request_ceiling','provider_quota_and_backoff_preserved']
 try:t.fetch('https://api.stackexchange.com/2.3/questions?site=other','se_test','content')
 except t.Stop as exc:assert 'preserved_host_stop' in str(exc)
 else:raise AssertionError('provider stop bypassed')
 checks.append('no_quota_bypass_retry')
 proof=t.WORK/'OWN_CORRECTION.json';proof.write_text('explicit owner fixture correction')
 url='https://public.example/own-interrupted-native';key=t.sha(('se_test|content|'+url).encode())[:24]
 st=t.state();st['attempts'][key]='interrupted_transport_stop';t.persist_state(st)
 t.atomic(t.WORK/'receipts'/f'{key}.json',{'request_id':key,'status':'interrupted_transport_stop','owner_thread_id':t.OWNER,'owner_runtime_correction_reference':proof.name,'owner_runtime_correction_sha256':t.sha(proof.read_bytes())})
 before_requests=t.state()['requests'];rec=t.fetch(url,'se_test','content');again=t.fetch(url,'se_test','content')
 assert rec['status']=='saved' and rec['request_id']==again['request_id'] and t.state()['requests']==before_requests+1
 assert t.read_json(t.WORK/'receipts'/f'{key}.json')['status']=='interrupted_transport_stop'
 checks.append('owner_interruption_recovery_digest_bound_charged_once_original_preserved')
 url='https://public.example/genuine-source-timeout';key=t.sha(('se_test|content|'+url).encode())[:24];st=t.state();st['attempts'][key]='transport_stop';t.persist_state(st)
 t.atomic(t.WORK/'receipts'/f'{key}.json',{'request_id':key,'status':'transport_stop','error':'source timeout'})
 before_requests=t.state()['requests']
 try:t.fetch(url,'se_test','content')
 except t.Stop as exc:assert str(exc)=='preserved_attempt_stop '+key
 else:raise AssertionError('source timeout incorrectly retried')
 assert t.state()['requests']==before_requests
 checks.append('genuine_source_stop_not_reclassified_as_owner_recovery')
 class SlowOpener:
  def open(self,*args,**kw):time.sleep(.3);return Response()
 urllib.request.build_opener=lambda *a,**kw:SlowOpener()
 t.release=lambda **kw:dict(default_raw_object_cap_bytes=2097152,max_http_requests_including_access_and_policy_probes=None,hard_deadline_at_utc=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=.05)).isoformat(),minimum_host_spacing_seconds=0)
 before=time.monotonic();rec=t.fetch('https://public.example/test-duration','se_test','content')
 assert rec['status']=='transport_stop' and 'total_native_request_duration_bound' in rec['error'] and time.monotonic()-before<.25
 checks.append('total_http_duration_including_trickle_bounded_by_remaining_deadline')
 # The real shared-lock wrapper rechecks the release after lock acquisition.
 calls=[0]
 def lock_release(**kw):
  calls[0]+=1
  if calls[0]>1:raise t.Stop('fixed_deadline')
  return {'shared_heavy_io_lock':str(t.WORK/'fixture-heavy.lock')}
 t.release=lock_release;t.shared=old_shared
 try:
  with t.shared(0):raise AssertionError('expired lock wait allowed operation')
 except t.Stop as exc:assert str(exc)=='fixed_deadline'
 checks.append('deadline_rechecked_after_shared_lock_wait')
 t.shared=lock
 # Compact state references accepted identity metadata, journals only new keys.
 t._state_cache.clear()
 inherited=t.WORK/'inherited.json';t.atomic(inherited,dict(requests=1109,hosts={},attempts={'old':'saved'},blocked_hosts={},object_ids=['id'],returned_object_ids=['source|post|'+str(i) for i in range(51671)]))
 t.atomic(t.WORK/'STATE.json',dict(inherited_state_reference=str(inherited),requests=1109,attempts={}))
 st=t.state();st['returned_object_ids'].append('new|post|51672');st['requests']=1110;t.persist_state(st)
 assert (t.WORK/'STATE.json').stat().st_size<1000
 t._state_cache.clear();assert len(t.state()['returned_object_ids'])==51672 and t.state()['requests']==1110
 checks.append('compact_restart_preserves_inherited_and_new_counter_keys')
t.WORK=old_work;t.release=old_release;t.shared=old_shared;urllib.request.build_opener=old_builder;t._state_cache.clear()
t.atomic(t.WORK/'GUARD_REGRESSION.json',dict(at_utc=t.utc(),passed=True,checks=checks,synthetic_only=True))
print(json.dumps({'passed':True,'checks':len(checks),'live_requests':0}))
