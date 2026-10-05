"""Actual released-candidate runner path, entirely synthetic and socket denied."""
import sys
sys.dont_write_bytecode=True
import unittest,tempfile,socket,json,hashlib,copy,sqlite3
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
import run,transport,store

class Chain(unittest.TestCase):
 def test_same_candidate_registration_payload_mapping150_reopen_and_review(self):
  plan=transport.read(run.OUT/'ROUTE_PLAN.json');scope=transport.read(run.OUT/'control/SCOPE.json');cell=plan['released_candidates'][0]
  with tempfile.TemporaryDirectory(prefix='media20_SYNTHETIC_') as d:
   out=Path(d);transport.save(out/'control/SCOPE.json',scope);transport.save(out/'ROUTE_PLAN.json',plan);transport.save(out/'evidence/HTTP_STATE.json',{'sources':{}})
   (out/'raw').mkdir();(out/cell['robots_raw_path']).write_bytes((run.OUT/cell['robots_raw_path']).read_bytes())
   urls=['https://'+cell['host']+'/synthetic-fixture-'+str(i)+'/' for i in range(1,6)]
   frame_raw=out/'raw/synthetic_search_response.json';frame_raw.write_text(json.dumps({'synthetic':True,'article_urls':urls}))
   transport.save(out/cell['frame_receipt_path'],{'query':cell['query'],'frame_pages':1,'monthly_denominator':None,'pi':None,'article_urls':list(reversed(urls)),'observed_at_utc':'2026-10-05T03:00:00Z','raw_receipt_path':'raw/synthetic_search_response.json','raw_receipt_sha256':hashlib.sha256(frame_raw.read_bytes()).hexdigest(),'synthetic':True})
   requested=[]
   def fake_fetch(source,url,purpose):
    requested.append(url);rid=hashlib.sha256(json.dumps([source,url,purpose],separators=(',',':')).encode()).hexdigest()[:32]
    node={'@type':'NewsArticle','url':url,'datePublished':'2025-07-03T12:00:00Z','dateModified':'2026-10-01','license':'https://creativecommons.org/licenses/by/4.0/'}
    raw=('<html><link rel="canonical" href="'+url+'"><script type="application/ld+json">'+json.dumps(node)+'</script><article><div class="entry-content">Synthetic ordinary notice '+url+'.</div></article></html>').encode()
    path=out/'raw'/f'{rid}.bin';path.write_bytes(raw)
    r={'request_id':rid,'source_id':source,'request_url':url,'purpose':purpose,'requested_at_utc':'2026-10-05T03:00:00Z','finished_at_utc':'2026-10-05T03:00:01Z','status':'raw_retained','http_status':200,'byte_count':len(raw),'raw_path':str(path.relative_to(out)),'sha256':hashlib.sha256(raw).hexdigest(),'mime_type':'text/html','synthetic':True}
    transport.save(out/'evidence/requests'/f'{rid}.json',r);return r
   with ExitStack() as stack:
    for mod,name,value in [(run,'OUT',out),(run,'STATE',out/'evidence/HTTP_STATE.json'),(transport,'OUT',out),(transport,'SCOPE',out/'control/SCOPE.json'),(transport,'STATE',out/'evidence/HTTP_STATE.json')]:stack.enter_context(patch.object(mod,name,value))
    stack.enter_context(patch.object(run,'check_release',return_value=None)) # release transport tested separately; no synthetic approval copied to real task.
    stack.enter_context(patch.object(run,'before_deadline',return_value=100))
    stack.enter_context(patch.object(run,'_fetch',side_effect=fake_fetch))
    run.run_bodies(out/'ROUTE_PLAN.json');run.run_bodies(out/'ROUTE_PLAN.json')
    self.assertEqual(len(requested),5)
    c=run.initialise(plan=plan);self.assertEqual(store.counts(c),{'article_parents':5,'article_versions':5,'verified_full_bodies':0,'paper_issues':0,'OCR_locators':0,'raw_objects':5,'requests':5})
    self.assertEqual(c.execute('SELECT count(*) FROM sample_slot WHERE parent_id IS NOT NULL').fetchone()[0],0)
    self.assertEqual(c.execute('SELECT count(*) FROM candidate_sample').fetchone()[0],5)
    self.assertEqual(c.execute('SELECT count(*) FROM sample_slot').fetchone()[0],150)
    rows=run.terminal_slots(c,plan);self.assertEqual(len(rows),150);self.assertEqual(sum(bool(x['candidate_parent_id']) for x in rows),5);self.assertFalse(any(x['original_source_success'] for x in rows));self.assertTrue(all(x['pi']=='' for x in rows))
    # A mismatched original source slot is rejected even with a valid candidate parent.
    wrong=c.execute("SELECT slot_id FROM sample_slot JOIN frame USING(frame_id) WHERE provider='guardian' AND month='2025-07' LIMIT 1").fetchone()[0]
    parent=c.execute('SELECT parent_id FROM article_parent LIMIT 1').fetchone()[0]
    with self.assertRaises(sqlite3.IntegrityError):run.insert(c,'candidate_sample',{'original_slot_id':wrong,'mapping_id':cell['mapping_id'],'candidate_frame_id':cell['frame_id'],'parent_id':parent,'status':'synthetic_wrong_slot','note':'synthetic'})
    for p in (out/'evidence/requests').glob('*.json'):
     r=transport.read(p);parsed=transport.read(out/'evidence/parsed'/p.name);body=out/'bodies'/f"{r['request_id']}.txt"
     transport.save(out/'evidence/reviews'/p.name,{'status':'complete_boundary_verified','raw_sha256':r['sha256'],'body_sha256':hashlib.sha256(body.read_bytes()).hexdigest(),'body_selector':parsed['body_selector'],'article_url':parsed['canonical_url'],'rights_review':'route_licence_applies_no_observed_exception','synthetic':True})
    run.finalise_reviews(c);self.assertEqual(store.counts(c)['verified_full_bodies'],5);c.close()
    c=run.initialise(plan=plan);self.assertEqual(store.counts(c)['requests'],5);self.assertEqual(store.counts(c)['verified_full_bodies'],5);self.assertEqual(sum(x['round20_status']=='scope_changed_full_boundary_verified' for x in run.terminal_slots(c,plan)),5);c.close()

if __name__=='__main__':
 with patch.object(socket,'socket',side_effect=RuntimeError('NETWORK DENIED')):unittest.main(verbosity=2)
