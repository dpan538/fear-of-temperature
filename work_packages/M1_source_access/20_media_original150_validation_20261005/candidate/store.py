"""Persistent separate pilot. Never unlinks data; writes observations transactionally."""
import sqlite3,json,hashlib
from pathlib import Path
from contextlib import contextmanager
from identity import native_parent,native_identity_key
HERE=Path(__file__).resolve().parent

def open_db(path):
 p=Path(path)
 if p.is_symlink():raise RuntimeError('DB symlink forbidden')
 c=sqlite3.connect(p,isolation_level=None);c.execute('PRAGMA foreign_keys=ON')
 ver=c.execute('PRAGMA user_version').fetchone()[0]
 if ver not in {0,3}:c.close();raise RuntimeError('Different schema requires an explicit migration')
 try:c.executescript('BEGIN IMMEDIATE;\n'+(HERE/'schema.sql').read_text()+'\nCOMMIT;')
 except BaseException:
  if c.in_transaction:c.rollback()
  c.close();raise
 return c
@contextmanager
def transaction(c):
 c.execute('BEGIN IMMEDIATE')
 try:yield;c.commit()
 except BaseException:c.rollback();raise

def full_body_verified(parsed,raw_sha,body_sha,review):
 return bool(parsed['identity_status']=='canonical_JSONLD_match' and parsed['eligible_month'] and parsed['readability_status']=='visible_body_boundary_pending' and parsed['body_text'] and review and review.get('status')=='complete_boundary_verified' and review.get('raw_sha256')==raw_sha and review.get('body_sha256')==body_sha and review.get('body_selector')==parsed['body_selector'] and review.get('article_url')==parsed['canonical_url'])

def counts(c):
 return {'article_parents':c.execute('SELECT count(*) FROM article_parent').fetchone()[0],'article_versions':c.execute('SELECT count(*) FROM article_version').fetchone()[0],'verified_full_bodies':c.execute("SELECT count(*) FROM article_version WHERE readability_status='full_boundary_verified'").fetchone()[0],'paper_issues':c.execute('SELECT count(*) FROM paper_issue').fetchone()[0],'OCR_locators':c.execute('SELECT count(*) FROM article_locator').fetchone()[0],'raw_objects':c.execute('SELECT count(*) FROM raw_object').fetchone()[0],'requests':c.execute('SELECT count(*) FROM request_attempt').fetchone()[0]}

