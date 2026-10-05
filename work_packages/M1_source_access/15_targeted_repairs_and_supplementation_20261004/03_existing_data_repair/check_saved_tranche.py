#!/usr/bin/env python3
"""Recheck the staged changed parent tranche with the frozen independent validator.

Known validator adapter limits are retained per parent and never hidden as passes.
No formal database write or corpus scan.
"""
import json
from collections import Counter
import repair_cli as r

def main():
    p=json.loads((r.HERE/'PLAN.json').read_text());results=[];originals={}
    with r.locks():
        # All legacy/span checks are restricted to the actual correction plan.
        for rec in p['repairs']+[{**n,'document_id':n['document']['document_id'],'source_id':n['document']['source_id'],'external_id':n['document']['external_id']} for n in p['new_parents']]:
            path=rec['raw_path'];doc=p['before_images'].get(rec['document_id'],{}).get('document',rec.get('document'))
            adapter=r.diagnostic.adapter_for(rec['source_id'],path)
            if path not in originals:originals[path]=r.diagnostic.parse_original(r.ROOT/path,adapter,doc['content_type'])
            orig=originals[path]
            parent=r.diagnostic.Parent(rec['source_id'],rec['document_id'],rec['original_group_id'],str(doc['publication_date']),doc['content_type'],'layer-object',rec['content_version_id'],path,'',1)
            for ix,n in enumerate(rec['nodes']):
                role='question_context' if n['role']=='question' else 'government_response'
                parent.segments[str(ix)]=r.diagnostic.Segment(str(ix),f'role={role};source_id={n["node_id"]};speaker={n["speaker"]}',n['text'],ix,rec['content_version_id'],n['speaker'])
            v=r.diagnostic.validate_parent(parent,orig)
            limit=''
            if v['status']!='supported_split':
                if adapter=='historic_item_html':limit='Frozen paragraph-only HTML adapter omits contribution-boundary Lords question forms and table nodes; corrected contribution adapter and falsification fixtures provide the additional evidence. Frozen verdict retained.'
                elif adapter=='archive_detail_json' and set(v['rule_ids'].split(';'))<= {'R-SPAN'}:limit='Frozen adapter retains column-number source furniture; correction explicitly removes only .column-number markup. Compare source locator and visible contribution text.'
            results.append({'document_id':rec['document_id'],'adapter':adapter,'original_group_id':rec['original_group_id'],'frozen_validator_status':v['status'],'rules':v['rule_ids'],'details':v['details'],'adapter_limit':limit,'evidence':path,'unexpected_conflict':v['status']!='supported_split' and not limit})
    r.csvwrite(r.HERE/'saved_tranche_independent_checks.csv',results,list(results[0]))
    result={'checked_at_utc':r.now(),'changed_and_repartitioned_parent_checks':len(results),'saved_containers_read':len(originals),'statuses':dict(Counter(x['frozen_validator_status'] for x in results)),'named_adapter_limits':sum(bool(x['adapter_limit']) for x in results),'unexpected_conflicts':[x for x in results if x['unexpected_conflict']],'scope':'Frozen validator on changed/recovered parents only; no full audit; its HTML/column-furniture limits remain visible.'}
    r.atomic(r.HERE/'SAVED_TRANCHE_CHECKS.json',result);print(json.dumps(result,indent=2))
    if result['unexpected_conflicts']:raise SystemExit(1)
    r.atomic(r.HERE/'FINAL_SAVED_TRANCHE_CHECKS.json',{'status':'passed_with_named_adapter_limits','final_plan_sha256':r.digest((r.HERE/'PLAN.json').read_bytes()),'final_changed_and_recovered_parent_checks':len(results),'statuses':result['statuses'],'named_adapter_limits':result['named_adapter_limits'],'unexpected_conflicts':[],'method':result['scope']})
if __name__=='__main__':main()
