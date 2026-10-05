#!/usr/bin/env python3
"""Bounded local repair layer. No network, collector edits, or legacy row updates.

Use the repository .venv/bin/python. --dry-run freezes a checked local plan;
--apply commits it; --verify checks only that tranche; --rollback deactivates it.
The effective views are the supported consumer interface, documented in REPORT.
"""
from __future__ import annotations
import argparse
import contextlib
import csv
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import duckdb
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT / 'work_packages/M1_source_access'
STAGE = BASE / '15_targeted_repairs_and_supplementation_20261004'
VALID = BASE / '14_structural_validation_20261004'
DB = BASE / '06_government_content_acquisition/fear_temperature_government_content.duckdb'
USDB = BASE / '09_us_au_government_acquisition/fear_temperature_us_au_v1.duckdb'
EUDB = BASE / '10_eu_cellar_acquisition/eu_stage.duckdb'
RULE = 'targeted_structural_repair_v1_20261004'
RUN = 'repair_20261004_task3_v1'
sys.path.insert(0, str(VALID / '01_archive_split'))
import validate_archive_splits as diagnostic

def now(): return datetime.now(timezone.utc).isoformat()
def dump(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, default=str, separators=(',', ':'))
def digest(x): return hashlib.sha256(x if isinstance(x, bytes) else str(x).encode()).hexdigest()
def sid(prefix, *parts): return prefix + '_' + digest('\x1f'.join(map(str, parts)))[:20]
def clean(x): return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(x or ''))).strip()
def csvread(p):
    with Path(p).open(newline='', encoding='utf-8') as f: return list(csv.DictReader(f))
def csvwrite(p, rows, fields):
    with Path(p).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def atomic(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.task3.tmp')
    with tmp.open('w') as f: json.dump(value, f, ensure_ascii=False, indent=2, default=str); f.write('\n'); f.flush(); os.fsync(f.fileno())
    tmp.replace(p)
def stamp(p, hashed=False):
    p = Path(p).resolve(); s = p.stat()
    v = {'path':str(p.relative_to(ROOT)), 'bytes':s.st_size, 'mtime_ns':s.st_mtime_ns}
    if hashed: v['sha256'] = digest(p.read_bytes())
    return v
def rows(con, sql, args=None):
    cur = con.execute(sql, args or []); fields = [x[0] for x in cur.description]
    return [dict(zip(fields, r)) for r in cur.fetchall()]
@contextlib.contextmanager
def locks(writer=False):
    hs = []
    try:
        paths = [VALID / 'control/heavy_io.lock']
        if writer: paths.append(STAGE / 'control/formal_database_writer.lock')
        for p in paths:
            if p.name=='heavy_io.lock' and not p.exists(): raise RuntimeError('Missing shared heavy-I/O lock')
            h = p.open('a+'); fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB); hs.append(h)
        yield
    finally:
        for h in reversed(hs): fcntl.flock(h, fcntl.LOCK_UN); h.close()

def body_html(value):
    soup = BeautifulSoup(str(value or ''), 'html.parser')
    # Source furniture is independently addressable markup, not utterance text.
    for x in soup.select('.column-number, script, style'): x.decompose()
    return clean(soup.get_text(' ', strip=True))
def question(text):
    return bool(re.match(r'^(?:\d+\.\s*)?(?:\[[^]]+\]\s*)?(?:To ask\b|asked Her Majesty[’\x27]s Government\b)', clean(text), re.I))
def single_saved_day(g):
    """Exact typed source date, corroborated by a non-range day/weekday heading.

    A received-between heading is never exact, regardless of its format value.
    Truncated/missing year strings remain recorded, not silently corrected.
    """
    head=g.get('date_heading','')
    if 'between ' in head.lower():return '', 'range_only'
    attr=g.get('date_attribute','')
    try:d=datetime.strptime(attr,'%Y-%m-%d')
    except (ValueError,TypeError):return '', 'invalid_saved_format_date'
    m=re.fullmatch(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:,?\s+(\d{1,4}))?[.>\s]*',head,re.I)
    if not m:return '', 'non_single_heading'
    wd,day,month,year=m.groups()
    if d.strftime('%A').lower()!=wd.lower() or d.day!=int(day) or d.strftime('%B').lower()!=month.lower():return '', 'format_heading_day_month_weekday_conflict'
    if year and len(year)==4 and int(year)!=d.year:return '', 'format_heading_year_conflict'
    return attr, 'exact_saved_format_corroborated_by_heading' + (';heading_year_truncated_or_absent' if not year or len(year)<4 else ';visible_full_year')
def node(key, role, text, speaker, order, loc, basis='explicit_saved_node'):
    return {'node_id':str(key), 'role':role, 'text':clean(text), 'speaker':clean(speaker), 'order':order, 'locator':loc, 'role_basis':basis}

def archive_nodes(path):
    obj = json.loads(path.read_text()); ov = obj.get('Overview') or {}; key = str(ov.get('ExtId') or '')
    if not key: raise ValueError('Saved detail has no Overview.ExtId')
    ns=[]; prior_question=False; qspeaker=''
    for i, item in enumerate(obj.get('Items') or []):
        if item.get('ItemType') != 'Contribution': continue
        tag = str(item.get('HRSTag') or '').lower(); soup=BeautifulSoup(str(item.get('Value') or ''),'html.parser')
        qtag = tag in ('question','err_question')
        qt = soup.find(lambda x: x.name and x.name.lower()=='questiontext') if qtag else None
        text = body_html(str(qt) if qt else item.get('Value'))
        if not text: continue
        ident=str(item.get('ExternalId') or item.get('ItemId') or '')
        if not ident: raise ValueError('Nonempty contribution without stable locator')
        isq=qtag or question(text)
        # Untagged numbered continuation only while the question is still open.
        if not isq and prior_question and re.match(r'^\(\d+\)\s+',text) and not item.get('AttributedTo'): isq=True
        speaker=clean(item.get('AttributedTo')); basis='HRSTag='+str(item.get('HRSTag'))
        if isq:
            if speaker: qspeaker=speaker
            elif qspeaker: speaker=qspeaker; basis+=';speaker_inherited_from_question'
        prior_question=isq
        ns.append(node(ident,'question' if isq else 'response',text,speaker,i, f'{path.relative_to(ROOT)}#Items[{i}];ExternalId_or_ItemId={ident}',basis))
    return {key:{'key':key,'date':str(ov.get('Date') or '')[:10],'title':clean(ov.get('Title')),'nodes':ns,'date_basis':'saved_Overview.Date'}}

