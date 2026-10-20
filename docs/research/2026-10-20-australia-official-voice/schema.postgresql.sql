-- Two research tables; JSON arrays retain all matching terms and known lineage.
CREATE TABLE source_documents (
    doc_id VARCHAR(64) PRIMARY KEY,
    source_channel TEXT NOT NULL, institutional_tier TEXT NOT NULL,
    native_id TEXT NOT NULL, native_unit TEXT NOT NULL, source_version TEXT NOT NULL,
    parent_native_id TEXT, title TEXT,
    publication_date DATE, publication_date_raw TEXT,
    publication_start DATE, publication_end DATE,
    date_granularity TEXT NOT NULL, date_basis TEXT NOT NULL,
    date_status TEXT NOT NULL, publication_month VARCHAR(7),
    author_speaker TEXT, voice_role TEXT NOT NULL DEFAULT 'unresolved', role_evidence TEXT,
    query_match_basis TEXT NOT NULL DEFAULT 'supplied_text_or_title',
    url_source TEXT NOT NULL, doi_or_handle TEXT,
    query_matched JSONB NOT NULL DEFAULT '[]', query_dimensions JSONB NOT NULL DEFAULT '[]',
    excerpt_text TEXT, excerpt_kind TEXT NOT NULL, excerpt_locator TEXT,
    text_readability TEXT NOT NULL, research_use_status TEXT NOT NULL DEFAULT 'unknown',
    related_work_ids JSONB NOT NULL DEFAULT '[]', source_metadata_hash CHAR(64) NOT NULL,
    source_context_json JSONB NOT NULL DEFAULT '{}',
    metadata_version_history JSONB NOT NULL DEFAULT '[]',
    retrieved_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(source_channel, native_id),
    CHECK(publication_start IS NULL OR publication_end >= publication_start),
    CHECK(excerpt_text IS NULL OR char_length(excerpt_text) <= 500)
);
CREATE INDEX idx_doc_pub_date ON source_documents(publication_date);
CREATE INDEX idx_doc_month ON source_documents(publication_month);
CREATE INDEX idx_doc_channel ON source_documents(source_channel);
CREATE INDEX idx_doc_tier ON source_documents(institutional_tier);
CREATE TABLE event_claims (
    event_id TEXT PRIMARY KEY, doc_id VARCHAR(64) NOT NULL REFERENCES source_documents(doc_id),
    event_group_id TEXT, event_type TEXT NOT NULL, location_region TEXT, state TEXT,
    start_date DATE, end_date DATE, date_granularity TEXT NOT NULL DEFAULT 'unknown',
    temp_definition TEXT, temp_value_celsius NUMERIC(8,3),
    verification_status TEXT NOT NULL DEFAULT 'draft',
    evidence_excerpt TEXT NOT NULL, evidence_locator TEXT NOT NULL,
    verified_by TEXT, verified_at TIMESTAMPTZ, notes TEXT,
    CHECK(verification_status IN ('draft','verified','duplicate_candidate','disputed')),
    CHECK(end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
    CHECK(char_length(evidence_excerpt) <= 500),
    CHECK(verification_status != 'verified' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL))
);
CREATE INDEX idx_event_start_date ON event_claims(start_date);
CREATE INDEX idx_event_type ON event_claims(event_type);
