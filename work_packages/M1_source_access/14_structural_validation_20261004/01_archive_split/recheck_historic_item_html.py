#!/usr/bin/env python3
"""Targeted validation of the 321 saved 1991 Historic Hansard item pages."""
from __future__ import annotations

import csv
import argparse
import json
import shutil
import time
from collections import Counter,defaultdict

import duckdb

import validate_archive_splits as v


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--continuations',action='store_true',help='Recheck only flagged saved item pages after numbered-question continuation rule')
    args=parser.parse_args()
    out=v.HERE;root=v.DEFAULT_ROOT
    tag='item_continuations' if args.continuations else 'item_html'
    log_path=out/('ITEM_HTML_CONTINUATION_RECHECK_LOG.json' if args.continuations else 'ITEM_HTML_RECHECK_LOG.json')
    if log_path.exists():raise RuntimeError('This item-page recheck already completed')
    target=set()
    with (out/'parent_results.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            selected=(row['adapter']=='historic_item_html' and row['status']=='boundary_conflict') if args.continuations else (row['adapter']=='unsupported' and row['raw_path'].lower().endswith(('.htm','.html')))
            if selected:
                target.add((row['source_id'],row['raw_path'],row['content_version_id']))
    for name in ('parent_results.csv','container_results.csv','exceptions.csv','execution_coverage.csv','INPUT_MANIFEST.json'):
        src=out/name;shutil.copy2(src,out/(src.stem+'.before_'+tag+src.suffix))
    corrections={};containers={};new_exceptions=[];locks=[];start=time.monotonic()
    handle,entry=v.acquire_lock(root/v.LOCK_REL,locks,'saved_historic_item_html_'+tag)
    try:
        con=duckdb.connect(str(root/v.DB_REL),read_only=True)
        group_key=None;parents={}
        def flush() -> None:
            nonlocal parents
            if group_key is None:return
            sid,path,vid=group_key
            try:original=v.parse_historic_item_html(root/path);error=''
            except Exception as exc:original=None;error=f'{type(exc).__name__}: {str(exc)[:260]}'
            results=[v.validate_parent(p,original,error) for p in parents.values()]
            v.mark_duplicate_imports(results,parents,original)
            for row in results:
                corrections[(sid,row['document_id'],path,vid)]=row
                if row['status'] not in ('supported_split','legitimate_shared_span'):
                    new_exceptions.append({'unit':'parent','source_id':sid,'adapter':'historic_item_html',
                        'document_id':row['document_id'],'external_id':row['external_id'],'raw_path':path,
                        'status':row['status'],'rule_ids':row['rule_ids'],'evidence_locator':row['evidence_locator'],
                        'details':row['details'],'minimal_action':'Compare each question/reply block in this saved item page before any split repair.'})
            counts=Counter(x['status'] for x in results)
            containers[group_key]={'source_id':sid,'adapter':'historic_item_html','raw_path':path,'content_version_id':vid,
                'imported_parent_count':len(parents),'original_group_count':len(original.groups) if original else '',
                'original_node_count':len(original.nodes) if original else '',
                'mapped_parent_count':sum(bool(x['original_group_id']) for x in results),
                'supported_parents':counts['supported_split'],'shared_parents':counts['legitimate_shared_span'],
                'duplicate_parents':counts['duplicate_import'],'boundary_conflicts':counts['boundary_conflict'],
                'insufficient_parents':counts['insufficient_evidence'],'omitted_candidate_groups':0,
                'status':'boundary_conflict' if counts['boundary_conflict'] or counts['duplicate_import'] else 'insufficient_evidence' if counts['insufficient_evidence'] else 'supported_split',
                'rule_ids':'R-ORIGINAL' if original is None else 'R-UNIT;R-SPAN;R-MAPPING',
                'evidence_locator':path,'details':error or 'mapped_saved_item_page_only'}
            parents={}
        for row in v.input_rows(con,sorted(target)):
            sid,pid,ext,date,genre,oid,vid,path,mime,nver,segid,actor,loc,text,segorder,segvid=row
            current=(sid,path or '',vid or '')
            if group_key is not None and current!=group_key:flush()
            group_key=current
            if pid not in parents:
                parents[pid]=v.Parent(sid,pid,ext or '',date or '',genre or '',oid or '',vid or '',path or '',mime or '',int(nver or 0))
            if segid and segid not in parents[pid].segments:
                parents[pid].segments[segid]=v.Segment(segid,loc or '',text or '',int(segorder) if segorder is not None else None,segvid or '',actor or '')
        flush();con.close()
    finally:v.release_lock(handle,entry)
    if set(containers)!=target:raise RuntimeError(f'Item-page inventory mismatch: expected {len(target)}, found {len(containers)}')
    with (out/'parent_results.csv').open(newline='',encoding='utf-8') as src,(out/('parent_results.'+tag+'.csv')).open('w',newline='',encoding='utf-8') as dst:
        reader=csv.DictReader(src);writer=csv.DictWriter(dst,fieldnames=v.PARENT_FIELDS);writer.writeheader()
        for row in reader:writer.writerow(corrections.get((row['source_id'],row['document_id'],row['raw_path'],row['content_version_id']),row))
    with (out/'container_results.csv').open(newline='',encoding='utf-8') as src,(out/('container_results.'+tag+'.csv')).open('w',newline='',encoding='utf-8') as dst:
        reader=csv.DictReader(src);writer=csv.DictWriter(dst,fieldnames=v.CONTAINER_FIELDS);writer.writeheader()
        for row in reader:writer.writerow(containers.get((row['source_id'],row['raw_path'],row['content_version_id']),row))
    target_paths={(s,p) for s,p,_ in target}
    with (out/'exceptions.csv').open(newline='',encoding='utf-8') as src,(out/('exceptions.'+tag+'.csv')).open('w',newline='',encoding='utf-8') as dst:
        reader=csv.DictReader(src);writer=csv.DictWriter(dst,fieldnames=v.EXCEPTION_FIELDS);writer.writeheader()
        for row in reader:
            if (row['source_id'],row['raw_path']) not in target_paths:writer.writerow(row)
        for row in new_exceptions:writer.writerow(row)
    counts=defaultdict(Counter)
    with (out/('parent_results.'+tag+'.csv')).open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            z=counts[row['source_id']];z['parents']+=1;z[row['status']]+=1
    with (out/('container_results.'+tag+'.csv')).open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            z=counts[row['source_id']];z['containers']+=1
            z['original_containers_read']+=bool(row['original_group_count'])
            z['omitted_candidate_groups']+=int(row['omitted_candidate_groups'] or 0)
    with (out/('execution_coverage.'+tag+'.csv')).open('w',newline='',encoding='utf-8') as f:
        fields=['source_id','adapter','inventory_parents','inventory_containers','original_containers_read',
                'supported_split','legitimate_shared_span','duplicate_import','boundary_conflict','insufficient_evidence',
                'omitted_candidate_groups','original_verification_scope']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for sid,adapter in v.SOURCES.items():
            z=counts[sid]
            w.writerow({'source_id':sid,'adapter':adapter,'inventory_parents':z['parents'],'inventory_containers':z['containers'],
                'original_containers_read':z['original_containers_read'],'supported_split':z['supported_split'],
                'legitimate_shared_span':z['legitimate_shared_span'],'duplicate_import':z['duplicate_import'],
                'boundary_conflict':z['boundary_conflict'],'insufficient_evidence':z['insufficient_evidence'],
                'omitted_candidate_groups':z['omitted_candidate_groups'],
                'original_verification_scope':'mapped parent/node text, keyed ZIP omitted candidates, and targeted saved item HTML' if adapter=='historic_xml_zip' else 'mapped selected parents/nodes; no all-source omission claim'})
    manifest=json.loads((out/'INPUT_MANIFEST.json').read_text())
    manifest_key='historic_item_continuation_recheck' if args.continuations else 'historic_item_html_recheck'
    manifest[manifest_key]={'generated_utc':v.now(),'saved_pages':len(target),
        'parent_links':len(corrections),'scope':'Only registered 1991 repair item HTML links; no full corpus rerun',
        'lock_holds':locks,'elapsed_seconds':round(time.monotonic()-start,2)}
    (out/('INPUT_MANIFEST.'+tag+'.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    log={'saved_pages':len(target),'parent_links':len(corrections),
        'statuses':dict(Counter(x['status'] for x in corrections.values())),
        'lock_holds':locks,'elapsed_seconds':round(time.monotonic()-start,2)}
    log_path.write_text(json.dumps(log,indent=2)+'\n')
    for name in ('parent_results','container_results','exceptions','execution_coverage'):
        (out/(name+'.'+tag+'.csv')).replace(out/(name+'.csv'))
    (out/('INPUT_MANIFEST.'+tag+'.json')).replace(out/'INPUT_MANIFEST.json')
    print(json.dumps(log,indent=2))


if __name__=='__main__':main()
