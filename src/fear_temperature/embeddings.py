from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np


class SentenceEncoder:
    def __init__(
        self,
        model_id: str,
        revision: str,
        cache_dir: str | Path,
        device: str,
        local_files_only: bool = False,
    ) -> None:
        from huggingface_hub import snapshot_download
        from sentence_transformers import SentenceTransformer

        self.model_id = model_id
        self.revision = revision
        self.cache_dir = Path(cache_dir)
        self.requested_device = device
        self.actual_device = device
        self.fallback_reason: str | None = None
        model_source = model_id
        model_revision: str | None = revision
        if local_files_only:
            model_source = snapshot_download(
                repo_id=model_id,
                revision=revision,
                cache_dir=str(self.cache_dir),
                local_files_only=True,
            )
            model_revision = None
        kwargs: dict[str, Any] = {
            "revision": model_revision,
            "cache_folder": str(self.cache_dir),
            "device": device,
            "trust_remote_code": False,
            "local_files_only": local_files_only,
        }
        try:
            self.model = SentenceTransformer(model_source, **kwargs)
        except (RuntimeError, NotImplementedError) as exc:
            if device == "cpu":
                raise
            self.actual_device = "cpu"
            self.fallback_reason = f"Model load on {device} failed: {exc}"
            kwargs["device"] = "cpu"
            self.model = SentenceTransformer(model_source, **kwargs)

    def encode(self, texts: Sequence[str], batch_size: int = 16) -> np.ndarray:
        try:
            values = self.model.encode(
                list(texts),
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except (RuntimeError, NotImplementedError) as exc:
            if self.actual_device == "cpu":
                raise
            self.fallback_reason = f"Inference on {self.actual_device} failed: {exc}"
            self.actual_device = "cpu"
            self.model.to("cpu")
            values = self.model.encode(
                list(texts),
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return np.asarray(values, dtype=np.float32)

    def metadata(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "requested_device": self.requested_device,
            "actual_device": self.actual_device,
            "fallback_reason": self.fallback_reason,
            "dimensions": int(self.model.get_embedding_dimension()),
            "trust_remote_code": False,
        }


def persist_embeddings(
    embeddings: np.ndarray,
    passage_ids: Sequence[str],
    output_dir: str | Path,
    metadata: dict[str, Any],
) -> tuple[Path, Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    array_path = target / "passage_embeddings.npy"
    metadata_path = target / "passage_embeddings.json"
    np.save(array_path, embeddings, allow_pickle=False)
    payload = {
        **metadata,
        "shape": list(embeddings.shape),
        "dtype": str(embeddings.dtype),
        "passage_ids": list(passage_ids),
    }
    metadata_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return array_path, metadata_path
