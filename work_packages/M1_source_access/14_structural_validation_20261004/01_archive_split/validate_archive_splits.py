#!/usr/bin/env python3
"""Independent, read-only validation of UK parliamentary reply splits.

Run: .venv/bin/python validate_archive_splits.py run --root /path/to/repo
Uses one read-only DuckDB stream and saved XML/JSON/HTML originals. No HTTP.
The heavy phase holds the shared advisory lock and always releases it.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import html
import json
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import duckdb
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[3]
DB_REL = 'work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb'
LOCK_REL = 'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock'
SOURCES = {
 'src_549acfda11091ff8c9b8':'historic_xml_zip_or_item_html',
 'src_9e8f487d372ed011db82':'archive_detail_or_html',
 'src_90b3a872375c9e7fd267':'questions_statements_list_json',
 'src_3c349b00120866c263a3':'parlparse_xml_mirror',
}
DEPARTMENTS = {
 'ENERGY','ENVIRONMENT','ENVIRONMENT, FOOD AND RURAL AFFAIRS',
 'ENVIRONMENT, TRANSPORT AND THE REGIONS','TRADE AND INDUSTRY',
 'AGRICULTURE, FISHERIES AND FOOD','BUSINESS, ENTERPRISE AND REGULATORY REFORM',
 'ENERGY AND CLIMATE CHANGE',
}
START,END='1988-01-01','2026-09-21'
PARENT_FIELDS=['source_id','adapter','document_id','external_id','publication_date','content_type',
 'content_object_id','content_version_id','raw_path','original_group_id','answer_group_key',
 'original_question_ids','original_response_ids','stored_question_ids','stored_response_ids',
 'original_reply_nodes','matched_reply_nodes','segment_count','matched_segments','status',
 'rule_ids','evidence_locator','details']
CONTAINER_FIELDS=['source_id','adapter','raw_path','content_version_id','imported_parent_count',
 'original_group_count','original_node_count','mapped_parent_count','supported_parents',
 'shared_parents','duplicate_parents','boundary_conflicts','insufficient_parents',
 'omitted_candidate_groups','status','rule_ids','evidence_locator','details']
EXCEPTION_FIELDS=['unit','source_id','adapter','document_id','external_id','raw_path','status','rule_ids','evidence_locator','details','minimal_action']


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact(value: str | None) -> str:
    value=html.unescape(str(value or ''))
    value=unicodedata.normalize('NFKC',value)
    value=value.replace('\u00a0',' ')
    return re.sub(r'\s+',' ',value).strip()


def compare_text(stored: str, original: str) -> str:
    """Conservative span test; exact node identity is checked separately."""
    a,b=compact(stored),compact(original)
    if not a or not b:return 'insufficient'
    al,bl=a.casefold(),b.casefold()
    if al==bl:return 'match'
    if al in bl:
        return 'truncated' if len(a)<0.78*len(b) and len(b)>80 else 'match'
    if bl in al:
        return 'leakage' if len(a)-len(b)>max(40,.2*len(b)) else 'match'
    # This allows small punctuation/markup differences but never upgrades a
    # grossly different source span to supported merely by shared keywords.
    import difflib
    if max(len(a),len(b))<=10000:
        ratio=difflib.SequenceMatcher(None,al,bl,autojunk=False).ratio()
        if ratio>=.90:return 'match'
        if ratio<.45:return 'mismatch'
    return 'insufficient'


@dataclass
class Node:
    key: str
    role: str
    text: str
    speaker: str
    order: int
    group_key: str


@dataclass
class Group:
    key: str
    date: str
    title: str
    question_keys: list[str] = field(default_factory=list)
    response_keys: list[str] = field(default_factory=list)
    explicit_joint: bool = False
    uin: str = ''
    grouped_uins: list[str] = field(default_factory=list)


@dataclass
class Original:
    adapter: str
    nodes: dict[tuple[str,str],Node] = field(default_factory=dict)
    groups: dict[str,Group] = field(default_factory=dict)
    aliases: dict[tuple[str,str],str] = field(default_factory=dict)
    by_key: dict[str,list[Node]] = field(default_factory=lambda:defaultdict(list))
    signatures: dict[tuple[tuple[str,...],tuple[str,...]],list[str]] = field(default_factory=lambda:defaultdict(list))
    omission_scope: str = 'mapped_groups_only'
    parse_note: str = ''

    def add_node(self,node: Node,aliases: list[str] | None = None) -> None:
        self.nodes[(node.group_key,node.key)]=node
        self.by_key[node.key].append(node)
        for alias in aliases or []:
            if alias:
                self.aliases[(node.group_key,alias)]=node.key
                self.by_key[alias].append(node)

    def get_node(self,key: str,group_key: str | None = None) -> Node | None:
        if group_key:
            local=self.nodes.get((group_key,self.aliases.get((group_key,key),key)))
            if local:return local
        candidates={id(x):x for x in self.by_key.get(key,[])}
        return next(iter(candidates.values())) if len(candidates)==1 else None


@dataclass
class Segment:
    segment_id: str
    locator: str
    text: str
    order: int | None
    version_id: str
    actor: str


@dataclass
class Parent:
    source_id: str
    document_id: str
    external_id: str
    date: str
    genre: str
    object_id: str
    version_id: str
    raw_path: str
    mime: str
    normalized_version_count: int
    segments: dict[str,Segment] = field(default_factory=dict)


def strip_xml_speaker(element: ET.Element) -> tuple[str,str]:
    full=compact(' '.join(element.itertext()))
    member=element.find('./member')
    speaker=compact(' '.join(member.itertext())) if member is not None else ''
    if speaker:
        expr=r'^(?:\d+\.\s*)?(?:\[[^]]+\]\s*)?'+re.escape(speaker)+r'\s*[:;—-]*\s*'
        full=re.sub(expr,'',full,flags=re.I)
    return speaker,full


def question_start(text: str) -> bool:
    return bool(re.match(r'^(?:\d+\.\s*)?(?:\[[^]]+\]\s*)?To ask\b',compact(text),flags=re.I))


def visible_historic_date(element: ET.Element | None) -> str:
    if element is None:return ''
    text=compact(' '.join(element.itertext()))
    # Bulk volumes also have range headings such as "received between 23 May
    # and 2 June 2003". That is not a single sitting day: retain the explicit
    # format attribute rather than accidentally choosing the range end.
    single=re.fullmatch(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})',text)
    match=single or (re.search(r'\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b',text) if not element.attrib.get('format') else None)
    if match:
        try:return datetime.strptime(' '.join(match.groups()),'%d %B %Y').date().isoformat()
        except ValueError:pass
    return str(element.attrib.get('format') or '')[:10]


def parse_historic_zip(path: Path) -> Original:
    out=Original(adapter='historic_xml_zip',omission_scope='approved_department_groups_in_saved_volume')
    group_no=0; node_no=0
    with zipfile.ZipFile(path) as archive:
        names=[n for n in archive.namelist() if n.lower().endswith('.xml')]
        if not names:raise ValueError('ZIP has no XML member')
        for name in names:
            with archive.open(name) as stream:root=ET.parse(stream).getroot()
            for tag,genre in [('writtenanswers','ministerial_written_answer'),('writtenstatements','ministerial_written_statement')]:
                for container in root.iter(tag):
                    date_el=container.find('./date')
                    date=visible_historic_date(date_el)
                    if not (START<=date<=END):continue
                    for dept in list(container):
                        if dept.tag not in ('group','section'):continue
                        label=compact(' '.join(dept.find('./title').itertext())).upper() if dept.find('./title') is not None else ''
                        if label not in DEPARTMENTS:continue
                        for sec in dept.findall('./section'):
                            title=compact(' '.join(sec.find('./title').itertext())) if sec.find('./title') is not None else ''
                            body=sec.find('./body')
                            if body is None:body=sec
                            paras=body.findall('.//p')
                            pending_q: list[tuple[str,str,str,int]]=[]
                            pending_r: list[tuple[str,str,str,int]]=[]
                            def flush() -> None:
                                nonlocal group_no
                                if not pending_r:return
                                group_no+=1
                                first=next((x[0] for x in pending_r if x[0]),'')
                                key=first or f'no_id:{name}:{group_no}'
                                qkeys=[ident or f'{key}:q:{ix}' for ix,(ident,_,_,_) in enumerate(pending_q,1)]
                                rkeys=[ident or f'{key}:r:{ix}' for ix,(ident,_,_,_) in enumerate(pending_r,1)]
                                grp=Group(key=key,date=date,title=title,
                                          question_keys=qkeys,response_keys=rkeys,
                                          explicit_joint=len(pending_q)>1)
                                out.groups[key]=grp
                                if not first:
                                    sig=(tuple(compact(x[2]).casefold() for x in pending_q),
                                         tuple(compact(x[2]).casefold() for x in pending_r))
                                    out.signatures[sig].append(key)
                                for role,items in [('question',pending_q),('response',pending_r)]:
                                    keys=qkeys if role=='question' else rkeys
                                    for (ident,speaker,body,order),node_key in zip(items,keys):
                                        out.add_node(Node(node_key,role,body,speaker,order,key))
                            for para in paras:
                                speaker,body=strip_xml_speaker(para)
                                if not body:continue
                                ident=para.attrib.get('id','')
                                node_no+=1
                                if genre=='ministerial_written_statement':
                                    pending_r.append((ident,speaker,body,node_no));continue
                                isq=bool(speaker and question_start(body))
                                if isq:
                                    if pending_r:flush();pending_q=[];pending_r=[]
                                    pending_q.append((ident,speaker,body,node_no))
                                elif not speaker and pending_q and not pending_r:
                                    pending_q.append((ident,speaker,body,node_no))
                                elif speaker or pending_q or pending_r:
                                    pending_r.append((ident,speaker,body,node_no))
                            flush()
            del root
    return out


def parse_historic_item_html(path: Path) -> Original:
    soup=BeautifulSoup(path.read_bytes(),'html.parser')
    out=Original(adapter='historic_item_html',omission_scope='mapped_saved_item_page_only')
    match=re.search(r'(\d{4}-\d{2}-\d{2})',str(path.parent))
    date=match.group(1) if match else ''
    heading=soup.find('h1')
    title=compact(heading.get_text(' ',strip=True)) if heading else ''
    paras=[p for p in soup.find_all('p',id=True) if re.match(r'^S\d',str(p.get('id') or ''))]
    questions=[];responses=[]
    def flush() -> None:
        if not responses:return
        key=responses[0][0]
        group=Group(key,date,title,[x[0] for x in questions],[x[0] for x in responses],len(questions)>1)
        out.groups[key]=group
        for role,items in [('question',questions),('response',responses)]:
            for ident,body,order in items:
                out.add_node(Node(ident,role,body,'',order,key))
    for order,para in enumerate(paras,1):
        ident=str(para.get('id') or '')
        body=compact(para.get_text(' ',strip=True))
        if not body:continue
        if question_start(body):
            if responses:flush();questions=[];responses=[]
            questions.append((ident,body,order))
        elif questions and not responses and re.match(r'^\(\d+\)\s+',body):
            questions.append((ident,body,order))
        elif questions or responses:responses.append((ident,body,order))
    flush()
    return out


def parse_mirror_xml(path: Path) -> Original:
    out=Original(adapter='parlparse_xml_mirror',omission_scope='mapped_groups_only_targeted_mirror')
    root=ET.parse(path).getroot();title='';q=[];r=[];order=0
    date_match=re.search(r'(\d{4}-\d{2}-\d{2})',path.name)
    date=date_match.group(1) if date_match else ''
    def flush() -> None:
        if not r:return
        seed=(q[0][4] if q else r[0][4])
        if not seed:return
        key='parlparse:'+re.sub(r'\.(?:q|r)\d+$','',seed)
        grp=Group(key,date,title,[x[0] for x in q if x[0]],[x[0] for x in r if x[0]],len(q)>1)
        out.groups[key]=grp
        for role,items in [('question',q),('response',r)]:
            for ident,text,speaker,ordno,_ in items:
                if ident:out.add_node(Node(ident,role,text,speaker,ordno,key))
    for el in root:
        if el.tag=='major-heading':
            flush();q=[];r=[];title='';continue
        if el.tag=='minor-heading':
            flush();q=[];r=[];title=compact(' '.join(el.itertext()));continue
        if el.tag not in ('ques','reply','speech'):continue
        if el.tag=='ques' and r:flush();q=[];r=[]
        role='question' if el.tag=='ques' else 'response'
        blocks=list(el) or [el]
        values=[]
        for ix,block in enumerate(blocks,1):
            text=compact(' '.join(block.itertext()))
            if block.tag=='table':
                table_rows=[]
                for tr in block.findall('.//tr'):
                    cells=[compact(' '.join(c.itertext())) for c in tr if c.tag in ('td','th')]
                    if any(cells):table_rows.append(' | '.join(c for c in cells if c))
                text=' || '.join(table_rows) or text
            if text:values.append((block.attrib.get('pid') or f'block:{ix}',text))
        if role=='question':
            if values:
                order+=1
                q.append((values[0][0],compact(' '.join(v for _,v in values)),compact(el.attrib.get('speakername')),order,el.attrib.get('id','')))
        else:
            for ident,text in values:
                order+=1
                r.append((ident,text,compact(el.attrib.get('speakername')),order,el.attrib.get('id','')))
    flush();return out


def html_text(value: str) -> str:
    return compact(BeautifulSoup(str(value or ''),'html.parser').get_text(' ',strip=True))


def html_blocks(value: str) -> list[str]:
    soup=BeautifulSoup(str(value or ''),'html.parser')
    blocks=[compact(x.get_text(' ',strip=True)) for x in soup.find_all(['p','li','blockquote'])]
    blocks=[x for x in blocks if x]
    return blocks or ([html_text(value)] if html_text(value) else [])


def parse_archive_detail_json(path: Path) -> Original:
    obj=json.loads(path.read_text(encoding='utf-8'))
    out=Original(adapter='archive_detail_json',omission_scope='mapped_detail_only')
    overview=obj.get('Overview') or {};key=str(overview.get('ExtId') or '')
    if not key:raise ValueError('Overview.ExtId absent')
    date=str(overview.get('Date') or '')[:10]
    grp=Group(key,date,compact(overview.get('Title')))
    for order,item in enumerate(obj.get('Items') or [],1):
        if item.get('ItemType')!='Contribution':continue
        soup=BeautifulSoup(str(item.get('Value') or ''),'html.parser')
        qtag=str(item.get('HRSTag') or '').lower() in ('question','err_question')
        qnode=soup.find(lambda tag:tag.name and tag.name.lower()=='questiontext') if qtag else None
        value=compact((qnode or soup).get_text(' ',strip=True))
        if not value:continue
        ident=str(item.get('ExternalId') or item.get('ItemId') or '')
        if not ident:continue
        isq=qtag or question_start(value)
        role='question' if isq else 'response'
        node=Node(ident,role,value,compact(item.get('AttributedTo')),order,key)
        out.add_node(node)
        (grp.question_keys if isq else grp.response_keys).append(ident)
    grp.explicit_joint=len(grp.question_keys)>1
    out.groups[key]=grp
    return out


def parse_archive_html(path: Path) -> Original:
    soup=BeautifulSoup(path.read_bytes(),'html.parser')
    out=Original(adapter='archive_html',omission_scope='mapped_groups_only_partial_archive')
    scope=soup.select_one('#maincontent1') or soup.select_one('#maincontent') or soup.select_one('#content-small') or soup.body
    if scope is None:raise ValueError('No readable archive body')
    m=re.search(r'(\d{4}-\d{2}-\d{2})',str(path.parent))
    date=m.group(1) if m else ''
    headings=scope.find_all('h3')
    order=0
    for heading in headings:
        title=compact(heading.get_text(' ',strip=True))
        qnodes=[];rnodes=[];group_index=0;reply_speaker=''
        def flush() -> None:
            nonlocal group_index
            if not rnodes:return
            qanchor=qnodes[0][0].key if qnodes else ''
            if not qanchor:
                group_index+=1
                return
            key=f'publications_hansard:{date}:{qanchor}:{group_index}'
            group_index+=1
            grp=Group(key,date,title,[x[0].key for x in qnodes],[x[0].key for x in rnodes],len(qnodes)>1)
            out.groups[key]=grp
            for node,aliases in qnodes+rnodes:
                out.add_node(Node(node.key,node.role,node.text,node.speaker,node.order,key),aliases)
        nodes=[]
        for sibling in heading.next_siblings:
            if getattr(sibling,'name',None)=='h3':break
            if getattr(sibling,'name',None) in ('p','table','ul','ol','blockquote'):nodes.append(sibling)
        for ix,el in enumerate(nodes):
            text=compact(el.get_text(' ',strip=True))
            if not text or re.match(r'^\d{1,2}\s+\w+\s+20\d{2}\s*:\s*Column\s+\w+$',text,flags=re.I):continue
            aliases=[str(a.get('name') or a.get('id')) for a in el.find_all('a') if a.get('name') or a.get('id')]
            canonical=next((a for a in aliases if re.search(r'_wqn\d+$',a,re.I)),None)
            canonical=canonical or next((a for a in aliases if re.match(r'^(?:qn|st|stpa|qnpa)_',a,re.I)),None)
            canonical=canonical or next((a for a in aliases if len(a)>=8),None) or f'node:{ix}'
            bold=el.find(['b','strong']) if el.name=='p' else None
            speaker=compact(bold.get_text(' ',strip=True)).rstrip(':') if bold else ''
            if speaker:text=re.sub('^'+re.escape(speaker)+r'\s*:\s*','',text,count=1,flags=re.I)
            isq=question_start(text) or any(re.match(r'^qn_\d+$',a,re.I) or re.search(r'_wqn\d+$',a,re.I) for a in aliases)
            continuation=bool(qnodes and not rnodes) and (bool(re.match(r'^\(\d+\)\s+',text)) or any(re.match(r'^qnpa_',a,re.I) for a in aliases))
            order+=1
            if isq:
                if rnodes:flush();qnodes=[];rnodes=[];reply_speaker=''
                qnodes.append((Node(canonical,'question',text,speaker,order,''),aliases))
            elif continuation:qnodes.append((Node(canonical,'question',text,speaker,order,''),aliases))
            else:
                if not qnodes and not rnodes and not speaker and el.name=='p':continue
                if speaker and not reply_speaker:reply_speaker=speaker
                rnodes.append((Node(canonical,'response',text,speaker or reply_speaker,order,''),aliases))
        flush()
    return out


def parse_modern_json(path: Path,genre: str) -> Original:
    obj=json.loads(path.read_text(encoding='utf-8'))
    out=Original(adapter='modern_list_json',omission_scope='mapped_selected_list_items_only')
    for index,result in enumerate(obj.get('results') or []):
        value=result.get('value') or {};ident=value.get('id')
        if ident is None:continue
        ident=str(ident)
        if genre=='ministerial_written_statement':
            key=f'written_statement:{ident}'
            date=str(value.get('dateMade') or '')[:10]
            grp=Group(key,date,compact(value.get('title')))
            for blockno,body in enumerate(html_blocks(value.get('text') or ''),1):
                nid=f'statement:{ident}:{blockno}'
                out.add_node(Node(nid,'response',body,compact(value.get('memberRole')),index*1000+blockno,key))
                grp.response_keys.append(nid)
        else:
            key=f'written_question:{ident}'
            date=str(value.get('dateAnswered') or '')[:10]
            grp=Group(key,date,compact(value.get('heading')),uin=str(value.get('uin') or ''),
                      grouped_uins=[str(x) for x in (value.get('groupedQuestions') or [])])
            qtext=html_text(value.get('questionText') or '')
            if qtext:
                nid=f'question:{ident}';out.add_node(Node(nid,'question',qtext,str(value.get('askingMemberId') or ''),index*2,key));grp.question_keys.append(nid)
            for blockno,body in enumerate(html_blocks(value.get('answerText') or ''),1):
                nid=f'answer:{ident}:{blockno}'
                out.add_node(Node(nid,'response',body,str(value.get('answeringMemberId') or ''),index*1000+blockno,key))
                grp.response_keys.append(nid)
        out.groups[key]=grp
    return out


def adapter_for(source_id: str,raw_path: str) -> str:
    p=raw_path.lower()
    if source_id=='src_549acfda11091ff8c9b8' and p.endswith('.zip'):return 'historic_xml_zip'
    if source_id=='src_549acfda11091ff8c9b8' and p.endswith(('.htm','.html')):return 'historic_item_html'
    if source_id=='src_9e8f487d372ed011db82':
        if p.endswith('.json'):return 'archive_detail_json'
        if p.endswith(('.htm','.html')):return 'archive_html'
    if source_id=='src_90b3a872375c9e7fd267' and p.endswith('.json'):return 'modern_list_json'
    if source_id=='src_3c349b00120866c263a3' and p.endswith('.xml'):return 'parlparse_xml_mirror'
    return 'unsupported'


def parse_original(path: Path,adapter: str,genre: str) -> Original:
    if adapter=='historic_xml_zip':return parse_historic_zip(path)
    if adapter=='historic_item_html':return parse_historic_item_html(path)
    if adapter=='parlparse_xml_mirror':return parse_mirror_xml(path)
    if adapter=='archive_detail_json':return parse_archive_detail_json(path)
    if adapter=='archive_html':return parse_archive_html(path)
    if adapter=='modern_list_json':return parse_modern_json(path,genre)
    raise ValueError('unsupported adapter')


def locator_parts(locator: str) -> tuple[str,str,str]:
    fields=dict(x.split('=',1) for x in str(locator or '').split(';') if '=' in x)
    return fields.get('role',''),fields.get('source_id',''),fields.get('speaker','')


def validate_unkeyed_historic(parent: Parent,original: Original) -> dict[str,Any] | None:
    if not parent.external_id.startswith('historic_'):return None
    roles=defaultdict(list)
    for seg in sorted(parent.segments.values(),key=lambda x:(x.order if x.order is not None else 10**10,x.segment_id)):
        role,_,_=locator_parts(seg.locator)
        if role in ('question_context','government_response'):roles[role].append(seg)
    sig=(tuple(compact(x.text).casefold() for x in roles['question_context']),
         tuple(compact(x.text).casefold() for x in roles['government_response']))
    candidates=original.signatures.get(sig,[])
    if len(candidates)!=1:return None
    key=candidates[0];group=original.groups[key]
    remapped=Parent(parent.source_id,parent.document_id,key,parent.date,parent.genre,parent.object_id,
                    parent.version_id,parent.raw_path,parent.mime,parent.normalized_version_count)
    for role,nodes in [('question_context',group.question_keys),('government_response',group.response_keys)]:
        for seg,node_key in zip(roles[role],nodes):
            old_role,old_id,speaker=locator_parts(seg.locator)
            remapped.segments[seg.segment_id]=Segment(seg.segment_id,
                f'role={old_role};source_id={node_key};speaker={speaker}',seg.text,seg.order,seg.version_id,seg.actor)
    result=validate_parent(remapped,original)
    result['external_id']=parent.external_id
    result['stored_question_ids']=';'.join(locator_parts(x.locator)[1] for x in roles['question_context'])
    result['stored_response_ids']=';'.join(locator_parts(x.locator)[1] for x in roles['government_response'])
    result['rule_ids']+=';R-TEXT-UNIT'
    result['details']+=' | Unique exact question/reply text maps to saved XML group; hashed parent ID not independently reproduced.'
    return result


def validate_parent(parent: Parent,original: Original | None,parse_error: str='') -> dict[str,Any]:
    adapter=adapter_for(parent.source_id,parent.raw_path)
    base={'source_id':parent.source_id,'adapter':adapter,'document_id':parent.document_id,
          'external_id':parent.external_id,'publication_date':parent.date,'content_type':parent.genre,
          'content_object_id':parent.object_id,'content_version_id':parent.version_id,'raw_path':parent.raw_path,
          'original_group_id':'','answer_group_key':'','original_question_ids':'','original_response_ids':'',
          'stored_question_ids':'','stored_response_ids':'','original_reply_nodes':0,
          'matched_reply_nodes':0,'segment_count':len(parent.segments),'matched_segments':0,
          'status':'insufficient_evidence','rule_ids':'','evidence_locator':'','details':''}
    issues=[];rules=[];severe=False;unresolved=False
    if original is None:
        base.update(rule_ids='R-ORIGINAL',details=parse_error or 'No checkable saved original',evidence_locator=parent.raw_path)
        return base
    grp=original.groups.get(parent.external_id)
    if grp is None:
        text_match=validate_unkeyed_historic(parent,original) if original.adapter=='historic_xml_zip' else None
        if text_match is not None:return text_match
        if original.adapter=='historic_xml_zip' and parent.external_id.startswith('historic_'):
            base.update(status='insufficient_evidence',rule_ids='R-TEXT-UNIT',
                details='Unkeyed original group could not be matched uniquely by exact question/reply text',
                evidence_locator=parent.raw_path+'#unkeyed-group')
            return base
        base.update(status='boundary_conflict',rule_ids='R-UNIT',details='Stored parent ID does not match a parsed original reply group',evidence_locator=parent.external_id)
        return base
    base['original_group_id']=grp.key;base['answer_group_key']=grp.key
    base['original_question_ids']=';'.join(grp.question_keys)
    base['original_response_ids']=';'.join(grp.response_keys)
    base['original_reply_nodes']=len(grp.response_keys)
    base['evidence_locator']=parent.raw_path+'#'+grp.key
    if grp.date and parent.date and grp.date!=parent.date:
        severe=True;rules.append('R-DATE');issues.append(f'original date {grp.date} != stored {parent.date}')
    if parent.normalized_version_count>1:
        rules.append('R-VERSION');issues.append(f'{parent.normalized_version_count} normalized metadata versions; not extra parent')
    matched=0;response_nodes=[];question_nodes=[];orders=[]
    for seg in parent.segments.values():
        role,source_id,speaker=locator_parts(seg.locator)
        if role=='government_response':response_nodes.append(source_id)
        elif role=='question_context':question_nodes.append(source_id)
        if seg.version_id and parent.version_id and seg.version_id!=parent.version_id:
            severe=True;rules.append('R-MAPPING');issues.append('segment content_version_id differs from parent link')
        if not source_id:
            unresolved=True;rules.append('R-LOCATOR');issues.append('segment lacks source_id locator');continue
        node=original.get_node(source_id,grp.key)
        if node is None:
            # Exact source locator absent from a successfully parsed original.
            severe=True;rules.append('R-LOCATOR');issues.append('source node absent: '+source_id);continue
        if (role=='government_response' and node.role!='response') or (role=='question_context' and node.role!='question'):
            severe=True;rules.append('R-ROLE');issues.append('source role mismatch: '+source_id)
        if node.role=='response' and node.group_key!=grp.key:
            severe=True;rules.append('R-BOUNDARY');issues.append('reply node belongs to another original group: '+source_id)
        assessment=compare_text(seg.text,node.text)
        if assessment in ('truncated','leakage','mismatch'):
            severe=True;rules.append('R-SPAN');issues.append(assessment+' source span: '+source_id)
        elif assessment=='insufficient':
            unresolved=True;rules.append('R-SPAN');issues.append('text alignment unresolved: '+source_id)
        if (speaker and node.speaker and not re.match(r'^(?:member_id=)?\d+$',node.speaker)
            and compact(speaker).casefold()!=compact(node.speaker).casefold()):
            unresolved=True;rules.append('R-SPEAKER');issues.append('speaker differs at '+source_id)
        if assessment=='match':matched+=1
        if seg.order is not None:orders.append((node.role,seg.order,node.order))
    base['stored_question_ids']=';'.join(dict.fromkeys(question_nodes))
    base['stored_response_ids']=';'.join(dict.fromkeys(response_nodes))
    base['matched_segments']=matched
    matched_reply={original.get_node(k,grp.key).key for k in response_nodes if original.get_node(k,grp.key) is not None}
    required={original.get_node(k,grp.key).key for k in grp.response_keys if original.get_node(k,grp.key) is not None}
    base['matched_reply_nodes']=len(matched_reply & required)
    if required and required-matched_reply:
        severe=True;rules.append('R-OMISSION');issues.append('original reply node missing in stored child spans: '+','.join(sorted(required-matched_reply)[:4]))
    elif not required:
        unresolved=True;rules.append('R-ORIGINAL');issues.append('original group has no addressable reply node')
    for role in ('question','response'):
        seen=[b for _,a,b in sorted((x for x in orders if x[0]==role),key=lambda x:x[1])]
        if any(x>y for x,y in zip(seen,seen[1:])):
            unresolved=True;rules.append('R-ORDER');issues.append(role+' segment order differs from original node order')
    if not parent.segments:
        severe=True;rules.append('R-MAPPING');issues.append('no linked question/reply child segments')
    base['status']='boundary_conflict' if severe else 'insufficient_evidence' if unresolved else 'supported_split'
    base['rule_ids']=';'.join(dict.fromkeys(rules or ['R-UNIT','R-SPAN','R-MAPPING']))
    base['details']=' | '.join(dict.fromkeys(issues))[:1400] or 'Original unit, linked response spans and stored child text align under named checks.'
    return base


def mark_duplicate_imports(rows: list[dict[str,Any]],parents: dict[str,Parent],original: Original | None) -> None:
    if original is None:return
    owners=defaultdict(set)
    for pid,parent in parents.items():
        for seg in parent.segments.values():
            role,sid,_=locator_parts(seg.locator)
            if role!='government_response':continue
            node=original.get_node(sid,parent.external_id)
            if node:owners[(node.group_key,node.key,node.order)].add(pid)
    for node_id,pids in owners.items():
        if len(pids)<2:continue
        for row in rows:
            if row['document_id'] in pids:
                row['status']='duplicate_import'
                row['rule_ids']=(row['rule_ids']+';R-DUPLICATE').strip(';')
                row['details']=(row['details']+' | Same original reply node '+node_id[1]+' mapped to '+str(len(pids))+' parent IDs')[:1400]
                row['evidence_locator']=row['raw_path']+'#'+node_id[1]


def write_row(writer: csv.DictWriter,row: dict[str,Any]) -> None:
    writer.writerow({k:row.get(k,'') for k in writer.fieldnames})


def input_rows(con: duckdb.DuckDBPyConnection,target_keys: list[tuple[str,str,str]] | None = None) -> Iterator[tuple]:
    ids=','.join("'"+x+"'" for x in SOURCES)
    target_join=''
    if target_keys is not None:
        con.execute('CREATE TEMP TABLE target_keys (source_id VARCHAR, raw_path VARCHAR, content_version_id VARCHAR)')
        con.executemany('INSERT INTO target_keys VALUES (?,?,?)',target_keys)
        target_join='JOIN target_keys t ON t.source_id=d.source_id AND t.raw_path=v.raw_path AND t.content_version_id=v.content_version_id'
    sql=f"""
      WITH dv AS (SELECT document_id,count(*) n FROM document_versions GROUP BY 1)
      SELECT d.source_id,d.document_id,d.external_id,cast(d.publication_date AS varchar),d.content_type,
             x.content_object_id,v.content_version_id,v.raw_path,v.mime_type,coalesce(dv.n,0),
             va.segment_id,va.actor_name,s.locator,s.segment_text,s.segment_order,s.content_version_id
      FROM documents d
      LEFT JOIN document_content_objects x USING(document_id)
      LEFT JOIN content_versions v USING(content_object_id)
      LEFT JOIN dv USING(document_id)
      LEFT JOIN voice_attributions va USING(document_id)
      LEFT JOIN text_segments s USING(segment_id)
      {target_join}
      WHERE d.source_id IN ({ids}) AND d.content_type IN ('ministerial_written_answer','ministerial_written_statement')
      ORDER BY d.source_id,coalesce(v.raw_path,''),coalesce(v.content_version_id,''),d.document_id,s.segment_order,va.segment_id
    """
    cur=con.execute(sql)
    while True:
        batch=cur.fetchmany(5000)
        if not batch:break
        for row in batch:yield row


def acquire_lock(path: Path,log: list[dict[str,Any]],phase: str):
    path.parent.mkdir(parents=True,exist_ok=True)
    handle=path.open('a+')
    start=time.monotonic();wait_log=time.monotonic()
    while True:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);break
        except BlockingIOError:
            if time.monotonic()-wait_log>=20:
                print('Waiting for shared heavy I/O lock...',file=sys.stderr,flush=True);wait_log=time.monotonic()
            time.sleep(2)
    entry={'phase':phase,'acquired_utc':now(),'wait_seconds':round(time.monotonic()-start,3),'_start_monotonic':time.monotonic()}
    log.append(entry)
    return handle,entry


def release_lock(handle,entry):
    entry['held_seconds']=round(time.monotonic()-entry.pop('_start_monotonic'),3)
    entry['released_utc']=now()
    fcntl.flock(handle,fcntl.LOCK_UN);handle.close()


def run(root: Path,outdir: Path) -> None:
    outdir.mkdir(parents=True,exist_ok=True)
    db=root/DB_REL;lk=root/LOCK_REL
    checkpoint={'path':DB_REL,'mtime_utc':datetime.fromtimestamp(db.stat().st_mtime,timezone.utc).isoformat(),
                'bytes':db.stat().st_size}
    counters=defaultdict(Counter);locks=[];containers=0;parents_seen=set();modern_meta=[]
    parent_tmp=outdir/'parent_results.initial.csv'
    raw_start=time.monotonic()
    with parent_tmp.open('w',newline='',encoding='utf-8') as pf,(outdir/'container_results.csv').open('w',newline='',encoding='utf-8') as cf,(outdir/'exceptions.csv').open('w',newline='',encoding='utf-8') as ef:
        pw=csv.DictWriter(pf,fieldnames=PARENT_FIELDS);pw.writeheader()
        cw=csv.DictWriter(cf,fieldnames=CONTAINER_FIELDS);cw.writeheader()
        ew=csv.DictWriter(ef,fieldnames=EXCEPTION_FIELDS);ew.writeheader()
        handle,entry=acquire_lock(lk,locks,'single_db_inventory_and_saved_original_pass')
        try:
            con=duckdb.connect(str(db),read_only=True)
            group_key=None;group_parents={};last_progress=time.monotonic()
            def flush() -> None:
                nonlocal containers,group_parents,last_progress
                if group_key is None:return
                source,raw_path,vid=group_key
                adapter=adapter_for(source,raw_path or '')
                original=None;error='';path=None
                if raw_path:
                    path=(root/raw_path).resolve()
                    if not path.is_relative_to(root.resolve()):error='Raw path escapes repository'
                    elif not path.exists():error='Saved original file absent'
                    elif adapter=='unsupported':error='No source adapter for saved format'
                    else:
                        try:original=parse_original(path,adapter,next(iter(group_parents.values())).genre)
                        except Exception as exc:error=f'{type(exc).__name__}: {str(exc)[:260]}'
                else:error='No linked content version/raw path'
                rows=[validate_parent(p,original,error) for p in group_parents.values()]
                mark_duplicate_imports(rows,group_parents,original)
                mapped=len([r for r in rows if r['original_group_id']])
                expected={k for k in original.groups if not k.startswith('no_id:')} if original else set()
                imported={r['original_group_id'] for r in rows if r['original_group_id']}
                omitted=sorted(expected-imported) if original and original.omission_scope=='approved_department_groups_in_saved_volume' else []
                if original and original.adapter=='modern_list_json':
                    for p in group_parents.values():
                        g=original.groups.get(p.external_id)
                        if g and p.genre=='ministerial_written_answer':
                            answer=original.get_node(g.response_keys[0]).text if g.response_keys else ''
                            modern_meta.append((p.document_id,g.uin,g.grouped_uins,compact(answer).casefold()))
                for row in rows:
                    write_row(pw,row)
                    counters[source]['parents']+=1;counters[source][row['status']]+=1
                    if row['document_id'] in parents_seen:
                        write_row(ew,{'unit':'parent','source_id':source,'adapter':adapter,'document_id':row['document_id'],
                                     'external_id':row['external_id'],'raw_path':raw_path,'status':'duplicate_import',
                                     'rule_ids':'R-PARENT-LINK','evidence_locator':raw_path,
                                     'details':'Same parent linked to multiple container/version groups',
                                     'minimal_action':'Reconcile parent-object/version links; preserve raw versions.'})
                    parents_seen.add(row['document_id'])
                    if row['status'] not in ('supported_split','legitimate_shared_span'):
                        write_row(ew,{'unit':'parent','source_id':source,'adapter':adapter,
                            'document_id':row['document_id'],'external_id':row['external_id'],'raw_path':raw_path,
                            'status':row['status'],'rule_ids':row['rule_ids'],'evidence_locator':row['evidence_locator'],
                            'details':row['details'],'minimal_action':'Inspect named original node and parent/segment mapping; repair only supported defect.'})
                cstatus='insufficient_evidence' if original is None else 'boundary_conflict' if any(r['status'] in ('boundary_conflict','duplicate_import') for r in rows) else 'needs_review' if omitted else 'supported_split' if all(r['status'] in ('supported_split','legitimate_shared_span') for r in rows) else 'insufficient_evidence'
                crow={'source_id':source,'adapter':adapter,'raw_path':raw_path,'content_version_id':vid,
                    'imported_parent_count':len(group_parents),'original_group_count':len(original.groups) if original else '',
                    'original_node_count':len(original.nodes) if original else '',
                    'mapped_parent_count':mapped,'supported_parents':sum(r['status']=='supported_split' for r in rows),
                    'shared_parents':sum(r['status']=='legitimate_shared_span' for r in rows),
                    'duplicate_parents':sum(r['status']=='duplicate_import' for r in rows),
                    'boundary_conflicts':sum(r['status']=='boundary_conflict' for r in rows),
                    'insufficient_parents':sum(r['status']=='insufficient_evidence' for r in rows),
                    'omitted_candidate_groups':len(omitted),'status':cstatus,
                    'rule_ids':'R-ORIGINAL' if original is None else 'R-OMISSION' if omitted else 'R-UNIT;R-SPAN;R-MAPPING',
                    'evidence_locator':raw_path,'details':error or (original.omission_scope if original else '')}
                write_row(cw,crow);containers+=1;counters[source]['containers']+=1
                counters[source]['original_containers_read']+=bool(original)
                counters[source]['omitted_candidate_groups']+=len(omitted)
                if omitted:
                    for key in omitted:
                        g=original.groups[key]
                        write_row(ew,{'unit':'original_group','source_id':source,'adapter':adapter,'raw_path':raw_path,
                            'status':'needs_review','rule_ids':'R-OMISSION','evidence_locator':raw_path+'#'+key,
                            'details':f'Eligible department/date original reply group has no parent in this linked container; date={g.date}; title={g.title[:100]}',
                            'minimal_action':'Check overlap and prior exclusion ledger before any missing-parent repair.'})
                if time.monotonic()-last_progress>20:
                    print(f'processed {containers:,} containers / {len(parents_seen):,} parents; current {adapter}',file=sys.stderr,flush=True)
                    last_progress=time.monotonic()
                group_parents={}
            for row in input_rows(con):
                sid,pid,ext,date,genre,oid,vid,path,mime,nver,segid,actor,loc,text,segorder,segvid=row
                key=(sid,path or '',vid or '')
                if group_key is not None and key!=group_key:flush()
                group_key=key
                if pid not in group_parents:
                    group_parents[pid]=Parent(sid,pid,ext or '',date or '',genre or '',oid or '',vid or '',path or '',mime or '',int(nver or 0))
                parent=group_parents[pid]
                if segid and segid not in parent.segments:
                    parent.segments[segid]=Segment(segid,loc or '',text or '',int(segorder) if segorder is not None else None,segvid or '',actor or '')
            flush();con.close()
        finally:release_lock(handle,entry)
    # Derive explicit joint-answer groups after all list pages are read. A
    # response repeated under a source-declared groupedQuestions edge is one
    # answer group, whereas equal wording without that edge remains distinct.
    group_lookup={};by_uin=defaultdict(list)
    for pid,uin,linked,answer in modern_meta:
        if uin:by_uin[uin].append((pid,linked,answer))
    parent_union={u:u for u in by_uin}
    def find(u):
        while parent_union[u]!=u:
            parent_union[u]=parent_union[parent_union[u]];u=parent_union[u]
        return u
    for u,items in by_uin.items():
        for _,linked,_ in items:
            for v in linked:
                if v in parent_union:
                    a,b=find(u),find(v)
                    if a!=b:parent_union[max(a,b)]=min(a,b)
    clusters=defaultdict(list)
    for u,items in by_uin.items():
        for pid,linked,answer in items:clusters[find(u)].append((pid,u,answer))
    with (outdir/'answer_groups.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['answer_group_key','parent_count','question_uins','distinct_answer_texts','classification'])
        for key,items in sorted(clusters.items()):
            uniq={x[0] for x in items};texts={x[2] for x in items if x[2]}
            classif='legitimate_shared_span' if len(uniq)>1 and len(texts)==1 else 'different_text_or_incomplete' if len(uniq)>1 else 'single_question'
            w.writerow([key,len(uniq),';'.join(sorted({x[1] for x in items})),len(texts),classif])
            for pid,_,_ in items:group_lookup[pid]=(key,len(uniq),classif)
    with parent_tmp.open(newline='',encoding='utf-8') as src,(outdir/'parent_results.csv').open('w',newline='',encoding='utf-8') as dst:
        reader=csv.DictReader(src);writer=csv.DictWriter(dst,fieldnames=PARENT_FIELDS);writer.writeheader()
        for row in reader:
            if row['document_id'] in group_lookup:
                key,n,classification=group_lookup[row['document_id']]
                row['answer_group_key']='modern_uin:'+key
                if classification=='legitimate_shared_span' and row['status']=='supported_split':
                    row['status']='legitimate_shared_span';row['rule_ids']+=';R-JOINT'
                    row['details']='Explicit groupedQuestions relation; identical original answer text shared across '+str(n)+' question parents.'
            writer.writerow(row)
    parent_tmp.unlink()
    # Coverage is computed from final parent rows, after joint-answer status.
    final=defaultdict(Counter)
    final_containers=defaultdict(Counter)
    with (outdir/'parent_results.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            final[row['source_id']][row['status']]+=1
            final_containers[(row['source_id'],row['raw_path'],row['content_version_id'])][row['status']]+=1
    container_tmp=outdir/'container_results.initial.csv'
    (outdir/'container_results.csv').rename(container_tmp)
    with container_tmp.open(newline='',encoding='utf-8') as src,(outdir/'container_results.csv').open('w',newline='',encoding='utf-8') as dst:
        reader=csv.DictReader(src);writer=csv.DictWriter(dst,fieldnames=CONTAINER_FIELDS);writer.writeheader()
        for row in reader:
            counts=final_containers[(row['source_id'],row['raw_path'],row['content_version_id'])]
            row['supported_parents']=counts['supported_split']
            row['shared_parents']=counts['legitimate_shared_span']
            row['duplicate_parents']=counts['duplicate_import']
            row['boundary_conflicts']=counts['boundary_conflict']
            row['insufficient_parents']=counts['insufficient_evidence']
            writer.writerow(row)
    container_tmp.unlink()
    with (outdir/'execution_coverage.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['source_id','adapter','inventory_parents','inventory_containers','original_containers_read',
                'supported_split','legitimate_shared_span','duplicate_import','boundary_conflict','insufficient_evidence',
                'omitted_candidate_groups','original_verification_scope']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for source in SOURCES:
            z=counters[source];v=final[source]
            w.writerow({'source_id':source,'adapter':SOURCES[source],'inventory_parents':z['parents'],
                'inventory_containers':z['containers'],'original_containers_read':z['original_containers_read'],
                'supported_split':v['supported_split'],'legitimate_shared_span':v['legitimate_shared_span'],
                'duplicate_import':v['duplicate_import'],'boundary_conflict':v['boundary_conflict'],
                'insufficient_evidence':v['insufficient_evidence'],'omitted_candidate_groups':z['omitted_candidate_groups'],
                'original_verification_scope':'mapped parent/node text + approved department omitted-candidate inventory' if source=='src_549acfda11091ff8c9b8' else 'mapped selected parents/nodes; no all-source omission claim'})
    manifest={'generated_utc':now(),'publication_interval_inclusive':[START,END],'db_checkpoint':checkpoint,
              'source_ids':SOURCES,'query_scope':'all registered UK ministerial_written_answer/statement parents in UK 06, joined once to content versions and voice-attributed child segments; no topic filter',
              'raw_check':'saved ZIP XML, JSON list/detail, HTML archive and ParlParse XML read once per mapped container; no HTTP or full raw-file hashing',
              'lock_path':LOCK_REL,'lock_holds':locks,'elapsed_seconds':round(time.monotonic()-raw_start,2),
              'cross_source_mirror_candidates':'work_packages/M1_source_access/13_parallel_data_audit_20261004/02_distribution/cross_source_title_date_candidates.csv (83 mirror parents / 138 title-date pairs; candidate identity only)'}
    (outdir/'INPUT_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'containers':containers,'parents':len(parents_seen),'seconds':manifest['elapsed_seconds'],'coverage':{k:dict(v) for k,v in final.items()}},indent=2),flush=True)


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    rp=sub.add_parser('run',help='One read-only inventory and saved-original validation run')
    rp.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    rp.add_argument('--output',type=Path,default=HERE)
    args=ap.parse_args()
    if args.command=='run':run(args.root.resolve(),args.output.resolve())


if __name__=='__main__':main()
