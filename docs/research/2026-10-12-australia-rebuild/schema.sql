-- Australian rebuild contract v1. Reference design; NOT an executed migration.
-- SQLite is used for small standard-library conformance fixtures only.
PRAGMA foreign_keys = ON;

CREATE TABLE dataset_contract (
  contract_id TEXT PRIMARY KEY,
  publication_start TEXT NOT NULL CHECK (publication_start = '1988-01-01'),
  publication_end TEXT NOT NULL CHECK (publication_end = '2026-09-21'),
  peak_envelope_bytes INTEGER NOT NULL CHECK (peak_envelope_bytes = 100000000000),
  physical_floor_bytes INTEGER NOT NULL CHECK (physical_floor_bytes = 16106127360),
  status TEXT NOT NULL CHECK (status IN ('design_only', 'synthetic_conformance'))
);

CREATE TABLE archive_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  reference_path TEXT NOT NULL,
  reference_digest TEXT,
  digest_basis TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  preservation_status TEXT NOT NULL CHECK (preservation_status = 'preserve_in_place')
);
CREATE TABLE archive_records (
  archive_record_id TEXT PRIMARY KEY,
  snapshot_id TEXT NOT NULL REFERENCES archive_snapshots,
  original_id TEXT NOT NULL,
  original_version_id TEXT NOT NULL,
  locator TEXT NOT NULL,
  recorded_content_hash TEXT,
  hash_basis TEXT NOT NULL,
  raw_reference TEXT,
  UNIQUE(snapshot_id, original_id, original_version_id, locator)
);

CREATE TABLE sources (
  source_id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  stream TEXT NOT NULL CHECK (stream IN ('institutional', 'newspaper', 'public_civic'))
);
CREATE TABLE source_assertions (
  assertion_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources,
  australian_context_basis TEXT NOT NULL CHECK (australian_context_basis IN
    ('australian_institution', 'australian_publisher', 'australian_community', 'outside_scope', 'unknown')),
  australian_context_state TEXT NOT NULL CHECK (australian_context_state IN ('verified', 'pending', 'conflict', 'outside_scope')),
  identity_state TEXT NOT NULL CHECK (identity_state IN ('verified', 'pending', 'conflict')),
  genre TEXT NOT NULL,
  context_as_of TEXT,
  evidence_locator TEXT NOT NULL,
  applicability_start TEXT,
  applicability_end TEXT,
  applicability_state TEXT NOT NULL CHECK (applicability_state IN ('verified', 'pending', 'unknown'))
);
CREATE TABLE source_relations (
  relation_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources,
  relation_type TEXT NOT NULL CHECK (relation_type IN
    ('legal_publisher', 'title_edition', 'acquisition_parent', 'archive_reproduction', 'community', 'author_account', 'named_person')),
  target_key TEXT NOT NULL,
  valid_from TEXT,
  valid_to TEXT,
  verification_state TEXT NOT NULL CHECK (verification_state IN ('verified', 'pending', 'conflict')),
  evidence_locator TEXT NOT NULL
);
CREATE TABLE rights_assertions (
  rights_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources,
  public_access TEXT NOT NULL CHECK (public_access IN ('allowed', 'denied', 'unknown', 'conditional')),
  local_retention TEXT NOT NULL CHECK (local_retention IN ('allowed', 'denied', 'unknown', 'conditional')),
  internal_analysis TEXT NOT NULL CHECK (internal_analysis IN ('allowed', 'denied', 'unknown', 'conditional')),
  redistribution TEXT NOT NULL CHECK (redistribution IN ('allowed', 'denied', 'unknown', 'conditional')),
  licence TEXT NOT NULL,
  intended_use TEXT NOT NULL,
  conditions TEXT NOT NULL,
  evidence_locator TEXT NOT NULL,
  checked_at TEXT NOT NULL
);