def item_groups(path):
    soup=BeautifulSoup(path.read_bytes(),'html.parser'); title=clean(soup.h1.get_text(' ',strip=True)) if soup.h1 else ''
    cite=soup.select_one('cite.section'); date=''
    if cite:
        m=re.search(r'\b(\d{1,2} [A-Za-z]+ \d{4})\b',cite.get_text(' ',strip=True))
        if m: date=datetime.strptime(m[1],'%d %B %Y').date().isoformat()
    if not date: raise ValueError('No independently visible item citation date')
    groups={}; pending=[]; responded=False; seq=0
    def flush():
        nonlocal pending,responded
        replies=[n for n in pending if n['role']=='response']
        if replies:
            key=replies[0]['node_id'];groups[key]={'key':key,'date':date,'title':title,'nodes':pending,'date_basis':'visible_item_citation'}
        pending=[];responded=False
    # Use contribution containers rather than recursively concatenating p tags.
    for contribution in soup.select('div.member_contribution'):
        block=contribution.select_one('blockquote.contribution_text')
        if block is None: continue
        sp=block.select_one('cite.member'); speaker=clean(sp.get_text(' ',strip=True)) if sp else ''
        elems=[x for x in block.find_all(['p','table']) if x.name=='table' or x.find_parent('table') is None]
        if not elems: continue
        first=clean(elems[0].get_text(' ',strip=True)); isq=question(first)
        if isq and responded: flush()
        if not isq and not pending: raise ValueError('Reply without preceding addressable question')
        role='question' if isq else 'response'
        for ix,e in enumerate(elems):
            # The historic HTML contains tables nested inside invalid p markup.
            # Give every table its own locator and remove it from paragraph text.
            copy=BeautifulSoup(str(e),'html.parser')
            if e.name=='p':
                for t in copy.find_all('table'): t.decompose()
            text=clean(copy.get_text(' ',strip=True))
            if not text: continue
            ident=str(e.get('id') or f"{contribution.get('id')}:table:{ix}")
            seq+=1;pending.append(node(ident,role,text,speaker,seq,f'{path.relative_to(ROOT)}#contribution={contribution.get("id")};{e.name}[{ix}];id={ident}','contribution_question_boundary'))
        if not isq: responded=True
    flush();return groups

def xml_groups(path):
    original=diagnostic.parse_historic_zip(path); meta={}; raw_nodes={}; text_meta=defaultdict(list)
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.lower().endswith('.xml'):continue
            root=ET.fromstring(z.read(name))
            for ci,c in enumerate(root.iter('writtenanswers')):
                de=c.find('./date'); head=clean(' '.join(de.itertext())) if de is not None else ''
                attr=de.get('format','') if de is not None else ''
                for di,dept in enumerate(list(c)):
                    if dept.tag not in ('group','section'):continue
                    te=dept.find('./title'); label=clean(' '.join(te.itertext())).upper() if te is not None else ''
                    for si,section in enumerate(dept.findall('./section')):
                        for pi,p in enumerate(section.findall('.//p')):
                            ident=p.get('id','')
                            info={'department':label,'date_heading':head,'date_attribute':attr,'locator':f'{path.relative_to(ROOT)}#{name}/writtenanswers[{ci}]/group[{di}]/section[{si}]/p[{pi}];id={ident}'}
                            speaker,text=diagnostic.strip_xml_speaker(p)
                            text_meta[(clean(speaker),clean(text))].append(info)
                            if ident:
                                raw_nodes[ident]=p
                                meta[ident]=info
    out={}
    for k,g in original.groups.items():
        ns=[]
        for nk in g.question_keys+g.response_keys:
            n=original.get_node(nk,k); candidates=text_meta.get((clean(n.speaker),clean(n.text)),[])
            m=meta.get(nk,candidates[0] if len(candidates)==1 else {})
            ns.append(node(nk,n.role,n.text,n.speaker,n.order,m.get('locator',f'{path.relative_to(ROOT)}#{k};unkeyed={nk}'),'XML_member_question_boundary'))
        info=next((meta[n] for n in g.response_keys if n in meta),{})
        if not info:
            # Unkeyed groups retain the diagnostic exact-signature limitation.
            for n in ns:
                candidates=text_meta.get((clean(n['speaker']),clean(n['text'])),[])
                if len(candidates)==1:info=candidates[0];break
        out[k]={'key':k,'date':g.date,'title':g.title,'nodes':ns,**info,'date_basis':'XML_heading_and_format_attribute'}
    return out,original

def get_documents(con, ids):
    if not ids:return {}
    return {r['document_id']:r for r in rows(con,'SELECT * FROM documents WHERE document_id IN (SELECT unnest(?))',[sorted(ids)])}
def get_segments(con,ids):
    rs=rows(con,"""SELECT a.document_id,a.attribution_id,a.actor_name,a.evidence_locator,a.status attribution_status,s.*
      FROM voice_attributions a JOIN text_segments s USING(segment_id)
      WHERE a.document_id IN (SELECT unnest(?)) ORDER BY a.document_id,s.segment_order,s.segment_id""",[sorted(ids)])
    out=defaultdict(list)
    for r in rs:out[r['document_id']].append(r)
    return out
def parent_fingerprint(doc,segs): return digest(dump({'document':doc,'segments':segs}))
def equivalent(a,b):return clean(a).casefold()==clean(b).casefold()
def signature(ns):return tuple((n['role'],clean(n['text']).casefold()) for n in ns)
def chosen_group(doc,old,groups,diagnostic_row):
    ext=doc['external_id']
    if ext in groups:return groups[ext],'exact_external_id'
    expected=diagnostic_row.get('original_group_id','')
    if expected in groups:return groups[expected],'diagnostic_exact_text_mapping_rechecked'
    containing=[g for g in groups.values() if ext in [n['node_id'] for n in g['nodes']]]
    if len(containing)==1:return containing[0],'external_id_is_question_or_continuation;stable_parent_retained'
    old_sig=[]
    for s in old:
        role,_,_=diagnostic.locator_parts(s['locator']);old_sig.append(('question' if role=='question_context' else 'response',clean(s['segment_text']).casefold()))
    same=[g for g in groups.values() if signature(g['nodes'])==tuple(old_sig)]
    if len(same)==1:return same[0],'unique_full_text_signature;hashed_parent_id_not_reproduced'
    return None,'No unique saved group mapping'

