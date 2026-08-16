"""Align exact character-span annotations to fast-tokenizer BIO labels, fuzzy alignment, and audits."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .grouping import CanonicalPrescriptionGT
from .schemas import (
    ENTITY_TO_RELATION_MAP,
    AnnotationDocument,
    AnnotationDocumentV2,
    EntityRelation,
    EntityType,
    GoldEntityV2,
    OcrDocument,
)
from .text import build_document_text

LABELS = ("O",) + tuple(
    label
    for entity_type in EntityType
    for label in (f"B-{entity_type.value}", f"I-{entity_type.value}")
)
LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}
ID_TO_LABEL = {index: label for label, index in LABEL_TO_ID.items()}

DEFAULT_ACTIVE_ENTITY_TYPES = (
    EntityType.DRUG,
    EntityType.STRENGTH,
    EntityType.DOSAGE,
    EntityType.FREQUENCY,
    EntityType.ROUTE,
    EntityType.INSTRUCTION,
)


def build_label_map(
    entity_types: Iterable[EntityType | str] | None = None,
) -> tuple[tuple[str, ...], dict[str, int], dict[int, str]]:
    """Build BIO label tuple and bidirectional index mappings for a subset of entity types."""
    types = (
        [EntityType(t) if isinstance(t, str) else t for t in entity_types]
        if entity_types is not None
        else list(DEFAULT_ACTIVE_ENTITY_TYPES)
    )
    labels = ("O",) + tuple(
        label
        for entity_type in types
        for label in (f"B-{entity_type.value}", f"I-{entity_type.value}")
    )
    label_to_id = {label: index for index, label in enumerate(labels)}
    id_to_label = {index: label for label, index in label_to_id.items()}
    return labels, label_to_id, id_to_label


E0_LABELS, E0_LABEL_TO_ID, E0_ID_TO_LABEL = build_label_map(DEFAULT_ACTIVE_ENTITY_TYPES)


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class AlignmentRecord:
    prescription_id: str
    document_id: str
    medication_id: str
    entity_type: EntityType
    canonical_text: str
    matched_text: str | None
    start: int | None
    end: int | None
    confidence: float | None
    source_region_ids: list[str]
    status: MatchStatus


def simple_string_similarity(a: str, b: str) -> float:
    """Calculate character-level similarity ratio between two strings."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    a_norm = a.strip().lower()
    b_norm = b.strip().lower()
    if a_norm == b_norm:
        return 1.0
    if a_norm in b_norm or b_norm in a_norm:
        return min(len(a_norm), len(b_norm)) / max(len(a_norm), len(b_norm))
    c_a = Counter(a_norm)
    c_b = Counter(b_norm)
    overlap = sum((c_a & c_b).values())
    total = max(len(a_norm), len(b_norm))
    return overlap / total if total > 0 else 0.0