CREATE TABLE units (
  unit_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources,
  native_namespace TEXT NOT NULL,
  native_id TEXT NOT NULL,
  unit_kind TEXT NOT NULL CHECK (unit_kind IN
    ('news_article', 'public_letter', 'civic_submission', 'social_post', 'social_reply', 'social_question', 'social_answer', 'social_comment',
     'context_container', 'repost', 'preview', 'parliament_sitting', 'parliament_procedural_unit',
     'parliament_utterance', 'parliament_paragraph', 'government_document', 'petition',
     'ministerial_response', 'signature_count_context')),
  UNIQUE(source_id, native_namespace, native_id)
);
CREATE TABLE metadata_versions (
  metadata_version_id TEXT PRIMARY KEY,
  unit_id TEXT NOT NULL REFERENCES units,
  source_assertion_id TEXT NOT NULL REFERENCES source_assertions,
  source_url TEXT NOT NULL,
  publication_value TEXT,
  publication_precision TEXT NOT NULL CHECK (publication_precision IN ('timestamp', 'day', 'month', 'year', 'unknown')),
  publication_lower_day TEXT,
  publication_upper_day TEXT,
  publication_timezone TEXT,
  date_state TEXT NOT NULL CHECK (date_state IN ('verified', 'pending', 'conflict', 'failed', 'outside_scope')),
  date_evidence TEXT NOT NULL,
  native_identity_state TEXT NOT NULL CHECK (native_identity_state IN ('verified', 'pending', 'conflict')),
  author_native_id TEXT,
  author_geography TEXT,
  author_geography_basis TEXT NOT NULL DEFAULT 'unmeasured',
  retrieved_at TEXT NOT NULL,
  extracted_at TEXT,
  content_version_at TEXT,
  report_at TEXT NOT NULL,
  original_metadata_json TEXT NOT NULL,
  CHECK(publication_lower_day IS NULL OR publication_upper_day IS NULL OR publication_lower_day <= publication_upper_day)
);
CREATE TABLE unit_urls (
  unit_id TEXT NOT NULL REFERENCES units,
  url TEXT NOT NULL,
  relationship TEXT NOT NULL CHECK (relationship IN ('original', 'canonical', 'alias', 'archival_reproduction')),
  verification_state TEXT NOT NULL CHECK (verification_state IN ('verified', 'pending', 'conflict')),
  evidence_locator TEXT NOT NULL,
  PRIMARY KEY(unit_id, url, relationship)
);

-- Body hashes identify a version of this native unit, never independent authors/works.
CREATE TABLE content_versions (
  content_version_id TEXT PRIMARY KEY,
  unit_id TEXT NOT NULL REFERENCES units,
  archive_record_id TEXT NOT NULL REFERENCES archive_records,
  original_text_sha256 TEXT,
  original_format TEXT NOT NULL,
  source_bytes_sha256 TEXT,
  source_bytes_hash_basis TEXT NOT NULL,
  native_revision TEXT,
  content_version_at TEXT,
  provenance_type TEXT NOT NULL CHECK (provenance_type IN
    ('direct_original', 'archival_reproduction', 'indirect_secondary', 'mixed', 'unresolved')),
  provenance_evidence TEXT NOT NULL,
  completeness_state TEXT NOT NULL CHECK (completeness_state IN ('verified_complete', 'native_context', 'pending', 'confirmed_incomplete')),
  original_reference TEXT NOT NULL
);
CREATE TABLE text_representations (
  representation_id TEXT PRIMARY KEY,
  content_version_id TEXT NOT NULL REFERENCES content_versions,
  representation_kind TEXT NOT NULL CHECK (representation_kind IN ('original', 'structural_derived', 'ocr')),
  text_sha256 TEXT NOT NULL,
  text_value TEXT,
  external_reference TEXT,
  extraction_rule TEXT NOT NULL,
  extraction_rule_version TEXT NOT NULL,
  evidence_locator TEXT NOT NULL,
  CHECK((text_value IS NOT NULL) != (external_reference IS NOT NULL))
);
CREATE TABLE content_source_parts (
  content_version_id TEXT NOT NULL REFERENCES content_versions,
  part_ordinal INTEGER NOT NULL CHECK (part_ordinal >= 0),
  source_locator TEXT NOT NULL,
  source_object_hash TEXT,
  hash_basis TEXT NOT NULL,
  part_role TEXT NOT NULL CHECK (part_role IN ('whole_native_body', 'page', 'column', 'attachment', 'native_json_field', 'xml_node')),
  page_number INTEGER,
  source_span_json TEXT NOT NULL,
  evidence_locator TEXT NOT NULL,
  PRIMARY KEY(content_version_id, part_ordinal)
);
CREATE TABLE unit_versions (
  unit_version_id TEXT PRIMARY KEY,
  unit_id TEXT NOT NULL REFERENCES units,
  metadata_version_id TEXT NOT NULL REFERENCES metadata_versions,
  content_version_id TEXT REFERENCES content_versions,
  rights_id TEXT NOT NULL REFERENCES rights_assertions,
  independently_authored_body INTEGER NOT NULL CHECK (independently_authored_body IN (0,1)),
  recorded_at TEXT NOT NULL
);
CREATE TABLE unit_relations (
  relation_id TEXT PRIMARY KEY,
  child_unit_id TEXT NOT NULL REFERENCES units,
  relation_type TEXT NOT NULL CHECK (relation_type IN
    ('in_sitting', 'in_procedural_unit', 'in_utterance', 'paragraph_order', 'reply_to', 'thread_context',
     'repost_of', 'quotes_remote', 'attachment_of', 'syndicated_from', 'mirror_of', 'identity_resolution')),
  target_source_id TEXT NOT NULL,
  target_namespace TEXT NOT NULL,
  target_native_id TEXT NOT NULL,
  target_unit_id TEXT REFERENCES units,
  ordinal INTEGER CHECK (ordinal IS NULL OR ordinal >= 0),
  verification_state TEXT NOT NULL CHECK (verification_state IN ('verified', 'pending', 'conflict')),
  evidence_locator TEXT NOT NULL
);
CREATE TABLE speaker_role_assertions (
  role_assertion_id TEXT PRIMARY KEY,
  unit_id TEXT NOT NULL REFERENCES units,
  speaker_native_id TEXT NOT NULL,
  role_type TEXT NOT NULL CHECK (role_type IN ('speaker', 'party', 'executive_office', 'government_opposition', 'quoted_holder')),
  role_value TEXT NOT NULL,
  valid_from TEXT,
  valid_to TEXT,
  verification_state TEXT NOT NULL CHECK (verification_state IN ('verified', 'pending', 'conflict')),
  evidence_locator TEXT NOT NULL
);

