from __future__ import annotations

import json
from importlib import metadata
from pathlib import Path

import spacy

from fear_temperature.config import PROJECT_ROOT, Settings, load_yaml, resolve_device
from fear_temperature.embeddings import SentenceEncoder
from fear_temperature.emotions import GoEmotionsCandidate


def directory_size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def main() -> None:
    settings = Settings.from_env()
    settings.initialise_directories()
    models = load_yaml("configs/models.yaml")
    device, diagnostics = resolve_device(settings.device_preference)

    sentence = models["sentence_encoder"]
    encoder = SentenceEncoder(sentence["id"], sentence["revision"], settings.model_cache, device)
    encoder.encode(["future warming may harm coastal communities"])

    emotion = models["emotion_candidate"]
    classifier = GoEmotionsCandidate(
        emotion["id"], emotion["revision"], settings.model_cache, device
    )
    classifier.predict(["I worry about the climate my children will inherit."])

    parser = spacy.load("en_core_web_sm")
    parser("Scientists warn that warming could harm communities.")

    registry = {
        "cache": str(settings.model_cache),
        "cache_bytes": directory_size(settings.model_cache),
        "device_probe": diagnostics,
        "models": {
            "sentence_encoder": {**sentence, **encoder.metadata()},
            "emotion_candidate": {**emotion, **classifier.metadata()},
            "parser": {
                **models["parser"],
                "installed_version": parser.meta.get("version"),
            },
        },
        "packages": {
            name: metadata.version(name)
            for name in [
                "torch",
                "transformers",
                "sentence-transformers",
                "spacy",
                "en-core-web-sm",
                "bertopic",
            ]
        },
        "remote_custom_code": False,
    }
    target = PROJECT_ROOT / "models" / "registry.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(registry, indent=2))


if __name__ == "__main__":
    main()
