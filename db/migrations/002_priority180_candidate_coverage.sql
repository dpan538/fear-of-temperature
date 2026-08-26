BEGIN;

SET search_path = fear_temperature, public;

-- Candidate-level audit tables. Identical external requests may be shared, but
-- candidate_measurement_map preserves all 180 Priority research records.
CREATE TABLE ngram_measurement (
    ngram_measurement_id text PRIMARY KEY,
    measurement_form text NOT NULL,
    normalized_measurement_form text NOT NULL,
    provider text NOT NULL,
    corpus_identifier text NOT NULL,
    corpus_version_label text NOT NULL,
    year_start smallint NOT NULL,
    year_end smallint NOT NULL,
    smoothing smallint NOT NULL CHECK (smoothing = 0),
    case_insensitive boolean NOT NULL,
    execution_status text NOT NULL CHECK (execution_status IN (
        'SUCCEEDED_REUSED_BASELINE', 'SUCCEEDED_NEW',
        'ZERO_RESPONSE_REUSED_BASELINE', 'ZERO_RESPONSE_NEW',
        'TECHNICALLY_UNREPRESENTABLE', 'FAILED_REQUEST', 'FAILED_LENGTH_MISMATCH'
    )),
    retrieved_at timestamptz,
    request_url text,
    raw_response_path text,
    raw_payload_sha256 char(64),
    status_note text NOT NULL,
    UNIQUE (normalized_measurement_form, corpus_identifier, corpus_version_label, year_start, year_end, smoothing, case_insensitive),
    CHECK (year_start <= year_end)
);

CREATE TABLE priority_candidate_ngram_map (
    seed_candidate_id text PRIMARY KEY REFERENCES seed_candidate(seed_candidate_id),
    ngram_measurement_id text REFERENCES ngram_measurement(ngram_measurement_id),
    mapping_type text NOT NULL CHECK (mapping_type IN (
        'EXACT', 'NORMALIZED_VARIANT', 'VALIDATED_ALIAS', 'TECHNICALLY_UNREPRESENTABLE'
    )),
    project_query_id text NOT NULL,
    mapping_reason text NOT NULL,
    coverage_state text NOT NULL CHECK (coverage_state IN (
        'FULLY_COVERED', 'FULLY_ACCOUNTED_WITH_NGRAM_ALIAS',
        'FULLY_ACCOUNTED_NGRAM_TECHNICALLY_UNREPRESENTABLE'
    )),
    CHECK (
        (mapping_type = 'TECHNICALLY_UNREPRESENTABLE' AND ngram_measurement_id IS NULL) OR
        (mapping_type <> 'TECHNICALLY_UNREPRESENTABLE' AND ngram_measurement_id IS NOT NULL)
    )
);

CREATE TABLE ngram_measurement_observation (
    ngram_measurement_id text NOT NULL REFERENCES ngram_measurement(ngram_measurement_id),
    year smallint NOT NULL,
    normalized_frequency numeric(30,20),
    observation_status text NOT NULL CHECK (observation_status IN (
        'OBSERVED_NUMERIC', 'NO_SERIES_RETURNED'
    )),
    PRIMARY KEY (ngram_measurement_id, year),
    CHECK (year BETWEEN 1842 AND 2022),
    CHECK (
        (observation_status = 'OBSERVED_NUMERIC' AND normalized_frequency IS NOT NULL AND normalized_frequency >= 0) OR
        (observation_status = 'NO_SERIES_RETURNED' AND normalized_frequency IS NULL)
    )
);

CREATE TABLE dictionary_form_evidence (
    dictionary_form_id text PRIMARY KEY,
    normalized_form text NOT NULL UNIQUE,
    representative_surface_form text NOT NULL,
    dictionary_status text NOT NULL CHECK (dictionary_status IN (
        'DIRECT_HEADWORD', 'TECHNICAL_GLOSSARY', 'NO_STANDALONE_HEADWORD', 'UNRESOLVED'
    )),
    primary_source text NOT NULL,
    secondary_source text NOT NULL,
    historical_source text NOT NULL,
    definition_paraphrase text NOT NULL,
    historical_sense text NOT NULL,
    first_attestation text NOT NULL,
    source_url_or_id text NOT NULL,
    accessed_on date NOT NULL,
    provenance_note text NOT NULL
);

CREATE TABLE priority_candidate_dictionary_map (
    seed_candidate_id text PRIMARY KEY REFERENCES seed_candidate(seed_candidate_id),
    dictionary_form_id text NOT NULL REFERENCES dictionary_form_evidence(dictionary_form_id),
    anchor_sense_match text NOT NULL CHECK (anchor_sense_match IN (
        'STRONG', 'PARTIAL', 'DIFFERENT', 'UNRESOLVED'
    )),
    polysemy_note text NOT NULL
);

CREATE TABLE bounded_search_measurement (
    bounded_search_measurement_id text PRIMARY KEY,
    search_source text NOT NULL,
    metric_semantics text NOT NULL,
    search_query text NOT NULL,
    query_window text NOT NULL CHECK (query_window IN (
        'ALL_AVAILABLE', 'STRICT_ANCHOR', 'CONTEXTUAL_ANCHOR'
    )),
    window_start_year smallint,
    window_end_year smallint,
    exactness text NOT NULL CHECK (exactness IN (
        'EXACT_PHRASE', 'NORMALIZED_PHRASE', 'TOKEN_QUERY', 'VALIDATED_ALIAS'
    )),
    search_status text NOT NULL CHECK (search_status IN (
        'COMPLETED_ZERO', 'COMPLETED_NONZERO', 'NOT_RUN_PROVIDER_QUOTA',
        'FAILED_PROVIDER_OR_REQUEST', 'FAILED_RESPONSE_SHAPE'
    )),
    reported_result_count bigint CHECK (reported_result_count >= 0),
    retrieved_at timestamptz,
    api_or_interface text NOT NULL,
    request_url text NOT NULL,
    raw_response_path text,
    raw_response_sha256 char(64),
    notes text NOT NULL,
    CHECK (window_end_year IS NULL OR window_start_year IS NULL OR window_start_year <= window_end_year),
    CHECK (
        (search_status IN ('COMPLETED_ZERO', 'COMPLETED_NONZERO') AND reported_result_count IS NOT NULL) OR
        (search_status NOT IN ('COMPLETED_ZERO', 'COMPLETED_NONZERO') AND reported_result_count IS NULL)
    )
);

CREATE TABLE priority_candidate_search_map (
    seed_candidate_id text NOT NULL REFERENCES seed_candidate(seed_candidate_id),
    bounded_search_measurement_id text NOT NULL REFERENCES bounded_search_measurement(bounded_search_measurement_id),
    PRIMARY KEY (seed_candidate_id, bounded_search_measurement_id)
);

CREATE INDEX bounded_search_measurement_source_window_idx
    ON bounded_search_measurement (search_source, query_window, search_status);

COMMIT;
