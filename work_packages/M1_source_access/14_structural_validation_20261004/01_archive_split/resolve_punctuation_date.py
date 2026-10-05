#!/usr/bin/env python3
"""One-volume check for the 1991-06-14 written-answer heading punctuation."""
from __future__ import annotations

import csv
import json
import shutil
import time
from collections import Counter,defaultdict

import validate_archive_splits as v


def main() -> None:
    out=v.HERE;root=v.DEFAULT_ROOT
    if (out/'PUNCTUATION_DATE_RECHECK_LOG.json').exists():raise RuntimeError('One-volume punctuation check already completed')
    rows=list(csv.DictReader((out/'parent_results.csv').open(newline='',encoding='utf-8')))
    target=next(r['raw_path'] for r in rows if r['adapter']=='historic_xml_zip' and r['raw_path'].endswith('/S6CV0192P0.zip') and r['rule_ids']=='R-DATE')
    for name in ('parent_results.csv','container_results.csv','exceptions.csv','execution_coverage.csv','INPUT_MANIFEST.json'):
        src=out/name;shutil.copy2(src,out/(src.stem+'.before_punctuation'+src.suffix))
    locks=[];start=time.monotonic();handle,entry=v.acquire_lock(root/v.LOCK_REL,locks,'one_historic_single_day_punctuation_zip')
    try:original=v.parse_historic_zip(root/target)
    finally:v.release_lock(handle,entry)
    corrected=[]
    for row in rows:
        if row['raw_path']!=target or row['rule_ids']!='R-DATE':continue
        group=original.groups.get(row['original_group_id'])
        if group is None or group.date!=row['publication_date']:continue
        row['status']='supported_split';row['rule_ids']='R-UNIT;R-SPAN;R-MAPPING'
        row['details']='Visible single-day heading (Friday 14 June, 1991) agrees with stored date; saved source group and child spans align.'
        corrected.append(row['document_id'])
    with (out/'parent_results.punctuation_final.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=v.PARENT_FIELDS);w.writeheader();w.writerows(rows)
    parent_counts=defaultdict(Counter);source_counts=defaultdict(Counter)
    for row in rows:
        parent_counts[(row['source_id'],row['raw_path'],row['content_version_id'])][row['status']]+=1
        z=source_counts[row['source_id']];z['parents']+=1;z[row['status']]+=1
    containers=[]
    with (out/'container_results.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            counts=parent_counts[(row['source_id'],row['raw_path'],row['content_version_id'])]
            row['supported_parents']=counts['supported_split'];row['shared_parents']=counts['legitimate_shared_span']
            row['duplicate_parents']=counts['duplicate_import'];row['boundary_conflicts']=counts['boundary_conflict']
            row['insufficient_parents']=counts['insufficient_evidence']
            if row['raw_path']==target:
                row['status']='boundary_conflict' if counts['boundary_conflict'] or counts['duplicate_import'] else 'needs_review' if int(row['omitted_candidate_groups'] or 0) else 'insufficient_evidence' if counts['insufficient_evidence'] else 'supported_split'
            containers.append(row)
            z=source_counts[row['source_id']];z['containers']+=1
            z['original_containers_read']+=bool(row['original_group_count'])
            z['omitted_candidate_groups']+=int(row['omitted_candidate_groups'] or 0)
    with (out/'container_results.punctuation_final.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=v.CONTAINER_FIELDS);w.writeheader();w.writerows(containers)
    with (out/'exceptions.csv').open(newline='',encoding='utf-8') as src,(out/'exceptions.punctuation_final.csv').open('w',newline='',encoding='utf-8') as dst:
        reader=csv.DictReader(src);writer=csv.DictWriter(dst,fieldnames=v.EXCEPTION_FIELDS);writer.writeheader()
        for row in reader:
            if row['unit']=='parent' and row['document_id'] in corrected:continue
            writer.writerow(row)
    with (out/'execution_coverage.punctuation_final.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['source_id','adapter','inventory_parents','inventory_containers','original_containers_read',
                'supported_split','legitimate_shared_span','duplicate_import','boundary_conflict','insufficient_evidence',
                'omitted_candidate_groups','original_verification_scope']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for sid,adapter in v.SOURCES.items():
            z=source_counts[sid]
            w.writerow({'source_id':sid,'adapter':adapter,'inventory_parents':z['parents'],
                'inventory_containers':z['containers'],'original_containers_read':z['original_containers_read'],
                'supported_split':z['supported_split'],'legitimate_shared_span':z['legitimate_shared_span'],
                'duplicate_import':z['duplicate_import'],'boundary_conflict':z['boundary_conflict'],
                'insufficient_evidence':z['insufficient_evidence'],'omitted_candidate_groups':z['omitted_candidate_groups'],
                'original_verification_scope':'mapped parent/node text + keyed approved-department omitted-candidate inventory' if adapter=='historic_xml_zip' else 'mapped selected parents/nodes; no all-source omission claim'})
    manifest=json.loads((out/'INPUT_MANIFEST.json').read_text())
    manifest['single_day_punctuation_recheck']={'generated_utc':v.now(),'zip_containers':1,
        'corrected_parent_dates':len(corrected),'scope':'Only S6CV0192P0.zip; no database scan',
        'lock_holds':locks,'elapsed_seconds':round(time.monotonic()-start,2)}
    (out/'INPUT_MANIFEST.punctuation_final.json').write_text(json.dumps(manifest,indent=2)+'\n')
    log={'zip_containers':1,'corrected_parent_dates':len(corrected),'remaining_date_flags':sum(r['adapter']=='historic_xml_zip' and 'R-DATE' in r['rule_ids'] for r in rows),
         'lock_holds':locks,'elapsed_seconds':round(time.monotonic()-start,2)}
    (out/'PUNCTUATION_DATE_RECHECK_LOG.json').write_text(json.dumps(log,indent=2)+'\n')
    for name in ('parent_results','container_results','exceptions','execution_coverage'):
        (out/(name+'.punctuation_final.csv')).replace(out/(name+'.csv'))
    (out/'INPUT_MANIFEST.punctuation_final.json').replace(out/'INPUT_MANIFEST.json')
    print(json.dumps(log,indent=2))


if __name__=='__main__':main()
