SET search_path = fear_temperature, public;

DO $$
DECLARE
    candidate_count integer;
    unique_count integer;
    invalid_relationships integer;
    overwritten_raw integer;
BEGIN
    SELECT count(*), count(DISTINCT candidate_id)
      INTO candidate_count, unique_count
      FROM vw_candidate_analysis_180;
    IF candidate_count <> 180 OR unique_count <> 180 THEN
        RAISE EXCEPTION 'vw_candidate_analysis_180 expected 180 unique rows, got % / %', candidate_count, unique_count;
    END IF;

    IF EXISTS (
        SELECT 1 FROM vw_candidate_analysis_180
        WHERE anchor_id IS NULL OR layer_code NOT IN ('A','B','C','D')
           OR voice_code IS NULL OR annotation_missingness IS NULL
    ) THEN
        RAISE EXCEPTION 'Candidate analytical view has unresolved required structural fields';
    END IF;

    SELECT count(*) INTO invalid_relationships
    FROM candidate_relationship cr
    LEFT JOIN seed_candidate source ON source.seed_candidate_id = cr.source_candidate_id
    LEFT JOIN seed_candidate target ON target.seed_candidate_id = cr.target_candidate_id
    WHERE source.seed_candidate_id IS NULL OR target.seed_candidate_id IS NULL;
    IF invalid_relationships <> 0 THEN
        RAISE EXCEPTION 'Candidate relationship contains % invalid endpoints', invalid_relationships;
    END IF;

    SELECT count(*) INTO overwritten_raw
    FROM ngram_measurement_observation
    WHERE observation_status = 'OBSERVED_NUMERIC' AND normalized_frequency IS NULL;
    IF overwritten_raw <> 0 THEN
        RAISE EXCEPTION 'Raw Ngram values are missing for % observed rows', overwritten_raw;
    END IF;
END $$;
