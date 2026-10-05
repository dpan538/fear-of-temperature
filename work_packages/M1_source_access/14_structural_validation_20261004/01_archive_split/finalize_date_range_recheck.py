#!/usr/bin/env python3
"""Resolve only historic range-heading date exceptions in nine saved ZIPs."""
from __future__ import annotations

import csv
import json
import shutil
import time
from collections import Counter,defaultdict

import validate_archive_splits as v


def main() -> None:
    out=v.HERE;root=v.DEFAULT_ROOT
    if (out/'DATE_RANGE_RECHECK_LOG.json').exists():
        raise RuntimeError('Date-range recheck already completed')
    source=out/'parent_results.csv'
    rows=list(csv.DictReader(source.open(newline='',encoding='utf-8')))
    paths={r['raw_path'] for r in rows if r['adapter']=='historic_xml_zip' and r['rule_ids'] in ('R-DATE','R-DATE;R-TEXT-UNIT')}
    for name in ('parent_results.csv','container_results.csv','exceptions.csv','execution_coverage.csv','INPUT_MANIFEST.json'):
        src=out/name;shutil.copy2(src,out/(src.stem+'.before_date_range'+src.suffix))
    originals={};locks=[];start=time.monotonic()
    handle,entry=v.acquire_lock(root/v.LOCK_REL,locks,'nine_historic_range_heading_zip_recheck')
    try:
        for path in sorted(paths):originals[path]=v.parse_historic_zip(root/path)
    finally:v.release_lock(handle,entry)
    corrected=[]
    for row in rows:
        if row['raw_path'] not in originals or row['rule_ids'] not in ('R-DATE','R-DATE;R-TEXT-UNIT'):continue
        original=originals[row['raw_path']]
        group=original.groups.get(row['original_group_id'])
        if group is None or group.date!=row['publication_date']:continue
        old=row['details']
        row['status']='supported_split'
        row['rule_ids']='R-UNIT;R-SPAN;R-MAPPING'+(';R-TEXT-UNIT' if 'R-TEXT-UNIT' in row['rule_ids'] else '')
        row['details']='Saved source group and child spans align; range heading uses explicit XML date attribute.'
        if 'R-TEXT-UNIT' in row['rule_ids']:
            row['details']+=' Unique exact text maps the unkeyed group; hashed parent ID not independently reproduced.'
        corrected.append({'document_id':row['document_id'],'external_id':row['external_id'],
            'raw_path':row['raw_path'],'source_group':row['original_group_id'],
            'stored_date':row['publication_date'],'confirmed_source_date':group.date,'prior_details':old})
    with (out/'date_range_corrections.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['document_id','external_id','raw_path','source_group','stored_date','confirmed_source_date','prior_details']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(corrected)
    with (out/'parent_results.date_final.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=v.PARENT_FIELDS);w.writeheader();w.writerows(rows)
    by_container=defaultdict(Counter);by_source=defaultdict(Counter)
    for row in rows:
        by_container[(row['source_id'],row['raw_path'],row['content_version_id'])][row['status']]+=1
        by_source[row['source_id']]['parents']+=1;by_source[row['source_id']][row['status']]+=1
    containers=[]
    with (out/'container_results.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            c=by_container[(row['source_id'],row['raw_path'],row['content_version_id'])]
            row['supported_parents']=c['supported_split'];row['shared_parents']=c['legitimate_shared_span']
            row['duplicate_parents']=c['duplicate_import'];row['boundary_conflicts']=c['boundary_conflict']
            row['insufficient_parents']=c['insufficient_evidence']
            if row['raw_path'] in paths:
                row['status']='boundary_conflict' if c['boundary_conflict'] or c['duplicate_import'] else 'needs_review' if int(row['omitted_candidate_groups'] or 0) else 'insufficient_evidence' if c['insufficient_evidence'] else 'supported_split'
            containers.append(row)
            z=by_source[row['source_id']];z['containers']+=1
            z['original_containers_read']+=bool(row['original_group_count'])
            z['omitted_candidate_groups']+=int(row['omitted_candidate_groups'] or 0)
    with (out/'container_results.date_final.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=v.CONTAINER_FIELDS);w.writeheader();w.writerows(containers)
    corrected_docs={x['document_id'] for x in corrected}
    with (out/'exceptions.csv').open(newline='',encoding='utf-8') as src,(out/'exceptions.date_final.csv').open('w',newline='',encoding='utf-8') as dst:
        reader=csv.DictReader(src);writer=csv.DictWriter(dst,fieldnames=v.EXCEPTION_FIELDS);writer.writeheader()
        for row in reader:
            if row['unit']=='parent' and row['document_id'] in corrected_docs:continue
            writer.writerow(row)
    with (out/'execution_coverage.date_final.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['source_id','adapter','inventory_parents','inventory_containers','original_containers_read',
                'supported_split','legitimate_shared_span','duplicate_import','boundary_conflict','insufficient_evidence',
                'omitted_candidate_groups','original_verification_scope']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for source_id,adapter in v.SOURCES.items():
            z=by_source[source_id]
            writer.writerow({'source_id':source_id,'adapter':adapter,'inventory_parents':z['parents'],
                'inventory_containers':z['containers'],'original_containers_read':z['original_containers_read'],
                'supported_split':z['supported_split'],'legitimate_shared_span':z['legitimate_shared_span'],
                'duplicate_import':z['duplicate_import'],'boundary_conflict':z['boundary_conflict'],
                'insufficient_evidence':z['insufficient_evidence'],'omitted_candidate_groups':z['omitted_candidate_groups'],
                'original_verification_scope':'mapped parent/node text + keyed approved-department omitted-candidate inventory' if adapter=='historic_xml_zip' else 'mapped selected parents/nodes; no all-source omission claim'})
    manifest=json.loads((out/'INPUT_MANIFEST.json').read_text())
    manifest['date_range_recheck']={'generated_utc':v.now(),'zip_containers':len(paths),
        'corrected_parent_dates':len(corrected),'scope':'Only saved historic ZIPs with R-DATE and range-heading ambiguity; no database scan',
        'lock_holds':locks,'elapsed_seconds':round(time.monotonic()-start,2)}
    (out/'INPUT_MANIFEST.date_final.json').write_text(json.dumps(manifest,indent=2)+'\n')
    log={'zip_containers':len(paths),'corrected_parent_dates':len(corrected),
        'remaining_date_flags':sum(r['adapter']=='historic_xml_zip' and 'R-DATE' in r['rule_ids'] for r in rows),
        'lock_holds':locks,'elapsed_seconds':round(time.monotonic()-start,2)}
    (out/'DATE_RANGE_RECHECK_LOG.json').write_text(json.dumps(log,indent=2)+'\n')
    for name in ('parent_results','container_results','exceptions','execution_coverage'):
        (out/(name+'.date_final.csv')).replace(out/(name+'.csv'))
    (out/'INPUT_MANIFEST.date_final.json').replace(out/'INPUT_MANIFEST.json')
    print(json.dumps(log,indent=2))


if __name__=='__main__':main()
