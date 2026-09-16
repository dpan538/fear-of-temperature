from __future__ import annotations

import pytest

from fear_temperature.cleaning import normalise_text, prepare_corpus


def _record(external_id: str, text: str, role: str = "public") -> dict[str, object]:
    return {
        "external_id": external_id,
        "source_name": "Synthetic source",
        "publisher_role": role,
        "publication_date": "2015-01-01",
        "text": text,
        "fixture_relevant": True,
        "fixture_future_worry": True,
    }


def test_normalisation_is_conservative_and_deterministic() -> None:
    assert normalise_text("  rising\u00a0 temperature\n\n worry ") == "rising temperature worry"


def test_exact_duplicate_keeps_two_raw_lineages_and_one_canonical_passage() -> None:
    corpus = prepare_corpus(
        [
            _record("a", "I worry about future warming."),
            _record("b", "I worry about future warming."),
        ]
    )
    assert len(corpus.documents) == 2
    assert len(corpus.passages) == 1
    assert len(corpus.lineage) == 2
    assert corpus.lineage["canonical_passage_id"].nunique() == 1
    assert int(corpus.lineage["is_exact_duplicate"].sum()) == 1
    assert corpus.lineage["raw_id"].nunique() == 2


def test_invalid_role_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid publisher_role"):
        prepare_corpus([_record("bad", "text", role="unknown")])
