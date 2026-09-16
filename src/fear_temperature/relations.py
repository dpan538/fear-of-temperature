from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

import pandas as pd

RELATION_TYPES = {
    "attribute": "cause",
    "cause": "cause",
    "blame": "blame",
    "assign": "duty",
    "direct": "duty",
    "protect": "duty",
    "require": "duty",
    "fear": "emotion_target",
    "worry": "emotion_target",
    "threaten": "threatened_outcome",
    "harm": "threatened_outcome",
    "endanger": "threatened_outcome",
    "warn": "reported_risk",
    "say": "reported_statement",
    "state": "reported_statement",
}


def _phrase(tokens: Iterable[Any]) -> str | None:
    values = sorted(tokens, key=lambda token: token.i)
    if not values:
        return None
    start, end = values[0].i, values[-1].i + 1
    return values[0].doc[start:end].text


def _arguments(predicate: Any) -> tuple[str | None, str | None]:
    subjects = [
        child
        for child in predicate.children
        if child.dep_ in {"nsubj", "nsubjpass", "csubj", "agent"}
    ]
    objects = [
        child
        for child in predicate.children
        if child.dep_ in {"dobj", "obj", "pobj", "attr", "oprd", "ccomp", "xcomp"}
    ]
    actor = _phrase(subjects[0].subtree) if subjects else None
    affected = _phrase(objects[0].subtree) if objects else None
    return actor, affected


def extract_relation_candidates(passages: pd.DataFrame) -> pd.DataFrame:
    import spacy

    nlp = spacy.load("en_core_web_sm")
    rows: list[dict[str, Any]] = []
    for record, document in zip(
        passages.to_dict(orient="records"),
        nlp.pipe(passages["text"].tolist(), batch_size=16),
        strict=True,
    ):
        entities = [{"text": entity.text, "label": entity.label_} for entity in document.ents]
        for sentence in document.sents:
            for token in sentence:
                lemma = token.lemma_.lower()
                if token.pos_ not in {"VERB", "AUX"} or lemma not in RELATION_TYPES:
                    continue
                actor, affected = _arguments(token)
                negated = any(child.dep_ == "neg" for child in token.children)
                rows.append(
                    {
                        "passage_id": record["passage_id"],
                        "relation_type": RELATION_TYPES[lemma],
                        "predicate": token.text,
                        "predicate_lemma": lemma,
                        "actor_candidate": actor,
                        "object_candidate": affected,
                        "publisher_role": record["publisher_role"],
                        "quoted_speaker": record.get("quoted_speaker"),
                        "emotion_holder": record.get("emotion_holder"),
                        "negated": negated,
                        "evidence_span": sentence.text,
                        "entities_json": json.dumps(entities, ensure_ascii=False),
                        "method": "spacy_dependency_rule_baseline_not_srl",
                    }
                )
    columns = [
        "passage_id",
        "relation_type",
        "predicate",
        "predicate_lemma",
        "actor_candidate",
        "object_candidate",
        "publisher_role",
        "quoted_speaker",
        "emotion_holder",
        "negated",
        "evidence_span",
        "entities_json",
        "method",
    ]
    return pd.DataFrame(rows, columns=columns)