def align_prescription_to_ocr(
    prescription: CanonicalPrescriptionGT,
    ocr_doc: OcrDocument,
) -> tuple[AnnotationDocumentV2, list[AlignmentRecord]]:
    """Anchor-based fuzzy alignment of canonical GT records to OCR text."""
    doc_text = build_document_text(ocr_doc)
    raw_text = doc_text.raw_text
    entities: list[GoldEntityV2] = []
    relations: list[EntityRelation] = []
    records: list[AlignmentRecord] = []

    entity_counter = 0

    for med in prescription.medications:
        drug_target = med.drug_raw
        if not drug_target:
            continue

        clean_drug_target = drug_target
        if med.strength_raw and med.strength_raw.lower() in clean_drug_target.lower():
            clean_drug_target = re.sub(re.escape(med.strength_raw), "", clean_drug_target, flags=re.IGNORECASE).strip()
        if not clean_drug_target:
            clean_drug_target = med.brand_raw or drug_target

        drug_idx = raw_text.lower().find(clean_drug_target.lower())
        drug_record: AlignmentRecord
        drug_entity_id: str | None = None

        if drug_idx != -1:
            d_start = drug_idx
            d_end = drug_idx + len(clean_drug_target)
            actual_text = raw_text[d_start:d_end]
            src_regions = doc_text.source_regions(d_start, d_end)
            entity_counter += 1
            drug_entity_id = f"e{entity_counter}"

            entities.append(
                GoldEntityV2(
                    entity_id=drug_entity_id,
                    type=EntityType.DRUG,
                    text=actual_text,
                    start=d_start,
                    end=d_end,
                    medication_id=med.medication_id,
                    parent_entity_id=None,
                    source_region_ids=src_regions,
                )
            )
            drug_record = AlignmentRecord(
                prescription_id=prescription.prescription_id,
                document_id=ocr_doc.document_id,
                medication_id=med.medication_id,
                entity_type=EntityType.DRUG,
                canonical_text=clean_drug_target,
                matched_text=actual_text,
                start=d_start,
                end=d_end,
                confidence=0.95,
                source_region_ids=src_regions,
                status=MatchStatus.MATCHED,
            )
        else:
            drug_record = AlignmentRecord(
                prescription_id=prescription.prescription_id,
                document_id=ocr_doc.document_id,
                medication_id=med.medication_id,
                entity_type=EntityType.DRUG,
                canonical_text=clean_drug_target,
                matched_text=None,
                start=None,
                end=None,
                confidence=0.0,
                source_region_ids=[],
                status=MatchStatus.UNRESOLVED,
            )
        records.append(drug_record)

        attributes_to_check = [
            (EntityType.STRENGTH, med.strength_raw),
            (EntityType.DOSAGE, med.dosage_raw),
            (EntityType.FREQUENCY, med.frequency_raw),
            (
                EntityType.QUANTITY,
                f"{med.quantity_value_raw or ''} {med.quantity_unit_raw or ''}".strip(),
            ),
            (EntityType.DURATION, med.duration_raw),
            (EntityType.ROUTE, med.route_raw),
            (EntityType.FORM, med.form_raw),
            (EntityType.INSTRUCTION, med.instruction_raw),
        ]

        for ent_type, target_str in attributes_to_check:
            if not target_str:
                continue

            attr_record: AlignmentRecord
            if drug_entity_id is not None:
                search_window_start = max(0, d_start - 250)
                search_window_end = min(len(raw_text), d_end + 250)
                window_text = raw_text[search_window_start:search_window_end]

                attr_idx_in_window = window_text.lower().find(target_str.lower())
                if attr_idx_in_window != -1:
                    a_start = search_window_start + attr_idx_in_window
                    a_end = a_start + len(target_str)
                    actual_attr_text = raw_text[a_start:a_end]

                    has_overlap = any(
                        not (a_end <= existing.start or a_start >= existing.end)
                        for existing in entities
                    )
                    if not has_overlap:
                        entity_counter += 1
                        attr_entity_id = f"e{entity_counter}"
                        src_regs = doc_text.source_regions(a_start, a_end)
                        entities.append(
                            GoldEntityV2(
                                entity_id=attr_entity_id,
                                type=ent_type,
                                text=actual_attr_text,
                                start=a_start,
                                end=a_end,
                                medication_id=med.medication_id,
                                parent_entity_id=drug_entity_id,
                                source_region_ids=src_regs,
                            )
                        )
                        rel_type = ENTITY_TO_RELATION_MAP[ent_type]
                        relations.append(
                            EntityRelation(
                                head_entity_id=drug_entity_id,
                                tail_entity_id=attr_entity_id,
                                relation_type=rel_type,
                            )
                        )
                        attr_record = AlignmentRecord(
                            prescription_id=prescription.prescription_id,
                            document_id=ocr_doc.document_id,
                            medication_id=med.medication_id,
                            entity_type=ent_type,
                            canonical_text=target_str,
                            matched_text=actual_attr_text,
                            start=a_start,
                            end=a_end,
                            confidence=0.90,
                            source_region_ids=src_regs,
                            status=MatchStatus.MATCHED,
                        )
                    else:
                        attr_record = AlignmentRecord(
                            prescription_id=prescription.prescription_id,
                            document_id=ocr_doc.document_id,
                            medication_id=med.medication_id,
                            entity_type=ent_type,
                            canonical_text=target_str,
                            matched_text=None,
                            start=None,
                            end=None,
                            confidence=0.5,
                            source_region_ids=[],
                            status=MatchStatus.AMBIGUOUS,
                        )
                else:
                    attr_record = AlignmentRecord(
                        prescription_id=prescription.prescription_id,
                        document_id=ocr_doc.document_id,
                        medication_id=med.medication_id,
                        entity_type=ent_type,
                        canonical_text=target_str,
                        matched_text=None,
                        start=None,
                        end=None,
                        confidence=0.0,
                        source_region_ids=[],
                        status=MatchStatus.UNRESOLVED,
                    )
            else:
                attr_record = AlignmentRecord(
                    prescription_id=prescription.prescription_id,
                    document_id=ocr_doc.document_id,
                    medication_id=med.medication_id,
                    entity_type=ent_type,
                    canonical_text=target_str,
                    matched_text=None,
                    start=None,
                    end=None,
                    confidence=0.0,
                    source_region_ids=[],
                    status=MatchStatus.UNRESOLVED,
                )
            records.append(attr_record)

    entities_sorted = sorted(entities, key=lambda e: (e.start, e.end))

    anno_doc = AnnotationDocumentV2(
        schema_version="rxie.annotation.v2",
        document_id=ocr_doc.document_id,
        prescription_id=prescription.prescription_id,
        patient_id=prescription.patient_id,
        image_id=ocr_doc.document_id,
        raw_text=raw_text,
        entities=entities_sorted,
        relations=relations,
    )
    return anno_doc, records


