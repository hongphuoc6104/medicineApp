"""CLI for a minimal Hugging Face token-classification baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .alignment import ID_TO_LABEL, LABEL_TO_ID, LABELS, align_token_labels
from .annotations import load_jsonl
from .schemas import ANNOTATION_SCHEMA_VERSION


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _manifest(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "annotation_schema_version": ANNOTATION_SCHEMA_VERSION,
        "labels": list(LABELS),
        "seed": args.seed,
        "base_model": args.base_model,
        "input_sha256": {
            "train": _sha256(args.train_file),
            "validation": _sha256(args.validation_file),
        },
        "git_commit": _git_commit(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--train-file", required=True, type=Path)
    parser.add_argument("--validation-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    train_documents = load_jsonl(args.train_file)
    validation_documents = load_jsonl(args.validation_file)
    if not train_documents or not validation_documents:
        raise ValueError("train and validation files must both contain annotations")

    # Optional training dependencies stay out of import-time and test-time paths.
    import torch
    from datasets import Dataset
    from transformers import (
        AutoModelForTokenClassification,
        AutoTokenizer,
        DataCollatorForTokenClassification,
        Trainer,
        TrainingArguments,
        set_seed,
    )
    from seqeval.metrics import f1_score, precision_score, recall_score

    set_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    if not tokenizer.is_fast:
        raise ValueError("training requires a fast tokenizer")

    def prepare(documents: list[Any]) -> Dataset:
        rows = [
            align_token_labels(document, tokenizer, truncation=True)
            for document in documents
        ]
        return Dataset.from_list(rows)

    train_dataset = prepare(train_documents)
    validation_dataset = prepare(validation_documents)
    model = AutoModelForTokenClassification.from_pretrained(
        args.base_model,
        num_labels=len(LABELS),
        label2id=LABEL_TO_ID,
        id2label=ID_TO_LABEL,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "experiment_manifest.json"
    manifest_path.write_text(
        json.dumps(_manifest(args), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    def compute_metrics(prediction: Any) -> dict[str, float]:
        predicted_ids = prediction.predictions.argmax(axis=-1)
        true_predictions: list[list[str]] = []
        true_labels: list[list[str]] = []
        for row_predictions, row_labels in zip(
            predicted_ids, prediction.label_ids, strict=True
        ):
            filtered_predictions: list[str] = []
            filtered_labels: list[str] = []
            for predicted_id, label_id in zip(
                row_predictions, row_labels, strict=True
            ):
                if label_id == -100:
                    continue
                filtered_predictions.append(ID_TO_LABEL[int(predicted_id)])
                filtered_labels.append(ID_TO_LABEL[int(label_id)])
            true_predictions.append(filtered_predictions)
            true_labels.append(filtered_labels)
        return {
            "precision": precision_score(true_labels, true_predictions),
            "recall": recall_score(true_labels, true_predictions),
            "f1": f1_score(true_labels, true_predictions),
        }

    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        seed=args.seed,
        data_seed=args.seed,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        report_to=[],
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        tokenizer=tokenizer,
        data_collator=DataCollatorForTokenClassification(tokenizer),
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
