"""Shared fixtures, test doubles, and canonical reference helpers for RxIE E2E tests."""

from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field, model_validator

from rxie.grouping import (
    CanonicalMedication,
    CanonicalPrescriptionGT,
)
from rxie.schemas import (
    AnnotationProvenance,
    BoundingBox,
    Entity,
    EntityType,
    OcrDocument,
    OcrEngine,
    OcrPage,
    OcrRegion,
)
from rxie.text import build_document_text

# ==============================================================================
# 1. Relational V2 Schema & Relation Contracts
# ==============================================================================


class RelationType(str, Enum):
    HAS_STRENGTH = "HAS_STRENGTH"
    HAS_DOSAGE = "HAS_DOSAGE"
    HAS_FREQUENCY = "HAS_FREQUENCY"
    HAS_QUANTITY = "HAS_QUANTITY"
    HAS_DURATION = "HAS_DURATION"
    HAS_ROUTE = "HAS_ROUTE"
    HAS_INSTRUCTION = "HAS_INSTRUCTION"
    HAS_FORM = "HAS_FORM"


ENTITY_TO_RELATION_MAP = {
    EntityType.STRENGTH: RelationType.HAS_STRENGTH,
    EntityType.DOSAGE: RelationType.HAS_DOSAGE,
    EntityType.FREQUENCY: RelationType.HAS_FREQUENCY,
    EntityType.QUANTITY: RelationType.HAS_QUANTITY,
    EntityType.DURATION: RelationType.HAS_DURATION,
    EntityType.ROUTE: RelationType.HAS_ROUTE,
    EntityType.INSTRUCTION: RelationType.HAS_INSTRUCTION,
    EntityType.FORM: RelationType.HAS_FORM,
}


class GoldEntityV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: Annotated[str, Field(min_length=1)]
    type: EntityType
    text: Annotated[str, Field(min_length=1)]
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(gt=0)]
    medication_id: Annotated[str, Field(min_length=1)] | None = None
    parent_entity_id: Annotated[str, Field(min_length=1)] | None = None
    source_region_ids: list[str] = Field(default_factory=list)
    normalized: str | None = None

    @model_validator(mode="after")
    def validate_span(self) -> GoldEntityV2:
        if self.end <= self.start:
            raise ValueError("gold entity span must satisfy start < end")
        if self.type == EntityType.DRUG and self.parent_entity_id is not None:
            raise ValueError("DRUG entity must have parent_entity_id == None")
        return self


class EntityRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    head_entity_id: Annotated[str, Field(min_length=1)]
    tail_entity_id: Annotated[str, Field(min_length=1)]
    relation_type: RelationType


class AnnotationDocumentV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["rxie.annotation.v2"] = "rxie.annotation.v2"
    document_id: Annotated[str, Field(min_length=1)]
    prescription_id: Annotated[str, Field(min_length=1)] | None = None
    patient_id: str | None = None
    image_id: str | None = None
    raw_text: str
    entities: list[GoldEntityV2]
    relations: list[EntityRelation] = Field(default_factory=list)
    provenance: AnnotationProvenance = Field(default_factory=AnnotationProvenance)

    @model_validator(mode="after")
    def validate_document(self) -> AnnotationDocumentV2:
        # Check unique entity IDs
        entity_ids = [e.entity_id for e in self.entities]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("entity_id must be unique within document")

        entity_map = {e.entity_id: e for e in self.entities}

        # Validate spans
        ordered = sorted(self.entities, key=lambda e: (e.start, e.end))
        prev_end = 0
        for e in ordered:
            if e.end > len(self.raw_text):
                msg = f"entity span ({e.start}, {e.end}) exceeds raw_text length"
                raise ValueError(msg)
            if self.raw_text[e.start : e.end] != e.text:
                msg = f"entity text '{e.text}' does not match raw_text"
                raise ValueError(msg)
            if e.start < prev_end:
                msg = f"gold entity spans must not overlap: {e.text}"
                raise ValueError(msg)
            prev_end = e.end

            # Validate parent pointer
            if e.parent_entity_id is not None:
                if e.parent_entity_id not in entity_map:
                    raise ValueError(
                        f"parent_entity_id '{e.parent_entity_id}' not found in document"
                    )
                parent_entity = entity_map[e.parent_entity_id]
                if parent_entity.type != EntityType.DRUG:
                    msg = (
                        f"parent '{e.parent_entity_id}' must be of type DRUG, "
                        f"got {parent_entity.type}"
                    )
                    raise ValueError(msg)

        # Validate relations
        for rel in self.relations:
            if rel.head_entity_id not in entity_map:
                raise ValueError(
                    f"relation head '{rel.head_entity_id}' not found"
                )
            if rel.tail_entity_id not in entity_map:
                raise ValueError(
                    f"relation tail '{rel.tail_entity_id}' not found"
                )
            head = entity_map[rel.head_entity_id]
            tail = entity_map[rel.tail_entity_id]
            if head.type != EntityType.DRUG:
                raise ValueError(f"relation head must be DRUG, got {head.type}")
            expected_rel = ENTITY_TO_RELATION_MAP.get(tail.type)
            if expected_rel and rel.relation_type != expected_rel:
                raise ValueError(
                    f"relation {rel.relation_type} does not match tail entity type {expected_rel}"
                )

        return self


# ==============================================================================
# 2. Ingestion & ML Kit Parsing Helpers
# ==============================================================================


def clamp_coordinate(val: float, max_val: float) -> float:
    return max(0.0, min(float(val), float(max_val)))


def clamp_confidence(val: float | None) -> float | None:
    if val is None:
        return None
    return max(0.0, min(1.0, float(val)))


