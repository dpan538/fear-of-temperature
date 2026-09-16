from __future__ import annotations

import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _project_path(value: str, default: str) -> Path:
    candidate = Path(value or default).expanduser()
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    output_dir: Path
    model_cache: Path
    device_preference: str
    random_seed: int
    database_url: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            project_root=PROJECT_ROOT,
            data_dir=_project_path(os.getenv("FOT_DATA_DIR", ""), "data"),
            output_dir=_project_path(os.getenv("FOT_OUTPUT_DIR", ""), "outputs"),
            model_cache=_project_path(os.getenv("FOT_MODEL_CACHE", ""), ".cache/huggingface"),
            device_preference=os.getenv("FOT_DEVICE", "auto").strip().lower(),
            random_seed=int(os.getenv("FOT_RANDOM_SEED", "20260916")),
            database_url=os.getenv("FOT_DATABASE_URL", "").strip(),
        )

    def initialise_directories(self) -> None:
        for path in (
            self.data_dir / "raw",
            self.data_dir / "interim",
            self.data_dir / "processed",
            self.data_dir / "exports",
            self.output_dir,
            self.model_cache,
        ):
            path.mkdir(parents=True, exist_ok=True)


def load_yaml(relative_path: str | Path) -> dict[str, Any]:
    path = Path(relative_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    with path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected mapping in {path}")
    return loaded


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.backends.mps.is_available():
            torch.mps.manual_seed(seed)
    except ImportError:
        pass


def resolve_device(preference: str | None = None) -> tuple[str, dict[str, Any]]:
    requested = (preference or Settings.from_env().device_preference).lower()
    if requested not in {"auto", "cpu", "mps"}:
        raise ValueError("FOT_DEVICE must be auto, cpu, or mps")

    diagnostics: dict[str, Any] = {"requested": requested}
    try:
        import torch

        built = bool(torch.backends.mps.is_built())
        available = bool(torch.backends.mps.is_available())
        diagnostics.update(
            torch_version=torch.__version__, mps_built=built, mps_available=available
        )
        if requested == "mps" and not available:
            diagnostics["fallback_reason"] = "MPS requested but unavailable"
            return "cpu", diagnostics
        if requested in {"mps", "auto"} and available:
            try:
                probe = torch.ones(4, device="mps")
                diagnostics["mps_probe_sum"] = float((probe * 2).sum().cpu())
                return "mps", diagnostics
            except (RuntimeError, NotImplementedError) as exc:
                diagnostics["fallback_reason"] = f"MPS probe failed: {exc}"
        return "cpu", diagnostics
    except ImportError:
        diagnostics["fallback_reason"] = "PyTorch is not installed"
        return "cpu", diagnostics
