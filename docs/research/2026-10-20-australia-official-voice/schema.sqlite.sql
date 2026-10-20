PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS source_documents (
    doc_id TEXT PRIMARY KEY CHECK(length(doc_id)=64),
    source_channel TEXT NOT NULL,
    institutional_tier TEXT NOT NULL,
    native_id TEXT NOT NULL,
    native_unit TEXT NOT NULL,
    source_version TEXT NOT NULL,
    parent_native_id TEXT,
    title TEXT,
    publication_date TEXT,
    publication_date_raw TEXT,
    publication_start TEXT,
    publication_end TEXT,
    date_granularity TEXT NOT NULL,
    date_basis TEXT NOT NULL,
    date_status TEXT NOT NULL,
    publication_month TEXT,
    author_speaker TEXT,
    voice_role TEXT NOT NULL DEFAULT 'unresolved',
    role_evidence TEXT,
    query_match_basis TEXT NOT NULL DEFAULT 'supplied_text_or_title',
    url_source TEXT NOT NULL,
    doi_or_handle TEXT,
    query_matched TEXT NOT NULL,
    query_dimensions TEXT NOT NULL,
    excerpt_text TEXT,
    excerpt_kind TEXT NOT NULL,
    excerpt_locator TEXT,
    text_readability TEXT NOT NULL,
    research_use_status TEXT NOT NULL DEFAULT 'unknown',
    related_work_ids TEXT NOT NULL DEFAULT '[]',
    source_context_json TEXT NOT NULL DEFAULT '{}',
    source_metadata_hash TEXT NOT NULL,
    metadata_version_history TEXT NOT NULL DEFAULT '[]',
    retrieved_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(source_channel, native_id),
    CHECK(publication_start IS NULL OR publication_end >= publication_start)
);
CREATE INDEX IF NOT EXISTS idx_doc_pub_date ON source_documents(publication_date);
CREATE INDEX IF NOT EXISTS idx_doc_month ON source_documents(publication_month);
CREATE INDEX IF NOT EXISTS idx_doc_channel ON source_documents(source_channel);
CREATE INDEX IF NOT EXISTS idx_doc_tier ON source_documents(institutional_tier);
CREATE INDEX IF NOT EXISTS idx_doc_status ON source_documents(date_status);
CREATE TRIGGER IF NOT EXISTS source_excerpt_insert_bound BEFORE INSERT ON source_documents
WHEN length(NEW.excerpt_text) > 500
BEGIN SELECT RAISE(ABORT, 'excerpt exceeds 500 characters'); END;
CREATE TRIGGER IF NOT EXISTS source_excerpt_update_bound BEFORE UPDATE ON source_documents
WHEN length(NEW.excerpt_text) > 500
BEGIN SELECT RAISE(ABORT, 'excerpt exceeds 500 characters'); END;
CREATE TABLE IF NOT EXISTS event_claims (
    event_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES source_documents(doc_id),
    event_group_id TEXT,
    event_type TEXT NOT NULL,
    location_region TEXT,
    state TEXT,
    start_date TEXT,
    end_date TEXT,
    date_granularity TEXT NOT NULL DEFAULT 'unknown',
    temp_definition TEXT,
    temp_value_celsius NUMERIC,
    verification_status TEXT NOT NULL DEFAULT 'draft'
        CHECK(verification_status IN ('draft','verified','duplicate_candidate','disputed')),
    evidence_excerpt TEXT NOT NULL,
    evidence_locator TEXT NOT NULL,
    verified_by TEXT,
    verified_at TEXT,
    notes TEXT,
    CHECK(end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
    CHECK(verification_status != 'verified' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_event_start_date ON event_claims(start_date);
CREATE INDEX IF NOT EXISTS idx_event_type ON event_claims(event_type);
CREATE TRIGGER IF NOT EXISTS claim_excerpt_insert_bound BEFORE INSERT ON event_claims
WHEN length(NEW.evidence_excerpt) > 500
BEGIN SELECT RAISE(ABORT, 'claim excerpt exceeds 500 characters'); END;
CREATE TRIGGER IF NOT EXISTS claim_excerpt_update_bound BEFORE UPDATE ON event_claims
WHEN length(NEW.evidence_excerpt) > 500
BEGIN SELECT RAISE(ABORT, 'claim excerpt exceeds 500 characters'); END;
-- Operational receipts are not a third research table or a full-text cache.
CREATE TABLE IF NOT EXISTS ingest_pages (
    job_id TEXT NOT NULL, page_key TEXT NOT NULL, source_channel TEXT NOT NULL,
    request_url TEXT NOT NULL, response_hash TEXT NOT NULL, observed_rows INTEGER NOT NULL,
    saved_matches INTEGER NOT NULL, next_cursor TEXT, fetched_at TEXT NOT NULL,
    PRIMARY KEY(job_id, page_key)
);
CREATE TABLE IF NOT EXISTS ingest_jobs (
    job_id TEXT PRIMARY KEY, source_channel TEXT NOT NULL, state TEXT NOT NULL,
    cursor TEXT, detail TEXT, updated_at TEXT NOT NULL
);