def parse_mlkit_json_data(
    data: dict[str, Any], document_id: str | None = None
) -> OcrDocument:
    """Parse raw Android Google ML Kit OCR JSON structure into OcrDocument."""
    doc_id = (
        document_id
        or data.get("documentId")
        or data.get("document_id")
        or "doc_synthetic"
    )

    raw_width = data.get("imageWidth") if "imageWidth" in data else data.get("width")
    width = int(raw_width) if raw_width is not None else 1000

    raw_height = (
        data.get("imageHeight") if "imageHeight" in data else data.get("height")
    )
    height = int(raw_height) if raw_height is not None else 1000

    if width <= 0 or height <= 0:
        raise ValueError("page width and height must be positive integers")

    raw_blocks = data.get("blocks", [])
    if not isinstance(raw_blocks, list):
        raise ValueError("blocks must be a list")

    regions: list[OcrRegion] = []
    reading_order_counter = 0

    for b_idx, block in enumerate(raw_blocks):
        if not isinstance(block, dict):
            raise ValueError("block must be a dict")
        lines = block.get("lines", [])
        if not isinstance(lines, list):
            raise ValueError("lines must be a list")
        for l_idx, line in enumerate(lines):
            if not isinstance(line, dict):
                raise ValueError("line must be a dict")
            line_text = line.get("text", "")
            conf = clamp_confidence(line.get("confidence"))
            region_id = f"p0_b{b_idx}_l{l_idx}"

            # Corner points vs bounding box
            corner_pts = line.get("cornerPoints")
            if corner_pts and len(corner_pts) == 4:
                pts = []
                for pt in corner_pts:
                    if isinstance(pt, dict):
                        px = clamp_coordinate(pt.get("x", 0.0), width)
                        py = clamp_coordinate(pt.get("y", 0.0), height)
                    else:
                        px = clamp_coordinate(pt[0], width)
                        py = clamp_coordinate(pt[1], height)
                    pts.append((px, py))
                bbox_points = (pts[0], pts[1], pts[2], pts[3])
            else:
                bbox_dict = line.get("boundingBox", {})
                left = clamp_coordinate(bbox_dict.get("left", 0.0), width)
                top = clamp_coordinate(bbox_dict.get("top", 0.0), height)
                right = clamp_coordinate(
                    bbox_dict.get("right", min(width, left + 100.0)), width
                )
                bottom = clamp_coordinate(
                    bbox_dict.get("bottom", min(height, top + 30.0)), height
                )
                bbox_points = (
                    (left, top),
                    (right, top),
                    (right, bottom),
                    (left, bottom),
                )

            region = OcrRegion(
                region_id=region_id,
                text=line_text,
                confidence=conf,
                reading_order=reading_order_counter,
                bbox=BoundingBox(points=bbox_points),
            )
            regions.append(region)
            reading_order_counter += 1

    page = OcrPage(
        width=width,
        height=height,
        page_index=0,
        regions=regions,
    )
    engine = OcrEngine(
        name=data.get("ocrEngine", {}).get("name", "google_mlkit_text_recognition"),
        version=data.get("ocrEngine", {}).get("version", "0.15.1"),
    )
    return OcrDocument(
        schema_version="rxie.ocr.v1",
        document_id=doc_id,
        ocr_engine=engine,
        pages=[page],
    )


def load_mlkit_ocr_document(path: Path | str) -> OcrDocument:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return parse_mlkit_json_data(data, document_id=file_path.stem)


def ingest_all_mlkit_captures(
    source_dir: Path | str = "data/ocr_final",
    fail_fast: bool = True,
) -> dict[str, OcrDocument]:
    src = Path(source_dir)
    if not src.exists() or not src.is_dir():
        raise FileNotFoundError(f"OCR directory not found: {source_dir}")

    results: dict[str, OcrDocument] = {}
    for p in sorted(src.glob("*.json")):
        try:
            doc = load_mlkit_ocr_document(p)
            results[doc.document_id] = doc
        except Exception as exc:
            if fail_fast:
                raise ValueError(f"Failed to ingest {p.name}: {exc}") from exc
    return results


# ==============================================================================
# 3. Instruction Decomposition Engine (32 Clinical Patterns)
# ==============================================================================

