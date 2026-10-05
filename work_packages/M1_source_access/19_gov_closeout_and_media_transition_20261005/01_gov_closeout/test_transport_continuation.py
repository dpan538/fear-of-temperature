"""Network-denied fixtures for stop/identity/partial/cap boundaries."""
import csv
import importlib.util
import json
import socket
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('candidate',HERE/'transport_continuation.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class Response:
    def __init__(self,url,status=200,body=b'%PDF-1.4\nfixture',headers=None):
        self.url=url; self.status_code=status; self.body=body
        self.headers=headers if headers is not None else {'Content-Type':'application/pdf','Content-Length':str(len(body))}
    def iter_content(self,size): yield self.body
    def close(self): pass


class TransportFixtures(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.row=next(r for r in m.read_csv(m.OLD_HERE/'frozen_acquisition_manifest.csv') if r['item_uri']==m.FAILED_URI)
        self.contract=json.loads((m.OLD_HERE/'ACQUISITION_CONTRACT.json').read_text())
        self.stack=[]
        for key,val in [('ROOT',root),('OUT',root/'continuation'),('GLOBAL_STATE',root/'spacing.json')]:
            p=patch.object(m,key,val);p.start();self.stack.append(p)
        self.denied=patch.object(socket.socket,'connect',side_effect=AssertionError('Actual network forbidden'))
        self.denied.start();self.stack.append(self.denied)
        for key,val in [('check_release',lambda digest:self.contract),('budget',lambda *a,**kw:{})]:
            p=patch.object(m,key,val);p.start();self.stack.append(p)
            if key=='budget': self.budget_patch=p
        p=patch.object(m,'raw_roots',lambda:[root/'old/raw',m.OUT/'B_CORRECTED/raw',m.OUT/'AU_ORIGINALS/raw'])
        p.start();self.stack.append(p)
        self.sleep=patch.object(m.time,'sleep',return_value=None);self.sleep.start();self.stack.append(self.sleep)
    def tearDown(self):
        for p in reversed(self.stack):p.stop()
        self.tmp.cleanup()
    def get(self,response,row=None):
        with patch('requests.get',return_value=response) as request:
            result=m.fetch(row or self.row,self.contract,'B_CORRECTED','fixture')
            return result,request
    def test_same_item_wildcard_success(self):
        result,request=self.get(Response(self.row['request_url']))
        self.assertEqual(result['status'],'downloaded_candidate_original')
        args=request.call_args
        self.assertEqual(args.args[0],self.row['request_url']);self.assertEqual(args.kwargs['headers']['Accept'],'*/*')
        self.assertFalse(args.kwargs['allow_redirects']);self.assertEqual(request.call_count,1)
    def test_406_persists_and_never_retries(self):
        response=Response(self.row['request_url'],406,b'',{'Content-Type':'application/xml'})
        result,request=self.get(response);self.assertEqual(result['status'],'failed');self.assertEqual(request.call_count,1)
        self.assertTrue(m.load(m.state_path('B_CORRECTED'))['halted'])
        with patch('requests.get') as denied:
            with self.assertRaisesRegex(RuntimeError,'Persistent'):m.fetch(self.row,self.contract,'B_CORRECTED','fixture')
            denied.assert_not_called()
    def test_html_error_200_rejected(self):
        result,_=self.get(Response(self.row['request_url'],body=b'<html>challenge</html>',headers={'Content-Type':'text/html'}))
        self.assertEqual(result['status'],'failed');self.assertEqual(result['byte_count'],0)
    def test_octet_stream_error_signature_rejected_and_partial_kept(self):
        result,_=self.get(Response(self.row['request_url'],body=b'not a PDF',headers={'Content-Type':'application/octet-stream'}))
        self.assertEqual(result['status'],'failed');self.assertTrue((m.ROOT/result['partial_path']).exists())
        self.assertEqual(result['byte_count'],9)
    def test_truncated_body_keeps_accounted_partial(self):
        result,_=self.get(Response(self.row['request_url'],headers={'Content-Type':'application/pdf','Content-Length':'100'}))
        self.assertEqual(result['status'],'failed');self.assertTrue((m.ROOT/result['partial_path']).exists())
        self.assertEqual(m.raw_accounting()['partial_bytes'],len(b'%PDF-1.4\nfixture'))
    def test_redirect_stops_without_second_request(self):
        result,request=self.get(Response(self.row['request_url'],303,b'',{'Location':'https://op.europa.eu/elsewhere'}))
        self.assertEqual(result['status'],'failed');self.assertEqual(request.call_count,1)
    def test_sibling_and_date_change_rejected_before_http(self):
        for bad in [{**self.row,'item_uri':self.row['item_uri'].replace('DOC_1','DOC_2')},
                    {**self.row,'publication_dates':'2015-01-10'}]:
            with patch('requests.get') as denied:
                with self.assertRaisesRegex(RuntimeError,'Changed or sibling'):m.fetch(bad,self.contract,'B_CORRECTED','fixture')
                denied.assert_not_called()
    def test_retry_after_persisted_no_stream(self):
        result,_=self.get(Response(self.row['request_url'],headers={'Content-Type':'application/pdf','Retry-After':'120'}))
        self.assertEqual(result['status'],'failed');self.assertEqual(result['byte_count'],0)
        self.assertTrue(m.active_cooldown(m.load(m.state_path('B_CORRECTED'))))
    def test_existing_checkpoint_cannot_be_overwritten(self):
        self.get(Response(self.row['request_url']))
        with patch('requests.get') as denied:
            with self.assertRaisesRegex(RuntimeError,'Existing attempt'):m.fetch(self.row,self.contract,'B_CORRECTED','fixture')
            denied.assert_not_called()
    def test_unrequested_item_keeps_v3_accept(self):
        row=next(r for r in m.read_csv(m.OLD_HERE/'frozen_acquisition_manifest.csv') if r['item_uri']!=m.FAILED_URI)
        result,request=self.get(Response(row['request_url']),row)
        self.assertEqual(result['status'],'downloaded_candidate_original')
        self.assertEqual(request.call_args.kwargs['headers']['Accept'],'application/pdf')
    def test_shared_old_new_partial_cap_and_floor(self):
        # Restore real budget, keep raw accounting and disk responses synthetic.
        self.budget_patch.stop()
        cap=2*m.GIB
        with patch.object(m,'raw_accounting',return_value={'total_bytes':cap-1,'partial_bytes':100,'files':[]}), \
             patch.object(m.shutil,'disk_usage',return_value=type('D',(),{'free':30*m.GIB})()):
            with self.assertRaisesRegex(RuntimeError,r'Shared A\+B cap'):m.budget(self.contract,2)
        with patch.object(m,'raw_accounting',return_value={'total_bytes':0,'partial_bytes':0,'files':[]}), \
             patch.object(m.shutil,'disk_usage',return_value=type('D',(),{'free':17*m.GIB})()):
            with self.assertRaisesRegex(RuntimeError,'floor'):m.budget(self.contract,reserve_remaining=True)


class ReleaseFixtures(unittest.TestCase):
    def test_missing_new_release_denies_http(self):
        with tempfile.TemporaryDirectory() as t,patch.object(m,'RELEASE',Path(t)/'missing.json'),patch('requests.get') as denied:
            with self.assertRaisesRegex(RuntimeError,'New coordinator'):m.check_release('')
            denied.assert_not_called()
    def test_tampered_release_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'release.json';p.write_text('{"ready":true}')
            with patch.object(m,'RELEASE',p):
                with self.assertRaisesRegex(RuntimeError,'digest mismatch'):m.check_release('bad')


class AUFixtures(unittest.TestCase):
    def test_unconfirmed_primary_links_never_requested(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);html=root/'landing.html';html.write_text('<html><a href="different.pdf">other</a></html>')
            with patch.object(m,'ROOT',root),patch.object(m,'OUT',root/'out'),patch.object(m,'raw_accounting',return_value={}), \
                 patch.object(m,'fetch',return_value={'status':'downloaded_candidate_original','raw_path':'landing.html'}) as request:
                m.execute_au({},'fixture')
                self.assertEqual(request.call_count,2)
                self.assertTrue(all(call.kwargs.get('kind')=='html' for call in request.call_args_list))
    def test_only_exact_two_landing_pdf_pairs(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);plans=m.read_csv(m.HERE/'AU_ORIGINAL_CHECK_PLAN.csv')
            html=root/'landing.html';html.write_text('<html>'+''.join('<a href="'+r['candidate_pdf_url']+'">PDF</a>' for r in plans)+'</html>')
            with patch.object(m,'ROOT',root),patch.object(m,'OUT',root/'out'),patch.object(m,'raw_accounting',return_value={}), \
                 patch.object(m,'fetch',return_value={'status':'downloaded_candidate_original','raw_path':'landing.html'}) as request:
                m.execute_au({},'fixture')
                self.assertEqual([c.args[0]['request_url'] for c in request.call_args_list],
                                 [v for r in plans for v in [r['landing_url'],r['candidate_pdf_url']]])
                self.assertEqual(request.call_count,4)


class QueueFixtures(unittest.TestCase):
    def test_budget_stop_is_terminal_and_full_queue_accounted(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            old=SimpleNamespace(verified_reuse=lambda *a,**k:{'status':'verified_local_reuse','new_raw_bytes':0})
            with patch.object(m,'OUT',root/'out'),patch.object(m,'old_runner',return_value=old), \
                 patch.object(m,'raw_accounting',return_value={}),patch.object(m,'fetch',side_effect=RuntimeError('cap reached')) as request:
                m.execute_b({},'fixture')
                result=m.load(m.OUT/'B_CORRECTED/RESULT.json')
                self.assertEqual(len(result['outcomes']),979);self.assertEqual(request.call_count,1)
                self.assertFalse(result['complete_frozen_item_queue'])
                self.assertTrue(m.load(m.state_path('B_CORRECTED'))['halted'])
                self.assertEqual(sum(r['status']=='verified_local_reuse' for r in result['outcomes']),20)
                self.assertEqual(sum(r['status']=='not_attempted_after_stop' for r in result['outcomes']),958)




if __name__=='__main__': unittest.main(verbosity=2)
