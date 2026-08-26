BEGIN;

CREATE SCHEMA IF NOT EXISTS fear_temperature;
SET search_path = fear_temperature, public;

CREATE TABLE research_version (
    research_version_id text PRIMARY KEY,
    version_label text NOT NULL UNIQUE,
    status text NOT NULL CHECK (status IN (
        'PROVISIONAL', 'BLOCKED_FOR_INPUT_RECONCILIATION', 'PILOT_READY',
        'FROZEN', 'SUPERSEDED'
    )),
    seed_import_status text NOT NULL CHECK (seed_import_status IN (
        'NOT_STARTED', 'PARTIAL_RECONSTRUCTION', 'STRUCTURED_IMPORT',
        'COMPLETE_RECONSTRUCTION'
    )),
    created_at timestamptz NOT NULL DEFAULT now(),
    source_report text NOT NULL,
    provenance_notes text NOT NULL
);

CREATE TABLE lexical_layer (
    layer_code char(1) PRIMARY KEY CHECK (layer_code IN ('A', 'B', 'C', 'D')),
    label text NOT NULL UNIQUE,
    definition text NOT NULL
);

CREATE TABLE voice (
    voice_code text PRIMARY KEY CHECK (voice_code IN ('V1', 'V2', 'V3', 'V4', 'V5')),
    label text NOT NULL UNIQUE,
    definition text NOT NULL
);

CREATE TABLE expression_mode (
    expression_mode_code text PRIMARY KEY CHECK (expression_mode_code IN ('E1', 'E2', 'E3', 'E4', 'E5')),
    label text NOT NULL UNIQUE,
    definition text NOT NULL
);

CREATE TABLE review_outcome (
    review_outcome_code text PRIMARY KEY CHECK (review_outcome_code IN (
        'ACCEPT', 'ACCEPT_WITH_QUALIFICATION', 'REJECT_FALSE_POSITIVE',
        'REJECT_WRONG_SENSE', 'REJECT_WRONG_DATE', 'REJECT_WRONG_VOICE',
        'REJECT_INSUFFICIENT_CONTEXT', 'DUPLICATE', 'UNRESOLVED',
        'ESCALATE_FOR_ADJUDICATION'
    )),
    is_acceptance boolean NOT NULL,
    definition text NOT NULL
);

CREATE TABLE source_genre (
    source_genre_code text PRIMARY KEY,
    label text NOT NULL UNIQUE,
    definition text NOT NULL
);

CREATE TABLE historical_anchor (
    anchor_id text PRIMARY KEY,
    label text NOT NULL UNIQUE,
    strict_start date NOT NULL,
    strict_end date NOT NULL,
    contextual_start date NOT NULL,
    contextual_end date NOT NULL,
    definition text NOT NULL,
    notes text NOT NULL DEFAULT '',
    CHECK (strict_start <= strict_end),
    CHECK (contextual_start <= strict_start),
    CHECK (strict_end <= contextual_end)
);

CREATE TABLE lexical_family (
    family_id text PRIMARY KEY,
    family_code text NOT NULL UNIQUE,
    label text NOT NULL UNIQUE,
    definition text NOT NULL,
    primary_layer_code char(1) REFERENCES lexical_layer(layer_code),
    is_synonym_group boolean NOT NULL DEFAULT false CHECK (is_synonym_group = false)
);

CREATE TABLE canonical_concept (
    concept_id text PRIMARY KEY,
    family_id text NOT NULL REFERENCES lexical_family(family_id),
    preferred_label text NOT NULL,
    definition text NOT NULL,
    provisional_status text NOT NULL CHECK (provisional_status IN (
        'PROVISIONAL_QUERYABLE', 'PROVISIONAL_CONTEXT_ONLY', 'UNRESOLVED'
    )),
    provenance_note text NOT NULL,
    UNIQUE (family_id, preferred_label)
);

