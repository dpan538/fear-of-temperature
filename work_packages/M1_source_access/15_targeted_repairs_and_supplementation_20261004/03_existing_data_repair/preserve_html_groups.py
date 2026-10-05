#!/usr/bin/env python3
"""Pre-commit conservation amendment for groups already swallowed by flagged parents."""
import json
import shutil
from collections import defaultdict,Counter
import duckdb
import repair_cli as r

def main():
    if (r.HERE/'PLAN.before_html_conservation.json').exists():raise RuntimeError('HTML conservation amendment already frozen')
    p=json.loads((r.HERE/'PLAN.json').read_text());recovered=[];seen=set()
    with r.locks():
        r.verify_checkpoints(p)
        c=duckdb.connect(str(r.DB),read_only=True);c.execute("SET TimeZone='UTC'")
        repairs=[x for x in p['repairs'] if x['raw_path'].endswith(('.htm','.html'))]
        groups={x['raw_path']:r.item_groups(r.ROOT/x['raw_path']) for x in repairs}
        dates=sorted({g['date'] for gs in groups.values() for g in gs.values()});pd=r.rows(c,'SELECT document_id,source_id,publication_date,external_id FROM documents WHERE publication_date IN (SELECT unnest(?)::DATE)',[dates]);pm={x['document_id']:x for x in pd};ss=r.get_segments(c,set(pm));signatures=defaultdict(list)
        for pid,segs in ss.items():signatures[(str(pm[pid]['publication_date']),tuple(('question' if r.diagnostic.locator_parts(s['locator'])[0]=='question_context' else 'response',r.clean(s['segment_text']).casefold()) for s in segs))].append(pid)
        for old in repairs:
            pid=old['document_id'];doc=p['before_images'][pid]['document'];before=p['before_images'][pid]['segments'];oldids={r.diagnostic.locator_parts(s['locator'])[1] for s in before}
            for g in groups[old['raw_path']].values():
                if g['key']==old['original_group_id']:continue
                k=g['key'];source=doc['source_id'];newid=r.sid('doc',source,k)
                if (source,k) in seen:raise RuntimeError('Original group repeated across flagged item parents')
                seen.add((source,k))
                if k not in oldids:raise RuntimeError('Extra HTML group falls outside already stored child-node scope')
                existing=[x for x in pd if x['source_id']==source and x['external_id']==k]
                matched=signatures[(g['date'],r.signature(g['nodes']))]
                if existing or matched:raise RuntimeError('Already represented original group requires explicit ownership reconciliation: '+k)
                if g['date']!=doc['publication_date']:raise RuntimeError('Independent item citation date differs from selected parent date')
                department=c.execute("SELECT json_extract_string(normalised_payload_json,'$.department') FROM document_versions WHERE document_id=? AND is_current",[pid]).fetchone()[0]
                if department not in r.diagnostic.DEPARTMENTS:raise RuntimeError('Extra group outside frozen department frame')
                url=doc['canonical_url'].split('#',1)[0]+'#'+k
                if c.execute('SELECT count(*) FROM documents WHERE document_id=? OR canonical_url=?',[newid,url]).fetchone()[0]:raise RuntimeError('Stable new group identity collision')
                newdoc={**doc,'document_id':newid,'external_id':k,'canonical_url':url,'publication_timestamp':None,'publication_date_basis':'independent visible saved Historic item citation','deduplication_status':'existing_child_node_repartitioned_to_exact_original_group','source_overlap_status':'no_separately_registered_source_id_or_exact_dated_full_question_reply','body_status_reason':'Already saved utterance formerly swallowed by flagged parent; repartitioned in repair layer'}
                cv=next(v for v in p['before_images'][pid]['links'] if v['content_version_id']==old['content_version_id'])
                n={'document':newdoc,'content_object_id':cv['content_object_id'],'content_version_id':old['content_version_id'],'raw_path':old['raw_path'],'original_group_id':k,'department':department,'nodes':g['nodes'],'retrieved_at':cv['retrieved_at'],'derived_at':r.now(),'original_date_heading':g['date'],'date_support':'visible_item_citation','canonical_url_basis':'existing saved item route with original paragraph anchor; reachability not freshly checked','omission_issue_id':pid,'recovery_type':'repartition_existing_HTML_child_group','former_parent_document_id':pid}
                p['new_parents'].append(n);recovered.append({'former_parent_document_id':pid,'new_document_id':newid,'original_group_id':k,'date':g['date'],'raw_path':old['raw_path'],'old_response_node_present':True,'separate_parent_absent':True,'exact_dated_signature_absent':True,'source_node_ids':[v['node_id'] for v in g['nodes']]})
        c.close()
        p['html_conservation_amendment']={'time_utc':r.now(),'flagged_saved_item_pages_checked':len(groups),'already_stored_other_question_reply_groups_repartitioned':len(recovered),'date_scoped_cross_source_peers_checked':len(pd),'scope':'Only other groups with a reply node already present in a flagged legacy parent; no new HTML acquisition or uncollected item expansion.'}
        # Source-conservation evidence attaches to the initial issue, not 82 new
        # accusations or duplicate imports in the frozen coordinator ledger.
        for d in p['dispositions']:
            extra=[x['new_document_id'] for x in recovered if x['former_parent_document_id']==d['unit_id']]
            if extra and d['category']=='reply_role_or_boundary':d['resolution']+=' Other already stored original groups retained as independent derived parents: '+','.join(extra)
    for name in ['PLAN.json','DRY_RUN.json','issue_dispositions.csv','INPUT_MANIFEST.json']:
        f=r.HERE/name;shutil.copy2(f,f.with_name(f.stem+'.before_html_conservation'+f.suffix))
    r.atomic(r.HERE/'PLAN.json',p)
    r.csvwrite(r.HERE/'html_group_repartition.csv',recovered,list(recovered[0]))
    r.csvwrite(r.HERE/'issue_dispositions.csv',p['dispositions'],list(p['dispositions'][0]))
    manifest=json.loads((r.HERE/'INPUT_MANIFEST.json').read_text());manifest['html_conservation_amendment']=p['html_conservation_amendment'];r.atomic(r.HERE/'INPUT_MANIFEST.json',manifest)
    result={'status':'staged_checked_with_original_group_conservation','counts':{k:len(p[k]) for k in ['repairs','dates','states','new_parents','annotations','dispositions','requests']},'dispositions':dict(Counter(d['disposition'] for d in p['dispositions'])),'plan_sha256':r.digest((r.HERE/'PLAN.json').read_bytes()),'html_amendment':p['html_conservation_amendment']}
    r.atomic(r.HERE/'DRY_RUN.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
