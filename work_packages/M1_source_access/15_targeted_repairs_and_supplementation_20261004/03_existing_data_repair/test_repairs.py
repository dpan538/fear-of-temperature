#!/usr/bin/env python3
"""Falsification fixtures for boundaries, source roles, layer rollback and identity."""
import json
import tempfile
import unittest
from pathlib import Path
import duckdb
import repair_cli as r

class Repairs(unittest.TestCase):
    def saved(self, name, body):
        # Parsers require repository-contained evidence locators.
        self.addCleanup(lambda: self.tmp.cleanup())
        self.tmp=tempfile.TemporaryDirectory(dir=r.HERE)
        p=Path(self.tmp.name)/name;p.write_text(body);return p

    def test_err_question_and_numbered_continuation_are_not_reply(self):
        p=self.saved('detail.json',json.dumps({'Overview':{'ExtId':'one','Date':'2006-06-05'},'Items':[
            {'ItemType':'Contribution','ItemId':1,'HRSTag':'Question','AttributedTo':'MP','Value':'<QuestionText>To ask (1) about policy?</QuestionText>'},
            {'ItemType':'Contribution','ItemId':2,'HRSTag':'ERR_Question','Value':'(2) what is the timetable?'},
            {'ItemType':'Contribution','ItemId':3,'HRSTag':'hs_Para','AttributedTo':'Minister','Value':'The reply.<span class="column-number">99WA</span>'}]}))
        ns=r.archive_nodes(p)['one']['nodes']
        self.assertEqual([n['role'] for n in ns],['question','question','response'])
        self.assertEqual(ns[1]['speaker'],'MP')
        self.assertIn('inherited',ns[1]['role_basis'])
        self.assertEqual(ns[2]['text'],'The reply.')

    def test_interleaved_detail_keeps_each_explicit_question(self):
        p=self.saved('detail.json',json.dumps({'Overview':{'ExtId':'one','Date':'2006-06-05'},'Items':[
            {'ItemType':'Contribution','ItemId':1,'Value':'To ask first?'},
            {'ItemType':'Contribution','ItemId':2,'AttributedTo':'Minister','Value':'First response.'},
            {'ItemType':'Contribution','ItemId':3,'HRSTag':'Question','Value':'To ask second?'},
            {'ItemType':'Contribution','ItemId':4,'AttributedTo':'Minister','Value':'Second response.'}]}))
        self.assertEqual([n['role'] for n in r.archive_nodes(p)['one']['nodes']],['question','response','question','response'])

    def test_question_number_at_start_of_reply_not_reclassified_after_answer(self):
        p=self.saved('detail.json',json.dumps({'Overview':{'ExtId':'one','Date':'2006-06-05'},'Items':[
            {'ItemType':'Contribution','ItemId':1,'HRSTag':'Question','Value':'To ask what happened?'},
            {'ItemType':'Contribution','ItemId':2,'AttributedTo':'Minister','Value':'The first reply.'},
            {'ItemType':'Contribution','ItemId':3,'Value':'(2) The second point is answered here.'}]}))
        self.assertEqual(r.archive_nodes(p)['one']['nodes'][-1]['role'],'response')

    def test_html_separate_reply_continuations_and_next_group(self):
        p=self.saved('item.html','''<h1>Topic</h1><cite class="section">HC Deb 02 December 1991 vol 200</cite>
          <div class="member_contribution" id="S1"><blockquote class="contribution_text"><cite class="member">MP</cite><p id="q1">To ask first?</p><p id="q1b">(2) and the details?</p></blockquote></div>
          <div class="member_contribution" id="S2"><blockquote class="contribution_text"><cite class="member">Minister</cite><p id="r1">First answer.</p><p id="r2">Continuation.</p></blockquote></div>
          <div class="member_contribution" id="S3"><blockquote class="contribution_text"><cite class="member">Other MP</cite><p id="q2">To ask second?</p></blockquote></div>
          <div class="member_contribution" id="S4"><blockquote class="contribution_text"><cite class="member">Minister</cite><p id="r3">Second answer.</p></blockquote></div>''')
        gs=r.item_groups(p)
        self.assertEqual(list(gs),['r1','r3'])
        self.assertEqual([n['node_id'] for n in gs['r1']['nodes']],['q1','q1b','r1','r2'])
        self.assertEqual([n['role'] for n in gs['r1']['nodes']],['question','question','response','response'])
        self.assertEqual(gs['r1']['date'],'1991-12-02')

    def test_lords_question_form_and_joint_answer(self):
        p=self.saved('item.html','''<h1>Hall</h1><cite class="section">HL Deb 10 December 1991 vol 533</cite>
          <div class="member_contribution" id="S1"><blockquote class="contribution_text"><p id="q1">asked Her Majesty's Government: Whether a decision was reached.</p></blockquote></div>
          <div class="member_contribution" id="S2"><blockquote class="contribution_text"><p id="q2">asked Her Majesty’s Government: Whether the decision will be published.</p></blockquote></div>
          <div class="member_contribution" id="S3"><blockquote class="contribution_text"><p id="r1">The joint reply.</p></blockquote></div>''')
        gs=r.item_groups(p)
        self.assertEqual(len(gs),1)
        self.assertEqual([n['role'] for n in gs['r1']['nodes']],['question','question','response'])

    def test_nested_table_does_not_leak_into_question_or_duplicate_cells(self):
        p=self.saved('item.html','''<h1>Topic</h1><cite class="section">HC Deb 03 December 1991 vol 200</cite>
          <div class="member_contribution" id="S1"><blockquote class="contribution_text"><p id="q1">To ask expenditure?</p></blockquote></div>
          <div class="member_contribution" id="S2"><blockquote class="contribution_text"><p id="r1">It is tabulated.<table><tr><td>Wind</td><td>2.5</td></tr></table></p><p id="r2">The remainder.</p></blockquote></div>''')
        ns=r.item_groups(p)['r1']['nodes']
        self.assertEqual([n['text'] for n in ns],['To ask expenditure?','It is tabulated.','Wind 2.5','The remainder.'])

    def test_ambiguous_unkeyed_group_is_not_auto_repaired(self):
        old=[{'locator':'role=government_response;source_id=0','segment_text':'Same reply'}]
        ns=[{'role':'response','text':'Same reply','node_id':'x'}]
        self.assertIsNone(r.chosen_group({'external_id':'historic_hash'},old,{'a':{'nodes':ns},'b':{'nodes':ns}},{} )[0])

    def test_duplicate_external_ids_keep_distinct_original_positions(self):
        p=self.saved('detail.json',json.dumps({'Overview':{'ExtId':'one','Date':'2006-06-05'},'Items':[
            {'ItemType':'Contribution','ExternalId':'same','ItemId':1,'HRSTag':'Question','Value':'To ask first?'},
            {'ItemType':'Contribution','ExternalId':'same','ItemId':2,'HRSTag':'Question','Value':'To ask second?'}]}))
        ns=r.archive_nodes(p)['one']['nodes']
        self.assertEqual(len(ns),2)
        self.assertNotEqual(ns[0]['text'],ns[1]['text'])
        self.assertNotEqual(ns[0]['locator'],ns[1]['locator'])

    def test_moved_checkpoint_refuses_application(self):
        p=self.saved('checkpoint.bin','before')
        plan={'checkpoints':[r.stamp(p)],'inputs':[],'raw_inputs':[]}
        r.verify_checkpoints(plan)
        p.write_text('changed checkpoint')
        with self.assertRaisesRegex(RuntimeError,'checkpoint moved'):r.verify_checkpoints(plan)

    def test_source_external_id_not_fr_number_or_text_is_parent_key(self):
        self.assertNotEqual(r.sid('doc','src','r1'),r.sid('doc','src','r2'))
        self.assertEqual(r.sid('doc','src','r1'),r.sid('doc','src','r1'))

    def test_range_heading_is_never_exact_even_with_format_date(self):
        g={'date_attribute':'2003-10-07','date_heading':'The following answers were received between Tuesday 7 October and Monday 13 October 2003'}
        self.assertEqual(r.single_saved_day(g),('', 'range_only'))

    def test_single_source_date_corroboration_and_conflict_rejection(self):
        for head,day in [('Friday 31 January 1992>','1992-01-31'),('Thursday 3 March 194','1994-03-03'),('Thursday 6 November','1997-11-06'),('Monday 3 July 2000>','2000-07-03')]:
            self.assertEqual(r.single_saved_day({'date_attribute':day,'date_heading':head})[0],day)
        self.assertEqual(r.single_saved_day({'date_attribute':'1994-03-03','date_heading':'Thursday 3 March 1995'})[0],'')
        self.assertEqual(r.single_saved_day({'date_attribute':'1994-03-03','date_heading':'Friday 3 March 1994'})[0],'')

    def test_annotation_idempotency_and_transaction_rollback(self):
        c=duckdb.connect(':memory:');c.execute(r.SCHEMA)
        c.execute('BEGIN');c.execute('INSERT INTO repair_runs VALUES (?,?,?,?,?,?)',[r.RUN,r.RULE,'hash','now',True,'plan'])
        c.execute('INSERT INTO repair_annotations VALUES (?,?,?,?,?,?,?,?,?)',[r.RUN,'finding','parent','source','DATE','1','needs_review','unresolved','{}'])
        with self.assertRaises(duckdb.ConstraintException):c.execute('INSERT INTO repair_annotations VALUES (?,?,?,?,?,?,?,?,?)',[r.RUN,'finding','parent','source','DATE','1','needs_review','unresolved','{}'])
        c.execute('ROLLBACK');self.assertEqual(c.execute('SELECT count(*) FROM repair_annotations').fetchone()[0],0);c.close()

    def test_deactivation_preserves_history_and_removes_effective_layer(self):
        c=duckdb.connect(':memory:');c.execute(r.SCHEMA)
        c.execute('INSERT INTO repair_runs VALUES (?,?,?,?,?,?)',[r.RUN,r.RULE,'hash','now',True,'plan'])
        c.execute('INSERT INTO repair_annotations VALUES (?,?,?,?,?,?,?,?,?)',[r.RUN,'finding','parent','source','DATE','1','needs_review','unresolved','{}'])
        c.execute('CREATE VIEW active_annotations AS SELECT a.* FROM repair_annotations a JOIN repair_runs r USING(run_id) WHERE r.active')
        c.execute('BEGIN');c.execute('UPDATE repair_runs SET active=false WHERE run_id=?',[r.RUN]);c.execute('COMMIT')
        self.assertEqual(c.execute('SELECT count(*) FROM active_annotations').fetchone()[0],0)
        self.assertEqual(c.execute('SELECT count(*) FROM repair_annotations').fetchone()[0],1);c.close()

    def test_effective_views_isolate_ranges_preserve_ethics_and_shared_parent(self):
        c=duckdb.connect(':memory:');c.execute(r.SCHEMA)
        c.execute('''CREATE TABLE documents(document_id VARCHAR,source_id VARCHAR,external_id VARCHAR,publication_date DATE,publication_timestamp TIMESTAMPTZ,publication_date_basis VARCHAR,body_status VARCHAR,ethics_status VARCHAR,licence_status VARCHAR);
          CREATE TABLE document_content_objects(document_id VARCHAR,content_object_id VARCHAR,relationship_type VARCHAR,ordinal INTEGER);
          CREATE TABLE text_segments(segment_id VARCHAR,content_version_id VARCHAR,extraction_run_id VARCHAR,segment_order INTEGER,segment_text VARCHAR,locator VARCHAR,text_sha256 VARCHAR);
          CREATE TABLE voice_attributions(document_id VARCHAR,segment_id VARCHAR,actor_name VARCHAR)''')
        c.execute("INSERT INTO documents VALUES ('range','source','ext','2003-06-01',NULL,'old parser','blocked_pending_ethics_route','pending','internal'),('joint','modern','question:1','2014-10-13',NULL,'source','saved','pending','internal')")
        c.execute("INSERT INTO text_segments VALUES ('shared','version','old_run',0,'Same joint answer','role=government_response;source_id=r','hash')")
        c.execute("INSERT INTO voice_attributions VALUES ('joint','shared','Minister')")
        c.execute('INSERT INTO repair_runs VALUES (?,?,?,?,?,?)',[r.RUN,r.RULE,'hash','now',True,'plan'])
        c.execute('INSERT INTO repair_date_intervals VALUES (?,?,?,?,?,?,?,?,?)',[r.RUN,'range','2003-06-01',None,'2002-12-20','2003-01-06',None,'saved#range','range only'])
        c.execute('INSERT INTO repair_content_states VALUES (?,?,?,?,?,?,?)',[r.RUN,'range','saved_text_available','blocked_pending_ethics_route','pending','internal','{}'])
        r.create_views(c)
        self.assertEqual(c.execute("SELECT publication_date,analysis_month,exact_day_eligible,body_status,ethics_status,current_technical_state FROM repair_current_documents WHERE document_id='range'").fetchone(),(None,None,False,'blocked_pending_ethics_route','pending','saved_text_available'))
        self.assertEqual(c.execute("SELECT segment_text FROM repair_current_parent_segments WHERE document_id='joint'").fetchone()[0],'Same joint answer')
        c.execute('UPDATE repair_runs SET active=false')
        self.assertEqual(str(c.execute("SELECT publication_date FROM repair_current_documents WHERE document_id='range'").fetchone()[0]),'2003-06-01')
        self.assertEqual(c.execute('SELECT count(*) FROM repair_date_intervals').fetchone()[0],1);c.close()

if __name__=='__main__':unittest.main(verbosity=2)
