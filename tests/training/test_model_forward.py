"""Unit tests for model forward pass, finite loss, and backward gradient step."""

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer
from rxie.alignment import ID_TO_LABEL, LABEL_TO_ID, LABELS


def test_model_forward_backward_step():
    model_id = "Qualcomm-AI-Research/BamiBERT"
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForTokenClassification.from_pretrained(
        model_id,
        num_labels=len(LABELS),
        label2id=LABEL_TO_ID,
        id2label=ID_TO_LABEL,
    )
    model.train()

    inputs = tok("Amlodipine 5mg ngày uống 1 viên", return_tensors="pt")
    seq_len = inputs["input_ids"].shape[1]
    labels = torch.full((1, seq_len), fill_value=-100, dtype=torch.long)
    labels[0, 1] = LABEL_TO_ID["B-DRUG"]
    labels[0, 2] = LABEL_TO_ID["B-STRENGTH"]

    outputs = model(**inputs, labels=labels)
    loss = outputs.loss

    assert loss is not None
    assert torch.isfinite(loss), "Loss must be finite (no NaN or Inf)"
    assert outputs.logits.shape == (1, seq_len, len(LABELS))

    # Backward step
    loss.backward()
    grad_norm = sum(p.grad.norm().item() for p in model.parameters() if p.grad is not None)
    assert grad_norm > 0, "Gradients must be computed on backward pass"
