"""Derive requested geographic/source-carrier counts from frozen metadata only."""
from pathlib import Path
from collections import Counter, defaultdict
import csv, hashlib, json

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
PREVIOUS=ROOT/'work_packages/M1_source_access/33_media_eight_hour_review_20261011'
CLOSED=ROOT/'work_packages/M1_source_access/34_media_four_hour_review_20261011'
receipts=[]

def read(path):
    data=path.read_bytes();receipts.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest()})
    return json.loads(data) if path.suffix=='.json' else list(csv.DictReader(data.decode().splitlines()))

def table(name,rows):
    path=BASE/name;rows=list(rows)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

np=read(CLOSED/'closed/newspaper/CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv')
social=read(CLOSED/'closed/social/FINAL_SOURCE_MONTH_CALENDAR.csv')
registry={r['source_id']:r for r in read(PREVIOUS/'closed/eight_hour/social/source_registry_final.json')}
source_units={(r['stream'],r['source_id']):r for r in read(CLOSED/'analysis/finalized/source_contributions_genre_era.csv')}
assert len(np)==30704 and sum(int(r['usable_dated_independent_bodies']) for r in social)==988701
countries={'AU':'AU','NZ':'NZ','US':'US','UK':'GB','EU/Europe excluding UK':'UNRESOLVED_EUROPE_EX_UK'}
country_evidence={r['source_id']:r for r in read(BASE/'NEW_COUNTRY_EVIDENCE.csv')}
source_rows=[];monthly=Counter();source_sets=defaultdict(set);carrier=Counter()
for sid in sorted({r['source_id'] for r in np}):
    rows=[r for r in np if r['source_id']==sid];strata={r['stratum'] for r in rows};assert len(strata)==1
    stratum=next(iter(strata))
    source_rows.append({'stream':'newspaper','source_id':sid,'source_context_region':stratum,
      'source_context_country':country_evidence.get(sid,{}).get('source_context_country',countries[stratum]),
      'geographic_evidence_status':'current publisher location primary-evidenced; no historical ownership inference' if sid in country_evidence else 'accepted frozen source stratum; European country unresolved when not primary-evidenced',
      'individual_author_country':'unmeasured','retained_units':len(rows),'source_unit_class':'newspaper_title',
      'first_month':min(r['publication_date'][:7] for r in rows),'last_month':max(r['publication_date'][:7] for r in rows)})
    source_sets[('newspaper',stratum)].add(sid)
    for r in rows:monthly[('newspaper',stratum,r['publication_date'][:7])]+=1

confirmed={'mastodon_ie':('EU/Europe excluding UK','IE'),'mastodon_uk':('UK','GB'),
 'mastodon_au':('AU','AU'),'mastodon_us':('US','US'),'aussie_zone':('AU','AU'),
 'lemmy_nz':('NZ','NZ'),'midwest_social':('US','US'),'feddit_org':('EU/Europe excluding UK','UNRESOLVED_EUROPE_EX_UK')}
totals=Counter()
for r in social:totals[r['source_id']]+=int(r['usable_dated_independent_bodies'])
for sid,n in sorted(totals.items()):
    if not n:continue
    reg=registry[sid];positive=[r for r in social if r['source_id']==sid and int(r['usable_dated_independent_bodies'])>0]
    if sid in confirmed:
        assert 'verified' in str(reg.get('geographic_verification','')).lower()
        region,country=confirmed[sid];status='verified source-declared community frame; no author-country inference'
    elif str(reg.get('stratum','')).lower().startswith('global'):
        region,country='GLOBAL_COMMUNITY','UNRESOLVED';status='global carrier/community; individual locations unmeasured'
    else:
        region,country='UNRESOLVED_COMMUNITY','UNRESOLVED';status='provisional or absent geographic evidence; not promoted to a country'
    cls=source_units[('social',sid)]['source_unit_class']
    carrier_class='microblog_public_platform' if sid=='bluesky' or sid.startswith('mastodon_') else 'federated_forum_instance' if reg.get('platform')=='Lemmy' else cls
    carrier[carrier_class]+=n
    source_rows.append({'stream':'social','source_id':sid,'source_context_region':region,'source_context_country':country,
      'geographic_evidence_status':status,'individual_author_country':'unmeasured_in_export',
      'retained_units':n,'source_unit_class':carrier_class,'first_month':min(r['month'] for r in positive),'last_month':max(r['month'] for r in positive)})
    source_sets[('social',region)].add(sid)
    for r in positive:monthly[('social',region,r['month'])]+=int(r['usable_dated_independent_bodies'])

