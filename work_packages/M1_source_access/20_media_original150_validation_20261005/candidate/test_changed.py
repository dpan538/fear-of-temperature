"""Targeted synthetic tests only; sockets disabled for all checks."""
import sys
sys.dont_write_bytecode=True
import unittest,tempfile,socket,json,sqlite3,hashlib
from pathlib import Path
from unittest.mock import patch
import store,metadata,transport
from run import insert
class Changed(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.path=Path(self.t.name)/'pilot.sqlite';self.c=store.open_db(self.path)
  insert(self.c,'publisher',{'publisher_id':'pub','name':'fixture','hq_verification':'fixture'})
  for src in ['a','b']:
   insert(self.c,'outlet',{'source_id':src,'publisher_id':'pub','outlet_name':src,'outlet_type':'fixture','official_home':'https://example.test'})
  for ed,src in [('a','a'),('a2','a'),('b','b')]:insert(self.c,'edition',{'edition_id':ed,'source_id':src,'region_layer':'UK','edition_market':'fixture','edition_verification':'fixture','region_assignment_basis':'fixture'})
  insert(self.c,'source_era',{'era_id':'era','edition_id':'a','month':'2025-07','medium':'fixture','applicability':'fixture','era_scope_note':'fixture','rights_status':'fixture','access_status':'fixture'})
  insert(self.c,'frame',{'frame_id':'f','era_id':'era','provider':'a','month':'2025-07','unit':'article_publication_instance','date_filter_json':'{}','type_filter_json':'{}','enumeration_state':'partial','page_limit':1,'scope_detail':'fixture'})
  for p,src,ed in [('x','a','a'),('y','a','a2'),('z','b','b')]:insert(self.c,'article_parent',{'parent_id':p,'source_id':src,'edition_id':ed,'native_id':p,'native_id_basis':'fixture','canonical_url':'https://example.test/'+p,'genre':'fixture','publishing_role':'media','first_date_precision':'unknown','identity_state':'fixture'})
 def tearDown(self):self.c.close();self.t.cleanup()
 def slot(self,p):insert(self.c,'sample_slot',{'slot_id':'s','frame_id':'f','slot_index':1,'parent_id':p,'status':'fixture','selection_design':'nonprobability','planned_region_weight':.2,'planned_source_within_region_weight':.5})
 def test_persistent_reopen_keeps_prior_rows(self):
  self.c.close();self.c=store.open_db(self.path);self.assertEqual(self.c.execute('SELECT count(*) FROM article_parent').fetchone()[0],3)
 def test_observation_rolls_back_parent_on_interruption(self):
  p=self.parsed();r=self.req()
  with self.assertRaises(RuntimeError):store.record_observation(self.c,'a','a','f',p,r,'fixture.raw',fail_after_parent=True)
  self.assertEqual(self.c.execute('SELECT count(*) FROM article_parent').fetchone()[0],3)
 def test_slot_other_source_rejected(self):
  with self.assertRaises(sqlite3.IntegrityError):self.slot('z')
 def test_slot_other_edition_rejected_insert_update(self):
  with self.assertRaises(sqlite3.IntegrityError):self.slot('y')
  self.slot('x')
  with self.assertRaises(sqlite3.IntegrityError):self.c.execute("UPDATE sample_slot SET parent_id='y'")
 def test_membership_other_edition_rejected(self):
  with self.assertRaises(sqlite3.IntegrityError):insert(self.c,'frame_membership',{'frame_id':'f','parent_id':'y','index_url':'fixture','index_occurrence_count':1})
 def test_frame_era_reassignment_rejected(self):
  with self.assertRaises(sqlite3.IntegrityError):self.c.execute("UPDATE source_era SET edition_id='a2'")
 def test_parent_edition_reassignment_cannot_bypass_locators(self):
  with self.assertRaises(sqlite3.IntegrityError):self.c.execute("UPDATE article_parent SET edition_id='a2' WHERE parent_id='x'")
 def test_provenance_version_cannot_switch_parent(self):
  for p,v in [('x','vx'),('y','vy')]:insert(self.c,'article_version',{'version_id':v,'parent_id':p,'updated_precision':'unknown','content_time_precision':'unknown','retrieved_at_utc':'fixture','retrieval_precision':'fixture','readability_status':'fixture','preview_status':'fixture','ocr_quality_status':'fixture','layout_status':'fixture','rights_status':'fixture','access_status':'fixture','extractor_version':'fixture'})
  values={'assertion_id':'p','parent_id':'x','version_id':'vy','provenance_class':'unresolved','identity_verification':'fixture','date_mapping_verification':'fixture','content_mapping_verification':'fixture','evidence_locator':'fixture'}
  with self.assertRaises(sqlite3.IntegrityError):insert(self.c,'provenance_assertion',values)
  values['version_id']='vx';insert(self.c,'provenance_assertion',values)
  with self.assertRaises(sqlite3.IntegrityError):self.c.execute("UPDATE provenance_assertion SET version_id='vy'")
 def html(self,articles=None,extra=''):
  data=articles or [{'@type':'NewsArticle','mainEntityOfPage':'https://example.test/a','datePublished':'2025-07-03T12:00:00Z','dateModified':'2026-10-01','articleBody':'metadata body','license':'https://creativecommons.org/licenses/by/4.0/'}]
  return ('<html><link rel="canonical" href="/a"><script type="application/ld+json">'+json.dumps(data)+'</script><article><div class="entry-content">Routine notice.</div></article>'+extra+'</html>').encode()
 def parsed(self):return metadata.extract(self.html(),'https://example.test/a','2025-07','.entry-content')
 def req(self):return {'sha256':'fixture_raw_sha','request_id':'fixture_request','byte_count':100,'finished_at_utc':'2026-10-05T03:00:00Z'}
 def test_invalid_calendar_date_not_eligible(self):self.assertFalse(metadata.eligible('2025-02-30','2025-02'))
 def test_updated_never_substitutes_first_publication(self):
  x=metadata.extract(self.html([{'@type':'Article','url':'https://example.test/a','dateModified':'2025-07-03'}]),'https://example.test/a','2025-07');self.assertFalse(x['eligible_month'])
 def test_relative_canonical_matches(self):self.assertEqual(self.parsed()['canonical_url'],'https://example.test/a')
 def test_recommendation_node_not_selected(self):
  x=metadata.extract(self.html([{'@type':'Article','url':'https://example.test/other','datePublished':'2025-07-02'},{'@type':'Article','url':'https://example.test/a','datePublished':'2025-07-03'}]),'https://example.test/a','2025-07');self.assertTrue(x['eligible_month'])
 def test_two_conflicting_matching_nodes_remain_pending(self):
  x=metadata.extract(self.html([{'@type':'Article','url':'https://example.test/a'},{'@type':'NewsArticle','url':'https://example.test/a'}]),'https://example.test/a','2025-07');self.assertEqual(x['identity_status'],'ambiguous_or_unbound_article_nodes')
 def test_captcha_word_not_access_challenge(self):self.assertFalse(metadata.challenge(self.html(extra='<p>Privacy uses reCAPTCHA.</p>'))['stop'])
 def test_incapsula_empty_shell_stops(self):self.assertTrue(metadata.challenge(b'<html><script src="/_Incapsula_Resource"></script></html>')['stop'])
 def test_JSONLD_and_visible_body_not_automatic_full(self):
  p=self.parsed();self.assertFalse(store.full_body_verified(p,'x','y',None));self.assertEqual(p['readability_status'],'visible_body_boundary_pending')
 def test_review_hash_mismatch_prevents_full_body(self):
  p=self.parsed();review={'status':'complete_boundary_verified','raw_sha256':'wrong','body_sha256':'y','body_selector':p['body_selector'],'article_url':p['canonical_url']};self.assertFalse(store.full_body_verified(p,'x','y',review))
 def test_idempotent_observation_retains_one_parent_version(self):
  p=self.parsed();r=self.req();store.record_observation(self.c,'a','a','f',p,r,'fixture.raw');store.record_observation(self.c,'a','a','f',p,r,'fixture.raw');self.assertEqual(store.counts(self.c)['article_versions'],1);self.assertEqual(store.counts(self.c)['verified_full_bodies'],0)
 def test_missing_release_fails_without_network(self):
  with patch.object(transport,'OUT',Path(self.t.name)):
   with self.assertRaises(RuntimeError):transport.check_release(Path(self.t.name)/'plan.json')
if __name__=='__main__':
 with patch.object(socket,'socket',side_effect=RuntimeError('NETWORK DENIED')):unittest.main(verbosity=2)