def generate_alignment_audit_report(
    records: list[AlignmentRecord],
) -> dict[str, Any]:
    """Generate structured audit summary matrix from alignment records."""
    total = len(records)
    if total == 0:
        return {
            "total_records": 0,
            "matched": 0,
            "ambiguous": 0,
            "unresolved": 0,
            "overall_match_rate": 0.0,
            "by_entity_type": {},
        }

    status_counts = Counter(r.status for r in records)
    matched = status_counts[MatchStatus.MATCHED]
    ambiguous = status_counts[MatchStatus.AMBIGUOUS]
    unresolved = status_counts[MatchStatus.UNRESOLVED]

    by_type: dict[str, dict[str, int | float]] = {}
    for r in records:
        t_name = r.entity_type.value
        if t_name not in by_type:
            by_type[t_name] = {"total": 0, "matched": 0, "ambiguous": 0, "unresolved": 0}
        by_type[t_name]["total"] += 1
        if r.status == MatchStatus.MATCHED:
            by_type[t_name]["matched"] += 1
        elif r.status == MatchStatus.AMBIGUOUS:
            by_type[t_name]["ambiguous"] += 1
        else:
            by_type[t_name]["unresolved"] += 1

    for t_name, metrics in by_type.items():
        metrics["match_rate"] = metrics["matched"] / metrics["total"] if metrics["total"] > 0 else 0.0

    return {
        "total_records": total,
        "matched": matched,
        "ambiguous": ambiguous,
        "unresolved": unresolved,
        "overall_match_rate": matched / total if total > 0 else 0.0,
        "by_entity_type": by_type,
    }


def generate_dataset_splits(
    aligned_documents: list[AnnotationDocumentV2],
    splits_config_path: Path | str,
    output_dir: Path | str,
) -> dict[str, int]:
    """Partition aligned documents into train/val/test JSONL files."""
    cfg_p = Path(splits_config_path)
    with cfg_p.open("r", encoding="utf-8") as f:
        splits = json.load(f)

    train_rxs = set(splits.get("train", []))
    val_rxs = set(splits.get("val", []))
    test_rxs = set(splits.get("test", []))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_docs: list[AnnotationDocumentV2] = []
    val_docs: list[AnnotationDocumentV2] = []
    test_docs: list[AnnotationDocumentV2] = []

    for doc in aligned_documents:
        if not doc.prescription_id:
            raise ValueError(f"Document {doc.document_id} missing prescription_id")
        if doc.prescription_id in train_rxs:
            train_docs.append(doc)
        elif doc.prescription_id in val_rxs:
            val_docs.append(doc)
        elif doc.prescription_id in test_rxs:
            test_docs.append(doc)

    for name, docs in [
        ("train.jsonl", train_docs),
        ("val.jsonl", val_docs),
        ("test.jsonl", test_docs),
    ]:
        target_file = out_dir / name
        with target_file.open("w", encoding="utf-8") as f:
            for d in docs:
                f.write(
                    json.dumps(d.model_dump(mode="json"), ensure_ascii=False) + "\n"
                )

    return {
        "train": len(train_docs),
        "val": len(val_docs),
        "test": len(test_docs),
    }


