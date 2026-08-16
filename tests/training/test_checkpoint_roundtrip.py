"""Unit tests for checkpoint saving and reloading roundtrip."""

from pathlib import Path
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer
from rxie.alignment import ID_TO_LABEL, LABEL_TO_ID, LABELS


def test_checkpoint_save_and_reload(tmp_path: Path):
    model_id = "Qualcomm-AI-Research/BamiBERT"
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForTokenClassification.from_pretrained(
        model_id,
        num_labels=len(LABELS),
        label2id=LABEL_TO_ID,
        id2label=ID_TO_LABEL,
    )
    model.eval()

    inputs = tok("Atorvastatin 20mg", return_tensors="pt")
    with torch.no_grad():
        original_logits = model(**inputs).logits

    # Save to tmp_path
    save_dir = tmp_path / "test_ckpt"
    model.save_pretrained(save_dir)
    tok.save_pretrained(save_dir)

    assert (save_dir / "config.json").exists()
    assert (save_dir / "model.safetensors").exists() or (save_dir / "pytorch_model.bin").exists()

    # Reload from save_dir
    reloaded_tok = AutoTokenizer.from_pretrained(save_dir)
    reloaded_model = AutoModelForTokenClassification.from_pretrained(save_dir)
    reloaded_model.eval()

    reloaded_inputs = reloaded_tok("Atorvastatin 20mg", return_tensors="pt")
    with torch.no_grad():
        reloaded_logits = reloaded_model(**reloaded_inputs).logits

    assert torch.allclose(original_logits, reloaded_logits, atol=1e-5), "Reloaded model logits must match original"
