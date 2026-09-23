# Government content acquisition summary

The frozen 3,025-object list was fully attempted.
Successful downloads: 3021; successful text extractions: 3000.
Failures and non-extractable records are itemised in `exports/failure_manifest.csv`
and `exports/extraction_status.csv`. Current-access versions only are claimed;
retrieval time is not used as publication time.

## Recovery command

```bash
.venv/bin/python -m fear_temperature.government_collection acquire \
  --config work_packages/M1_source_access/06_government_content_acquisition/config.yaml \
  --resume
```

The command validates 04/05 hashes, skips hash-verified successful objects, and
retries incomplete or failed objects. It does not re-enumerate the source.
