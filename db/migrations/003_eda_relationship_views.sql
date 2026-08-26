BEGIN;

SET search_path = fear_temperature, public;

CREATE TABLE candidate_relationship (
    relation_id text PRIMARY KEY,
    source_candidate_id text NOT NULL REFERENCES seed_candidate(seed_candidate_id),
    target_candidate_id text NOT NULL REFERENCES seed_candidate(seed_candidate_id),
    relation_type text NOT NULL CHECK (relation_type IN (
        'SAME_SURFACE_FORM', 'NORMALIZED_VARIANT_OF', 'SAME_LEXICAL_FAMILY',
        'SAME_CANONICAL_CONCEPT', 'RECURS_ACROSS_ANCHORS',
        'USED_BY_MULTIPLE_VOICES', 'SHARES_NGRAM_MEASUREMENT',
        'RELATED_NOT_EQUIVALENT', 'SAME_FAMILY_DIFFERENT_SENSE',
        'FALSE_CONTINUITY_RISK', 'ANACHRONISTIC_MAPPING_REJECTED',
        'POSSIBLE_HISTORICAL_RECONFIGURATION'
    )),
    relation_class text NOT NULL CHECK (relation_class IN (
        'COMPUTATIONAL_STRUCTURAL', 'RESEARCH_SEMANTIC_CANDIDATE'
    )),
    anchor_relation text NOT NULL,
    evidence_basis text NOT NULL,
    confidence text NOT NULL CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW', 'UNRESOLVED')),
    provenance_note text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (source_candidate_id <> target_candidate_id),
    UNIQUE (source_candidate_id, target_candidate_id, relation_type)
);

COMMENT ON TABLE candidate_relationship IS
    'Explicit structural and evidence-supported candidate relations. Structural links do not assert semantic evolution.';

