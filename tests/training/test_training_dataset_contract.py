"""Integration contract for the real unsealed PhoBERT training dataset."""

from pathlib import Path

from transformers import AutoTokenizer

from rxie.alignment import DEFAULT_ACTIVE_ENTITY_TYPES, build_label_map
from rxie.schemas import AnnotationDocumentV2
from scripts.train_token_ner import RxieTokenDataset


def test_real_train_split_has_complete_single_loss_ownership():
    root = Path(__file__).resolve().parent.parent.parent
    tokenizer = AutoTokenizer.from_pretrained(
        "vinai/phobert-base-v2",
        revision="86cd7fd4c148980922ac11a2cf5e257f2ba639e1",
    )
    _, label_to_id, _ = build_label_map(DEFAULT_ACTIVE_ENTITY_TYPES)
    with (root / "data" / "ner_dataset" / "train.jsonl").open(
        "r", encoding="utf-8"
    ) as handle:
        documents = [
            AnnotationDocumentV2.model_validate_json(line)
            for line in handle
            if line.strip()
        ]
    dataset = RxieTokenDataset(
        documents,
        tokenizer,
        label_to_id,
        max_input_tokens=256,
        content_overlap=64,
        is_training=True,
    )

    assert len(documents) == 279
    assert len(dataset) == 474
    for document in documents:
        windows = [
            dataset.features[index]["window"]
            for index in dataset.doc_window_map[document.document_id]
        ]
        ownership: dict[int, int] = {}
        for window in windows:
            assert len(window.input_ids) <= 256
            for global_index, label in zip(
                window.global_token_indices, window.labels, strict=True
            ):
                if global_index is not None and label != -100:
                    ownership[global_index] = ownership.get(global_index, 0) + 1
        expected_indices = set(range(max(window.token_end for window in windows)))
        assert set(ownership) == expected_indices
        assert set(ownership.values()) == {1}
