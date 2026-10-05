SELECT source_id, content_type AS genre, analysis_month,
           count(*) AS parent_count,
           count(*) FILTER (WHERE exact_day_eligible) AS exact_day_parents,
           count(*) FILTER (WHERE date_interval_start IS NOT NULL) AS interval_parents,
           count(*) FILTER (WHERE parent_origin = 'recovered_saved_original') AS locally_derived_additional_parents,
           count(*) FILTER (WHERE current_technical_state IS NOT NULL) AS state_annotation_parents,
           count(*) FILTER (WHERE publication_date < DATE '1988-01-01'
                             OR publication_date > DATE '2026-09-21'
                             OR date_interval_start < DATE '1988-01-01'
                             OR date_interval_end > DATE '2026-09-21') AS outside_fixed_interval,
           count(*) FILTER (WHERE publication_date IS NULL AND date_interval_start IS NULL) AS no_supported_date
    FROM repair_current_documents
    GROUP BY source_id, content_type, analysis_month
    ORDER BY source_id, content_type, analysis_month;
