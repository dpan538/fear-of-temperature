from __future__ import annotations

from fear_temperature.config import PROJECT_ROOT, Settings, load_yaml
from fear_temperature.io import read_records


def test_fixture_covers_roles_quotes_and_emotion_boundaries() -> None:
    records = read_records(PROJECT_ROOT / "data/fixtures/synthetic_passages.jsonl")
    assert {record["publisher_role"] for record in records} == {"policy", "media", "public"}
    assert any(record["quoted_speaker"] for record in records)
    assert any("not afraid" in record["text"] for record in records)
    assert any(record["fixture_horizon"] == "immediate" for record in records)
    assert any(record["fixture_horizon"] == "intergenerational" for record in records)
    assert len(records) >= 30


def test_paths_resolve_from_project_root() -> None:
    settings = Settings.from_env()
    assert settings.data_dir.is_absolute()
    assert settings.output_dir.is_absolute()
    assert settings.model_cache.is_absolute()
    assert settings.data_dir.is_relative_to(PROJECT_ROOT)


def test_model_revisions_are_pinned() -> None:
    models = load_yaml("configs/models.yaml")
    assert len(models["sentence_encoder"]["revision"]) == 40
    assert len(models["emotion_candidate"]["revision"]) == 40
    assert models["parser"]["revision"] == "3.8.0"
