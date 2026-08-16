"""Unit tests for token classification data collator."""

import torch
from transformers import AutoTokenizer, DataCollatorForTokenClassification


def test_collator_padding_and_masking():
    tok = AutoTokenizer.from_pretrained("Qualcomm-AI-Research/BamiBERT")
    collator = DataCollatorForTokenClassification(tokenizer=tok, padding=True)

    features = [
        {"input_ids": [0, 10, 20, 2], "labels": [-100, 1, 2, -100]},
        {"input_ids": [0, 15, 2], "labels": [-100, 3, -100]},
    ]

    batch = collator(features)
    assert "input_ids" in batch
    assert "labels" in batch
    assert batch["input_ids"].shape == (2, 4)
    assert batch["labels"].shape == (2, 4)
    # The second sample should be padded with label -100
    assert batch["labels"][1, 3].item() == -100
