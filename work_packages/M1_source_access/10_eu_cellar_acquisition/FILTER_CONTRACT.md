---
contract_version: eu_cellar_com_preparatory_en_v1
jurisdiction: EU_supranational
institution: http://publications.europa.eu/resource/authority/corporate-body/COM
work_type: http://publications.europa.eu/ontology/cdm#act_preparatory
language_expression: http://publications.europa.eu/resource/authority/language/ENG
date_field: http://publications.europa.eu/ontology/cdm#work_date_document
start: 1988-01-01
end_inclusive: 2026-09-21
denominator_unit: DISTINCT_Work_URI
monthly_count_index: ../08_cross_region_government_coverage/eu_cellar_commission_preparatory_month_index.csv
parent_identity: Cellar_Work_URI
version_identity: Item_URI_plus_saved_byte_SHA256
no_climate_keyword_prefilter: true
write_target: eu_stage.duckdb
later_combined_target: ../09_us_au_government_acquisition/fear_temperature_us_au_v1.duckdb
---

# EU CELLAR acquisition contract

Enumerate the exact Work URI and every observed document date for each monthly index bin. Reconcile each month's distinct Works to its saved official count before using it as a complete denominator. The sum of monthly counts is not a global unique Work count; one Work may have multiple date observations.

Follow Work → English Expression → Manifestation → Item. A language, format, annex, later edition or print-only description is not automatically a new parent. Select one complete machine-readable Item where available; preserve format and relationship evidence for alternatives. Body usability requires an evidenced Work boundary, Commission issuer, original document date precise to month, and readable English full text.

The EU staging database is separate while the US supervisor has the only writer on the 09 combined database. The 09 database is the later combined target; the UK 06 baseline remains read-only. This source is an EU institutional series, not a substitute for missing national months. Project collection permission is granted, while institutional ethics and public redistribution remain separately unasserted.
