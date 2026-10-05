"""Synthetic, no-network checks. Fixtures are never inserted into the real pilot."""
import sys
sys.dont_write_bytecode=True
import unittest,tempfile,json,sqlite3
from pathlib import Path
from unittest.mock import patch
from contextlib import nullcontext
from types import SimpleNamespace
import prototype as p

HERE=Path(__file__).resolve().parent

def insert(c,table,**values):
 c.execute('INSERT INTO '+table+' ('+','.join(values)+') VALUES ('+','.join('?' for _ in values)+')',tuple(values.values()))

class SchemaTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.executescript((HERE/'schema.sql').read_text())
  insert(self.c,'publisher',publisher_id='p',name='Synthetic',hq_verification='fixture')
  for src,region in [('a','UK'),('b','US')]:
   insert(self.c,'outlet',source_id=src,publisher_id='p',outlet_name=src,outlet_type='news',official_home='https://example.test')
   insert(self.c,'edition',edition_id=src,source_id=src,region_layer=region,edition_market='fixture',edition_verification='fixture',region_assignment_basis='fixture')
  insert(self.c,'source_era',era_id='e',edition_id='a',month='2025-07',medium='web',applicability='unknown',era_scope_note='fixture',rights_status='fixture',access_status='fixture')
  insert(self.c,'frame',frame_id='f',era_id='e',provider='a',month='2025-07',unit='article_publication_instance',date_filter_json='{}',type_filter_json='{}',enumeration_state='partial_visible_frame',page_limit=1,scope_detail='fixture')
 def tearDown(self):self.c.close()
 def parent(self,pid='x',src='a',native='123'):
  insert(self.c,'article_parent',parent_id=pid,source_id=src,edition_id=src,native_id=native,native_id_basis='fixture',canonical_url='https://example.test/'+pid,genre='unknown',publishing_role='media',first_date_precision='unknown',identity_state='fixture')
 def slot(self,**override):
  values=dict(slot_id='s',frame_id='f',slot_index=1,status='unfilled',selection_design='non_probability_route_pilot_first_five_stable_urls',planned_region_weight=.2,planned_source_within_region_weight=.5);values.update(override);insert(self.c,'sample_slot',**values)
 def test_partial_count_is_not_monthly_zero(self):
  with self.assertRaises(sqlite3.IntegrityError):self.c.execute('UPDATE frame SET monthly_denominator=0')
 def test_verified_zero_requires_complete_frame(self):
  self.c.execute("UPDATE frame SET enumeration_state='complete_month_frame',monthly_denominator=0");self.assertEqual(self.c.execute('SELECT monthly_denominator FROM frame').fetchone()[0],0)
 def test_nonprobability_pi_forbidden(self):
  with self.assertRaises(sqlite3.IntegrityError):self.slot(pi=.5,pi_basis='unsupported')
 def test_partial_probability_pi_forbidden(self):
  with self.assertRaises(sqlite3.IntegrityError):self.slot(pi=.5,pi_basis='n/N',selection_design='probability_sample_complete_frame')
 def test_complete_probability_pi_allowed(self):
  self.c.execute("UPDATE frame SET enumeration_state='complete_month_frame',monthly_denominator=10")
  self.slot(pi=.5,pi_basis='fixture SRS n=5,N=10',selection_design='probability_sample_complete_frame')
  with self.assertRaises(sqlite3.IntegrityError):self.c.execute("UPDATE frame SET enumeration_state='partial_visible_frame',monthly_denominator=NULL")
 def test_missingness_keeps_null_pi(self):
  self.slot();self.assertIsNone(self.c.execute('SELECT pi FROM sample_slot').fetchone()[0])
 def test_duplicate_native_identity_rejected(self):
  self.parent()
  with self.assertRaises(sqlite3.IntegrityError):self.parent('y')
 def test_same_wire_two_publications_retained(self):
  self.parent('x','a');self.parent('y','b')
  insert(self.c,'story_cluster',story_id='wire',cluster_kind='wire_story',origin_provider='SyntheticWire',verification_state='fixture',evidence='fixture')
  for n in ['x','y']:insert(self.c,'publication_relationship',relation_id=n,parent_id=n,story_id='wire',relation_kind='wire_adoption',verification_state='fixture',evidence='fixture',publication_instance_retained=1)
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM article_parent').fetchone()[0],2)
 def test_quoted_government_does_not_change_media_role(self):
  self.parent()
  insert(self.c,'article_version',version_id='v',parent_id='x',updated_precision='unknown',content_time_precision='unknown',retrieved_at_utc='2026-10-05T00:00:00Z',retrieval_precision='second',readability_status='fixture',preview_status='fixture',ocr_quality_status='not_applicable',layout_status='fixture',rights_status='fixture',access_status='fixture',extractor_version='fixture')
  insert(self.c,'attributed_voice',voice_id='q',version_id='v',voice_kind='quoted_speaker',speaker_role='government',attribution_state='fixture',quotation_and_publishing_role_separate=1)
  self.assertEqual(self.c.execute('SELECT publishing_role FROM article_parent').fetchone()[0],'media')
 def test_unknown_dates_not_imputed_from_retrieval(self):
  self.parent();self.assertEqual(self.c.execute('SELECT first_publication_value,first_date_min,first_date_max FROM article_parent').fetchone(),(None,None,None))
 def test_foreign_key_parent_required(self):
  with self.assertRaises(sqlite3.IntegrityError):self.slot(parent_id='missing')

