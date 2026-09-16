from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .cleaning import NormalisedCorpus


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def store_corpus(corpus: NormalisedCorpus, output_dir: str | Path) -> dict[str, Any]:
    target = Path(output_dir)
    parquet_dir = target / "parquet"
    parquet_dir.mkdir(parents=True, exist_ok=True)

    frames = {
        "sources": corpus.sources,
        "documents": corpus.documents,
        "passages": corpus.passages,
        "lineage": corpus.lineage,
    }
    files: dict[str, dict[str, object]] = {}
    for name, frame in frames.items():
        path = parquet_dir / f"{name}.parquet"
        frame.to_parquet(path, index=False)
        files[name] = {"path": str(path), "rows": len(frame), "sha256": _sha256(path)}

    database_path = target / "fear_temperature_demo.duckdb"
    with duckdb.connect(str(database_path)) as connection:
        for name, frame in frames.items():
            connection.register("incoming", frame)
            connection.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM incoming")
            connection.unregister("incoming")
        connection.execute(
            """
            CREATE OR REPLACE VIEW passage_evidence AS
            SELECT
                l.raw_id,
                l.external_id,
                l.is_exact_duplicate,
                p.*,
                d.title,
                s.source_name
            FROM lineage l
            JOIN passages p ON p.passage_id = l.canonical_passage_id
            JOIN documents d ON d.document_id = l.document_id
            JOIN sources s ON s.source_id = d.source_id
            """
        )
    files["duckdb"] = {
        "path": str(database_path),
        "rows": None,
        "sha256": _sha256(database_path),
    }
    return {"files": files, "database": str(database_path)}


def store_analysis_tables(database_path: str | Path, tables: dict[str, pd.DataFrame]) -> None:
    with duckdb.connect(str(database_path)) as connection:
        for name, frame in tables.items():
            if not name.replace("_", "").isalnum():
                raise ValueError(f"Unsafe table name: {name}")
            connection.register("incoming_analysis", frame)
            connection.execute(
                f"CREATE OR REPLACE TABLE analysis_{name} AS SELECT * FROM incoming_analysis"
            )
            connection.unregister("incoming_analysis")
