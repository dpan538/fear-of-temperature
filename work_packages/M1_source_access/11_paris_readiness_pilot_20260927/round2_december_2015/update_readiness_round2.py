"""Create a new, source-qualified 49x3 snapshot without overwriting round 1."""
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent

def read(path):
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write(path,rows,fields):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

rows=read(BASE/'paris_month_role_readiness_49x3.csv')
media=read(HERE/'guardian_dec2015_article_metadata.csv')
spot=read(HERE/'guardian_dec2015_body_spot_checks.csv')
round1_media=read(BASE/'media_pilot_review.csv')
pet=read(HERE/'petition_177_id_date_mapping.csv')
pet_review={r['petition_id']:r for r in read(BASE/'public_pilot_review.csv')}
assert len(rows)==147 and len(media)==396 and all(r['published_utc_month']=='2015-12' for r in media)
assert len(spot)==3 and all(r['body_present']=='True' for r in spot)
body_checked={r['article_url'] for r in spot}
body_checked.update(r['parent_url'] for r in round1_media if r['archive_day'][:7]=='2015-12' and r['body_present']=='True')
assert len(body_checked)==4

submitted=defaultdict(list);published=defaultdict(list)
for p in pet:
    submitted[p['created_month_utc']].append(p)
    if p['published_only_eligible']=='1':published[p['opened_month_utc']].append(p)

for r in rows:
    r['round2_snapshot_utc']=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    r['public_all_submitted_query_created_count']=''
    r['public_rejected_query_created_count']=''
    r['public_published_query_created_count']=''
    r['public_published_query_opened_count']=''
    r['media_monthly_candidate_date_verification']=''
    m=r['month']
    if r['role']=='media' and m=='2015-12':
        r.update(eligible_denominator_source='Guardian environment 31 daily /all archives; distinct nonvideo current title cards; UTC original publication month',
                 eligible_denominator=396,dated_independent_parent_count=396,
                 readable_independent_parent_count=len(body_checked),
                 count_qualifier='396/396 article original-date metadata checked; only four unique bodies confirmed readable, so readable count is a lower bound; current archive candidate frame, not historical completeness or all Guardian news',
                 coverage_state='monthly_archive_candidate_frame_dated_body_subset',
                 source_genre='Guardian environment archive nonvideo article',
                 evidence_paths='work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/guardian_dec2015_archive_days.csv | work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/guardian_dec2015_article_metadata.csv | work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/guardian_dec2015_body_spot_checks.csv',
                 media_monthly_candidate_date_verification='396/396 original timestamps in 2015-12 UTC; 31/31 daily archive pages HTTP 200; no exposed within-day pagination')
    elif r['role']=='public' and '2015-07'<=m<='2017-04':
        created=submitted[m];opened=published[m]
        r.update(eligible_denominator_source='UK Parliament 2015-2017 archive q=climate; published-only opened_at UTC month',
                 eligible_denominator=len(opened),dated_independent_parent_count=len(opened),
                 readable_independent_parent_count=sum(p['petitioner_body_present']=='1' for p in opened),
                 count_qualifier='complete 177-ID keyword-query frame; main series is published/opened only; not all eligible petitions or broad public discourse',
                 coverage_state='published_query_hit_readable' if opened else 'verified_zero_within_published_keyword_query',
                 source_genre='UK Parliament published public petitions; rejected submissions excluded from main role count',
                 evidence_paths='work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/petition_177_id_date_mapping.csv',
                 public_all_submitted_query_created_count=len(created),
                 public_rejected_query_created_count=sum(p['state']=='rejected' for p in created),
                 public_published_query_created_count=sum(p['published_only_eligible']=='1' for p in created),
                 public_published_query_opened_count=len(opened))
        if m in ('2015-11','2015-12','2016-01'):
            reviewed=[pet_review[p['petition_id']] for p in opened if p['petition_id'] in pet_review]
            # All opened query hits in these months are covered by the existing near-event manual subset.
            assert len(reviewed)==len(opened)
            r['pilot_reviewed_parent_count']=len(reviewed)
            r['pilot_verified_climate_warming_parent_count']=sum(int(p['climate_warming_topic']) for p in reviewed)
            r['pilot_verified_anticipated_harm_parent_count']=sum(int(p['anticipated_climate_harm_cue']) for p in reviewed)
            r['pilot_verified_explicit_fear_parent_count']=sum(int(p['explicit_fear_expression']) for p in reviewed)

write(HERE/'paris_month_role_readiness_49x3_round2.csv',rows,list(rows[0]))
print('rows',len(rows),'government readable',sum(r['role']=='government' and r['coverage_state']=='readable_parent_present' for r in rows),
      'Guardian December candidates',next(r['dated_independent_parent_count'] for r in rows if r['role']=='media' and r['month']=='2015-12'),
      'public published query parents',sum(int(r['public_published_query_opened_count']) for r in rows if r['public_published_query_opened_count']!=''))
