from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import pandas as pd

from .cleaning import prepare_corpus
from .config import PROJECT_ROOT, Settings, load_yaml, resolve_device, seed_everything
from .corpus import store_analysis_tables, store_corpus
from .embeddings import SentenceEncoder, persist_embeddings
from .emotions import GoEmotionsCandidate, build_emotion_candidates
from .io import read_records, write_json
from .relations import extract_relation_candidates
from .retrieval import (
    retrieval_fixture_summary,
    semantic_retrieve,
    tfidf_retrieve,
)
from .temporal import (
    aggregate_role_time,
    channel_transition_diagnostic,
    conditional_var_demo,
    cross_correlation,
    fit_segmented_its,
    generate_synthetic_timeseries,
)
from .topics import fit_topic_candidates
from .visualization import export_interactive_temporal, export_temporal_figure


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def _package_versions(names: list[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def _write_frame(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".csv":
        frame.to_csv(path, index=False)
    else:
        frame.to_parquet(path, index=False)


def run_demo(
    config_path: str | Path = "configs/default.yaml",
    local_files_only: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    settings = Settings.from_env()
    settings.initialise_directories()
    config = load_yaml(config_path)
    models = load_yaml("configs/models.yaml")
    seed = int(config["project"].get("random_seed", settings.random_seed))
    seed_everything(seed)

    demo = config["demo"]
    input_path = PROJECT_ROOT / demo["input"]
    output_dir = PROJECT_ROOT / demo["output"]
    output_dir.mkdir(parents=True, exist_ok=True)

    corpus = prepare_corpus(read_records(input_path))
    storage = store_corpus(corpus, output_dir / "storage")
    passages = corpus.passages.copy()

    selected_device, device_diagnostics = resolve_device(settings.device_preference)
    encoder_config = models["sentence_encoder"]
    encoder = SentenceEncoder(
        encoder_config["id"],
        encoder_config["revision"],
        settings.model_cache,
        selected_device,
        local_files_only=local_files_only,
    )
    embeddings = encoder.encode(passages["text"].tolist())
    query_embedding = encoder.encode([demo["retrieval_query"]])[0]
    embedding_paths = persist_embeddings(
        embeddings,
        passages["passage_id"].tolist(),
        output_dir / "embeddings",
        encoder.metadata(),
    )

    top_k = int(demo["semantic_top_k"])
    tfidf = tfidf_retrieve(
        passages["text"].tolist(),
        passages["passage_id"].tolist(),
        demo["retrieval_query"],
        top_k,
        output_dir / "retrieval" / "tfidf_vectorizer.joblib",
    )
    semantic = semantic_retrieve(
        embeddings, query_embedding, passages["passage_id"].tolist(), top_k
    )
    retrieval = pd.concat([tfidf, semantic], ignore_index=True)
    retrieval_summary = retrieval_fixture_summary(retrieval, passages)

    emotion_config = models["emotion_candidate"]
    emotion_model = GoEmotionsCandidate(
        emotion_config["id"],
        emotion_config["revision"],
        settings.model_cache,
        selected_device,
        local_files_only=local_files_only,
    )
    emotions = build_emotion_candidates(passages, emotion_model)
    relations = extract_relation_candidates(passages)

    relevant_mask = passages["fixture_relevant"].astype(bool).to_numpy()
    topic_assignments, topic_info = fit_topic_candidates(
        passages.loc[relevant_mask, "text"].tolist(),
        passages.loc[relevant_mask, "passage_id"].tolist(),
        embeddings[relevant_mask],
        int(demo["topic_count"]),
        seed,
    )

    aggregation = aggregate_role_time(
        passages,
        frequency=config["aggregation"]["frequency"],
        roles=tuple(config["aggregation"]["roles"]),
    )
    synthetic_time = generate_synthetic_timeseries(
        periods=int(demo["temporal_periods"]),
        seed=seed,
        transition_index=int(demo["transition_index"]),
    )
    ccf = cross_correlation(
        synthetic_time["policy_attention"], synthetic_time["public_emotion"], max_lag=12
    )
    its = fit_segmented_its(synthetic_time["public_emotion"], int(demo["transition_index"]))
    var_metrics, var_forecasts = conditional_var_demo(synthetic_time)
    transition = channel_transition_diagnostic(synthetic_time, int(demo["transition_index"]))

    tables = {
        "retrieval": retrieval,
        "retrieval_fixture_summary": retrieval_summary,
        "emotion_candidates": emotions,
        "relation_candidates": relations,
        "topic_assignments": topic_assignments,
        "topic_info": topic_info,
        "aggregation_synthetic_expected": aggregation,
        "temporal_synthetic": synthetic_time,
        "ccf_synthetic": ccf,
        "its_synthetic": its.coefficients,
        "var_metrics_synthetic": var_metrics,
        "var_forecasts_synthetic": var_forecasts,
        "channel_transition_synthetic": transition,
    }
    table_dir = output_dir / "tables"
    for name, frame in tables.items():
        _write_frame(frame, table_dir / f"{name}.parquet")
    _write_frame(retrieval, table_dir / "retrieval.csv")
    _write_frame(aggregation, table_dir / "aggregation_synthetic_expected.csv")
    _write_frame(relations, table_dir / "relation_candidates.csv")
    store_analysis_tables(storage["database"], tables)

    static_figures = export_temporal_figure(synthetic_time, output_dir / "figures")
    interactive_figure = export_interactive_temporal(synthetic_time, output_dir / "figures")

    generated_files = sorted(
        path for path in output_dir.rglob("*") if path.is_file() and path.name != "manifest.json"
    )
    manifest: dict[str, Any] = {
        "status": "completed",
        "scope": "synthetic infrastructure validation; no empirical research claims",
        "input": _relative(input_path),
        "record_counts": {
            "raw": len(corpus.lineage),
            "canonical_passages": len(passages),
            "duplicates": int(corpus.lineage["is_exact_duplicate"].sum()),
            "relation_candidates": len(relations),
            "topic_assignments": len(topic_assignments),
        },
        "device_probe": device_diagnostics,
        "models": {
            "sentence_encoder": {**encoder_config, **encoder.metadata()},
            "emotion_candidate": {**emotion_config, **emotion_model.metadata()},
            "parser": models["parser"],
        },
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "packages": _package_versions(
            [
                "fear-temperature",
                "torch",
                "transformers",
                "sentence-transformers",
                "spacy",
                "en-core-web-sm",
                "bertopic",
                "duckdb",
                "pandas",
                "pyarrow",
                "scikit-learn",
                "statsmodels",
            ]
        ),
        "outputs": [
            {"path": _relative(path), "bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in generated_files
        ],
        "embedding_files": [_relative(path) for path in embedding_paths],
        "figure_files": [_relative(path) for path in [*static_figures, interactive_figure]],
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "random_seed": seed,
        "limitations": [
            "Fixture labels are synthetic expectations, not human gold labels.",
            "GoEmotions output is an unvalidated transfer candidate; nervousness is not "
            "climate anxiety.",
            "spaCy dependency rules are a relation baseline, not semantic role labelling.",
            "BERTopic and temporal outputs only verify interfaces on synthetic data.",
            "CCF and VAR outputs are predictive diagnostics, not causal findings.",
        ],
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the synthetic Fear of Temperature demo")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Require all configured model files to be available in the local cache",
    )
    args = parser.parse_args()
    manifest = run_demo(args.config, local_files_only=args.offline)
    summary = {key: manifest[key] for key in ["status", "record_counts", "runtime_seconds"]}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