CREATE TABLE lexical_form (
    lexical_form_id text PRIMARY KEY,
    surface_form text NOT NULL,
    normalized_form text NOT NULL,
    language_tag text NOT NULL DEFAULT 'en',
    ambiguity_class text NOT NULL CHECK (ambiguity_class IN (
        'CLIMATE_SPECIFIC', 'CONTEXT_REQUIRED', 'BACKGROUND_OR_AMBIGUOUS',
        'NEGATIVE_CONTROL', 'PROHIBITED_STANDALONE'
    )),
    is_high_value boolean NOT NULL DEFAULT false,
    provenance_note text NOT NULL,
    UNIQUE (normalized_form, language_tag)
);

CREATE TABLE lexical_form_sense (
    lexical_form_sense_id text PRIMARY KEY,
    lexical_form_id text NOT NULL REFERENCES lexical_form(lexical_form_id),
    concept_id text NOT NULL REFERENCES canonical_concept(concept_id),
    anchor_id text REFERENCES historical_anchor(anchor_id),
    sense_label text NOT NULL,
    valid_from_year smallint,
    valid_to_year smallint,
    relation_type text NOT NULL CHECK (relation_type IN (
        'PREFERRED_LABEL', 'EXACT_VARIANT_OF', 'MORPHOLOGICAL_VARIANT_OF',
        'HISTORICAL_FORM_OF', 'ORTHOGRAPHIC_VARIANT_OF',
        'RELATED_NOT_EQUIVALENT', 'SAME_FAMILY_DIFFERENT_SENSE',
        'FALSE_FRIEND', 'ANACHRONISTIC_MAPPING_REJECTED'
    )),
    provenance_note text NOT NULL,
    CHECK (valid_to_year IS NULL OR valid_from_year IS NULL OR valid_from_year <= valid_to_year),
    UNIQUE (lexical_form_id, concept_id, anchor_id, sense_label)
);

CREATE TABLE source (
    source_id text PRIMARY KEY,
    source_genre_code text NOT NULL REFERENCES source_genre(source_genre_code),
    canonical_name text NOT NULL,
    publisher_or_container text,
    stable_identifier text,
    canonical_url text,
    source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    provenance_status text NOT NULL CHECK (provenance_status IN (
        'DIRECTLY_INSPECTED', 'INSPECTED_TRANSCRIPTION',
        'RECONSTRUCTED_FROM_REPORT', 'UNRESOLVED'
    )),
    provenance_note text NOT NULL
);

CREATE TABLE document (
    document_id text PRIMARY KEY,
    source_id text NOT NULL REFERENCES source(source_id),
    title text NOT NULL,
    publication_start date,
    publication_end date,
    date_certainty text NOT NULL CHECK (date_certainty IN (
        'EXACT', 'YEAR_ONLY', 'RANGE', 'UNKNOWN'
    )),
    language_tag text NOT NULL DEFAULT 'en',
    stable_identifier text,
    canonical_url text,
    content_sha256 char(64),
    document_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    provenance_note text NOT NULL,
    CHECK (publication_end IS NULL OR publication_start IS NULL OR publication_start <= publication_end)
);

CREATE TABLE seed_candidate (
    seed_candidate_id text PRIMARY KEY,
    research_version_id text NOT NULL REFERENCES research_version(research_version_id),
    originating_report text NOT NULL,
    originating_seed_stage text NOT NULL CHECK (originating_seed_stage IN (
        'INITIAL_180', 'PRIORITY_180', 'EXPANSION_36', 'HIGH_VALUE_CASE'
    )),
    original_candidate_id text,
    reconstructed boolean NOT NULL,
    provenance_status text NOT NULL CHECK (provenance_status IN (
        'ORIGINAL_STRUCTURED_RECORD', 'RECONSTRUCTED_FROM_REPORT'
    )),
    source_page text,
    anchor_id text NOT NULL REFERENCES historical_anchor(anchor_id),
    surface_form text NOT NULL,
    layer_code char(1) REFERENCES lexical_layer(layer_code),
    voice_code text REFERENCES voice(voice_code),
    expression_mode_code text REFERENCES expression_mode(expression_mode_code),
    source_id text REFERENCES source(source_id),
    original_decision text,
    confidence_label text,
    relevance_label text,
    reconstruction_status text NOT NULL CHECK (reconstruction_status IN (
        'RECONSTRUCTED_FROM_REPORT', 'ORIGINAL_STRUCTURED_RECORD'
    )),
    reconciliation_status text NOT NULL CHECK (reconciliation_status IN (
        'RETAIN', 'EVIDENCE_ONLY', 'QUERY_VARIANT', 'NEGATIVE_CONTROL',
        'EXCLUDE', 'UNRESOLVED'
    )),
    provenance_note text NOT NULL,
    CHECK (
        (reconstructed AND provenance_status = 'RECONSTRUCTED_FROM_REPORT') OR
        (NOT reconstructed AND provenance_status = 'ORIGINAL_STRUCTURED_RECORD')
    )
);

