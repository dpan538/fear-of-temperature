"""Reusable frozen-target -> raw -> derivative -> pending/reviewed staging chain.

This is an executable framework, not validated adapters for all listed newspapers.
No route can acquire until its own gate clears; every failed target remains frozen.
"""
from __future__ import annotations
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import parser, staging, transport

def owned(path):
    path=Path(path).resolve()
    if transport.OWN.resolve() not in path.parents:
        raise ValueError('Pipeline inputs/outputs must belong to the newspaper package')
    return path

def freeze_frame(source, month, discovery_receipt, candidates, *, native_order,
                 frame_complete=False, next_cursor=None):
    """Candidates must be dated native article links; containers cannot stand in."""
    if native_order not in {'native_DOM','native_date_ascending','native_date_descending'}:
        raise ValueError('Undeclared order')
    if not source.replace('_','').isalnum():raise ValueError('Unsafe source identifier')
    if not '1988-01'<=month<='2026-09':raise ValueError('Outside calendar')
    unique=[];seen=set();aliases=[]
    for item in candidates:
        if item['unit_kind']!='article':raise ValueError('Only article parents may be selected')
        day=item['publication_date'];dt.date.fromisoformat(day)
        if day[:7]!=month or not '1988-01-01'<=day<='2026-09-21':continue
        key=item['native_id']
        if key in seen:
            aliases.append(item);continue
        seen.add(key);unique.append(item)
    days=[x['publication_date'] for x in unique]
    if native_order!='native_DOM' and days!=sorted(days,reverse=native_order=='native_date_descending'):
        raise ValueError('Candidates disagree with declared native date order')
    frame={'source_id':source,'month':month,'frozen_at_utc':transport.utc(),
           'native_order':native_order,'discovery_receipt':discovery_receipt,
           'candidates':unique,'selected':unique[:1],'frame_complete':frame_complete,
           'identity_aliases':aliases,
           'next_cursor':next_cursor,'topic_query':None,'fear_filter':None,
           'eligible_population_count':None,'inclusion_probability':None,
           'failure_replacement':'none; failed target retained'}
    path=transport.OWN/'frames'/f'{source}_{month}.json';path.parent.mkdir(exist_ok=True)
    if path.exists():raise ValueError('Frozen frame exists; no silent rewrite/refill')
    path.write_text(json.dumps(frame,indent=2)+'\n')
    return path

def inspect_target(frame_path, gate_path, adapter, *, request_version='initial',previous_request_id=None,recovery_reason=None):
    frame_path=owned(frame_path);frame=json.loads(frame_path.read_text())
    if not frame['selected']:raise ValueError('No selected article; gap stays explicit')
    target=frame['selected'][0]
    receipt=transport.fetch(frame['source_id'],target['url'],'article',gate_path,
        request_version=request_version,previous_request_id=previous_request_id,recovery_reason=recovery_reason)
    if receipt['status']!='saved' or receipt.get('partial'):
        return {'state':receipt['status'],'request_id':receipt['request_id'],'newspaper_qualified':False}
    raw=owned(transport.OWN/receipt['raw_path'])
    if parser.digest(raw.read_bytes())!=receipt['raw_sha256']:raise ValueError('Raw digest mismatch')
    result=parser.extract(raw.read_bytes(),**adapter)
    directory=transport.OWN/'inspections';directory.mkdir(exist_ok=True)
    pass_id=hashlib.sha256((receipt['request_id']+result.get('parser_sha256',parser.parser_digest())+
                           result.get('adapter_sha256','unresolved')).encode()).hexdigest()[:24]
    body=transport.OWN/'bodies'/(pass_id+'.txt');body.parent.mkdir(exist_ok=True)
    with transport.HEAVY_LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        additional=len(result.get('body','').encode())+65536
        budget=transport.preflight(additional)
        if not budget['passed']:
            return {'state':'derivative_storage_blocked','request_id':receipt['request_id'],
                    'budget':budget,'newspaper_qualified':False,'raw_preserved':True}
        if result.get('body'):
            if len(result['body'].encode())>3*transport.SCOPE['default_object_cap_bytes']:
                raise ValueError('Derivative copy cap exceeded; raw is preserved')
            if body.exists() and body.read_text()!=result['body']:raise ValueError('Derivative conflict')
            if not body.exists():body.write_text(result['body'])
    inspection={'pass_id':pass_id,'frame_path':str(frame_path),'frame_sha256':transport.sha(frame_path),
        'target':target,'receipt':receipt,'body_path':str(body),
        'extraction':{k:v for k,v in result.items() if k!='body'},
        'parser_sha256':parser.parser_digest(),'pipeline_sha256':transport.sha(__file__),
        'review_state':'pending','qualified_readable':False,
        'historical_version_equivalence':'not established'}
    path=directory/(pass_id+'.json')
    if not path.exists():path.write_text(json.dumps(inspection,indent=2)+'\n')
    return {'inspection_path':str(path),'state':result['state'],'newspaper_qualified':False}