CREATE OR REPLACE VIEW vw_candidate_analysis_180 AS
WITH priority AS (
    SELECT
        sc.*,
        COALESCE(
            NULLIF(substring(sc.original_decision FROM 'PRIORITY_RANK=([0-9]+)'), '')::integer,
            right(sc.seed_candidate_id, 2)::integer
        ) AS priority_rank,
        lower(trim(regexp_replace(sc.surface_form, '[^[:alnum:]°%+.-]+', ' ', 'g'))) AS normalized_form
    FROM seed_candidate sc
    WHERE sc.originating_seed_stage = 'PRIORITY_180'
), ngram_stats AS (
    SELECT
        pcm.seed_candidate_id,
        nm.ngram_measurement_id,
        nm.measurement_form,
        pcm.project_query_id,
        pcm.mapping_type,
        nm.execution_status AS ngram_status,
        min(o.year) FILTER (WHERE o.normalized_frequency > 0) AS first_nonzero_year,
        (array_agg(o.year ORDER BY o.normalized_frequency DESC NULLS LAST, o.year))[1] AS peak_year,
        max(o.normalized_frequency) AS peak_frequency_raw,
        avg(o.normalized_frequency) FILTER (WHERE o.year IN (2006, 2007)) AS anchor_0607_raw,
        max(o.normalized_frequency) FILTER (WHERE o.year = 2022) AS frequency_2022_raw
    FROM priority_candidate_ngram_map pcm
    LEFT JOIN ngram_measurement nm ON nm.ngram_measurement_id = pcm.ngram_measurement_id
    LEFT JOIN ngram_measurement_observation o ON o.ngram_measurement_id = nm.ngram_measurement_id
    GROUP BY pcm.seed_candidate_id, nm.ngram_measurement_id, nm.measurement_form,
             pcm.project_query_id, pcm.mapping_type, nm.execution_status
), ngram_anchor AS (
    SELECT
        pcm.seed_candidate_id,
        CASE
            WHEN ha.label = '2006–2007' THEN avg(o.normalized_frequency) FILTER (WHERE o.year IN (2006, 2007))
            ELSE max(o.normalized_frequency) FILTER (WHERE o.year = extract(year FROM ha.strict_start)::integer)
        END AS anchor_frequency_raw
    FROM priority_candidate_ngram_map pcm
    JOIN priority p ON p.seed_candidate_id = pcm.seed_candidate_id
    JOIN historical_anchor ha ON ha.anchor_id = p.anchor_id
    LEFT JOIN ngram_measurement_observation o ON o.ngram_measurement_id = pcm.ngram_measurement_id
    GROUP BY pcm.seed_candidate_id, ha.label, ha.strict_start
), dictionary_pick AS (
    SELECT
        pcdm.seed_candidate_id,
        dfe.dictionary_status,
        pcdm.anchor_sense_match,
        pcdm.polysemy_note
    FROM priority_candidate_dictionary_map pcdm
    JOIN dictionary_form_evidence dfe ON dfe.dictionary_form_id = pcdm.dictionary_form_id
), search_pick AS (
    SELECT DISTINCT ON (pcsm.seed_candidate_id)
        pcsm.seed_candidate_id,
        bsm.search_status,
        bsm.search_source AS search_metric_code,
        bsm.reported_result_count
    FROM priority_candidate_search_map pcsm
    JOIN bounded_search_measurement bsm
      ON bsm.bounded_search_measurement_id = pcsm.bounded_search_measurement_id
    ORDER BY pcsm.seed_candidate_id,
             (bsm.query_window = 'ALL_AVAILABLE') DESC,
             (bsm.search_source LIKE 'INTERNET_ARCHIVE%') DESC,
             bsm.retrieved_at DESC NULLS LAST
)
SELECT
    p.seed_candidate_id AS candidate_id,
    p.anchor_id,
    ha.label AS anchor_label,
    p.priority_rank,
    p.surface_form,
    p.normalized_form,
    COALESCE(concept.preferred_label, 'UNRESOLVED') AS canonical_concept,
    COALESCE(family.family_code, 'UNRESOLVED') AS lexical_family,
    p.layer_code,
    COALESCE(p.voice_code, 'NOT_ANNOTATED_IN_SOURCE') AS voice_code,
    COALESCE(p.expression_mode_code, 'NOT_EXPOSED_IN_REPORT') AS expression_mode,
    COALESCE(p.source_id, 'NOT_EXPOSED_IN_REPORT') AS evidence_source,
    p.provenance_status,
    COALESCE(dp.dictionary_status, 'UNRESOLVED') AS dictionary_status,
    COALESCE(dp.anchor_sense_match, 'UNRESOLVED') AS dictionary_anchor_sense_match,
    CASE
        WHEN dp.polysemy_note IS NULL OR trim(dp.polysemy_note) = '' THEN 'UNRESOLVED'
        WHEN lower(dp.polysemy_note) LIKE '%false friend%' OR lower(dp.polysemy_note) LIKE '%not personal%' THEN 'HIGH_AMBIGUITY'
        ELSE 'CONTEXT_SENSITIVE'
    END AS dictionary_polysemy_status,
    COALESCE(ns.ngram_status, 'TECHNICALLY_UNREPRESENTABLE') AS ngram_status,
    COALESCE(ns.measurement_form, 'NOT_APPLICABLE') AS ngram_measurement_form,
    ns.first_nonzero_year AS ngram_first_nonzero_year,
    ns.peak_year AS ngram_peak_year,
    ns.peak_frequency_raw AS ngram_peak_frequency_raw,
    ns.peak_frequency_raw * 1000000 AS ngram_peak_per_million,
    na.anchor_frequency_raw AS ngram_anchor_frequency_raw,
    na.anchor_frequency_raw * 1000000 AS ngram_anchor_per_million,
    ns.frequency_2022_raw AS ngram_2022_frequency_raw,
    ns.frequency_2022_raw * 1000000 AS ngram_2022_per_million,
    COALESCE(sp.search_status, 'UNRESOLVED') AS search_status,
    COALESCE(sp.search_metric_code, 'UNRESOLVED') AS search_metric_code,
    sp.reported_result_count AS search_result_count,
    CASE WHEN sp.reported_result_count IS NULL THEN NULL ELSE log(10, sp.reported_result_count + 1) END AS search_log10_result_count,
    CASE
        WHEN p.voice_code IS NULL THEN 'VOICE=NOT_ANNOTATED_IN_SOURCE'
        WHEN p.expression_mode_code IS NULL THEN 'EXPRESSION_MODE=NOT_EXPOSED_IN_REPORT'
        WHEN dp.dictionary_status IS NULL THEN 'DICTIONARY=UNRESOLVED'
        WHEN ns.ngram_status IS NULL THEN 'NGRAM=NOT_APPLICABLE'
        WHEN sp.search_status IS NULL THEN 'SEARCH=UNRESOLVED'
        ELSE 'COMPLETE'
    END AS annotation_missingness,
    'String frequency is not semantic evidence; inventory composition is not historical prevalence.'::text AS interpretation_warning
