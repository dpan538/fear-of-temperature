#!/usr/bin/env python3
"""Preserved, bounded pre-commit amendment: five omission ZIPs and AU/route evidence.

Does not repeat the main source audit. Keeps PLAN.initial.json and initial CSVs.
"""
import json
import re
import shutil
from collections import Counter,defaultdict
from datetime import datetime
import duckdb
import repair_cli as r

def main():
    if (r.HERE/'PLAN.initial.json').exists():raise RuntimeError('Amendment already frozen')
    p=json.loads((r.HERE/'PLAN.json').read_text())
    with r.locks():
        r.verify_checkpoints(p)
        c=duckdb.connect(str(r.DB),read_only=True);c.execute("SET TimeZone='UTC'")
        candidates=[t for t in p['dispositions'] if t['category']=='candidate_saved_original_omission']
        gs={path:r.xml_groups(r.ROOT/path)[0] for path in {t['unit_id'].rsplit('#',1)[0] for t in candidates}}
        ids=[t['unit_id'].rsplit('#',1)[1] for t in candidates]
        registered={a['external_id'] for a in r.rows(c,'SELECT external_id FROM documents WHERE external_id IN (SELECT unnest(?))',[ids])}
        owners={a['node_id'] for a in r.rows(c,"SELECT regexp_extract(s.locator,'source_id=([^;]+)',1) node_id FROM voice_attributions a JOIN text_segments s USING(segment_id) WHERE regexp_extract(s.locator,'source_id=([^;]+)',1) IN (SELECT unnest(?))",[ids])}
        dates=sorted({g['date'] for groups in gs.values() for g in groups.values() if g['key'] in ids})
        peers=r.rows(c,'SELECT document_id,source_id,publication_date FROM documents WHERE publication_date IN (SELECT unnest(?)::DATE)',[dates]);pd={x['document_id']:x for x in peers};ss=r.get_segments(c,set(pd));sigs=defaultdict(list)
        for pid,seg in ss.items():
            key=(str(pd[pid]['publication_date']),tuple(('question' if r.diagnostic.locator_parts(s['locator'])[0]=='question_context' else 'response',r.clean(s['segment_text']).casefold()) for s in seg));sigs[key].append(pid)
        omissions=[]
        for t in candidates:
            path,key=t['unit_id'].rsplit('#',1);g=gs[path][key];day,basis=r.single_saved_day(g)
            if key in registered or key in owners:raise RuntimeError('Candidate now represented; checkpoint cannot be amended as absent: '+key)
            if sigs[(g['date'],r.signature(g['nodes']))]:t.update(disposition='confirmed',resolution='Exact dated full question/reply already represented: '+r.dump(sigs[(g['date'],r.signature(g['nodes']))]));continue
            if g.get('department') not in r.diagnostic.DEPARTMENTS or not day or day!=g['date']:
                t.update(disposition='unresolved',resolution='Saved explicit day cannot be corroborated without inventing a date: '+basis);continue
            cv=r.rows(c,'SELECT * FROM content_versions WHERE raw_path=?',[path])
            if len(cv)!=1:raise RuntimeError('Ambiguous saved volume content version')
            cv=cv[0];source=t['source'];pid=r.sid('doc',source,key);dt=datetime.fromisoformat(day);slug=re.sub(r'[^a-z0-9]+','-',g['title'].lower()).strip('-')
            url=f'https://api.parliament.uk/historic-hansard/written-answers/{dt.year}/{dt.strftime("%b").lower()}/{dt.day:02d}/{slug}#{key}'
            if c.execute('SELECT count(*) FROM documents WHERE document_id=? OR canonical_url=?',[pid,url]).fetchone()[0]:raise RuntimeError('Stable identity/canonical collision')
            template=r.rows(c,'SELECT d.* FROM documents d JOIN document_content_objects x USING(document_id) WHERE x.content_object_id=? LIMIT 1',[cv['content_object_id']])[0]
            doc={**template,'document_id':pid,'source_id':source,'external_id':key,'canonical_url':url,'title':g['title'],'publication_date':day,'publication_timestamp':None,'publication_date_basis':'exact saved XML format corroborated by single day/month/weekday; '+basis,'collected_at':str(cv['retrieved_at']),'updated_timestamp':None,'deduplication_status':'exact_source_node_and_dated_full_text_checked','source_overlap_status':'no_exact_dated_full_question_reply_match_in_saved_UK_frame','body_status':'downloaded_and_extracted','body_status_reason':'Locally recovered saved ZIP original in versioned repair layer'}
            n={'document':doc,'content_object_id':cv['content_object_id'],'content_version_id':cv['content_version_id'],'raw_path':path,'original_group_id':key,'department':g['department'],'nodes':g['nodes'],'retrieved_at':str(cv['retrieved_at']),'derived_at':r.now(),'original_date_heading':g['date_heading'],'saved_date_attribute':g['date_attribute'],'date_support':basis,'canonical_url_basis':'locally reconstructed historic route and original paragraph anchor; URL reachability untested','omission_issue_id':t['unit_id']}
            p['new_parents'].append(n)
            t.update(disposition='repaired',resolution='Eligible exact typed source date, corroborated by single day/month/weekday heading; prior exclusions, source-node ownership and exact dated cross-source question/reply signatures checked. Locally recovered parent; '+basis)
            omissions.append({'unit_id':t['unit_id'],'document_id':pid,'source_date':day,'saved_date_attribute':g['date_attribute'],'original_date_heading':g['date_heading'],'date_support':basis,'department':g['department'],'source_nodes':[x['node_id'] for x in g['nodes']],'same_id_registered':False,'reply_node_owner_present':False,'full_dated_overlap_parent_ids':[],'disposition':'repaired'})
        c.close()
        # Correct detail-section vs contribution IDs; retain the earlier HTTP400 route evidence.
        for req in p['requests']:
            if req['request_type']!='named_missing_detail':continue
            m=re.search(r'/written-statements/([^/]+)/',req['canonical_url']);section=m[1]
            child=p['before_images'][req['unit_id']]['document']['external_id']
            fp=r.BASE/f'07_historical_government_acquisition/raw/hansard_api/details/{req["source_date"][:4]}/{section}.json.fetch.json'
            prior=json.loads(fp.read_text());p['inputs'].append(r.stamp(fp,True))
            req['requested_original']=f'Hansard statement section ExtId {section}, contribution anchor {child}, date {req["source_date"]}'
            req['why_existing_evidence_insufficient']='Search-derived statement text is saved, but no section original/body nodes; prior detail request HTTP400. Seek a documented alternate original route, not a blind repeated request.'
            req['existing_evidence']+=';'+r.dump(prior)
        # AU originals already exist: annotate current availability and author/host
        # relationships from their first two saved pages. No redownload request.
        ua=duckdb.connect(str(r.USDB),read_only=True)
        auids={d['unit_id'] for d in p['dispositions'] if d['source']=='au_dcceew_current_catalogue_2026_snapshot' and d['category'] in ('STATUS','ISSUER')}
        for pid in auids:
            page=r.rows(ua,"SELECT DISTINCT s.content_version_id,s.locator,s.segment_text FROM document_content_objects x JOIN content_versions cv USING(content_object_id) JOIN text_segments s USING(content_version_id) WHERE document_id=? AND (s.locator LIKE 'page=1;%' OR s.locator LIKE 'page=2;%') ORDER BY s.content_version_id,s.locator",[pid])
            p.setdefault('companion_saved_page_evidence',[]).append({'unit_id':pid,'saved_pages':page})
            for d in p['dispositions']:
                if d['unit_id']!=pid:continue
                if d['category']=='STATUS' and page:
                    d.update(disposition='confirmed',resolution='Existing primary/attachment PDF text is saved; historical body label retained. Current technical availability saved_text_available is recorded additively in this provenance annotation; US/AU DB unchanged.')
                elif d['category']=='ISSUER':
                    d.update(disposition='unresolved',resolution='Saved original title page lists Pillans, Stevens, Kyne and Salini, CSIRO Marine Research and University of Queensland affiliations, August 2005. Page2 explicitly separates authors\x27 opinions from Australian Government/Minister. Government host is not authorial issuer; formal publisher/commissioning role remains unverified. Existing original is present; no download needed.')
            for v in r.rows(ua,'SELECT cv.raw_path FROM document_content_objects x JOIN content_versions cv USING(content_object_id) WHERE document_id=?',[pid]):p['inputs'].append(r.stamp(r.ROOT/v['raw_path']))
        ua.close()
        p['requests']=[q for q in p['requests'] if q['request_type']!='issuer']
        dm={(d['unit_id'],d['category']):d for d in p['dispositions']}
        for a in p['annotations']:
            d=dm[(a['unit_id'],a['rule_id'])];a.update(disposition=d['disposition'],resolution=d['resolution'])
        p['amendment']={'at_utc':r.now(),'reason':'Exact saved date-format fields corroborated against non-range day/month/weekday; source heading typos retained. Existing AU originals inspected; section/child original requests corrected.','new_saved_ZIP_containers_checked':5,'all_existing_parent_span_scan_repeated':False,'omission_cross_source_date_scoped_parents_checked':len(peers)}
    for name in ['PLAN.json','DRY_RUN.json','issue_dispositions.csv','missing_original_requests.csv','INPUT_MANIFEST.json']:
        f=r.HERE/name;shutil.copy2(f,f.with_name(f.stem+'.initial'+f.suffix))
    r.atomic(r.HERE/'PLAN.json',p)
    r.csvwrite(r.HERE/'omission_dispositions.csv',omissions,list(omissions[0]))
    r.csvwrite(r.HERE/'issue_dispositions.csv',p['dispositions'],list(p['dispositions'][0]))
    r.csvwrite(r.HERE/'missing_original_requests.csv',p['requests'],['unit_id','source_id','source_date','canonical_url','requested_original','why_existing_evidence_insufficient','existing_evidence','request_type','priority'])
    manifest=json.loads((r.HERE/'INPUT_MANIFEST.json').read_text());manifest.update(inputs=p['inputs'],amendment=p['amendment']);r.atomic(r.HERE/'INPUT_MANIFEST.json',manifest)
    summary={'status':'staged_checked_plan_after_bounded_amendment','counts':{k:len(p[k]) for k in ['repairs','dates','states','new_parents','annotations','dispositions','requests']},'dispositions':dict(Counter(d['disposition'] for d in p['dispositions'])),'plan_bytes':(r.HERE/'PLAN.json').stat().st_size,'plan_sha256':r.digest((r.HERE/'PLAN.json').read_bytes())}
    r.atomic(r.HERE/'DRY_RUN.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
