#!/usr/bin/env python3
"""Read-only exact-ID reconciliation of keyed historic ZIP omission leads."""
from __future__ import annotations

import csv
import json
import time
from collections import Counter,defaultdict

import duckdb

import validate_archive_splits as v


def main() -> None:
    out=v.HERE;root=v.DEFAULT_ROOT
    if (out/'omission_reconciliation.csv').exists():raise RuntimeError('Omission reconciliation already completed')
    candidates=[]
    with (out/'exceptions.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['unit']=='original_group' and row['source_id']=='src_549acfda11091ff8c9b8':
                candidates.append((row['source_id'],row['raw_path'],row['evidence_locator'].rsplit('#',1)[-1],row['details']))
    ids=sorted({x[2] for x in candidates})
    found=defaultdict(set);locks=[];start=time.monotonic()
    handle,entry=v.acquire_lock(root/v.LOCK_REL,locks,'exact_id_historic_omission_reconciliation')
    try:
        con=duckdb.connect(str(root/v.DB_REL),read_only=True)
        sql='''SELECT d.external_id,cv.raw_path FROM documents d
               JOIN document_content_objects x USING(document_id)
               JOIN content_versions cv USING(content_object_id)
               WHERE d.source_id=? AND d.external_id IN (SELECT unnest(?))'''
        for ext,path in con.execute(sql,['src_549acfda11091ff8c9b8',ids]).fetchall():found[str(ext)].add(str(path))
        con.close()
    finally:v.release_lock(handle,entry)
    rows=[];counts=Counter()
    for sid,path,ext,detail in candidates:
        paths=found.get(ext,set())
        if path in paths:status='registered_in_same_container_check_mapping'
        elif paths:status='registered_in_overlapping_container'
        else:status='unregistered_source_group_candidate'
        counts[status]+=1
        rows.append({'source_id':sid,'source_group_id':ext,'candidate_raw_path':path,
                     'reconciliation_status':status,'registered_raw_paths':';'.join(sorted(paths)),
                     'source_evidence':detail,'minimum_action':'Check earlier source exclusions and overlap ledger; repair only if eligible and genuinely absent.'})
    with (out/'omission_reconciliation.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['source_id','source_group_id','candidate_raw_path','reconciliation_status',
                'registered_raw_paths','source_evidence','minimum_action']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    manifest=json.loads((out/'INPUT_MANIFEST.json').read_text())
    manifest['omission_reconciliation']={'generated_utc':v.now(),'candidates':len(candidates),
        'results':dict(counts),'scope':'Exact same-source external ID only; no cross-source title/semantic merge',
        'lock_holds':locks,'elapsed_seconds':round(time.monotonic()-start,2)}
    (out/'INPUT_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest['omission_reconciliation'],indent=2))


if __name__=='__main__':main()
