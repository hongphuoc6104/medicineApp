#!/usr/bin/env python3
"""
Official Token NER Training & Evaluation Runner for RxIE Benchmark V1 (E0, E1, E2).
Supports PhoBERT, BamiBERT, and ViPubmedDeBERTa with:
  - 13 active BIO labels (6 clinical entity classes)
  - Validation-based Checkpoint Selection & Early Stopping
  - Prescription-level Macro Entity F1 optimization
  - Run-level Git Provenance, Checkpoint Manifest & Full Multi-Metric Evaluation Export

Usage:
  python scripts/train_token_ner.py --model E0_phobert --seed 42 --learning-rate 2e-5
  python scripts/train_token_ner.py --model E0_phobert --seed 42 --smoke-steps 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))
sys.path.insert(0, str(root_dir))

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    get_linear_schedule_with_warmup,
)

from rxie.alignment import (
    DEFAULT_ACTIVE_ENTITY_TYPES,
    build_label_map,
)
from rxie.evaluation import evaluate_structured_annotations
from rxie.schemas import (
    AnnotationDocumentV2,
    EntityRelation,
    EntityType,
    GoldEntityV2,
    RelationType,
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_git_commit() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(root_dir),
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_COMMIT"


def get_file_sha256(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_token_offsets(tokenizer: Any, text: str) -> tuple[list[int], list[tuple[int, int]]]:
    """Extract input IDs and token (start, end) character offsets across fast and python tokenizers."""
    if getattr(tokenizer, "is_fast", False):
        enc = tokenizer(text, return_offsets_mapping=True, add_special_tokens=True)
        return enc["input_ids"], enc["offset_mapping"]

    import re
    input_ids = [tokenizer.bos_token_id] if tokenizer.bos_token_id is not None else []
    offsets = [(0, 0)] if tokenizer.bos_token_id is not None else []

    for m in re.finditer(r"\S+", text):
        w_text = m.group(0)
        w_start, w_end = m.start(), m.end()
        sub_tokens = tokenizer.tokenize(w_text)
        sub_ids = tokenizer.convert_tokens_to_ids(sub_tokens)

        cur = w_start
        for st, sid in zip(sub_tokens, sub_ids, strict=True):
            clean = st.replace("@@", "").replace("_", "")
            idx = text.lower().find(clean.lower(), cur)
            if idx != -1 and idx < w_end:
                offsets.append((idx, idx + len(clean)))
                cur = idx + len(clean)
            else:
                offsets.append((cur, w_end))
                cur = w_end
            input_ids.append(sid)

    if tokenizer.eos_token_id is not None:
        input_ids.append(tokenizer.eos_token_id)
        offsets.append((0, 0))

    return input_ids, offsets


class RxieTokenDataset(Dataset):
    def __init__(
        self,
        documents: list[AnnotationDocumentV2],
        tokenizer: Any,
        label_to_id: dict[str, int],
        max_length: int = 512,
    ) -> None:
        self.documents = documents
        self.tokenizer = tokenizer
        self.label_to_id = label_to_id
        self.max_length = max_length
        self.features: list[dict[str, Any]] = []
        self._prepare_features()

    def _prepare_features(self) -> None:
        for doc in self.documents:
            input_ids, offsets = get_token_offsets(self.tokenizer, doc.raw_text)

            # Truncate if exceeds max_length
            if len(input_ids) > self.max_length:
                input_ids = input_ids[: self.max_length]
                offsets = offsets[: self.max_length]

            labels = []
            seen_entities = set()
            for t_start, t_end in offsets:
                if t_start == t_end:
                    labels.append(-100)
                    continue
                overlapping = [
                    (idx, ent)
                    for idx, ent in enumerate(doc.entities)
                    if ent.start < t_end and t_start < ent.end
                ]
                if not overlapping:
                    labels.append(self.label_to_id["O"])
                    continue
                idx, ent = overlapping[0]
                prefix = "B" if idx not in seen_entities else "I"
                tag = f"{prefix}-{ent.type.value}"
                seen_entities.add(idx)
                labels.append(self.label_to_id.get(tag, self.label_to_id["O"]))

            attention_mask = [1] * len(input_ids)
            self.features.append({
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "labels": labels,
                "document_id": doc.document_id,
                "offsets": offsets,
            })

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        item = self.features[idx]
        return {
            "input_ids": torch.tensor(item["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(item["attention_mask"], dtype=torch.long),
            "labels": torch.tensor(item["labels"], dtype=torch.long),
        }


def decode_predictions_to_documents(
    documents: list[AnnotationDocumentV2],
    raw_features: list[dict[str, Any]],
    pred_labels: list[list[int]],
    id_to_label: dict[int, str],
) -> list[AnnotationDocumentV2]:
    pred_docs: list[AnnotationDocumentV2] = []
    doc_map = {d.document_id: d for d in documents}

    for feat, preds in zip(raw_features, pred_labels, strict=True):
        doc_id = feat["document_id"]
        source_doc = doc_map[doc_id]
        raw_text = source_doc.raw_text
        offsets = feat["offsets"]

        # Parse BIO predictions into character spans
        extracted_entities: list[GoldEntityV2] = []
        current_entity_type: str | None = None
        current_start: int = 0
        current_end: int = 0
        ent_counter = 1

        for idx, (t_start, t_end) in enumerate(offsets):
            if idx >= len(preds):
                break
            label_id = preds[idx]
            if label_id == -100:
                continue
            tag = id_to_label.get(label_id, "O")

            if tag.startswith("B-"):
                if current_entity_type is not None:
                    # Save previous entity
                    span_text = raw_text[current_start:current_end]
                    extracted_entities.append(GoldEntityV2(
                        entity_id=f"e_{ent_counter}",
                        type=EntityType(current_entity_type),
                        text=span_text,
                        start=current_start,
                        end=current_end,
                    ))
                    ent_counter += 1
                current_entity_type = tag[2:]
                current_start = t_start
                current_end = t_end
            elif tag.startswith("I-"):
                ent_type = tag[2:]
                if current_entity_type == ent_type:
                    current_end = t_end
                else:
                    if current_entity_type is not None:
                        span_text = raw_text[current_start:current_end]
                        extracted_entities.append(GoldEntityV2(
                            entity_id=f"e_{ent_counter}",
                            type=EntityType(current_entity_type),
                            text=span_text,
                            start=current_start,
                            end=current_end,
                        ))
                        ent_counter += 1
                    current_entity_type = ent_type
                    current_start = t_start
                    current_end = t_end
            else:  # "O"
                if current_entity_type is not None:
                    span_text = raw_text[current_start:current_end]
                    extracted_entities.append(GoldEntityV2(
                        entity_id=f"e_{ent_counter}",
                        type=EntityType(current_entity_type),
                        text=span_text,
                        start=current_start,
                        end=current_end,
                    ))
                    ent_counter += 1
                    current_entity_type = None

        if current_entity_type is not None:
            span_text = raw_text[current_start:current_end]
            extracted_entities.append(GoldEntityV2(
                entity_id=f"e_{ent_counter}",
                type=EntityType(current_entity_type),
                text=span_text,
                start=current_start,
                end=current_end,
            ))

        # Assign heuristic parent relations for structured evaluation
        # Link each non-DRUG entity to the nearest preceding DRUG entity
        drug_entities = [e for e in extracted_entities if e.type == EntityType.DRUG]
        relations: list[EntityRelation] = []

        for e in extracted_entities:
            if e.type != EntityType.DRUG:
                preceding_drugs = [d for d in drug_entities if d.end <= e.start]
                if preceding_drugs:
                    parent_drug = preceding_drugs[-1]
                    e.parent_entity_id = parent_drug.entity_id
                    rel_type = {
                        EntityType.STRENGTH: RelationType.HAS_STRENGTH,
                        EntityType.DOSAGE: RelationType.HAS_DOSAGE,
                        EntityType.FREQUENCY: RelationType.HAS_FREQUENCY,
                        EntityType.ROUTE: RelationType.HAS_ROUTE,
                        EntityType.INSTRUCTION: RelationType.HAS_INSTRUCTION,
                    }.get(e.type, RelationType.HAS_INSTRUCTION)
                    relations.append(EntityRelation(
                        head_entity_id=parent_drug.entity_id,
                        tail_entity_id=e.entity_id,
                        relation_type=rel_type,
                    ))

        pred_docs.append(AnnotationDocumentV2(
            schema_version="rxie.annotation.v2",
            document_id=source_doc.document_id,
            prescription_id=source_doc.prescription_id,
            patient_id=source_doc.patient_id,
            raw_text=raw_text,
            entities=extracted_entities,
            relations=relations,
        ))

    return pred_docs


def evaluate_model_on_split(
    model: Any,
    dataset: RxieTokenDataset,
    documents: list[AnnotationDocumentV2],
    id_to_label: dict[int, str],
    device: torch.device,
    batch_size: int = 8,
) -> tuple[dict[str, Any], list[AnnotationDocumentV2]]:
    model.eval()
    collator = DataCollatorForTokenClassification(tokenizer=dataset.tokenizer, padding=True)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, collate_fn=collator)
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

    pred_docs = decode_predictions_to_documents(documents, dataset.features, all_preds, id_to_label)
    report = evaluate_structured_annotations(documents, pred_docs)
    return report.model_dump(mode="python"), pred_docs


def run_training() -> None:
    parser = argparse.ArgumentParser(description="RxIE Token NER Training Runner")
    parser.add_argument("--config", type=Path, default=root_dir / "configs" / "benchmark_v1.yaml")
    parser.add_argument("--model", type=str, default="E0_phobert", choices=["E0_phobert", "E1_bamibert", "E2_vipubmeddeberta"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--smoke-steps", type=int, default=None, help="If set, runs a fast smoke training on N steps")
    parser.add_argument("--output-dir", type=Path, default=None)

    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model_cfg = cfg["models"][args.model]
    hp_cfg = cfg["hyperparameters"]

    lr = args.learning_rate or hp_cfg["learning_rates"][1]  # default 2e-5
    epochs = args.epochs or hp_cfg["epochs_max"]
    batch_size = args.batch_size or hp_cfg["batch_size"]
    max_length = hp_cfg["max_sequence_length"]

    active_entity_types = cfg["token_ner"]["active_entity_types"]
    labels, label_to_id, id_to_label = build_label_map(active_entity_types)
    num_labels = len(labels)

    out_dir = args.output_dir or root_dir / "experiments" / args.model / f"seed_{args.seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    best_ckpt_dir = out_dir / "best_checkpoint"

    print("==================================================")
    print(f"   RxIE Token NER Training: {model_cfg['name']}   ")
    print("==================================================")
    print(f"[*] Backbone: {model_cfg['backbone']}")
    print(f"[*] Seed: {args.seed} | Device: {device}")
    print(f"[*] Active Entity Classes ({len(active_entity_types)}): {active_entity_types}")
    print(f"[*] Total BIO Labels: {num_labels}")
    print(f"[*] Learning Rate: {lr} | Epochs: {epochs} | Batch Size: {batch_size}")
    print(f"[*] Output Directory: {out_dir}")

    # Load datasets
    train_docs = [AnnotationDocumentV2.model_validate_json(l) for l in (root_dir / cfg["splits"]["train_file"]).open("r") if l.strip()]
    val_docs = [AnnotationDocumentV2.model_validate_json(l) for l in (root_dir / cfg["splits"]["val_file"]).open("r") if l.strip()]

    tokenizer = AutoTokenizer.from_pretrained(model_cfg["tokenizer"])
    # Model max sequence length
    model_config = AutoModelForTokenClassification.from_pretrained(model_cfg["backbone"]).config
    max_pos = getattr(model_config, "max_position_embeddings", 512)
    # PhoBERT has max_position_embeddings=258 (256 tokens + 2 special tokens)
    effective_max_len = min(max_length, max_pos - (2 if max_pos == 258 else 0))

    print(f"[*] Effective Max Sequence Length for {args.model}: {effective_max_len} tokens")

    train_dataset = RxieTokenDataset(train_docs, tokenizer, label_to_id, max_length=effective_max_len)
    val_dataset = RxieTokenDataset(val_docs, tokenizer, label_to_id, max_length=effective_max_len)

    collator = DataCollatorForTokenClassification(tokenizer=tokenizer, padding=True)
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collator)

    # Initialize model
    model = AutoModelForTokenClassification.from_pretrained(
        model_cfg["backbone"],
        num_labels=num_labels,
        label2id=label_to_id,
        id2label=id_to_label,
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=hp_cfg["weight_decay"])
    total_steps = len(train_dataloader) * epochs if not args.smoke_steps else args.smoke_steps
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * hp_cfg["warmup_ratio"]),
        num_training_steps=total_steps,
    )

    best_val_metric = -1.0
    best_epoch = 0
    patience = cfg["early_stopping"]["patience"]
    patience_counter = 0
    training_log = []
    best_pred_docs: list[AnnotationDocumentV2] = []
    best_val_report: dict[str, Any] = {}

    step_count = 0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0

        for batch in train_dataloader:
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            batch_labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=batch_labels)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()
            step_count += 1
            if args.smoke_steps and step_count >= args.smoke_steps:
                break

        avg_train_loss = total_loss / (len(train_dataloader) if not args.smoke_steps else step_count)

        # Validation evaluation
        val_report, pred_docs = evaluate_model_on_split(model, val_dataset, val_docs, id_to_label, device, batch_size=batch_size)
        primary_metric = val_report["prescription_macro_summary"]["prescription_macro_entity_f1"]
        micro_f1 = val_report["entity_micro"]["f1"]

        log_entry = {
            "epoch": epoch,
            "train_loss": avg_train_loss,
            "val_prescription_macro_f1": primary_metric,
            "val_entity_micro_f1": micro_f1,
            "val_record_exact_match": val_report["record_exact_match"],
        }
        training_log.append(log_entry)

        print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_train_loss:.4f} | Val Rx-Macro F1: {primary_metric:.4f} | Val Micro F1: {micro_f1:.4f}")

        # Checkpoint selection
        if primary_metric > best_val_metric:
            best_val_metric = primary_metric
            best_epoch = epoch
            best_val_report = val_report
            best_pred_docs = pred_docs
            patience_counter = 0

            # Save best checkpoint
            best_ckpt_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(best_ckpt_dir)
            tokenizer.save_pretrained(best_ckpt_dir)
        else:
            patience_counter += 1
            if patience_counter >= patience and not args.smoke_steps:
                print(f"[!] Early stopping triggered at epoch {epoch} (Patience: {patience})")
                break

        if args.smoke_steps and step_count >= args.smoke_steps:
            print(f"[+] Smoke test completed after {step_count} steps.")
            break

    # Save run-level provenance & artifacts
    git_commit = get_git_commit()
    dataset_dir = root_dir / "data" / "ner_dataset"

    environment_record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_git_commit": git_commit,
        "dataset_version": cfg["dataset_version"],
        "dataset_checksums": {
            "train.jsonl": get_file_sha256(dataset_dir / "train.jsonl"),
            "val.jsonl": get_file_sha256(dataset_dir / "val.jsonl"),
            "test.jsonl": get_file_sha256(dataset_dir / "test.jsonl"),
        },
        "system": {
            "python_version": sys.version,
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        },
    }

    manifest_record = {
        "model_id": args.model,
        "model_name": model_cfg["name"],
        "seed": args.seed,
        "selected_on_validation": True,
        "best_epoch": best_epoch,
        "best_validation_metric": best_val_metric,
        "primary_metric_name": cfg["model_selection"]["primary_metric"],
        "active_entity_types": active_entity_types,
        "num_labels": num_labels,
        "labels": labels,
        "source_git_commit": git_commit,
        "dataset_version": cfg["dataset_version"],
        "dataset_checksums": environment_record["dataset_checksums"],
    }

    with (out_dir / "environment.json").open("w", encoding="utf-8") as f:
        json.dump(environment_record, f, ensure_ascii=False, indent=2)

    with (out_dir / "checkpoint_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest_record, f, ensure_ascii=False, indent=2)

    with (out_dir / "training_log.json").open("w", encoding="utf-8") as f:
        json.dump(training_log, f, ensure_ascii=False, indent=2)

    with (out_dir / "metrics_val.json").open("w", encoding="utf-8") as f:
        json.dump(best_val_report, f, ensure_ascii=False, indent=2)

    with (out_dir / "predictions_val.jsonl").open("w", encoding="utf-8") as f:
        for doc in best_pred_docs:
            f.write(json.dumps(doc.model_dump(mode="json"), ensure_ascii=False) + "\n")

    print("==================================================")
    print(f"[+] Training completed successfully for {args.model} (Seed {args.seed})")
    print(f"    - Best Epoch: {best_epoch} | Best Rx-Macro F1: {best_val_metric:.4f}")
    print(f"    - Checkpoint & Manifest: {out_dir / 'checkpoint_manifest.json'}")
    print(f"    - Validation Metrics:    {out_dir / 'metrics_val.json'}")
    print("==================================================")


if __name__ == "__main__":
    run_training()
