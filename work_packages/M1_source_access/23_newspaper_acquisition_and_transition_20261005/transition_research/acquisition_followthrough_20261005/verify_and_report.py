"""One bounded successor receipt/staging reconciliation, not a corpus audit."""
import collections
import csv
import datetime as dt
import hashlib
import json
import pathlib
import sqlite3
import collect_first_batch as resources

ROOT=resources.ROOT
receipts=[json.loads(s) for s in (ROOT/'REQUESTS.jsonl').read_text().split('\n') if s]
records=[json.loads(s) for s in (ROOT/'PUBLICATION_UNITS.jsonl').read_text().split('\n') if s]
issues=json.loads((ROOT/'ISSUE_CONTAINER_MANIFEST.json').read_text())
checks=[]
cache_path=ROOT/'VERIFIED_FILE_RECEIPTS.json'
old_cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
new_cache={};hash_reads=0;cached_checks=0
def agrees(path,sha256,expected_bytes=None):
    global hash_reads,cached_checks
    file=ROOT/path;stat=file.stat()
    fingerprint=dict(sha256=sha256,bytes=stat.st_size,mtime_ns=stat.st_mtime_ns)
    if expected_bytes is not None and expected_bytes!=stat.st_size:return False
    if old_cache.get(path)==fingerprint:
        cached_checks+=1;passed=True
    else:
        hash_reads+=1;passed=hashlib.sha256(file.read_bytes()).hexdigest()==sha256
    if passed:new_cache[path]=fingerprint
    return passed
def check(name,passed,detail):
    checks.append(dict(check=name,passed=bool(passed),detail=detail))
for row in receipts:
    if row.get('raw_path'):
        check('retained raw agrees with receipt '+row['request_id'],agrees(row['raw_path'],row['raw_sha256'],row['raw_bytes']),row['status'])
for row in records:
    if row.get('body_path'):
        check('retained body agrees with derived receipt '+row['url'],agrees(row['body_path'],row['body_sha256']),(ROOT/row['body_path']).stat().st_size)
    if row.get('publication_date'):
        check('fixed publication interval '+row['url'],'1988-01-01'<=row['publication_date']<='2026-09-21',row['publication_date'])
check('unique retained native publication identities',len(records)==len({r['url'] for r in records}),len(records))
con=sqlite3.connect(ROOT/'newspaper_followthrough.sqlite3')
parents=con.execute('SELECT COUNT(*) FROM pages').fetchone()[0]
versions=con.execute('SELECT COUNT(*) FROM versions').fetchone()[0]
check('local staging integrity',con.execute('PRAGMA integrity_check').fetchone()[0]=='ok',parents)
check('staged publication-parent total agrees with own manifest',parents==len(records),dict(staged=parents,manifest=len(records)))
check('versions cover retained parents',versions>=parents,versions)
check('whole-issue containers are separately staged',con.execute('SELECT COUNT(*) FROM issue_containers').fetchone()[0]==len(issues),len(issues))
con.close()
months=list(csv.DictReader((ROOT/'NEWSPAPER_MONTH_LEDGER.csv').open()))
for stratum in ['EU/Europe excluding UK','UK','AU','US','NZ','pooled']:
    selected=[r for r in months if r['stratum']==stratum]
    check('fixed 465-month ledger '+stratum,len(selected)==465 and selected[0]['month']=='1988-01' and selected[-1]['month']=='2026-09',len(selected))
check('no semantic acquisition labels',all(not r.get('semantic_labels_executed') and not r.get('length_filter_used') for r in records),'No climate, affect or fear gates')
source_requests=collections.Counter(r.get('source_id','mit_tech') for r in receipts)
staged=json.loads((ROOT/'STAGING_RESULT.json').read_text())
budget=resources.preflight()
stamp=dt.datetime.now(dt.timezone.utc).isoformat()
validation=dict(at_utc=stamp,scope='Only this retained successor tranche; no government or hidden reviewer code accessed',new_or_changed_file_hash_reads=hash_reads,reused_immutable_file_receipts=cached_checks,checks=checks,passed=all(c['passed'] for c in checks),
    replay=json.loads((ROOT/'RUN_RESULT_replay_fifth.json').read_text()) if (ROOT/'RUN_RESULT_replay_fifth.json').exists() else 'not yet recorded',
    staging_idempotence=json.loads((ROOT/'STAGING_IDEMPOTENCE.json').read_text()) if (ROOT/'STAGING_IDEMPOTENCE.json').exists() else 'not yet recorded')
(ROOT/'ACQUISITION_VERIFICATION.json').write_text(json.dumps(validation,indent=2)+'\n')
cache_path.write_text(json.dumps(new_cache,indent=2)+'\n')
cursor=dict(at_utc=stamp,last_completed_batches=[p.stem for p in sorted(ROOT.glob('RUN_RESULT*.json')) if 'bounded_batch_downloaded' in json.loads(p.read_text()).get('stop','')],
    actual_staging=staged,live_budget=budget,next_round_id=max([int(p.name[5:7]) for p in ROOT.glob('ROUND??_SCOPE.json')],default=2)+1,
    next_action='Use plan_next_round.py with a fresh round id, execute its frozen native plan, then stage once; continue within measured capacity',
    genuine_access_stops=[dict(url=r['url'],http_status=r.get('http_status'),status=r['status']) for r in receipts if r.get('http_status') in {401,403,429}],
    failed_targets_preserved_no_retry=[dict(url=r['url'],status=r['status']) for r in receipts if r['status']=='transport_error'],
    publication_interval=['1988-01-01','2026-09-21'],no_full_archive_or_national_representativeness_claim=True)
