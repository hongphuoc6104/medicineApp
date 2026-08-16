"""Unit tests for dataset loading and validation in training infrastructure."""

from pathlib import Path
from rxie.schemas import AnnotationDocumentV2


def test_load_dataset_splits():
    root = Path(__file__).resolve().parent.parent.parent
    dataset_dir = root / "data" / "ner_dataset"

    for split in ["train", "val", "test"]:
        f_path = dataset_dir / f"{split}.jsonl"
        assert f_path.exists(), f"Split file {f_path} missing"

        docs = []
        with f_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    docs.append(AnnotationDocumentV2.model_validate_json(line))

        assert len(docs) > 0, f"Split {split} is empty"
        for doc in docs[:10]:
            assert doc.document_id
            assert doc.raw_text
            for ent in doc.entities:
                assert ent.entity_id
                assert ent.type
                assert ent.start < ent.end
                assert doc.raw_text[ent.start:ent.end] == ent.text
