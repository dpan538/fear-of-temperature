# Inverse source and amount requirements for media acquisition design

Status: completed offline method work, deferred from the current acquisition
repair. Its assumptions and scenarios are not runtime quotas, acceptance
standards or collection priorities. The subsequent eight-hour acquisition
results are reported in [package33](../33_media_eight_hour_review_20261011/README.md).

This package implements the requested step from descriptive diagnostics to
explicit, conditional source/era/amount requirements. It does not claim that
the present corpus is adequate, run a collector, change any frozen input, or
construct semantic/emotion labels.

See [the design contract](../../../docs/acquisition/MEDIA_DESIGN_TARGETS.md).

Run from the repository root:

```sh
.venv/bin/python work_packages/M1_source_access/32_media_design_targets_20261010/run_targets.py
.venv/bin/python -m pytest -q tests/test_media_design_targets.py tests/test_media_diagnostics.py
```

The runner reads only finalized metadata from the 10 October broader-history
round. `results/SUMMARY.json` binds exact input paths/hashes. It writes:

- `SOURCE_CLASSIFICATION_PROPOSAL.csv`: source-type and purpose proposals;
  identity verification and historical parent evidence remain separate.
- `CATEGORY_GAPS_BASELINE.csv`: quantity and source concentration within those
  classes. `CATEGORY_REQUIREMENTS.csv` explicitly lists absent proposed forum
  and general-newspaper components; `ERA_CLASS_SUPPORT.csv` exposes support
  actually present in each historical era. These do not impose equal outputs.
- `SOURCE_COUNT_REQUIREMENTS.csv`: 27 combinations of amount, precision and
  dependence, giving required effective groups or an infeasibility result.
- `AMOUNT_REQUIREMENTS.csv`: 45 inverse scenarios, giving required bodies or
  no finite solution at the stipulated effective group support.
- `MONTHLY_DESIGN_GAPS.csv`: 8,370 monthly scenarios with actual source support,
  requirements, gaps and three separate [0,1] attainment coefficients.
- `ANNUAL_SOURCE_SUPPORT.csv` and `MATCHED_RECENT_YEAR_SHARES.csv`: annual
  support and like-calendar comparison; source-mixture differences remain.
- `RAW_POOL_DILUTION_LOWER_BOUNDS.csv`: demonstrates the amount required merely
  to dilute a dominant group, not an acquisition goal or resource forecast.

Validation: 21 new parameterized/edge checks plus the existing 41 diagnostic
checks pass (62 total). They verify inverse requirements against the original
variance model, boundary/infeasible cases, a 50-name dominant-source example,
the exact bounded-mean deletion influence guarantee, and necessary dilution
bounds. Two input-total assertions match the closed collection summaries.
No numerical result is an estimate of actual population confidence coverage.

The dedicated academic-search MCP tools are unavailable in this session.
Literature support was checked through PubMed, publisher pages and official
NIST/MeCCO sources using the web tool; the prior package31 bibliography remains
the bibliographic base. These are focused method checks, not a systematic
literature review. Cluster-sampling assumptions and transfer limits are stated
in the design contract. No publication claims a universal normal source count
or validates this project's proposed tolerance choices.
