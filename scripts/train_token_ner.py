#!/usr/bin/env python3
# ruff: noqa: E402
"""
Official Token NER Training & Evaluation Runner for RxIE Benchmark V1 (E0, E1, E2).
Supports PhoBERT, BamiBERT, and ViPubmedDeBERTa with:
  - Token-level Sliding Window with Non-Duplicate Loss Masking during Training
  - 13 active BIO labels (6 clinical entity classes)
  - Isolated Output Directory Convention:
      Tuning: experiments/<model>/tuning/lr_<lr>_seed_<seed>/
       Official: experiments/<model>/official/seed_<seed>/
      Smoke:  experiments/<model>/smoke/seed_<seed>/
   - Protocol B: official runs require a global-LR selection manifest and train fresh
  - Single Source of Truth Tokenization via rxie.tokenization.tokenize_with_offsets
  - Active-class Macro F1 Evaluation (exclusively across 6 active trainable classes)
  - Run-level Git Provenance, Checkpoint Manifest & Full Multi-Metric Evaluation Export

Usage:
  # Hyperparameter tuning run (validation only, test blocked):
  python scripts/train_token_ner.py --model E0_phobert --run-type tuning
    --learning-rate 2e-5 --seed 42

  # Fresh official run after global LR selection:
  python scripts/train_token_ner.py --model E0_phobert --run-type official
    --selection-manifest reports/benchmark_v1/E0_phobert/selection_manifest.json
    --seed 42

  # Quick smoke run (validation only, test blocked):
  python scripts/train_token_ner.py --model E0_phobert --run-type smoke
    --smoke-steps 3 --seed 42
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
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

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
from transformers import (
    __version__ as transformers_version,
)

from rxie.alignment import (
    build_label_map,
)
from rxie.benchmark_protocol import (
    benchmark_implementation_sha256,
    load_and_validate_selection_manifest,
    sha256_directory,
    sha256_file,
)
from rxie.chunking import (
    create_token_sliding_windows,
    decode_windows_to_document,
)
from rxie.evaluation import evaluate_structured_annotations
from rxie.schemas import (
    AnnotationDocumentV2,
)
from rxie.tokenization import tokenize_with_offsets


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)


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


def is_git_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(root_dir),
    )
    return bool(result.stdout.strip())


def get_file_sha256(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class RxieTokenDataset(Dataset):
    def __init__(
        self,
        documents: list[AnnotationDocumentV2],
        tokenizer: Any,
        label_to_id: dict[str, int],
        max_input_tokens: int = 256,
        content_overlap: int = 64,
        is_training: bool = False,
    ) -> None:
        self.documents = documents
        self.tokenizer = tokenizer
        self.label_to_id = label_to_id
        self.max_input_tokens = max_input_tokens
        self.content_overlap = content_overlap
        self.is_training = is_training
        self.features: list[dict[str, Any]] = []
        self.doc_window_map: dict[str, list[int]] = {}
        self.multi_window_doc_count = 0
        self._prepare_features()

    def _prepare_features(self) -> None:
        feature_idx = 0
        for doc in self.documents:
            input_ids, offsets = tokenize_with_offsets(
                self.tokenizer,
                doc.raw_text,
                add_special_tokens=False,
            )

            labels = []
            seen_entities = set()
            entity_token_indices: dict[int, list[int]] = {}
            for t_start, t_end in offsets:
                overlapping = [
                    (idx, ent)
                    for idx, ent in enumerate(doc.entities)
                    if ent.start < t_end and t_start < ent.end
                ]
                if not overlapping:
                    labels.append(self.label_to_id["O"])
                    continue
                if len(overlapping) > 1:
                    raise ValueError(
                        f"Token [{t_start}:{t_end}] overlaps multiple gold entities "
                        f"in {doc.document_id}"
                    )
                idx, ent = overlapping[0]
                prefix = "B" if idx not in seen_entities else "I"
                tag = f"{prefix}-{ent.type.value}"
                seen_entities.add(idx)
                label_id = self.label_to_id.get(tag, self.label_to_id["O"])
                labels.append(label_id)
                if label_id != self.label_to_id["O"]:
                    entity_token_indices.setdefault(idx, []).append(len(labels) - 1)

            entity_token_ranges = []
            active_entity_indices = {
                index
                for index, entity in enumerate(doc.entities)
                if f"B-{entity.type.value}" in self.label_to_id
            }
            if set(entity_token_indices) != active_entity_indices:
                missing = sorted(active_entity_indices - set(entity_token_indices))
                raise ValueError(
                    f"Active entities without token alignment in "
                    f"{doc.document_id}: {missing}"
                )
            for token_indices in entity_token_indices.values():
                if token_indices != list(
                    range(token_indices[0], token_indices[-1] + 1)
                ):
                    raise ValueError(
                        f"Non-contiguous entity token alignment in {doc.document_id}"
                    )
                entity_token_ranges.append((token_indices[0], token_indices[-1] + 1))

            windows = create_token_sliding_windows(
                input_ids=input_ids,
                offsets=offsets,
                labels=labels,
                tokenizer=self.tokenizer,
                max_input_tokens=self.max_input_tokens,
                content_overlap=self.content_overlap,
                mask_overlap_for_training=self.is_training,
                entity_token_ranges=entity_token_ranges,
            )

            if len(windows) > 1:
                self.multi_window_doc_count += 1

            self.doc_window_map[doc.document_id] = []
            for win in windows:
                self.features.append(
                    {
                        "document_id": doc.document_id,
                        "window": win,
                        "input_ids": win.input_ids,
                        "attention_mask": win.attention_mask,
                        "labels": win.labels,
                        "offsets": win.offsets,
                    }
                )
                self.doc_window_map[doc.document_id].append(feature_idx)
                feature_idx += 1

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        item = self.features[idx]
        return {
            "input_ids": torch.tensor(item["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(item["attention_mask"], dtype=torch.long),
            "labels": torch.tensor(item["labels"], dtype=torch.long),
        }


def decode_all_predictions(
    documents: list[AnnotationDocumentV2],
    dataset: RxieTokenDataset,
    all_logits: list[list[list[float]]],
    id_to_label: dict[int, str],
) -> list[AnnotationDocumentV2]:
    pred_docs: list[AnnotationDocumentV2] = []
    for doc in documents:
        win_indices = dataset.doc_window_map[doc.document_id]
        doc_windows = [dataset.features[i]["window"] for i in win_indices]
        doc_logits = [all_logits[i] for i in win_indices]
        pred_doc = decode_windows_to_document(doc, doc_windows, doc_logits, id_to_label)
        pred_docs.append(pred_doc)
    return pred_docs


def evaluate_model_on_split(
    model: Any,
    dataset: RxieTokenDataset,
    documents: list[AnnotationDocumentV2],
    id_to_label: dict[int, str],
    device: torch.device,
    batch_size: int = 8,
    active_entity_types: Any = None,
) -> tuple[dict[str, Any], list[AnnotationDocumentV2]]:
    model.eval()
    collator = DataCollatorForTokenClassification(
        tokenizer=dataset.tokenizer, padding=True
    )
    dataloader = DataLoader(
        dataset, batch_size=batch_size, shuffle=False, collate_fn=collator
    )
    all_logits: list[list[list[float]]] = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            for i in range(outputs.logits.shape[0]):
                mask = batch["attention_mask"][i].tolist()
                actual_len = sum(mask)
                all_logits.append(outputs.logits[i, :actual_len].cpu().tolist())

    pred_docs = decode_all_predictions(documents, dataset, all_logits, id_to_label)
    report = evaluate_structured_annotations(
        documents,
        pred_docs,
        active_entity_types=active_entity_types,
        task_type="token_ner",
    )
    return report.model_dump(mode="python"), pred_docs


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RxIE Token NER Training Runner")
    parser.add_argument(
        "--config", type=Path, default=root_dir / "configs" / "benchmark_v1.yaml"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="E0_phobert",
        choices=["E0_phobert", "E1_bamibert", "E2_vipubmeddeberta"],
    )
    parser.add_argument(
        "--run-type",
        required=True,
        choices=["tuning", "smoke", "official"],
        help="Execution mode; official requires a selector-produced manifest",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument(
        "--smoke-steps",
        type=int,
        default=None,
        help="If set, runs a fast smoke training on N steps",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--selection-manifest", type=Path, default=None)
    return parser


def run_training() -> None:
    parser = build_argument_parser()

    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    model_cfg = cfg["models"][args.model]
    hp_cfg = cfg["hyperparameters"]

    configured_lrs = [float(value) for value in hp_cfg["learning_rates"]]
    configured_seeds = [int(value) for value in cfg["seeds"]]
    if args.seed not in configured_seeds:
        parser.error(f"--seed must be one of {configured_seeds}")
    if args.run_type == "tuning":
        if (
            args.learning_rate is None
            or float(args.learning_rate) not in configured_lrs
        ):
            parser.error(f"tuning requires --learning-rate from {configured_lrs}")
        if (
            args.selection_manifest is not None
            or args.smoke_steps is not None
            or args.output_dir is not None
            or args.epochs is not None
            or args.batch_size is not None
        ):
            parser.error(
                "tuning forbids --selection-manifest, --smoke-steps, --output-dir, "
                "--epochs, and --batch-size"
            )
    elif args.run_type == "official":
        if args.selection_manifest is None:
            parser.error("official requires --selection-manifest")
        if (
            args.learning_rate is not None
            or args.smoke_steps is not None
            or args.output_dir is not None
            or args.epochs is not None
            or args.batch_size is not None
        ):
            parser.error(
                "official forbids --learning-rate, --smoke-steps, --output-dir, "
                "--epochs, and --batch-size"
            )
    elif args.selection_manifest is not None:
        parser.error("smoke forbids --selection-manifest")

    canonical_config_path = root_dir / "configs" / "benchmark_v1.yaml"
    if (
        args.run_type != "smoke"
        and args.config.resolve() != canonical_config_path.resolve()
    ):
        parser.error("tuning and official runs require the canonical benchmark config")
    source_git_commit = get_git_commit()
    source_git_dirty = is_git_dirty()
    if args.run_type != "smoke" and (
        source_git_commit == "UNKNOWN_COMMIT" or source_git_dirty
    ):
        parser.error("tuning and official runs require a clean, committed source tree")

    dataset_dir = root_dir / "data" / "ner_dataset"
    release_manifest_path = dataset_dir / "release_manifest.json"
    with release_manifest_path.open("r", encoding="utf-8") as handle:
        release_manifest = json.load(handle)
    if release_manifest["dataset_version"] != cfg["dataset_version"]:
        raise RuntimeError("Dataset release version does not match benchmark config")
    for split_name in ["train", "val"]:
        split_path = root_dir / cfg["splits"][f"{split_name}_file"]
        expected_hash = release_manifest["file_checksums_sha256"][f"{split_name}.jsonl"]
        if get_file_sha256(split_path) != expected_hash:
            raise RuntimeError(f"Frozen dataset checksum mismatch: {split_name}.jsonl")

    selection_manifest = None
    selection_manifest_sha256 = None
    if args.run_type == "official":
        expected_selection_path = root_dir / cfg["selection"][
            "manifest_path_template"
        ].format(model=args.model)
        if args.selection_manifest.resolve() != expected_selection_path.resolve():
            parser.error(
                "official requires canonical selection manifest: "
                f"{expected_selection_path}"
            )
        selection_manifest, lr = load_and_validate_selection_manifest(
            args.selection_manifest,
            config=cfg,
            config_path=args.config,
            model_id=args.model,
            repository_root=root_dir,
        )
        selection_manifest_sha256 = sha256_file(args.selection_manifest)
    else:
        lr = float(args.learning_rate or configured_lrs[1])
    epochs = args.epochs or hp_cfg["epochs_max"]
    batch_size = args.batch_size or hp_cfg["batch_size"]
    content_overlap = int(hp_cfg["content_overlap"])
    is_smoke = args.run_type == "smoke"
    smoke_steps = args.smoke_steps or 3
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Isolated output directory convention
    if args.output_dir is not None:
        out_dir = args.output_dir
    else:
        lr_str = f"{lr:.1e}"
        if args.run_type == "tuning":
            out_dir = (
                root_dir
                / "experiments"
                / args.model
                / "tuning"
                / f"lr_{lr_str}_seed_{args.seed}"
            )
        elif args.run_type == "smoke":
            out_dir = (
                root_dir / "experiments" / args.model / "smoke" / f"seed_{args.seed}"
            )
        else:
            out_dir = (
                root_dir / "experiments" / args.model / "official" / f"seed_{args.seed}"
            )

    if out_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing run directory: {out_dir}"
        )
    out_dir.mkdir(parents=True, exist_ok=False)
    best_ckpt_dir = out_dir / "best_checkpoint"

    active_entity_types = cfg["token_ner"]["active_entity_types"]
    labels, label_to_id, id_to_label = build_label_map(active_entity_types)
    num_labels = len(labels)

    tokenizer = AutoTokenizer.from_pretrained(
        model_cfg["tokenizer_id"],
        revision=model_cfg["tokenizer_revision"],
    )
    max_input_tokens = int(model_cfg["max_input_tokens"])
    special_token_count = int(tokenizer.num_special_tokens_to_add(pair=False))
    content_capacity = max_input_tokens - special_token_count

    print("==================================================")
    print(f"   RxIE Token NER Training: {model_cfg['name']}   ")
    print("==================================================")
    print(f"[*] Backbone: {model_cfg['backbone_id']}@{model_cfg['backbone_revision']}")
    print(
        f"[*] Run Type: {args.run_type.upper()} | Seed: {args.seed} | Device: {device}"
    )
    print(
        f"[*] Max Input: {max_input_tokens} total | "
        f"Content Capacity: {content_capacity} "
        f"| Content Overlap: {content_overlap}"
    )
    print(
        f"[*] Active Entity Classes ({len(active_entity_types)}): {active_entity_types}"
    )
    print(f"[*] Total BIO Labels: {num_labels}")
    print(f"[*] Learning Rate: {lr} | Epochs: {epochs} | Batch Size: {batch_size}")
    print(f"[*] Output Directory: {out_dir}")

    # Load datasets
    train_docs = [
        AnnotationDocumentV2.model_validate_json(line)
        for line in (root_dir / cfg["splits"]["train_file"]).open("r")
        if line.strip()
    ]
    val_docs = [
        AnnotationDocumentV2.model_validate_json(line)
        for line in (root_dir / cfg["splits"]["val_file"]).open("r")
        if line.strip()
    ]

    train_dataset = RxieTokenDataset(
        train_docs,
        tokenizer,
        label_to_id,
        max_input_tokens=max_input_tokens,
        content_overlap=content_overlap,
        is_training=True,
    )
    val_dataset = RxieTokenDataset(
        val_docs,
        tokenizer,
        label_to_id,
        max_input_tokens=max_input_tokens,
        content_overlap=content_overlap,
        is_training=False,
    )

    print(
        f"[*] Train Windows: {len(train_dataset)} from {len(train_docs)} docs "
        f"({train_dataset.multi_window_doc_count} multi-window docs)"
    )
    print(
        f"[*] Val Windows:   {len(val_dataset)} from {len(val_docs)} docs "
        f"({val_dataset.multi_window_doc_count} multi-window docs)"
    )

    collator = DataCollatorForTokenClassification(tokenizer=tokenizer, padding=True)
    data_generator = torch.Generator()
    data_generator.manual_seed(args.seed)
    train_dataloader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collator,
        generator=data_generator,
    )

    # Initialize model
    model = AutoModelForTokenClassification.from_pretrained(
        model_cfg["backbone_id"],
        revision=model_cfg["backbone_revision"],
        num_labels=num_labels,
        label2id=label_to_id,
        id2label=id_to_label,
    ).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=lr, weight_decay=hp_cfg["weight_decay"]
    )
    total_steps = len(train_dataloader) * epochs if not is_smoke else smoke_steps
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

            outputs = model(
                input_ids=input_ids, attention_mask=attention_mask, labels=batch_labels
            )
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()
            step_count += 1
            if is_smoke and step_count >= smoke_steps:
                break

        avg_train_loss = total_loss / (
            len(train_dataloader) if not is_smoke else step_count
        )

        # Validation evaluation with multi-window decoding and active-class macro PRF
        val_report, pred_docs = evaluate_model_on_split(
            model,
            val_dataset,
            val_docs,
            id_to_label,
            device,
            batch_size=batch_size,
            active_entity_types=active_entity_types,
        )
        primary_metric = val_report["prescription_macro_summary"][
            "prescription_macro_entity_f1"
        ]
        micro_f1 = val_report["entity_micro"]["f1"]
        active_macro_f1 = val_report["entity_macro"]["f1"]

        log_entry = {
            "epoch": epoch,
            "train_loss": avg_train_loss,
            "val_prescription_macro_f1": primary_metric,
            "val_entity_micro_f1": micro_f1,
            "val_active_entity_macro_f1": active_macro_f1,
            "val_record_exact_match": None,
        }
        training_log.append(log_entry)

        print(
            f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_train_loss:.4f} "
            f"| Val Rx-Macro F1: {primary_metric:.4f} "
            f"| Active Macro F1: {active_macro_f1:.4f} "
            f"| Micro F1: {micro_f1:.4f}"
        )

        # Checkpoint selection
        if primary_metric > best_val_metric or is_smoke:
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
            if patience_counter >= patience and not is_smoke:
                print(
                    f"[!] Early stopping triggered at epoch {epoch} "
                    f"(Patience: {patience})"
                )
                break

        if is_smoke and step_count >= smoke_steps:
            print(f"[+] Smoke test completed after {step_count} steps.")
            break

    # Save run-level provenance & artifacts
    git_commit = source_git_commit

    environment_record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_git_commit": git_commit,
        "source_git_dirty": source_git_dirty,
        "dataset_version": cfg["dataset_version"],
        "dataset_checksums": {
            "train.jsonl": get_file_sha256(dataset_dir / "train.jsonl"),
            "val.jsonl": get_file_sha256(dataset_dir / "val.jsonl"),
            "test.jsonl": release_manifest["file_checksums_sha256"]["test.jsonl"],
        },
        "system": {
            "python_version": sys.version,
            "torch_version": torch.__version__,
            "transformers_version": transformers_version,
            "numpy_version": np.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_name": torch.cuda.get_device_name(0)
            if torch.cuda.is_available()
            else "CPU",
            "cuda_version": torch.version.cuda,
            "cudnn_version": torch.backends.cudnn.version()
            if torch.cuda.is_available()
            else None,
        },
        "determinism": {
            "python_numpy_torch_cuda_seed": args.seed,
            "cudnn_deterministic": torch.backends.cudnn.deterministic,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        },
    }

    manifest_record = {
        "model_id": args.model,
        "model_name": model_cfg["name"],
        "seed": args.seed,
        "learning_rate": lr,
        "manifest_schema_version": "rxie.checkpoint_manifest.v2",
        "protocol_version": cfg["protocol_version"],
        "run_type": args.run_type,
        "best_epoch": best_epoch,
        "best_validation_metric": best_val_metric,
        "primary_metric_name": cfg["model_selection"]["primary_metric"],
        "max_input_tokens": max_input_tokens,
        "special_token_count": special_token_count,
        "content_capacity": content_capacity,
        "content_overlap": content_overlap,
        "active_entity_types": active_entity_types,
        "num_labels": num_labels,
        "labels": labels,
        "source_git_commit": git_commit,
        "source_git_dirty": source_git_dirty,
        "config_sha256": sha256_file(args.config),
        "dataset_version": cfg["dataset_version"],
        "dataset_checksums": environment_record["dataset_checksums"],
        "backbone_id": model_cfg["backbone_id"],
        "backbone_revision": model_cfg["backbone_revision"],
        "tokenizer_id": model_cfg["tokenizer_id"],
        "tokenizer_revision": model_cfg["tokenizer_revision"],
        "batch_size": batch_size,
        "epochs_max": epochs,
        "weight_decay": hp_cfg["weight_decay"],
        "warmup_ratio": hp_cfg["warmup_ratio"],
        "total_steps": total_steps,
        "sampling_policy": cfg["sampling"]["policy"],
        "benchmark_implementation_sha256": benchmark_implementation_sha256(root_dir),
        "selection_manifest_sha256": selection_manifest_sha256,
        "selection_manifest_path": (
            str(args.selection_manifest.resolve().relative_to(root_dir.resolve()))
            if args.selection_manifest is not None
            else None
        ),
        "selected_lr": selection_manifest.get("selected_lr")
        if selection_manifest
        else None,
        "best_checkpoint_sha256": sha256_directory(best_ckpt_dir),
    }

    with (out_dir / "environment.json").open("x", encoding="utf-8") as f:
        json.dump(environment_record, f, ensure_ascii=False, indent=2)
        f.write("\n")

    manifest_record["environment_sha256"] = get_file_sha256(
        out_dir / "environment.json"
    )

    with (out_dir / "checkpoint_manifest.json").open("x", encoding="utf-8") as f:
        json.dump(manifest_record, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with (out_dir / "training_log.json").open("x", encoding="utf-8") as f:
        json.dump(training_log, f, ensure_ascii=False, indent=2)

    with (out_dir / "metrics_val.json").open("x", encoding="utf-8") as f:
        json.dump(best_val_report, f, ensure_ascii=False, indent=2)

    with (out_dir / "predictions_val.jsonl").open("x", encoding="utf-8") as f:
        for doc in best_pred_docs:
            f.write(json.dumps(doc.model_dump(mode="json"), ensure_ascii=False) + "\n")

    print("==================================================")
    print(f"[+] Training completed successfully for {args.model} (Seed {args.seed})")
    print(f"    - Run Type: {args.run_type.upper()}")
    print(f"    - Best Epoch: {best_epoch} | Best Rx-Macro F1: {best_val_metric:.4f}")
    print(f"    - Checkpoint & Manifest: {out_dir / 'checkpoint_manifest.json'}")
    print(f"    - Validation Metrics:    {out_dir / 'metrics_val.json'}")
    print("==================================================")


if __name__ == "__main__":
    run_training()