# Exact mapping for the 32 verified canonical patterns
CANONICAL_32_DECOMPOSITION_RULES: dict[str, dict[str, str | None]] = {
    "Ngày uống 1 viên sáng": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày sáng",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sáng",
        "duration_raw": None,
    },
    "Ngày uống 1 viên buổi sáng": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày buổi sáng",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "buổi sáng",
        "duration_raw": None,
    },
    "Ngày uống 1 viên sau ăn": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sau ăn",
        "duration_raw": None,
    },
    "Ngày uống 1 viên tối": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày tối",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "tối",
        "duration_raw": None,
    },
    "Nhỏ mắt khi khô, 3-4 lần/ngày": {
        "dosage_raw": None,
        "frequency_raw": "3-4 lần/ngày",
        "route_raw": "Nhỏ mắt",
        "form_raw": None,
        "instruction_raw": "khi khô",
        "duration_raw": None,
    },
    "Ngày uống 2 viên (sáng, tối)": {
        "dosage_raw": "2 viên",
        "frequency_raw": "Ngày (sáng, tối)",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sáng, tối",
        "duration_raw": None,
    },
    "Ngày uống 1 viên buổi tối": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày buổi tối",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "buổi tối",
        "duration_raw": None,
    },
    "Ngày uống 1 viên sau ăn trưa": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày trưa",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sau ăn trưa",
        "duration_raw": None,
    },
    "Uống 1 viên buổi sáng": {
        "dosage_raw": "1 viên",
        "frequency_raw": "buổi sáng",
        "route_raw": "Uống",
        "form_raw": "viên",
        "instruction_raw": "buổi sáng",
        "duration_raw": None,
    },
    "Ngày uống 2 lần, mỗi lần 1 viên": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày 2 lần",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "mỗi lần 1 viên",
        "duration_raw": None,
    },
    "Ngày uống 1 viên buổi sáng trước ăn": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày buổi sáng",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "trước ăn",
        "duration_raw": None,
    },
    "Ngày uống 2 viên sau ăn": {
        "dosage_raw": "2 viên",
        "frequency_raw": "Ngày",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sau ăn",
        "duration_raw": None,
    },
    "Ngày uống 2 viên sau ăn tối": {
        "dosage_raw": "2 viên",
        "frequency_raw": "Ngày tối",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sau ăn tối",
        "duration_raw": None,
    },
    "Ngày uống 1 viên trước ăn sáng 30 phút": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày sáng",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "trước ăn sáng 30 phút",
        "duration_raw": None,
    },
    "Ngày uống 1 viên sau ăn no (khi đau)": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sau ăn no (khi đau)",
        "duration_raw": None,
    },
    "Ngày uống 2 lần, mỗi lần 1 viên sau ăn": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày 2 lần",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sau ăn",
        "duration_raw": None,
    },
    "Ngày uống 1 viên buổi tối (khi ngứa mũi)": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày buổi tối",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "khi ngứa mũi",
        "duration_raw": None,
    },
    "Uống 1 viên khi đau đầu, cách mỗi 4 - 6 giờ": {
        "dosage_raw": "1 viên",
        "frequency_raw": "cách mỗi 4 - 6 giờ",
        "route_raw": "Uống",
        "form_raw": "viên",
        "instruction_raw": "khi đau đầu",
        "duration_raw": None,
    },
    "Sáng uống 1 ống sau ăn": {
        "dosage_raw": "1 ống",
        "frequency_raw": "Sáng",
        "route_raw": "uống",
        "form_raw": "ống",
        "instruction_raw": "sau ăn",
        "duration_raw": None,
    },
    "Sáng uống 1 viên (hòa tan trong nước)": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Sáng",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "hòa tan trong nước",
        "duration_raw": None,
    },
    "Trưa uống 1 viên sau ăn": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Trưa",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sau ăn",
        "duration_raw": None,
    },
    "Nhỏ mắt khi mỏi, khô": {
        "dosage_raw": None,
        "frequency_raw": None,
        "route_raw": "Nhỏ mắt",
        "form_raw": None,
        "instruction_raw": "khi mỏi, khô",
        "duration_raw": None,
    },
    "Ngày uống 1-2 viên sau ăn tối": {
        "dosage_raw": "1-2 viên",
        "frequency_raw": "Ngày tối",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sau ăn tối",
        "duration_raw": None,
    },
    "Tiêm dưới da 10 đơn vị buổi tối": {
        "dosage_raw": "10 đơn vị",
        "frequency_raw": "buổi tối",
        "route_raw": "Tiêm dưới da",
        "form_raw": "đơn vị",
        "instruction_raw": "buổi tối",
        "duration_raw": None,
    },
    "Ngày uống 3 viên sau ăn": {
        "dosage_raw": "3 viên",
        "frequency_raw": "Ngày",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sau ăn",
        "duration_raw": None,
    },
    "Ngày uống 1/2 viên tối": {
        "dosage_raw": "1/2 viên",
        "frequency_raw": "Ngày tối",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "tối",
        "duration_raw": None,
    },
    "Ngày uống 2 viên trước ăn": {
        "dosage_raw": "2 viên",
        "frequency_raw": "Ngày",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "trước ăn",
        "duration_raw": None,
    },
    "Bôi vùng nấm 2 lần/ngày": {
        "dosage_raw": None,
        "frequency_raw": "2 lần/ngày",
        "route_raw": "Bôi",
        "form_raw": None,
        "instruction_raw": "vùng nấm",
        "duration_raw": None,
    },
    "Uống 1 viên khi đau/sốt, cách mỗi 4-6h": {
        "dosage_raw": "1 viên",
        "frequency_raw": "cách mỗi 4-6h",
        "route_raw": "Uống",
        "form_raw": "viên",
        "instruction_raw": "khi đau/sốt",
        "duration_raw": None,
    },
    "Bôi vùng đau 2 lần/ngày": {
        "dosage_raw": None,
        "frequency_raw": "2 lần/ngày",
        "route_raw": "Bôi",
        "form_raw": None,
        "instruction_raw": "vùng đau",
        "duration_raw": None,
    },
    "Ngày uống 1 viên sau ăn no": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "sau ăn no",
        "duration_raw": None,
    },
    "Ngày uống 1-2 viên trước khi ngủ": {
        "dosage_raw": "1-2 viên",
        "frequency_raw": "Ngày",
        "route_raw": "uống",
        "form_raw": "viên",
        "instruction_raw": "trước khi ngủ",
        "duration_raw": None,
    },
}


def decompose_instruction(instruction_raw: str | None) -> dict[str, str | None]:
    """Decompose composite Vietnamese prescription instruction into atomic fields."""
    if not instruction_raw or not instruction_raw.strip():
        return {
            "dosage_raw": None,
            "frequency_raw": None,
            "duration_raw": None,
            "route_raw": None,
            "instruction_raw": None,
            "form_raw": None,
        }

    raw = instruction_raw.strip()

    # Exact table match first
    if raw in CANONICAL_32_DECOMPOSITION_RULES:
        return dict(CANONICAL_32_DECOMPOSITION_RULES[raw])

    # Rule-based fallback decomposition
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    route: str | None = None
    form: str | None = None
    residual: str | None = None

    # Route extraction
    route_match = re.search(
        r"\b(uống|Uống|Nhỏ mắt|nhỏ mắt|Bôi|bôi|Tiêm dưới da|tiêm dưới da|Xịt|xịt)\b",
        raw,
    )
    if route_match:
        route = route_match.group(1)

    # Dosage extraction (e.g. "1 viên", "1/2 viên", "1-2 viên", "10 đơn vị", "1 ống")
    dosage_match = re.search(
        r"(\d+(?:[/-]\d+)?\s*(?:viên|ống|gói|giọt|đơn vị|ml|nhát))", raw, re.IGNORECASE
    )
    if dosage_match:
        dosage = dosage_match.group(1).strip()
        # Form extraction from dosage unit
        form_word = dosage.split()[-1].lower()
        form = form_word

    # Frequency extraction
    freq_pat = (
        r"(\d+-\d+\s*lần/ngày|\d+\s*lần/ngày|cách mỗi\s*[\d\s-]+(?:h|giờ)|"
        r"ngày\s*(?:buổi\s*)?(?:sáng|trưa|chiều|tối)?|buổi\s*(?:sáng|trưa|tối)|"
        r"sáng|trưa|tối)"
    )
    freq_match = re.search(freq_pat, raw, re.IGNORECASE)
    if freq_match:
        frequency = freq_match.group(1).strip()

    # Duration extraction
    dur_match = re.search(r"(\d+\s*(?:ngày|tuần|tháng))", raw, re.IGNORECASE)
    if dur_match:
        duration = dur_match.group(1).strip()

    # Residual instruction
    residual = raw
    for component in [dosage, route, frequency, duration]:
        if component:
            residual = residual.replace(component, "")
    residual = re.sub(r"[,;()]", " ", residual)
    residual = re.sub(r"\s+", " ", residual).strip()
    if not residual:
        residual = None

    return {
        "dosage_raw": dosage,
        "frequency_raw": frequency,
        "duration_raw": duration,
        "route_raw": route,
        "instruction_raw": residual or raw,
        "form_raw": form,
    }