def verify_split_isolation(
    train_docs: list[AnnotationDocumentV2],
    val_docs: list[AnnotationDocumentV2],
    test_docs: list[AnnotationDocumentV2],
) -> dict[str, Any]:
    """Verify zero prescription ID and zero patient ID leakage across splits."""
    train_rx = {d.prescription_id for d in train_docs if d.prescription_id}
    val_rx = {d.prescription_id for d in val_docs if d.prescription_id}
    test_rx = {d.prescription_id for d in test_docs if d.prescription_id}

    train_pat = {d.patient_id for d in train_docs if d.patient_id}
    val_pat = {d.patient_id for d in val_docs if d.patient_id}
    test_pat = {d.patient_id for d in test_docs if d.patient_id}

    rx_leakage = (train_rx & val_rx) | (train_rx & test_rx) | (val_rx & test_rx)
    pat_leakage = (train_pat & val_pat) | (train_pat & test_pat) | (val_pat & test_pat)

    return {
        "is_isolated": len(rx_leakage) == 0 and len(pat_leakage) == 0,
        "rx_leakage": list(rx_leakage),
        "patient_leakage": list(pat_leakage),
        "train_rx_count": len(train_rx),
        "val_rx_count": len(val_rx),
        "test_rx_count": len(test_rx),
    }


def align_token_labels(
    document: AnnotationDocument,
    tokenizer: Any,
    allow_whitespace_boundary: bool = False,
    label_to_id: dict[str, int] | None = None,
    **tokenizer_kwargs: Any,
) -> dict[str, Any]:
    """Tokenize one document and add labels, using -100 for special tokens."""
    if not getattr(tokenizer, "is_fast", False):
        raise ValueError("alignment requires a fast tokenizer with offset mapping")
    encoded = tokenizer(
        document.raw_text, return_offsets_mapping=True, **tokenizer_kwargs
    )
    offsets = encoded.pop("offset_mapping")
    if offsets and isinstance(offsets[0][0], (list, tuple)):
        raise ValueError("overflowing/batched tokenizer output is not supported")

    active_label_to_id = label_to_id if label_to_id is not None else LABEL_TO_ID

    labels: list[int] = []
    seen_entities: set[int] = set()
    for token_start, token_end in offsets:
        if token_start == token_end:
            labels.append(-100)
            continue
        overlapping = [
            (index, entity)
            for index, entity in enumerate(document.entities)
            if entity.start < token_end and token_start < entity.end
        ]
        if not overlapping:
            labels.append(active_label_to_id["O"])
            continue
        index, entity = overlapping[0]
        if allow_whitespace_boundary:
            has_bad_prefix = token_start < entity.start and not document.raw_text[token_start:entity.start].isspace()
            has_bad_suffix = token_end > entity.end and not document.raw_text[entity.end:token_end].isspace()
        else:
            has_bad_prefix = token_start < entity.start
            has_bad_suffix = token_end > entity.end

        if len(overlapping) > 1 or has_bad_prefix or has_bad_suffix:
            raise ValueError(
                f"token offset ({token_start}, {token_end}) crosses an entity boundary"
            )
        prefix = "B" if index not in seen_entities else "I"
        tag = f"{prefix}-{entity.type.value}"
        seen_entities.add(index)
        labels.append(active_label_to_id.get(tag, active_label_to_id["O"]))

    # Only check missing for entities whose tags are supported in active_label_to_id
    active_entity_indices = {
        idx
        for idx, ent in enumerate(document.entities)
        if f"B-{ent.type.value}" in active_label_to_id
    }
    missing = active_entity_indices - seen_entities
    if missing:
        raise ValueError("one or more entities have no aligned tokens")
    encoded["labels"] = labels
    return dict(encoded)

