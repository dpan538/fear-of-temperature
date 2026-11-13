# Search Definitions, Weights and Registers

Acquisition is closed. This package publishes the reproducible semantic and scheduling record without collector controls, raw search snippets or source bodies.

| Artifact | Scope |
|---|---|
| [Complete readable matrix](QUERY_MATRIX.md) | All current parent terms, 638 child assignments and 24 sub-parent discovery definitions |
| [Current JSON definitions](../../../config/search/current.json) | Semantic projection of frozen v3.15, with original source SHA |
| [Historical versions](../../../config/search/versions.json) | 19 selected v3.x definition stages, including all four v3.14 stages |
| [Profiles](../../../config/search/profiles.json) | Cities, geographic OR alternatives, genre variants and native discovery effort semantics; dispatch disabled |
| [Weights](../../../config/search/weights.json) | Family effort and the actual saved scheduler year-count snapshot |
| [Actual query registrations](executions/round31_queries.csv) | 942 registered executions, in saved insertion order |
| [Saved jobs](executions/round31_saved_jobs.csv) | 4,169 designed jobs: 710 saved completed, 3,459 saved pending |
| [Offline builder](../../../scripts/search/build_query_jobs.py) | Portable adaptation of the production query-building algorithm; no HTTP or corpus access |

The execution and job registers are different frames: 942 executions do not imply that 942 saved jobs completed. Queries added through other shapes or phases, exact IDs and saved snapshot timing differ. A pending saved job does not authorize resumed collection.

Execution rows preserve literal query, ID, family, available effort/hints/child IDs, attribution availability and original evidence artifact name. Result snippets, result URLs, request headers, private filesystem paths and raw responses remain local. `formal_record_credit=0` means that registering a query does not acquire a body or add a corpus record. Missing child IDs/weights or result attribution are not filled by inference. Evidence artifact names are provenance identifiers, not promises that raw evidence is present in Git.

The canonical matrix contains 988 term memberships and 985 distinct literal terms. Term memberships, child IDs, named sub-parents, expressions designed, jobs planned, searches registered and records admitted are not interchangeable counts. The historical definition catalogue does not establish that all expressions were individually executed or exhaust every earlier v1/v2/runtime artifact.

To reproduce designed jobs offline from the repository root:

```bash
.venv/bin/python scripts/search/build_query_jobs.py --output /tmp/fear-temperature-designed-jobs.json
```

The command writes a new derived file only. It neither refreshes saved historical states nor sends queries. The [acquisition process](../../research/2026-11-13-corpus-release/ACQUISITION_PROCESS.md) explains how web candidates, native discovery, body acquisition and formal credit were separated.
