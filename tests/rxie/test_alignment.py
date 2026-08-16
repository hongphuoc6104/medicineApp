import pytest

from rxie.alignment import LABEL_TO_ID, LABELS, align_token_labels
from rxie.schemas import AnnotationDocument, EntityType


class FakeFastTokenizer:
    is_fast = True

    def __call__(self, text, return_offsets_mapping, **kwargs):
        assert return_offsets_mapping is True
        assert text == "Take Drug X 5mg"
        return {
            "input_ids": [101, 1, 2, 3, 4, 102],
            "attention_mask": [1, 1, 1, 1, 1, 1],
            "offset_mapping": [(0, 0), (0, 4), (5, 9), (10, 11), (12, 15), (0, 0)],
        }


def test_label_map_covers_o_and_bio_for_all_ten_types():
    assert len(LABELS) == 21
    assert LABELS[0] == "O"
    for entity_type in EntityType:
        assert f"B-{entity_type.value}" in LABEL_TO_ID
        assert f"I-{entity_type.value}" in LABEL_TO_ID


def test_aligns_exact_char_spans_to_bio_and_ignores_special_tokens():
    document = AnnotationDocument.model_validate(
        {
            "document_id": "doc-1",
            "raw_text": "Take Drug X 5mg",
            "entities": [
                {"type": "DRUG", "text": "Drug X", "start": 5, "end": 11},
                {"type": "STRENGTH", "text": "5mg", "start": 12, "end": 15},
            ],
        }
    )

    encoded = align_token_labels(document, FakeFastTokenizer())

    assert encoded["labels"] == [
        -100,
        LABEL_TO_ID["O"],
        LABEL_TO_ID["B-DRUG"],
        LABEL_TO_ID["I-DRUG"],
        LABEL_TO_ID["B-STRENGTH"],
        -100,
    ]
    assert "offset_mapping" not in encoded


def test_rejects_token_that_crosses_entity_boundary():
    class CrossingTokenizer(FakeFastTokenizer):
        def __call__(self, text, return_offsets_mapping, **kwargs):
            return {"input_ids": [1], "offset_mapping": [(4, 9)]}

    document = AnnotationDocument.model_validate(
        {
            "document_id": "doc-1",
            "raw_text": "Take Drug X 5mg",
            "entities": [
                {"type": "DRUG", "text": "Drug X", "start": 5, "end": 11}
            ],
        }
    )

    with pytest.raises(ValueError, match="crosses an entity boundary"):
        align_token_labels(document, CrossingTokenizer())