def build_plan():
    if (HERE/'PLAN.json').exists():
        p=json.loads((HERE/'PLAN.json').read_text())
        print(dump({'status':'read_only_frozen_plan_summary','plan_sha256':digest((HERE/'PLAN.json').read_bytes()),'counts':{k:len(p[k]) for k in ['repairs','dates','states','new_parents','annotations','dispositions','requests']},'note':'Existing frozen plan preserved; this mode performs no database mutation or repeated source audit.'}))
        return
    triage=csvread(STAGE/'coordinator_triage.csv'); assert len(triage)==3080
    diagrows={r['document_id']:r for r in csvread(VALID/'01_archive_split/parent_results.csv') if r['document_id'] in {t['unit_id'] for t in triage if t['origin']=='task1'}}
    findings={ (r['unit_id'],r['rule_id']):r for r in csvread(VALID/'02_provenance_logic/findings.csv') if r['outcome']=='needs_review'}
    inputs=[stamp(p,True) for p in [STAGE/'coordinator_triage.csv',STAGE/'ACCEPTANCE_AND_SCOPE.md',VALID/'01_archive_split/exceptions.csv',VALID/'01_archive_split/validate_archive_splits.py',VALID/'02_provenance_logic/findings.csv']]
    checkpoints=[stamp(p) for p in [DB,USDB,EUDB]]
    plan={'run_id':RUN,'rule_version':RULE,'created_at_utc':now(),'fixed_interval':['1988-01-01','2026-09-21'],'inputs':inputs,'checkpoints':checkpoints,'repairs':[],'dates':[],'states':[],'new_parents':[],'annotations':[],'dispositions':[],'requests':[],'composition':[],'raw_inputs':[],'regression_parents':[]}
    with locks():
      con=duckdb.connect(str(DB),read_only=True);con.execute("SET TimeZone='UTC'")
      uk_ids={t['unit_id'] for t in triage if t['unit_id'].startswith('doc_')};docs=get_documents(con,uk_ids);oldsegs=get_segments(con,uk_ids)
      # Snapshot only affected records and their linked saved-version metadata.
      linkrows=rows(con,"""SELECT x.document_id,x.relationship_type,cv.* FROM document_content_objects x JOIN content_versions cv USING(content_object_id) WHERE x.document_id IN (SELECT unnest(?)) ORDER BY x.document_id,cv.content_version_id""",[sorted(uk_ids)])
      links=defaultdict(list)
      for r in linkrows:links[r['document_id']].append(r)
      plan['pre_counts']={t:con.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['documents','document_versions','text_segments','voice_attributions','content_versions','content_fetches','raw_records','acquisition_object_statuses']}
      plan['before_images']={pid:{'document':docs[pid],'segments':oldsegs[pid],'links':links[pid]} for pid in docs}
      paths={r['raw_path'] for r in diagrows.values() if r.get('raw_path')}
      paths.update(t['evidence'].rsplit('#',1)[0] for t in triage if t['category']=='candidate_saved_original_omission')
      originals={};xmloriginal={}
      for ix,rp in enumerate(sorted(paths)):
        p=ROOT/rp
        if not p.is_file(): originals[rp]={};continue
        plan['raw_inputs'].append(stamp(p,True))
        try:
            if rp.endswith('.zip'): originals[rp],xmloriginal[rp]=xml_groups(p)
            elif rp.endswith(('.htm','.html')):originals[rp]=item_groups(p)
            elif 'written_answer_details' in rp:originals[rp]=archive_nodes(p)
            else:originals[rp]={}
        except (ValueError,KeyError,ET.ParseError) as exc:originals[rp]={};plan.setdefault('parse_limits',[]).append({'path':rp,'reason':str(exc)})
        if ix%200==0: print(f'Inspected saved containers {ix+1}/{len(paths)}',flush=True)
      # Existing-source repairs are whole-parent replacement projections; old runs remain immutable.
      disposition_map={};repair_map={}
      for t in triage:
        if t['category'] not in ('reply_role_or_boundary','original_mapping_uncertain','source_date_conflict'):continue
        pid=t['unit_id'];d=docs[pid];dr=diagrows[pid];rp=dr['raw_path'];gs=originals[rp];old=oldsegs[pid]
        g,mapping=chosen_group(d,old,gs,dr)
        if t['category']=='source_date_conflict':
            heading=(g or {}).get('date_heading','')
            if 'between 20 December 2002 and 6 January 2003' in heading:lo,hi='2002-12-20','2003-01-06'
            elif 'between Tuesday 7 October and Monday 13 October 2003' in heading:lo,hi='2003-10-07','2003-10-13'
            else:lo=hi=''
            if not lo:disposition_map[(pid,t['category'])]=('unresolved','Date heading cannot be bounded without inventing a date');continue
            plan['dates'].append({'document_id':pid,'prior_date':str(d['publication_date']),'exact_date':None,'interval_start':lo,'interval_end':hi,'analysis_month':lo[:7] if lo[:7]==hi[:7] else None,'evidence_locator':rp+'#'+heading,'reason':'Explicit received-between range; format attribute and old parser value are not independent exact-day evidence.'})
            disposition_map[(pid,t['category'])]=('repaired','Range annotated; exact day NULL in effective view; month retained only if the entire range is within one month. Legacy date retained.')
            continue
        if g is None or not any(n['role']=='response' for n in g['nodes']):
            disposition_map[(pid,t['category'])]=('unresolved',mapping)
            if not gs and 'hansard_api/search' in rp:
                plan['requests'].append({'unit_id':pid,'source_id':d['source_id'],'source_date':str(d['publication_date']),'canonical_url':d['canonical_url'],'requested_original':f'Saved Hansard detail for ExtId {d["external_id"]}','why_existing_evidence_insufficient':'Only a search-result container is linked, with no saved detail/body node mapping.','existing_evidence':rp,'request_type':'named_missing_detail','priority':'split_identity_boundary'})
            continue
        if g['date'] != str(d['publication_date']):
            disposition_map[(pid,t['category'])]=('unresolved','Saved group date differs; no automatic boundary repair across dates');continue
        # Complete identity/date evidence plus a stored node anchor is required.
        oldids={diagnostic.locator_parts(s['locator'])[1] for s in old};newids={n['node_id'] for n in g['nodes']}
        if not oldids & newids and 'signature' not in mapping and 'text_mapping' not in mapping:
            disposition_map[(pid,t['category'])]=('unresolved','No stable old/new source node anchor');continue
        r={'document_id':pid,'source_id':d['source_id'],'external_id':d['external_id'],'content_version_id':dr['content_version_id'],'raw_path':rp,'original_group_id':g['key'],'mapping_basis':mapping,'before_fingerprint':parent_fingerprint(d,old),'before_segment_ids':[s['segment_id'] for s in old],'nodes':g['nodes'],'prior_rule_ids':dr['rule_ids']}
        repair_map[pid]=r
        disposition_map[(pid,t['category'])]=('repaired','Versioned full-parent role/span projection from original nodes; legacy segments/extraction run unchanged. Mapping: '+mapping)
      plan['repairs']=list(repair_map.values())
      # Item reconstruction may reveal additional original groups within an affected saved page.
      # They are recorded, without silently expanding the 202 approved candidate ledger.
      for rp,gs in originals.items():
        if rp.endswith(('.html','.htm')) and gs:
            plan.setdefault('item_extra_group_limits',[]).append({'path':rp,'original_groups':list(gs),'scope':'Only selected parent correction; unregistered additional HTML groups require a separately accepted omission scope.'})
      status_ids={t['unit_id'] for t in triage if t['category']=='STATUS' and t['unit_id'] in docs}
      status_vids=sorted({v['content_version_id'] for pid in status_ids for v in links[pid]})
      stats=rows(con,"SELECT content_version_id,count(*) segment_count,sum(length(segment_text)) characters FROM text_segments WHERE content_version_id IN (SELECT unnest(?)) AND length(trim(segment_text))>0 GROUP BY 1",[status_vids])
      readable={s['content_version_id']:s for s in stats}
      for t in triage:
        if t['category']!='STATUS' or t['source'] not in ('src_ac30b1ae596ab5ab5379','src_5b20e03d548a16a2d5c2') and t['unit_id'] not in docs:continue
        pid=t['unit_id']
        if pid not in docs:continue
        vv=links[pid];vids=[v['content_version_id'] for v in vv]
        evidence=[{**v,**readable[v['content_version_id']]} for v in vv if v['content_version_id'] in readable and (ROOT/v['raw_path']).is_file() and (ROOT/v['raw_path']).stat().st_size>0]
        state='saved_text_available' if evidence else 'saved_text_relation_unresolved'
        plan['states'].append({'document_id':pid,'state':state,'previous_body_status':docs[pid]['body_status'],'ethics_status':docs[pid]['ethics_status'],'licence_status':docs[pid]['licence_status'],'evidence':evidence,'rule_version':RULE})
        disposition_map[(pid,'STATUS')]=('repaired' if evidence else 'unresolved','Current technical availability recorded independently; historical body_status, ethics, licence and failed attempts preserved.')
      # Candidate omission review: frozen department/date, previous exclusions,
      # same-ID/node ownership and exact dated question+reply overlap.
      omit=[t for t in triage if t['category']=='candidate_saved_original_omission']
      exfiles=[BASE/'07_historical_government_acquisition/reports/historic_parser_artifact_exclusions.csv',BASE/'07_historical_government_acquisition/historical_coverage_recovery/exclusion_ledger.csv',BASE/'07_historical_government_acquisition/zero_month_policy_recovery/excluded_alternatives.csv']
      excluded=set()
      for p in exfiles:
        plan['inputs'].append(stamp(p,True))
        for e in csvread(p):excluded.update(str(v) for k,v in e.items() if 'id' in k)
      candids=[t['unit_id'].rsplit('#',1)[-1] for t in omit]
      # A candidate reply already used by any registered parent is not reimported.
      owners=defaultdict(list)
      for o in rows(con,"SELECT a.document_id,d.source_id,d.external_id,d.publication_date,regexp_extract(s.locator,'source_id=([^;]+)',1) node_id FROM voice_attributions a JOIN text_segments s USING(segment_id) JOIN documents d USING(document_id) WHERE regexp_extract(s.locator,'source_id=([^;]+)',1) IN (SELECT unnest(?))",[candids]):owners[o['node_id']].append(o)
      candidate_dates=sorted({g['date'] for t in omit for g in [originals[t['unit_id'].rsplit('#',1)[0]].get(t['unit_id'].rsplit('#',1)[1])] if g})
      peerids=[r['document_id'] for r in rows(con,"SELECT document_id FROM documents WHERE publication_date IN (SELECT unnest(?)::DATE)",[candidate_dates])]
      peerseg=get_segments(con,peerids);peersig=defaultdict(list)
      for pid,ss in peerseg.items():
        sig=tuple(('question' if diagnostic.locator_parts(s['locator'])[0]=='question_context' else 'response',clean(s['segment_text']).casefold()) for s in ss)
        peersig[sig].append(pid)
      for t in omit:
        rp,k=t['unit_id'].rsplit('#',1);g=originals[rp].get(k)
        reason='';status='unresolved'
        if k in excluded:status='ineligible';reason='Named earlier exclusion retained'
        elif not g:reason='Candidate is not a stable independently mapped original group'
        elif g.get('department') not in diagnostic.DEPARTMENTS:status='ineligible';reason='Outside frozen department frame'
        elif not ('1988-01-01'<=g['date']<='2026-09-21'):status='ineligible';reason='Outside fixed publication interval'
        elif 'between ' in g.get('date_heading','').lower():reason='Original has range-only day; no exact-day ingestion'
        elif owners[k]:status='confirmed';reason='Original reply is already represented under registered parent: '+dump(owners[k])
        elif peersig[signature(g['nodes'])]:status='confirmed';reason='Full exact question/reply signature represented on candidate days: '+dump(peersig[signature(g['nodes'])])
        else:
            explicit,date_support=single_saved_day(g)
            if explicit!=g['date']:reason='Visible day and parsed date do not independently agree'
            else:
                cv=rows(con,'SELECT * FROM content_versions WHERE raw_path=?',[rp])
                if len(cv)!=1:reason='Saved volume has ambiguous content-version identity'
                else:
                    source=t['source'];date=g['date'];slug=re.sub(r'[^a-z0-9]+','-',g['title'].lower()).strip('-');dt=datetime.fromisoformat(date)
                    url=f'https://api.parliament.uk/historic-hansard/written-answers/{dt.year}/{dt.strftime("%b").lower()}/{dt.day:02d}/{slug}#{k}'
                    # Keep the established source+external-id stable identity convention.
                    pid=sid('doc',source,k)
                    if con.execute('SELECT count(*) FROM documents WHERE document_id=? OR (source_id=? AND external_id=?) OR canonical_url=?',[pid,source,k,url]).fetchone()[0]:status='confirmed';reason='Stable parent identity already registered'
                    else:
                        template=rows(con,'SELECT d.* FROM documents d JOIN document_content_objects x USING(document_id) WHERE x.content_object_id=? LIMIT 1',[cv[0]['content_object_id']])[0]
                        doc={**template,'document_id':pid,'source_id':source,'external_id':k,'canonical_url':url,'title':g['title'],'publication_date':date,'publication_timestamp':None,'publication_date_basis':'explicit saved XML sitting heading; locally derived '+RULE,'collected_at':str(cv[0]['retrieved_at']),'deduplication_status':'exact_source_node_and_dated_full_text_checked','source_overlap_status':'no_exact_dated_full_question_reply_match_in_saved_UK_frame','body_status':'downloaded_and_extracted','body_status_reason':'Recovered from already saved ZIP into versioned repair layer'}
                        plan['new_parents'].append({'document':doc,'content_object_id':cv[0]['content_object_id'],'content_version_id':cv[0]['content_version_id'],'raw_path':rp,'original_group_id':k,'department':g['department'],'nodes':g['nodes'],'retrieved_at':str(cv[0]['retrieved_at']),'derived_at':now(),'original_date_heading':g['date_heading'],'saved_date_attribute':g['date_attribute'],'date_support':date_support,'omission_issue_id':t['unit_id']})
                        status='repaired';reason='Eligible exact-day original absent by stable ID, source node, prior exclusions and full dated signature; incremental repair-layer parent, no download.'
        disposition_map[(t['unit_id'],t['category'])]=(status,reason)
      # Focused regression baseline: existing legitimate modern shared groups and
      # ordinary historic/XML/detail parents, selected from frozen diagnostics.
      modern=csvread(VALID/'01_archive_split/answer_groups.csv')
      share=next((r for r in modern if r.get('status')=='legitimate_shared_span'),None)
      # Header variations are tolerated by selecting from parent result statuses.
      regs=[]
      for r in csvread(VALID/'01_archive_split/parent_results.csv'):
        if (r['status']=='legitimate_shared_span' and sum(x['status']=='legitimate_shared_span' for x in regs)<6) or (r['status']=='supported_split' and r['adapter'] in ('historic_xml_zip','archive_detail_json','historic_item_html') and not any(x['adapter']==r['adapter'] and x['status']=='supported_split' for x in regs)):
            regs.append(r)
        if len(regs)>=9:break
      rd=get_documents(con,{r['document_id'] for r in regs});rs=get_segments(con,set(rd))
      plan['regression_parents']=[{'document_id':r['document_id'],'status':r['status'],'adapter':r['adapter'],'fingerprint':parent_fingerprint(rd[r['document_id']],rs[r['document_id']])} for r in regs]
      con.close()
      # Companion non-UK reviews are additive annotations, never speculative rewrites.
      ua=duckdb.connect(str(USDB),read_only=True);ua.execute("SET TimeZone='UTC'")
      foreign_ids={t['unit_id'] for t in triage if t['unit_id'].startswith('doc:')};fd=get_documents(ua,foreign_ids)
      fe={r['document_id']:r for r in rows(ua,'SELECT * FROM us_au_record_evidence WHERE document_id IN (SELECT unnest(?))',[sorted(foreign_ids)])}
      for t in triage:
        if t['unit_id'] not in fd:continue
        pid=t['unit_id'];d=fd[pid];ev=fe.get(pid,{})
        if t['category']=='IDENT':status='confirmed';reason='Distinct canonical URL/publication-day parents retained; repeating FR number is not a merge key.'
        else:
            status='unresolved';reason='Existing candidate evidence does not verify exact original date/issuer/file boundary: '+dump(ev)
            if t['category'] in ('DATE_SCOPE','ISSUER'):
                plan['requests'].append({'unit_id':pid,'source_id':d['source_id'],'source_date':ev.get('date_value') or str(d['publication_date'] or ''),'canonical_url':d['canonical_url'],'requested_original':'Original title/imprint/publication page and primary-file mapping','why_existing_evidence_insufficient':findings[(pid,t['category'])]['reason'],'existing_evidence':dump(ev),'request_type':t['category'].lower(),'priority':'source_date_or_issuer'})
        disposition_map[(pid,t['category'])]=(status,reason)
        plan.setdefault('companion_evidence',[]).append({'unit_id':pid,'rule':t['category'],'document':d,'saved_evidence':ev})
      ua.close()
      eu=duckdb.connect(str(EUDB),read_only=True)
      eids=sorted({t['unit_id'] for t in triage if t['source']=='eu_cellar_com_preparatory_en_v1'})
      evs=rows(eu,'SELECT * FROM eu_content_versions WHERE work_uri IN (SELECT unnest(?))',[eids]);ewdates=rows(eu,'SELECT * FROM eu_work_dates WHERE work_uri IN (SELECT unnest(?))',[eids]);eu.close()
      edates={r['work_uri']:str(r['document_date']) for r in ewdates}
      for t in triage:
        if t['unit_id'] in eids:
            f=findings[(t['unit_id'],t['category'])];disposition_map[(t['unit_id'],t['category'])]=('unresolved','Named OCR/layout/table/selected-Item limitation retained; saved bytes do not establish validated complete text. '+f['observed'])
      # A specific optional technical need is exported for failed selected Items.
      # OCR/placeholder originals already saved are local extraction tasks, not downloads.
      for w in eids:
        f=findings[(w,'CONTENT_LINK')];ob=json.loads(f['observed'])
        if ob.get('disposition')=='selected_item_failed':
            plan['requests'].append({'unit_id':w,'source_id':'eu_cellar_com_preparatory_en_v1','source_date':edates.get(w,''),'canonical_url':w,'requested_original':'Named selected English Item or documented English alternative','why_existing_evidence_insufficient':f['observed'],'existing_evidence':f['evidence_path']+'#'+f['evidence_locator'],'request_type':'optional_named_failed_item','priority':'optional_only_if_selected_frame_requires'})
      plan['eu_review_saved_versions']=evs
      for t in triage:
        key=(t['unit_id'],t['category'])
        if t['category']=='DATE_CROSS':
            d=docs[t['unit_id']];disp=('confirmed','Convention annotation only; source calendar date '+str(d['publication_date'])+' and saved publication timestamp '+str(d['publication_timestamp'])+' retained. Analysis-day/month convention undecided.')
        else:disp=disposition_map.get(key,('unresolved','No supported bounded mutation; explicit review annotation retained.'))
        issue=sid('issue',t['origin'],t['unit_id'],t['category'],t['rules'],t['evidence'])
        plan['dispositions'].append({**t,'issue_id':issue,'disposition':disp[0],'resolution':disp[1],'rule_version':RULE})
        if t['origin']=='task2':
            f=findings[key];plan['annotations'].append({**f,'disposition':disp[0],'resolution':disp[1]})
      plan['composition']=[{'need_id':'composition_parliament_dominance','source_id':'pooled_government','date_interval':'1988-01-01/2026-09-21','genre':'parliamentary answers compared with independently framed executive documents','unit':'independent dated original parent','why_existing_evidence_insufficient':'Saved UK parliamentary frames dominate UK genre composition; country/source counts alone do not give interchangeable role series. Use existing frozen composition tables to define at most one alternative first tranche.','evidence':'13_parallel_data_audit_20261004/02_distribution/monthly_source_genre_counts.csv; ACCEPTANCE_AND_SCOPE.md Task4','proposed_scope':'Task4 predeclared coherent frame and stopping rule; no equalisation or semantic gate'}]
    # One compact plan is also the before-image/change manifest. No full DB copy.
    atomic(HERE/'PLAN.json',plan)
    csvwrite(HERE/'issue_dispositions.csv',plan['dispositions'],list(plan['dispositions'][0]))
    csvwrite(HERE/'missing_original_requests.csv',plan['requests'],['unit_id','source_id','source_date','canonical_url','requested_original','why_existing_evidence_insufficient','existing_evidence','request_type','priority'])
    csvwrite(HERE/'source_composition_needs.csv',plan['composition'],list(plan['composition'][0]))
    atomic(HERE/'INPUT_MANIFEST.json',{'created_at_utc':plan['created_at_utc'],'fixed_interval':plan['fixed_interval'],'formal_authority':str(DB.relative_to(ROOT)),'UK09_copy_policy':'Historical copied UK tables remain unchanged; UK06 plus active repair views is authoritative. Never add copied UK09 counts.','inputs':plan['inputs'],'database_checkpoints':checkpoints,'changed_raw_inputs':plan['raw_inputs'],'pre_counts':plan['pre_counts']})
    summary={'status':'staged_checked_plan','counts':{k:len(plan[k]) for k in ['repairs','dates','states','new_parents','annotations','dispositions','requests']},'dispositions':dict(Counter(r['disposition'] for r in plan['dispositions'])),'plan_bytes':(HERE/'PLAN.json').stat().st_size,'plan_sha256':digest((HERE/'PLAN.json').read_bytes())}
    atomic(HERE/'DRY_RUN.json',summary);print(json.dumps(summary,indent=2))