CREATE UNIQUE INDEX seed_candidate_original_id_unique
    ON seed_candidate (originating_seed_stage, original_candidate_id)
    WHERE original_candidate_id IS NOT NULL;

CREATE TABLE query_rule (
    query_id text PRIMARY KEY,
    research_version_id text NOT NULL REFERENCES research_version(research_version_id),
    lexical_form_id text NOT NULL REFERENCES lexical_form(lexical_form_id),
    concept_id text NOT NULL REFERENCES canonical_concept(concept_id),
    family_id text NOT NULL REFERENCES lexical_family(family_id),
    primary_layer_code char(1) NOT NULL REFERENCES lexical_layer(layer_code),
    anchor_id text NOT NULL REFERENCES historical_anchor(anchor_id),
    surface_form text NOT NULL,
    query_type text NOT NULL CHECK (query_type IN (
        'EXACT_STRING', 'EXACT_PHRASE', 'CONTEXTUAL', 'NEGATIVE_CONTROL'
    )),
    query_classification text NOT NULL CHECK (query_classification IN (
        'EXECUTABLE_NGRAM', 'EXECUTABLE_CORPUS_ONLY', 'BACKGROUND_AMBIGUOUS',
        'NEGATIVE_CONTROL', 'CONTEXT_ONLY', 'UNRESOLVED'
    )),
    interpretation_class text NOT NULL CHECK (interpretation_class IN (
        'CLIMATE_SPECIFIC', 'BACKGROUND_AMBIGUOUS', 'CONTEXT_REQUIRED',
        'NEGATIVE_CONTROL', 'PROHIBITED_STANDALONE', 'UNRESOLVED'
    )),
    ngram_compatibility_status text NOT NULL CHECK (ngram_compatibility_status IN (
        'COMPATIBLE', 'TOO_LONG', 'STRUCTURALLY_UNSUPPORTED',
        'PUNCTUATION_HEAVY', 'NUMERIC_OR_SYMBOLIC',
        'SEMANTICALLY_USELESS_ISOLATED', 'CONTEXT_DEPENDENT', 'UNRESOLVED'
    )),
    ngram_execution_eligible boolean NOT NULL DEFAULT false,
    ngram_compatibility_reason text NOT NULL,
    case_policy text NOT NULL CHECK (case_policy IN ('CASE_SENSITIVE', 'CASE_INSENSITIVE_AGGREGATE')),
    hyphenation_policy text NOT NULL,
    orthographic_policy text NOT NULL,
    ocr_policy text NOT NULL,
    production_allowed boolean NOT NULL DEFAULT true,
    ambiguity_risk text NOT NULL CHECK (ambiguity_risk IN ('LOW', 'MEDIUM', 'HIGH')),
    precision_risk text NOT NULL CHECK (precision_risk IN ('LOW', 'MEDIUM', 'HIGH')),
    recall_risk text NOT NULL CHECK (recall_risk IN ('LOW', 'MEDIUM', 'HIGH')),
    retrieval_smoothing smallint NOT NULL DEFAULT 0 CHECK (retrieval_smoothing >= 0),
    expected_voice_code text REFERENCES voice(voice_code),
    source_strata text NOT NULL,
    review_priority text NOT NULL CHECK (review_priority IN ('LOW', 'MEDIUM', 'HIGH')),
    minimum_context text NOT NULL DEFAULT '',
    exclusions_note text NOT NULL DEFAULT '',
    valid_match_pattern text NOT NULL DEFAULT '',
    invalid_match_pattern text NOT NULL DEFAULT '',
    reconstructed boolean NOT NULL DEFAULT true,
    provenance_status text NOT NULL CHECK (provenance_status IN (
        'RECONSTRUCTED_FROM_REPORT', 'ORIGINAL_STRUCTURED_RECORD'
    )),
    source_report text NOT NULL,
    source_page text,
    provenance_note text NOT NULL,
    CHECK (NOT (lower(surface_form) = 'change' AND production_allowed)),
    CHECK (NOT ngram_execution_eligible OR ngram_compatibility_status = 'COMPATIBLE')
);

