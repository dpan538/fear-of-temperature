"""Charge every visible discovery operation and known redirect; do not invent hidden hops."""
import collections,datetime as dt,json
from transport import OWN,read_state,save_state

def main():
    counts=collections.defaultdict(lambda:dict(metadata=0,search=0,body=0))
    for path in (OWN/'sources/DISCOVERY_REQUESTS.jsonl',OWN/'sources/POLICY_REQUESTS.jsonl'):
        if not path.exists():continue
        for line in path.read_text().splitlines():
            r=json.loads(line);title=r.get('title',r.get('source_id'))
            counts[title]['metadata']+=1
            counts[title]['search']+=r.get('method')=='search'
    for path in (OWN/'requests').glob('*.json'):
        r=json.loads(path.read_text()); title=r['source_id']
        # A connection attempt is charged even when no response/hop is received.
        attempts=r.get('charged_attempts',len(r.get('hops',[])))
        counts[title]['metadata' if r['purpose']!='article' else 'body']+=attempts
    state=read_state()
    registry=OWN/'sources/SOURCE_REGISTRY_EFFECTIVE.json'
    if registry.exists():
        for source in json.loads(registry.read_text())['sources']:counts[source['title_id']]
    for title,value in counts.items():
        prior=state['titles'].get(title,{})
        for key in value:value[key]=max(value[key],prior.get(key,0))
        if value['metadata']>32 or value['search']>3:raise RuntimeError('Request allowance exceeded: '+title)
        prior.update(value,count_basis='visible discovery + known redirects + native policy and transport attempts; never lower previously charged state; web internal hops unavailable')
        state['titles'][title]=prior
    save_state(state)
    output={'at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'titles':dict(counts),
            'unreported_web_internal_hops':'not observable; no zero-hop claim',
            'no_fourth_search':True,'metadata_limit':32,'search_limit':3,
            'native_transport_future_calls':'additive to these seeded allowances, not a reset'}
    (OWN/'sources/REQUEST_ALLOWANCES.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()