def verify_checkpoints(plan):
    for expected in plan['checkpoints']:
        actual=stamp(ROOT/expected['path'])
        if actual!=expected:raise RuntimeError('Database checkpoint moved: '+expected['path'])
    for expected in plan['inputs']+plan['raw_inputs']:
        if stamp(ROOT/expected['path'],'sha256' in expected)!=expected:raise RuntimeError('Evidence checkpoint moved: '+expected['path'])

def writer_preflight():
    # ps is intentionally strict. If the sandbox blocks it, run this authorised
    # CLI with the required process-read approval; never assume no process.
    proc=subprocess.run(['ps','-axo','pid,ppid,command'],capture_output=True,text=True)
    if proc.returncode:raise RuntimeError('Cannot verify live collectors/writers: '+proc.stderr.strip())
    hits=[]
    for line in proc.stdout.splitlines()[1:]:
        m=re.match(r'\s*(\d+)\s+(\d+)\s+(.*)',line)
        if not m or int(m[1]) in (os.getpid(),os.getppid()):continue
        cmd=m[3]
        if (re.search(r'(?:python\S*|duckdb)\s',cmd) and re.search(r'fear_of_temperature|acquis|collect|ingest|repair|validate|eu_stage|government_content',cmd)) or re.search(r'\b(?:lsof|duckdb)\b.*(?:government_content|us_au_v1|eu_stage)',cmd):hits.append(line)
    if hits:raise RuntimeError('External collector/DB access conflict; do not terminate: '+dump(hits))
    # Native DuckDB exclusive file locking is a further mandatory writer check.
    return {'checked_at_utc':now(),'process_check':'no_matching_external_collector_or_DB_process','pid':os.getpid()}

