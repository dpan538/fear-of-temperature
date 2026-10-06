"""Close only this bounded newspaper package; no network, collection or DB mutation."""
import collections
import csv
import datetime as dt
import fcntl
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

OWN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OWN / 'prototype'))
import transport

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(relative):
    return json.loads((OWN / relative).read_text())

def save(relative, value):
    (OWN / relative).write_text(json.dumps(value, indent=2) + '\n')

def main():
    at = dt.datetime.now(dt.timezone.utc).isoformat()
    scope = transport.SCOPE
    registry = read('sources/SOURCE_REGISTRY_EFFECTIVE.json')
    sources = registry['sources']
    allowances = read('sources/REQUEST_ALLOWANCES.json')['titles']
    discovery = [json.loads(line) for line in (OWN/'sources/DISCOVERY_REQUESTS.jsonl').read_text().splitlines()]
    policies = [json.loads(line) for line in (OWN/'sources/POLICY_REQUESTS.jsonl').read_text().splitlines()]
    regional = list(csv.DictReader((OWN/'coverage/REGIONAL_MONTH_LEDGER.csv').open()))
    pooled = list(csv.DictReader((OWN/'coverage/POOLED_MONTH_LEDGER.csv').open()))
    tests = read('tests/TEST_RECEIPT.json')
    raw_manifest = read('manifests/NEWSPAPER_RAW_AND_REQUEST_MANIFEST.json')
    checks = {}
    checks['registry_twenty_four_per_stratum'] = len(sources)==20 and collections.Counter(s['stratum'] for s in sources)=={s:4 for s in scope['strata']}
    checks['regional_coordinates_unique_2325'] = len(regional)==2325 and len({(r['stratum'],r['month']) for r in regional})==2325
    checks['pooled_months_unique_465'] = len(pooled)==465 and len({r['month'] for r in pooled})==465
    checks['equal_planned_effort_465_per_stratum'] = all(sum(int(r['planned_presence_effort']) for r in regional if r['stratum']==s)==465 for s in scope['strata'])
    checks['fixed_endpoint_and_partial_month'] = scope['publication_interval']==['1988-01-01','2026-09-21'] and all(r['period_end']=='2026-09-21' and r['partial_month']=='True' for r in regional if r['month']=='2026-09') and min(r['month'] for r in regional)=='1988-01' and max(r['month'] for r in regional)=='2026-09'
    checks['population_unknown_not_observed_zero'] = all(r['underlying_publication_count']==r['eligible_frame_population']==r['inclusion_probability']=='' and r['verified_empty_frame']=='False' for r in regional)
    checks['newspaper_qualified_counts_zero'] = all(r['qualified_retained_article_count']=='0' for r in regional+pooled)
    checks['no_newspaper_payload_requests_raw_or_frozen_article_frames'] = raw_manifest['newspaper_network_payload_requests']==0 and not raw_manifest['newspaper_payload_receipts'] and not raw_manifest['newspaper_raw_objects'] and not raw_manifest['newspaper_frozen_article_frames']
    checks['request_limits'] = all(allowances[s['title_id']]['metadata']<=32 and allowances[s['title_id']]['search']<=3 for s in sources)
    checks['visible_request_reconciliation'] = sum(v['metadata'] for v in allowances.values())==len(discovery)+len(policies)==147 and sum(v['search'] for v in allowances.values())==34
    checks['test_receipt_current_code_and_output'] = tests['exit_code']==0 and all(sha(OWN/p)==digest for p,digest in tests['code_digests'].items()) and sha(OWN/'tests/LATEST_TEST_OUTPUT.txt')==tests['output_sha256'] and 'Ran 25 tests' in (OWN/'tests/LATEST_TEST_OUTPUT.txt').read_text()
    schema=read('coverage/LEDGER_SCHEMA.json')
    checks['ledger_uses_effective_registry'] = schema['source_registry_sha256']==sha(OWN/'sources/SOURCE_REGISTRY_EFFECTIVE.json')
    freeze=read('sources/REGISTRY_FREEZE_RECEIPT.json')
    checks['initial_candidate_frame_preserved'] = freeze['initial_registry_sha256']==sha(OWN/'sources/SOURCE_REGISTRY.json') and freeze['effective_registry_sha256']==sha(OWN/'sources/SOURCE_REGISTRY_EFFECTIVE.json')
    control_hashes={x['path']:x['sha256'] for x in read('control/INPUT_RECEIPT.json')['files']}
    for name in ('PLAN.md','control/SCOPE.json'):
        p=OWN.parent/name
        checks['unchanged_coordinator_'+name.replace('/','_')]=sha(p)==control_hashes[str(p.relative_to(transport.REPO))]
    policy_records=[]
    for r in policies:
        p=OWN/r['local_path']
        assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
        policy_records.append({**r,'valid_robots_text':r['source_id']!='stanford_daily','role':'compact source-policy preparation; not newspaper article/index evidence'})
    checks['six_policy_objects_match_receipts']=len(policy_records)==6
    with transport.HEAVY_LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        con=sqlite3.connect(f'file:{OWN}/staging/newspaper.sqlite3?mode=ro',uri=True)
        integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
        parents=con.execute('SELECT lane,count(*) FROM articles GROUP BY lane').fetchall()
        versions=con.execute('SELECT count(*) FROM versions').fetchone()[0]
        qualified=con.execute("SELECT count(DISTINCT a.article_id) FROM articles a JOIN versions v USING(article_id) WHERE a.lane='newspaper' AND a.newspaper_eligible=1 AND v.qualified_readable=1").fetchone()[0]
        cursors=[dict(zip([d[0] for d in con.execute('SELECT * FROM cursors').description],row)) for row in con.execute('SELECT * FROM cursors')]
        con.close()
    checks['own_staging_integrity_and_diagnostic_separation']=integrity=='ok' and dict(parents)=={'diagnostic':1} and versions==2 and qualified==0
    diagnostic_versions=read('manifests/VERSION_MANIFEST.json')['records']
    for v in diagnostic_versions:
        assert sha(v['body_path'])==v['body_sha256'] and sha(v['raw_path'])==v['raw_sha256']
    clean=read('diagnostics/ca1698af14973f0b5c0ba528_baeaba4d87d7_2e2f4b838bd2_2026-10-05T114609485639_0000_RECEIPT.json')
    checks['clean_repair_parser_and_staging_match_verified_pass'] = clean['executed_code_sha256']['parser.py']==sha(OWN/'prototype/parser.py') and clean['executed_code_sha256']['staging.py']==sha(OWN/'prototype/staging.py') and clean['first_write']['new_versions_inserted']==0 and clean['restart_duplicate_write']['new_versions_inserted']==0
    checks['old_frozen_raw_and_body_preserved'] = sha(clean['raw_path'])==clean['raw_sha256_before_after'] and sha(transport.REPO/'work_packages/M1_source_access/22_real_payload_acquisition_20261005/media/bodies/ca1698af14973f0b5c0ba528.txt')==clean['old_body_sha256_before_after']
    assert all(checks.values()), checks
    save('manifests/POLICY_AND_DIAGNOSTIC_MANIFEST.json',{'recorded_at_utc':at,'policy_objects':policy_records,'diagnostic_versions':diagnostic_versions,'frozen_external_raw_copied':False,'historical_companion_hash_limit':'The initial 11:04/11:06 receipts recorded parser and, in the second pass, adapter digests; companion helper/staging digests were not captured then. The 11:46 receipt records its exact executed code and does not retroactively fill those missing fields.','source_tool_locators':'sources/TOOL_RESPONSE_LOCATORS_V3.json'})
    save('manifests/VERSION_REVIEW.json',{'recorded_at_utc':at,'article_lane':'diagnostic; newspaper eligibility false','reviews':[{'version_id':v['version_id'],'body_sha256':v['body_sha256'],'qualified_readable':False,'newspaper_coverage_contribution':0,'assessment':'First inline-token repair retained newsletter/advertisement widgets; preserved as superseded diagnostic.' if i==0 else 'Inline token and seven narrative paragraph boundaries checked on named frozen HTML; aside/below-content widgets removed. No newspaper identity or historical body equivalence established.'} for i,v in enumerate(diagnostic_versions)]})
    snapshot={'checked_at_utc':at,'database':'staging/newspaper.sqlite3','read_mode':'read-only under shared heavy-I/O lock','integrity_check':integrity,'articles_by_lane':dict(parents),'version_count':versions,'qualified_newspaper_parents':qualified,'cursors':cursors,'no_formal_government_database_access':True}
    save('staging/CLOSING_CHECKPOINT.json',snapshot)
    storage=transport.preflight()
    save('control/FINAL_STORAGE_CHECK.json',storage)
    unused=[{'source_id':s['title_id'],'stratum':s['stratum'],'metadata_remaining':32-allowances[s['title_id']]['metadata'],'search_responses_remaining':3-allowances[s['title_id']]['search'],'access_state':s['access_state'],'stable_api_verified':False,'real_article_adapter_validated':False} for s in sources]
    cursor={'closed_at_utc':at,'released_at_utc':scope['released_at_utc'],'hard_network_deadline_utc':scope['network_deadline_utc'],'deadline_reached_at_close':dt.datetime.now(dt.timezone.utc)>=transport.DEADLINE,'tranche_state':'bounded preparation complete; newspaper acquisition blocked and unstarted','specific_stop':'actual original-reserve-aware storage preflight failed; complete source-specific production gates and article adapters also remain unavailable','continuous_objective_complete':False,'automatic_followup':False,'publication_interval':scope['publication_interval'],'all_465_months_and_2325_coordinates_preserved':True,'qualified_newspaper_articles':0,'retained_newspaper_cells':0,'newspaper_body_or_index_downloads':0,'selected_article_frames':0,'failed_selected_article_targets':[],'failed_selection_semantics':'None selected. Recorded source/index tool failures are discovery observations, not failed frozen article targets. No silent refill or quota transfer.','unstarted_rollout':{'first_month':'1988-01','strata':scope['strata'],'all_coordinates_pending':2325,'next_target_native_id':None,'next_page_cursor':None},'continuation_conditions':['actual passing storage preflight using unchanged reserves and lifetime accounting','applicable primary route, retention and identity/date evidence','validated source-specific article boundary, OCR/continuation mapping where needed','new bounded coordinator release after this closed tranche; retain counts/stops and prior receipts'],'concrete_unused_paths':['The Tech current issue/HTML article route; old tech.mit.edu401 stop remains; PDF-era adapter separately unresolved','Press native issue-to-article HTML route; prior failed January1988 issue preserved; prohibited PDF image-server path remains unused','Trove documented anonymous experimentation route requires current official conditions and actual viability, not an assumed key or response','Beaver date-control enumeration and article OCR/parent mapping','Mancunion and Trinity primary publisher/archive links still need confirmation; search caps already used'],'source_allowances':unused,'request_ledger':'sources/DISCOVERY_REQUESTS.jsonl','policy_request_ledger':'sources/POLICY_REQUESTS.jsonl','storage_snapshot':'control/FINAL_STORAGE_CHECK.json'}
    save('control/CONTINUATION_CURSOR.json',cursor)
    budget={'snapshot_at_utc':storage['at_utc'],'accepted_prior_media_bytes':scope['accepted_media_prior_bytes'],'own_all_files_bytes_at_snapshot':storage['media_lifetime_bytes']-scope['accepted_media_prior_bytes'],'lifetime_total_at_snapshot':storage['media_lifetime_bytes'],'lifetime_ceiling_bytes':scope['media_lifetime_cap_bytes'],'remaining_lifetime_bytes_at_snapshot':scope['media_lifetime_cap_bytes']-storage['media_lifetime_bytes'],'prospective_default_raw_bytes':scope['default_object_cap_bytes'],'required_free_threshold_default_payload_bytes':scope['minimum_free_floor_bytes']+scope['original_remaining_reserve_bytes_snapshot']+transport.OVERHEAD+scope['default_object_cap_bytes'],'threshold_gap_bytes_at_snapshot':max(0,scope['minimum_free_floor_bytes']-storage['projected_free_after_all_reserves']),'visible_preparation_operations':147,'candidate_title_operations':146,'context_operations':1,'native_policy_operations':6,'public_search_responses':34,'counts_include_known_redirects':True,'unreported_web_internal_hops':'unknown, no physical request total claim','no_reserve_or_cap_relaxation':True,'snapshot_limit':'Own-file accounting is deliberately wider than corpus copies. Subsequent compact closing records also consume allowance; physical free space can change outside this owner. Any actual request repeats preflight.'}
    save('control/CLOSING_BUDGET.json',budget)
    save('control/PACKAGE_VERIFICATION.json',{'checked_at_utc':at,'checks':checks,'all_passed':all(checks.values()),'own_staging':snapshot,'metadata_only_regional_cells':sum(r['observation_state']=='metadata_only' for r in regional),'targeted_test_count':25,'test_receipt_sha256':sha(OWN/'tests/TEST_RECEIPT.json'),'effective_registry_sha256':sha(OWN/'sources/SOURCE_REGISTRY_EFFECTIVE.json'),'verifier_sha256':sha(__file__),'verification_scope':'One changed-tranche check of own ledgers, small staging, receipts, code and named frozen diagnostic. No full corpus/government/evaluator audit. Tests do not validate live source adapters or universal correctness.','network_during_verification':False})
    report=f'''# Newspaper tranche result

The bounded source-preparation and changed-code package is delivered; the continuous newspaper acquisition objective remains incomplete. No newspaper article or index was downloaded or retained. Every measured original-reserve-aware payload preflight failed. The fixed publication interval remains **1988-01-01 through 2026-09-21**, with partial September 2026. This closure is before the {scope['network_deadline_utc']} maximum network deadline, not a claim that the deadline elapsed or discovery was exhausted.

## Actual outputs and counts

| Item | Actual result |
|---|---:|
| Candidate newspaper titles | 20; four in each of five disjoint strata |
| Planned regional month coordinates | 2,325; 465 per stratum |
| Planned pooled months | 465 |
| Regional cells with compact dated metadata observations | 53 |
| Qualified retained newspaper parents, cells and pooled months | 0 / 0 / 0 |
| Local newspaper article/index network attempts and raw objects | 0 / 0 |
| Frozen discovered source-month article selections | 0 |
| Saved compact native policy responses | 6; Stanford response is error HTML, not valid robots |
| Visible discovery/policy operations | 147; 146 candidate-title operations plus one LOC context operation |
| Public-search responses | 34; no title exceeds three |
| Own diagnostic staging | One non-newspaper parent, two unqualified derivatives |
| Targeted tests | 25 passed; transport mocked and fixture databases temporary |

Underlying publication counts, eligible frame populations and inclusion probabilities remain unknown in every cell. Zero retained articles means zero acquired newspaper evidence; it does not mean newspapers or emotion were absent. No empty publication frame or regional structural inapplicability was established. The one-per-cell presence plan is neither sufficient density nor archive completeness. Student, community and regional candidates retain their distinct composition; this convenience frame is not nationally representative.

## Source readiness and remaining gaps

`SOURCE_ERA_AND_INTERFACE_REPORT.md` provides primary links, era discrepancies and separate rights, authentication and transport states. `sources/SOURCE_REGISTRY.json` preserves the initial candidate frame; the effective registry adds later evidence without substituting selected articles. The Press 1988 calendar, Canberra 1992 page metadata and The Tech 1988 issue/PDF link support investigating early periods. Alice 2007 issue links and The Tech 2007 article links support middle-period route preparation. Recent links do not validate historical OCR/body adapters or complete the endpoint frame.

The Tech's current publisher-linked domain responds independently of its legacy 401 host. Its September issue mixes publication dates before and after September 21, requiring article-level mapping. Press coverage evidence now reaches1995, but direct issue/article probes failed. Canberra's ACT 1994/NLA 1995 discrepancy and anonymous Trove API conditions remain unresolved. Beaver exposes date controls, not a verified article frame. Cyprus Mail's responsive year archive does not clear current retention restrictions. Deseret, Alice's declared actor, Varsity and accepted prior-source stops are preserved. None passed a complete live source-era → frozen article frame → retained full prose → qualified staging chain; no production source gate is shipped. Founding dates, holding catalogues, issue containers, search caches and advertised totals do not substitute for independent readable articles.

Provenance remains dimensional: direct media utterance, archival reproduction, indirect holding evidence, mixed work origins or unresolved mapping. Directness does not verify every claim. Current retrieved content is not presumed equal to its historical version. `sources/PROBE_OBSERVATIONS.json` records compact metadata only; tool-response locators are pointers, not locally retained historical bodies. Individual UTC timestamps and unreported internal web hops are unavailable for discovery calls; the ordered logical-operation ledger and six timestamped native policy receipts are retained without invented precision.

## Code and real saved-payload repair

`prototype/parser.py` fixes the evidenced inline-node word split while preserving actual whitespace and block structure. A declared source adapter and manual boundary review are required. `pipeline.py` freezes native/date-ordered article selection before bodies, preserves failure without refill, binds raw/body/parser/adapter hashes and stages only reviewed newspaper units. `transport.py` enforces storage, exact receipt/version recovery, host/rate/deadline/access stops and bounded streaming. `staging.py` separates parent identity from versions and commits request, version and cursor atomically. These are reusable safeguards, not universally validated newspaper or OCR adapters.

The only real saved object read for repair is the named frozen round22 Texas Tribune raw HTML. Its raw SHA256 is `354e710253c171fd9c6abb21fb6d17342a63bcc8358c83ce9dfe2d47961f88fb`; the frozen old body remains unchanged. The first 2104-byte derivative repaired the inline token but retained newsletter/advertisement widgets and is preserved. The second 1937-byte derivative excludes those widgets and keeps the seven narrative paragraphs; its SHA256 is `ddbefe27c252d15f8538dfdee802e6ad2d66abdef546efc2ecb56529963ddfb0`. Both remain unqualified diagnostics because newspaper identity and historical body equivalence were not established. Their coverage contribution is zero.

The 11:46 UTC dated receipt captures exact executed parser/helper/staging/transport digests and duplicate reruns inserting zero versions. Initial 11:04/11:06 receipts captured parser and, in the second pass, adapter digests; helper/staging companion digests were not captured then. The later check does not retroactively fill that gap. Current test receipts separately bind the final changed code. Tests cover inline boundaries, units/previews, native order, duplicate/rollback transactions, parent conflicts, cutoff, frozen frames, storage/truncation/cooldown and explicit same-target recovery. They do not demonstrate a live newspaper download or validate every source. Own staging integrity is `ok`; there is no government database access.

## Closing capacity and continuation

The actual closing snapshot at **{storage['at_utc']}** records free space **{storage['free_bytes']:,} bytes**. After the unchanged original reserve **3,335,940,580**, additional staging/WAL/recovery **50,331,648**, and default prospective raw **2,097,152**, projected free space is **{storage['projected_free_after_all_reserves']:,} bytes**, below the **16,106,127,360-byte** floor. The default required free threshold is **19,494,496,740 bytes**; the shortfall at this snapshot is **{budget['threshold_gap_bytes_at_snapshot']:,} bytes**. The payload preflight therefore **fails**. Lifetime usage at that snapshot is conservatively **{storage['media_lifetime_bytes']:,} bytes** including the accepted 25,819,723-byte prior tranche and all own files; the ceiling remains 134,217,728. Compact closing files consume a little additional allowance and every future request must measure again. No user data was deleted and no reserve, cap or floor was reduced.

`control/CONTINUATION_CURSOR.json` preserves all 2,325 pending coordinates, source request allowances and access stops. There is no selected article to retry or silently replace. `ROLLOUT_PLAN.md` gives conditional era routes and concrete unused paths: The Tech current HTML versus early PDF adapters, permitted Press HTML, current documented Trove anonymous conditions, Beaver date controls, and confirmed primary Mancunion/Trinity routes. Rights-stopped titles remain stopped. A later bounded coordinator release and an actual passing preflight are necessary to resume acquisition after this closed tranche; no automatic follow-up or new window is created. Request and lifetime budgets may require multiple bounded tranches, and attainable population/density remains unknown.

All new files are inside `newspaper/`. Previous packages, proposal, root controls and the shared project log were read only where required and were not edited. Git, formal government databases and sealed evaluator material were not accessed; government acquisition did not run. No social-post collection or corpus-wide semantic/climate/emotion/fear labelling ran. Coordinator owns acceptance and integration. `control/PACKAGE_VERIFICATION.json`, `staging/CLOSING_CHECKPOINT.json`, `manifests/`, `tests/TEST_RECEIPT.json` and `DELIVERY_INDEX.json` make this partial result reviewable.
'''
    (OWN/'FINAL_REPORT.md').write_text(report)
    log=f'''# Newspaper owner execution log

All times are UTC; individual browser/search operation times were not captured and are not reconstructed. Ordered operations remain in the discovery ledger.

- 10:42:38.680119: bounded release; fixed endpoint, disjoint calendar, ownership and resource controls received.
- 10:46:06.976848: initial actual storage check failed; article/index collection did not start.
- 11:03:00–11:03:10: five bounded native robots responses saved; Stanford returned error HTML. Actual declared-agent Alice restriction preserved.
- 11:04 and11:06: named frozen Texas Tribune HTML repaired into two new diagnostic derivatives; first retained widgets and second removed them. Prior raw/body untouched, newspaper qualification zero.
- 11:04:01,11:17:18,11:34:18: further actual storage checks failed, original reserves unchanged.
- 11:46:09.485639–11:46:09.557437: dated real-payload verification recorded exact executed code; duplicate/reopen inserts zero; one diagnostic parent, two versions, zero newspapers.
- 11:49:19.573285–11:49:20.991639: sixth native policy response, The Tech current domain. Legacy host 401 kept separate; API/search disallow preserved.
- 12:10:21.114857–12:10:29.374835: final changed-code suite passed 25 targeted tests with mocked transport.
- {at}: one changed-tranche package check: own small staging integrity, fixed 465/2,325 ledgers, 53 metadata-only cells, receipt/code hashes, six policy objects and named old raw/body preservation passed. No live newspaper payload requests.
- {storage['at_utc']}: closing original-reserve-aware actual storage preflight failed. Package closed with unstarted newspaper cursor before hard deadline; continuous acquisition goal incomplete. No automatic continuation, shared log/Git edits or additional agents/windows.
'''
    (OWN/'LOG.md').write_text(log)
    records=[{'path':str(p.relative_to(OWN)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OWN.rglob('*')) if p.is_file() and p.name!='DELIVERY_INDEX.json']
    save('DELIVERY_INDEX.json',{'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'all files in own newspaper package only; index excludes itself','records':records,'indexed_file_count':len(records),'indexed_bytes':sum(r['bytes'] for r in records),'accepted_prior_media_bytes':scope['accepted_media_prior_bytes'],'newspaper_corpus_articles':0,'diagnostic_parent_count':1,'diagnostic_versions':2,'continuous_acquisition_complete':False})
    print(json.dumps({'all_verification_checks_passed':True,'checks':len(checks),'metadata_cells':53,'articles':0,'storage':storage,'indexed_files':len(records),'report':str(OWN/'FINAL_REPORT.md')},indent=2))

if __name__=='__main__':
    main()
