"""Synthetic whole-ID advance and missing-context regressions; no DB/HTTP."""
import copy,json
import small_collect as s,transport as t,entities as e

f={'base':'https://example.invalid','chunks':[{'topic':7,'ids':[101,102]}],'topics':[8,9]}
c={'chunk_offset':0,'post_offset':0,'topic_offset':0,'new_pending_chunks':[],'new_topics':[],'kind':'discourse','frame':'fixture'}
url,route,unit=s.job(c,f);assert '101' in url and '102' not in url
rows=[{'native_namespace':'forum_post','native_post_id':'101'}]
s.advance(c,f,{},route,unit,rows);assert c['post_offset']==1 and f['chunks'][0]['ids']==[101,102]
url,route,unit=s.job(c,f);assert '102' in url
s.advance(c,f,{},route,unit,[{'native_namespace':'forum_post','native_post_id':'102'}]);assert c['chunk_offset']==1 and c['post_offset']==0
url,route,unit=s.job(c,f);assert url.endswith('/t/8.json')
s.advance(c,f,{'post_stream':{'posts':[{'id':201}],'stream':[201,202,203]}},route,unit,[])
assert c['topic_offset']==1 and c['new_pending_chunks']==[{'topic':8,'ids':[202,203]}]
url,route,unit=s.job(c,f);assert unit['post_id']==202
data={'post_stream':{'posts':[{'id':101,'topic_id':7,'post_number':2,'created_at':'2001-01-01T00:00:00Z','cooked':'routine neutral text'}]}}
native=e.discourse(data,'fixture','https://example.invalid','unknown');assert len(native)==1 and e.prepare(native[0])['independently_authored_body']==1
assert s.pending_chunk(c,f)[0]['ids']==[202,203]
t.atomic(t.WORK/'CURSOR_REGRESSION.json',{'at_utc':t.utc(),'passed':True,'checks':['reference-only old IDs not mutated','single native ID per request','cursor advance only after durable caller result','whole topic missing ID surplus stays queued','exact post response does not invent missing topic container','neutral complete native text retained'],'database_access':False,'source_requests':0,'runner_sha256':t.sha((t.WORK/'small_collect.py').read_bytes())})
print('cursor regression passed')
