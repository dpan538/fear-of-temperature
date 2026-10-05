#!/usr/bin/env python3
"""One targeted correction pass for first-pass parser exceptions.

Reads only containers with historic ZIP ID/date exceptions or local fallback
locator exceptions in ParlParse/archive HTML. Preserves the original pass.
"""
from __future__ import annotations

import csv
import json
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

import validate_archive_splits as v


def key(row):
    return row['source_id'],row['raw_path'],row['content_version_id']


def main() -> None:
    out=v.HERE;root=v.DEFAULT_ROOT
    baseline=out/'parent_results.full_pass.csv'
    if (out/'RECHECK_LOG.json').exists():raise RuntimeError('Targeted recheck has already completed; refusing a second pass')
    for name in ('parent_results.csv','container_results.csv','exceptions.csv','execution_coverage.csv','INPUT_MANIFEST.json'):
        src=out/name
        shutil.copy2(src,out/(src.stem+'.full_pass'+src.suffix))
    targets=set()
    before=defaultdict(Counter)
    with baseline.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            before[row['adapter']][row['status']]+=1
            if row['adapter'] in ('historic_xml_zip','parlparse_xml_mirror','archive_html') and row['status'] not in ('supported_split','legitimate_shared_span'):
                targets.add(key(row))
    with (out/'recheck_target_keys.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['source_id','raw_path','content_version_id']);w.writerows(sorted(targets))
    corrections={};container_corrections={};new_exceptions=[];lock_log=[];start=time.monotonic()
    handle,entry=v.acquire_lock(root/v.LOCK_REL,lock_log,'targeted_exception_containers_only')
    try:
        con=duckdb.connect(str(root/v.DB_REL),read_only=True)
        group_key=None;parents={};done=0
        def flush() -> None:
            nonlocal parents,done
            if group_key is None:return
            source,path,version=group_key
            adapter=v.adapter_for(source,path)
            original=None;error=''
            try:original=v.parse_original(root/path,adapter,next(iter(parents.values())).genre)
            except Exception as exc:error=f'{type(exc).__name__}: {str(exc)[:260]}'
            rows=[v.validate_parent(p,original,error) for p in parents.values()]
            v.mark_duplicate_imports(rows,parents,original)
            for row in rows:
                corrections[(source,row['document_id'],path,version)]=row
                if row['status'] not in ('supported_split','legitimate_shared_span'):
                    new_exceptions.append({'unit':'parent','source_id':source,'adapter':adapter,
                        'document_id':row['document_id'],'external_id':row['external_id'],'raw_path':path,
                        'status':row['status'],'rule_ids':row['rule_ids'],'evidence_locator':row['evidence_locator'],
                        'details':row['details'],'minimal_action':'Inspect named saved-original node and parent/segment mapping; repair only a supported defect.'})
            mapped={row['original_group_id'] for row in rows if row['original_group_id']}
            expected={k for k in original.groups if not k.startswith('no_id:')} if original else set()
            omitted=sorted(expected-mapped) if original and original.omission_scope=='approved_department_groups_in_saved_volume' else []
            for group_id in omitted:
                group=original.groups[group_id]
                new_exceptions.append({'unit':'original_group','source_id':source,'adapter':adapter,
                    'raw_path':path,'status':'needs_review','rule_ids':'R-OMISSION','evidence_locator':path+'#'+group_id,
                    'details':f'Approved department/date source reply group has no linked parent; date={group.date}; title={group.title[:100]}',
                    'minimal_action':'Check earlier exclusion and overlap ledger before any missing-parent repair.'})
            counts=Counter(row['status'] for row in rows)
            cstatus='insufficient_evidence' if original is None else 'boundary_conflict' if counts['boundary_conflict'] or counts['duplicate_import'] else 'needs_review' if omitted else 'supported_split' if not counts['insufficient_evidence'] else 'insufficient_evidence'
            container_corrections[group_key]={
                'source_id':source,'adapter':adapter,'raw_path':path,'content_version_id':version,
                'imported_parent_count':len(parents),'original_group_count':len(original.groups) if original else '',
                'original_node_count':len(original.nodes) if original else '',
                'mapped_parent_count':len(mapped),'supported_parents':counts['supported_split'],
                'shared_parents':counts['legitimate_shared_span'],'duplicate_parents':counts['duplicate_import'],
                'boundary_conflicts':counts['boundary_conflict'],'insufficient_parents':counts['insufficient_evidence'],
                'omitted_candidate_groups':len(omitted),'status':cstatus,
                'rule_ids':'R-ORIGINAL' if original is None else 'R-OMISSION' if omitted else 'R-UNIT;R-SPAN;R-MAPPING',
                'evidence_locator':path,'details':error or (original.omission_scope if original else '')}
            done+=1
            if done%100==0:print(f'targeted recheck {done}/{len(targets)} containers',flush=True)
            parents={}
        for row in v.input_rows(con,sorted(targets)):
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
    if set(container_corrections)!=targets:
        raise RuntimeError(f'Targeted container inventory mismatch: expected {len(targets)}, read {len(container_corrections)}')
    with baseline.open(newline='',encoding='utf-8') as src,(out/'parent_results.rechecked.csv').open('w',newline='',encoding='utf-8') as dst:
        reader=csv.DictReader(src);writer=csv.DictWriter(dst,fieldnames=v.PARENT_FIELDS);writer.writeheader()
        for row in reader:
            replacement=corrections.get((row['source_id'],row['document_id'],row['raw_path'],row['content_version_id']))
            writer.writerow(replacement or row)
    with (out/'container_results.full_pass.csv').open(newline='',encoding='utf-8') as src,(out/'container_results.rechecked.csv').open('w',newline='',encoding='utf-8') as dst:
        reader=csv.DictReader(src);writer=csv.DictWriter(dst,fieldnames=v.CONTAINER_FIELDS);writer.writeheader()
        for row in reader:writer.writerow(container_corrections.get(key(row),row))
    target_paths={(s,p) for s,p,_ in targets}
    with (out/'exceptions.full_pass.csv').open(newline='',encoding='utf-8') as src,(out/'exceptions.rechecked.csv').open('w',newline='',encoding='utf-8') as dst:
        reader=csv.DictReader(src);writer=csv.DictWriter(dst,fieldnames=v.EXCEPTION_FIELDS);writer.writeheader()
        for row in reader:
            if (row['source_id'],row['raw_path']) not in target_paths:writer.writerow(row)
        for row in new_exceptions:writer.writerow(row)
    after=defaultdict(Counter);totals=defaultdict(Counter)
    with (out/'parent_results.rechecked.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            after[row['adapter']][row['status']]+=1;totals[row['source_id']]['parents']+=1
            totals[row['source_id']][row['status']]+=1
    with (out/'container_results.rechecked.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            t=totals[row['source_id']];t['containers']+=1
            t['original_containers_read']+=bool(row['original_group_count'])
            t['omitted_candidate_groups']+=int(row['omitted_candidate_groups'] or 0)
    with (out/'execution_coverage.rechecked.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['source_id','adapter','inventory_parents','inventory_containers','original_containers_read',
                'supported_split','legitimate_shared_span','duplicate_import','boundary_conflict','insufficient_evidence',
                'omitted_candidate_groups','original_verification_scope']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for source,adapter in v.SOURCES.items():
            t=totals[source]
            writer.writerow({'source_id':source,'adapter':adapter,'inventory_parents':t['parents'],
                'inventory_containers':t['containers'],'original_containers_read':t['original_containers_read'],
                'supported_split':t['supported_split'],'legitimate_shared_span':t['legitimate_shared_span'],
                'duplicate_import':t['duplicate_import'],'boundary_conflict':t['boundary_conflict'],
                'insufficient_evidence':t['insufficient_evidence'],'omitted_candidate_groups':t['omitted_candidate_groups'],
                'original_verification_scope':'mapped parent/node text + keyed approved-department omitted-candidate inventory' if adapter=='historic_xml_zip' else 'mapped selected parents/nodes; no all-source omission claim'})
    manifest=json.loads((out/'INPUT_MANIFEST.full_pass.json').read_text())
    manifest['targeted_recheck']={'generated_utc':v.now(),'containers':len(targets),'parent_links':len(corrections),
        'scope':'Only first-pass exception containers for historic ZIP ID/date and local fallback locator checks; no full corpus rerun',
        'lock_holds':lock_log,'elapsed_seconds':round(time.monotonic()-start,2)}
    (out/'INPUT_MANIFEST.rechecked.json').write_text(json.dumps(manifest,indent=2)+'\n')
    log={'before':{k:dict(x) for k,x in before.items()},'after':{k:dict(x) for k,x in after.items()},
         'target_containers':len(targets),'rechecked_parent_links':len(corrections),'new_exceptions':len(new_exceptions),
         'lock_holds':lock_log,'elapsed_seconds':round(time.monotonic()-start,2)}
    (out/'RECHECK_LOG.json').write_text(json.dumps(log,indent=2)+'\n')
    for name in ('parent_results','container_results','exceptions','execution_coverage'):
        (out/(name+'.rechecked.csv')).replace(out/(name+'.csv'))
    (out/'INPUT_MANIFEST.rechecked.json').replace(out/'INPUT_MANIFEST.json')
    print(json.dumps({'target_containers':len(targets),'parent_links':len(corrections),
                      'after':log['after'],'seconds':log['elapsed_seconds']},indent=2))


if __name__=='__main__':main()