SCHEMA="""
CREATE TABLE IF NOT EXISTS repair_runs(run_id VARCHAR PRIMARY KEY,rule_version VARCHAR,plan_sha256 VARCHAR,committed_at_utc VARCHAR,active BOOLEAN,plan_path VARCHAR);
CREATE TABLE IF NOT EXISTS repair_parent_versions(run_id VARCHAR,document_id VARCHAR,original_group_id VARCHAR,content_version_id VARCHAR,raw_path VARCHAR,before_fingerprint VARCHAR,metadata_json VARCHAR,PRIMARY KEY(run_id,document_id));
CREATE TABLE IF NOT EXISTS repair_segments(run_id VARCHAR,document_id VARCHAR,segment_id VARCHAR,content_version_id VARCHAR,segment_order INTEGER,role VARCHAR,actor_name VARCHAR,segment_text VARCHAR,locator VARCHAR,text_sha256 VARCHAR,source_node_id VARCHAR,role_basis VARCHAR,PRIMARY KEY(run_id,segment_id));
CREATE TABLE IF NOT EXISTS repair_date_intervals(run_id VARCHAR,document_id VARCHAR,prior_date DATE,exact_date DATE,interval_start DATE,interval_end DATE,analysis_month VARCHAR,evidence_locator VARCHAR,reason VARCHAR,PRIMARY KEY(run_id,document_id));
CREATE TABLE IF NOT EXISTS repair_content_states(run_id VARCHAR,document_id VARCHAR,current_technical_state VARCHAR,prior_body_status VARCHAR,ethics_status VARCHAR,licence_status VARCHAR,evidence_json VARCHAR,PRIMARY KEY(run_id,document_id));
CREATE TABLE IF NOT EXISTS repair_recovered_parents(run_id VARCHAR,document_id VARCHAR,source_id VARCHAR,external_id VARCHAR,canonical_url VARCHAR,publication_date DATE,content_object_id VARCHAR,content_version_id VARCHAR,document_json VARCHAR,evidence_json VARCHAR,PRIMARY KEY(run_id,document_id));
CREATE TABLE IF NOT EXISTS repair_annotations(run_id VARCHAR,finding_id VARCHAR,unit_id VARCHAR,source_id VARCHAR,rule_id VARCHAR,rule_version VARCHAR,outcome VARCHAR,disposition VARCHAR,evidence_json VARCHAR,PRIMARY KEY(run_id,finding_id));
CREATE TABLE IF NOT EXISTS repair_issue_dispositions(run_id VARCHAR,issue_id VARCHAR,unit_id VARCHAR,category VARCHAR,disposition VARCHAR,evidence_json VARCHAR,PRIMARY KEY(run_id,issue_id));
"""

