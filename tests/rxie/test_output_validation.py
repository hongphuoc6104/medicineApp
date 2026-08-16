import pytest

from rxie.schemas import Entity, EntityType, OcrDocument
from rxie.text import build_document_text, validate_entities
from tests.rxie.test_schema import payload


def test_rejects_entity_text_that_disagrees_with_offsets():
    document = build_document_text(OcrDocument.model_validate(payload()))
    entity = Entity(
        type=EntityType.DRUG,
        text="wrong",
        start=0,
        end=5,
        confidence=0.8,
        source_region_ids=["r1"],
    )

    with pytest.raises(ValueError, match="does not match"):
        validate_entities([entity], document)


def test_rejects_incorrect_region_provenance():
    document = build_document_text(OcrDocument.model_validate(payload()))
    entity = Entity(
        type=EntityType.STRENGTH,
        text="500 mg",
        start=12,
        end=18,
        confidence=0.8,
        source_region_ids=["r1"],
    )

    with pytest.raises(ValueError, match="do not match"):
        validate_entities([entity], document)
