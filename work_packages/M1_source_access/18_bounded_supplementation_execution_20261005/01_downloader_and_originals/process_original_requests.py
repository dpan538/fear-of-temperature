"""Exactly five original requests. Bounded A staging, no database writes/extraction."""
import argparse,csv,hashlib,importlib.util,json,re
from datetime import datetime
from pathlib import Path
from urllib.parse import urldefrag,urljoin,urlsplit
from bs4 import BeautifulSoup
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
CODE=ROOT/'work_packages/M1_source_access/15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation/stage_frozen_items.py'
spec=importlib.util.spec_from_file_location('downloader',CODE);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
SOURCE=d.REPAIR/'missing_original_requests.csv'
CONTRACT=d.load_json(d.CONTRACT)
PRIMARY={
'doc:7c7006b4ea3168ebe548e229915d853b':'https://www.dcceew.gov.au/sites/default/files/documents/interim-report-fugitive-methane-expert-panel.pdf',
'doc:bc6340389c3977a04993b0a20f55bcca':'https://www.dcceew.gov.au/sites/default/files/documents/australias-sustainable-ocean-plan.pdf'}

def source_rows():
    d.require(d.hash_file(SOURCE)==d.A_SHA,'Final A source manifest changed')
    rows=list(csv.DictReader(SOURCE.open()));d.require(len(rows)==5 and {r['unit_id'] for r in rows}==d.A_IDS,'Wrong A identities');return rows

def local_checks(rows):
    checks=[]
    old=d.WP/'09_us_au_government_acquisition'
    attachments=old/'reports/au_attachment_candidates.csv'
    for row in rows:
        item={'unit_id':row['unit_id'],'canonical_url':row['canonical_url'],'saved_original_reuse':False,'checked_at_utc':d.now(),'named_paths':[]}
        if row['unit_id'].startswith('doc_'):
            section=row['canonical_url'].split('/')[7] if False else urlsplit(row['canonical_url']).path.split('/')[4]
            year=row['source_date'][:4]
            detail=d.WP/f'07_historical_government_acquisition/raw/hansard_api/details/{year}/{section}.json'
            cp=detail.with_suffix('.json.fetch.json')
            search=d.ROOT/row['existing_evidence'].split(';')[0]
            for p in [detail,cp,search]:
                info={'path':str(p.relative_to(d.ROOT)),'exists':p.is_file()}
                if p.is_file():info.update(bytes=p.stat().st_size,sha256=d.hash_file(p))
                if p==cp and p.is_file():info['historical_fetch']=d.load_json(p)
                item['named_paths'].append(info)
            item['reuse_reason']='Search text is not the requested section original; exact historical section raw absent and HTTP400 sidecar retained. Canonical HTML is the bounded alternate.'
        else:
            item['prior_primary_link_evidence']={'path':str(attachments.relative_to(d.ROOT)),'sha256':d.hash_file(attachments),'matched_rows':[r for r in csv.DictReader(attachments.open()) if r['landing_url']==row['canonical_url']]}
            for url in [row['canonical_url'],PRIMARY[row['unit_id']]]:
                pdf=url.endswith('.pdf');key=':'+hashlib.sha256(url.encode()).hexdigest()[:32]
                p=old/'raw'/('au_files' if pdf else 'au_landing')/(key+('.pdf' if pdf else '.html'))
                cp=p.with_suffix(p.suffix+'.request.json');info={'path':str(p.relative_to(d.ROOT)),'request_url':url,'exists':p.is_file(),'checkpoint_exists':cp.exists()}
                if p.is_file() or cp.exists():
                    try:
                        verify_row={'request_url':url,'max_object_bytes':100_000_000 if pdf else 20_000_000}
                        verified=d.verified_reuse(verify_row,p,cp,'pdf' if pdf else 'html');info['verified_reuse']=verified;item['saved_original_reuse']=True
                    except Exception as exc:info['reuse_conflict']=str(exc)
                item['named_paths'].append(info)
            item['reuse_reason']='Exact URL-derived landing and primary-file paths checked; catalogue or prior web observations alone are not saved original bytes.'
        checks.append(item)
    return {'checked_at_utc':d.now(),'source_manifest_sha256':d.A_SHA,'checks':checks,'scope':'Named exact paths only; no corpus scan or database query','network_requests':0}