def create_views(con):
    # A recovered parent is a real persisted derived identity; no pretend raw
    # fetch, backdated extraction run, or duplicated volume/content row.
    cols=con.execute('DESCRIBE documents').fetchall()
    proj=[]
    for name,typ,*_ in cols:
        expr=f"json_extract_string(p.document_json,'$.{name}')"
        proj.append(f'CAST({expr} AS {typ}) AS {name}')
    con.execute('''CREATE OR REPLACE VIEW repair_parent_inventory AS SELECT d.* FROM documents d UNION ALL SELECT '''+', '.join(proj)+''' FROM repair_recovered_parents p JOIN repair_runs r USING(run_id) WHERE r.active''')
    con.execute("""CREATE OR REPLACE VIEW repair_current_documents AS
      SELECT d.* EXCLUDE(publication_date,publication_timestamp,publication_date_basis),
        CASE WHEN i.document_id IS NOT NULL THEN i.exact_date ELSE d.publication_date END publication_date,
        CASE WHEN i.document_id IS NOT NULL THEN NULL ELSE d.publication_timestamp END publication_timestamp,
        CASE WHEN i.document_id IS NOT NULL THEN 'explicit saved interval; exact day unverified' ELSE d.publication_date_basis END publication_date_basis,
        i.interval_start date_interval_start,i.interval_end date_interval_end,
        CASE WHEN i.document_id IS NOT NULL THEN i.exact_date IS NOT NULL ELSE d.publication_date IS NOT NULL END exact_day_eligible,
        CASE WHEN i.document_id IS NOT NULL THEN i.analysis_month ELSE strftime(d.publication_date,'%Y-%m') END analysis_month,
        s.current_technical_state,
        CASE WHEN d.document_id IN(SELECT document_id FROM repair_recovered_parents p JOIN repair_runs r USING(run_id) WHERE r.active) THEN 'recovered_saved_original' ELSE 'legacy_parent' END parent_origin
      FROM repair_parent_inventory d LEFT JOIN (SELECT i.* FROM repair_date_intervals i JOIN repair_runs r USING(run_id) WHERE r.active) i USING(document_id)
      LEFT JOIN (SELECT s.* FROM repair_content_states s JOIN repair_runs r USING(run_id) WHERE r.active) s USING(document_id)""")
    con.execute("""CREATE OR REPLACE VIEW repair_current_parent_segments AS
      SELECT a.document_id,s.segment_id,s.content_version_id,s.extraction_run_id,s.segment_order,s.segment_text,s.locator,a.actor_name,
        regexp_extract(s.locator,'role=([^;]+)',1) discourse_role,regexp_extract(s.locator,'source_id=([^;]+)',1) source_node_id,
        'legacy' repair_rule_version,NULL::VARCHAR repair_run_id,s.text_sha256
      FROM voice_attributions a JOIN text_segments s USING(segment_id)
      WHERE a.document_id NOT IN (SELECT p.document_id FROM repair_parent_versions p JOIN repair_runs r USING(run_id) WHERE r.active)
      UNION ALL
      SELECT s.document_id,s.segment_id,s.content_version_id,s.run_id,s.segment_order,s.segment_text,s.locator,s.actor_name,
        CASE WHEN s.role='question' THEN 'question_context' ELSE 'government_response' END discourse_role,s.source_node_id,r.rule_version,s.run_id,s.text_sha256
      FROM repair_segments s JOIN repair_runs r USING(run_id) WHERE r.active""")
    con.execute("""CREATE OR REPLACE VIEW repair_current_provenance_annotations AS SELECT a.* FROM repair_annotations a JOIN repair_runs r USING(run_id) WHERE r.active""")
    con.execute("""CREATE OR REPLACE VIEW repair_current_document_content_objects AS
      SELECT * FROM document_content_objects UNION ALL
      SELECT p.document_id,p.content_object_id,'attachment' relationship_type,0 object_order
      FROM repair_recovered_parents p JOIN repair_runs r USING(run_id) WHERE r.active""")