FROM priority p
JOIN historical_anchor ha ON ha.anchor_id = p.anchor_id
LEFT JOIN LATERAL (
    SELECT cc.concept_id, cc.preferred_label, cc.family_id
    FROM lexical_form lf
    JOIN lexical_form_sense lfs ON lfs.lexical_form_id = lf.lexical_form_id
    JOIN canonical_concept cc ON cc.concept_id = lfs.concept_id
    WHERE lower(trim(regexp_replace(lf.surface_form, '[^[:alnum:]°%+.-]+', ' ', 'g'))) = p.normalized_form
    ORDER BY (lfs.anchor_id = p.anchor_id) DESC, (lfs.anchor_id IS NULL) DESC, lfs.lexical_form_sense_id
    LIMIT 1
) concept ON true
LEFT JOIN lexical_family family ON family.family_id = concept.family_id
LEFT JOIN ngram_stats ns ON ns.seed_candidate_id = p.seed_candidate_id
LEFT JOIN ngram_anchor na ON na.seed_candidate_id = p.seed_candidate_id
LEFT JOIN dictionary_pick dp ON dp.seed_candidate_id = p.seed_candidate_id
LEFT JOIN search_pick sp ON sp.seed_candidate_id = p.seed_candidate_id;

CREATE OR REPLACE VIEW vw_anchor_layer_counts AS
SELECT
    anchor_label AS anchor,
    count(*) FILTER (WHERE layer_code = 'A') AS a_count,
    count(*) FILTER (WHERE layer_code = 'B') AS b_count,
    count(*) FILTER (WHERE layer_code = 'C') AS c_count,
    count(*) FILTER (WHERE layer_code = 'D') AS d_count,
    count(*) AS total,
    count(*) FILTER (WHERE layer_code = 'A')::numeric / count(*) AS a_percentage,
    count(*) FILTER (WHERE layer_code = 'B')::numeric / count(*) AS b_percentage,
    count(*) FILTER (WHERE layer_code = 'C')::numeric / count(*) AS c_percentage,
    count(*) FILTER (WHERE layer_code = 'D')::numeric / count(*) AS d_percentage
FROM vw_candidate_analysis_180
GROUP BY anchor_label;

CREATE OR REPLACE VIEW vw_anchor_voice_counts AS
SELECT
    anchor_label AS anchor,
    count(*) FILTER (WHERE voice_code = 'V1') AS v1,
    count(*) FILTER (WHERE voice_code = 'V2') AS v2,
    count(*) FILTER (WHERE voice_code = 'V3') AS v3,
    count(*) FILTER (WHERE voice_code = 'V4') AS v4,
    count(*) FILTER (WHERE voice_code = 'V5') AS v5,
    count(*) AS total,
    count(*) FILTER (WHERE voice_code = 'V1')::numeric / count(*) AS v1_percentage,
    count(*) FILTER (WHERE voice_code = 'V2')::numeric / count(*) AS v2_percentage,
    count(*) FILTER (WHERE voice_code = 'V3')::numeric / count(*) AS v3_percentage,
    count(*) FILTER (WHERE voice_code = 'V4')::numeric / count(*) AS v4_percentage,
    count(*) FILTER (WHERE voice_code = 'V5')::numeric / count(*) AS v5_percentage
