import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'prototype'))
import parser
import staging
import transport
import pipeline
import reconcile_allowances

class ParserTests(unittest.TestCase):
    def parse(self, html, **kw):
        return parser.extract(html.encode(),selector='article',boundary_evidence='labelled fixture',**kw)
    def test_inline_word_and_actual_space(self):
        self.assertEqual(self.parse('<article><p>A <a>l</a>ong-time <em>reader</em>.</p></article>')['body'], 'A long-time reader.')
        self.assertEqual(self.parse('<article><p>one <b>two</b> three</p></article>')['body'],'one two three')
    def test_blocks_lists_breaks_tables_not_duplicated(self):
        body=self.parse('<article><div><p>A<br>B</p><ul><li>C</li><li>D</li></ul><table><tr><td>E</td><td>F</td></tr></table></div></article>')['body']
        self.assertEqual(body.count('A'),1)
        self.assertIn('A\nB',body); self.assertIn('C\n\nD',body); self.assertIn('E\tF',body)
    def test_preview_and_container_do_not_qualify(self):
        self.assertEqual(self.parse('<article><p>Lead only</p></article><div data-paywall></div>')['state'],'preview_or_access_marker')
        self.assertEqual(self.parse('<article>Issue OCR</article>',unit_kind='issue')['state'],'container_only')
    def test_missing_or_multiple_boundary_stays_unresolved(self):
        self.assertEqual(self.parse('<main>Text</main>')['state'],'unresolved_boundary')
        self.assertEqual(self.parse('<article>A</article><article>B</article>')['node_count'],2)
    def test_widgets_and_jsonld_are_not_bodies(self):
        self.assertEqual(self.parse('<article><p>Narrative</p><aside class="widget">Other</aside></article>',remove=('.widget',))['body'],'Narrative')
        self.assertEqual(self.parse('<script type="application/ld+json">{"articleBody":"Text"}</script>')['state'],'unresolved_boundary')
    def test_identity_container_rejected(self):
        self.assertEqual(parser.native_identity('https://trove.nla.gov.au/newspaper/article/123','trove_article'),'123')
        with self.assertRaises(ValueError): parser.native_identity('https://trove.nla.gov.au/newspaper/page/123','trove_article')
        with self.assertRaises(ValueError): parser.native_identity('https://archives.stanforddaily.com/?a=d&d=stanford19880101-01','veridian_article')
    def test_native_order_pagination_and_duplicate_links(self):
        frame=parser.enumerate_links(b'<a href="/article/2">B</a><a href="/article/1">A</a><a href="/article/2">B</a><a rel="next" href="?page=2">Next</a>', 'https://example.org/',r'/article/')
        self.assertEqual([x['url'] for x in frame['links']],['https://example.org/article/2','https://example.org/article/1'])
        self.assertEqual(frame['next_url'],'https://example.org/?page=2'); self.assertFalse(frame['frame_complete'])

class StagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.db=Path(self.tmp.name)/'fixture.sqlite3'
        self.record=dict(lane='fixture',source_id='fixture_title',native_id='article-1',acquisition_parent='fixture_archive',stratum='US',country='US',edition='fixture',publication_date='1988-01-01',publication_precision='day',unit_kind='article',provenance='synthetic_fixture',newspaper_eligible=0)
        h=hashlib.sha256(b'fixture').hexdigest()
        self.version=dict(raw_path='fixture',raw_sha256=h,body_path='fixture',body_sha256=h,parser_sha256=parser.parser_digest(),retrieved_at='2026-10-05T11:00:00+00:00',content_version_time=None,historical_version_equivalence='unverified',qualified_readable=0,extraction_json='{}')
        self.receipt={'request_id':'fixture_request','fixture':True}
    def tearDown(self): self.tmp.cleanup()
    def test_interrupted_transaction_and_restart(self):
        with staging.writer(self.db) as con:
            with self.assertRaises(RuntimeError): staging.ingest(con,self.record,self.version,self.receipt,{'next':'2'},interrupt_after_version=True)
            self.assertEqual(staging.snapshot(con)['versions'],0)
            self.assertEqual(staging.snapshot(con)['cursors'],[])
        with staging.writer(self.db) as con:
            self.assertEqual(staging.ingest(con,self.record,self.version,self.receipt,{'next':'2'})['new_versions_inserted'],1)
        with staging.writer(self.db) as con:
            self.assertEqual(staging.ingest(con,self.record,self.version,self.receipt,{'next':'2'})['new_versions_inserted'],0)
            self.assertEqual(staging.snapshot(con)['qualified_newspaper_articles'],0)
            self.assertEqual(staging.snapshot(con)['versions'],1)
    def test_new_parser_version_same_parent(self):
        with staging.writer(self.db) as con:
            a=staging.ingest(con,self.record,self.version,self.receipt,{})
            self.version['parser_sha256']='a'*64
            b=staging.ingest(con,self.record,self.version,self.receipt,{})
            self.assertEqual(a['article_id'],b['article_id']); self.assertNotEqual(a['version_id'],b['version_id'])
    def test_fixed_endpoint_and_wrong_unit_and_diagnostic(self):
        with staging.writer(self.db) as con:
            self.record['publication_date']='2026-09-22'
            with self.assertRaises(ValueError): staging.ingest(con,self.record,self.version,self.receipt,{})
            self.record.update(publication_date='2026-09-21',unit_kind='issue',newspaper_eligible=1)
            with self.assertRaises(ValueError): staging.ingest(con,self.record,self.version,self.receipt,{})
            self.record.update(unit_kind='article',newspaper_eligible=0); self.version['qualified_readable']=1
            with self.assertRaises(ValueError): staging.ingest(con,self.record,self.version,self.receipt,{})
    def test_identity_date_conflict_rolls_back(self):
        with staging.writer(self.db) as con:
            staging.ingest(con,self.record,self.version,self.receipt,{'next':'2'})
            self.record['publication_date']='1988-01-02'
            with self.assertRaises(ValueError): staging.ingest(con,self.record,self.version,self.receipt,{'next':'3'})
            self.assertEqual(staging.snapshot(con)['cursors'][0]['cursor'],{'next':'2'})
    def test_edition_and_provenance_conflicts_do_not_reassign_parent(self):
        with staging.writer(self.db) as con:
            staging.ingest(con,self.record,self.version,self.receipt,{'next':'2'})
            for key in ('edition','provenance','acquisition_parent'):
                changed=dict(self.record);changed[key]='conflicting'
                with self.assertRaises(ValueError):staging.ingest(con,changed,self.version,self.receipt,{'next':'3'})
            self.assertEqual(staging.snapshot(con)['cursors'][0]['cursor'],{'next':'2'})