def insert_nodes(con,parent,vid,ns):
    values=[]
    for ix,n in enumerate(ns):
        segment=sid('seg',RUN,parent,n['node_id'],ix,digest(n['text']))
        role='question_context' if n['role']=='question' else 'government_response'
        loc=f'role={role};source_id={n["node_id"]};speaker={n["speaker"] or "unknown"};original_locator={n["locator"]}'
        values.append((RUN,parent,segment,vid,ix,n['role'],n['speaker'],n['text'],loc,digest(n['text']),n['node_id'],n['role_basis']))
    if values:con.executemany('INSERT INTO repair_segments VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',values)

def accept(con,plan):
    failures=[]
    if len(plan['dispositions'])!=3080 or len({r['issue_id'] for r in plan['dispositions']})!=3080:failures.append('triage accounting mismatch')
    actual=rows(con,'SELECT * FROM repair_current_parent_segments WHERE repair_run_id=? ORDER BY document_id,segment_order',[RUN]);by=defaultdict(list)
    for r in actual:by[r['document_id']].append(r)
    for p in plan['repairs']+[{'document_id':p['document']['document_id'],'nodes':p['nodes'],'content_version_id':p['content_version_id']} for p in plan['new_parents']]:
        pid=p['document_id'];expected=p['nodes'];got=by[pid]
        if len(got)!=len(expected):failures.append(pid+': segment cardinality');continue
        for a,n in zip(got,expected):
            role='question_context' if n['role']=='question' else 'government_response'
            if a['source_node_id']!=n['node_id'] or a['segment_text']!=n['text'] or a['discourse_role']!=role or a['content_version_id']!=p['content_version_id'] or a['text_sha256']!=digest(n['text']):failures.append(pid+': role/span/node/version mismatch')
    # Legacy before images and named shared-answer fixtures must remain byte/value equal.
    docs=get_documents(con,set(plan['before_images']));ss=get_segments(con,set(docs))
    for pid,b in plan['before_images'].items():
        if parent_fingerprint(docs[pid],ss[pid])!=parent_fingerprint(b['document'],b['segments']):failures.append(pid+': legacy data changed')
    rd=get_documents(con,{r['document_id'] for r in plan['regression_parents']});rs=get_segments(con,set(rd))
    for r in plan['regression_parents']:
        if parent_fingerprint(rd[r['document_id']],rs[r['document_id']])!=r['fingerprint']:failures.append(r['document_id']+': regression baseline changed')
    for i in plan['dates']:
        d=con.execute('SELECT publication_date,publication_timestamp,date_interval_start,date_interval_end,analysis_month,exact_day_eligible FROM repair_current_documents WHERE document_id=?',[i['document_id']]).fetchone()
        if d[:2]!=(None,None) or str(d[2])!=i['interval_start'] or str(d[3])!=i['interval_end'] or d[4]!=i['analysis_month'] or d[5]:failures.append(i['document_id']+': date isolation')
    for s in plan['states']:
        d=con.execute('SELECT current_technical_state,body_status,ethics_status,licence_status FROM repair_current_documents WHERE document_id=?',[s['document_id']]).fetchone()
        if tuple(d)!=(s['state'],s['previous_body_status'],s['ethics_status'],s['licence_status']):failures.append(s['document_id']+': technical/ethics separation')
    for t,n in plan['pre_counts'].items():
        if con.execute('SELECT count(*) FROM '+t).fetchone()[0]!=n:failures.append(t+': legacy count changed')
    for table,key in [('repair_parent_versions','repairs'),('repair_date_intervals','dates'),('repair_content_states','states'),('repair_recovered_parents','new_parents'),('repair_annotations','annotations'),('repair_issue_dispositions','dispositions')]:
        if con.execute('SELECT count(*) FROM '+table+' WHERE run_id=?',[RUN]).fetchone()[0]!=len(plan[key]):failures.append(table+': manifest count mismatch')
    duplicate=con.execute('SELECT count(*) FROM(SELECT document_id FROM repair_current_documents GROUP BY 1 HAVING count(*)>1)').fetchone()[0]
    if duplicate:failures.append('effective duplicate parent IDs')
    n=con.execute('SELECT count(*) FROM repair_current_documents').fetchone()[0]
    if n!=plan['pre_counts']['documents']+len(plan['new_parents']):failures.append('effective parent count mismatch')
    if failures:raise RuntimeError('Acceptance failed: '+dump(failures[:25]))
    return {'status':'passed','checked_at_utc':now(),'changed_parent_projections':len(plan['repairs']),'new_parent_projections':len(plan['new_parents']),'changed_segment_rows':len(actual),'date_intervals':len(plan['dates']),'technical_states':len(plan['states']),'issue_dispositions':len(plan['dispositions']),'effective_parent_count':n,'unchanged_legacy_before_images':len(docs),'shared_answer_and_other_regression_parents':len(rd),'failures':[]}

