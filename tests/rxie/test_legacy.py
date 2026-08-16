import json

import pytest

from rxie.annotations import load_jsonl
from rxie.legacy import convert_file
from rxie.schemas import EntityType


def test_convert_file_writes_versioned_drug_only_annotations(tmp_path):
    source = tmp_path / "legacy.json"
    destination = tmp_path / "annotations.jsonl"
    source.write_text(
        json.dumps(
            [
                {
                    "id": "legacy-1",
                    "tokens": ["Paracetamol", "500mg"],
                    "ner_tags": ["B-DRUG", "O"],
                }
            ]
        ),
        encoding="utf-8",
    )

    assert convert_file(source, destination) == 1

    documents = load_jsonl(destination)
    assert documents[0].entities[0].type == EntityType.DRUG
    assert documents[0].provenance.source == "legacy_drug_only"


def test_convert_file_rejects_duplicate_ids(tmp_path):
    source = tmp_path / "legacy.json"
    row = {"id": "duplicate", "tokens": ["A"], "ner_tags": ["O"]}
    source.write_text(json.dumps([row, row]), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        convert_file(source, tmp_path / "annotations.jsonl")