CREATE TABLE query_rule_context_term (
    query_id text NOT NULL REFERENCES query_rule(query_id) ON DELETE CASCADE,
    context_role text NOT NULL CHECK (context_role IN ('REQUIRED', 'OPTIONAL', 'EXCLUDE')),
    context_term text NOT NULL,
    PRIMARY KEY (query_id, context_role, context_term)
);

CREATE TABLE exclusion_rule (
    exclusion_rule_id text PRIMARY KEY,
    lexical_form_id text REFERENCES lexical_form(lexical_form_id),
    surface_form text NOT NULL,
    rule_type text NOT NULL CHECK (rule_type IN (
        'REQUIRE_CONTEXT', 'EXCLUDE_DOMAIN', 'FALSE_FRIEND',
        'PROHIBIT_STANDALONE', 'REQUIRE_PROVENANCE_SPLIT'
    )),
    pattern_or_domain text NOT NULL,
    rationale text NOT NULL,
    review_priority text NOT NULL CHECK (review_priority IN ('LOW', 'MEDIUM', 'HIGH'))
);

CREATE TABLE query_run (
    query_run_id text PRIMARY KEY,
    research_version_id text NOT NULL REFERENCES research_version(research_version_id),
    provider text NOT NULL,
    corpus_identifier text NOT NULL,
    corpus_version_label text NOT NULL,
    year_start smallint NOT NULL,
    year_end smallint NOT NULL,
    retrieval_smoothing smallint NOT NULL CHECK (retrieval_smoothing >= 0),
    case_insensitive boolean NOT NULL,
    parameter_set_hash char(64) NOT NULL,
    retrieved_at timestamptz NOT NULL,
    endpoint_url text NOT NULL,
    status text NOT NULL CHECK (status IN ('SUCCEEDED', 'PARTIAL', 'BLOCKED', 'FAILED')),
    raw_response_path text,
    response_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_message text,
    CHECK (year_start <= year_end)
);

CREATE TABLE query_execution_result (
    query_run_id text NOT NULL REFERENCES query_run(query_run_id),
    query_id text NOT NULL REFERENCES query_rule(query_id),
    request_surface_form text NOT NULL,
    execution_status text NOT NULL CHECK (execution_status IN (
        'SUCCEEDED', 'ZERO_RESULT', 'FAILED', 'NOT_RUN_INCOMPATIBLE', 'NOT_RUN_CLASSIFICATION'
    )),
    attempt_count smallint NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    observation_count smallint NOT NULL DEFAULT 0 CHECK (observation_count >= 0),
    first_response_ngram text,
    raw_response_path text,
    raw_payload_sha256 char(64),
    error_reason text,
    retrieved_at timestamptz,
    response_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (query_run_id, query_id)
);

CREATE TABLE frequency_observation (
    frequency_observation_id text PRIMARY KEY,
    query_run_id text NOT NULL REFERENCES query_run(query_run_id),
    research_version_id text NOT NULL REFERENCES research_version(research_version_id),
    query_id text NOT NULL REFERENCES query_rule(query_id),
    lexical_form_id text NOT NULL REFERENCES lexical_form(lexical_form_id),
    concept_id text NOT NULL REFERENCES canonical_concept(concept_id),
    family_id text NOT NULL REFERENCES lexical_family(family_id),
    provider text NOT NULL,
    corpus_identifier text NOT NULL,
    corpus_version_label text NOT NULL,
    surface_form text NOT NULL,
    response_ngram text NOT NULL,
    year smallint NOT NULL,
    normalized_frequency numeric(30,20) NOT NULL CHECK (normalized_frequency >= 0),
    retrieval_smoothing smallint NOT NULL DEFAULT 0 CHECK (retrieval_smoothing = 0),
    parameter_set_hash char(64) NOT NULL,
    retrieved_at timestamptz NOT NULL,
    raw_response_path text NOT NULL,
    raw_payload_sha256 char(64) NOT NULL,
    UNIQUE (query_id, corpus_identifier, corpus_version_label, year, parameter_set_hash)
);