def html_evidence(row,path):
    soup=BeautifulSoup(path.read_bytes(),'html.parser')
    main=soup.find('main') or soup.find('article') or soup.find(id='main-content')
    view=main or soup
    h1=[n.get_text(' ',strip=True) for n in view.find_all('h1')]
    text=view.get_text(' ',strip=True)
    evidence={'saved_path':str(path.relative_to(d.ROOT)),'sha256':d.hash_file(path),'page_title':soup.title.get_text(' ',strip=True) if soup.title else '', 'h1_titles':h1,'main_tag':main.name if main else None,'host':urlsplit(row['canonical_url']).hostname,'retrieval_is_not_historical_content_version':True}
    if row['unit_id'].startswith('doc_'):
        section=urlsplit(row['canonical_url']).path.split('/')[4];anchor=urlsplit(row['canonical_url']).fragment
        node=soup.find(id=anchor) or soup.find(attrs={'data-id':anchor})
        date=datetime.strptime(row['source_date'],'%Y-%m-%d');date_words=[date.strftime('%d %B %Y').lstrip('0'),date.strftime('%A %d %B %Y').replace(' 0',' '),row['source_date']]
        container=node
        if node:
            for parent in [node,*list(node.parents)[:5]]:
                if any('contribution' in str(c).lower() for c in parent.get('class',[])):
                    container=parent;break
        evidence.update(section_ext_id=section,contribution_anchor=anchor,anchor_found=node is not None,
                        source_date=row['source_date'],visible_date_strings=[s for s in date_words if s in text],time_elements=[n.get('datetime') or n.get_text(' ',strip=True) for n in soup.find_all('time')],
                        anchor_tag=node.name if node else None,anchor_attributes=dict(node.attrs) if node else {},
                        contribution_container_tag=container.name if container else None,contribution_container_attributes=dict(container.attrs) if container else {},
                        contribution_paragraph_nodes=len(container.find_all('p')) if container else 0,
                        boundary_status='candidate contribution container found; full section segmentation requires later validator' if node else 'requested contribution anchor unresolved',
                        issuer='UK Parliament',directness='Official historical Hansard reproduction of the recorded parliamentary utterance; speaker attribution pending')
    else:
        labelled=[]
        for match in re.finditer(r'(?:Published|Publication date|Date published)\s*:?\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[A-Za-z]+\s+[0-9]{4})',text,re.I):labelled.append(match.group(0))
        links=[]
        for a in view.find_all('a',href=True):
            url=urljoin(row['canonical_url'],a['href'])
            if url.startswith('https://www.dcceew.gov.au/sites/default/files/') and urlsplit(url).path.lower().endswith('.pdf'):
                links.append({'url':url,'label':a.get_text(' ',strip=True)})
        evidence.update(labelled_publication_date_candidates=labelled,primary_file_links=links,
                        primary_mapping_status='Exact previously documented titled PDF link present' if any(p['url']==PRIMARY[row['unit_id']] for p in links) else 'Exact primary link not confirmed',
                        issuer_host='Australian Government DCCEEW website',author_or_original_issuer='pending title/imprint review',date_precision='unknown',cms_created_at_used_as_publication_date=False,
                        boundary_status='Landing main/article title and explicit file mapping only; attachment identity pending')
    return evidence


def object_row(row,url,kind):
    return {'unit_id':row['unit_id'],'request_url':url,'staging_path':'raw/'+hashlib.sha256(url.encode()).hexdigest()+('.pdf' if kind=='pdf' else '.html'),'max_object_bytes':100_000_000 if kind=='pdf' else 20_000_000}


