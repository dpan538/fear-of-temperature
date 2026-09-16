# Incremental workspace migration inventory

Snapshot date: 16 September 2026. This inventory records the state inspected before the Python/NLP workspace rebuild and the additive changes made afterward.

## Protected pre-existing material

| Path / asset | Inspected state | Action |
|---|---:|---|
| `data/` | approximately 43 MB; tracked lexical, Ngram, priority-180 and relational outputs plus empty stage roots | preserved; no raw or historical output rewritten |
| `db/` | approximately 28 MB; four migrations, five SQL seeds and validation SQL | preserved byte-for-byte during rebuild |
| `scripts/fear-temperature/` | approximately 1.1 MB; Python/Node legacy builders and validators | preserved; exposed through a VS Code legacy task |
| `figures/fear-temperature/` | approximately 15 MB plus important untracked UHD figures | preserved; no figure moved or deleted |
| `outputs/quantitative-v01/`, `outputs/priority180/` | approximately 1.5 MB | preserved |
| `proposal/` | approximately 216 MB, untracked at inspection; current proposal and build runtime | preserved; not regenerated or bulk-edited |
| `docs/proposal/`, `docs/handoffs/` | important untracked handoff/proposal material | preserved |
| `tools/` | approximately 82 MB, untracked at inspection | preserved |
| root research PDFs and Git history | tracked | preserved |

Untracked did not mean disposable. No `git reset`, `git clean`, database recreation, remote push, data publication or GitHub metadata change was performed.

## Database migration integrity snapshot

The pre-existing SQL files were not moved or edited. SHA-256 values recorded during inspection:

| File | SHA-256 |
|---|---|
| `db/migrations/001_fear_temperature_fast_pilot.sql` | `10ecd298a407e048f4434e9666780ab383ef8749dfa88d8b61b0b55c8b5109e4` |
| `db/migrations/002_priority180_candidate_coverage.sql` | `6ae2821b68b4b2659837dc22f7cd4a1a8c37cbd1dcd609535ab014df0b9979f0` |
| `db/migrations/003_eda_relationship_views.sql` | `e67139f94fe86b3ad31d1e6c907f10fc2e68f6c721572b33ba87834681df5472` |
| `db/migrations/004_relational_passage_linkage.sql` | `b33a8012758bb9eefcb85f6c006df66b6aed1f7c3e77ff4240928a579d32bea7` |

## Path treatment

No old-to-new file moves were necessary. The rebuild classifies work through new package, configuration, documentation and task entry points while retaining legacy paths:

| Existing path | New relationship |
|---|---|
| `requirements.txt` | compatibility shim delegating to `pyproject.toml[legacy]`; no second version source |
| `scripts/fear-temperature/` | documented as legacy/provisional baseline; validator remains runnable |
| `db/` | retained PostgreSQL route; new demo writes only to ignored `outputs/demo/*.duckdb` |
| `data/fear-temperature/` | retained historical baseline; new tracked input is only `data/fixtures/` |
| `proposal/` | remains authoritative for research design |

## Added workspace layers

- `pyproject.toml`, `uv.lock`, `.python-version`, `.env.example` and root `.venv`;
- `src/fear_temperature/` installable research package;
- `configs/` model and run settings;
- tracked synthetic fixture and numbered notebooks;
- bootstrap, model download, kernel and notebook scripts;
- tests for lineage, missingness/zero, S/E/B identity, lag direction, chronological split, schema and reproducibility;
- `.vscode/` settings, extension recommendations, tasks and debug entries;
- environment, architecture, data/model, migration and validation documentation.

The local `.env`, model cache, virtual environment, generated demo outputs and temporary clean-rebuild environment are not repository data.
