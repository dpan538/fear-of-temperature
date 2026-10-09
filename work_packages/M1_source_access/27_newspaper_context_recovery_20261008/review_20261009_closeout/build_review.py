"""Reconcile finalized metadata and build descriptive, non-semantic planning views.

Never opens a corpus database, raw response or body. The model is a conditional
capacity scenario, not a fitted population/coverage forecast or execution release.
"""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PKG = ROOT / 'work_packages/M1_source_access/27_newspaper_context_recovery_20261008'
OUT = Path(__file__).resolve().parent
N = PKG / 'continuations/20261009_newspaper_open_production/worker'
S = PKG / 'social_public_api/continuations/20261009_public_native_expansion/worker'


def read(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def table(name, data):
    if not data:
        return
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    nd = read(N / 'DELIVERY_SUMMARY.json')
    sd = read(S / 'CLOSED.json')['snapshot']
    # Reuse the accepted database/body checks. Hash only selected final artifacts.
    selected = []
    for name, evidence in read(N / 'DELIVERY_FILE_RECEIPTS.json')['files'].items():
        if name.endswith('.sqlite3') or name in ['close_receipt.py', 'DELIVERY_SUMMARY.json', 'OPPORTUNITY_SUMMARY.json']:
            continue
        f = N / name
        assert digest(f) == evidence['sha256'], name
        selected.append(f)
    for evidence in sd['files']:
        f = S / evidence['path']
        assert digest(f) == evidence['sha256'], str(f)
        selected.append(f)
    for name, expected in sd['implementation_hashes'].items():
        f = S / name
        assert digest(f) == expected, name
        selected.append(f)
    # Focused regression implementations are useful final code, not execution receipts.
    selected.extend(N / x for x in ['check_metadata_robots_guard.py', 'check_frontier_batch_recovery.py', 'check_batch_html_extension.py'])
    selected = sorted(set(selected))
    assert nd['all_changed_tranche_checks_passed'] and not nd['mapping_errors']
    assert sd['changed_tranche_check']['new_native_mapping_check']['mapping_issues'] == 0
    assert read(S / 'FINAL_DELIVERY_CHECK.json')['lifetime_mutex_acquired_and_released']
    assert nd['collection_close']['writer_exit_observed']

    nr = rows(N / 'CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv')
    added = rows(N / 'ADDITIONAL_ARTICLE_REGISTER.csv')
    assert len(nr) == len({x['article_id'] for x in nr}) == 9538
    assert len(added) == len({x['article_id'] for x in added}) == 6453
    assert {x['article_id'] for x in added} <= {x['article_id'] for x in nr}
    assert all('1988-01-01' <= x['publication_date'][:10] <= '2026-09-21' for x in nr)
    assert not ({x['source_id'] for x in nr} & {'mit_tech', 'trinity_news', 'beaver', 'mancunion'})
    months = [f'{y}-{m:02}' for y in range(1988, 2027) for m in range(1, 13) if (y, m) <= (2026, 9)]
    monthly = rows(N / 'coverage/MONTHLY_pooled.csv')
    assert [x['month'] for x in monthly] == months
    nc = {x['month']: int(x['complete_native_article_IDs']) for x in monthly}
    nw = {x['month']: int(x['complete_independent_articles']) for x in monthly}
    actual = Counter(x['publication_date'][:7] for x in nr)
    assert all(actual[m] == nc[m] for m in months)
    assert sum(v >= 2 for v in nw.values()) == 365
    for ledger in (N / 'coverage').glob('*.csv'):
        entries = rows(ledger)
        assert [r['month'] for r in entries] == months
        stratum = entries[0]['stratum']
        members = [r for r in nr if stratum == 'pooled' or r['stratum'] == stratum]
        work_sets = defaultdict(set)
        native_counts = Counter()
        for r in members:
            month = r['publication_date'][:7]
            native_counts[month] += 1
            work_sets[month].add(r['work_family_id'] or r['article_id'])
        assert all(native_counts[r['month']] == int(r['complete_native_article_IDs']) and len(work_sets[r['month']]) == int(r['complete_independent_articles']) for r in entries)
    sm = rows(S / 'summaries/source_publication_month_counts.csv')
    sc = Counter()
    social_by_source = defaultdict(Counter)
    for r in sm:
        v = int(r['publication_month_qualified_independent_bodies'])
        sc[r['native_reported_month']] += v
        social_by_source[r['source_id']][r['native_reported_month']] += v
    assert sum(sc.values()) == 42478 and sum(v > 0 for v in sc.values()) == 165
    baseline = rows(PKG / 'review_20261009/tables/monthly_frame_coverage.csv')
    bn = {x['month']: int(x['native_article_IDs']) for x in baseline if x['analysis_frame'] == 'newspaper_current' and x['stratum'] == 'pooled'}
    if not bn:
        frames = {x['analysis_frame'] for x in baseline}
        name = next(f for f in frames if 'newspaper' in f)
        bn = {x['month']: int(x['native_article_IDs']) for x in baseline if x['analysis_frame'] == name and x['stratum'] == 'pooled'}
    merged = [dict(month=m, newspaper_articles=nc[m], newspaper_known_works=nw[m], newspaper_before=bn[m], social_dated_bodies=sc[m]) for m in months]
    table('monthly_distribution.csv', merged)

    mix = []
    names = {}
    for r in nr:
        names[r['source_id']] = r['source'] or r['source_id']
    for source, count in Counter(r['source_id'] for r in nr).most_common():
        source_rows = [r for r in nr if r['source_id'] == source]
        mix.append(dict(stream='newspaper', source_id=source, label=names[source], units=count, share=count/9538, observed_months=len({r['publication_date'][:7] for r in source_rows})))
    for r in sorted(sd['qualified_by_source'], key=lambda r: -r['qualified_native_units']):
        source, count = r['source_id'], r['qualified_native_units']
        mix.append(dict(stream='social', source_id=source, label=source, units=count, share=count/42488, observed_months=sum(v > 0 for v in social_by_source[source].values())))
    table('source_composition.csv', mix)
    coverage = []
    for stratum, c in nd['coverage'].items():
        coverage.append(dict(stratum=stratum, floor_months=c['months_at_minimum_coverage'], one_months=c['one_article_months'], zero_months=c['zero_article_months'], denominator=465))
    table('newspaper_regional_coverage.csv', coverage)

    periods = [('1988–1990','1988-01','1990-12'),('1991–2006','1991-01','2006-12'),('2007–2016','2007-01','2016-12'),('2017–2026*','2017-01','2026-09')]
    period_rows = []
    for label, first, last in periods:
        chosen = [m for m in months if first <= m <= last]
        period_rows.append(dict(period=label, months=len(chosen), newspaper_articles=sum(nc[m] for m in chosen), newspaper_floor=sum(nw[m]>=2 for m in chosen), social_dated_bodies=sum(sc[m] for m in chosen), social_present=sum(sc[m]>0 for m in chosen)))
    table('era_summary.csv', period_rows)
    gaps = []
    current = []
    for m in months + ['END']:
        if m != 'END' and nw[m] < 2:
            current.append(m)
        elif current:
            gaps.append(dict(start=current[0], end=current[-1], months=len(current), known_works=sum(nw[x] for x in current)))
            current = []
    table('newspaper_gap_runs.csv', sorted(gaps, key=lambda r: -r['months']))
    flags = []
    series = [('newspaper', nc), ('social_dated_bodies', sc)]
    for stream, counts in series:
        for i, m in enumerate(months):
            neighbors = [counts[months[j]] for j in range(max(0,i-3),min(len(months),i+4)) if j!=i]
            peak = counts[m] >= 20 and counts[m] >= 3*max([1]+neighbors)
            if peak:
                flags.append(dict(stream=stream, month=m, units=counts[m], max_observed_neighbor=max(neighbors), observed_neighbors=len(neighbors), flag='nonblocking_exploratory_20_and_3x_adjacent_max', attribution='unresolved; no event or error inferred'))
    table('nonblocking_peak_flags.csv', flags)

    calendars = rows(S / 'summaries/source_month_calendar.csv')
    applicability = []
    for source in social_by_source:
        rr = [x for x in calendars if x['source_id'] == source]
        states = Counter(x['state'] for x in rr)
        observed = sum(int(x['publication_month_qualified_independent_bodies'])>0 for x in rr)
        known_unobserved = states['applicable_unobserved']
        applicability.append(dict(source_id=source, observed_months=observed, known_applicable_unobserved=known_unobserved, known_applicable_denominator=observed+known_unobserved, unknown_era_months=states['historical_scope_unknown'], other_states=json.dumps({k:v for k,v in states.items() if k not in ['applicable_unobserved','observed_complete_text','historical_scope_unknown']})))
    table('social_applicable_eras.csv', applicability)
    relation_counts = Counter()
    for r in rows(S / 'summaries/relations_manifest.csv'):
        relation_counts[(r['relation_type'],r['resolution_state'])] += 1
    table('relation_resolution.csv', [dict(relation_type=k[0],state=k[1],edges=v) for k,v in sorted(relation_counts.items())])
    quality = rows(S / 'summaries/quality_by_source.csv')
    # Empirical throughput includes preparation in each released acquisition interval.
    start = datetime.fromisoformat('2026-10-09T02:41:51.640855+00:00')
    social_hours = (datetime.fromisoformat(sd['stop']['at_utc'])-start).total_seconds()/3600
    params = dict(hours=8, productive_hours=6.5, newspaper_per_hour=6453/4,
                  social_core_per_hour=40922/social_hours, social_acquisition_hours=social_hours,
                  social_objects_per_core=50000/40922, social_requests_per_core=971/40922,
                  newspaper_bytes_per_addition=50000, social_bytes_per_addition=25000,
                  newspaper_byte_assumption='Rounded planning allowance above mixed-stream residual observed growth; includes outputs, not an isolated body size',
                  social_byte_assumption='Rounded up from about 0.828 GB growth / 40,922 added core texts; raw, versions and repeated exports included',
                  physical_growth_planning_bytes=3_000_000_000, closeout_and_journal_reserve_bytes=500_000_000,
                  social_current_bytes=sd['budget_at_documentation_closeout']['social_bytes'],
                  shared_current_bytes=nd['resource_at_delivery']['cumulative_bytes'], shared_cap_bytes=15_000_000_000,
                  proposed_additional_objects=200000, proposed_additional_requests=5000,
                  cap_status='All next-round ceilings are planning assumptions, not an execution release')
    simulations = []
    added_months = Counter(x['publication_date'][:7] for x in added)
    # Expected floor under independent Poisson arrivals at empirical month shares.
    # This deliberately cannot invent coverage in months absent from this tranche.
    for social_cap in [2_000_000_000, 4_000_000_000]:
        for name, nf, sf in [('conservative',0.5,0.35),('central',1,0.65),('favorable',1.5,1)]:
            n = math.floor(params['productive_hours']*params['newspaper_per_hour']*nf)
            s_time = math.floor(params['productive_hours']*params['social_core_per_hour']*sf)
            s_byte = max(0,math.floor((social_cap-params['social_current_bytes'])/params['social_bytes_per_addition']))
            physical_left = max(0,params['physical_growth_planning_bytes']-params['closeout_and_journal_reserve_bytes']-n*params['newspaper_bytes_per_addition'])
            s_phys = math.floor(physical_left/params['social_bytes_per_addition'])
            s_obj = math.floor(params['proposed_additional_objects']/params['social_objects_per_core'])
            s_req = math.floor(params['proposed_additional_requests']/params['social_requests_per_core'])
            s = min(s_time,s_byte,s_phys,s_obj,s_req)
            expected = 0
            for m in months:
                lam = n*added_months[m]/6453
                expected += 1 if nw[m]>=2 else (1-math.exp(-lam) if nw[m]==1 else 1-math.exp(-lam)*(1+lam))
            simulations.append(dict(scenario=name,social_envelope_bytes=social_cap,newspaper_additions=n,newspaper_total=9538+n,social_core_additions=s,social_core_total=42488+s,social_unconstrained_by_bytes=s_time,estimated_growth_bytes=n*50000+s*25000,unchanged_month_support_expected_newspaper_floor=round(expected,1),unchanged_social_month_support=165,binding_social_limit='time' if s==s_time else 'social_envelope' if s==s_byte else 'physical_planning_capacity' if s==s_phys else 'objects_or_requests'))
    table('eight_hour_scenarios.csv', simulations)
    dump('model_parameters.json', params)
    summary = dict(newspaper=dict(total=9538,added=6453,floor_months=365,one=15,zero=85,baseline=3085,baseline_floor=262,exactly_two_months=sum(v==2 for v in nw.values()),sources=len(names),campus_preserved=9249),social=dict(core=42488,added=40922,independent=42487,dated=42478,months=165,sources=14,entities=51626,versions=54789,relations=88091,attachments=17213,date_pending=9,institutional=156,unknown_role=42332),newspaper_source_mix=mix[:len(names)],social_source_mix=mix[len(names):],coverage=coverage,eras=period_rows,peak_flags=flags,scenarios=simulations,model_parameters=params)
    dump('summary.json', summary)
    dump('chart_data.json', dict(months=merged,summary=summary,applicability=applicability,quality=quality))
    dump('acceptance.json', dict(selected_artifacts_verified=len(selected),artifact_bytes=sum(x.stat().st_size for x in selected),newspaper_changed_checks=nd['checks'],social_changed_checks=sd['changed_tranche_check'],metadata_reconciled=True,old_corpus_rescanned=False,databases_opened=False,owner_windows_messaged=False))
    (OUT/'control').mkdir(exist_ok=True)
    dump('control/publish_paths.json',[str(f.relative_to(ROOT)) for f in selected])
    dump('input_artifact_manifest.json',[dict(path=str(f.relative_to(ROOT)),bytes=f.stat().st_size,sha256=digest(f)) for f in selected])
    print(json.dumps(dict(summary=summary,selected_files=len(selected),selected_bytes=sum(x.stat().st_size for x in selected)),ensure_ascii=False))


if __name__ == '__main__':
    main()