FROM vw_candidate_analysis_180
GROUP BY anchor_label;

CREATE OR REPLACE VIEW vw_anchor_family_counts AS
SELECT anchor_label AS anchor, lexical_family AS family, count(*) AS candidate_count,
       count(*)::numeric / sum(count(*)) OVER (PARTITION BY anchor_label) AS percentage_within_anchor
FROM vw_candidate_analysis_180
GROUP BY anchor_label, lexical_family;

CREATE OR REPLACE VIEW vw_voice_family_counts AS
SELECT voice_code AS voice, lexical_family AS family, count(*) AS candidate_count
FROM vw_candidate_analysis_180
GROUP BY voice_code, lexical_family;

CREATE OR REPLACE VIEW vw_anchor_voice_family_counts AS
SELECT anchor_label AS anchor, voice_code AS voice, lexical_family AS family, count(*) AS candidate_count
FROM vw_candidate_analysis_180
GROUP BY anchor_label, voice_code, lexical_family;

CREATE OR REPLACE VIEW vw_term_anchor_presence AS
SELECT normalized_form AS normalized_lexical_form,
       count(*) FILTER (WHERE anchor_label = '1842') AS "1842",
       count(*) FILTER (WHERE anchor_label = '1938') AS "1938",
       count(*) FILTER (WHERE anchor_label = '1988') AS "1988",
       count(*) FILTER (WHERE anchor_label = '2006–2007') AS "2006–2007",
       count(*) FILTER (WHERE anchor_label = '2015') AS "2015",
       count(*) FILTER (WHERE anchor_label = '2022') AS "2022",
       string_agg(candidate_id, '; ' ORDER BY candidate_id) AS candidate_ids,
       string_agg(DISTINCT layer_code::text, '; ' ORDER BY layer_code::text) AS primary_layers,
       string_agg(DISTINCT voice_code, '; ' ORDER BY voice_code) AS voices
FROM vw_candidate_analysis_180
GROUP BY normalized_form;

CREATE OR REPLACE VIEW vw_family_anchor_presence AS
SELECT lexical_family,
       count(*) FILTER (WHERE anchor_label = '1842') AS "1842",
       count(*) FILTER (WHERE anchor_label = '1938') AS "1938",
       count(*) FILTER (WHERE anchor_label = '1988') AS "1988",
       count(*) FILTER (WHERE anchor_label = '2006–2007') AS "2006–2007",
       count(*) FILTER (WHERE anchor_label = '2015') AS "2015",
       count(*) FILTER (WHERE anchor_label = '2022') AS "2022",
       string_agg(candidate_id, '; ' ORDER BY candidate_id) AS candidate_ids
FROM vw_candidate_analysis_180
GROUP BY lexical_family;

CREATE OR REPLACE VIEW vw_candidate_measurement_map AS
SELECT
    c.candidate_id,
    c.anchor_label AS anchor,
    c.surface_form,
    pcm.project_query_id AS query_rule_id,
    COALESCE(pcm.ngram_measurement_id, 'NOT_APPLICABLE') AS ngram_measurement_id,
    c.ngram_measurement_form,
    pcm.mapping_type AS ngram_mapping_type,
    c.ngram_status,
    pcdm.dictionary_form_id AS dictionary_measurement_id,
    c.dictionary_status,
    bsm.bounded_search_measurement_id,
    c.search_metric_code,
    c.search_status,
    'TRACEABLE'::text AS traceability_status
FROM vw_candidate_analysis_180 c
JOIN priority_candidate_ngram_map pcm ON pcm.seed_candidate_id = c.candidate_id
JOIN priority_candidate_dictionary_map pcdm ON pcdm.seed_candidate_id = c.candidate_id
LEFT JOIN priority_candidate_search_map pcsm ON pcsm.seed_candidate_id = c.candidate_id
LEFT JOIN bounded_search_measurement bsm
  ON bsm.bounded_search_measurement_id = pcsm.bounded_search_measurement_id
 AND bsm.query_window = 'ALL_AVAILABLE';

COMMIT;
