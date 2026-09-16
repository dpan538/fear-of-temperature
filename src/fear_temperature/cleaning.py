from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import pandas as pd

VALID_ROLES = {"policy", "media", "public"}


def normalise_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text))
    value = value.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def stable_id(prefix: str, *parts: object) -> str:
    joined = "\x1f".join(str(part) for part in parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


@dataclass(frozen=True)
class NormalisedCorpus:
    sources: pd.DataFrame
    documents: pd.DataFrame
    passages: pd.DataFrame
    lineage: pd.DataFrame


def _required(record: dict[str, Any], field: str) -> Any:
    value = record.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"Missing required field: {field}")
    return value


def prepare_corpus(records: list[dict[str, Any]]) -> NormalisedCorpus:
    source_rows: dict[str, dict[str, Any]] = {}
    document_rows: dict[str, dict[str, Any]] = {}
    canonical_passages: dict[str, dict[str, Any]] = {}
    lineage_rows: list[dict[str, Any]] = []

    for position, record in enumerate(records):
        role = str(_required(record, "publisher_role")).strip().lower()
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid publisher_role {role!r}")
        source_name = normalise_text(str(_required(record, "source_name")))
        external_id = normalise_text(str(_required(record, "external_id")))
        raw_text = str(_required(record, "text"))
        text = normalise_text(raw_text)
        publication_date = pd.Timestamp(_required(record, "publication_date")).normalize()
        if publication_date.year < 1900 or publication_date.year > 2100:
            raise ValueError(f"Implausible date for {external_id}: {publication_date.date()}")

        source_id = stable_id("src", role, source_name)
        document_id = stable_id("doc", source_id, external_id)
        content_sha256 = hashlib.sha256(text.lower().encode("utf-8")).hexdigest()
        passage_id = stable_id("pas", content_sha256)
        raw_id = stable_id("raw", external_id, position, raw_text)

        source_rows[source_id] = {
            "source_id": source_id,
            "source_name": source_name,
            "publisher_role": role,
            "source_kind": "synthetic_fixture",
        }
        document_rows[document_id] = {
            "document_id": document_id,
            "source_id": source_id,
            "external_id": external_id,
            "title": normalise_text(str(record.get("title", external_id))),
            "publication_date": publication_date,
            "location": record.get("location"),
            "language": "en",
            "content_sha256": content_sha256,
        }

        is_duplicate = passage_id in canonical_passages
        if not is_duplicate:
            canonical_passages[passage_id] = {
                "passage_id": passage_id,
                "document_id": document_id,
                "source_id": source_id,
                "publisher_role": role,
                "publication_date": publication_date,
                "text": text,
                "content_sha256": content_sha256,
                "quoted_speaker": record.get("quoted_speaker"),
                "speaker_role": record.get("speaker_role"),
                "emotion_holder": record.get("emotion_holder"),
                "location": record.get("location"),
                "fixture_relevant": bool(record.get("fixture_relevant", False)),
                "fixture_future_worry": bool(record.get("fixture_future_worry", False)),
                "fixture_horizon": record.get("fixture_horizon", "unspecified"),
                "fixture_note": record.get("fixture_note", ""),
                "label_status": "synthetic_expected_only_not_human_gold",
                "weight": 1.0,
            }
        lineage_rows.append(
            {
                "raw_id": raw_id,
                "external_id": external_id,
                "document_id": document_id,
                "canonical_passage_id": passage_id,
                "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                "normalised_text_sha256": content_sha256,
                "is_exact_duplicate": is_duplicate,
            }
        )

    sources = pd.DataFrame(source_rows.values()).sort_values("source_id").reset_index(drop=True)
    documents = (
        pd.DataFrame(document_rows.values()).sort_values("document_id").reset_index(drop=True)
    )
    passages = (
        pd.DataFrame(canonical_passages.values())
        .sort_values(["publication_date", "passage_id"])
        .reset_index(drop=True)
    )
    lineage = pd.DataFrame(lineage_rows).sort_values("raw_id").reset_index(drop=True)
    return NormalisedCorpus(sources, documents, passages, lineage)