def decompose_medication(med: CanonicalMedication) -> CanonicalMedication:
    """Update CanonicalMedication instance with decomposed atomic fields."""
    decomp = decompose_instruction(med.instruction_raw)
    data = med.model_dump()
    for k, v in decomp.items():
        if v is not None and not data.get(k):
            data[k] = v
    return CanonicalMedication.model_validate(data)


def decompose_prescription(gt: CanonicalPrescriptionGT) -> CanonicalPrescriptionGT:
    """Update all CanonicalMedication records within a prescription GT."""
    data = gt.model_dump()
    data["medications"] = [
        decompose_medication(CanonicalMedication.model_validate(m)).model_dump()
        for m in data["medications"]
    ]
    return CanonicalPrescriptionGT.model_validate(data)


def validate_canonical_gt(prescription: CanonicalPrescriptionGT) -> bool:
    """Verify schema, ID uniqueness, and medication record integrity."""
    med_ids = [m.medication_id for m in prescription.medications]
    if len(med_ids) != len(set(med_ids)):
        return False
    if not prescription.prescription_id or not prescription.patient_id:
        return False
    return True


def validate_all_canonical_gt(
    gt_dir: Path | str = "data/canonical_ground_truth",
) -> dict[str, Any]:
    src = Path(gt_dir)
    if not src.exists() or not src.is_dir():
        return {
            "total_files": 0,
            "valid_files": 0,
            "invalid_files": 0,
            "total_medications": 0,
            "decomposed_medications": 0,
            "prescriptions_by_status": {"verified": 0, "draft": 0, "empty": 0},
            "errors": [f"Directory {gt_dir} does not exist"],
        }

    total = 0
    valid = 0
    invalid = 0
    total_meds = 0
    decomp_meds = 0
    status_counts = Counter()
    errors = []

    for p in sorted(src.glob("*.json")):
        total += 1
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            gt = CanonicalPrescriptionGT.model_validate(data)
            if validate_canonical_gt(gt):
                valid += 1
                status_counts[gt.annotation_status] += 1
                total_meds += len(gt.medications)
                for m in gt.medications:
                    if m.dosage_raw or m.frequency_raw or m.route_raw:
                        decomp_meds += 1
            else:
                invalid += 1
                errors.append(f"{p.name}: failed semantic validation")
        except Exception as exc:
            invalid += 1
            errors.append(f"{p.name}: {exc}")

    return {
        "total_files": total,
        "valid_files": valid,
        "invalid_files": invalid,
        "total_medications": total_meds,
        "decomposed_medications": decomp_meds,
        "prescriptions_by_status": dict(status_counts),
        "errors": errors,
    }


# ==============================================================================
# 4. Fuzzy Alignment Engine & Observation Auditing
# ==============================================================================


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
    # Character intersection overlap
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

    # Sort medications
    for med in prescription.medications:
        drug_target = med.drug_raw
        if not drug_target:
            continue

        clean_drug_target = drug_target
        if med.strength_raw and med.strength_raw.lower() in clean_drug_target.lower():
            clean_drug_target = re.sub(re.escape(med.strength_raw), "", clean_drug_target, flags=re.IGNORECASE).strip()
        if not clean_drug_target:
            clean_drug_target = med.brand_raw or drug_target

        # Search drug anchor in raw text
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

        # Proximity attribute matching if drug anchor found
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
                # Search within proximity (+/- 250 chars) of drug anchor
                search_window_start = max(0, d_start - 250)
                search_window_end = min(len(raw_text), d_end + 250)
                window_text = raw_text[search_window_start:search_window_end]

                attr_idx_in_window = window_text.lower().find(target_str.lower())
                if attr_idx_in_window != -1:
                    a_start = search_window_start + attr_idx_in_window
                    a_end = a_start + len(target_str)
                    actual_attr_text = raw_text[a_start:a_end]

                    # Non-overlapping check with existing entities
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

    # Sort entities by start offset
    entities.sort(key=lambda e: (e.start, e.end))
    annotation_doc = AnnotationDocumentV2(
        document_id=ocr_doc.document_id,
        prescription_id=prescription.prescription_id,
        patient_id=prescription.patient_id,
        image_id=ocr_doc.document_id,
        raw_text=raw_text,
        entities=entities,
        relations=relations,
    )
    return annotation_doc, records


