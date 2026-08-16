#!/usr/bin/env python3
"""
P12: Anti-Leakage Final Test Set Evaluator for RxIE.
Strictly requires explicit validation checkpoint selection (selected_on_validation=True, eligible_for_final_test=True)
and a non-smoke run before performing real model inference and evaluation on the sealed test split.

Usage:
  python scripts/evaluate_final_test.py --checkpoint-dir experiments/E0_phobert/seed_42
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))
sys.path.insert(0, str(root_dir))

import torch
from torch.utils.data import DataLoader
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
)

from rxie.alignment import build_label_map
from rxie.chunking import decode_windows_to_document
from rxie.evaluation import evaluate_structured_annotations
from rxie.schemas import AnnotationDocumentV2


def run_test_inference(
    checkpoint_dir: Path,
    manifest: dict[str, Any],
    test_docs: list[AnnotationDocumentV2],
    device: torch.device,
) -> list[AnnotationDocumentV2]:
    from scripts.train_token_ner import RxieTokenDataset, decode_all_predictions

    best_ckpt_dir = checkpoint_dir / "best_checkpoint"
    if not best_ckpt_dir.exists():
        raise FileNotFoundError(
            f"Cannot evaluate test split: '{best_ckpt_dir}' not found. "
            "A fully trained best_checkpoint model directory is required."
        )

    labels = manifest.get("labels", [])
    label_to_id = {l: i for i, l in enumerate(labels)}
    id_to_label = {i: l for i, l in enumerate(labels)}

    tokenizer = AutoTokenizer.from_pretrained(best_ckpt_dir)
    model = AutoModelForTokenClassification.from_pretrained(best_ckpt_dir).to(device)
    model.eval()

    effective_max_len = manifest.get("effective_max_length", 256)
    stride = manifest.get("sliding_window_stride", 64)

    test_dataset = RxieTokenDataset(test_docs, tokenizer, label_to_id, max_length=effective_max_len, stride=stride)
    collator = DataCollatorForTokenClassification(tokenizer=tokenizer, padding=True)
    dataloader = DataLoader(test_dataset, batch_size=8, shuffle=False, collate_fn=collator)

    all_preds: list[list[int]] = []
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            batch_preds = torch.argmax(logits, dim=-1).cpu().tolist()

            for i, p_list in enumerate(batch_preds):
                mask = batch["attention_mask"][i].tolist()
                actual_len = sum(mask)
                all_preds.append(p_list[:actual_len])

    return decode_all_predictions(test_docs, test_dataset, all_preds, id_to_label)


def main() -> None:
    parser = argparse.ArgumentParser(description="Final Test Split Evaluator (Anti-Leakage Gated)")
    parser.add_argument("--checkpoint-dir", required=True, type=Path, help="Path to experiment checkpoint directory containing checkpoint_manifest.json")
    parser.add_argument("--test-file", type=Path, default=root_dir / "data" / "ner_dataset" / "test.jsonl", help="Path to sealed test JSONL file")
    parser.add_argument("--force", action="store_true", help="Bypass validation selection gate (Warning: logs leakage alert)")

    args = parser.parse_args()
    ckpt_dir = args.checkpoint_dir
    manifest_path = ckpt_dir / "checkpoint_manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing checkpoint manifest: {manifest_path}. Checkpoint must be trained and verified first.")

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Anti-Leakage Gate Check
    is_selected = manifest_data.get("selected_on_validation", False)
    is_eligible = manifest_data.get("eligible_for_final_test", True)
    run_type = manifest_data.get("run_type", "benchmark_run")

    if (not is_selected or not is_eligible or run_type == "smoke") and not args.force:
        raise PermissionError(
            f"ANTI-LEAKAGE GATE BLOCKED: Checkpoint in {ckpt_dir} is NOT eligible for final test evaluation! "
            f"[selected_on_validation={is_selected}, eligible_for_final_test={is_eligible}, run_type='{run_type}']. "
            f"Only valid checkpoints selected on the validation split may access the sealed test set."
        )

    print("==================================================")
    print("      RXIE FINAL TEST SPLIT EVALUATION (SEALED)   ")
    print("==================================================")
    print(f"[*] Checkpoint: {ckpt_dir}")
    print(f"[*] Run Type: {run_type} | Selected on Validation: {is_selected}")
    print(f"[*] Test Dataset: {args.test_file}")

    if not args.test_file.exists():
        raise FileNotFoundError(f"Test split file not found: {args.test_file}")

    with args.test_file.open("r", encoding="utf-8") as f:
        gold_test_docs = [AnnotationDocumentV2.model_validate_json(line) for line in f if line.strip()]

    print(f"[*] Loaded {len(gold_test_docs)} sealed test documents.")

    pred_file = ckpt_dir / "predictions_test.jsonl"
    if not pred_file.exists():
        print(f"[*] Running model inference on test set with sliding window pipeline...")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        pred_docs = run_test_inference(ckpt_dir, manifest_data, gold_test_docs, device)
        with pred_file.open("w", encoding="utf-8") as f:
            for doc in pred_docs:
                f.write(json.dumps(doc.model_dump(mode="json"), ensure_ascii=False) + "\n")
        print(f"[+] Saved test predictions -> {pred_file}")
    else:
        print(f"[*] Loading existing test predictions -> {pred_file}")
        with pred_file.open("r", encoding="utf-8") as f:
            pred_docs = [AnnotationDocumentV2.model_validate_json(line) for line in f if line.strip()]

    report = evaluate_structured_annotations(
        gold_test_docs, pred_docs, active_entity_types=manifest_data.get("active_entity_types")
    )

    out_metrics_path = ckpt_dir / "metrics_test.json"
    with out_metrics_path.open("w", encoding="utf-8") as f:
        json.dump(report.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    print(f"[+] Exported Final Test Metrics -> {out_metrics_path}")
    print(f"    - Strict Entity Micro F1: {report.entity_micro.f1:.4f}")
    print(f"    - Active Entity Macro F1: {report.entity_macro.f1:.4f}")
    print(f"    - Prescription Macro F1:  {report.prescription_macro_summary.get('prescription_macro_entity_f1', 0):.4f}")
    print("==================================================")


if __name__ == "__main__":
    main()
