\set ON_ERROR_STOP on
SET search_path TO fear_temperature, public;

DO $$
BEGIN
    IF (SELECT count(*) FROM historical_anchor) <> 6 THEN RAISE EXCEPTION 'historical_anchor count mismatch'; END IF;
    IF (SELECT count(*) FROM lexical_layer) <> 4 THEN RAISE EXCEPTION 'lexical_layer count mismatch'; END IF;
    IF (SELECT count(*) FROM voice) <> 5 THEN RAISE EXCEPTION 'voice count mismatch'; END IF;
    IF (SELECT count(*) FROM expression_mode) <> 5 THEN RAISE EXCEPTION 'expression_mode count mismatch'; END IF;
    IF (SELECT count(*) FROM lexical_family) <> 14 THEN RAISE EXCEPTION 'lexical_family count mismatch'; END IF;
    IF EXISTS (
        SELECT 1 FROM historical_anchor
        WHERE contextual_start > strict_start OR strict_end > contextual_end
    ) THEN RAISE EXCEPTION 'strict anchor window outside contextual window'; END IF;

    IF (SELECT count(*) FROM seed_candidate) <> 396 THEN RAISE EXCEPTION 'seed_candidate count mismatch'; END IF;
    IF (SELECT count(*) FROM seed_candidate WHERE originating_seed_stage = 'INITIAL_180') <> 180 THEN RAISE EXCEPTION 'initial seed count mismatch'; END IF;
    IF (SELECT count(*) FROM seed_candidate WHERE originating_seed_stage = 'PRIORITY_180') <> 180 THEN RAISE EXCEPTION 'priority seed count mismatch'; END IF;
    IF (SELECT count(*) FROM seed_candidate WHERE originating_seed_stage = 'EXPANSION_36') <> 36 THEN RAISE EXCEPTION 'expansion seed count mismatch'; END IF;
    IF EXISTS (
        SELECT 1 FROM seed_candidate
        WHERE reconstructed IS NOT TRUE OR reconstruction_status <> 'RECONSTRUCTED_FROM_REPORT'
    ) THEN RAISE EXCEPTION 'seed reconstruction provenance incomplete'; END IF;

    IF (SELECT count(*) FROM query_rule) <> 143 THEN RAISE EXCEPTION 'query_rule count mismatch'; END IF;
    IF (SELECT count(*) FROM query_rule WHERE ngram_execution_eligible) <> 138 THEN RAISE EXCEPTION 'Ngram eligible query count mismatch'; END IF;
    IF EXISTS (
        SELECT 1 FROM query_rule
        WHERE reconstructed IS NOT TRUE OR provenance_status <> 'RECONSTRUCTED_FROM_REPORT'
    ) THEN RAISE EXCEPTION 'query reconstruction provenance incomplete'; END IF;
    IF EXISTS (
        SELECT 1 FROM query_rule
        WHERE lower(surface_form) IN ('temperature','heat','fear','worry','anxiety','concern','risk','threat','crisis','emergency')
          AND interpretation_class <> 'BACKGROUND_AMBIGUOUS'
    ) THEN RAISE EXCEPTION 'generic term lacks ambiguity classification'; END IF;
    IF EXISTS (
        SELECT 1 FROM query_rule WHERE lower(surface_form) = 'change' AND production_allowed
    ) THEN RAISE EXCEPTION 'standalone change is production-enabled'; END IF;

    IF (SELECT count(*) FROM query_execution_result WHERE execution_status = 'SUCCEEDED') <> 132 THEN RAISE EXCEPTION 'successful query count mismatch'; END IF;
    IF (SELECT count(*) FROM query_execution_result WHERE execution_status = 'ZERO_RESULT') <> 6 THEN RAISE EXCEPTION 'zero-result query count mismatch'; END IF;
    IF (SELECT count(*) FROM query_execution_result WHERE execution_status = 'FAILED') <> 0 THEN RAISE EXCEPTION 'unexpected failed query'; END IF;
    IF (SELECT count(*) FROM query_execution_result WHERE execution_status = 'NOT_RUN_INCOMPATIBLE') <> 5 THEN RAISE EXCEPTION 'incompatible query count mismatch'; END IF;

    IF (SELECT count(*) FROM frequency_observation) <> 23892 THEN RAISE EXCEPTION 'frequency observation count mismatch'; END IF;
    IF (SELECT min(year) FROM frequency_observation) <> 1842 OR (SELECT max(year) FROM frequency_observation) <> 2022 THEN RAISE EXCEPTION 'frequency year range mismatch'; END IF;
    IF EXISTS (SELECT 1 FROM frequency_observation WHERE retrieval_smoothing <> 0) THEN RAISE EXCEPTION 'raw observation has non-zero smoothing'; END IF;
    IF EXISTS (
        SELECT query_id, corpus_identifier, corpus_version_label, year, parameter_set_hash
        FROM frequency_observation
        GROUP BY query_id, corpus_identifier, corpus_version_label, year, parameter_set_hash
        HAVING count(*) > 1
    ) THEN RAISE EXCEPTION 'duplicate frequency observations'; END IF;

    IF (SELECT count(*) FROM search_observation) <> 0 THEN RAISE EXCEPTION 'unbounded search quantities were inserted'; END IF;
END
$$;

SELECT
    current_setting('server_version') AS postgres_version,
    (SELECT count(*) FROM historical_anchor) AS anchors,
    (SELECT count(*) FROM seed_candidate) AS seed_records,
    (SELECT count(*) FROM query_rule) AS query_rules,
    (SELECT count(*) FROM frequency_observation) AS annual_observations,
    (SELECT count(*) FROM search_observation) AS bounded_search_observations;
