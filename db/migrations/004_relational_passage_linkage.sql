BEGIN;

SET search_path = fear_temperature, public;

-- Linkage is an independently validated relation, never inferred from passage
-- co-occurrence.  The object annotation must be A/B; the linked annotation is
-- validated as C (affect) or D (threat) by the analytical views below.
CREATE TABLE passage_linkage_validation (
    passage_linkage_id text PRIMARY KEY,
    passage_id text NOT NULL REFERENCES evidence_passage(passage_id),
    object_annotation_id text NOT NULL REFERENCES semantic_annotation(annotation_id),
    linked_annotation_id text NOT NULL REFERENCES semantic_annotation(annotation_id),
    linkage_type text NOT NULL CHECK (linkage_type IN ('THREAT', 'AFFECT')),
    affect_mode text CHECK (affect_mode IN (
        'AFFECT_MODE_DIRECT', 'AFFECT_MODE_PRESCRIBED', 'AFFECT_MODE_ELICITED',
        'AFFECT_MODE_RESEARCHER_LABELLED'
    )),
    relation_strength text NOT NULL CHECK (relation_strength IN ('DIRECT', 'STRONG', 'QUALIFIED', 'WEAK')),
    validation_status text NOT NULL CHECK (validation_status IN (
        'ACCEPT', 'ACCEPT_WITH_QUALIFICATION', 'REJECT', 'UNRESOLVED'
    )),
    validator_id text NOT NULL,
    validated_at timestamptz NOT NULL,
    notes text NOT NULL,
    CHECK (object_annotation_id <> linked_annotation_id),
    CHECK (
        (linkage_type = 'AFFECT' AND affect_mode IS NOT NULL) OR
        (linkage_type = 'THREAT' AND affect_mode IS NULL)
    ),
    UNIQUE (passage_id, object_annotation_id, linked_annotation_id, linkage_type, validator_id, validated_at)
);

CREATE OR REPLACE VIEW vw_latest_accepted_annotation AS
WITH latest AS (
    SELECT DISTINCT ON (rd.annotation_id)
        rd.annotation_id,
        ro.is_acceptance,
        rd.review_outcome_code,
        rd.decided_at
    FROM review_decision rd
    JOIN review_outcome ro USING (review_outcome_code)
    ORDER BY rd.annotation_id, rd.decided_at DESC, rd.review_decision_id DESC
)
SELECT annotation_id, review_outcome_code, decided_at
FROM latest
WHERE is_acceptance;

CREATE OR REPLACE VIEW vw_ab_object_passages AS
SELECT DISTINCT
    ep.passage_id,
    sa.annotation_id AS object_annotation_id,
    ha.label AS anchor,
    sa.voice_code AS voice,
    s.source_id AS source,
    s.source_genre_code AS source_genre,
    lo.matched_surface AS object_term,
    lf.family_code AS object_family,
    sa.layer_code AS object_layer,
    la.review_outcome_code AS validation_status
FROM evidence_passage ep
JOIN document d USING (document_id)
JOIN source s USING (source_id)
LEFT JOIN historical_anchor ha ON ha.anchor_id = ep.anchor_id
JOIN lexical_occurrence lo USING (passage_id)
JOIN semantic_annotation sa USING (occurrence_id)
JOIN vw_latest_accepted_annotation la USING (annotation_id)
LEFT JOIN canonical_concept cc USING (concept_id)
LEFT JOIN lexical_family lf USING (family_id)
WHERE sa.layer_code IN ('A', 'B')
  AND lo.occurrence_status = 'VERIFIED_MATCH';

CREATE OR REPLACE VIEW vw_threat_linkage_passages AS
SELECT DISTINCT
    ab.*,
    linked_sa.annotation_id AS linked_annotation_id,
    linked_sa.voice_code AS linked_voice,
    linked_lo.matched_surface AS threat_term,
    linked_lf.family_code AS threat_family,
    plv.relation_strength,
    plv.validation_status,
    plv.notes
FROM vw_ab_object_passages ab
JOIN passage_linkage_validation plv
  ON plv.passage_id = ab.passage_id
 AND plv.object_annotation_id = ab.object_annotation_id
JOIN semantic_annotation linked_sa ON linked_sa.annotation_id = plv.linked_annotation_id
JOIN vw_latest_accepted_annotation linked_review ON linked_review.annotation_id = linked_sa.annotation_id
JOIN lexical_occurrence linked_lo ON linked_lo.occurrence_id = linked_sa.occurrence_id
LEFT JOIN canonical_concept linked_cc ON linked_cc.concept_id = linked_sa.concept_id
LEFT JOIN lexical_family linked_lf ON linked_lf.family_id = linked_cc.family_id
WHERE plv.linkage_type = 'THREAT'
  AND plv.validation_status IN ('ACCEPT', 'ACCEPT_WITH_QUALIFICATION')
  AND linked_sa.layer_code = 'D'
  AND linked_lo.occurrence_status = 'VERIFIED_MATCH';

CREATE OR REPLACE VIEW vw_affect_linkage_passages AS
SELECT DISTINCT
    ab.*,
    linked_sa.annotation_id AS linked_annotation_id,
    linked_sa.voice_code AS linked_voice,
    linked_lo.matched_surface AS affect_term,
    linked_lf.family_code AS affect_family,
    plv.affect_mode,
    plv.relation_strength,
    plv.validation_status,
    plv.notes
FROM vw_ab_object_passages ab
JOIN passage_linkage_validation plv
  ON plv.passage_id = ab.passage_id
 AND plv.object_annotation_id = ab.object_annotation_id
JOIN semantic_annotation linked_sa ON linked_sa.annotation_id = plv.linked_annotation_id
JOIN vw_latest_accepted_annotation linked_review ON linked_review.annotation_id = linked_sa.annotation_id
JOIN lexical_occurrence linked_lo ON linked_lo.occurrence_id = linked_sa.occurrence_id
LEFT JOIN canonical_concept linked_cc ON linked_cc.concept_id = linked_sa.concept_id
LEFT JOIN lexical_family linked_lf ON linked_lf.family_id = linked_cc.family_id
WHERE plv.linkage_type = 'AFFECT'
  AND plv.validation_status IN ('ACCEPT', 'ACCEPT_WITH_QUALIFICATION')
  AND linked_sa.layer_code = 'C'
  AND linked_lo.occurrence_status = 'VERIFIED_MATCH';

COMMIT;