(ROOT/'CONTINUATION_CURSOR.json').write_text(json.dumps(cursor,indent=2)+'\n')
saved_us=sum(r['purpose']=='article' and r['status']=='saved' for r in receipts)
saved_au=sum(r['purpose']=='au_article' and r['status']=='saved' for r in receipts)
physical=budget['free_bytes']/1024**3;lifetime=budget['media_lifetime_used_bytes']/1024**2
lines=['# Actual newspaper acquisition successor',f'\nSnapshot: {stamp}. Publication interval: 1988-01-01 through 2026-09-21; September is partial.',
    '\nDai explicitly authorized immediate actual collection and consecutive rounds with live capacity. The inherited combined reserve was canceled for this successor. The frozen predecessor recorded zero new newspaper article payloads; its static-reserve stop and unfinished universal-adapter gate remain historical receipts, not current progression gates.',
    f'\nSaved raw responses now include {saved_us} US The Tech native article pages and {saved_au} AU InDaily newspaper-brand digital pages. The Tech is a student-press supplement, not a national newspaper sample; InDaily is a newspaper-brand digital successor with the print/digital break retained.',
    f'\nLocal staging contains {parents} publication parents and {versions} content versions: {staged["readable_publication_units"]} readable units and {staged["retained_pending_units"]} pending unit(s). URL identities do not establish independent original stories. The Corrections and Activities Midway pages have no derived prose and remain retained and annotated. Table, quoted-work and syndication relations remain visible.',
    f'\nSeparately retained: {len(issues)} complete original-issue PDF containers ({sum(i["pdf_pages"] for i in issues)} scanned pages), including printed February 1988, 1989, 1990 and 1991 issues. One 1988 cross-page article has an explicit seven-segment parent mapping. Whole issues and remaining PDF articles are not added to the article-parent count; segmentation/OCR work does not delay further acquisition.',
    '\n| Stratum | Readable saved publication units | Months with dated source presence | Calendar denominator |\n|---|---:|---:|---:|']
for stratum in ['EU/Europe excluding UK','UK','AU','US','NZ','pooled']:
    readable=staged['readable_publication_units'] if stratum=='pooled' else staged['readable_by_stratum'][stratum]
    lines.append(f'| {stratum} | {readable} | {staged["dated_presence_months_by_stratum"][stratum]} | 465 |')
lines.extend(['\nPresence is a lower bound in the acquired source frame. Missing months mean not acquired/unknown here, not zero publication, discourse or emotion. Pooled presence does not certify any stratum or complete archives. No climate/affect/fear labeling or semantic exclusion was executed.',
    '\nResource control is measured before every request: live disk free space, cumulative retained media bytes, a 15 GiB physical floor and 48 MiB staging/recovery allowance. Per-object caps and planned index counts adapt to current capacity. No static 3,335,940,580-byte inherited reserve remains in the successor. The original 128 MiB cumulative media budget is a separate limit, not a claim that physical disk is full.',
    f'\nLatest actual disk free: {physical:.3f} GiB. Cumulative media allocation used: {lifetime:.3f} MiB / 128 MiB, including the prior 25,819,723 bytes, old newspaper package and all successor files. Values are snapshots; the next request recalculates them.',
    '\nThe NZ The Press public calendar actually returned HTTP403; the receipt is preserved and that route is stopped. One US weather-page transport failure is preserved without retry/refill, while the remaining original targets continued. Successful routes are not held waiting for another source or a universal adapter.',
    '\nSuccessful successive batches, unchanged selected native order, raw SHA-256 receipts, local staging transactions and the continuation cursor are retained in this package. The shared heavy-I/O mutex is never unlinked. Only the local successor staging database is written. Government inputs, predecessor reports, shared logs, social streams and sealed independent-audit code remain outside this write scope.',
    '\nContinue in the same chat using CONTINUATION_INSTRUCTIONS.md and plan_next_round.py; freeze each bounded successor plan, execute real downloads, then extract the changed tranche and reconcile the local ledger. Distinguish source access stops, physical-floor limits and lifetime-budget limits using exact measured receipts.',
    f'\nChanged-tranche verification: {sum(c["passed"] for c in checks)}/{len(checks)} checks passed. Idempotent local extraction and a cached-download replay are separately recorded; this is not a repeated full-corpus audit.'])
approval_path=ROOT/'AUTOMATION_APPROVAL_STATE.json'
if approval_path.exists():
    approval=json.loads(approval_path.read_text())
    lines.append('\nRecurring continuation state: '+approval['status']+'. '+approval.get('reason',''))
(ROOT/'ACQUISITION_STATUS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(passed=validation['passed'],checks=len(checks),parents=parents,versions=versions,saved_us_html=saved_us,saved_au_html=saved_au,whole_issue_pdfs=len(issues),staged=staged,live_budget=budget)))
