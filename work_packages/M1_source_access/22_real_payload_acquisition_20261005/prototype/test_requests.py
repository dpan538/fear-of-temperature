"""Exercise actual request path offline in temporary outputs, no real fixture rows."""
import contextlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import transport as t
class Response:
    def __init__(self,status=200,data=b'%PDF-1.7\nfixture',mime='application/pdf',extra=None):
        self.status_code=status;self.data=data;self.headers={'Content-Type':mime,'Content-Length':str(len(data)),**(extra or {})}
    def iter_content(self,size):yield self.data
    def close(self):pass
class ActualRequestPath(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='round22_synthetic_');self.p=Path(self.tmp.name)
        for path in ['prototype','control','government','media/frames','media/policy']:(self.p/path).mkdir(parents=True,exist_ok=True)
        self.scope=t.read(t.SCOPE);self.scope['network_deadline_utc']='2099-01-01T00:00:00+00:00'
        t.save(self.p/'control/SCOPE.json',self.scope)
        shutil.copyfile(t.OUT/'PLAN.md',self.p/'PLAN.md')
        for name in ['CANDIDATES.json','REQUEST_POLICY.json']:shutil.copyfile(t.OUT/'control'/name,self.p/'control'/name)
        coord=t.OUT/'control/COORDINATION.json'
        if not coord.exists():coord=t.OUT/'control/COORDINATION_READ_ONLY_RECEIPT.json'
        shutil.copyfile(coord,self.p/'control/COORDINATION.json')
        shutil.copyfile(Path(t.__file__),self.p/'prototype/transport.py')
        self.urls=[f'https://publications.europa.eu/resource/cellar/test.0001.01/DOC_{i}' for i in range(11)]
        t.save(self.p/'government/TARGET_SEQUENCE.json',{'targets':[{'request_url':u} for u in self.urls]})
        self.stack=contextlib.ExitStack()
        self.stack.enter_context(patch.object(t,'OUT',self.p));self.stack.enter_context(patch.object(t,'SCOPE',self.p/'control/SCOPE.json'))
        self.stack.enter_context(patch.object(t,'lock',lambda:contextlib.nullcontext()))
        self.stack.enter_context(patch.object(t,'budget',return_value={'passed':True,'synthetic':True}))
        self.stack.enter_context(patch.object(t.time,'sleep',return_value=None))
        t.preflight_receipt(self.p/'control/REQUEST_POLICY.json')
    def tearDown(self):self.stack.close();self.tmp.cleanup()
    def run_fetch(self,response,url=None,cap=2097152):
        with patch.object(t.requests,'get',return_value=response) as get:
            result=t.fetch('eu_cellar',url or self.urls[0],'selected_Item','consistent_exact_uri',lane='government',hosts=['publications.europa.eu'],cap=cap)
            self.assertEqual(get.call_count,1)
            self.assertEqual(get.call_args.kwargs['headers']['Accept'],'*/*')
            self.assertFalse(get.call_args.kwargs['allow_redirects'])
            return result
    def test_valid_octet_pdf_exact_uri(self):
        r=self.run_fetch(Response(mime='application/octet-stream'));self.assertEqual(r['status'],'saved')
        self.assertTrue((self.p/r['raw_path']).read_bytes().startswith(b'%PDF-'))
    def test_html_rejected_persistent_stop(self):
        r=self.run_fetch(Response(data=b'<html>not PDF</html>',mime='text/html'));self.assertEqual(r['status'],'failed')
        with patch.object(t.requests,'get') as get:
            with self.assertRaises(RuntimeError):t.fetch('eu_cellar',self.urls[1],'selected_Item','consistent_exact_uri',lane='government')
            get.assert_not_called()
    def test_signature_rejected(self):
        self.assertEqual(self.run_fetch(Response(data=b'not PDF'))['status'],'failed')
    def test_truncation_partial_charged(self):
        r=self.run_fetch(Response(),cap=4);self.assertEqual(r['status'],'truncated')
        self.assertEqual((self.p/r['partial_path']).read_bytes(),b'%PDF')
    def test_bad_length_retained_not_certified(self):
        self.assertEqual(self.run_fetch(Response(extra={'Content-Length':'999'}))['status'],'failed')
    def test_redirect_stops_without_second_request(self):
        r=self.run_fetch(Response(status=302,extra={'Location':self.urls[1]}));self.assertEqual(r['status'],'failed');self.assertEqual(len(r['hops']),1)
    def test_retry_after_persistent_restriction(self):
        r=self.run_fetch(Response(extra={'Retry-After':'3600'}));self.assertEqual(r['status'],'failed');self.assertTrue(r['publisher_denial'])
    def test_non_pdf_406_remains_new_failure(self):
        r=self.run_fetch(Response(status=406,data=b'<error/>',mime='application/xml'));self.assertEqual(r['http_status'],406);self.assertFalse(r['publisher_denial'])
    def test_frozen_order_and_scope_before_network(self):
        with patch.object(t.requests,'get') as get:
            with self.assertRaises(RuntimeError):t.fetch('eu_cellar',self.urls[1],'selected_Item','consistent_exact_uri',lane='government')
            with self.assertRaises(RuntimeError):t.fetch('eu_cellar','https://publications.europa.eu/resource/cellar/other','selected_Item','consistent_exact_uri',lane='government')
            get.assert_not_called()
    def test_policy_digest_change_stops_before_network(self):
        policy=t.read(self.p/'control/REQUEST_POLICY.json');policy['automatic_retries']=3;t.save(self.p/'control/REQUEST_POLICY.json',policy)
        with patch.object(t.requests,'get') as get:
            with self.assertRaises(RuntimeError):t.fetch('eu_cellar',self.urls[0],'selected_Item','consistent_exact_uri',lane='government')
            get.assert_not_called()
    def test_attempt_cannot_be_repeated(self):
        self.run_fetch(Response())
        with patch.object(t.requests,'get') as get:
            with self.assertRaises(RuntimeError):t.fetch('eu_cellar',self.urls[0],'selected_Item','consistent_exact_uri',lane='government')
            get.assert_not_called()
    def test_closed_round_cannot_make_a_new_request(self):
        t.save(self.p/'control/NETWORK_CLOSED.json',{'closed':True})
        with patch.object(t.requests,'get') as get:
            with self.assertRaisesRegex(RuntimeError,'network pass closed'):
                t.fetch('eu_cellar',self.urls[0],'selected_Item','consistent_exact_uri',lane='government')
            get.assert_not_called()
if __name__=='__main__':unittest.main()