table('SOURCE_GEOGRAPHY.csv',source_rows)
pooled=Counter()
for (stream,region,month),n in monthly.items():pooled[stream,region]+=n
table('REGION_COUNTS.csv',({'stream':stream,'source_context_region':region,'retained_units':n,
 'share_of_stream':n/(30704 if stream=='newspaper' else 988701),'contributing_source_IDs':len(source_sets[stream,region]),
 'geographic_unit':'publisher/source-community frame; never individual author country'} for (stream,region),n in sorted(pooled.items())))
table('REGION_MONTH_COUNTS.csv',({'stream':stream,'source_context_region':region,'month':month,'retained_units':n} for (stream,region,month),n in sorted(monthly.items())))
country=Counter()
for r in source_rows:country[r['stream'],r['source_context_country']]+=r['retained_units']
country_by_source={(r['stream'],r['source_id']):r['source_context_country'] for r in source_rows}
country_month=Counter()
for r in np:country_month['newspaper',country_by_source['newspaper',r['source_id']],r['publication_date'][:7]]+=1
for r in social:
    n=int(r['usable_dated_independent_bodies'])
    if n:country_month['social',country_by_source['social',r['source_id']],r['month']]+=n
assert sum(carrier.values())==988701
for stream,expected in [('newspaper',30704),('social',988701)]:
    assert sum(n for (s,c),n in country.items() if s==stream)==expected
    assert sum(n for (s,c,m),n in country_month.items() if s==stream)==expected
table('SOURCE_CONTEXT_COUNTRY_COUNTS.csv',({'stream':stream,'source_context_country':c,'retained_units':n,
 'country_unit':'source/publisher/community context only; unresolved country remains unresolved'} for (stream,c),n in sorted(country.items())))
table('COUNTRY_MONTH_COUNTS.csv',({'stream':stream,'source_context_country':c,'month':m,'retained_units':n} for (stream,c,m),n in sorted(country_month.items())))
table('SOCIAL_CARRIER_COUNTS.csv',({'carrier_class':c,'dated_independent_bodies':n,'share_of_social':n/988701,
 'ordinary_public_role_validated':False} for c,n in sorted(carrier.items())))
table('MULTIPLE_SCALE_SCENARIOS.csv',({'multiplier':m,'stream':s,'current_units':n,'scenario_total_units':m*n,
 'additional_units_needed':(m-1)*n,'status':'development scenario, not a production cap, runtime stop or promised yield'} for m in [2,3,5] for s,n in [('newspaper',30704),('social',988701)]))
summary={'publication_interval':['1988-01-01','2026-09-21'],'new_acquisition_performed':False,
 'baseline_counts':{'newspaper_regular':30704,'social_dated':988701},
 'social_verified_regional_community_mass':sum(r['retained_units'] for r in source_rows if r['stream']=='social' and r['source_id'] in confirmed),
 'individual_author_country_distribution_available':False,
 'reason':'Frozen metadata contains source/community strata, not validated per-body author-country fields. Country of a platform, server, language or topic is not author country.',
 'social_carrier_counts':dict(carrier),'input_receipts':receipts,'frozen_inputs_preserved':True,
 'no_topic_affect_fear_or_inferred_location_model_executed':True}
(BASE/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'regions':{str(k):v for k,v in pooled.items()},'carrier':dict(carrier),'regional_social_mass':summary['social_verified_regional_community_mass']}))
