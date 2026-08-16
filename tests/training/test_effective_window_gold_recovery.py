"""Gold recovery and model-input contracts for all benchmark tokenizers."""

from pathlib import Path

import pytest
from transformers import AutoTokenizer

from rxie.alignment import DEFAULT_ACTIVE_ENTITY_TYPES
from rxie.chunking import create_token_sliding_windows
from rxie.schemas import AnnotationDocumentV2
from rxie.tokenization import tokenize_with_offsets

ROOT = Path(__file__).resolve().parent.parent.parent
MODELS = [
    ("vinai/phobert-base-v2", "86cd7fd4c148980922ac11a2cf5e257f2ba639e1"),
    ("Qualcomm-AI-Research/BamiBERT", "57bc1340debbe4e348ec549047a763caebe4a977"),
    ("manhtt-079/vipubmed-deberta-base", "a5478252c02549e7bd3f9a7bf2a530cecab57cbc"),
]


@pytest.mark.parametrize(("model_id", "revision"), MODELS)
def test_all_benchmark_tokenizers_recover_gold_with_valid_windows(
    model_id: str, revision: str
):
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    with (ROOT / "data" / "ner_dataset" / "val.jsonl").open(
        "r", encoding="utf-8"
    ) as handle:
        documents = [
            AnnotationDocumentV2.model_validate_json(line)
            for line in handle
            if line.strip()
        ]

    total_active = 0
    recovered_active = 0
    for document in documents:
        input_ids, offsets = tokenize_with_offsets(
            tokenizer,
            document.raw_text,
            add_special_tokens=False,
        )
        windows = create_token_sliding_windows(
            input_ids,
            offsets,
            [0] * len(input_ids),
            tokenizer,
            max_input_tokens=256,
            content_overlap=64,
        )
        for window in windows:
            assert len(window.input_ids) <= 256
            assert window.labels[0] == window.labels[-1] == -100
            assert window.global_token_indices[0] is None
            assert window.global_token_indices[-1] is None

        active_entities = [
            entity
            for entity in document.entities
            if entity.type in DEFAULT_ACTIVE_ENTITY_TYPES
        ]
        total_active += len(active_entities)
        for entity in active_entities:
            token_indices = [
                index
                for index, (start, end) in enumerate(offsets)
                if start < entity.end and entity.start < end
            ]
            assert token_indices, (
                f"No token mapped to {document.document_id}:{entity.entity_id}"
            )
            if any(
                window.token_start <= token_indices[0]
                and token_indices[-1] < window.token_end
                for window in windows
            ):
                recovered_active += 1

    assert total_active > 0
    assert recovered_active == total_active
