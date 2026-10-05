#!/usr/bin/env python3
"""Focused falsification fixtures for the read-only archive split checks."""
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import validate_archive_splits as v


class SplitChecks(unittest.TestCase):
    def parent(self, external, segments, source='src_90b3a872375c9e7fd267',date='2014-10-13'):
        p=v.Parent(source,'doc:'+external,external,date,'ministerial_written_answer',
                   'object:1','version:1','saved.json','application/json',1)
        for i,(role,key,text) in enumerate(segments):
            p.segments[str(i)]=v.Segment(str(i),f'role={role};source_id={key}',text,i,'version:1','')
        return p

    def test_modern_reply_blocks_and_missing_block(self):
        payload={'results':[{'value':{'id':7,'uin':'A7','dateAnswered':'2014-10-13',
            'questionText':'To ask about energy.',
            'answerText':'<p>First complete reply.</p><p>Second complete reply.</p>',
            'groupedQuestions':[]}}]}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'page.json';path.write_text(json.dumps(payload))
            original=v.parse_modern_json(path,'ministerial_written_answer')
        self.assertEqual(original.groups['written_question:7'].response_keys,['answer:7:1','answer:7:2'])
        complete=self.parent('written_question:7',[
            ('question_context','question:7','To ask about energy.'),
            ('government_response','answer:7:1','First complete reply.'),
            ('government_response','answer:7:2','Second complete reply.')])
        self.assertEqual(v.validate_parent(complete,original)['status'],'supported_split')
        complete.segments.pop('2')
        broken=v.validate_parent(complete,original)
        self.assertEqual(broken['status'],'boundary_conflict')
        self.assertIn('R-OMISSION',broken['rule_ids'])

    def test_cross_group_reply_is_boundary_conflict(self):
        o=v.Original('fixture')
        for key in ('written_question:1','written_question:2'):
            rid='answer:'+key[-1]+':1'
            o.groups[key]=v.Group(key,'2014-10-13','',[],[rid])
            o.add_node(v.Node(rid,'response','Reply '+key[-1],'',1,key))
        p=self.parent('written_question:1',[('government_response','answer:2:1','Reply 2')])
        result=v.validate_parent(p,o)
        self.assertEqual(result['status'],'boundary_conflict')
        self.assertIn('R-BOUNDARY',result['rule_ids'])

    def test_detail_interleaved_questions_and_replies(self):
        detail={'Overview':{'ExtId':'item-1','Date':'2005-01-11'},'Items':[
            {'ItemType':'Contribution','ExternalId':'q1','Value':'To ask first?'},
            {'ItemType':'Contribution','ExternalId':'r1','Value':'First reply.'},
            {'ItemType':'Contribution','ExternalId':'q2','Value':'To ask second?'},
            {'ItemType':'Contribution','ExternalId':'r2','Value':'Second reply.'}]}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'detail.json';path.write_text(json.dumps(detail))
            o=v.parse_archive_detail_json(path)
        self.assertEqual(o.groups['item-1'].question_keys,['q1','q2'])
        self.assertEqual(o.groups['item-1'].response_keys,['r1','r2'])
        p=self.parent('item-1',[(r,k,t) for r,k,t in [
            ('question_context','q1','To ask first?'),('question_context','q2','To ask second?'),
            ('government_response','r1','First reply.'),('government_response','r2','Second reply.')]],
            source='src_9e8f487d372ed011db82',date='2005-01-11')
        self.assertEqual(v.validate_parent(p,o)['status'],'supported_split')

    def test_mirror_two_answers_under_one_heading(self):
        xml='''<publicwhip><minor-heading id="base.h">Topic</minor-heading>
        <ques id="base.q0"><p pid="q0">To ask first?</p></ques>
        <reply id="base.r0"><p pid="r0">First.</p></reply>
        <ques id="other.q0"><p pid="q1">To ask second?</p></ques>
        <reply id="other.r0"><p pid="r1">Second.</p></reply></publicwhip>'''
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'answers2012-01-01.xml';path.write_text(xml)
            o=v.parse_mirror_xml(path)
        self.assertEqual(len(o.groups),2)
        self.assertEqual(o.groups['parlparse:base'].response_keys,['r0'])
        self.assertEqual(o.groups['parlparse:other'].response_keys,['r1'])

    def test_duplicate_reply_node_flagged(self):
        o=v.Original('fixture')
        o.groups['one']=v.Group('one','2014-10-13','',[],['shared'])
        o.add_node(v.Node('shared','response','Shared reply','',1,'one'))
        p1=self.parent('one',[('government_response','shared','Shared reply')])
        p2=self.parent('two',[('government_response','shared','Shared reply')])
        rows=[v.validate_parent(p1,o),v.validate_parent(p2,o)]
        v.mark_duplicate_imports(rows,{p1.document_id:p1,p2.document_id:p2},o)
        self.assertEqual([x['status'] for x in rows],['duplicate_import','duplicate_import'])

    def test_archive_html_groups_response_continuations(self):
        markup='''<html><div id="content-small"><h3>Energy</h3>
        <p><a name="page_wqn0"></a><b>A:</b> To ask about energy?</p>
        <p><a name="st_1"></a><b>Minister:</b> First reply block.</p>
        <p><a name="stpa_1"></a>Second reply block.</p>
        <p><a name="page_wqn1"></a><b>B:</b> To ask again?</p>
        <p><a name="st_2"></a><b>Minister:</b> Another reply.</p>
        </div></html>'''
        with tempfile.TemporaryDirectory() as d:
            day=Path(d)/'2013-05-15';day.mkdir()
            path=day/'page.htm';path.write_text(markup)
            o=v.parse_archive_html(path)
        first=o.groups['publications_hansard:2013-05-15:page_wqn0:0']
        second=o.groups['publications_hansard:2013-05-15:page_wqn1:1']
        self.assertEqual(first.response_keys,['st_1','stpa_1'])
        self.assertEqual(second.response_keys,['st_2'])

    def test_unkeyed_historic_group_requires_unique_exact_text(self):
        o=v.Original('historic_xml_zip')
        g=v.Group('no_id:volume.xml:1','1998-01-20','Topic',['q'],['r'])
        o.groups[g.key]=g
        o.add_node(v.Node('q','question','To ask about energy.','',1,g.key))
        o.add_node(v.Node('r','response','The reply is complete.','',2,g.key))
        signature=(('to ask about energy.',),('the reply is complete.',))
        o.signatures[signature].append(g.key)
        p=self.parent('historic_abc',[
            ('question_context','100','To ask about energy.'),
            ('government_response','101','The reply is complete.')],
            source='src_549acfda11091ff8c9b8',date='1998-01-20')
        self.assertEqual(v.validate_parent(p,o)['status'],'supported_split')
        o.signatures[signature].append('no_id:volume.xml:2')
        self.assertEqual(v.validate_parent(p,o)['status'],'insufficient_evidence')

    def test_historic_single_day_and_range_heading_dates(self):
        single=ET.fromstring('<date format="1900-12-11">Tuesday 11 December 1990</date>')
        period=ET.fromstring('<date format="2003-05-23">The following answers were received between 23 May and 2 June 2003</date>')
        punctuation=ET.fromstring('<date format="1991-04-14">Friday 14 June, 1991</date>')
        self.assertEqual(v.visible_historic_date(single),'1990-12-11')
        self.assertEqual(v.visible_historic_date(period),'2003-05-23')
        self.assertEqual(v.visible_historic_date(punctuation),'1991-06-14')

    def test_historic_item_html_keeps_two_reply_parents(self):
        markup='''<html><h1>Energy</h1><p id="S6X-1">To ask first?</p>
        <p id="S6X-2">First reply.</p><p id="S6X-3">Continuation.</p>
        <p id="S6X-4">To ask again?</p><p id="S6X-5">Second reply.</p></html>'''
        with tempfile.TemporaryDirectory() as d:
            day=Path(d)/'1991-12-02';day.mkdir()
            path=day/'item.html';path.write_text(markup)
            o=v.parse_historic_item_html(path)
        self.assertEqual(o.groups['S6X-2'].response_keys,['S6X-2','S6X-3'])
        self.assertEqual(o.groups['S6X-5'].response_keys,['S6X-5'])

    def test_historic_item_numbered_question_continuation(self):
        markup='''<html><p id="S6X-1">To ask the minister (1) the count;</p>
        <p id="S6X-2">(2) the policy.</p><p id="S6X-3">The answer.</p></html>'''
        with tempfile.TemporaryDirectory() as d:
            day=Path(d)/'1991-12-02';day.mkdir()
            path=day/'item.html';path.write_text(markup)
            o=v.parse_historic_item_html(path)
        self.assertEqual(o.groups['S6X-3'].question_keys,['S6X-1','S6X-2'])
        self.assertEqual(o.groups['S6X-3'].response_keys,['S6X-3'])


if __name__=='__main__':unittest.main()