def process(row,local,stop_reason):
    evidence={'unit_id':row['unit_id'],'source_id':row['source_id'],'canonical_url':row['canonical_url'],'requested_original':row['requested_original'],'source_manifest_sha256':d.A_SHA,'local_reuse_check':local,'attempts':[],'terminal_at_utc':'','fixed_publication_interval':d.INTERVAL,'date_precision':'unknown','publication_date':None,'remaining_checks':[]}
    if stop_reason:
        evidence.update(terminal_status='stopped_safety_or_access',stop_reason=stop_reason,remaining_checks=['Official route not attempted after persistent access/safety stop; availability and identity remain untested.'])
    else:
        url=urldefrag(row['canonical_url'])[0];saved=None
        for info in local['named_paths']:
            if info.get('request_url')==url and info.get('verified_reuse'):
                saved=d.ROOT/info['path'];evidence['verified_reuse']=info['verified_reuse'];break
        try:
            result=None
            if not saved:
                result=d.stream_one(object_row(row,url,'html'),CONTRACT,OUT,'html',{'hansard.parliament.uk','www.dcceew.gov.au','dcceew.gov.au'})
                evidence['attempts'].append(result)
                if result['status']=='downloaded_candidate_original':saved=d.ROOT/result['raw_path']
            if saved:
                evidence['html']=html_evidence(row,saved)
                if row['unit_id'].startswith('doc_'):
                    evidence.update(terminal_status='verified_local_reuse' if not result else 'original_obtained_validation_pending',date_precision='day',publication_date=row['source_date'],date_basis='Existing exact request date plus official URL; visible-page date and identity checked separately in html evidence',remaining_checks=['Validate contribution/section boundary, holder and full original-body mapping before integration.','Current retrieval does not establish unchanged historical wording.'])
                else:
                    primary=PRIMARY[row['unit_id']]
                    mapped=any(p['url']==primary for p in evidence['html']['primary_file_links'])
                    if mapped:
                        reused=next((i.get('verified_reuse') for i in local['named_paths'] if i.get('request_url')==primary and i.get('verified_reuse')),None)
                        if reused:evidence['primary_file_reuse']=reused
                        else:
                            pdf=d.stream_one(object_row(row,primary,'pdf'),CONTRACT,OUT,'pdf',{'www.dcceew.gov.au','dcceew.gov.au'})
                            evidence['attempts'].append(pdf)
                    evidence.update(terminal_status='date_unresolved',remaining_checks=['Inspect title/imprint and author/issuer of the primary file; no PDF text extraction performed.','No verified day-level original publication date: CMS creation date is not publication evidence; September 2026 may straddle the fixed cutoff.'])
                    if d.STATE.exists() and d.load_json(d.STATE).get('halted'):evidence['access_or_safety_limit']=d.load_json(d.STATE)
            else:
                status=(result or {}).get('http_status',0)
                evidence.update(terminal_status='access_restricted' if status in {401,403,429} else ('bounded_unavailable' if status in {404,410} else 'stopped_safety_or_access'),remaining_checks=['No readable original obtained from this bounded route; historical saved search/catalogue evidence retained.'])
        except Exception as exc:
            evidence.update(terminal_status='stopped_safety_or_access',stop_reason=type(exc).__name__+': '+str(exc),remaining_checks=['Route stopped; no automatic resumption or substitute source.'])
    evidence['terminal_at_utc']=d.now()
    path=OUT/'evidence'/(hashlib.sha256(row['unit_id'].encode()).hexdigest()+'.json');d.save_json(path,evidence)
    state=d.load_json(d.STATE) if d.STATE.exists() else {}
    next_stop=state.get('stop_reason') if state.get('halted') else evidence.get('stop_reason')
    return evidence,path,next_stop


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    rows=source_rows()
    with d.locks(download=True):
        if not (OUT/'A_LOCAL_REUSE_CHECKS.json').exists():d.save_json(OUT/'A_LOCAL_REUSE_CHECKS.json',local_checks(rows))
        if not args.execute:print('Named local reuse checks saved; no HTTP');return
        d.require(not (OUT/'A_DISPOSITIONS.csv').exists(),'A terminal ledger already exists; no automatic resumption')
        ready=d.load_json(OUT/'DOWNLOADER_READY.json');d.require(ready['status']=='ready' and ready['downloader_sha256']==d.code_hash(),'Readiness missing/mismatched')
        ok,reason,release=d.release_check(CONTRACT,ready['repair_release_sha256'],locked=True);d.require(ok,reason)
        d.budget_check(CONTRACT,reserve_remaining=True)
        checks={r['unit_id']:r for r in d.load_json(OUT/'A_LOCAL_REUSE_CHECKS.json')['checks']}
        results=[];stop_reason=None
        for row in rows:
            evidence,path,stop_reason=process(row,checks[row['unit_id']],stop_reason)
            results.append((row,evidence,path))
            print(json.dumps({'unit_id':row['unit_id'],'terminal_status':evidence['terminal_status'],'attempts':len(evidence['attempts'])}),flush=True)
        ledger=OUT/'A_DISPOSITIONS.csv'
        fields=['unit_id','source_id','source_request_url','source_manifest_sha256','terminal_status','attempted_routes','attempt_times_utc','http_statuses','saved_paths','sha256s','saved_bytes','publication_date','date_precision','identity_body_evidence','remaining_checks','evidence_path','evidence_sha256']
        with ledger.open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
            for row,evidence,path in results:
                attempts=evidence['attempts'];files=[r for r in attempts if r.get('raw_path') or r.get('partial_path')]
                writer.writerow({'unit_id':row['unit_id'],'source_id':row['source_id'],'source_request_url':row['canonical_url'],'source_manifest_sha256':d.A_SHA,'terminal_status':evidence['terminal_status'],'attempted_routes':json.dumps([r['request_url'] for r in attempts]),'attempt_times_utc':json.dumps([r['requested_at_utc'] for r in attempts]),'http_statuses':json.dumps([r.get('http_status',0) for r in attempts]),'saved_paths':json.dumps([r.get('raw_path') or r.get('partial_path') for r in files]),'sha256s':json.dumps([r.get('sha256') or r.get('partial_sha256') for r in files]),'saved_bytes':sum(r['byte_count'] for r in files),'publication_date':evidence['publication_date'],'date_precision':evidence['date_precision'],'identity_body_evidence':json.dumps(evidence.get('html',{}),ensure_ascii=False),'remaining_checks':json.dumps(evidence['remaining_checks'],ensure_ascii=False),'evidence_path':str(path.relative_to(d.ROOT)),'evidence_sha256':d.hash_file(path)})
        shared=d.raw_accounting();a_files=[{**f,'sha256':d.hash_file(d.ROOT/f['path'])} for f in shared['files'] if (d.ROOT/f['path']).is_relative_to(OUT/'raw')]
        accounting={'complete':True,'completed_at_utc':d.now(),'unit_ids':sorted(d.A_IDS),'terminal_outcomes':{r['unit_id']:e['terminal_status'] for r,e,p in results},'source_manifest_path':str(SOURCE.relative_to(d.ROOT)),'source_manifest_sha256':d.A_SHA,'ledger_sha256':d.hash_file(ledger),'A_raw_files':a_files,'A_raw_bytes':sum(f['bytes'] for f in a_files),'A_partial_bytes':sum(f['bytes'] for f in a_files if f['partial']),'shared_raw_accounting':shared,'remaining_shared_raw_budget_bytes':2*d.GIB-shared['total_bytes'],'budget':d.budget_check(CONTRACT),'http_state':d.load_json(d.STATE) if d.STATE.exists() else {},'downloader_sha256':d.code_hash(),'formal_database_writes':0,'extraction_started':False,'eu_HTTP_requests':0,'fixed_publication_interval':d.INTERVAL,'stop_reason':stop_reason}
        d.save_json(OUT/'A_ACCOUNTING.json',accounting)
        print(json.dumps({'complete':True,'five_terminal_dispositions':len(results),'A_raw_bytes':accounting['A_raw_bytes'],'stop_reason':stop_reason}),flush=True)

if __name__=='__main__':main()
