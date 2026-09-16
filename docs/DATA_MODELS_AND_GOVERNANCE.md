# Data, models and governance

## Tracked versus local artefacts

Tracked:

- code, tests, configuration and lock file;
- the explicitly synthetic JSONL fixture;
- proposal, historical baseline, migrations and documentation.

Ignored and local:

- `.venv`, `.cache`, model weights and local `.env`;
- `data/raw/*`, new interim/processed demo data and local databases;
- `outputs/demo/` and notebook execution copies;
- PostgreSQL runtime directories and secrets.

Do not place API keys, restricted text or identifying data in notebooks, logs, Git history or model manifests.

## Verified model register

| Role | Model | Exact revision/version | Licence recorded by source | Verified use |
|---|---|---|---|---|
| Sentence encoder | `sentence-transformers/all-MiniLM-L6-v2` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Apache-2.0 | 384-d semantic retrieval, persistent vectors, BERTopic input |
| Emotion candidate | `SamLowe/roberta-base-go_emotions` | `d75048347613a25d77de8cf6412eaae9fa7b26be` | MIT | multi-label candidate probabilities including separate fear/nervousness scores |
| Parser | `en_core_web_sm` | 3.8.0 | model metadata/source terms apply | English syntax/entities for a dependency-rule baseline |

All were downloaded from their official Hugging Face or Explosion release locations. Remote custom model code is disabled. The measured Hugging Face cache after verified loading was 1,187,283,756 bytes; `.venv` occupied approximately 1.7 GB. The cache includes library snapshots and may change when explicitly updated.

Model installation proves that the software can run locally. It does not prove construct validity, cross-period transfer, source fairness, calibrated probabilities, SRL quality or climate-specific emotion performance.

## Interpretation boundaries

- Sentence similarity supports candidate retrieval; it does not establish emotion, agreement or blame.
- GoEmotions was derived from Reddit labels. `fear` and `nervousness` require project validation; `nervousness` is not a climate-anxiety category.
- spaCy dependency parsing/NER is not semantic role labelling. Candidate actors and objects must not be interpreted automatically as culpable parties.
- BERTopic is a candidate topic workflow. Matched-source checks, outlier coverage, resampling stability and contextual passages are required before diachronic interpretation.
- Synthetic fixture fields are software expectations, not human annotations or empirical scores.
- Textual fear/worry is not population prevalence or a mental-health diagnosis.

## Data access and release

The proposal's supervisory and UQ ethics gates remain in force. Public availability does not automatically permit collection, quotation, inference or redistribution. Source terms govern originals, metadata, derived features and embeddings separately. Restricted originals remain separate from releasable derivatives; only permission-reviewed material may be published.

No blanket open-source licence has been applied to the repository, and no licence is asserted for third-party corpora.
