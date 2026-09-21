# Version-control boundary

These commits record the completed metadata batch and its implementation.
They do not implement the subsequent five-core-table proposal or authorise
content collection. The frozen source batch remains unchanged.

## Tracked

- Collection code, tests and configuration.
- The 1,020-record enumeration manifest and query-partition inventory.
- Field dictionary, scope, freeze record, verification summaries and review materials.
- The earlier nine-record metadata fixtures required by pilot tests.

## Local artefacts

DuckDB binaries, the full batch raw-response archive, generated database exports,
smoke outputs and repeated per-content status manifests remain local. The freeze
and rebuild records refer to some of these local artefacts. A fresh Git checkout
alone cannot reproduce the exact frozen batch without its saved raw evidence.
Do not replace that evidence with a fresh live query and call it the same snapshot.

The existing batch README describes the commands and artefact locations.
Meeting materials and the proposal are outside these collection commits.
No full-text content was collected in this batch; the recorded content gate
remains unresolved. No remote push accompanies these commits.