CREATE TABLE admission_ledger (
  ledger_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  decision_id TEXT NOT NULL UNIQUE,
  archive_record_id TEXT NOT NULL REFERENCES archive_records,
  unit_version_id TEXT NOT NULL REFERENCES unit_versions,
  disposition TEXT NOT NULL CHECK (disposition IN ('admitted', 'context_only', 'pending', 'quarantine', 'restricted', 'archive_only')),
  reason_codes_json TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  reviewed_at TEXT NOT NULL,
  contract_id TEXT NOT NULL REFERENCES dataset_contract
);
CREATE TABLE admission_checks (
  decision_id TEXT NOT NULL REFERENCES admission_ledger(decision_id),
  check_name TEXT NOT NULL CHECK (check_name IN ('source', 'identity', 'publication_date', 'native_unit', 'content', 'rights', 'lineage')),
  check_state TEXT NOT NULL CHECK (check_state IN ('verified', 'pending', 'conflict', 'failed', 'outside_scope', 'restricted', 'not_applicable')),
  reason_code TEXT NOT NULL,
  evidence_locator TEXT NOT NULL,
  PRIMARY KEY(decision_id, check_name)
);
CREATE TABLE archive_to_new_map (
  archive_record_id TEXT NOT NULL REFERENCES archive_records,
  unit_version_id TEXT NOT NULL REFERENCES unit_versions,
  decision_id TEXT NOT NULL REFERENCES admission_ledger(decision_id),
  mapping_state TEXT NOT NULL CHECK (mapping_state IN ('accepted', 'context', 'proposed', 'withheld')),
  original_id TEXT NOT NULL,
  original_version_id TEXT NOT NULL,
  original_recorded_hash TEXT,
  new_unit_id TEXT NOT NULL REFERENCES units,
  new_content_version_id TEXT REFERENCES content_versions,
  new_original_text_hash TEXT,
  PRIMARY KEY(archive_record_id, unit_version_id, decision_id)
);
CREATE TABLE structural_changes (
  change_id TEXT PRIMARY KEY,
  archive_record_id TEXT NOT NULL REFERENCES archive_records,
  unit_version_id TEXT NOT NULL REFERENCES unit_versions,
  field_name TEXT NOT NULL,
  prior_value_json TEXT NOT NULL,
  derived_value_json TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  evidence_locator TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  reviewed_at TEXT NOT NULL,
  derived_representation_id TEXT REFERENCES text_representations
);