def generate_alignment_audit_report(
    records: list[AlignmentRecord],
    output_json_path: Path | str | None = None,
    output_csv_path: Path | str | None = None,
) -> dict[str, Any]:
    """Generate structured observation audit matrix from alignment records."""
    total = len(records)
    status_counts = Counter(r.status.value for r in records)

    matched = status_counts[MatchStatus.MATCHED.value]
    ambiguous = status_counts[MatchStatus.AMBIGUOUS.value]
    unresolved = status_counts[MatchStatus.UNRESOLVED.value]

    by_rx = defaultdict(
        lambda: {"total": 0, "matched": 0, "ambiguous": 0, "unresolved": 0}
    )
    for r in records:
        by_rx[r.prescription_id]["total"] += 1
        by_rx[r.prescription_id][r.status.value.lower()] += 1

    by_type = defaultdict(
        lambda: {"total": 0, "matched": 0, "ambiguous": 0, "unresolved": 0}
    )
    for r in records:
        by_type[r.entity_type.value]["total"] += 1
        by_type[r.entity_type.value][r.status.value.lower()] += 1

    report = {
        "summary": {
            "total_records": total,
            "matched_count": matched,
            "matched_pct": round(matched / total * 100, 2) if total else 0.0,
            "ambiguous_count": ambiguous,
            "ambiguous_pct": round(ambiguous / total * 100, 2) if total else 0.0,
            "unresolved_count": unresolved,
            "unresolved_pct": round(unresolved / total * 100, 2) if total else 0.0,
        },
        "by_prescription": dict(by_rx),
        "by_entity_type": dict(by_type),
        "records": [
            {
                "prescription_id": r.prescription_id,
                "document_id": r.document_id,
                "medication_id": r.medication_id,
                "entity_type": r.entity_type.value,
                "canonical_text": r.canonical_text,
                "matched_text": r.matched_text,
                "start": r.start,
                "end": r.end,
                "confidence": r.confidence,
                "source_region_ids": r.source_region_ids,
                "status": r.status.value,
            }
            for r in records
        ],
    }

    if output_json_path:
        out_p = Path(output_json_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with out_p.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    if output_csv_path:
        csv_p = Path(output_csv_path)
        csv_p.parent.mkdir(parents=True, exist_ok=True)
        with csv_p.open("w", encoding="utf-8") as f:
            f.write(
                "prescription_id,document_id,medication_id,entity_type,"
                "canonical_text,matched_text,start,end,confidence,status\n"
            )
            for r in records:
                m_txt = r.matched_text or ""
                s_val = r.start if r.start is not None else ""
                e_val = r.end if r.end is not None else ""
                c_val = r.confidence if r.confidence is not None else ""
                f.write(
                    f'{r.prescription_id},{r.document_id},{r.medication_id},'
                    f'{r.entity_type.value},"{r.canonical_text}","{m_txt}",'
                    f'{s_val},{e_val},{c_val},{r.status.value}\n'
                )

    return report


# ==============================================================================
# 5. Fast Tokenizer Mock & PhoBERT Flat BIO Exporter
# ==============================================================================


class MockFastTokenizer:
    """Mock HuggingFace FastTokenizer with offset_mapping support."""

    def __init__(self) -> None:
        self.is_fast = True

    def __call__(
        self, text: str, return_offsets_mapping: bool = True, **kwargs: Any
    ) -> dict[str, Any]:
        if not return_offsets_mapping:
            raise ValueError("MockFastTokenizer requires return_offsets_mapping=True")

        words = []
        offsets = [(0, 0)]  # [CLS] token
        input_ids = [1]  # <s> / [CLS]

        cursor = 0
        tokens_raw = re.findall(r"\S+|\n", text)

        for tok in tokens_raw:
            pos = text.find(tok, cursor)
            if pos != -1:
                start = pos
                end = pos + len(tok)
                offsets.append((start, end))
                input_ids.append(100 + len(words))
                words.append(tok)
                cursor = end

        offsets.append((0, 0))  # [SEP] token
        input_ids.append(2)  # </s> / [SEP]

        return {
            "input_ids": input_ids,
            "attention_mask": [1] * len(input_ids),
            "offset_mapping": offsets,
        }


# ==============================================================================
# 6. Dataset Generator & Split Verification
# ==============================================================================


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


# ==============================================================================
# 7. Prescription-Balanced Samplers
# ==============================================================================


class PrescriptionWeightedRandomSampler:
    """Prescription-balanced weighted random sampler (w_i = 1 / N_{p(i)})."""

    def __init__(
        self,
        documents: list[AnnotationDocumentV2],
        num_samples: int | None = None,
        seed: int = 42,
    ) -> None:
        if not documents:
            raise ValueError("documents list must not be empty")
        self.documents = documents
        self.prescription_counts = Counter(d.prescription_id for d in documents)
        self.weights = [
            1.0 / self.prescription_counts[d.prescription_id] for d in documents
        ]
        self.num_samples = num_samples if num_samples is not None else len(documents)
        self.rng = random.Random(seed)

    def sample_indices(self) -> list[int]:
        if self.num_samples == 0:
            return []
        indices = list(range(len(self.documents)))
        return self.rng.choices(indices, weights=self.weights, k=self.num_samples)


# ==============================================================================
# 8. Multi-Metric Structured Evaluation Suite
# ==============================================================================


@dataclass(frozen=True)
class PrfScore:
    precision: float
    recall: float
    f1: float
    true_positive: int
    predicted: int
    gold: int


@dataclass(frozen=True)
class EntityEvaluation:
    overall: PrfScore
    macro: PrfScore
    per_class: dict[EntityType, PrfScore]


@dataclass(frozen=True)
class RelationEvaluation:
    parent_accuracy: float
    relation_micro: PrfScore
    relation_macro: PrfScore
    per_type: dict[RelationType, PrfScore]


@dataclass(frozen=True)
class RecordEvaluation:
    record_exact_match: float
    record_tuple_prf: PrfScore
    document_exact_match: float
    total_gold_records: int
    total_predicted_records: int
    exact_matched_records: int


@dataclass(frozen=True)
class StructuredEvaluationReport:
    entity_micro: PrfScore
    entity_macro: PrfScore
    entity_per_class: dict[EntityType, PrfScore]
    parent_accuracy: float
    relation_micro: PrfScore
    relation_macro: PrfScore
    relation_per_type: dict[RelationType, PrfScore]
    record_exact_match: float
    record_tuple_prf: PrfScore
    document_exact_match: float
    prescription_macro_summary: dict[str, float]
    prescription_breakdown: dict[str, dict[str, float]]


def _calc_prf(tp: int, pred: int, gold: int) -> PrfScore:
    precision = tp / pred if pred else (1.0 if not gold else 0.0)
    recall = tp / gold if gold else (1.0 if not pred else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PrfScore(precision, recall, f1, tp, pred, gold)


def evaluate_strict_entities(
    gold_entities: list[GoldEntityV2] | list[Entity],
    pred_entities: list[GoldEntityV2] | list[Entity],
) -> EntityEvaluation:
    gold_keys = {(e.type, e.start, e.end) for e in gold_entities}
    pred_keys = {(e.type, e.start, e.end) for e in pred_entities}

    overall_tp = len(gold_keys & pred_keys)
    overall_prf = _calc_prf(overall_tp, len(pred_keys), len(gold_keys))

    per_class: dict[EntityType, PrfScore] = {}
    f1_list: list[float] = []

    for ent_type in EntityType:
        g_c = {k for k in gold_keys if k[0] == ent_type}
        p_c = {k for k in pred_keys if k[0] == ent_type}
        score = _calc_prf(len(g_c & p_c), len(p_c), len(g_c))
        per_class[ent_type] = score
        f1_list.append(score.f1)

    macro_f1 = sum(f1_list) / len(f1_list)
    macro_p = sum(s.precision for s in per_class.values()) / len(per_class)
    macro_r = sum(s.recall for s in per_class.values()) / len(per_class)
    macro_prf = PrfScore(
        macro_p, macro_r, macro_f1, overall_tp, len(pred_keys), len(gold_keys)
    )

    return EntityEvaluation(overall=overall_prf, macro=macro_prf, per_class=per_class)


def evaluate_relations(
    gold_doc: AnnotationDocumentV2,
    pred_doc: AnnotationDocumentV2,
) -> RelationEvaluation:
    gold_map = {e.entity_id: e for e in gold_doc.entities}
    pred_map = {e.entity_id: e for e in pred_doc.entities}

    # Gold attributes (non-drug)
    gold_attrs = [e for e in gold_doc.entities if e.type != EntityType.DRUG]
    correct_parent_count = 0

    for ga in gold_attrs:
        # Find matching pred entity
        matching_pred = next(
            (
                pe
                for pe in pred_doc.entities
                if pe.type == ga.type and pe.start == ga.start and pe.end == ga.end
            ),
            None,
        )
        if matching_pred is not None:
            # Check parent match
            gold_parent_span = None
            if ga.parent_entity_id and ga.parent_entity_id in gold_map:
                gp = gold_map[ga.parent_entity_id]
                gold_parent_span = (gp.type, gp.start, gp.end)

            pred_parent_span = None
            if (
                matching_pred.parent_entity_id
                and matching_pred.parent_entity_id in pred_map
            ):
                pp = pred_map[matching_pred.parent_entity_id]
                pred_parent_span = (pp.type, pp.start, pp.end)

            if gold_parent_span == pred_parent_span:
                correct_parent_count += 1

    parent_accuracy = correct_parent_count / len(gold_attrs) if gold_attrs else 1.0

    # Relation triples: ((h_type, h_start, h_end), (t_type, t_start, t_end), rel_type)
    def extract_triples(doc: AnnotationDocumentV2) -> set[tuple]:
        emap = {e.entity_id: e for e in doc.entities}
        triples = set()
        for r in doc.relations:
            if r.head_entity_id in emap and r.tail_entity_id in emap:
                h = emap[r.head_entity_id]
                t = emap[r.tail_entity_id]
                triples.add(
                    (
                        (h.type, h.start, h.end),
                        (t.type, t.start, t.end),
                        r.relation_type,
                    )
                )
        return triples

    gold_triples = extract_triples(gold_doc)
    pred_triples = extract_triples(pred_doc)

    tp = len(gold_triples & pred_triples)
    micro_prf = _calc_prf(tp, len(pred_triples), len(gold_triples))

    per_type: dict[RelationType, PrfScore] = {}
    f1_list: list[float] = []

    for r_type in RelationType:
        gt_c = {t for t in gold_triples if t[2] == r_type}
        pt_c = {t for t in pred_triples if t[2] == r_type}
        score = _calc_prf(len(gt_c & pt_c), len(pt_c), len(gt_c))
        per_type[r_type] = score
        f1_list.append(score.f1)

    macro_prf = PrfScore(
        precision=sum(s.precision for s in per_type.values()) / len(per_type),
        recall=sum(s.recall for s in per_type.values()) / len(per_type),
        f1=sum(f1_list) / len(f1_list),
        true_positive=tp,
        predicted=len(pred_triples),
        gold=len(gold_triples),
    )

    return RelationEvaluation(
        parent_accuracy=parent_accuracy,
        relation_micro=micro_prf,
        relation_macro=macro_prf,
        per_type=per_type,
    )


def evaluate_records(
    gold_docs: list[AnnotationDocumentV2],
    pred_docs: list[AnnotationDocumentV2],
) -> RecordEvaluation:
    total_gold_records = 0
    total_pred_records = 0
    exact_matched_records = 0
    doc_em_count = 0

    gold_tuples_all: set[tuple] = set()
    pred_tuples_all: set[tuple] = set()

    for g_doc, p_doc in zip(gold_docs, pred_docs, strict=False):
        # Extract records from gold
        g_drugs = [e for e in g_doc.entities if e.type == EntityType.DRUG]
        p_drugs = [e for e in p_doc.entities if e.type == EntityType.DRUG]

        total_gold_records += len(g_drugs)
        total_pred_records += len(p_drugs)

        g_records: list[tuple[tuple, frozenset[tuple]]] = []
        for gd in g_drugs:
            attrs = frozenset(
                (e.type, e.start, e.end)
                for e in g_doc.entities
                if e.parent_entity_id == gd.entity_id
            )
            g_records.append(((gd.type, gd.start, gd.end), attrs))
            for a in attrs:
                gold_tuples_all.add(
                    ((g_doc.document_id, (gd.type, gd.start, gd.end)), a)
                )

        p_records: list[tuple[tuple, frozenset[tuple]]] = []
        for pd in p_drugs:
            attrs = frozenset(
                (e.type, e.start, e.end)
                for e in p_doc.entities
                if e.parent_entity_id == pd.entity_id
            )
            p_records.append(((pd.type, pd.start, pd.end), attrs))
            for a in attrs:
                pred_tuples_all.add(
                    ((p_doc.document_id, (pd.type, pd.start, pd.end)), a)
                )

        matched_in_doc = 0
        for gr in g_records:
            if gr in p_records:
                exact_matched_records += 1
                matched_in_doc += 1

        if (
            len(g_records) > 0
            and matched_in_doc == len(g_records)
            and len(p_records) == len(g_records)
        ):
            doc_em_count += 1
        elif len(g_records) == 0 and len(p_records) == 0:
            doc_em_count += 1

    record_em = (
        exact_matched_records / total_gold_records if total_gold_records else 1.0
    )
    doc_em = doc_em_count / len(gold_docs) if gold_docs else 1.0

    tuple_tp = len(gold_tuples_all & pred_tuples_all)
    tuple_prf = _calc_prf(tuple_tp, len(pred_tuples_all), len(gold_tuples_all))

    return RecordEvaluation(
        record_exact_match=record_em,
        record_tuple_prf=tuple_prf,
        document_exact_match=doc_em,
        total_gold_records=total_gold_records,
        total_predicted_records=total_pred_records,
        exact_matched_records=exact_matched_records,
    )


def evaluate_dual_level(
    gold_docs: list[AnnotationDocumentV2],
    pred_docs: list[AnnotationDocumentV2],
) -> StructuredEvaluationReport:
    # 1. Pool all entities across documents for Capture-Level Micro
    all_gold_ents = [e for d in gold_docs for e in d.entities]
    all_pred_ents = [e for d in pred_docs for e in d.entities]
    entity_eval = evaluate_strict_entities(all_gold_ents, all_pred_ents)

    # 2. Record eval
    record_eval = evaluate_records(gold_docs, pred_docs)

    # 3. Overall relation eval
    all_parent_accs = []
    for g, p in zip(gold_docs, pred_docs, strict=False):
        r_eval = evaluate_relations(g, p)
        all_parent_accs.append(r_eval.parent_accuracy)

    mean_parent_acc = (
        sum(all_parent_accs) / len(all_parent_accs) if all_parent_accs else 1.0
    )

    # 4. Prescription-level breakdown & Macro aggregation
    by_rx_gold: dict[str, list[AnnotationDocumentV2]] = defaultdict(list)
    by_rx_pred: dict[str, list[AnnotationDocumentV2]] = defaultdict(list)

    for g, p in zip(gold_docs, pred_docs, strict=False):
        rx_id = g.prescription_id or "RX_UNKNOWN"
        by_rx_gold[rx_id].append(g)
        by_rx_pred[rx_id].append(p)

    rx_breakdown: dict[str, dict[str, float]] = {}
    rx_f1s = []
    rx_ems = []

    for rx_id, g_sub in by_rx_gold.items():
        p_sub = by_rx_pred[rx_id]
        g_sub_ents = [e for d in g_sub for e in d.entities]
        p_sub_ents = [e for d in p_sub for e in d.entities]
        sub_ent_eval = evaluate_strict_entities(g_sub_ents, p_sub_ents)
        sub_rec_eval = evaluate_records(g_sub, p_sub)

        rx_breakdown[rx_id] = {
            "entity_micro_f1": sub_ent_eval.overall.f1,
            "entity_macro_f1": sub_ent_eval.macro.f1,
            "record_exact_match": sub_rec_eval.record_exact_match,
            "document_exact_match": sub_rec_eval.document_exact_match,
        }
        rx_f1s.append(sub_ent_eval.overall.f1)
        rx_ems.append(sub_rec_eval.record_exact_match)

    macro_summary = {
        "prescription_macro_entity_f1": sum(rx_f1s) / len(rx_f1s) if rx_f1s else 0.0,
        "prescription_macro_record_em": sum(rx_ems) / len(rx_ems) if rx_ems else 0.0,
    }

    dummy_rel_eval = (
        evaluate_relations(gold_docs[0], pred_docs[0]) if gold_docs else None
    )
    rel_micro = (
        dummy_rel_eval.relation_micro
        if dummy_rel_eval
        else PrfScore(1.0, 1.0, 1.0, 0, 0, 0)
    )
    rel_macro = (
        dummy_rel_eval.relation_macro
        if dummy_rel_eval
        else PrfScore(1.0, 1.0, 1.0, 0, 0, 0)
    )
    per_type = dummy_rel_eval.per_type if dummy_rel_eval else {}

    return StructuredEvaluationReport(
        entity_micro=entity_eval.overall,
        entity_macro=entity_eval.macro,
        entity_per_class=entity_eval.per_class,
        parent_accuracy=mean_parent_acc,
        relation_micro=rel_micro,
        relation_macro=rel_macro,
        relation_per_type=per_type,
        record_exact_match=record_eval.record_exact_match,
        record_tuple_prf=record_eval.record_tuple_prf,
        document_exact_match=record_eval.document_exact_match,
        prescription_macro_summary=macro_summary,
        prescription_breakdown=rx_breakdown,
    )


# ==============================================================================
# 9. Pytest Fixtures
# ==============================================================================


@pytest.fixture
def synthetic_mlkit_builder():
    """Factory fixture to build valid ML Kit raw JSON payloads."""

    def _builder(
        doc_id: str = "RX_001_IMG01",
        width: int = 1000,
        height: int = 1000,
        lines: list[tuple[str, list[float] | None, float | None]] | None = None,
    ) -> dict[str, Any]:
        if lines is None:
            lines = [
                ("BỆNH VIỆN ĐA KHOA CẦN THƠ", [50, 50, 450, 80], 0.98),
                ("ĐƠN THUỐC", [200, 100, 350, 130], 0.99),
                ("1. Losartan 50mg", [100, 200, 350, 230], 0.96),
                ("Số lượng: 28 Viên", [400, 200, 600, 230], 0.95),
                ("Ngày uống 1 viên buổi sáng", [100, 240, 500, 270], 0.94),
            ]

        raw_lines = []
        for text, box, conf in lines:
            if box is not None:
                left_c, top_c, right_c, bottom_c = box
                corner_pts = [
                    {"x": left_c, "y": top_c},
                    {"x": right_c, "y": top_c},
                    {"x": right_c, "y": bottom_c},
                    {"x": left_c, "y": bottom_c},
                ]
                bbox_dict = {
                    "left": left_c,
                    "top": top_c,
                    "right": right_c,
                    "bottom": bottom_c,
                }
            else:
                corner_pts = None
                bbox_dict = {}

            raw_lines.append(
                {
                    "text": text,
                    "confidence": conf,
                    "cornerPoints": corner_pts,
                    "boundingBox": bbox_dict,
                }
            )

        return {
            "documentId": doc_id,
            "imageWidth": width,
            "imageHeight": height,
            "ocrEngine": {"name": "google_mlkit_text_recognition", "version": "0.15.1"},
            "blocks": [{"lines": raw_lines}],
        }

    return _builder


@pytest.fixture
def sample_mlkit_raw_json(synthetic_mlkit_builder):
    return synthetic_mlkit_builder()


@pytest.fixture
def sample_canonical_prescription_gt() -> CanonicalPrescriptionGT:
    return CanonicalPrescriptionGT(
        prescription_id="RX_001",
        patient_id="PAT_001",
        hospital_name="BỆNH VIỆN ĐA KHOA CẦN THƠ",
        prescription_date="2026-01-15",
        annotation_status="verified",
        verified_by="expert_physician_1",
        verified_at="2026-01-16T10:00:00Z",
        medications=[
            CanonicalMedication(
                medication_id="RX_001_M01",
                drug_raw="Losartan",
                drug_normalized="losartan",
                brand_raw="Cozaar",
                brand_normalized="cozaar",
                strength_raw="50mg",
                strength_normalized="50 mg",
                quantity_value_raw="28",
                quantity_value_normalized=28,
                quantity_unit_raw="Viên",
                quantity_unit_normalized="viên",
                dosage_raw="1 viên",
                frequency_raw="Ngày buổi sáng",
                route_raw="uống",
                instruction_raw="buổi sáng",
                form_raw="viên",
            ),
            CanonicalMedication(
                medication_id="RX_001_M02",
                drug_raw="Nexium",
                drug_normalized="esomeprazole",
                strength_raw="40mg",
                strength_normalized="40 mg",
                quantity_value_raw="14",
                quantity_value_normalized=14,
                quantity_unit_raw="Viên",
                quantity_unit_normalized="viên",
                dosage_raw="1 viên",
                frequency_raw="Ngày sáng",
                route_raw="uống",
                instruction_raw="trước ăn sáng 30 phút",
                form_raw="viên",
            ),
        ],
    )


@pytest.fixture
def sample_annotation_document_v2() -> AnnotationDocumentV2:
    raw_text = "Losartan 50mg Số lượng: 28 Viên\nNgày uống 1 viên buổi sáng"
    d_start = raw_text.find("Losartan")
    d_end = d_start + len("Losartan")

    s_start = raw_text.find("50mg")
    s_end = s_start + len("50mg")

    q_start = raw_text.find("28 Viên")
    q_end = q_start + len("28 Viên")

    dos_start = raw_text.find("1 viên")
    dos_end = dos_start + len("1 viên")

    e_drug = GoldEntityV2(
        entity_id="e1",
        type=EntityType.DRUG,
        text="Losartan",
        start=d_start,
        end=d_end,
        medication_id="RX_001_M01",
        parent_entity_id=None,
    )
    e_str = GoldEntityV2(
        entity_id="e2",
        type=EntityType.STRENGTH,
        text="50mg",
        start=s_start,
        end=s_end,
        medication_id="RX_001_M01",
        parent_entity_id="e1",
    )
    e_qty = GoldEntityV2(
        entity_id="e3",
        type=EntityType.QUANTITY,
        text="28 Viên",
        start=q_start,
        end=q_end,
        medication_id="RX_001_M01",
        parent_entity_id="e1",
    )
    e_dos = GoldEntityV2(
        entity_id="e4",
        type=EntityType.DOSAGE,
        text="1 viên",
        start=dos_start,
        end=dos_end,
        medication_id="RX_001_M01",
        parent_entity_id="e1",
    )

    relations = [
        EntityRelation(
            head_entity_id="e1",
            tail_entity_id="e2",
            relation_type=RelationType.HAS_STRENGTH,
        ),
        EntityRelation(
            head_entity_id="e1",
            tail_entity_id="e3",
            relation_type=RelationType.HAS_QUANTITY,
        ),
        EntityRelation(
            head_entity_id="e1",
            tail_entity_id="e4",
            relation_type=RelationType.HAS_DOSAGE,
        ),
    ]

    return AnnotationDocumentV2(
        document_id="RX_001_IMG01",
        prescription_id="RX_001",
        patient_id="PAT_001",
        image_id="RX_001_IMG01",
        raw_text=raw_text,
        entities=[e_drug, e_str, e_qty, e_dos],
        relations=relations,
    )


@pytest.fixture
def mock_fast_tokenizer() -> MockFastTokenizer:
    return MockFastTokenizer()


@pytest.fixture
def temp_test_dir(tmp_path: Path) -> Path:
    d = tmp_path / "rxie_e2e_test_env"
    d.mkdir(parents=True, exist_ok=True)
    return d
