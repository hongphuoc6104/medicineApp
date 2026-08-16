"""Lazy, local-only Hugging Face token-classification adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .schemas import Entity, EntityType
from .text import DocumentText


class HuggingFaceTokenClassifier:
    def __init__(self, artifact_path: Path):
        # Heavy optional dependencies are imported only after an artifact is selected.
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(
            artifact_path, local_files_only=True, use_fast=True
        )
        if not self._tokenizer.is_fast:
            raise ValueError("RxIE requires a fast tokenizer for offset mapping")
        self._model = AutoModelForTokenClassification.from_pretrained(
            artifact_path, local_files_only=True
        )
        self._model.eval()
        self._model_version = str(
            getattr(self._model.config, "model_version", artifact_path.name)
        )

    @property
    def model_version(self) -> str:
        return self._model_version

    def classify(self, document: DocumentText) -> list[Entity]:
        encoded = self._tokenizer(
            document.raw_text,
            return_offsets_mapping=True,
            return_tensors="pt",
            return_overflowing_tokens=True,
            stride=64,
            truncation=True,
        )
        offsets = encoded.pop("offset_mapping").tolist()
        encoded.pop("overflow_to_sample_mapping", None)
        with self._torch.inference_mode():
            probabilities = self._model(**encoded).logits.softmax(dim=-1)
        label_ids = probabilities.argmax(dim=-1).tolist()
        scores = probabilities.max(dim=-1).values.tolist()
        labels = self._model.config.id2label
        by_offset: dict[tuple[int, int], tuple[str, float]] = {}
        for chunk_offsets, chunk_labels, chunk_scores in zip(
            offsets, label_ids, scores, strict=True
        ):
            for (start, end), label_id, score in zip(
                chunk_offsets, chunk_labels, chunk_scores, strict=True
            ):
                label = str(labels[label_id])
                previous = by_offset.get((start, end))
                if end > start and (previous is None or score > previous[1]):
                    by_offset[(start, end)] = (label, float(score))
        tokens = [
            (start, end, label, score)
            for (start, end), (label, score) in sorted(by_offset.items())
            if label != "O"
        ]
        return self._merge_bio_tokens(tokens, document)

    @staticmethod
    def _merge_bio_tokens(
        tokens: list[tuple[int, int, str, float]], document: DocumentText
    ) -> list[Entity]:
        groups: list[dict[str, Any]] = []
        for start, end, label, score in tokens:
            prefix, separator, raw_type = label.partition("-")
            entity_type = raw_type if separator else label
            if entity_type not in EntityType._value2member_map_:
                raise ValueError(f"unsupported model label: {label}")
            can_extend = (
                prefix == "I"
                and groups
                and groups[-1]["type"] == entity_type
                and start <= groups[-1]["end"] + 1
            )
            if can_extend:
                groups[-1]["end"] = end
                groups[-1]["scores"].append(score)
            else:
                groups.append({
                    "type": entity_type,
                    "start": start,
                    "end": end,
                    "scores": [score],
                })

        entities = []
        for group in groups:
            start, end = group["start"], group["end"]
            entities.append(
                Entity(
                    type=group["type"],
                    text=document.raw_text[start:end],
                    start=start,
                    end=end,
                    confidence=sum(group["scores"]) / len(group["scores"]),
                    source_region_ids=document.source_regions(start, end),
                )
            )
        return entities
