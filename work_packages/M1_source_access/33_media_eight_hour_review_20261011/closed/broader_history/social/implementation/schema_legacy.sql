CREATE TABLE IF NOT EXISTS posts (
 persistent_post_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
 native_post_id TEXT NOT NULL, source_url TEXT NOT NULL,
 native_unit TEXT NOT NULL, thread_id TEXT NOT NULL, reply_to_post_id TEXT,
 native_created_at TEXT NOT NULL, author_id TEXT, author_role TEXT NOT NULL,
 author_country TEXT, context_status TEXT NOT NULL,
 UNIQUE(source_id,native_unit,native_post_id)
);
CREATE TABLE IF NOT EXISTS native_identities (
 source_id TEXT NOT NULL, native_namespace TEXT NOT NULL, native_post_id TEXT NOT NULL,
 persistent_post_id TEXT NOT NULL REFERENCES posts(persistent_post_id),
 identity_basis TEXT NOT NULL,
 PRIMARY KEY(source_id,native_namespace,native_post_id)
);
CREATE TABLE IF NOT EXISTS post_urls (
 persistent_post_id TEXT NOT NULL REFERENCES posts(persistent_post_id),
 source_url TEXT NOT NULL, request_id TEXT NOT NULL,
 canonical_or_alias TEXT NOT NULL, PRIMARY KEY(persistent_post_id,source_url)
);
CREATE TABLE IF NOT EXISTS parent_context (
 persistent_post_id TEXT PRIMARY KEY REFERENCES posts(persistent_post_id),
 parent_namespace TEXT, parent_native_post_id TEXT, root_thread_id TEXT,
 context_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS versions (
 body_version_id TEXT PRIMARY KEY,
 persistent_post_id TEXT NOT NULL REFERENCES posts(persistent_post_id),
 body_sha256 TEXT NOT NULL, body_original TEXT NOT NULL, body_text TEXT NOT NULL,
 native_edited_at TEXT, native_revision TEXT, first_retrieved_at TEXT NOT NULL,
 content_license TEXT NOT NULL, license_basis TEXT NOT NULL,
 completeness TEXT NOT NULL, provenance TEXT NOT NULL, native_fields_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS responses (
 request_id TEXT PRIMARY KEY, request_url TEXT NOT NULL, retrieved_at TEXT NOT NULL,
 raw_reference TEXT NOT NULL, raw_sha256 TEXT NOT NULL, stored_sha256 TEXT NOT NULL,
 raw_bytes INTEGER NOT NULL, stored_bytes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
 body_version_id TEXT NOT NULL REFERENCES versions(body_version_id),
 request_id TEXT NOT NULL REFERENCES responses(request_id), retrieved_at TEXT NOT NULL,
 PRIMARY KEY(body_version_id,request_id)
);
CREATE INDEX IF NOT EXISTS posts_source_date ON posts(source_id,native_created_at);
