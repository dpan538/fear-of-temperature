"""Owner-only newspaper staging; fixtures and non-newspaper diagnostics are separate."""
from __future__ import annotations
import datetime as dt
import fcntl
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS requests(
 request_id TEXT PRIMARY KEY, receipt_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS articles(
 article_id TEXT PRIMARY KEY, lane TEXT NOT NULL CHECK(lane IN ('newspaper','diagnostic','fixture')),
 source_id TEXT NOT NULL, native_id TEXT NOT NULL, acquisition_parent TEXT NOT NULL,
 stratum TEXT NOT NULL, country TEXT NOT NULL, edition TEXT NOT NULL,
 publication_date TEXT NOT NULL, publication_precision TEXT NOT NULL,
 unit_kind TEXT NOT NULL, provenance TEXT NOT NULL,
 newspaper_eligible INTEGER NOT NULL CHECK(newspaper_eligible IN (0,1)),
 UNIQUE(lane,source_id,native_id));
CREATE TABLE IF NOT EXISTS versions(
 version_id TEXT PRIMARY KEY, article_id TEXT NOT NULL REFERENCES articles(article_id),
 request_id TEXT NOT NULL REFERENCES requests(request_id), raw_path TEXT NOT NULL,
 raw_sha256 TEXT NOT NULL, body_path TEXT NOT NULL, body_sha256 TEXT NOT NULL,
 parser_sha256 TEXT NOT NULL, retrieved_at TEXT NOT NULL,
 content_version_time TEXT, historical_version_equivalence TEXT NOT NULL,
 qualified_readable INTEGER NOT NULL CHECK(qualified_readable IN (0,1)),
 extraction_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cursors(
 lane TEXT NOT NULL, source_id TEXT NOT NULL, cursor_json TEXT NOT NULL,
 updated_at TEXT NOT NULL, PRIMARY KEY(lane,source_id));
'''

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',',':')).encode()).hexdigest()

@contextmanager
def writer(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep lock inode. Never unlink it, including after exception/restart.
    with path.with_suffix('.writer.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        con = sqlite3.connect(path)
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA synchronous=FULL')
        con.executescript(SCHEMA)
        try:
            yield con
        finally:
            con.close()

def ingest(con, record, version, receipt, cursor, *, interrupt_after_version=False):
    lane = record['lane']
    day = record['publication_date']
    dt.date.fromisoformat(day)
    if not '1988-01-01' <= day <= '2026-09-21':
        raise ValueError('Publication is outside the fixed interval')
    if record['unit_kind'] != 'article' and record['newspaper_eligible']:
        raise ValueError('Issue/page/post cannot be a newspaper article parent')
    if lane != 'newspaper' and record['newspaper_eligible']:
        raise ValueError('Diagnostics/fixtures cannot contribute newspaper coverage')
    if version['qualified_readable'] and (not record['newspaper_eligible'] or
                                         record['unit_kind'] != 'article'):
        raise ValueError('Only reviewed newspaper articles qualify')
    for key in ('raw_sha256','body_sha256','parser_sha256'):
        if len(version[key]) != 64:
            raise ValueError('Exact SHA256 required: ' + key)
    aid = canonical_hash([lane,record['source_id'],record['native_id']])
    vid = canonical_hash([aid,version['raw_sha256'],version['body_sha256'],version['parser_sha256']])
    con.execute('BEGIN IMMEDIATE')
    try:
        con.execute('INSERT OR IGNORE INTO requests VALUES (?,?)',
                    (receipt['request_id'],json.dumps(receipt,sort_keys=True)))
        values = [aid] + [record[k] for k in ('lane','source_id','native_id','acquisition_parent',
                 'stratum','country','edition','publication_date','publication_precision',
                 'unit_kind','provenance','newspaper_eligible')]
        con.execute('INSERT OR IGNORE INTO articles VALUES ('+','.join('?' for _ in values)+')',values)
        existing = con.execute('SELECT * FROM articles WHERE article_id=?',(aid,)).fetchone()
        if existing != tuple(values):
            raise ValueError('Conflicting parent metadata requires explicit resolution')
        values = [vid,aid,receipt['request_id']] + [version[k] for k in ('raw_path','raw_sha256',
                 'body_path','body_sha256','parser_sha256','retrieved_at','content_version_time',
                 'historical_version_equivalence','qualified_readable','extraction_json')]
        inserted = con.execute('INSERT OR IGNORE INTO versions VALUES ('+','.join('?' for _ in values)+')',values).rowcount
        if interrupt_after_version:
            raise RuntimeError('Injected fixture interruption before cursor commit')
        con.execute('INSERT INTO cursors VALUES (?,?,?,?) ON CONFLICT(lane,source_id) DO UPDATE SET cursor_json=excluded.cursor_json,updated_at=excluded.updated_at',
                    (lane,record['source_id'],json.dumps(cursor,sort_keys=True),dt.datetime.now(dt.timezone.utc).isoformat()))
        con.commit()
    except BaseException:
        con.rollback()
        raise
    return {'article_id':aid,'version_id':vid,'new_versions_inserted':inserted}

def snapshot(con):
    return {'articles_by_lane':dict(con.execute('SELECT lane,count(*) FROM articles GROUP BY lane')),
            'versions':con.execute('SELECT count(*) FROM versions').fetchone()[0],
            'qualified_newspaper_articles':con.execute("SELECT count(DISTINCT a.article_id) FROM articles a JOIN versions v USING(article_id) WHERE a.lane='newspaper' AND a.newspaper_eligible=1 AND v.qualified_readable=1").fetchone()[0],
            'cursors':[{'lane':r[0],'source_id':r[1],'cursor':json.loads(r[2]),'updated_at':r[3]}
                       for r in con.execute('SELECT * FROM cursors')]}
