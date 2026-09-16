from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pandas as pd


def read_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".jsonl":
        records: list[dict[str, Any]] = []
        with source.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                value = json.loads(stripped)
                if not isinstance(value, dict):
                    raise ValueError(f"{source}:{line_number} is not a JSON object")
                records.append(value)
        return records
    if suffix == ".csv":
        return cast(list[dict[str, Any]], pd.read_csv(source).to_dict(orient="records"))
    if suffix in {".parquet", ".pq"}:
        return cast(list[dict[str, Any]], pd.read_parquet(source).to_dict(orient="records"))
    raise ValueError(f"Unsupported input format: {source.suffix}")


def write_json(path: str | Path, value: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
