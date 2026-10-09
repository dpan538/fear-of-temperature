"""Bounded dated instance snapshots plus a clearly institutional actor feed."""
import datetime as dt
import json
import urllib.parse
import social_elt as e

def _consume(url,sid,basis):
    rec=e.fetch(url,sid,'content')
    if rec['status']!='saved':
        print(json.dumps({'source':sid,'request_id':rec['request_id'],'status':rec['status'],'http_status':rec.get('http_status')}),flush=True);return None
    data=e.json_payload(rec)
    rows,dispositions=e.bluesky_records(data) if sid=='bluesky' else e.mastodon_records(data,sid)
    with e.shared(65536):e.atomic(e.WORK/'receipts'/(rec['request_id']+'.dispositions.json'),dict(request_id=rec['request_id'],dispositions=dispositions,frame_basis=basis))
    print(json.dumps({'source':sid,**e.load(rows,rec)}),flush=True)
    return data

def consume(url,sid,basis):
    try:return _consume(url,sid,basis)
    except Exception as error:
        reason=str(error)
        if isinstance(error,e.Stop) and any(reason.startswith(x) for x in ('fixed_deadline','resource_stop','request_ceiling','returned_native_object_ceiling','object_ceiling','owner_','scope_digest','active_social_lease')):raise
        with e.shared(65536):e.append(e.WORK/'LANE_FAILURES.jsonl',{'at_utc':e.utc(),'source_id':sid,'url':url,'reason':type(error).__name__+': '+reason,'durable_successes_preserved':True})
        print(json.dumps({'source':sid,'route_status':'preserved_lane_failure','reason':reason}),flush=True)
        return None

def run():
    # This implementation-derived bound only drives the documented max_id
    # cursor. The returned native created_at is always checked independently.
    bound=int(dt.datetime(2026,9,22,tzinfo=dt.timezone.utc).timestamp()*1000)<<16
    for sid,host in [('mastodon_ie','mastodon.ie'),('mastodon_uk','mastodon.me.uk'),('mastodon_au','aus.social'),('mastodon_us','sfba.social')]:
        url='https://'+host+'/api/v1/timelines/public?'+urllib.parse.urlencode(dict(local='true',limit=40,max_id=bound))
        consume(url,sid,'Local-instance public timeline; Snowflake.id_at primary implementation supplies cursor, never publication date; author geography remains unknown')
    cursor=None
    for page in range(3):
        params=dict(actor='bsky.app',limit=50,filter='posts_no_replies',includePins='false')
        if cursor:params['cursor']=cursor
        data=consume('https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?'+urllib.parse.urlencode(params),'bluesky','Official Bluesky bsky.app account; institutional expression, no ordinary-public or country inference')
        if data is None:break
        cursor=data.get('cursor')
        if not cursor:break
    print(json.dumps({'platform_wave_status':'bounded_frame_completed','requests_charged':e.state()['requests'],'loaded_distinct':len(e.state()['object_ids']),'returned_distinct':len(e.state().get('returned_object_ids',[]))}),flush=True)
if __name__=='__main__':
    with e.writer():run()
