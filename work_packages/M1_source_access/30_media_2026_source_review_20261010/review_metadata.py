"""Reproduce advisory review marks from pinned closed metadata only."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent
PIN=OUT/'worker/pinned'
MONTHS=[f'{y:04}-{m:02}' for y in range(1988,2027) for m in range(1,13) if f'{y:04}-{m:02}'<='2026-09']

def read(name):
    with (PIN/name).open(newline='') as f:return list(csv.DictReader(f))

def save(name, rows):
    with (OUT/name).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    pin=json.loads((OUT/'worker/INPUT_PIN_MANIFEST.json').read_text())
    for item in pin['copies']:
        assert hashlib.sha256((OUT/item['path']).read_bytes()).hexdigest()==item['sha256'],item
    nsum=json.loads((PIN/'np9_summary.json').read_text())
    ssum=json.loads((PIN/'s9_collection_manifest.json').read_text())
    four=json.loads((PIN/'s4_collection_manifest.json').read_text())
    snapshots={'np9_closed':nsum['at_utc'],'s9_closed':ssum['snapshot_at_utc'],'s4_closed_pre_resume':four['snapshot_at_utc']}
    collections={}
    for snapshot,stream in [('np9_closed','newspaper'),('s9_closed','social')]:
        collections[snapshot]={}
        for row in read('p29_source_month.csv'):
            if row['stream']==stream:collections[snapshot][row['source_id'],row['month']]=int(row['bodies'])
    collections['s4_closed_pre_resume']={(r['source_id'],r['month']):int(r['usable_dated_independent_bodies']) for r in read('s4_source_month_calendar.csv')}
    contributing={snap:sorted({s for (s,m),count in data.items() if m.startswith('2026-') and count>0}) for snap,data in collections.items()}
    assert len(contributing['np9_closed'])==2
    assert contributing['s9_closed']==contributing['s4_closed_pre_resume']
    context=[];marks=[];monthly=defaultdict(dict)
    for snap,data in collections.items():
        stream='newspaper' if snap=='np9_closed' else 'social'
        for month in MONTHS:monthly[snap][month]=sum(v for (s,m),v in data.items() if m==month)
        for source in contributing[snap]:
            nonzero=[m for (s,m),n in data.items() if s==source and n>0]
            for month in [m for m in MONTHS if m.startswith('2026-')]:
                count=data.get((source,month),0);i=MONTHS.index(month)
                neighbors=[MONTHS[j] for j in range(i-3,i+4) if 0<=j<len(MONTHS) and j!=i]
                vals=[data.get((source,m),0) for m in neighbors]
                mean=sum(vals)/len(vals);ratio=count/mean if mean else None
                reasons=['SOURCE_FRAME_COUNTS_NOT_POPULATION'];status='confirmed';action='retain'
                if month=='2026-09':reasons.append('PARTIAL_SEPTEMBER_FIXED_CUTOFF')
                if len(neighbors)<6:reasons.append('ADJACENT_CONTEXT_BOUNDARY_INCOMPLETE')
                if source.startswith('mastodon_'):
                    reasons.append('RECENT_FIRST_LOCAL_TIMELINE_FRONTIER');action='retain_with_context'
                    if count==0:reasons.append('EARLIER_FRONTIER_UNOBSERVED_NOT_SOURCE_ABSENCE')
                if ratio is not None and ratio>=3 and count>0:
                    reasons.append('SAME_SOURCE_ADJACENT_HIGH_COUNT_CANDIDATE');action='retain_with_context'
                if source=='bluesky':reasons.append('CLIENT_DECLARED_NATIVE_TIMESTAMP')
                if source=='northern_rivers_times':reasons.append('PUBLISHER_ORGANIZATION_VALID_TIME_UNRESOLVED')
                marks.append({'mark_id':f'{snap}:{source}:{month}','review_scope':'source_month_aggregate',
                              'snapshot_id':snap,'snapshot_at_utc':snapshots[snap],'stream':stream,'source_id':source,
                              'month':month,'count':count,'counting_unit':'complete_article_ID' if stream=='newspaper' else 'usable_dated_independent_body',
                              'evidence_status':status,'reason_codes':';'.join(reasons),'recommended_next_action':action,
                              'native_date_status':'not_universally_verified','body_content_status':'unreviewed',
                              'event_attribution':'unassessed','parent_provenance_status':'see_separate_parent_dimension_assertions',
                              'first_observed_source_month':min(nonzero),'last_observed_source_month':max(nonzero),
                              'preceding_following_months':'|'.join(neighbors),'neighbor_count':len(neighbors),
                              'neighbor_mean':mean,'ratio_to_neighbor_mean':ratio if ratio is not None else '',
                              'source_era_completeness':'unknown','invalidity_confirmed':False,
                              'evidence_locator':'worker/pinned/p29_source_month.csv' if snap!='s4_closed_pre_resume' else 'worker/pinned/s4_source_month_calendar.csv'})
    save('2026_SOURCE_MONTH_MARKS.csv',marks)
    n=read('np9_2026_metadata.csv')
    assert len(n)==837 and len({r['article_id'] for r in n})==837
    keys={key:defaultdict(list) for key in ['source_url','body_sha256','work_family_id','version_id']}
    for row in n:
        for key in keys:
            if row[key]:keys[key][row[key]].append(row['article_id'])
    records=[];mismatches=[]
    for row in n:
        date.fromisoformat(row['publication_date'])
        assert '2026-01-01'<=row['publication_date']<='2026-09-21'
        codes=['METADATA_ID_DATE_UNIT_CHECKED_NATIVE_ORIGINAL_UNREVIEWED'];action='verify_native_date';counterparts=[]
        for key in ['source_url','body_sha256','work_family_id']:
            ids=keys[key].get(row[key],[]) if row[key] else []
            if len(ids)>1:
                codes.append({'source_url':'SAME_SOURCE_URL_CANDIDATE','body_sha256':'EXACT_BODY_HASH_CANDIDATE','work_family_id':'KNOWN_WORK_MEMBERSHIP_MULTIPLICITY'}[key])
                counterparts+= [x for x in ids if x!=row['article_id']]
                if key=='body_sha256':action='link_alias_candidate'
        conflicts=[]
        for key in ['publisher_timestamp','url_date']:
            val=row.get(key,'')[:10]
            try:date.fromisoformat(val)
            except ValueError:continue
            if val!=row['publication_date']:conflicts.append(key+'='+val)
        if conflicts:codes.append('METADATA_DATE_FIELD_CONFLICT');mismatches.append(row['article_id']);action='verify_native_date'
        records.append({'record_id':row['article_id'],'source_id':row['source_id'],'snapshot_id':'np9_closed',
                        'source_url':row['source_url'],'reported_native_publication_time':row['publication_date'],
                        'review_scope':'closed_export_metadata_only','evidence_status':'supported_candidate' if counterparts or conflicts else 'confirmed',
                        'reason_codes':';'.join(codes),'recommended_next_action':action,'invalidity_confirmed':False,
                        'native_original_body_read':False,'historical_content_equivalence':'unresolved',
                        'checked_fields':'ID uniqueness; ISO publication day; fixed interval; URL/work/version/hash grouping; reported date field comparison',
                        'counterpart_ids':'|'.join(sorted(set(counterparts))),'date_conflict_details':';'.join(conflicts),
                        'evidence_locator':'worker/pinned/np9_2026_metadata.csv#article_id='+row['article_id']})
    samples=read('s9_2026_endpoint_sample.csv')
    for row in samples:
        in_interval='2026-01-01'<=row['native_created_at'][:10]<='2026-09-21'
        date.fromisoformat(row['native_created_at'][:10])
        records.append({'record_id':row['entity_id'],'source_id':row['source_id'],'snapshot_id':'s9_closed',
                        'source_url':row['source_url'],'reported_native_publication_time':row['native_created_at'],
                        'review_scope':'deterministic_earliest_latest_native_entity_metadata_sample','evidence_status':'confirmed',
                        'reason_codes':'METADATA_NATIVE_TIME_CHECKED_ORIGINAL_UNREVIEWED'+('' if in_interval else ';NATIVE_CATALOG_CONTEXT_AFTER_FIXED_CUTOFF_BODY_MEMBERSHIP_UNCHECKED'),
                        'recommended_next_action':'verify_native_date' if in_interval else 'retain_with_context','invalidity_confirmed':False,'native_original_body_read':False,
                        'historical_content_equivalence':'unresolved','checked_fields':'reported native entity/time/URL; fixed interval; first retrieval; role unknown retained',
                        'counterpart_ids':'','date_conflict_details':'',
                        'evidence_locator':'worker/pinned/s9_2026_endpoint_sample.csv#entity_id='+row['entity_id']})
    save('2026_RECORD_MARKS.csv',records)
    totals={snap:{'total':sum(data.values()),'year2026':sum(v for (s,m),v in data.items() if m.startswith('2026-')),
                  'september2026':monthly[snap]['2026-09'],'sources_in_2026':len(contributing[snap])} for snap,data in collections.items()}
    for d in totals.values():d['year2026_share']=d['year2026']/d['total']
    deltas=[]
    for source in contributing['s9_closed']:
        old=sum(v for (s,m),v in collections['s9_closed'].items() if s==source and m.startswith('2026-'))
        new=sum(v for (s,m),v in collections['s4_closed_pre_resume'].items() if s==source and m.startswith('2026-'))
        deltas.append({'source_id':source,'s9_2026_dated_bodies':old,'s4_2026_dated_bodies':new,'added_2026_dated_bodies':new-old})
    save('2026_SOCIAL_SNAPSHOT_COMPARISON.csv',deltas)
    aug=monthly['s9_closed']['2026-08'];sep=monthly['s9_closed']['2026-09']
    diagnostics={'scope':'initial metadata-only diagnostic pass; final named-native scope is REVIEW_LIMITS.json',
                 'snapshots':snapshots,'totals':totals,'newspaper_metadata_rows':len(n),
                 'newspaper_duplicate_IDs':0,'newspaper_group_multiplicity':{key:[ids for ids in val.values() if len(ids)>1] for key,val in keys.items()},
                 'newspaper_reported_date_conflicts':mismatches,
                 'newspaper_missing_metadata_fields':{key:sum(not r.get(key) for r in n) for key in ['raw_reference','publisher_timestamp','content_version_time','date_field','url_date']},
                 'social_selected_native_entities':len(samples),'record_mark_rows':len(records),'source_month_mark_rows':len(marks),
                 'social_sample_after_fixed_cutoff':sum(r['native_created_at'][:10]>'2026-09-21' for r in samples),
                 'same_source_high_count_candidates':[r['mark_id'] for r in marks if 'SAME_SOURCE_ADJACENT_HIGH_COUNT_CANDIDATE' in r['reason_codes']],
                 's9_august_september':{'august':aug,'september':sep,'delta':sep-aug},
                 'unreviewed':'All original bodies; social entities outside selected sample; later append/resume phases; active newspaper; complete parent history; federation same-work mapping; semantic validity; population denominators.',
                 'no_corpus_mutation':True,'no_collectors_contacted':True,'no_composite_score':True}
    with (OUT/'DIAGNOSTICS.json').open('x') as f:f.write(json.dumps(diagnostics,indent=2)+'\n')
    print(json.dumps(diagnostics,indent=2))

if __name__=='__main__':main()
