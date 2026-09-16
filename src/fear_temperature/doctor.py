from __future__ import annotations

import argparse
import json
import platform
import sys
from importlib import import_module, metadata
from pathlib import Path
from typing import Any

from jupyter_client.kernelspec import KernelSpecManager

from .config import PROJECT_ROOT, Settings, load_yaml, resolve_device


def _check(name: str, ok: bool, detail: Any, critical: bool = True) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "critical": critical, "detail": detail}


def run_doctor(full_models: bool = False) -> dict[str, Any]:
    settings = Settings.from_env()
    settings.initialise_directories()
    checks: list[dict[str, Any]] = []
    version = platform.python_version()
    checks.append(_check("python_3_12", version.startswith("3.12."), version))
    executable = Path(sys.executable).absolute()
    expected_venv = (PROJECT_ROOT / ".venv").resolve()
    checks.append(
        _check(
            "project_venv",
            Path(sys.prefix).resolve() == expected_venv
            and executable.is_relative_to(PROJECT_ROOT / ".venv"),
            {"executable": str(executable), "sys_prefix": sys.prefix},
        )
    )
    workspace_paths = {
        "project_root": settings.project_root,
        "data_dir": settings.data_dir,
        "output_dir": settings.output_dir,
        "model_cache": settings.model_cache,
        "fixture": settings.data_dir / "fixtures" / "synthetic_passages.jsonl",
        "model_config": settings.project_root / "configs" / "models.yaml",
    }
    checks.append(
        _check(
            "workspace_paths",
            settings.project_root == PROJECT_ROOT
            and all(path.exists() for path in workspace_paths.values()),
            {name: str(path) for name, path in workspace_paths.items()},
        )
    )

    package_names = [
        "duckdb",
        "pandas",
        "pyarrow",
        "sklearn",
        "statsmodels",
        "torch",
        "transformers",
        "sentence_transformers",
        "spacy",
        "bertopic",
        "jupyterlab",
        "pytest",
        "ruff",
    ]
    for import_name in package_names:
        try:
            module = import_module(import_name)
            package_version = getattr(module, "__version__", None)
            if package_version is None:
                package_version = metadata.version(import_name.replace("_", "-"))
            checks.append(_check(f"import_{import_name}", True, package_version))
        except Exception as exc:
            checks.append(_check(f"import_{import_name}", False, repr(exc)))

    try:
        import spacy

        parser = spacy.load("en_core_web_sm")
        parsed = parser("Scientists warn that warming could harm communities.")
        checks.append(
            _check(
                "spacy_pipeline",
                bool(parsed.ents) or any(token.dep_ for token in parsed),
                {"components": parser.pipe_names, "model": parser.meta.get("version")},
            )
        )
    except Exception as exc:
        checks.append(_check("spacy_pipeline", False, repr(exc)))

    selected_device, diagnostics = resolve_device(settings.device_preference)
    checks.append(_check("device_probe", True, {"selected": selected_device, **diagnostics}))

    try:
        specification = KernelSpecManager().get_kernel_spec("fear-of-temperature")
        kernel_executable = Path(specification.argv[0]).absolute()
        checks.append(
            _check(
                "jupyter_kernel",
                kernel_executable.is_relative_to(PROJECT_ROOT / ".venv")
                and kernel_executable.resolve() == executable.resolve(),
                {
                    "display_name": specification.display_name,
                    "argv": specification.argv,
                    "resource_dir": specification.resource_dir,
                },
            )
        )
    except Exception as exc:
        checks.append(_check("jupyter_kernel", False, repr(exc)))

    manifest_path = settings.output_dir / "demo" / "manifest.json"
    checks.append(
        _check(
            "demo_manifest",
            manifest_path.exists(),
            str(manifest_path),
        )
    )

    if full_models:
        models = load_yaml("configs/models.yaml")
        try:
            from .embeddings import SentenceEncoder

            encoder = SentenceEncoder(
                models["sentence_encoder"]["id"],
                models["sentence_encoder"]["revision"],
                settings.model_cache,
                selected_device,
                local_files_only=True,
            )
            vector = encoder.encode(["future warming may harm communities"])
            checks.append(
                _check(
                    "sentence_encoder_offline",
                    vector.shape == (1, int(models["sentence_encoder"]["dimensions"])),
                    {"shape": list(vector.shape), **encoder.metadata()},
                )
            )
        except Exception as exc:
            checks.append(_check("sentence_encoder_offline", False, repr(exc)))
        try:
            from .emotions import GoEmotionsCandidate

            emotion = GoEmotionsCandidate(
                models["emotion_candidate"]["id"],
                models["emotion_candidate"]["revision"],
                settings.model_cache,
                selected_device,
                local_files_only=True,
            )
            result = emotion.predict(["I fear what warming will do to my children."])
            checks.append(
                _check(
                    "goemotions_offline",
                    "goemotions_fear_score" in result,
                    emotion.metadata(),
                )
            )
        except Exception as exc:
            checks.append(_check("goemotions_offline", False, repr(exc)))

    failed = [check["name"] for check in checks if check["critical"] and not check["ok"]]
    return {
        "status": "ok" if not failed else "failed",
        "failed": failed,
        "project_root": str(PROJECT_ROOT),
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose the Fear of Temperature workspace")
    parser.add_argument("--full-models", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_doctor(full_models=args.full_models)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        for check in report["checks"]:
            marker = "OK" if check["ok"] else "FAIL"
            print(f"[{marker}] {check['name']}: {check['detail']}")
        print(f"status: {report['status']}")
    raise SystemExit(0 if report["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