def record_observation(c,source,edition,frame_id,parsed,request_meta,raw_path,body_path=None,review=None,fail_after_parent=False):
 """Add evidence once. Eligibility, source/edition and full-body evidence independent."""
 pid=native_parent(source,edition,parsed['canonical_url']);key=native_identity_key(parsed['canonical_url'])
 rawsha=request_meta['sha256'];rid='raw:'+rawsha;version='version:'+hashlib.sha256((pid+rawsha).encode()).hexdigest()[:32]
 body=parsed.get('body_text');bsha=hashlib.sha256(body.encode()).hexdigest() if body is not None else None
 full=bool(body_path and full_body_verified(parsed,rawsha,bsha,review))
 with transaction(c):
  old=c.execute('SELECT source_id,edition_id,native_id FROM article_parent WHERE parent_id=?',(pid,)).fetchone()
  if old and old!=(source,edition,key):raise RuntimeError('Parent identity conflict; no overwrite')
  if not old:c.execute('INSERT INTO article_parent(parent_id,source_id,edition_id,native_id,native_id_basis,canonical_url,genre,publishing_role,first_publication_value,first_date_precision,first_timezone,date_evidence,identity_state) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(pid,source,edition,key,'canonical_URL_fallback_with_declared_edition',parsed['canonical_url'],str(parsed.get('genre','unknown')),'media',parsed.get('first_publication',{}).get('raw'),parsed.get('first_publication',{}).get('precision','unknown'),parsed.get('first_publication',{}).get('timezone'),'matched JSONLD; publication month is source-local; no updated-date substitution',parsed['identity_status']))
  if fail_after_parent:raise RuntimeError('synthetic interrupted transaction')
  if not c.execute('SELECT 1 FROM raw_object WHERE raw_id=?',(rid,)).fetchone():c.execute('INSERT INTO raw_object VALUES(?,?,?,?,?,?,?,?,?,?,?)',(rid,raw_path,rawsha,request_meta['byte_count'],request_meta.get('mime_type'),'article_HTML',0,parsed['rights_status'],'restricted_private_research; no automatic public redistribution',request_meta['request_id'],request_meta['finished_at_utc']))
  record_request(c,source,request_meta,rid)
  if not c.execute('SELECT 1 FROM article_version WHERE version_id=?',(version,)).fetchone():c.execute('INSERT INTO article_version(version_id,parent_id,raw_id,raw_publication_value,updated_value,updated_precision,content_time_precision,retrieved_at_utc,retrieval_precision,body_storage_path,body_sha256,readability_status,preview_status,ocr_quality_status,layout_status,rights_status,access_status,extractor_version,version_evidence) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(version,pid,rid,parsed.get('first_publication',{}).get('raw'),parsed.get('updated',{}).get('raw'),parsed.get('updated',{}).get('precision','unknown'),'unknown',request_meta['finished_at_utc'],'microsecond',body_path,bsha,'full_boundary_verified' if full else parsed['readability_status'],'preview_only' if parsed['readability_status']=='preview_only' else 'not_established','not_applicable_HTML','boundary_review_required',parsed['rights_status'],'HTTP payload retained; not historical content-version proof','media20_metadata_v3',json.dumps({'raw_sha256':rawsha,'body_sha256':bsha,'review':review})))
  if parsed['eligible_month']:c.execute('INSERT OR IGNORE INTO frame_membership VALUES(?,?,?,?,?)',(frame_id,pid,request_meta.get('frame_url',''),1,'Source/edition FK trigger; first publication month checked'))
  c.execute('INSERT OR IGNORE INTO provenance_assertion(assertion_id,parent_id,version_id,provenance_class,identity_verification,date_mapping_verification,content_mapping_verification,evidence_locator,access_limit) VALUES(?,?,?,?,?,?,?,?,?)',('provenance:'+version,pid,version,'unresolved','canonical JSONLD match; original/member/syndication mapping pending','JSONLD first-publication calendar/month checked; independent displayed-date check pending','body boundary verified' if full else 'pending',raw_path,'retrieval is current version; historical body not established'))
 return {'parent_id':pid,'version_id':version,'full_body_verified':full,'body_sha256':bsha}

def record_request(c,source,r,raw_id=None):
 old=c.execute('SELECT source_id,request_url,status FROM request_attempt WHERE request_id=?',(r['request_id'],)).fetchone()
 values=(source,r.get('request_url','synthetic://fixture'),r.get('status','synthetic_fixture'))
 if old and old!=values:raise RuntimeError('Request identity conflict; no overwrite')
 if not old:c.execute('INSERT INTO request_attempt(request_id,source_id,purpose,request_url,requested_at_utc,finished_at_utc,http_status,status,final_url,response_headers_json,raw_id,error,retry_not_before_utc,transport) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(r['request_id'],source,r.get('purpose','synthetic_fixture'),values[1],r.get('requested_at_utc',r['finished_at_utc']),r['finished_at_utc'],r.get('http_status'),values[2],r.get('final_url'),json.dumps(r.get('response_headers',{})),raw_id,r.get('error'),r.get('retry_not_before_utc'),'synthetic' if r.get('synthetic') else 'requests_no_redirect_no_retry'))

def finalize_review(c,version_id,parsed,review,root):
 """Only offline review of the exact retained version; never creates a body/request."""
 row=c.execute('SELECT r.path,r.sha256,v.body_storage_path,v.body_sha256 FROM article_version v JOIN raw_object r ON r.raw_id=v.raw_id WHERE version_id=?',(version_id,)).fetchone()
 if not row or not row[2]:raise RuntimeError('No retained body for this version')
 raw_path,rawsha,body_path,bsha=row
 if hashlib.sha256((Path(root)/raw_path).read_bytes()).hexdigest()!=rawsha or hashlib.sha256((Path(root)/body_path).read_bytes()).hexdigest()!=bsha:raise RuntimeError('Retained hash mismatch')
 if not full_body_verified(parsed,rawsha,bsha,review):raise RuntimeError('Complete-boundary review not substantiated')
 with transaction(c):
  c.execute("UPDATE article_version SET readability_status='full_boundary_verified',layout_status='complete_boundary_verified',version_evidence=? WHERE version_id=?",(json.dumps({'raw_sha256':rawsha,'body_sha256':bsha,'review':review}),version_id))
  c.execute("UPDATE provenance_assertion SET content_mapping_verification='body boundary verified; original/member/syndication classification pending' WHERE version_id=?",(version_id,))