class ParseTests(unittest.TestCase):
 def test_HTTP_200_challenge_is_not_readable(self):
  x=p.assess_payload('<html><script src="/_Incapsula_Resource"></script><body></body></html>'.encode());self.assertEqual(x['payload_state'],'access_challenge');self.assertTrue(x['stop_source']);self.assertFalse(x['article_body_claimed'])
 def test_tracking_only_removed(self):
  self.assertEqual(p.canonical('https://EXAMPLE.test/a?id=7&utm_source=x#x'),'https://example.test/a?id=7')
 def test_sources_keep_distinct_publication_ids(self):self.assertNotEqual(p.native_parent('a','https://example.test/a'),p.native_parent('b','https://example.test/a'))
 def test_dated_navigation_not_article(self):
  x=p.parse_frame('<main><a href="/article-index/2025/07/01/">01</a></main>','https://example.test/article-index/2025/07/','2025-07','a')
  self.assertEqual(x['observed_unique_links'],0);self.assertEqual(len(x['navigation_urls']),1);self.assertIsNone(x['monthly_denominator'])
 def test_date_filter_without_topic_or_title_filter(self):
  x=p.parse_frame('<main><a href="/news/2025/07/03/neutral">Routine</a><a href="/news/2025/06/03/other">Other</a><a href="/news/2025/07/03/neutral?utm_source=x">Duplicate</a></main>','https://example.test/index','2025-07','a')
  self.assertEqual(x['observed_unique_links'],1);self.assertIsNone(x['monthly_denominator']);self.assertTrue(x['pagination_truncated'])
 def test_retired_route_is_not_zero(self):
  x=p.parse_frame('<main>This page is no longer being updated</main>','https://example.test','2025-07','a');self.assertEqual(x['enumeration_state'],'route_retired');self.assertIsNone(x['monthly_denominator'])
 def test_preview_not_full_body(self):
  x=p.parse_article('<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','datePublished':'2015-12-01','dateModified':'2026-10-01T12:00:00Z','articleBody':'Preview text','isAccessibleForFree':False})+'</script>','https://example.test/a')
  self.assertEqual(x['readability_status'],'preview_only');self.assertEqual(x['first_date_precision'],'day');self.assertNotEqual(x['first_publication_value'],x['updated_value']);self.assertIsNone(x['content_version_time'])
 def test_nested_jsonld_and_missing_body(self):
  x=p.parse_article('<script type="application/ld+json">{"@graph":[{"@type":"NewsArticle","datePublished":"2025-07-01T13:00:00+12:00"}]}</script>','https://example.test/a')
  self.assertEqual(x['first_date_precision'],'timestamp_with_offset');self.assertEqual(x['readability_status'],'no_body_in_structured_metadata')

class HTTPTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(prefix='media_fixture_');self.root=Path(self.t.name)
  self.scope=self.root/'PILOT_SCOPE.json';p.save(self.scope,{'object_cap_bytes':10,'raw_cap_bytes':30,'government_batch_reserved_bytes':2147483648,'storage_floor_bytes':16106127360})
  self.patches=[patch.object(p,'OUT',self.root),patch.object(p,'STATE',self.root/'HTTP_STATE.json'),patch.object(p,'SCOPE',self.scope),patch.object(p,'lock',lambda:nullcontext()),patch.object(p.shutil,'disk_usage',lambda x:SimpleNamespace(free=30*1024**3)),patch.object(p.time,'sleep',lambda x:None)]
  for x in self.patches:x.start()
  p.save(self.root/'ROUTE_PLAN.json',{'allowlisted_probes':[{'source_id':'a','url':'https://example.test/index','purpose':'fixture','allowed_hosts':['example.test']}]})
 def tearDown(self):
  for x in reversed(self.patches):x.stop()
  self.t.cleanup()
 def call(self,response):
  with patch('requests.get',return_value=response) as get:
   r=p.request('a','https://example.test/index','fixture',{'example.test'});self.assertEqual(get.call_count,1);return r
 def response(self,status=200,headers=None,chunks=None):
  return SimpleNamespace(status_code=status,headers=headers or {},url='https://example.test/index',iter_content=lambda n:iter(chunks or [b'12345']),close=lambda:None)
 def test_429_persists_cooldown_and_halt(self):
  r=self.call(self.response(429,{'Retry-After':'120'}));state=p.read(p.STATE);self.assertEqual(r['http_status'],429);self.assertTrue(state['sources']['a']['halted']);self.assertIn('retry_not_before_utc',state['sources']['a'])
  with patch('requests.get') as get:
   with self.assertRaises(RuntimeError):p.request('a','https://example.test/index','fixture',{'example.test'})
   get.assert_not_called()
 def test_403_stops_before_response_body(self):
  r=self.call(self.response(403));self.assertEqual(r['byte_count'],0);self.assertIsNone(r['raw_path'])
 def test_no_automatic_redirect(self):
  r=self.call(self.response(302,{'Location':'https://example.test/login?token=secret'}));self.assertEqual(r['status'],'failed');self.assertNotIn('secret',json.dumps(r))
 def test_partial_stream_counted_on_cap_failure(self):
  r=self.call(self.response(chunks=[b'12345678',b'9012']));self.assertEqual(r['status'],'failed');self.assertEqual(p.raw_account()['partial_bytes'],8);self.assertEqual(r['byte_count'],8)
 def test_oversized_content_length_stops_without_body(self):
  r=self.call(self.response(headers={'Content-Length':'11'}));self.assertEqual(r['byte_count'],0);self.assertFalse((self.root/'raw').exists() and any((self.root/'raw').iterdir()))
 def test_truncation_preserves_partial(self):
  r=self.call(self.response(headers={'Content-Length':'8'}));self.assertEqual(r['status'],'failed');self.assertEqual(p.raw_account()['partial_bytes'],5)
 def test_cap_includes_existing_partial(self):
  (self.root/'raw').mkdir();(self.root/'raw'/'old.part').write_bytes(b'x'*25)
  with self.assertRaises(RuntimeError):p.budget(6)
 def test_storage_reserves_not_double_counted(self):
  with patch.object(p.shutil,'disk_usage',lambda x:SimpleNamespace(free=18*1024**3)):
   with self.assertRaises(RuntimeError):p.budget(10)
  (self.root/'raw').mkdir();(self.root/'raw'/'old.part').write_bytes(b'x'*5)
  r=p.budget(1);self.assertEqual(r['other_activity_remaining_bytes'],1073741824-6)
 def test_frozen_exact_plan_rejects_unapproved_route(self):
  with patch('requests.get') as get:
   with self.assertRaises(RuntimeError):p.request('a','https://example.test/article','fixture',{'example.test'})
   get.assert_not_called()
 def test_halt_applies_to_unattempted_distinct_route(self):
  self.call(self.response(403))
  plan=p.read(self.root/'ROUTE_PLAN.json');plan['allowlisted_probes'].append({'source_id':'a','url':'https://example.test/next','purpose':'fixture','allowed_hosts':['example.test']});p.save(self.root/'ROUTE_PLAN.json',plan)
  with patch('requests.get') as get:
   with self.assertRaises(RuntimeError):p.request('a','https://example.test/next','fixture',{'example.test'})
   get.assert_not_called()
 def test_busy_lock_creates_no_attempt(self):
  def busy():raise BlockingIOError('synthetic busy lock')
  with patch.object(p,'lock',busy),patch('requests.get') as get:
   with self.assertRaises(BlockingIOError):p.request('a','https://example.test/index','fixture',{'example.test'})
   get.assert_not_called();self.assertFalse((self.root/'requests').exists())
 def test_success_hash_and_bytes(self):
  r=self.call(self.response());self.assertEqual(r['status'],'saved_public_route_evidence');self.assertEqual(r['byte_count'],5);self.assertEqual(r['sha256'],p.sha(self.root/r['raw_path']))

if __name__=='__main__':unittest.main(verbosity=2)
