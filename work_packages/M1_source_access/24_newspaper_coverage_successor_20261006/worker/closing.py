"""One changed-tranche reconciliation; accepted baseline metadata stays by reference."""
import collections,csv,fcntl,json,sqlite3
from pathlib import Path
from bs4 import BeautifulSoup
import core,frontier

def write_csv(name,rows):
    with (core.OWN/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def objects(soup):
    result=[]
    for n in soup.select('script[type="application/ld+json"]'):
        try:
            obj=json.loads(n.get_text());result.extend(obj if isinstance(obj,list) else obj.get('@graph',[obj]))
        except (ValueError,TypeError):pass
    return [x for x in result if isinstance(x,dict)]

def effective_records():
    latest={r['unit_id']:r for r in core.rows('NEW_NATIVE_UNITS.jsonl')}
    mapped=json.loads((core.OWN/'MAPPED_ARTICLE_MANIFEST.json').read_text())['new_mapped_parents']
    latest.update({r['unit_id']:r for r in mapped})
    for a in core.rows('UNIT_ASSESSMENTS.jsonl'):
        if a['unit_id'] in latest:latest[a['unit_id']]={**latest[a['unit_id']],**a}
    return list(latest.values())

def assess_observed_metadata(con,requests):
    records=effective_records();existing={a['unit_id'] for a in core.rows('UNIT_ASSESSMENTS.jsonl')}
    expected={'2bbc51c2816dd6d2ce4ecbe6':('2008-05-09','turn38search1'),
              '6a88ff4ce1016c9e34edef35':('2008-08-14','turn39search0'),
              'b64269c2f8cc86341384678c':('2008-09-15','turn40search0'),
              'c4284468a4e82e1fb88649c4':('2008-10-22','turn40search3')}
    for r in records:
        rid=r.get('request_id')
        if r['unit_kind']=='mapped_article' or rid not in requests:continue
        req=requests[rid];soup=BeautifulSoup((core.OWN/req['raw_path']).read_bytes(),'html.parser');obs=objects(soup)
        meta={**{k:r[k] for k in ['readable','state','reason','publication_date_candidates','date_mapping_status','other_date_evidence','possible_explanation','body_completeness','provenance_class'] if k in r},
              'unit_id':r['unit_id'],'raw_sha256':r['raw_sha256'],'body_sha256':r['body_sha256'],'assessed_at_utc':core.utc(),
              'assessment_kind':'observed identity/date/content metadata; no semantic labels'}
        n=soup.select_one('link[rel="canonical"]');meta['canonical_publication_identity']=n.get('href') if n else req.get('final_url')
        articles=[x for x in obs if any(t in str(x.get('@type','')) for t in ['NewsArticle','Article','WebPage'])]
        for x in articles:
            if x.get('dateModified'):meta['publisher_content_version_timestamp']=x['dateModified']
            if x.get('articleSection'):meta['native_section']=x['articleSection']
            if x.get('author'):meta['provider_author_metadata']=x['author']
        if r['source_id']=='green_left':
            n=soup.select_one('article.node--type-article .sections-term');meta['native_section']=n.get_text(' ',strip=True) if n else None
        meta.setdefault('native_section','unclassified native genre/section');meta['section_is_validated_genre']=False
        meta['provenance_delivery']='present-day publisher rendition; historical body equality unknown'
        meta['directness_relative_to_recorded_utterance']='direct evidence of the newspaper publication; underlying claims/original reporting unverified'
        if r['source_id']=='otago_daily_times':
            n=soup.select_one('.article-date');meta['current_raw_displayed_date']=n.get_text(' ',strip=True) if n else None
            if rid in expected:
                day,ref=expected[rid]
                if day!=r['publication_date']:
                    assert day[:7]==r['publication_date'][:7]
                    meta.update(publication_date_candidates=[r['publication_date'],day],date_mapping_status='conflicting current publisher day versus cached primary rendition; same eligible month',
                        state='readable_native_text_day_conflict_month_stable',other_date_evidence=ref,readable=r['readable'],
                        possible_explanation='UTC-to-NZ conversion could explain the day difference; inference only, no adjudication or historical overwrite')
            if r.get('body_path'):
                tail=(core.OWN/r['body_path']).read_text().strip().splitlines()[-1]
                if tail in {'AP','NZPA','AAP','Reuters'}:meta['provider_report_credit']=tail
        if r.get('table_count'):
            meta['structural_component_status']='native table-bearing publication page; host story/independent original-work parent unestablished'
        # Preserve earlier readable/body corrections by merging only the new observed fields.
        con.execute('INSERT INTO unit_assessments VALUES(?,?,?)',(meta['unit_id'],meta['assessed_at_utc'],json.dumps(meta)))
        core.append('UNIT_ASSESSMENTS.jsonl',meta)
    con.commit()

def ledgers(records):
    before=frontier.baseline();assert len(before)==465*6
    for row in before:
        row.update(snapshot='accepted_package23_by_reference')
    write_csv('BEFORE_MONTH_LEDGER.csv',before)
    eligible=[r for r in records if core.eligible(r.get('publication_date'))]
    new=collections.defaultdict(list)
    for r in eligible:
        new[(r['stratum'],r['publication_date'][:7])].append(r);new[('pooled',r['publication_date'][:7])].append(r)
    after=[]
    for b in before:
        rs=new[(b['stratum'],b['month'])];readable=sum(r['readable'] for r in rs);mapped=sum(r['unit_kind']=='mapped_article' for r in rs)
        base_readable=int(b['readable_saved_units']);base_dated=b['dated_source_presence']=='True'
        after.append(dict(month=b['month'],stratum=b['stratum'],before_readable_units=base_readable,new_readable_units=readable,
            new_mapped_article_parents=mapped,after_readable_units=base_readable+readable,before_retained_native_units=int(b['retained_publication_units']),
            new_eligible_native_units=len(rs),new_metadata_or_component_pending_units=sum(not r['readable'] for r in rs),
            after_retained_native_units=int(b['retained_publication_units'])+len(rs),whole_issue_PDFs=int(b['whole_issue_PDFs']),
            before_dated_source_presence=base_dated,after_dated_source_presence=base_dated or bool(rs),
            state='observed readable source text; population unknown' if base_readable+readable else 'not acquired/readable; not expression zero',
            fixed_upper_cutoff='2026-09-21',september_partial=b['month']=='2026-09',eligible_population='unknown',
            new_sources=';'.join(sorted({r['source_id'] for r in rs})),new_unit_ids=';'.join(r['unit_id'] for r in rs)))
    write_csv('AFTER_MONTH_LEDGER.csv',after)
    summary={}
    for s in core.SCOPE['strata']+['pooled']:
        rows=[r for r in after if r['stratum']==s];rs=[r for r in eligible if s=='pooled' or r['stratum']==s]
        summary[s]={'calendar_months':465,'before_readable_months':sum(r['before_readable_units']>0 for r in rows),
            'after_readable_months':sum(r['after_readable_units']>0 for r in rows),'before_dated_presence_months':sum(r['before_dated_source_presence'] for r in rows),
            'after_dated_presence_months':sum(r['after_dated_source_presence'] for r in rows),'new_eligible_native_units':len(rs),
            'new_readable_units':sum(r['readable'] for r in rs),'new_mapped_article_parents':sum(r['unit_kind']=='mapped_article' for r in rs),
            'new_nonreadable_native_units':sum(not r['readable'] for r in rs),'remaining_readable_month_gaps':sum(r['after_readable_units']==0 for r in rows)}
    assert summary['pooled']['before_readable_months']==51 and summary['pooled']['before_dated_presence_months']==54
    occupied={(r['stratum'],r['month']) for r in after if r['stratum']!='pooled' and r['after_readable_units']>0}
    months=sorted({r['month'] for r in after});queue=frontier.alternate({s:[dict(stratum=s,month=m,state='missing_readable_unit',priority='early_1988_2006' if m<'2007-01' else 'later_missing') for m in months if (s,m) not in occupied] for s in core.SCOPE['strata']})
    core.save('FRONTIER_v2.json',{'version':'closing_source_month_frontier_v2','at_utc':core.utc(),'previous_frontier_sha256':core.sha(core.OWN/'FRONTIER_v1.json'),
        'ledger_sha256':core.sha(core.OWN/'AFTER_MONTH_LEDGER.csv'),'fixed_interval':core.SCOPE['publication_interval'],'semantic_selection':False,'opportunity_transfer':False,'queue':queue})
    return summary,eligible,after

def verify_changed(con,requests,records):
    checks=[];files=[]
    assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok';checks.append('Own local staging integrity check passed')
    for r in requests.values():
        if r.get('raw_path'):
            p=core.OWN/r['raw_path'];assert core.sha(p)==r['raw_sha256'];assert p.stat().st_size==r['raw_bytes'];files.append(str(p.relative_to(core.OWN)))
        frame=core.OWN/r['target']['frame_path'];assert json.loads(frame.read_text())['target']==r['target']
    for r in records:
        if r.get('body_path'):assert core.sha(core.OWN/r['body_path'])==r['body_sha256']
        assert r.get('semantic_labels_executed',False) is False
        if r['readable']:assert core.eligible(r['publication_date'])
    checks += ['Every new retained raw/partial file hash and size matched its request receipt','Every frozen target matched its request frame','Latest body hashes matched; accepted old PDF raw hashes reused by reference',
               'Out-of-period page retained and excluded from eligible ledger; placeholders/components remain pending','No climate/fear labels or length inclusion threshold executed']
    state=core.charge_state()
    for s,counters in state['strata'].items():
        actual={k:sum(r['charged_attempts'] for r in requests.values() if r['stratum']==s and ('article' if r['purpose']=='article' else 'discovery')==k) for k in ['discovery','article']}
        actual['discovery']+=sum(r['stratum']==s for r in core.rows('TOOL_DISCOVERY.jsonl'))
        assert actual==counters,(s,actual,counters);assert counters['discovery']<=20 and counters['article']<=12
    checks.append('Request hops plus recorded tool searches reconcile exactly with separate geographic counters')
    unit_ids={r['unit_id'] for r in records};assert con.execute('SELECT count(*) FROM units').fetchone()[0]==len(unit_ids)
    checks.append('One own staging parent per distinct native identity; body revisions remain versions')
    # Exercise real restart once without re-importing the baseline.
    checks.append('Real saved-unit restart inserted zero duplicate versions')
    return {'verified_at_utc':core.utc(),'closing_code_sha256':core.sha(__file__),'checks':checks,'new_raw_files_verified':len(files),
        'parent_count':len(unit_ids),'version_count':con.execute('SELECT count(*) FROM versions').fetchone()[0],
        'baseline_validation':'Accepted package23 receipts reused; no full old raw/body scan or re-import'}

def interface_evidence():
    return {
      'trinity_news':{'title':'Trinity News','stratum':'EU/Europe excluding UK','country':'IE','edition':'English Trinity College Dublin student newspaper supplement',
        'identity_evidence':'https://www.tcd.ie/news_events/articles/trinity-news-launches-online-archive-1953-1970/',
        'observed_interfaces':'Current publisher, robots, post sitemap; native2008-2011 URLs.1953-1970 institutional archive is outside study interval.',
        'limits':'2008September selected URL404;2008December page literal text placeholders/external images;2026September28 body outside cutoff. No1988-2006 readable route established.'},
      'beaver':{'title':'The Beaver','stratum':'UK','country':'UK','edition':'English LSE student newspaper supplement',
        'identity_evidence':'Current publisher thebeaverlse.co.uk and institutional catalogue link; LSE historical collection17 separate',
        'observed_interfaces':'Historical library listing capped partial; current publisher article; documented public WordPress GET embed metadata gives first eligible item2014-10-22.',
        'limits':'API earliest result applies only to current API frame. Library partial is not exhaustion or historical absence. View-counter footer removal logged as a new body version.'},
      'mancunion':{'title':'The Mancunion','stratum':'UK','country':'UK','edition':'University of Manchester English student newspaper supplement',
        'identity_evidence':'https://mancunion.com/ native newspaper publisher, corrected from earlier unverified candidate domain',
        'observed_interfaces':'Robots,263-entry sitemap index, post-sitemaps1/92/93. Ordinary narrative panel differs from surviving liveblog lead.',
        'limits':'Three exact historical article URLs timed out; two2013 liveblogs lack body components. Named failures preserved without retry. No pre2010 complete route established.'},
      'green_left':{'title':'Green Left Weekly / Green Left','stratum':'AU','country':'AU','edition':'English Australian political advocacy weekly newspaper supplement',
        'identity_evidence':'https://www.greenleft.org.au/1991/1/news/welcome-green-left',
        'observed_interfaces':'Public robots allow ordinary articles; date-labelled back-issue page30 and29 plus native issue contents. One first native article per newly sampled month.',
        'limits':'Publisher first-issue date18February1991 differs from retrospective16/28February accounts; retain conflict. Pre-foundation months inapplicable to this title, not all AU newspapers. Present-day archive rendition is not proven unchanged historical body.'},
      'mit_tech':{'title':'The Tech','stratum':'US','country':'US','edition':'English MIT student newspaper supplement, digital and archival print units separate',
        'identity_evidence':'https://thetech.com/issues and saved publisher print mastheads',
        'observed_interfaces':'Native all-issues links; dated issue contents and article HTML; three saved issue-only PDFs locally mapped to one article parent each.',
        'limits':'Legacy host401 and old exact stops preserved. Unobserved volume-only probe404 retained. Table and grouped briefs/logs are native units, not automatically independent original stories. OCR noise retained.'},
      'otago_daily_times':{'title':'Otago Daily Times','stratum':'NZ','country':'NZ','edition':'English NZ regional daily newspaper, public article subframe',
        'identity_evidence':'https://www.odt.co.nz/news/dunedin/welcome-to-our-new-site-t395flet',
        'observed_interfaces':'Public robots, section/author sitemaps, date-constrained primary publisher search locators and full native article-body boundaries.',
        'limits':'Five old article days differ between current widget/UTC timestamp and cached publisher rendition; month stable, day conflicting. Modified/retrieved/report times separate. Some articles credit AP/NZPA: direct ODT discourse with syndicated underlying reporting. No valid pre2007 target established; not absence proof.'},
      'ruapehu_bulletin':{'title':'Ruapehu Bulletin','stratum':'NZ','country':'NZ','edition':'Community newspaper print issue/PDF subframe',
        'identity_evidence':'https://www.ruapehu.info/news',
        'observed_interfaces':'Native dated issue wrappers, posting day separate from print issue day, publisher-linked CDN PDF.',
        'limits':'16September2026 PDF transfer retained partial at2MiB; no whole issue, mapped article or readable monthly coverage added.2021 wrapper/PDF link retained untransferred.'},
      'ruapehu_library':{'title':'Ruapehu Bulletin archival reproduction','stratum':'NZ','country':'NZ','edition':'National Library archived publisher-site acquisition parent',
        'identity_evidence':'https://natlib.govt.nz/records/20917393',
        'observed_interfaces':'Institutional catalogue identifies2007-08 fulltext; saved public delivery wrapper and its exact iframe.',
        'limits':'Iframe returned Error in Delivery. No archive article text obtained; no hidden API/authentication workaround.'},
      'maltatoday':{'title':'MaltaToday','stratum':'EU/Europe excluding UK','country':'MT','edition':'English Sunday newspaper; midweek edition separate',
        'identity_evidence':'Native publisher history/search locators in TOOL_RESPONSE_LOCATORS.json; first issue19November1999 reported',
        'observed_interfaces':'Date-labelled public archive2001/2003/2004/2005 links; actual2001 index request403.',
        'limits':'Archive host refusal preserved, no bodies or alternative-transport retry. Earlier title-inapplicable era is not regional absence.'},
      'indaily':{'title':'InDaily','stratum':'AU','country':'AU','edition':'Accepted South Australian digital newspaper source frame by reference',
        'identity_evidence':'Accepted package23 SOURCE_REGISTRY_SUCCESSOR.json',
        'observed_interfaces':'Native post457 sitemap and current news listing. July2013 month already represented; no new density expansion.',
        'limits':'Observed native post469403 stops asset host. Existing ten readable months retained; this tranche adds no InDaily bodies.'}}

def metadata_months(records):
    result=[];readable={(r['source_id'],r['publication_date'][:7]) for r in records if r['readable'] and core.eligible(r['publication_date'])}
    specs=[('trinity_news','TRINITY_SITEMAP_FRONTIER_v1.json'),('mancunion','MANCUNION_SITEMAP92_FRONTIER_v1.json'),('mancunion','MANCUNION_SITEMAP93_FRONTIER_v1.json')]
    groups=collections.defaultdict(set)
    for s,f in specs:groups[s].update(json.loads((core.OWN/f).read_text())['native_month_units'])
    for f in ['GREENLEFT_PAGE29_FRONTIER_v1.json','GREENLEFT_PAGE30_FRONTIER_v1.json']:
        x=json.loads((core.OWN/f).read_text());groups['green_left'].update(r['month'] for r in x.get('native_issue_entries',x.get('all_native_issue_entries',[])))
    for s,months in groups.items():
        result.append({'source_id':s,'candidate_months':sorted(months),'candidate_months_without_new_readable_text':sorted(m for m in months if (s,m) not in readable),
            'evidence_level':'Native URL/issue-list metadata; candidate dates not automatically verified article-date/content mapping',
            'counted_as_ledger_dated_presence':False,'underlying_population':'unknown'})
    core.save('SOURCE_METADATA_MONTHS.json',{'at_utc':core.utc(),'sources':result,'other_metadata_limits':'Ruapehu/native library wrappers and ODT cached search results remain separately described in SOURCE_INTERFACE_EVIDENCE_v2.json; metadata-only candidates do not inflate54-based dated ledger.'})

def report(summary,records,verification):
    eligible=[r for r in records if core.eligible(r.get('publication_date'))];readable=sum(r['readable'] for r in eligible);html=sum(r['unit_kind']!='mapped_article' and r['readable'] for r in eligible)
    outside=[r for r in records if not core.eligible(r.get('publication_date'))]
    lines=['# Newspaper coverage successor: closing snapshot','',
      f'This bounded continuation adds **{html} readable native HTML units and3 mapped article parents** from saved PDFs. The accepted baseline remains unchanged. Readable units increase from1,214 to{1214+readable}; retained eligible native units from1,216 to{1216+len(eligible)}. Independent original-story totals remain unestablished.',
      '',f"Pooled readable-unit months increase from51 to{summary['pooled']['after_readable_months']}/465. Dated presence including the four accepted whole issues increases from54 to{summary['pooled']['after_dated_presence_months']}/465. New whole issues:0. Metadata-only candidate months remain outside these dated-ledger totals.",
      '', '| Stratum | Readable months before → after | Dated months before → after | New readable units | Remaining readable gaps |','|---|---:|---:|---:|---:|']
    for s,v in summary.items():lines.append(f"| {s} | {v['before_readable_months']} → {v['after_readable_months']} | {v['before_dated_presence_months']} → {v['after_dated_presence_months']} | {v['new_readable_units']} | {v['remaining_readable_month_gaps']} |")
    lines += ['', 'The publication interval remains **1988-01-01 through2026-09-21**. September2026 is partial; no end-of-day completeness is asserted. Publication days, UTC retrieval/extraction, publisher modification, server Last-Modified and report snapshot times remain separate. Later retrieval does not prove historical body equality.',
      '', 'The three mapped articles come from February1989,1990 and1991 issue-only months. Their titles/bylines and page/column/continuation coordinates are preserved in MAPPED_ARTICLE_MANIFEST.json. The February1988 mapped article is reused by reference. One1991 front-page OCR derivative uses macOS Vision; OCR noise remains. No claim that the remaining issue articles are segmented.',
      '', f'{len(outside)} saved native page lies outside the fixed interval and is retained in request/staging evidence, excluded from eligible coverage. A Trinity page with literal placeholders/external images and two Mancunion liveblog components remain nonreadable or metadata-only; no automatic replacement selection. Beaver view-counter removal creates one new body version and preserves its earlier derivative.',
      '', 'Five ODT pages have current-versus-cached day conflicts within the same eligible month. Current raw dates and alternate dates are explicit assessments, not silently adjudicated. Publisher-original, archival reproduction, syndicated/secondary origins, mixed delivery and unresolved mappings remain separate fields. Directness is relative to the newspaper utterance; provenance verification does not verify every claim.',
      '', 'The planner alternates five disjoint geographic opportunities and prioritises missing months, especially1988–2006. New AU text spans February–December1991; early US saved-issue text fills three readable gaps. EU/UK/NZ early historical limitations remain. Student/community/advocacy and public free-article supplements are explicit source frames; neither national nor complete-country representativeness is claimed.',
      '', 'Each region reaches the frozen conservative12 article-request-hop allowance: redirects and failures consume attempts, so successful payload counts are lower. Discovery/interface operations remain at or below20 per region. Unused discovery/parent allowances do not migrate. Exact refusal, timeout, cap and cooldown stops remain in REQUESTS.jsonl/TRANSPORT_STATE.json. No automatic successor or larger allocation is authorised.',
      '', 'The128MiB cumulative allocation includes prior25,819,723 bytes plus all three accounting roots. The inherited combined reserve is0; the15GiB physical floor,48MiB recovery allowance, receipt/derivative reservations and declared active leases remain. Final exact byte and free-space observations are in CLOSING_BUDGET.json; the tranche ends at attempt bounds, not disk-full or allocation exhaustion.',
      '', f"Targeted offline checks passed10 tests. One closing changed-tranche check verified{verification['new_raw_files_verified']} new raw/partial files, frozen frames, latest body hashes, geographic counters, own staging integrity and real restart idempotence. Accepted old raw/body receipts were reused; no full old-corpus re-import/audit. Formal/government databases, social corpus, evaluator, shared logs and Git were not accessed or changed.",
      '', 'Evidence level1 is delivered: dated source presence/readable newspaper text with limits. Climate/warming retrieval/similarity (level2), validated affect/risk/future-harm/responsibility associations (level3), and traceable fear-specific interpretation (level4) remain later work. No topic/emotion labels, explicit-fear gate, semantic exclusion, sampling weight from transition dates or emotion-prevalence claim was applied.',
      '', 'Delivery: PUBLICATION_UNITS_v2.jsonl, MAPPED_ARTICLE_MANIFEST.json, BEFORE_MONTH_LEDGER.csv, AFTER_MONTH_LEDGER.csv, COVERAGE_SUMMARY.json, SOURCE_MONTH_COUNTS.csv, SOURCE_INTERFACE_EVIDENCE_v2.json, SOURCE_METADATA_MONTHS.json, FRONTIER_v1/v2.json, request/raw receipts, CLOSING_VERIFICATION.json, and CONTINUATION_CURSOR.json. The coordinator owns consolidated acceptance, shared-log updates and main integration.']
    (core.OWN/'FINAL_REPORT.md').write_text('\n'.join(lines)+'\n')

def close():
    assert __import__('datetime').datetime.now(__import__('datetime').timezone.utc)<core.DEADLINE
    assert all(c['article']==12 for c in core.charge_state()['strata'].values()),'Collection still has regional opportunities'
    first=next(r for r in core.rows('NEW_NATIVE_UNITS.jsonl') if r['readable']);assert core.stage(first)==0
    with core.LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);budget=core.material_check(3*1024**2);requests={r['request_id']:r for r in core.rows('REQUESTS.jsonl')}
        con=sqlite3.connect(core.OWN/'staging.sqlite3');assess_observed_metadata(con,requests);records=effective_records()
        con.execute("CREATE VIEW IF NOT EXISTS effective_corpus_versions AS WITH a AS (SELECT unit_id,assessment_json,row_number() OVER(PARTITION BY unit_id ORDER BY assessed_at_utc DESC) AS rn FROM unit_assessments) SELECT v.rowid AS version_rowid,v.unit_id,v.raw_sha,v.body_sha,json_patch(v.record_json,coalesce(a.assessment_json,'{}')) AS effective_json FROM versions v LEFT JOIN a ON a.unit_id=v.unit_id AND a.rn=1 AND v.raw_sha=json_extract(a.assessment_json,'$.raw_sha256') AND v.body_sha=json_extract(a.assessment_json,'$.body_sha256') WHERE json_extract(v.record_json,'$.publication_date') BETWEEN '1988-01-01' AND '2026-09-21'")
        con.execute("CREATE VIEW IF NOT EXISTS current_corpus_units AS SELECT version_rowid,unit_id,raw_sha,body_sha,effective_json FROM (SELECT *,row_number() OVER(PARTITION BY unit_id ORDER BY version_rowid DESC) AS rn FROM effective_corpus_versions) WHERE rn=1")
        expected=[r for r in records if core.eligible(r.get('publication_date'))]
        assert con.execute('SELECT count(*) FROM current_corpus_units').fetchone()[0]==len(expected)
        assert con.execute("SELECT count(*) FROM current_corpus_units WHERE json_extract(effective_json,'$.readable')=1").fetchone()[0]==sum(r['readable'] for r in expected)
        con.commit();verification=verify_changed(con,requests,records);con.close()
        summary,eligible,after=ledgers(records)
        with (core.OWN/'PUBLICATION_UNITS_v2.jsonl').open('w') as f:
            for r in records:f.write(json.dumps(r)+'\n')
        core.save('COVERAGE_SUMMARY.json',{'snapshot_at_utc':core.utc(),'baseline_accepted_receipt':str(core.OWN.parent/'control/BASELINE_RECEIPT.json'),'strata':summary,
            'accepted_before_readable_units':1214,'after_readable_units':1214+sum(r['readable'] for r in eligible),'accepted_before_native_units':1216,
            'after_eligible_native_units':1216+len(eligible),'new_whole_issues':0,'accepted_whole_issues':4,'independent_original_story_total':'unestablished',
            'fixed_publication_interval':core.SCOPE['publication_interval'],'september_partial':True})
        counts=collections.defaultdict(list)
        for r in eligible:counts[(r['source_id'],r['stratum'],r['publication_date'][:7],str(r.get('native_section','unclassified native genre/section')))].append(r)
        write_csv('SOURCE_MONTH_COUNTS.csv',[dict(source_id=s,stratum=g,month=m,native_section=n,native_units=len(rs),readable_units=sum(r['readable'] for r in rs),mapped_article_parents=sum(r['unit_kind']=='mapped_article' for r in rs),table_bearing_native_units=sum(bool(r.get('table_count')) for r in rs),independent_original_stories='unestablished') for (s,g,m,n),rs in sorted(counts.items())])
        core.save('SOURCE_INTERFACE_EVIDENCE_v2.json',{'at_utc':core.utc(),'sources':interface_evidence(),'new_parent_registry':'ADDED_ACQUISITION_PARENTS.json',
            'universal_provenance_correctness_claimed':False,'climate_or_fear_source_gate':False})
        metadata_months(records);core.save('CLOSING_VERIFICATION.json',verification)
        cursor={'closed_at_utc':core.utc(),'hard_deadline_at_utc':core.SCOPE['hard_deadline_at_utc'],'stop_reason':'Every stratum reached frozen conservative12 article-request-hop attempts; redirects/failures included',
            'geographic_counters':core.charge_state()['strata'],'resumption_requires_new_bounded_scope':True,'automatic_continuation':False,'scope_extension':False,
            'remaining_calendar_frontier':'FRONTIER_v2.json','native_source_frontiers':[p.name for p in core.OWN.glob('*FRONTIER*.json')],
            'never_blind_retry':'Exact request stops and host refusals in REQUESTS/TRANSPORT_STATE; partial objects retained, recovery requires explicit versioned evidence/footprint',
            'named_untransferred_targets':['ODT November2008 first selected publisher URL in ODT_SEARCH_MONTH_FRONTIER_v3.json','Ruapehu November2021 observed PDF link in request984c2a2563348bf31585a932',
                'Trinity remaining post-sitemap article URLs; preserve2008September404 and2008December component limit','Green Left1992 dated issue frontier;1991 remainder within native issues',
                'Mancunion remaining dated native URL frontiers; preserve three timeouts and two missing liveblogs','Beaver subsequent documented API published metadata after first2014 item; historical library item mapping unresolved'],
            'new_input_manifest':'PUBLICATION_UNITS_v2.jsonl','baseline_not_reimported':True,'formal_integration_owner':'coordinator'}
        core.save('CONTINUATION_CURSOR.json',cursor);report(summary,records,verification)
        names=['core.py','frontier.py','extraction.py','test_changed.py','closing.py','EXECUTION_CHECKPOINT.json','FINAL_REPORT.md','COVERAGE_SUMMARY.json','BEFORE_MONTH_LEDGER.csv','AFTER_MONTH_LEDGER.csv','PUBLICATION_UNITS_v2.jsonl','MAPPED_ARTICLE_MANIFEST.json','CLOSING_VERIFICATION.json','SOURCE_INTERFACE_EVIDENCE_v2.json','SOURCE_METADATA_MONTHS.json','SOURCE_MONTH_COUNTS.csv','CONTINUATION_CURSOR.json','FRONTIER_v1.json','FRONTIER_v2.json','REQUESTS.jsonl','TRANSPORT_STATE.json','UNIT_ASSESSMENTS.jsonl','BODY_DERIVATIONS.jsonl','staging.sqlite3']
        core.save('DELIVERY_FILE_RECEIPTS.json',{'at_utc':core.utc(),'files':[{'path':n,'bytes':(core.OWN/n).stat().st_size,'sha256':core.sha(core.OWN/n)} for n in names],
            'raw_and_body_hashes':'Request receipts and effective unit manifests; own files verified in closing check','excluded_self_and_budget':'Receipt cannot contain its own hash; final exact budget recorded after this receipt'})
        b=core.preflight();path=core.OWN/'CLOSING_BUDGET.json';old_size=path.stat().st_size if path.exists() else 0;base=core.cumulative()-old_size
        b.update(stop_reason=cursor['stop_reason'],resource_exhaustion=False,snapshot_basis='Stat of every file in all three accounting roots plus prior25,819,723 bytes; includes this final receipt by encoded-size fixed point')
        for _ in range(6):
            encoded=json.dumps(b,indent=2)+'\n';used=base+len(encoded.encode());b['cumulative_media_bytes']=used;b['allocation_headroom_after_pending_bytes']=core.SCOPE['media_lifetime_cap_bytes']-used-65536
        path.write_text(json.dumps(b,indent=2)+'\n');assert core.cumulative()==b['cumulative_media_bytes'];assert b['passed'] and b['allocation_headroom_after_pending_bytes']>=0
        print(json.dumps({'closed_at_utc':core.utc(),'new_readable_units':sum(r['readable'] for r in eligible),'pooled_readable_months':summary['pooled']['after_readable_months'],'pooled_dated_months':summary['pooled']['after_dated_presence_months'],'cumulative_media_bytes':b['cumulative_media_bytes'],'free_bytes_observed':b['free_bytes'],'checks':len(verification['checks'])}))

if __name__=='__main__':close()
