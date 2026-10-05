---
contract_version: us_au_government_v1
study_start: 1988-01-01
study_end: 2026-09-21
unit_policy: source_specific_documents_not_cross_country_policy_counts
series:
  - id: us_fr_epa_doe_rules_1994
    jurisdiction: US_federal
    official_entry: https://www.federalregister.gov/api/v1/documents.json
    source_register_id: us_fr_rules
    institution_filter_field: conditions[agencies][]
    institution_filter_values: [environmental-protection-agency, energy-department]
    institution_rule: official_agency_hierarchy_including_subagencies
    genre_filter_field: conditions[type][]
    genre_filter_values: [RULE, PRORULE]
    date_field: publication_date
    date_precision: day
    first_date: 1994-01-01
    last_date: 2026-09-21
    language: English_presumed_from_source; verify_on_saved_text
    inclusion: all_records_in_132_verified_year_agency_genre_partitions
    exclusion: no_climate_keyword_filter; no_non_rule_genres
    pagination: per_page_1000; all_total_pages_reconciled
    denominator_unit: unique_canonical_document_URL
    stratum_hits: 33560
    enumerated_unique: 33544
    canonical_identity: canonical_html_url_and_publication_date; document_number_is_not_unique
    text_role: Federal_Register_document_HTML; official_PDF_is_alternative_format_when_linked
    attachment_rule: alternative_formats_are_content_objects_not_new_documents
    coverage_status: enumerated_1994_to_cutoff; bodies_pending_acquisition
  - id: au_dcceew_current_catalogue_2026_snapshot
    jurisdiction: AU_federal
    official_entry: https://www.dcceew.gov.au/about/publications
    source_register_id: au_dcceew_publications_listing
    institution_filter_field: current_DCCEEW_publications_catalogue
    institution_filter_values: [all_catalogue_subjects]
    institution_rule: current_host_can_include_predecessor_authors; verify_each_original
    genre_filter_field: listing_type
    genre_filter_values: [Publication]
    date_field: original_issue_date_when_evidenced; otherwise_unknown
    date_precision: day_month_year_or_unknown_as_evidenced
    first_date: 1988-01-01
    last_date: 2026-09-21
    language: English_presumed_from_catalogue; verify_on_saved_original
    inclusion: all_821_unique_landing_URLs_in_83_page_snapshot_for_boundary_review
    exclusion: post_cutoff_originals_only_after_original_date_review; no_topic_selection
    pagination: 83_of_83_pages_reconciled; 823_cards
    denominator_unit: unique_landing_URL_candidate; verified_works_pending
    enumerated_unique: 821
    canonical_identity: normalized_official_landing_URL_then_original_work_evidence
    text_role: landing_HTML_is_catalogue_or_summary; primary_PDF_or_HTML_body_is_work_representation
    attachment_rule: primary_files_alternates_summaries_and_background_files_link_to_parent; no_auto_new_document
    coverage_status: landing_index_enumerated; original_dates_and_file_boundaries_unresolved
  - id: us_pre_1994_official_archive_candidate
    jurisdiction: US_federal
    official_entry: https://www.govinfo.gov/features/dig-fr-index
    source_route: annual_cumulative_Federal_Register_Index_1988_to_1993_plus_scanned_full_issues
    route_limit: annual_index_is_a_finding_aid; agency_genre_document_denominator_not_enumerated
    date_field: issue_date_in_1936_to_1994_scanned_print_archive
    first_date: 1988-01-01
    last_date: 1993-12-31
    denominator_unit: unknown_until_official_agency_and_genre_index_enumerated
    coverage_status: source_route_verified; not_a_zero_count; separate_series
  - id: au_predecessor_official_archive_candidate
    jurisdiction: AU_federal
    official_entry: https://www.dcceew.gov.au/climate-change/policy/publications/archive
    date_field: original_issue_date
    first_date: 1988-01-01
    last_date: 2022-06-30
    denominator_unit: unknown_until_predecessor_archive_enumerated
    coverage_status: official_route_identified; not_a_zero_count; separate_series
---

# US and Australian government acquisition filter contract

The US denominator is Federal Register rulemaking in two official agency hierarchies. Its 16 cross-agency overlaps are one document with multiple agency associations; two document-number collisions require canonical URL identity. The 1994 boundary is the API route boundary, not a claim that no earlier US material exists. There is no climate keyword gate.

The Australian denominator is currently **landing pages**, not policy works. A Drupal/CMS creation time is never an original publication date. The current host can carry predecessor-department works. Publisher, original date and primary-file role must be evidenced from the landing page or original file; unknown month remains unknown. Two catalogue cards have CMS timestamps after the cutoff and remain candidates until their original issue dates are checked.

The 1988–1993 US print archive and Australian predecessor archives are separate candidate series. GovInfo has annual cumulative Federal Register indexes for 1988–1993 and scanned full issues, but the index is a finding aid, not an EPA/DOE rule and proposed-rule document count. Neither candidate series inherits the current-series denominator. Government source claims express an institution's words, not their factual truth. Project permission to collect is recorded separately from institutional ethics status; no UQ approval or exemption is asserted.