CREATE INDEX frequency_observation_lookup_idx
    ON frequency_observation (query_id, corpus_identifier, year);

CREATE TABLE search_observation (
    search_observation_id text PRIMARY KEY,
    query_run_id text NOT NULL REFERENCES query_run(query_run_id),
    query_id text NOT NULL REFERENCES query_rule(query_id),
    corpus_identifier text NOT NULL,
    observed_at timestamptz NOT NULL,
    collection_status text NOT NULL DEFAULT 'NOT_RUN' CHECK (collection_status IN (
        'NOT_RUN', 'SUCCEEDED', 'PARTIAL', 'FAILED'
    )),
    raw_hits bigint CHECK (raw_hits >= 0),
    unique_documents bigint CHECK (unique_documents >= 0),
    passages_retrieved bigint CHECK (passages_retrieved >= 0),
    passages_reviewed bigint CHECK (passages_reviewed >= 0),
    accepted_passages bigint CHECK (accepted_passages >= 0),
    rejected_passages bigint CHECK (rejected_passages >= 0),
    false_positive_count bigint CHECK (false_positive_count >= 0),
    collector_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    provenance_note text NOT NULL
);

CREATE TABLE evidence_passage (
    passage_id text PRIMARY KEY,
    document_id text NOT NULL REFERENCES document(document_id),
    anchor_id text REFERENCES historical_anchor(anchor_id),
    evidence_state text NOT NULL CHECK (evidence_state IN (
        'CANDIDATE_OCCURRENCE', 'ACCEPTED_EVIDENCE', 'REJECTED', 'UNRESOLVED'
    )),
    locator text NOT NULL,
    headline_or_deck text,
    preceding_sentence text,
    matching_sentence text NOT NULL,
    following_sentence text,
    enclosing_paragraph text NOT NULL,
    substantive_speaker text,
    quotation_boundary text,
    attribution_text text,
    survey_question text,
    survey_response_options text,
    treaty_context text,
    captured_at timestamptz NOT NULL,
    provenance_note text NOT NULL,
    CHECK (evidence_state <> 'ACCEPTED_EVIDENCE' OR length(trim(enclosing_paragraph)) > 0)
);

CREATE TABLE lexical_occurrence (
    occurrence_id text PRIMARY KEY,
    passage_id text NOT NULL REFERENCES evidence_passage(passage_id),
    lexical_form_id text REFERENCES lexical_form(lexical_form_id),
    query_id text REFERENCES query_rule(query_id),
    matched_surface text NOT NULL,
    character_start integer CHECK (character_start IS NULL OR character_start >= 0),
    character_end integer CHECK (character_end IS NULL OR character_end >= 0),
    occurrence_status text NOT NULL CHECK (occurrence_status IN (
        'CANDIDATE', 'VERIFIED_MATCH', 'FALSE_POSITIVE', 'WRONG_SENSE'
    )),
    CHECK (character_end IS NULL OR character_start IS NULL OR character_end >= character_start)
);

