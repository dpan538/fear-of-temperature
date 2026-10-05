"""Record finite manual relevance decisions and annotate the 49x3 readiness sheet."""
import csv
from collections import Counter, defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent

def read(name):
    with (HERE/name).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write(name,rows,fields):
    with (HERE/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

# These decisions concern the preserved authorial text, not a full-month census.
# 1 = topical relation to physical warming, climate impacts or mitigation;
# 0 = reviewed and not supported by that text. Fear/anticipated harm is stricter.
GOV_TOPIC={
 'doc_4f93a3a7854e81261140':1, # low-carbon technology within anaerobic digestion report
 'doc_43f93700451af3bdbe79':0, # information-request process
 'doc_590ef0fa0e3a55b865d5':0, # carrier-bag charge; current 2021 version caveat
 'doc_dec013c16372221fa734':0, # household energy-efficiency programme, no warming claim in selected answer
 'doc_d6090ca51ed2d21e2540':0, # tariff de-rating
 'doc_53638464697f65ec260b':0, # generation operating durations
 'doc_1353fa700ccfe20b3b28':0, # local air quality
 'doc_25eca39cba683c051642':0, # regional investment
 'doc_3a215c95cb2a2370437d':0, # dairy farm counts
 'doc_5fa2cdc11875174d936b':0, # department buildings
 'doc_faf266d8f9d2e15b4020':0, # nuclear decommissioning
 'doc:98d69c37a37fee4bb17517a7cd67c4ca':0, # hazardous-air-pollutant rule
 'doc:b02a7e737ce58f94f1546c7144b23b5a':0, # air-quality state plan
 'doc:5010a3bab658e3dab3df79bd4b0c26e4':0, # nonroad-engine CFR correction
 'doc:6beeebd5d6c3a145fcad2c43fb75a94e':0, # pesticide tolerance
 'doc:40d73bf431b177bebfaf48d9ff2e6d1f':1, # GHG reporting correction: administrative subject only
 'doc:9556a85402f8a029170e112cbfbb73a8':0, # Illinois air-quality SIP
 'doc:424caae73efed84077410b0a2a018548':0, # insecticidal protein exemption
 'doc:2715713f78d438e7f7a724b19f621b58':1, # GHG permitting direct final rule
 'doc:f2cfe1971d224ff15d94fff4a6aa2f03':0, # surfactant tolerance
}
GOV_TITLE_TOPIC={
 ('2015-02','Climate Change'):1,
 ('2015-03','Department for Energy and Climate Change: Off-payroll Working'):0,
 ('2015-06','Climate Change'):1,
}

PUBLIC_TOPIC={
 '117267':1,'116675':1,'119541':0,'116061':1,'114487':0,'118848':0,
 '114623':1,'117357':1,'116375':0,'114128':1,'118119':1,'113997':1,
 '116128':0,'117286':1,'117174':1,'112204':1,'116606':1,'117301':1,
 '116084':1,'112356':0,'116435':0,
}
PUBLIC_HARM={'114623','117357','113997','117286','117174','112204'}

gov=[]
for r in read('government_pilot_selected.csv'):
    pid=r['parent_id']; topic=GOV_TOPIC.get(pid,GOV_TITLE_TOPIC.get((r['month'],r['title'])))
    if topic is None:raise ValueError(f'unreviewed government ID {pid} {r["title"]}')
    note=''
    if r['source'].startswith('UK ministerial'):
        note='Question context is preserved separately; topic decision rests on ministerial response plus question context.'
    elif r['source']=='UK policy':
        note='Landing page and linked attachment are one parent; sampled source segments can include PDF line breaks.'
        if r['updated_at'] and r['updated_at'][:10]>r['publication_date']:
            note+=' Current body was updated after first publication; historical wording unverified.'
    else:
        note='Verified Federal Register original; API final_rule subtype retained.'
        if r['header_subtype']=='cfr_correction':note+=' Correction does not represent a substantive new climate argument.'
    r.update(reviewed_parent=1,climate_warming_topic=topic,anticipated_climate_harm_cue=0,explicit_fear_expression=0,
             label_basis='manual title, selected original-body passages, subtype and source context',review_note=note)
    gov.append(r)
write('government_pilot_review.csv',gov,list(gov[0]))

media=[]
for r in read('media_pilot_selected.csv'):
    title=r['title'].lower()
    topic=0 if 'oldest tracked bird' in title else 1
    r.update(reviewed_parent=1,climate_warming_topic=topic,anticipated_climate_harm_cue=0,explicit_fear_expression=0,
             label_basis='manual article headline and short body inspection',
             review_note='Archive-day sample only; current HTML may differ from first-published article.')
    media.append(r)
write('media_pilot_review.csv',media,list(media[0]))

public=[]
for r in read('public_pilot_2015_11_to_2016_01.csv'):
    pid=r['petition_id']
    if pid not in PUBLIC_TOPIC:raise ValueError(f'unreviewed public ID {pid}')
    r.update(reviewed_parent=1,climate_warming_topic=PUBLIC_TOPIC[pid],
             anticipated_climate_harm_cue=int(pid in PUBLIC_HARM),explicit_fear_expression=0,
             label_basis='manual petitioner-authored action/background/additional detail; government response excluded',
             review_note=('Rejected submission; not visible as a published petition.' if r['state']=='rejected' else 'Published petition.')
               + (' Keyword noise: climate is used in another sense or only incidentally.' if not PUBLIC_TOPIC[pid] else ''))
    public.append(r)
write('public_pilot_review.csv',public,list(public[0]))

matrix=read('paris_month_role_readiness_49x3.csv')
public_frame=read('public_climate_query_frame.csv')
media_frame=read('media_day_archive_frame.csv')
pub_month=defaultdict(list)
for r in public_frame:pub_month[r['created_at'][:7]].append(r)
med_frame=Counter(r['archive_day'][:7] for r in media_frame)
reviews={'government':gov,'media':media,'public':public}
for r in matrix:
    m,role=r['month'],r['role']
    subset=[x for x in reviews[role] if (x.get('month') or x.get('archive_day','')[:7] or x.get('created_at','')[:7])==m]
    r['pilot_reviewed_parent_count']=len(subset) if subset else ''
    r['pilot_verified_climate_warming_parent_count']=sum(int(x['climate_warming_topic']) for x in subset) if subset else ''
    r['pilot_verified_anticipated_harm_parent_count']=sum(int(x['anticipated_climate_harm_cue']) for x in subset) if subset else ''
    r['pilot_verified_explicit_fear_parent_count']=sum(int(x['explicit_fear_expression']) for x in subset) if subset else ''
    if role=='public' and '2015-07'<=m<='2017-04':
        hits=pub_month[m]
        r.update(eligible_denominator_source='UK Parliament 2015-2017 archive q=climate search hits; creation month',
                 eligible_denominator=len(hits),dated_independent_parent_count=len(hits),
                 readable_independent_parent_count=sum(bool(x['background'] or x['additional_details']) for x in hits),
                 count_qualifier='complete paginated keyword-query result at snapshot; includes rejected submissions; not all petitions',
                 coverage_state='query_hit_readable' if hits else 'verified_zero_within_keyword_query',
                 source_genre='UK Parliament public petition submissions, published and rejected',
                 evidence_paths='work_packages/M1_source_access/11_paris_readiness_pilot_20260927/public_climate_query_frame.csv')
    elif role=='media' and med_frame[m]:
        r.update(eligible_denominator_source='Guardian environment archive cards on one fixed day in this month',
                 eligible_denominator=med_frame[m],dated_independent_parent_count=len(subset),
                 readable_independent_parent_count=sum(x['body_present']=='True' for x in subset),
                 count_qualifier='one-day archive frame; sampled article dates/bodies verified; no monthly population denominator',
                 coverage_state='sampled_readable_parent_present',source_genre='Guardian environment archive, nonvideo article',
                 evidence_paths='work_packages/M1_source_access/11_paris_readiness_pilot_20260927/media_day_archive_frame.csv')
write('paris_month_role_readiness_49x3.csv',matrix,list(matrix[0]))
assert len(matrix)==147
assert sum(r['role']=='government' and r['coverage_state']=='readable_parent_present' for r in matrix)==49
print({'government_reviewed':len(gov),'government_topic':sum(int(r['climate_warming_topic']) for r in gov),
       'media_reviewed':len(media),'media_topic':sum(int(r['climate_warming_topic']) for r in media),
       'public_reviewed':len(public),'public_topic':sum(int(r['climate_warming_topic']) for r in public),
       'public_anticipated_harm':sum(int(r['anticipated_climate_harm_cue']) for r in public),
       'explicit_fear_all_pilots':sum(int(r['explicit_fear_expression']) for r in gov+media+public)})
