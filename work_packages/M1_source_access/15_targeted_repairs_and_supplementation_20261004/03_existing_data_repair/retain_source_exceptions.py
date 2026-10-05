#!/usr/bin/env python3
"""Keep three inspected diagnostic limitations out of supported formal repairs."""
import json
import shutil
from collections import Counter
import repair_cli as r

def main():
    if (r.HERE/'PLAN.before_source_exceptions.json').exists():raise RuntimeError('Source exception amendment already frozen')
    p=json.loads((r.HERE/'PLAN.json').read_text())
    cases={
        'doc_0ef3ec165703e15b48df':('unresolved','Saved detail repeats ExternalIds 07112753001352/07112753001353 for two different question/reply pairs with distinct ItemIds. Frozen validator overwrites duplicate keys. Complete legacy text retained; subsection/pair identity requires a separately defined correction. No missing original or redownload.'),
        'doc_f308b3448ce327debabe':('unresolved','Saved detail repeats question ExternalId 0606271000413 for two different questions with distinct ItemIds. Frozen validator resolves only the later node. Both legacy texts are already saved; leave source identity ambiguity explicit. No missing original or redownload.'),
        'doc_9e2d4c3363a4075b1553':('confirmed','Actual saved XML member text is Mr. Moynihan; and legacy typed actor is identical. Semicolon is also the locator field delimiter, causing a frozen speaker-comparison artefact. No source speaker mismatch or text repair demonstrated; legacy actor retained.')}
    with r.locks():
        for rec in p['repairs']:
            if rec['document_id'] not in cases:continue
            p.setdefault('source_exception_evidence',[]).append({'document_id':rec['document_id'],'raw_path':rec['raw_path'],'saved_nodes':rec['nodes'],'disposition':cases[rec['document_id']][0],'reason':cases[rec['document_id']][1]})
        p['repairs']=[x for x in p['repairs'] if x['document_id'] not in cases]
        for d in p['dispositions']:
            if d['unit_id'] in cases:d.update(disposition=cases[d['unit_id']][0],resolution=cases[d['unit_id']][1])
        p['source_exception_amendment']={'time_utc':r.now(),'saved_detail_external_id_collision_parents':2,'literal_XML_actor_delimiter_false_positive_parents':1,'supported_repair_projections_removed':3,'raw_and_legacy_unchanged':True}
    for name in ['PLAN.json','DRY_RUN.json','issue_dispositions.csv','INPUT_MANIFEST.json']:
        f=r.HERE/name;shutil.copy2(f,f.with_name(f.stem+'.before_source_exceptions'+f.suffix))
    r.atomic(r.HERE/'PLAN.json',p);r.csvwrite(r.HERE/'issue_dispositions.csv',p['dispositions'],list(p['dispositions'][0]))
    manifest=json.loads((r.HERE/'INPUT_MANIFEST.json').read_text());manifest['source_exception_amendment']=p['source_exception_amendment'];r.atomic(r.HERE/'INPUT_MANIFEST.json',manifest)
    r.atomic(r.HERE/'DRY_RUN.json',{'status':'staged_supported_repairs_with_named_source_exceptions','counts':{k:len(p[k]) for k in ['repairs','dates','states','new_parents','annotations','dispositions','requests']},'dispositions':dict(Counter(d['disposition'] for d in p['dispositions'])),'plan_sha256':r.digest((r.HERE/'PLAN.json').read_bytes())})
    print(r.dump(p['source_exception_amendment']))
if __name__=='__main__':main()
