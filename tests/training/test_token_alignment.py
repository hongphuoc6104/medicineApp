"""Unit tests for token-level label alignment."""

from transformers import AutoTokenizer
from rxie.alignment import align_token_labels
from rxie.schemas import AnnotationDocument, EntityType, GoldEntity


def test_align_token_labels_fast_tokenizer():
    tok = AutoTokenizer.from_pretrained("Qualcomm-AI-Research/BamiBERT")
    doc = AnnotationDocument(
        schema_version="rxie.annotation.v1",
        document_id="doc_test_01",
        raw_text="Amlodipine 5mg ngày uống 1 viên",
        entities=[
            GoldEntity(type=EntityType.DRUG, text="Amlodipine", start=0, end=10),
            GoldEntity(type=EntityType.STRENGTH, text="5mg", start=11, end=14),
            GoldEntity(type=EntityType.ROUTE, text="uống", start=20, end=24),
            GoldEntity(type=EntityType.DOSAGE, text="1 viên", start=25, end=31),
        ],
    )
    res = align_token_labels(doc, tok, allow_whitespace_boundary=True)
    assert "input_ids" in res
    assert "labels" in res
    assert len(res["input_ids"]) == len(res["labels"])
    # Check that at least some labels are not 'O' (0) or -100
    labeled = [l for l in res["labels"] if l != 0 and l != -100]
    assert len(labeled) >= 4, "Must contain BIO labels for all 4 entities"