-- Reserved downstream lineage, not generated by this adapter or its tests.
CREATE TABLE passages (
  passage_id TEXT PRIMARY KEY,
  representation_id TEXT NOT NULL REFERENCES text_representations,
  start_character INTEGER NOT NULL CHECK (start_character >= 0),
  end_character INTEGER NOT NULL CHECK (end_character > start_character),
  segmentation_rule TEXT NOT NULL,
  segmentation_rule_version TEXT NOT NULL,
  overlap_group TEXT,
  CHECK(start_character < end_character)
);
CREATE TABLE working_assets (
  asset_id TEXT PRIMARY KEY,
  asset_kind TEXT NOT NULL CHECK (asset_kind IN ('input', 'text', 'lineage', 'passage', 'vector', 'index', 'model_cache', 'result', 'checkpoint', 'backup', 'temporary')),
  reference_path TEXT NOT NULL,
  accounting_basis TEXT NOT NULL CHECK (accounting_basis IN ('physical_new_bytes', 'referenced_australian_bytes')),
  accounted_bytes INTEGER NOT NULL CHECK (accounted_bytes >= 0),
  physical_new_bytes INTEGER NOT NULL CHECK (physical_new_bytes >= 0),
  observed_at TEXT NOT NULL
);
CREATE TABLE analysis_views (
  view_id TEXT PRIMARY KEY,
  source_frame_json TEXT NOT NULL,
  comparison_unit TEXT NOT NULL,
  start_day TEXT NOT NULL CHECK (start_day >= '1988-01-01'),
  end_day TEXT NOT NULL CHECK (end_day <= '2026-09-21' AND end_day >= start_day),
  freeze_at TEXT NOT NULL,
  evidence_locator TEXT NOT NULL
);
CREATE TABLE analysis_view_members (
  view_id TEXT NOT NULL REFERENCES analysis_views,
  unit_id TEXT NOT NULL REFERENCES units,
  unit_version_id TEXT NOT NULL REFERENCES unit_versions,
  decision_id TEXT NOT NULL REFERENCES admission_ledger(decision_id),
  PRIMARY KEY(view_id, unit_id)
);
CREATE TABLE analysis_view_sources (
  view_id TEXT NOT NULL REFERENCES analysis_views,
  source_id TEXT NOT NULL REFERENCES sources,
  genre TEXT NOT NULL,
  role_frame TEXT NOT NULL CHECK (role_frame IN ('institutional', 'media', 'public_civic', 'executive')),
  evidence_locator TEXT NOT NULL,
  PRIMARY KEY(view_id, source_id, genre, role_frame)
);
CREATE TRIGGER analysis_view_sources_no_update BEFORE UPDATE ON analysis_view_sources
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;
CREATE TRIGGER analysis_view_sources_no_delete BEFORE DELETE ON analysis_view_sources
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;
-- One versioned frame×source×native genre/role×month row per calendar cell.
-- Observed presence alone does not establish complete applicable inventory.
CREATE TABLE coverage_cells (
  frame_id TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES sources,
  genre TEXT NOT NULL,
  role_frame TEXT NOT NULL,
  unit_kind TEXT NOT NULL,
  month TEXT NOT NULL,
  lower_day TEXT NOT NULL CHECK (lower_day >= '1988-01-01'),
  upper_day TEXT NOT NULL CHECK (upper_day <= '2026-09-21' AND upper_day >= lower_day),
  applicability_state TEXT NOT NULL CHECK (applicability_state IN ('applicable', 'structurally_inapplicable', 'unknown', 'conflict')),
  observation_state TEXT NOT NULL CHECK (observation_state IN ('readable_presence', 'applicable_unobserved', 'date_pending', 'access_blocked', 'structurally_inapplicable', 'unknown')),
  readable_native_units INTEGER CHECK (readable_native_units IS NULL OR readable_native_units >= 0),
  independent_work_count INTEGER CHECK (independent_work_count IS NULL OR independent_work_count >= 0),
  pending_units INTEGER CHECK (pending_units IS NULL OR pending_units >= 0),
  inventory_state TEXT NOT NULL CHECK (inventory_state IN ('verified_complete', 'partial', 'blocked', 'unknown')),
  evidence_locator TEXT NOT NULL,
  PRIMARY KEY(frame_id, source_id, genre, role_frame, unit_kind, month)
);
CREATE TRIGGER coverage_cells_no_update BEFORE UPDATE ON coverage_cells
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;
CREATE TRIGGER coverage_cells_no_delete BEFORE DELETE ON coverage_cells
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;
CREATE TRIGGER view_member_validated BEFORE INSERT ON analysis_view_members
WHEN NOT EXISTS (
  SELECT 1 FROM unit_versions uv JOIN admission_ledger a USING(unit_version_id)
    JOIN metadata_versions m USING(metadata_version_id) JOIN units u ON u.unit_id = uv.unit_id
    JOIN sources so ON so.source_id = u.source_id
    JOIN source_assertions sa ON sa.assertion_id = m.source_assertion_id
    JOIN analysis_views v ON v.view_id = NEW.view_id
    JOIN analysis_view_sources vs ON vs.view_id = v.view_id AND vs.source_id = u.source_id AND vs.genre = sa.genre
  WHERE uv.unit_id = NEW.unit_id AND uv.unit_version_id = NEW.unit_version_id
    AND a.decision_id = NEW.decision_id AND a.disposition = 'admitted'
    AND m.publication_lower_day >= v.start_day AND m.publication_upper_day <= v.end_day
    AND u.unit_kind = v.comparison_unit
    AND ((vs.role_frame IN ('institutional','executive') AND so.stream = 'institutional')
      OR (vs.role_frame = 'media' AND so.stream = 'newspaper')
      OR (vs.role_frame = 'public_civic' AND so.stream = 'public_civic'))
    AND (vs.role_frame != 'executive' OR EXISTS (
      SELECT 1 FROM speaker_role_assertions sr WHERE sr.unit_id = uv.unit_id
        AND sr.role_type = 'executive_office' AND sr.verification_state = 'verified'
        AND sr.valid_from <= m.publication_lower_day AND sr.valid_to >= m.publication_upper_day))
    AND (SELECT COUNT(*) FROM admission_checks c WHERE c.decision_id = a.decision_id) = 7
    AND NOT EXISTS (SELECT 1 FROM admission_checks c WHERE c.decision_id = a.decision_id
                    AND c.check_state NOT IN ('verified','not_applicable'))
)
BEGIN SELECT RAISE(ABORT, 'unverified_or_mismatched_view_member'); END;
CREATE INDEX units_source_kind ON units(source_id, unit_kind);
CREATE INDEX metadata_unit ON metadata_versions(unit_id);
CREATE INDEX content_unit ON content_versions(unit_id);
CREATE INDEX ledger_version ON admission_ledger(unit_version_id, ledger_sequence);
CREATE INDEX relations_native_target ON unit_relations(target_source_id, target_namespace, target_native_id);

