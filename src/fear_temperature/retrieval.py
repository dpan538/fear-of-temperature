from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


def tfidf_retrieve(
    texts: Sequence[str],
    passage_ids: Sequence[str],
    query: str,
    top_k: int,
    vectorizer_path: str | Path | None = None,
) -> pd.DataFrame:
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
        stop_words="english",
    )
    matrix = vectorizer.fit_transform(list(texts))
    query_vector = vectorizer.transform([query])
    scores = (matrix @ query_vector.T).toarray().ravel()
    order = np.argsort(-scores, kind="stable")[:top_k]
    if vectorizer_path is not None:
        destination = Path(vectorizer_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(vectorizer, destination)
    return pd.DataFrame(
        {
            "method": "tfidf",
            "rank": np.arange(1, len(order) + 1),
            "passage_id": np.asarray(passage_ids)[order],
            "score": scores[order],
        }
    )


def semantic_retrieve(
    embeddings: np.ndarray,
    query_embedding: np.ndarray,
    passage_ids: Sequence[str],
    top_k: int,
) -> pd.DataFrame:
    query = np.asarray(query_embedding).reshape(-1)
    scores = embeddings @ query
    order = np.argsort(-scores, kind="stable")[:top_k]
    return pd.DataFrame(
        {
            "method": "sentence_transformer",
            "rank": np.arange(1, len(order) + 1),
            "passage_id": np.asarray(passage_ids)[order],
            "score": scores[order],
        }
    )


def retrieval_fixture_summary(results: pd.DataFrame, passages: pd.DataFrame) -> pd.DataFrame:
    joined = results.merge(
        passages[["passage_id", "fixture_relevant", "fixture_future_worry"]],
        on="passage_id",
        how="left",
        validate="many_to_one",
    )
    summary = (
        joined.groupby("method", as_index=False)
        .agg(
            retrieved=("passage_id", "size"),
            fixture_relevant_at_k=("fixture_relevant", "sum"),
            fixture_future_worry_at_k=("fixture_future_worry", "sum"),
        )
        .sort_values("method")
    )
    summary["interpretation"] = "synthetic fixture diagnostic; not empirical performance"
    return summary