def apply_plan():
    plan=json.loads((HERE/'PLAN.json').read_text());planhash=digest((HERE/'PLAN.json').read_bytes())
    sourcecheck=json.loads((HERE/'FINAL_SAVED_TRANCHE_CHECKS.json').read_text())
    if sourcecheck['final_plan_sha256']!=planhash or sourcecheck['unexpected_conflicts']:raise RuntimeError('Final source-tranche check does not match frozen plan')
    fixture=json.loads((HERE/'TEST_RESULTS.json').read_text())
    if fixture.get('status')!='passed' or fixture.get('test_failures'):raise RuntimeError('Focused falsification fixtures have not passed')
    with locks(writer=True):
        process=writer_preflight()
        # Idempotent reruns verify the committed payload, without duplicating findings.
        probe=duckdb.connect(str(DB),read_only=True);probe.execute("SET TimeZone='UTC'")
        exists=probe.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='repair_runs'").fetchone()[0]
        prior=probe.execute('SELECT plan_sha256,active FROM repair_runs WHERE run_id=?',[RUN]).fetchone() if exists else None
        if prior:
            if prior!=(planhash,True):raise RuntimeError('Existing run inactive or different manifest')
            result=accept(probe,plan);probe.close();print(dump({'idempotent':'no_write',**result}));return
        probe.close();verify_checkpoints(plan)
        budget=max(512*1024**2,(HERE/'PLAN.json').stat().st_size*12)
        free=shutil.disk_usage(ROOT).free
        if free-budget<15*1024**3:raise RuntimeError('Insufficient safe bounded transaction/rollback footprint above retained 15GiB floor')
        atomic(HERE/'WRITE_PREFLIGHT.json',{'time_utc':now(),'process_check':process,'free_bytes':free,'reserved_transaction_WAL_rollback_bytes':budget,'floor_bytes':15*1024**3,'strategy':'append-only compact layer; no existing table rewritten; no whole DB backup; native DuckDB lock plus two advisory locks','lock_order':['heavy_io.lock','formal_database_writer.lock']})
        con=duckdb.connect(str(DB));con.execute("SET TimeZone='UTC'");con.execute("SET memory_limit='512MB'");con.execute('SET threads=2');con.execute('SET checkpoint_threshold=\'256MB\'')
        committed=False
        try:
            con.execute('BEGIN TRANSACTION');con.execute(SCHEMA)
            con.execute('INSERT INTO repair_runs VALUES (?,?,?,?,?,?)',[RUN,RULE,planhash,now(),True,str((HERE/'PLAN.json').relative_to(ROOT))])
            for p in plan['repairs']:
                con.execute('INSERT INTO repair_parent_versions VALUES (?,?,?,?,?,?,?)',[RUN,p['document_id'],p['original_group_id'],p['content_version_id'],p['raw_path'],p['before_fingerprint'],dump({k:v for k,v in p.items() if k!='nodes'})]);insert_nodes(con,p['document_id'],p['content_version_id'],p['nodes'])
            for i in plan['dates']:con.execute('INSERT INTO repair_date_intervals VALUES (?,?,?,?,?,?,?,?,?)',[RUN,i['document_id'],i['prior_date'],i['exact_date'],i['interval_start'],i['interval_end'],i['analysis_month'],i['evidence_locator'],i['reason']])
            for s in plan['states']:con.execute('INSERT INTO repair_content_states VALUES (?,?,?,?,?,?,?)',[RUN,s['document_id'],s['state'],s['previous_body_status'],s['ethics_status'],s['licence_status'],dump(s['evidence'])])
            for p in plan['new_parents']:
                d=p['document'];con.execute('INSERT INTO repair_recovered_parents VALUES (?,?,?,?,?,?,?,?,?,?)',[RUN,d['document_id'],d['source_id'],d['external_id'],d['canonical_url'],d['publication_date'],p['content_object_id'],p['content_version_id'],dump(d),dump({k:v for k,v in p.items() if k not in ('nodes','document')})]);insert_nodes(con,d['document_id'],p['content_version_id'],p['nodes'])
            if plan['annotations']:con.executemany('INSERT INTO repair_annotations VALUES (?,?,?,?,?,?,?,?,?)',[(RUN,a['finding_id'],a['unit_id'],a['source_id'],a['rule_id'],a['rule_version'],a['outcome'],a['disposition'],dump(a)) for a in plan['annotations']])
            con.executemany('INSERT INTO repair_issue_dispositions VALUES (?,?,?,?,?,?)',[(RUN,d['issue_id'],d['unit_id'],d['category'],d['disposition'],dump(d)) for d in plan['dispositions']])
            create_views(con);result=accept(con,plan)
            con.execute('COMMIT');committed=True
            # Re-read the affected layer after COMMIT; release only after closure.
            result=accept(con,plan)
        except Exception:
            if not committed:con.execute('ROLLBACK')
            raise
        finally:con.close()
        atomic(HERE/'ACCEPTANCE.json',result)
        post=stamp(DB);atomic(HERE/'APPLIED.json',{'status':'applied_and_checked','committed_at_utc':now(),'run_id':RUN,'plan_sha256':planhash,'pre_checkpoint':plan['checkpoints'][0],'post_checkpoint':post,'acceptance':result,'free_bytes_after':shutil.disk_usage(ROOT).free})
        atomic(HERE/'CHANGE_MANIFEST.json',{'run_id':RUN,'rule_version':RULE,'plan_sha256':planhash,'before_images':'PLAN.json#before_images','new_values':'PLAN.json#repairs,dates,states,new_parents,annotations','prior_extraction_versions':'PLAN.json#before_images.*.segments.extraction_run_id','rollback':'--rollback deactivates run transactionally; raw/legacy evidence unaffected','pre_checkpoint':plan['checkpoints'][0],'post_checkpoint':post,'counts':{k:len(plan[k]) for k in ['repairs','dates','states','new_parents','annotations','dispositions']}})
        print(dump({**result,'status':'applied_and_checked'}))

def verify_plan():
    plan=json.loads((HERE/'PLAN.json').read_text())
    with locks():
        con=duckdb.connect(str(DB),read_only=True);con.execute("SET TimeZone='UTC'")
        try:r=accept(con,plan)
        finally:con.close()
    atomic(HERE/'VERIFY.json',r);print(dump(r))

def rollback():
    with locks(writer=True):
        writer_preflight()
        expected=json.loads((HERE/'APPLIED.json').read_text())['post_checkpoint']
        if stamp(DB)!=expected:raise RuntimeError('Post-repair checkpoint moved; rollback needs an explicit dependency review')
        con=duckdb.connect(str(DB));con.execute('BEGIN TRANSACTION')
        try:
            run=con.execute('SELECT active FROM repair_runs WHERE run_id=?',[RUN]).fetchone()
            if run is None:raise RuntimeError('Repair run absent')
            con.execute('UPDATE repair_runs SET active=false WHERE run_id=?',[RUN]);con.execute('COMMIT')
        except Exception:con.execute('ROLLBACK');raise
        finally:con.close()
        marker=STAGE/'control/REPAIR_READY.json'
        if marker.exists():atomic(marker,{'ready':False,'status':'rolled_back','run_id':RUN,'time_utc':now()})
        atomic(HERE/'ROLLBACK_RESULT.json',{'status':'rolled_back_by_deactivation','run_id':RUN,'time_utc':now(),'historical_rows_retained':True})

def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    for opt in ['dry-run','apply','verify','rollback']:g.add_argument('--'+opt,action='store_true')
    a=p.parse_args()
    if a.dry_run:build_plan()
    elif a.apply:apply_plan()
    elif a.verify:verify_plan()
    else:rollback()
if __name__=='__main__':main()
