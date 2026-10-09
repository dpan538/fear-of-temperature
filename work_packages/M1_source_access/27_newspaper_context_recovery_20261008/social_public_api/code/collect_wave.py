"""Released wave: policy-cleared forums first, then dated specialist Q&A.

This bounded frame is not an archive census or topic query. Resume reuses saved
responses; every genuinely new request is charged and immediately Loaded.
"""
import datetime as dt
import json
import urllib.parse
import social_elt as e

def _get_and_load(url,sid):
    r=e.fetch(url,sid,'content')
    if r['status']!='saved':
        print(json.dumps({'source':sid,'request_id':r['request_id'],'status':r['status']}),flush=True);return None
    d=e.json_payload(r)
    previous=[json.loads(x) for x in (e.WORK/'LOADS.jsonl').read_text().splitlines()] if (e.WORK/'LOADS.jsonl').exists() else []
    if any(x['request_id']==r['request_id'] and x['eligible_records']>0 for x in previous):return d
    if sid=='python_discourse':
        rows,dispositions=e.discourse_records(d,sid)
        with e.shared(65536):e.atomic(e.WORK/'receipts'/(r['request_id']+'.dispositions.json'),{'request_id':r['request_id'],'dispositions':dispositions})
    else:rows=e.stackexchange_records(d,sid)
    result=e.load(rows,r)
    print(json.dumps({'source':sid,'request_id':r['request_id'],'returned':r.get('native_objects_returned',len(rows)),**result}),flush=True)
    return d

def get_and_load(url,sid):
    try:return _get_and_load(url,sid)
    except Exception as error:
        reason=str(error)
        if isinstance(error,e.Stop) and any(reason.startswith(x) for x in ('fixed_deadline','resource_stop','request_ceiling','returned_native_object_ceiling','object_ceiling','owner_','scope_digest','active_social_lease')):raise
        with e.shared(65536):e.append(e.WORK/'LANE_FAILURES.jsonl',{'at_utc':e.utc(),'source_id':sid,'url':url,'reason':type(error).__name__+': '+reason,'durable_successes_preserved':True})
        print(json.dumps({'source':sid,'route_status':'preserved_lane_failure','reason':reason}),flush=True)
        return None

def run():
    # Native chronological index prefixes are source-native selection evidence.
    # Index excerpts are not independently retained posts.
    frame=e.read_json(e.WORK/'FORUM_FRAME.json')
    index=e.read_json(e.WORK/'receipts'/(frame['index_request_id']+'.json'))
    posts=e.json_payload(index)['latest_posts']
    topics=list(dict.fromkeys(p['topic_id'] for p in posts))[:10]
    with e.shared(65536):
        st=e.state();st['returned_object_ids']=sorted(set(st.get('returned_object_ids',[]))|{'python_discourse|forum_post|'+str(p['id']) for p in posts});e.atomic(e.WORK/'STATE.json',st)
        e.atomic(e.WORK/'SOURCE_FRAME.json',dict(forum_native_prefix_before_ID=1000,forum_topic_IDs=topics,QA_selection='First 30 questions by native creation order in each calendar year from source beta-era through fixed cutoff; native questions not filtered by topic. Then creation-ordered answers/comments to selected questions.',no_semantic_filter=True))
    for tid in topics:
        get_and_load(f'https://discuss.python.org/t/{tid}.json','python_discourse')
    cutoff=int(dt.datetime(2026,9,22,tzinfo=dt.timezone.utc).timestamp())-1
    for site,start in [('sustainability',2013),('earthscience',2014)]:
        sid='se_'+site;selected=[]
        for year in range(start,2027):
            begin=int(dt.datetime(year,1,1,tzinfo=dt.timezone.utc).timestamp())
            end=min(cutoff,int(dt.datetime(year+1,1,1,tzinfo=dt.timezone.utc).timestamp())-1)
            params=dict(site=site,pagesize=30,order='asc',sort='creation',fromdate=begin,todate=end,filter='withbody',page=1)
            d=get_and_load('https://api.stackexchange.com/2.3/questions?'+urllib.parse.urlencode(params),sid)
            if d:selected.extend(x['question_id'] for x in d.get('items',[]))
        # Explicit partial context cohort; complete native bodies remain units.
        ids=';'.join(map(str,selected[:50]))
        if ids:
            for suffix in ['answers','comments']:
                params=dict(site=site,pagesize=100,order='asc',sort='creation',todate=cutoff,filter=e.read_json(e.WORK/'STACK_FILTER.json')['filter'],page=1)
                get_and_load(f'https://api.stackexchange.com/2.3/questions/{ids}/{suffix}?'+urllib.parse.urlencode(params),sid)
    print(json.dumps({'wave_status':'completed_bounded_source_frame','requests_charged':e.state()['requests'],'loaded_distinct':len(e.state()['object_ids']),'returned_distinct':len(e.state().get('returned_object_ids',[]))}),flush=True)

if __name__=='__main__':
    with e.writer():run()