def stage_reviewed(inspection_path, source_record, review_path):
    """Evidence-linked unit/date/boundary review, not a request-ID completion whitelist.

    The worker can record these checks inside the already authorised collection.
    No user approval per article is introduced by this prototype.
    """
    inspection_path=owned(inspection_path);review_path=owned(review_path)
    report=json.loads(inspection_path.read_text());review=json.loads(review_path.read_text())
    extraction=report['extraction'];receipt=report['receipt'];target=report['target']
    if review.get('status')!='qualified_readable_article':raise ValueError('Review pending/not qualified')
    if extraction['state']!='structural_candidate':raise ValueError('Preview/container/unresolved boundary')
    frame_path=owned(report['frame_path'])
    if transport.sha(frame_path)!=report['frame_sha256']:raise ValueError('Frozen frame changed after inspection')
    frame=json.loads(frame_path.read_text())
    if not frame['selected'] or frame['selected'][0]!=target:raise ValueError('Target differs from frozen selection')
    if source_record['source_id']!=frame['source_id'] or receipt['source_id']!=frame['source_id']:
        raise ValueError('Source identity differs across frame/receipt/parent')
    for key in ('raw_sha256','body_sha256','parser_sha256','adapter_sha256'):
        if review.get(key)!=extraction[key]:raise ValueError('Review refers to another extraction: '+key)
    required=('newspaper_identity','independent_article_parent','publication_date_mapping',
              'complete_visible_prose','no_issue_or_page_conflation','body_boundary','provenance_mapping')
    if not all(review.get('checks',{}).get(k) is True for k in required):raise ValueError('Required structural check unresolved')
    if review['publication_date']!=target['publication_date']:raise ValueError('Frame/date conflict')
    raw=owned(transport.OWN/receipt['raw_path']);body=owned(report['body_path'])
    if parser.digest(raw.read_bytes())!=extraction['raw_sha256'] or parser.digest(body.read_bytes())!=extraction['body_sha256']:
        raise ValueError('Raw/body changed after review')
    record=dict(source_record,lane='newspaper',native_id=target['native_id'],
                publication_date=target['publication_date'],unit_kind='article',newspaper_eligible=1)
    version=dict(raw_path=str(raw),raw_sha256=extraction['raw_sha256'],body_path=str(body),
        body_sha256=extraction['body_sha256'],parser_sha256=extraction['parser_sha256'],
        retrieved_at=receipt['finished_at_utc'],content_version_time=review.get('content_version_time'),
        historical_version_equivalence='not established',qualified_readable=1,
        extraction_json=json.dumps({'extraction':extraction,'review_path':str(review_path),
                                    'review_sha256':transport.sha(review_path)}))
    cursor={'last_frame':report['frame_path'],'frame_sha256':report['frame_sha256'],
            'last_request':receipt['request_id'],'next':frame['next_cursor'],'failed_targets_replaced':False}
    with transport.HEAVY_LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with staging.writer(transport.OWN/'staging/newspaper.sqlite3') as con:
            result=staging.ingest(con,record,version,receipt,cursor)
    return result
