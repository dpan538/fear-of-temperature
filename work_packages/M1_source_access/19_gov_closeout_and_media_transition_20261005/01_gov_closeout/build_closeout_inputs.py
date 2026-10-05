"""Package named saved aggregates, changed-Item annotations and bounded plans.
No original-body reread, database query/write, network call or evaluator access.
"""
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
WP=ROOT/'work_packages/M1_source_access'
B=WP/'18_bounded_supplementation_execution_20261005/02_eu_staging'
A=WP/'18_bounded_supplementation_execution_20261005/01_downloader_and_originals'
OLD=WP/'15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation'
INTERVAL=['1988-01-01','2026-09-21']


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def read(p):
    with Path(p).open() as f:return list(csv.DictReader(f))


def csvout(name, rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def jsout(name, obj): (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')


def annotate():
    shapes=read(HERE/'CHANGED_ITEM_TEXT_SHAPE.csv'); original=read(B/'STAGING_INGESTION_HANDOFF.csv')
    assert len(shapes)==len(original)==20
    # Explicit annotations from the saved first-page text and visual contact sheets.
    dates=[29,31,28,23,24,16,8,21,29,28,29,10,12,14,9,30,31,29,20,21]
    refs=['COM(2015) 26 final','2015/C 33/03','2015/C 28/06; 2015/C 28/07',
          '2015/C 024/04','2015/C 25/08','2015/C 014/01','2015/C 3/03; 2015/C 3/04',
          '2015/C 18/03','COM(2015) 29 final','2015/C 28/08; 2015/C 28/09',
          '2015/C 29/03; 2015/C 29/04','2015/C 6/06','COM(2015) 1 final','2015/C 10/09',
          'COM(2014) 750 final','2015/C 032/01','2015/C 33/04','COM(2015) 22 final',
          'COM(2015) 8 final','COM(2015) 13 final']
    titles=[
       'Council Decision proposal: PLO/Palestinian Authority, Protocol 3 rules of origin',
       'Information communicated by Member States regarding closure of fisheries',
       'Information communicated by Member States regarding closure of fisheries (two notices on page 1)',
       'State aid France SA.38545: Mory-Ducros restructuring; invitation to submit comments',
       'Publication of application: Arroz Carolino do Baixo Mondego',
       'Commission communication: electromagnetic compatibility harmonised standards',
       'Information communicated by Member States regarding closure of fisheries (two notices on page 1)',
       'Publication of amendment application: Uva de mesa embolsada del Vinalopo',
       'Council Decision proposal: Jordan, Protocol 3 rules of origin',
       'Information communicated by Member States regarding closure of fisheries (two notices on page 1)',
       'Information communicated by Member States regarding closure of fisheries (two notices on page 1)',
       'Publication of application: Telemea de Ibanesti',
       'Council Decision proposal: Venezuela fishing opportunities off French Guiana',
       'Corrigendum: Trans-European Transport Network Executive Agency final accounts 2013',
       'Council Decision proposal: Heavy Metals Protocol amendment acceptance',
       'Summary of EU medicinal-product marketing authorisation decisions, December 2014',
       'List of registered and certified credit rating agencies',
       'Council Decision proposal: Bosnia and Herzegovina, Protocol 2 rules of origin',
       'Regulation proposal: Schengen Borders Code codification',
       'Decision proposal: European Globalisation Adjustment Fund PL/Zachem']
    com={1,9,13,15,18,19,20}; multi={3,7,10,11}; identity=[]
    for i,(r,o) in enumerate(zip(shapes,original),1):
        assert r['item_uri']==o['item_uri']
        printed=f'2015-01-{dates[i-1]:02d}'
        r.update(selected_manifestation_distinct_items=o['selected_manifestation_distinct_items'],
                 all_distinct_item_alternatives=o['all_distinct_item_alternatives'],
                 observed_selected_Item_count_for_Work='1',visual_check='first page legible; remaining pages not visually inspected',
                 content_identity_status='saved CDM WEMI maps selected Item to Work; printed reference observed; Work-title metadata not saved',
                 printed_issue_date=printed,printed_date_role='COM issue date on cover' if i in com else 'Official Journal issue date in page header/footer',
                 printed_reference=refs[i-1],printed_title=titles[i-1],
                 printed_title_form='descriptive transcription; full first-page source retained',
                 printed_component_role='COM proposal PDF' if i in com else 'Official Journal notice/corrigendum rendition',
                 observed_genre='legislative/council-decision proposal' if i in com else 'official notice/list/communication/corrigendum',
                 first_page_multiple_notice_refs=i in multi,
                 body_issuer_observed='European Commission' if i in com or i in {4,5,6,8,12,15,16} else
                    ('Member State communication republished in EU Official Journal' if i in {2,3,7,10,11} else
                     ('ESMA list, Commission republication' if i==17 else 'Trans-European Transport Network Executive Agency corrigendum')),
                 directness='official archival reproduction; recorded institutions/communications retained separately',
                 provenance_verification='official Item route and raw hash verified; printed identity and issue date observed; no claim-truth verification',
                 issue_date_comparison='conflict_one_day_same_month' if printed!=r['publication_dates'] else 'agrees_with_saved_Work_day',
                 analysis_month_support='2015-01 under both saved metadata and printed date',
                 identity_mapping_limit='multi-notice page: selected Work text boundary not isolated' if i in multi else 'one Item does not establish full Work or annex set',
                 complete_work_status='pending component and content-boundary acceptance',
                 historical_version_equivalence='unknown; later retrieval/Last-Modified not proof of original historical wording',
                 parent_statistics_eligible='False',formal_ingestion_performed='False',
                 shape_includes='all PDF text-layer characters incl. cover/header/footnote; no semantic or boilerplate exclusion')
        identity.append({k:r[k] for k in ['sequence','parent_id','item_uri','publication_dates','printed_issue_date',
                   'issue_date_comparison','printed_reference','printed_title','observed_genre','body_issuer_observed',
                   'selected_manifestation_distinct_items','first_page_multiple_notice_refs','identity_mapping_limit',
                   'complete_work_status','parent_statistics_eligible']})
    csvout('CHANGED_ITEM_TEXT_SHAPE.csv',shapes);csvout('CHANGED_ITEM_IDENTITY_DATE.csv',identity)
    check=json.loads((HERE/'CHANGED_ITEM_CHECK.json').read_text())
    check.update(visual_identity_check='20 first pages inspected; 135 total pages not all visually inspected',
                 printed_issue_day_agreements=19,printed_issue_day_conflicts=1,first_page_multi_notice_items=4,
                 observed_COM_proposal_items=7,observed_OJ_notice_items=13,
                 items_with_multiple_selected_manifestation_items=sum(int(r['selected_manifestation_distinct_items'])>1 for r in shapes),
                 complete_Work_acceptance='not established',eligible_parent_length_rows=0,
                 unique_raw_sha256=len({r['raw_sha256'] for r in shapes}),
                 manual_annotations_path='CHANGED_ITEM_IDENTITY_DATE.csv')
    jsout('CHANGED_ITEM_CHECK.json',check)


def au_plan():
    dispositions=read(A/'A_DISPOSITIONS.csv'); out=[]
    pdfs=['https://www.dcceew.gov.au/sites/default/files/documents/interim-report-fugitive-methane-expert-panel.pdf',
          'https://www.dcceew.gov.au/sites/default/files/documents/australias-sustainable-ocean-plan.pdf']
    labels=["Enhancing Australia's Fugitive Methane Emissions Estimates: Consideration of Atmospheric Measurement Approaches - an Interim Report (PDF)",
            'Australia’s Sustainable Ocean Plan (PDF)']
    for i,r in enumerate(dispositions[3:]):
        assert r['actually_attempted']=='false'
        out.append({'unit_id':r['unit_id'],'source_id':r['source_id'],'landing_url':r['source_request_url'],
          'candidate_pdf_url':pdfs[i],'saved_link_label':labels[i],
          'candidate_link_evidence':'work_packages/M1_source_access/09_us_au_government_acquisition/reports/au_attachment_candidates.csv',
          'original_publication_date':'unknown','cms_created_at_not_publication_date':r['cms_created_at_not_publication_date'],
          'previous_attempts_this_five_request_phase':0,'current_host':'www.dcceew.gov.au',
          'legal_publisher':'unverified','document_author':'unverified','commissioning_issuer':'unverified',
          'primary_file_role':'candidate only; current exact landing link must be confirmed before PDF request',
          'maximum_requests':2,'landing_cap_bytes':2*2**20,'pdf_cap_bytes':25*2**20,
          'date_check':'inspect printed title/imprint/issue day; distinguish revision and CMS time; preserve intervals if only month/year',
          'cutoff_rule':'eligible only if original issue evidence supports <=2026-09-21; unknown stays unresolved; no CMS exclusion',
          'access_rule':'ordinary public route only; no accounts, paid access, anti-bot bypass or alternate targets',
          'retry_rule':'one attempt per named route; no redirects followed; failed checkpoint and phase stop persist',
          'execution_authorization':'pending new merged coordinator release'})
    csvout('AU_ORIGINAL_CHECK_PLAN.csv',out)


def frames():
    uk=read(WP/'16_post_repair_analysis_20261004/uk_effective_source_genre.csv')
    old=read(WP/'13_parallel_data_audit_20261004/02_distribution/monthly_source_genre_counts.csv')
    by=defaultdict(list)
    for r in old:by[(r['source_id'],r['genre'])].append(r)
    out=[]
    def frame(**fields):
        row={'frame_id':'','region':'','source_id':'','source_label':'','source_route_is_department':False,
             'institution_or_portfolio_scope':'','genre_scope':'','source_native_unit':'','date_basis':'',
             'publication_interval':'1988-01-01..2026-09-21','source_observation_span':'','known_inventory_count':'',
             'operational_extracted_status_count':'','source_text_presence_level':'','climate_relevance_level':'unassessed; not current gate',
             'affect_risk_association_level':'unvalidated','fear_specific_level':'unassessed',
             'parent_count_use':'source-frame inventory only; no cross-source independence claim',
             'item_version_segment_rules':'','provenance_class':'','verification_status':'','conflicting_or_pending':'',
             'observed_at_or_checkpoint_utc':'','retrieval_time_scope':'','content_version_scope':'later saved version may differ from historical wording',
             'evidence_path':'','coverage_limits':'','overlap_rule':'','department_map_status':'unknown; source route is not department'}
        row.update(fields);out.append(row)
    for r in uk:
        key=(r['source_id'],r['genre']); previous=by[key]; span=previous[0]['source_observed_span']
        frame(frame_id='UK:'+r['source_id']+':'+r['genre'],region='UK',source_id=r['source_id'],source_label=r['source_label'],
          institution_or_portfolio_scope='Commons recorded ministerial discourse' if 'answer' in r['genre'] or 'statement' in r['genre'] else 'frozen DEFRA / historic policy source frame',
          genre_scope=r['genre'],source_native_unit='effective source-specific document parent ID',
          date_basis='effective source-local day or supported interval; cross-month intervals retained unassigned',
          source_observation_span=span,known_inventory_count=r['parent_count'],
          source_text_presence_level='saved source/repair mappings; readable-text coverage not refreshed',
          item_version_segment_rules='parent IDs distinct within source; source objects/attachments, reply groups and segments linked separately',
          provenance_class='verified mirror / archival reproduction' if 'mirror' in r['source_label'] else
             ('official archival reproduction' if 'Hansard' in r['source_label'] else 'direct institutional / archival source, mapping dependent'),
          verification_status='effective metadata aggregate and committed bounded repair acceptance; not universal original-date/content correctness',
          conflicting_or_pending='119 local/UTC convention differences; 124 interval cases, 51 cross-month globally; 37 frozen HTML-adapter limitations',
          observed_at_or_checkpoint_utc='2026-10-04T14:21:27.701426+00:00',
          retrieval_time_scope='baseline first 2026-09-21T14:08:38+08:00 / last 2026-09-22T21:01:49+08:00; later saved-source repair separately recorded',
          evidence_path='work_packages/M1_source_access/16_post_repair_analysis_20261004/uk_effective_source_genre.csv',
          coverage_limits='observed source span is not exhaustive monthly population coverage; 2013-05 archive partial',
          overlap_rule='ParlParse mirror and shared replies can overlap official routes; UK09 copy adds no UK inventory',
          department_map_status='source-wide crosswalk unavailable; do not call Hansard or Questions API a department')
    for genre in ['final_rule','proposed_rule']:
        rr=by[('us_fr_epa_doe_rules_1994',genre)]
        frame(frame_id='US:EPA_DOE:'+genre,region='US',source_id=rr[0]['source_id'],source_label='US Federal Register EPA/DOE',
          institution_or_portfolio_scope='EPA OR DOE; preserve cross-agency association; 16 stratum overlaps are one canonical parent',
          genre_scope=genre,source_native_unit='canonical Federal Register document URL / document number',
          date_basis='Federal Register publication day',source_observation_span='1994-01..2026-09',
          known_inventory_count=sum(int(r['parent_count']) for r in rr),
          operational_extracted_status_count=sum(int(r['extracted_status_parent_count']) for r in rr),
          source_text_presence_level='saved operational status; changed tranche here has zero US additions',
          item_version_segment_rules='18,590 saved versions in prior US checkpoint; pages and segments not parents',
          provenance_class='direct institutional publication / official reproduction',
          verification_status='saved enumerated and operational checkpoint, not re-audited',
          conflicting_or_pending='1988-1993 official index/page/issue evidence is not an enumerated Work denominator; 1994 frame gaps remain',
          observed_at_or_checkpoint_utc='US/AU DB checkpoint 2026-09-27T12:36:23.210504+00:00',
          retrieval_time_scope='2026-09-21T14:08:38+08:00..2026-09-27T20:31:31.618256+08:00 saved mixed US/AU range',
          evidence_path='work_packages/M1_source_access/13_parallel_data_audit_20261004/02_distribution/monthly_source_genre_counts.csv',
          coverage_limits='fixed agency/genre frame only; incomplete body queue; Sept partial',
          overlap_rule='33,560 agency-stratum hits resolve to 33,544 unique parent URLs',
          department_map_status='EPA/DOE frame known; per-parent association required for department plot')
    frame(frame_id='EU:CELLAR:COM_ACT_PREP_ENG',region='EU_supranational',source_id='EU_CELLAR_COM',source_label='EU CELLAR COM frozen class',
      institution_or_portfolio_scope='COM RDF authority; act_preparatory RDF class; ENG Expressions',
      genre_scope='frozen preparatory class; printed bodies include proposal and OJ notice/list/communication/corrigendum',
      source_native_unit='Work URI',date_basis='saved CDM work_date_document; printed Item dates separately retained',
      source_observation_span='1988-01..2026-09 (465 enumerated month bins)',known_inventory_count=50578,
      operational_extracted_status_count=19085,source_text_presence_level='old staged 19,114 Item versions; new 20 Items in January 2015 have text layers, un-ingested',
      item_version_segment_rules='Work > Expression > Manifestation > Item/version > pages; 979 selected candidates within 1,009 2015 Works',
      provenance_class='official archival reproduction; printed institution/holder may differ within notice renditions',
      verification_status='saved metadata/WEMI checkpoint; changed 20 SHA/signature/page/text and first-page evidence checked',
      conflicting_or_pending='one printed-day conflict; four first-page multi-notice Items; six selected Manifestations have multiple Items; complete Work acceptance pending',
      observed_at_or_checkpoint_utc='EU DB checkpoint 2026-09-27T15:31:29.765522+00:00; B stopped 2026-10-04T18:38:18.022392+00:00',
      retrieval_time_scope='saved EU range 2026-09-26T14:28:22.549862+00:00..2026-09-27T15:31:23.954179+00:00; new 20 requests in separate B ledger',
      evidence_path='work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/01_gov_closeout/CHANGED_ITEM_TEXT_SHAPE.csv',
      coverage_limits='2015 B:20 candidates,1 HTTP406,958 unattempted,30 no-link Works; 2024-08 class zero not all COM zero',
      overlap_rule='component/format multiplicity retained; one Item cannot certify complete or independent Work text',
      department_map_status='COM authority known; DG/department mapping not inferred from platform or title')
    frame(frame_id='AU:DCCEEW:CATALOGUE',region='AU',source_id='au_dcceew_current_catalogue_2026_snapshot',source_label='AU DCCEEW current catalogue',
      institution_or_portfolio_scope='current DCCEEW all-publications listing pages 0..82; predecessor author/issuer not equated with current host',
      genre_scope='catalogue publication candidate',source_native_unit='unique landing URL candidate, not verified independent policy Work',
      date_basis='CMS created time is separate; original issue date unknown for most',source_observation_span='current 83-page catalogue snapshot, not original publication coverage span',
      known_inventory_count=821,source_text_presence_level='catalogue/link observations; seven verified originals overlap this inventory',
      item_version_segment_rules='landing and primary/alternative files remain one candidate parent with versions',
      provenance_class='unresolved / mixed until original imprint and author/host/issuer are checked',
      verification_status='saved snapshot; 819 main-table publication days missing; no universal mapping pass',
      conflicting_or_pending='two final-original requests not yet attempted; CMS2026-09-17/22 do not decide eligibility',
      observed_at_or_checkpoint_utc='US/AU DB checkpoint 2026-09-27T12:36:23.210504+00:00',
      retrieval_time_scope='saved catalogue/observation receipts; current bundle performs no AU request',
      evidence_path='work_packages/M1_source_access/09_us_au_government_acquisition/reports/au_candidate_outcomes.csv',
      coverage_limits='original-date month denominator unknown; access timeout/challenges retained as unresolved',
      overlap_rule='verified originals are subset, do not add seven to821')
    frame(frame_id='AU:VERIFIED_ORIGINAL_SUBSET',region='AU',source_id='AU_VERIFIED_ORIGINAL',source_label='AU independently checked original subset',
      institution_or_portfolio_scope='saved official landing/file evidence; externally authored report retains author and commissioning uncertainty',
      genre_scope='primary publication',source_native_unit='original publication parent, overlapping catalogue subset',
      date_basis='five day/month originals, two year-only; year-only not placed in exact months',known_inventory_count=7,
      source_text_presence_level='seven saved verified originals at prior checkpoint; not reread here',
      item_version_segment_rules='browser/main staging overlap retained; no new parent from PDF or landing',
      provenance_class='direct / official archival / hosted external, recorded per original',
      verification_status='prior checked source identity/date precision; 2005 report legal publisher/commissioner unresolved',
      observed_at_or_checkpoint_utc='AU browser DB checkpoint 2026-09-26T17:12:20.944330+00:00',
      retrieval_time_scope='saved AU browser range 2026-09-26T14:21:54.536040+00:00..2026-09-26T17:11:42.319813+00:00 plus earlier originals',
      evidence_path='work_packages/M1_source_access/13_parallel_data_audit_20261004/02_distribution/RESULT.json',
      coverage_limits='named subset only, no complete historical AU government denominator',overlap_rule='subset of821, never additive')
    ie=read(WP/'08_cross_region_government_coverage/ie_written_question_month_index.csv')
    nz=read(WP/'08_cross_region_government_coverage/nz_parliament_climate_answered_2025_month_index.csv')
    frame(frame_id='IE:WRITTEN_QUESTION_INDEX',region='IE',source_id='IE_OIREACHTAS_ALL_DEPT_WRITTEN',source_label='Oireachtas written-question API index',
      institution_or_portfolio_scope='qtype=written; all departments, no topic filter',genre_scope='written question index',
      source_native_unit='question record/index total, not independent ministerial answer',date_basis='question date_start/date_end API monthly partitions',
      source_observation_span='2012-07..2026-09-21 (171 partitions)',known_inventory_count=sum(int(r['official_index_count']) for r in ie),
      source_text_presence_level='index counts; 2012-09 complete question-record sample separately saved',
      item_version_segment_rules='question and answer relations separate;357 selected question rows share280 distinct answer strings',
      provenance_class='official index / archival answer reproduction when body mapped',verification_status='171 saved API count receipts; not684,809 downloaded answers',
      observed_at_or_checkpoint_utc=min(r['retrieved_at_utc'] for r in ie)+'..'+max(r['retrieved_at_utc'] for r in ie),
      evidence_path='work_packages/M1_source_access/08_cross_region_government_coverage/ie_written_question_month_index.csv',
      coverage_limits=f"{sum(int(r['official_index_count'])>0 for r in ie)} positive and {sum(int(r['official_index_count'])==0 for r in ie)} query-zero partitions; index zero not independent-answer completeness",
      overlap_rule='2012-09 sample:357 responses,280 exact full-answer strings,77 excess instances in45 repeat groups; no automatic deletion')
    frame(frame_id='NZ:WRITTEN_QUESTION_2025_PORTFOLIO',region='NZ',source_id='NZ_PARLIAMENT_2025_CLIMATE_CHANGE_PORTFOLIO',source_label='NZ Parliament saved portfolio index diagnostic',
      institution_or_portfolio_scope='historical frozen Climate Change portfolio and current Question Answered status; retained scope, not a new topic inclusion gate',
      genre_scope='written question with currently answered display status',source_native_unit='displayed question record count, not answer-date or unique-answer count',
      date_basis='question-asked date range in official UI',source_observation_span='2025-01..2025-12',
      known_inventory_count=sum(int(r['displayed_count']) for r in nz),source_text_presence_level='12 saved UI index counts; bounded answer identity sample',
      item_version_segment_rules='question, received answer, corrected answer and publication version not collapsed',
      provenance_class='official index/archival reproduction when body mapped',verification_status='saved browser-rendered counts; no exhaustive original-answer retrieval',
      observed_at_or_checkpoint_utc=min(r['observed_at_utc'] for r in nz)+'..'+max(r['observed_at_utc'] for r in nz),
      evidence_path='work_packages/M1_source_access/08_cross_region_government_coverage/nz_parliament_climate_answered_2025_month_index.csv',
      coverage_limits='536 question records in12positive months; current answered status does not establish answer-received dates',
      overlap_rule='unique response denominator unknown')
    for region,label,source,scope,url in [
      ('IE','Irish government publication entrance','IE_GOV_PUBLICATIONS','saved department publication entrance, not enumerated','https://www.gov.ie/en/organisation/department-of-the-environment-climate-and-communications/'),
      ('NZ','NZ Ministry for the Environment publications','NZ_MFE','saved HTTP200 anti-bot challenge; no enumerated denominator','https://environment.govt.nz/publications/'),
      ('NZ','NZ Beehive executive publications','NZ_BEEHIVE','named official executive-publication route; no complete denominator in saved checkpoint','https://www.beehive.govt.nz/'),
      ('AU','AU Parliament questions entrance','AU_PARLIAMENT','saved HTTP403; not enumerated','https://www.aph.gov.au/housenp'),
      ('EU_supranational','European Parliament questions diagnostic','EU_EP_QUESTIONS','one original Work response checked; no year partitions enumerated','https://data.europarl.europa.eu/api/v2/parliamentary-questions')]:
        frame(frame_id=source,region=region,source_id=source,source_label=label,institution_or_portfolio_scope=scope,
              source_native_unit='entrance/route observation only',date_basis='not established for a population',
              source_text_presence_level='named route or bounded original evidence only',provenance_class='unresolved for a corpus',
              verification_status='saved route evidence, no new requests',observed_at_or_checkpoint_utc='saved2026-09-23 / review2026-09-26; retain narrower source receipts',
              evidence_path='docs/research/2026-09-26-ie-eu-nz-source-sufficiency-review.md',coverage_limits=scope,
              conflicting_or_pending='access and original-date/identity checks as applicable',overlap_rule='route is not new documents',canonical_entry=url)
    csvout('GOV_FRAME_REGISTER.csv',out)
    # Keep frozen inputs available to the independent reviewer. No evaluator is run.
    (HERE/'inputs').mkdir(exist_ok=True)
    for src,name in [(WP/'16_post_repair_analysis_20261004/uk_effective_month_source_genre.csv','UK_EFFECTIVE_MONTH_SOURCE_GENRE.csv'),
                     (WP/'16_post_repair_analysis_20261004/uk_effective_source_genre.csv','UK_EFFECTIVE_SOURCE_GENRE.csv'),
                     (WP/'08_cross_region_government_coverage/ie_written_question_month_index.csv','IE_WRITTEN_QUESTION_MONTH_INDEX.csv'),
                     (WP/'08_cross_region_government_coverage/nz_parliament_climate_answered_2025_month_index.csv','NZ_2025_PORTFOLIO_QUESTION_MONTH_INDEX.csv'),
                     (WP/'10_eu_cellar_acquisition/reports/eu_monthly_status.csv','EU_PRIOR_MONTHLY_STATUS.csv')]:
        shutil.copyfile(src,HERE/'inputs'/name)
    csvout('inputs/US_EU_AU_SAVED_MONTH_SOURCE_GENRE.csv',[r for r in old if not r['source_id'].startswith('src_')])
    return out


def main():
    annotate();au_plan();out=frames()
    jsout('BOUNDED_PARENT_EXPORT_REQUEST.json',{
      'status':'optional single bounded export proposal; not executed; not a media progression gate',
      'reason':'parent length by type and department crosswalk absent from saved aggregate inputs; Item lengths cannot substitute',
      'publication_interval':['2015-01-01','2015-12-31'],'fixed_study_interval':INTERVAL,
      'frames':['UK effective source/genre parents','US frozen EPA/DOE rules','EU frozen COM Work frame','AU verified original subset only'],
      'columns':['source_id','jurisdiction','native_parent_id','effective_publication_date_or_interval','date_basis','date_precision',
          'genre','verified_issuer_id','department_mapping_evidence_or_unknown','mirror_or_shared_utterance_group',
          'selected_content_version_id','version_time','retrieval_time','raw_sha256','readability_status','complete_Work_or_component_state',
          'stored_full_parent_text_char_count','stored_full_parent_word_count','length_definition','count_eligibility','evidence_locator'],
      'rules':['one source×date export under shared heavy-I/O lock from accepted stored views',
          'no full-corpus text scan, embeddings or fresh raw OCR; unavailable counts stay unknown',
          'reply/Work/source-container/component/version/segment remain distinct',
          'mirror sensitivity retained; department not guessed from platform',
          'no official write required; independent reviewer chooses any further analysis'],
      'export_executed':False})
    print(json.dumps({'frame_rows':len(out),'changed_items':20,'network_requests':0,'database_queries':0,'database_writes':0}))


if __name__=='__main__':main()