CREATE TABLE semantic_annotation (
    annotation_id text PRIMARY KEY,
    occurrence_id text NOT NULL REFERENCES lexical_occurrence(occurrence_id),
    concept_id text REFERENCES canonical_concept(concept_id),
    layer_code char(1) NOT NULL REFERENCES lexical_layer(layer_code),
    voice_code text NOT NULL REFERENCES voice(voice_code),
    expression_mode_code text NOT NULL REFERENCES expression_mode(expression_mode_code),
    discourse_function text NOT NULL,
    affect_status text NOT NULL CHECK (affect_status IN (
        'EXPLICIT_AFFECT', 'AFFECT_ADJACENT', 'AFFECT_PRESCRIPTION',
        'RESEARCH_CONSTRUCT', 'NO_AFFECT', 'UNRESOLVED'
    )),
    threat_status text NOT NULL CHECK (threat_status IN (
        'THREAT_WITHOUT_AFFECT', 'THREAT_WITH_AFFECT', 'NO_THREAT', 'UNRESOLVED'
    )),
    referent text,
    affected_subject text,
    instrument_supplied_wording boolean NOT NULL DEFAULT false,
    participant_generated_wording boolean NOT NULL DEFAULT false,
    annotation_notes text NOT NULL,
    annotated_at timestamptz NOT NULL,
    CHECK (NOT (instrument_supplied_wording AND participant_generated_wording))
);

CREATE TABLE review_decision (
    review_decision_id text PRIMARY KEY,
    annotation_id text NOT NULL REFERENCES semantic_annotation(annotation_id),
    review_outcome_code text NOT NULL REFERENCES review_outcome(review_outcome_code),
    reviewer_id text NOT NULL,
    decided_at timestamptz NOT NULL,
    rationale text NOT NULL,
    confidence numeric(4,3) CHECK (confidence BETWEEN 0 AND 1),
    supersedes_review_decision_id text REFERENCES review_decision(review_decision_id),
    UNIQUE (annotation_id, reviewer_id, decided_at)
);

CREATE TABLE provenance_event (
    provenance_event_id text PRIMARY KEY,
    research_version_id text NOT NULL REFERENCES research_version(research_version_id),
    event_type text NOT NULL,
    occurred_at timestamptz NOT NULL,
    actor_or_software text NOT NULL,
    target_table text NOT NULL,
    target_id text NOT NULL,
    source_report text,
    source_file_sha256 char(64),
    source_page text,
    raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    provenance_note text NOT NULL
);

CREATE INDEX provenance_target_idx ON provenance_event (target_table, target_id);

CREATE TABLE pilot_sampling_plan (
    research_version_id text NOT NULL REFERENCES research_version(research_version_id),
    anchor_id text NOT NULL REFERENCES historical_anchor(anchor_id),
    accepted_passage_target smallint NOT NULL CHECK (accepted_passage_target > 0),
    v1_target smallint NOT NULL DEFAULT 0 CHECK (v1_target >= 0),
    v2_target smallint NOT NULL DEFAULT 0 CHECK (v2_target >= 0),
    v3_target smallint NOT NULL DEFAULT 0 CHECK (v3_target >= 0),
    v4_target smallint NOT NULL DEFAULT 0 CHECK (v4_target >= 0),
    v5_target smallint NOT NULL DEFAULT 0 CHECK (v5_target >= 0),
    rationale text NOT NULL,
    PRIMARY KEY (research_version_id, anchor_id),
    CHECK (v1_target + v2_target + v3_target + v4_target + v5_target = accepted_passage_target)
);

CREATE TABLE pilot_quality_metric_definition (
    metric_code text PRIMARY KEY,
    label text NOT NULL UNIQUE,
    numerator_definition text,
    denominator_definition text,
    readiness_status text NOT NULL CHECK (readiness_status IN ('READY_FOR_REAL_DATA', 'NOT_APPLICABLE')),
    caution_note text NOT NULL
);

CREATE OR REPLACE FUNCTION prevent_audit_row_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% rows are immutable; append a superseding/auditing row instead', TG_TABLE_NAME;
END;
$$;

CREATE TRIGGER seed_candidate_no_update_delete
BEFORE UPDATE OR DELETE ON seed_candidate
FOR EACH ROW EXECUTE FUNCTION prevent_audit_row_mutation();

CREATE TRIGGER review_decision_no_update_delete
BEFORE UPDATE OR DELETE ON review_decision
FOR EACH ROW EXECUTE FUNCTION prevent_audit_row_mutation();

CREATE TRIGGER provenance_event_no_update_delete
BEFORE UPDATE OR DELETE ON provenance_event
FOR EACH ROW EXECUTE FUNCTION prevent_audit_row_mutation();

COMMIT;
