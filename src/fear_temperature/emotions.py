from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

EMOTION_PATTERN = re.compile(
    r"\b(fear|afraid|frighten(?:ed|ing)?|worr(?:y|ied|ies)|anxious|anxiety)\b",
    re.I,
)
FUTURE_PATTERN = re.compile(
    r"\b(future|decade|century|children|grandchildren|inherit|will|could|coming|"
    r"long[- ]term|next fifty years)\b",
    re.I,
)
IMMEDIATE_HEAT_PATTERN = re.compile(
    r"\b(today|tonight|this week|heatwave|heat emergency|extreme temperature|immediate)\b", re.I
)
NEGATED_PATTERN = re.compile(
    r"\b(?:not|never|no)\b.{0,24}\b(?:fear|afraid|panic|worr(?:y|ied)|anxious|anxiety)\b",
    re.I,
)


def rule_emotion_candidate(text: str) -> dict[str, Any]:
    lowered = text.lower()
    cue_match = EMOTION_PATTERN.search(text)
    negated = bool(NEGATED_PATTERN.search(text))
    future = bool(FUTURE_PATTERN.search(text))
    immediate = bool(IMMEDIATE_HEAT_PATTERN.search(text))
    return {
        "emotion_cue": cue_match.group(0).lower() if cue_match else None,
        "fear_cue": bool(re.search(r"\b(fear|afraid|frighten(?:ed|ing)?)\b", lowered)),
        "worry_cue": bool(re.search(r"\bworr(?:y|ied|ies)\b", lowered)),
        "anxiety_cue": bool(re.search(r"\b(anxious|anxiety)\b", lowered)),
        "negated_emotion": negated,
        "future_horizon_cue": future,
        "immediate_heat_cue": immediate,
        "future_worry_rule_candidate": bool(cue_match and future and not negated),
    }


class GoEmotionsCandidate:
    def __init__(
        self,
        model_id: str,
        revision: str,
        cache_dir: str | Path,
        device: str,
        local_files_only: bool = False,
    ) -> None:
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.model_id = model_id
        self.revision = revision
        self.requested_device = device
        self.actual_device = device
        self.fallback_reason: str | None = None
        model_source = model_id
        model_revision: str | None = revision
        if local_files_only:
            model_source = snapshot_download(
                repo_id=model_id,
                revision=revision,
                cache_dir=str(cache_dir),
                local_files_only=True,
            )
            model_revision = None
        common = {
            "revision": model_revision,
            "cache_dir": str(cache_dir),
            "trust_remote_code": False,
            "local_files_only": local_files_only,
        }
        self.tokenizer = AutoTokenizer.from_pretrained(model_source, **common)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_source, use_safetensors=True, **common
        )
        try:
            self.model.to(device)
        except (RuntimeError, NotImplementedError) as exc:
            if device == "cpu":
                raise
            self.actual_device = "cpu"
            self.fallback_reason = f"Model transfer to {device} failed: {exc}"
            self.model.to("cpu")
        self.model.eval()
        self.id2label = {int(index): label for index, label in self.model.config.id2label.items()}

    def _infer_batch(self, texts: Sequence[str]) -> list[list[float]]:
        encoded = self.tokenizer(
            list(texts), padding=True, truncation=True, max_length=256, return_tensors="pt"
        )
        encoded = {key: value.to(self.actual_device) for key, value in encoded.items()}
        with self.torch.inference_mode():
            logits = self.model(**encoded).logits
            probabilities = self.torch.sigmoid(logits).detach().cpu().numpy()
        return probabilities.tolist()

    def predict(self, texts: Sequence[str], batch_size: int = 8) -> pd.DataFrame:
        all_probabilities: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = list(texts[start : start + batch_size])
            try:
                all_probabilities.extend(self._infer_batch(batch))
            except (RuntimeError, NotImplementedError) as exc:
                if self.actual_device == "cpu":
                    raise
                self.fallback_reason = f"Inference on {self.actual_device} failed: {exc}"
                self.actual_device = "cpu"
                self.model.to("cpu")
                all_probabilities.extend(self._infer_batch(batch))

        rows: list[dict[str, Any]] = []
        for probabilities in all_probabilities:
            labelled = {
                self.id2label[index]: float(score) for index, score in enumerate(probabilities)
            }
            top = sorted(labelled.items(), key=lambda item: (-item[1], item[0]))[:5]
            rows.append(
                {
                    "goemotions_fear_score": labelled.get("fear", 0.0),
                    "goemotions_nervousness_score": labelled.get("nervousness", 0.0),
                    "goemotions_top_labels": "|".join(label for label, _ in top),
                    "goemotions_scores_json": json.dumps(labelled, sort_keys=True),
                    "goemotions_status": "unvalidated_candidate_not_climate_anxiety",
                }
            )
        return pd.DataFrame(rows)

    def metadata(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "requested_device": self.requested_device,
            "actual_device": self.actual_device,
            "fallback_reason": self.fallback_reason,
            "trust_remote_code": False,
            "interpretation": "GoEmotions transfer candidate; nervousness is not climate anxiety",
        }


def build_emotion_candidates(
    passages: pd.DataFrame, classifier: GoEmotionsCandidate
) -> pd.DataFrame:
    rules = pd.DataFrame([rule_emotion_candidate(text) for text in passages["text"]])
    transformer = classifier.predict(passages["text"].tolist())
    return pd.concat([passages[["passage_id"]].reset_index(drop=True), rules, transformer], axis=1)
