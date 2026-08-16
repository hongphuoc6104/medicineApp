"""Unit tests for effective-window token sliding and gold entity recoverability across all benchmark models."""

import json
from pathlib import Path
from transformers import AutoTokenizer

from rxie.alignment import DEFAULT_ACTIVE_ENTITY_TYPES, build_label_map
from rxie.chunking import create_token_sliding_windows
from rxie.schemas import AnnotationDocumentV2, EntityType
from rxie.tokenization import tokenize_with_offsets

root_dir = Path(__file__).resolve().parent.parent.parent


def test_phobert_token_sliding_window_gold_recovery():
    """Verify that sliding window (256/64) on PhoBERT fully encloses 100% of gold entities."""
    tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base-v2")
    active_types = DEFAULT_ACTIVE_ENTITY_TYPES

    val_file = root_dir / "data" / "ner_dataset" / "val.jsonl"
    with val_file.open("r", encoding="utf-8") as f:
        docs = [AnnotationDocumentV2.model_validate_json(l) for l in f if l.strip()]

    total_active_entities = 0
    enclosed_active_entities = 0
    multi_window_doc_count = 0

    max_length = 256
    stride = 64

    for doc in docs:
        input_ids, offsets = tokenize_with_offsets(tokenizer, doc.raw_text)
        active_doc_ents = [e for e in doc.entities if e.type in active_types]
        total_active_entities += len(active_doc_ents)

        windows = create_token_sliding_windows(
            input_ids=input_ids,
            offsets=offsets,
            labels=[0] * len(input_ids),
            max_length=max_length,
            stride=stride,
        )

        if len(windows) > 1:
            multi_window_doc_count += 1

        for ent in active_doc_ents:
            ent_tok_indices = [
                i for i, (ts, te) in enumerate(offsets)
                if ts < ent.end and te > ent.start and ts != te
            ]
            assert len(ent_tok_indices) > 0, f"No tokens mapped to entity: {ent}"
            first_t = min(ent_tok_indices)
            last_t = max(ent_tok_indices)

            is_enclosed = any(
                w.token_start <= first_t and last_t < w.token_end
                for w in windows
            )
            if is_enclosed:
                enclosed_active_entities += 1

    assert multi_window_doc_count > 0, "Validation set must contain multi-window documents for PhoBERT"
    recovery_rate = enclosed_active_entities / max(1, total_active_entities)
    assert recovery_rate == 1.0, f"PhoBERT gold recovery was {recovery_rate:.4f}, expected 1.0 (100%)"


def test_bamibert_token_window_gold_recovery():
    """Verify that BamiBERT (512/64) achieves 100% gold entity enclosure."""
    tokenizer = AutoTokenizer.from_pretrained("Qualcomm-AI-Research/BamiBERT")
    active_types = DEFAULT_ACTIVE_ENTITY_TYPES

    val_file = root_dir / "data" / "ner_dataset" / "val.jsonl"
    with val_file.open("r", encoding="utf-8") as f:
        docs = [AnnotationDocumentV2.model_validate_json(l) for l in f if l.strip()]

    total_active = 0
    enclosed_active = 0

    for doc in docs:
        input_ids, offsets = tokenize_with_offsets(tokenizer, doc.raw_text)
        active_doc_ents = [e for e in doc.entities if e.type in active_types]
        total_active += len(active_doc_ents)

        windows = create_token_sliding_windows(input_ids, offsets, [0] * len(input_ids), max_length=512, stride=64)

        for ent in active_doc_ents:
            ent_tok_indices = [
                i for i, (ts, te) in enumerate(offsets)
                if ts < ent.end and te > ent.start and ts != te
            ]
            if not ent_tok_indices:
                continue
            first_t = min(ent_tok_indices)
            last_t = max(ent_tok_indices)

            is_enclosed = any(
                w.token_start <= first_t and last_t < w.token_end
                for w in windows
            )
            if is_enclosed:
                enclosed_active = enclosed_active + 1

    assert enclosed_active == total_active, f"BamiBERT recovery was {enclosed_active}/{total_active}"