class TransportTests(unittest.TestCase):
    def test_original_reserve_not_relaxed(self):
        with patch('transport.shutil.disk_usage',return_value=type('D',(),{'free':18768379904})()),patch('transport.corpus_bytes',return_value=0):
            p=transport.preflight()
        self.assertFalse(p['passed']); self.assertEqual(p['original_remaining_reserve_bytes'],3335940580)
    def test_lifetime_copies_and_pending_overhead_stop(self):
        with patch('transport.shutil.disk_usage',return_value=type('D',(),{'free':40*1024**3})()),patch('transport.corpus_bytes',return_value=110*1024**2):
            self.assertFalse(transport.preflight()['passed'])
    def fixture_transport(self):
        tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(tmp.cleanup);base=Path(tmp.name);own=base/'newspaper';own.mkdir();(own/'control').mkdir()
        (base/'control').mkdir();(base/'control/SCOPE.json').write_text(json.dumps(transport.SCOPE))
        gate=own/'gate.json';gate.write_text(json.dumps({'source_id':'fixture','access_state':'public_route_permitted','public_hosts':['example.org'],'changed_parser_validated':True}))
        for target,value in [('transport.OWN',own),('transport.HEAVY_LOCK',own/'heavy.lock')]:
            p=patch(target,value);p.start();self.addCleanup(p.stop)
        return own,gate
    def test_storage_stop_sends_no_request_and_is_restart_stable(self):
        own,gate=self.fixture_transport()
        with patch('transport.preflight',return_value={'passed':False}),patch('transport.requests.Session') as session:
            first=transport.fetch('fixture','https://example.org/a','article',gate)
            second=transport.fetch('fixture','https://example.org/a','article',gate)
        session.assert_not_called();self.assertEqual(first,second)
        self.assertEqual(first['charged_attempts'],0);self.assertEqual(first['status'],'storage_blocked')
    def test_explicit_recovery_keeps_failed_receipt_and_same_target(self):
        own,gate=self.fixture_transport()
        with patch('transport.preflight',return_value={'passed':False}):
            prior=transport.fetch('fixture','https://example.org/a','article',gate)
        prior_path=own/'requests'/(prior['request_id']+'.json');before=prior_path.read_bytes()
        response=MagicMock();response.status_code=200;response.headers={};response.iter_content.return_value=[b'fixture']
        session=MagicMock();session.get.return_value=response
        with patch('transport.preflight',return_value={'passed':True}),patch('transport.requests.Session',return_value=session):
            recovered=transport.fetch('fixture','https://example.org/a','article',gate,request_version='capacity-v2',previous_request_id=prior['request_id'],recovery_reason='Fixture actual fresh capacity passes')
        self.assertEqual(recovered['status'],'saved');self.assertNotEqual(prior['request_id'],recovered['request_id'])
        self.assertEqual(prior_path.read_bytes(),before);self.assertEqual(session.get.call_count,1)
        with self.assertRaises(ValueError):transport.fetch('fixture','https://example.org/b','article',gate,request_version='v3',previous_request_id=prior['request_id'],recovery_reason='Invalid target swap')
    def test_truncation_preserves_partial_and_duplicate_does_not_refetch(self):
        own,gate=self.fixture_transport();response=MagicMock()
        response.status_code=200;response.headers={'Content-Type':'text/html'}
        response.iter_content.return_value=[b'x'*65]
        session=MagicMock();session.get.return_value=response
        scope=dict(transport.SCOPE,default_object_cap_bytes=64)
        with patch('transport.SCOPE',scope),patch('transport.preflight',return_value={'passed':True}),patch('transport.requests.Session',return_value=session):
            first=transport.fetch('fixture','https://example.org/a','article',gate)
            second=transport.fetch('fixture','https://example.org/a','article',gate)
        self.assertEqual(session.get.call_count,1);self.assertEqual(first,second)
        self.assertEqual(first['byte_count'],64);self.assertTrue(first['partial'])
        self.assertEqual(first['status'],'object_cap_stop');self.assertTrue((own/first['raw_path']).exists())
    def test_retry_after_stop_blocks_a_new_url_without_another_request(self):
        own,gate=self.fixture_transport();response=MagicMock()
        response.status_code=429;response.headers={'Retry-After':'120'}
        session=MagicMock();session.get.return_value=response
        with patch('transport.preflight',return_value={'passed':True}),patch('transport.requests.Session',return_value=session):
            first=transport.fetch('fixture','https://example.org/a','article',gate)
            second=transport.fetch('fixture','https://example.org/b','article',gate)
        self.assertEqual(session.get.call_count,1);self.assertEqual(first['status'],'http_stop')
        self.assertEqual(second['charged_attempts'],0)
        self.assertGreater(transport.read_state()['titles']['fixture']['cooldown_until'],0)
    def test_reconciliation_never_resets_native_transport_charges(self):
        own,gate=self.fixture_transport();(own/'sources').mkdir();(own/'requests').mkdir()
        (own/'sources/DISCOVERY_REQUESTS.jsonl').write_text(json.dumps({'title':'fixture','method':'search'})+'\n')
        (own/'requests/native.json').write_text(json.dumps({'source_id':'fixture','purpose':'index','charged_attempts':2,'hops':[]}))
        transport.save_state({'titles':{'fixture':{'metadata':4,'body':3,'search':1,'access_stop':'fixture_stop'}},'hosts':{}})
        with patch('reconcile_allowances.OWN',own),patch('builtins.print'):
            reconcile_allowances.main();reconcile_allowances.main()
        state=transport.read_state()['titles']['fixture']
        self.assertEqual((state['metadata'],state['body'],state['search']),(4,3,1));self.assertEqual(state['access_stop'],'fixture_stop')

class FrozenFrameTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.own=Path(self.tmp.name)
        self.item=dict(native_id='native-1',url='https://example.org/article/1',publication_date='2026-09-21',unit_kind='article')
        self.mock=patch('pipeline.transport.OWN',self.own);self.mock.start()
    def tearDown(self):self.mock.stop();self.tmp.cleanup()
    def test_frame_frozen_before_body_no_refill_and_alias(self):
        alias=dict(self.item,url='https://example.org/article/1-alias')
        p=pipeline.freeze_frame('fixture','2026-09','fixture_discovery',[self.item,alias],native_order='native_DOM')
        frame=json.loads(p.read_text());self.assertEqual(len(frame['selected']),1)
        self.assertEqual(len(frame['identity_aliases']),1);self.assertIsNone(frame['inclusion_probability'])
        with self.assertRaises(ValueError):pipeline.freeze_frame('fixture','2026-09','other',[],native_order='native_DOM')
    def test_partial_september_filter_and_issue_rejection(self):
        late=dict(self.item,publication_date='2026-09-22')
        p=pipeline.freeze_frame('fixture','2026-09','fixture_discovery',[late],native_order='native_DOM')
        self.assertEqual(json.loads(p.read_text())['selected'],[])
        with self.assertRaises(ValueError):pipeline.freeze_frame('fixture','1988-01','fixture_discovery',[dict(self.item,unit_kind='issue')],native_order='native_DOM')
    def test_declared_date_order_and_owned_paths(self):
        earlier=dict(self.item,native_id='native-2',publication_date='2026-09-20')
        with self.assertRaises(ValueError):pipeline.freeze_frame('fixture','2026-09','fixture_discovery',[self.item,earlier],native_order='native_date_ascending')
        with self.assertRaises(ValueError):pipeline.freeze_frame('../elsewhere','2026-09','fixture_discovery',[self.item],native_order='native_DOM')
        with self.assertRaises(ValueError):pipeline.owned('/private/tmp/unowned-review.json')
    def test_modified_frame_cannot_be_staged(self):
        p=pipeline.freeze_frame('fixture','2026-09','fixture_discovery',[self.item],native_order='native_DOM')
        inspection=self.own/'inspection.json';review=self.own/'review.json'
        report={'extraction':{'state':'structural_candidate'},'receipt':{},'target':self.item,
                'frame_path':str(p),'frame_sha256':transport.sha(p)}
        inspection.write_text(json.dumps(report));review.write_text(json.dumps({'status':'qualified_readable_article'}))
        changed=json.loads(p.read_text());changed['selected']=[];p.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'Frozen frame changed'):pipeline.stage_reviewed(inspection,{},review)
    def test_blocked_transport_does_not_generate_derivative(self):
        p=pipeline.freeze_frame('fixture','2026-09','fixture_discovery',[self.item],native_order='native_DOM')
        with patch('pipeline.transport.fetch',return_value={'status':'storage_blocked','request_id':'fixture_stop'}):
            r=pipeline.inspect_target(p,'fixture_gate',dict(selector='article',boundary_evidence='fixture'))
        self.assertEqual(r['state'],'storage_blocked');self.assertFalse((self.own/'bodies').exists())
    def test_review_cannot_qualify_a_preview(self):
        inspection=self.own/'inspection.json';review=self.own/'review.json'
        inspection.write_text(json.dumps({'extraction':{'state':'preview_or_access_marker'},'receipt':{},'target':{}}))
        review.write_text(json.dumps({'status':'qualified_readable_article'}))
        with self.assertRaises(ValueError):pipeline.stage_reviewed(inspection,{},review)

if __name__=='__main__': unittest.main(verbosity=2)
