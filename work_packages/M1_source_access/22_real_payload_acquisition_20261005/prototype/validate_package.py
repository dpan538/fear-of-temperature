"""Final changed-tranche consistency check, reusing new raw hash receipts."""
import ast,csv,json
from collections import Counter
import transport as t

def rows(name):return list(csv.DictReader((t.OUT/name).open()))
def main():
 scope=t.read(t.SCOPE);articles=rows('media/ARTICLE_MANIFEST.csv');q=rows('media/QUOTA_TABLE.csv');mapping=rows('media/CANDIDATE_SLOT_MAPPING.csv');gov=rows('government/TRANSPORT_AND_CHECK_LEDGER.csv');raw=rows('RAW_MANIFEST.csv');byraw={x['path']:x for x in raw}
 req=[t.read(p) for lane in ['media','government'] for p in (t.OUT/lane/'requests').glob('*.json')];frames=[t.read(p) for p in (t.OUT/'media/frames').glob('*.json')]
 checks={}
 checks['fixed_publication_interval']=scope['publication_interval']==['1988-01-01','2026-09-21']
 checks['real_body_attempts']=len(articles)==42 and sum(x['complete_visible_prose']=='True' for x in articles)==30
 checks['body_statuses_reconcile']=sum(x['transport_status']=='saved' for x in articles)==41 and sum(x['http_status']=='404' for x in articles)==1
 checks['original150_preserved']=len(mapping)==150 and all(x['original_source_success']=='False' for x in mapping)
 checks['original_quota_cells']=len(q)==15 and sum(int(x['original_quota']) for x in q)==150 and all(int(x['quota_transfer'])==0 for x in q)
 checks['candidate_coordinate_reconciliation']=sum(int(x['candidate_verified_prose']) for x in q)==30 and sum(int(x['candidate_body_attempts']) for x in q)==42 and sum(int(x['candidate_unattempted_frozen']) for x in q)==2
 cats=t.read(t.OUT/'control/CANDIDATES.json')['candidates'];checks['candidate_cap']=max(Counter(c['stratum'] for c in cats).values())<=2
 checks['body_cell_cap_and_months']=all(n<=5 for n in Counter((x['source_id'],x['publication_month']) for x in articles).values()) and all(x['publication_month'] in scope['original_months'] for x in articles)
 checks['frozen_target_counts']=sum(len(f['selected']) for f in frames)==44 and all(len(f['selected'])<=5 for f in frames)
 checks['requests_bound_to_selected_frames']=all(any(f['source_id']==r['source_id'] and f['month']==r['publication_month'] and r['request_url'] in [x['url'] for x in f['selected']] for f in frames) for r in req if r['purpose']=='body')
 checks['live_body_frame_hashes_preserved']=all(t.digest(t.OUT/r['frame_path'])==r['frame_sha256'] for r in req if r['purpose']=='body')
 checks['metadata_and_search_caps']=all(sum(max(1,len(r.get('hops',[]))) for r in req if r['source_id']==c['source_id'] and r['purpose']!='body')<=20 and sum(r['request_url'].startswith('web-search:') for r in req if r['source_id']==c['source_id'])<=3 for c in cats)
 checks['raw_receipts_and_manifest_agree']=all(all(r.get('sha256' if k=='raw_path' else 'partial_sha256',byraw[r[k]]['sha256'])==byraw[r[k]]['sha256'] for k in ['raw_path','partial_path'] if r.get(k)) for r in req)
 checks['retained_new_raw_files_present_and_sizes']=all((t.OUT/r['path']).is_file() and (t.OUT/r['path']).stat().st_size==int(r['bytes']) for r in raw)
 checks['complete_body_files_and_hashes']=all(t.digest(t.OUT/a['body_path'])==a['body_sha256'] and (t.OUT/a['body_path']).stat().st_size==int(a['body_bytes']) for a in articles if a['complete_visible_prose']=='True')
 checks['complete_body_hashes_distinct']=len({a['body_sha256'] for a in articles if a['complete_visible_prose']=='True'})==30
 target=t.read(t.OUT/'government/TARGET_SEQUENCE.json')['targets'];checks['government_exact_bounded_order']=len(gov)==11 and [r['item_uri'] for r in gov]==[r['item_uri'] for r in target]
 checks['government_dates_and_no_complete_Work']=all(r['printed_publication_date']==r['cdm_publication_date'] and r['complete_Work_verified']=='False' and r['formal_ingestion']=='False' and r['http_status']=='200' for r in gov)
 checks['known_genre_conflicts_exposed']=sum(r['provenance_check']=='conflicting inherited genre/issuer mapping' for r in gov)==5
 checks['network_closed_and_failed_milestone']=t.read(t.OUT/'control/NETWORK_CLOSED.json')['offline_packaging_only'] and t.read(t.OUT/'control/FIRST_MILESTONE.json')['first30minute_verified_chains']==0
 checks['registered_public_inputs_unchanged']=all(t.digest(t.ROOT/r['path'])==r['sha256'] for r in t.read(t.OUT/'control/INPUT_RECEIPT.json')['files'])
 for p in (t.OUT/'prototype').glob('*.py'):ast.parse(p.read_text())
 checks['code_syntax']=True
 validation=t.read(t.OUT/'control/OFFLINE_VALIDATION.json');checks['24_targeted_tests']=validation['passed'] and validation['targeted_test_count']==24
 storage=t.budget();checks['original_reserves_and_floor']=storage['passed']
 result=dict(at_utc=t.now().isoformat(),checks=checks,passed=all(checks.values()),known_unresolved=['Partial date frames and unknown denominators/probabilities','Rights/ownership/HQ/components qualified per source','Five inherited government genre conflicts','Search capture and initial underenumeration limitations','Historical content-version equivalence unproven'],new_raw_hash_method='Reuse the once-built physical new-object RAW_MANIFEST and per-request hashes; no old government raw read',body_hash_method='Changed30 derived fulltext files checked against certification hashes',formal_database_access=False,private_evaluator_access=False)
 t.save(t.OUT/'control/FINAL_VALIDATION.json',result);t.save(t.OUT/'control/FINAL_STORAGE.json',storage)
 print(json.dumps(result,indent=2));assert result['passed']
if __name__=='__main__':main()