CREATE VIEW accepted_native_versions AS
 SELECT uv.*, u.source_id, u.unit_kind, m.publication_precision,
        m.publication_lower_day, m.publication_upper_day
 FROM unit_versions uv JOIN units u USING(unit_id)
 JOIN metadata_versions m USING(metadata_version_id)
 JOIN admission_ledger a USING(unit_version_id)
 WHERE a.disposition = 'admitted'
 AND a.ledger_sequence = (SELECT MAX(b.ledger_sequence) FROM admission_ledger b WHERE b.unit_version_id = uv.unit_version_id)
 AND m.date_state = 'verified'
 AND m.publication_lower_day >= '1988-01-01' AND m.publication_upper_day <= '2026-09-21'
 AND NOT EXISTS(SELECT 1 FROM admission_checks c WHERE c.decision_id = a.decision_id AND c.check_state NOT IN ('verified','not_applicable'))
 AND (SELECT COUNT(*) FROM admission_checks c WHERE c.decision_id = a.decision_id) = 7;

CREATE VIEW accepted_monthly_versions AS
 SELECT * FROM accepted_native_versions
 WHERE publication_precision IN ('timestamp', 'day', 'month');

CREATE VIEW accepted_news_works AS
 SELECT DISTINCT a.unit_id, a.source_id FROM accepted_native_versions a JOIN sources s USING(source_id)
 WHERE a.unit_kind = 'news_article' AND s.stream = 'newspaper';
CREATE VIEW accepted_public_authored_bodies AS
 SELECT DISTINCT a.unit_id, a.source_id, a.unit_kind FROM accepted_native_versions a JOIN sources s USING(source_id)
 WHERE a.unit_kind IN ('public_letter','civic_submission','social_post','social_reply','social_question','social_answer','social_comment','petition')
 AND a.independently_authored_body = 1 AND s.stream = 'public_civic';
CREATE VIEW accepted_parliamentary_paragraphs AS
 SELECT DISTINCT unit_id, source_id FROM accepted_native_versions WHERE unit_kind = 'parliament_paragraph';

