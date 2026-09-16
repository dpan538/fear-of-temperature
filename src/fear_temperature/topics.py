from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer


def fit_topic_candidates(
    texts: Sequence[str],
    passage_ids: Sequence[str],
    embeddings: np.ndarray,
    topic_count: int,
    random_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    from bertopic import BERTopic
    from bertopic.dimensionality import BaseDimensionalityReduction

    if len(texts) < topic_count * 2:
        raise ValueError("Synthetic topic demo needs at least two texts per requested topic")
    cluster_model = KMeans(n_clusters=topic_count, random_state=random_seed, n_init=20)
    vectorizer = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    topic_model = BERTopic(
        embedding_model=None,
        umap_model=BaseDimensionalityReduction(),
        hdbscan_model=cluster_model,
        vectorizer_model=vectorizer,
        calculate_probabilities=False,
        verbose=False,
    )
    topics, _ = topic_model.fit_transform(list(texts), embeddings)

    assignments = pd.DataFrame(
        {
            "passage_id": list(passage_ids),
            "topic_id": topics,
            "method": "bertopic_precomputed_sentence_embeddings_kmeans_demo",
            "interpretation": "synthetic interface check; topics are not empirical findings",
        }
    )
    info = topic_model.get_topic_info().copy()
    info.columns = [column.lower() for column in info.columns]
    info["top_terms"] = info["topic"].map(
        lambda topic: "|".join(word for word, _ in (topic_model.get_topic(topic) or [])[:8])
    )
    info["method"] = "bertopic_precomputed_sentence_embeddings_kmeans_demo"
    return assignments, info
