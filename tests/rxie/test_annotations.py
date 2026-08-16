import json

import pytest
from pydantic import ValidationError

from rxie.annotations import convert_legacy_bio, legacy_bio_to_char_spans, load_jsonl
from rxie.schemas import AnnotationDocument


def annotation(**overrides):
    value = {
        "schema_version": "rxie.annotation.v1",
        "document_id": "doc-1",
        "raw_text": "Paracetamol 500 mg",
        "entities": [
            {"type": "DRUG", "text": "Paracetamol", "start": 0, "end": 11},
            {"type": "STRENGTH", "text": "500 mg", "start": 12, "end": 18},
        ],
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize(
    ("entities", "message"),
    [
        ([{"type": "DRUG", "text": "wrong", "start": 0, "end": 5}], "does not match"),
        ([{"type": "DRUG", "text": "x", "start": 19, "end": 20}], "exceeds"),
        (
            [
                {"type": "DRUG", "text": "Paracetamol", "start": 0, "end": 11},
                {"type": "NOTE", "text": "mol 500", "start": 8, "end": 15},
            ],
            "must not overlap",
        ),
    ],
)
def test_annotation_rejects_invalid_exact_spans(entities, message):
    with pytest.raises(ValidationError, match=message):
        AnnotationDocument.model_validate(annotation(entities=entities))


def test_jsonl_loader_validates_and_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "annotations.jsonl"
    record = json.dumps(annotation())
    path.write_text(f"{record}\n{record}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate document_id.*:2"):
        load_jsonl(path)


def test_legacy_bio_conversion_uses_exact_drug_spans_and_provenance():
    document = convert_legacy_bio(
        "legacy-1",
        ["Uong", "Paracetamol", "500mg", "sang"],
        ["O", "B-DRUG", "I-DRUG", "O"],
    )

    assert document.raw_text == "Uong Paracetamol 500mg sang"
    assert [entity.model_dump(mode="json") for entity in document.entities] == [
        {
            "type": "DRUG",
            "text": "Paracetamol 500mg",
            "start": 5,
            "end": 22,
        }
    ]
    assert document.provenance.source == "legacy_drug_only"
    assert "not ten-class ground truth" in document.provenance.warnings[0]


def test_legacy_bio_rejects_orphan_inside_tag():
    with pytest.raises(ValueError, match="I-DRUG must follow"):
        legacy_bio_to_char_spans(["Paracetamol"], ["I-DRUG"])
