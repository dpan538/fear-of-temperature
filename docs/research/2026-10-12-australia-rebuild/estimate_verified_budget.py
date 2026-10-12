"""Conditional native-form arithmetic; no model, download or corpus segmentation."""
from pathlib import Path
import json, math, shutil, hashlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
GB=10**9
GIB=2**30

def main():
    sample=json.loads((HERE/'LENGTH_SAMPLE_SUMMARY.json').read_text())
    stock=json.loads((HERE.parent/'2026-10-12-australia-source-freeze/NEWS_PUBLIC_METADATA_SUMMARY.json').read_text())
    groups={g['source_id']:g for g in sample['groups']}
    source_cases=[]
    for window in ['all_saved_AU_candidate_stock','recent_27_full_months']:
        sources=[]
        for stream in ['newspaper','public_community']:
            for s in stock[stream]['by_source']:
                count=s['count'] if window.startswith('all_') else sum(n for m,n in s['source_month_counts'] if '2024-06'<=m<='2026-08')
                if not count:continue
                g=groups[s['source_id']]
                sources.append({'source_id':s['source_id'],'native_units':count,'length_sample_n':g['sample_n'],
                    'conditional_text_bytes':math.ceil(count*g['utf8_bytes']['mean']),
                    'conditional_word_windows':math.ceil(count*g['window220_overlap20_word_proxy']['mean'])})
        source_cases.append({'name':window,'basis':'counts observed in frozen metadata; lengths/windows extrapolate a NONPROBABILITY archive sample and are sensitivity arithmetic, not forecasts or final tokenizer passages',
                            'sources':sources,'conditional_text_bytes':sum(s['conditional_text_bytes'] for s in sources),'conditional_windows':sum(s['conditional_word_windows'] for s in sources)})
    paragraph_sample_path=ROOT/'work_packages/M1_source_access/38_australia_rebuild_verified_20261012/local_government/paragraph_sample_summary.json'
    parliamentary=None
    if paragraph_sample_path.exists():
        j=json.loads(paragraph_sample_path.read_text());rg=j['row_groups']
        mean=sum(r['native_text_utf8_bytes']['total'] for r in rg)/sum(r['rows_decoded'] for r in rg)
        parliamentary={'paragraphs':6911269,'conditional_utf8_bytes_per_paragraph':mean,'conditional_text_bytes':math.ceil(6911269*mean),'sample_rows':sum(r['rows_decoded'] for r in rg),
                       'basis':'known deposit row count; nonrandom2block text mean transferred ONLY as a stress sensitivity. One vector per raw paragraph assumed, including empty/procedural rows; no adopted segmentation/role filter.'}
    assumptions={'source_package_bytes':502442451,'metadata_bytes_per_native_item':600,'lineage_bytes_per_window':400,
                 'passage_text_overlap_factor':1.10,'index_extra_dense_payload_copies':1,'index_graph_and_ID_bytes_per_window':128,
                 'model_cache_bytes':2*GB,'research_outputs_bytes':250_000_000,'unmeasured_media_raw_intake_allowance_bytes':GB,
                 'engineering_shard_rows':100000,'input_shard_buffer_bytes':256*2**20,'database_journal_and_atomic_write_allowance_bytes':512*2**20,
                 'basis':'Explicit unmeasured overhead assumptions. Shard rows bound an operation, not corpus inclusion/count/collector stopping. Replace with observed per-operation and actual index/cache sizes before scaling.'}
    cases=[]
    media=source_cases[0]
    for name,paragraphs,text,windows,native in [('media_community_saved_candidates',0,media['conditional_text_bytes'],media['conditional_windows'],8169+45679)]+(
        [('all_RAPID_paragraphs_plus_media_stress',parliamentary['paragraphs'],media['conditional_text_bytes']+parliamentary['conditional_text_bytes'],media['conditional_windows']+parliamentary['paragraphs'],8169+45679+parliamentary['paragraphs'])] if parliamentary else []):
        for dimensions,index in [(384,False),(384,True),(1024,True)]:
            vector=windows*dimensions*4
            optional_index=vector+128*windows if index else 0
            canonical=text+native*600
            passages=math.ceil(text*1.1)+windows*400
            base=assumptions['source_package_bytes']+assumptions['unmeasured_media_raw_intake_allowance_bytes']+assumptions['model_cache_bytes']+assumptions['research_outputs_bytes']
            retained=base+canonical+passages+vector+optional_index
            scratch=assumptions['input_shard_buffer_bytes']+assumptions['database_journal_and_atomic_write_allowance_bytes']+min(windows,100000)*dimensions*4*2
            cases.append({'name':name,'dimensions':dimensions,'dtype':'float32','build_one_optional_index':index,'conditional_windows':windows,
                          'canonical_text_and_metadata_bytes':canonical,'passages_and_lineage_bytes':passages,'dense_vectors_bytes':vector,'index_bytes':optional_index,
                          'retained_bytes':retained,'streamed_operation_scratch_assumption_bytes':scratch,'conditional_streamed_peak_bytes':retained+scratch,
                          'legacy_additional_whole_dense_matrix_bytes':vector,'conditional_legacy_peak_bytes':retained+scratch+vector,
                          'fits_primary_100GB_streamed_arithmetic':retained+scratch<=100*GB,
                          'runtime_sensitivity_hours_NOT_benchmark':{str(rate):round(windows/rate/3600,2) for rate in [1,10,50]}})
    free=shutil.disk_usage(ROOT).free;floor=15*GIB;recovery=48*2**20
    result={'version':'100GB-primary-native-form-sensitivity-v1','peak_working_ceiling_bytes':100*GB,'publication_interval':['1988-01-01','2026-09-21'],
            'observed_capacity':{'free_bytes':free,'physical_floor_bytes':floor,'recovery_bytes':recovery,'upper_new_operation_headroom_bytes':max(0,free-floor-recovery),'time':'2026-10-12, point-in-time; concurrent work and operation footprints must be rechecked'},
            'media_source_cases':source_cases,'parliamentary_stress_basis':parliamentary,'unmeasured_assumptions':assumptions,'cases':cases,
            'limitations':['No model throughput, peak RAM, tokenizer count, source-representative length or actual index-build peak has been measured.','Exact recent parliamentary paragraph/utterance total remains unknown; sitting counts cannot substitute.','Raw rehydration, additional versions/attachments, backups and index-build copies can exceed these sensitivities; add their simultaneous bytes explicitly before an intake.','AntConc corpus/index export copies are separately measured on a bounded subset; no 100GB tool capacity claim.','Old protected holdings remain outside scientific cap but occupy the same physical disk.'],
            'researcher_effort_estimates':[{'phase':p,'active_hours':[lo,hi]} for p,lo,hi in [('source-rights/native-unit and inventory acceptance',6,12),('clean importer and selective carry-forward',8,16),('structural checks and dated speaker/office mapping',12,28),('AntConc recipe and original-context reading',8,16),('later relevance/passage/model benchmark validation',8,16),('first supported RQ1/RQ2 comparison and evidence review',20,40)]],
            'effort_status':'62–128 active researcher hours is judgement for ready-data path; excludes access waits, unknown supplementation, machine runtime, extended fear annotation and prototype. Not a delivery guarantee.',
            'input_digests':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [HERE/'LENGTH_SAMPLE_SUMMARY.json',HERE.parent/'2026-10-12-australia-source-freeze/NEWS_PUBLIC_METADATA_SUMMARY.json']+([paragraph_sample_path] if paragraph_sample_path.exists() else [])],
            'models_or_bulk_segmentation_executed':False}
    for c in cases:c['fits_current_snapshot_headroom_arithmetic']=c['conditional_streamed_peak_bytes']<=max(0,free-floor-recovery)
    (HERE/'VERIFIED_BUDGET_SENSITIVITY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'current_headroom_GB':(free-floor-recovery)/GB,'media_conditional':[{k:c[k] for k in ['name','conditional_text_bytes','conditional_windows']} for c in source_cases],
                      'cases':[{'name':c['name'],'dimensions':c['dimensions'],'index':c['build_one_optional_index'],'streamed_peak_GB':round(c['conditional_streamed_peak_bytes']/GB,3),'legacy_peak_GB':round(c['conditional_legacy_peak_bytes']/GB,3)} for c in cases]},indent=2))

if __name__=='__main__':main()