-- Freeze membership chooses exactly one evidenced version per unit. Later
-- corrections require another view_id; an old freeze remains historical evidence.
CREATE VIEW frozen_native_versions AS
 SELECT vm.view_id, uv.*, u.source_id, u.unit_kind, m.publication_precision,
        m.publication_lower_day, m.publication_upper_day
 FROM analysis_view_members vm JOIN unit_versions uv USING(unit_version_id)
 JOIN units u ON u.unit_id = vm.unit_id JOIN metadata_versions m USING(metadata_version_id);

-- Every evidence/version/map/decision row is append-only. Trigger definitions
-- follow. No old lease, counter, queue or scheduler is present.

CREATE TRIGGER analysis_views_no_update BEFORE UPDATE ON analysis_views
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;
CREATE TRIGGER analysis_views_no_delete BEFORE DELETE ON analysis_views
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;
CREATE TRIGGER analysis_view_members_no_update BEFORE UPDATE ON analysis_view_members
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;
CREATE TRIGGER analysis_view_members_no_delete BEFORE DELETE ON analysis_view_members
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER dataset_contract_no_update BEFORE UPDATE ON dataset_contract
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER dataset_contract_no_delete BEFORE DELETE ON dataset_contract
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER archive_snapshots_no_update BEFORE UPDATE ON archive_snapshots
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER archive_snapshots_no_delete BEFORE DELETE ON archive_snapshots
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER archive_records_no_update BEFORE UPDATE ON archive_records
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER archive_records_no_delete BEFORE DELETE ON archive_records
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER sources_no_update BEFORE UPDATE ON sources
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER sources_no_delete BEFORE DELETE ON sources
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER source_assertions_no_update BEFORE UPDATE ON source_assertions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER source_assertions_no_delete BEFORE DELETE ON source_assertions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER source_relations_no_update BEFORE UPDATE ON source_relations
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER source_relations_no_delete BEFORE DELETE ON source_relations
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER rights_assertions_no_update BEFORE UPDATE ON rights_assertions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER rights_assertions_no_delete BEFORE DELETE ON rights_assertions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER units_no_update BEFORE UPDATE ON units
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER units_no_delete BEFORE DELETE ON units
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER metadata_versions_no_update BEFORE UPDATE ON metadata_versions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER metadata_versions_no_delete BEFORE DELETE ON metadata_versions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER unit_urls_no_update BEFORE UPDATE ON unit_urls
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER unit_urls_no_delete BEFORE DELETE ON unit_urls
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER content_versions_no_update BEFORE UPDATE ON content_versions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER content_versions_no_delete BEFORE DELETE ON content_versions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER text_representations_no_update BEFORE UPDATE ON text_representations
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER text_representations_no_delete BEFORE DELETE ON text_representations
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER content_source_parts_no_update BEFORE UPDATE ON content_source_parts
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER content_source_parts_no_delete BEFORE DELETE ON content_source_parts
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER unit_versions_no_update BEFORE UPDATE ON unit_versions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER unit_versions_no_delete BEFORE DELETE ON unit_versions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER unit_relations_no_update BEFORE UPDATE ON unit_relations
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER unit_relations_no_delete BEFORE DELETE ON unit_relations
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER speaker_role_assertions_no_update BEFORE UPDATE ON speaker_role_assertions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER speaker_role_assertions_no_delete BEFORE DELETE ON speaker_role_assertions
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER admission_ledger_no_update BEFORE UPDATE ON admission_ledger
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER admission_ledger_no_delete BEFORE DELETE ON admission_ledger
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER admission_checks_no_update BEFORE UPDATE ON admission_checks
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER admission_checks_no_delete BEFORE DELETE ON admission_checks
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER archive_to_new_map_no_update BEFORE UPDATE ON archive_to_new_map
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER archive_to_new_map_no_delete BEFORE DELETE ON archive_to_new_map
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER structural_changes_no_update BEFORE UPDATE ON structural_changes
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER structural_changes_no_delete BEFORE DELETE ON structural_changes
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER passages_no_update BEFORE UPDATE ON passages
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER passages_no_delete BEFORE DELETE ON passages
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER working_assets_no_update BEFORE UPDATE ON working_assets
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;

CREATE TRIGGER working_assets_no_delete BEFORE DELETE ON working_assets
BEGIN SELECT RAISE(ABORT, 'append_only_contract'); END;
