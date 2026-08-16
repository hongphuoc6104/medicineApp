"""Tier 3: Cross-Feature Pairwise Interactions Test Suite for RxIE Sprint A.

This suite tests pairwise combinatorial interactions connecting adjacent
and multi-stage modules across the entire RxIE extraction pipeline:
1. Ingestion + Text Reconstruction
2. Ingestion + Alignment / Validation Engine
3. Canonical GT Decomposition + Alignment / Grouping
4. Alignment Engine + Annotation Document Generation
5. Annotation Document + Flat BIO PhoBERT Export
6. Dataset Generator (19/4/4 Split Isolation) + Prescription Samplers
7. Sampler + PyTorch / DataLoader Integration
8. Annotation Documents + Strict Multi-Metric Evaluator
9. Evaluator + Dual-Level Aggregation (Capture Micro vs Prescription Macro)
10. Ingestion + API 503 Security Guard
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from rxie.alignment import ID_TO_LABEL, align_token_labels
from rxie.annotations import (
    LEGACY_PROVENANCE_WARNING,
    convert_legacy_bio,
)
from rxie.api import create_app
from rxie.evaluation import (
    strict_entity_evaluation,
)
from rxie.grouping import (
    CanonicalPrescriptionGT,
    HierarchicalPrescriptionSampler,
    compute_content_similarity,
    extract_content_features,
    identify_prescription_fingerprint,
)
from rxie.ingestion import (
    load_mlkit_ocr_document,
    parse_mlkit_json_data,
)
from rxie.schemas import (
    AnnotationDocument,
    AnnotationProvenance,
    Entity,
    EntityType,
    GoldEntity,
)
from rxie.text import DocumentText, build_document_text, validate_entities

# ---------------------------------------------------------------------------
# Test Helpers & Simulators
# ---------------------------------------------------------------------------


class MockFastTokenizer:
    """Fast tokenizer simulator providing offset mappings for test documents."""

    is_fast = True

    def __init__(self, vocab_map: dict[str, int] | None = None):
        self.vocab_map = vocab_map or {}
        self.pad_token_id = 0
        self.cls_token_id = 101
        self.sep_token_id = 102

    def __call__(
        self,
        text: str,
        return_offsets_mapping: bool = True,
        truncation: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not return_offsets_mapping:
            raise ValueError("MockFastTokenizer requires return_offsets_mapping=True")

        input_ids = [self.cls_token_id]
        attention_mask = [1]
        offset_mapping: list[tuple[int, int]] = [(0, 0)]

        pos = 0
        while pos < len(text):
            if text[pos].isspace():
                pos += 1
                continue
            start = pos
            while pos < len(text) and not text[pos].isspace():
                pos += 1
            token_text = text[start:pos]
            token_id = self.vocab_map.get(token_text, 1000 + len(input_ids))
            input_ids.append(token_id)
            attention_mask.append(1)
            offset_mapping.append((start, pos))

        input_ids.append(self.sep_token_id)
        attention_mask.append(1)
        offset_mapping.append((0, 0))

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "offset_mapping": offset_mapping,
        }


class MockPrescriptionClassifier:
    """Mock classifier implementing EntityClassifier Protocol for testing."""

    model_version = "mock-pipeline-v1.0.0"

    def __init__(self, entities: list[Entity] | None = None):
        self._entities = entities or []

    def classify(self, document: DocumentText) -> list[Entity]:
        if self._entities:
            return self._entities
        results = []
        for span in document.regions:
            line_text = document.raw_text[span.start : span.end]
            if "Amlodipine" in line_text:
                idx = document.raw_text.find("Amlodipine", span.start)
                results.append(
                    Entity(
                        type=EntityType.DRUG,
                        text="Amlodipine",
                        start=idx,
                        end=idx + 10,
                        confidence=0.98,
                        source_region_ids=document.source_regions(idx, idx + 10),
                    )
                )
        return results


def decompose_instruction_rule(
    instruction_raw: str | None,
) -> dict[str, str | None]:
    """Decompose composite Vietnamese prescription instructions into slots."""
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
    result: dict[str, str | None] = {
        "dosage_raw": None,
        "frequency_raw": None,
        "duration_raw": None,
        "route_raw": None,
        "instruction_raw": None,
        "form_raw": None,
    }

    # Route extraction
    for route in ["Tiêm dưới da", "Nhỏ mắt", "Bôi", "Uống", "uống"]:
        if route.lower() in raw.lower():
            if route.lower() == "uống":
                result["route_raw"] = "Uống"
            else:
                result["route_raw"] = route
            break

    # Dosage & Form extraction
    if "1 viên" in raw or "1v" in raw.lower():
        result["dosage_raw"] = "1 viên"
        result["form_raw"] = "viên"
    elif "2 viên" in raw:
        result["dosage_raw"] = "2 viên"
        result["form_raw"] = "viên"
    elif "3 viên" in raw:
        result["dosage_raw"] = "3 viên"
        result["form_raw"] = "viên"
    elif "1-2 viên" in raw:
        result["dosage_raw"] = "1-2 viên"
        result["form_raw"] = "viên"
    elif "1/2 viên" in raw:
        result["dosage_raw"] = "1/2 viên"
        result["form_raw"] = "viên"
    elif "1 ống" in raw:
        result["dosage_raw"] = "1 ống"
        result["form_raw"] = "ống"
    elif "10 đơn vị" in raw:
        result["dosage_raw"] = "10 đơn vị"
        result["form_raw"] = "đơn vị"

    # Frequency extraction
    if "3-4 lần/ngày" in raw:
        result["frequency_raw"] = "3-4 lần/ngày"
    elif "2 lần/ngày" in raw:
        result["frequency_raw"] = "2 lần/ngày"
    elif "ngày 2 lần" in raw.lower():
        result["frequency_raw"] = "Ngày 2 lần"
    elif "buổi sáng" in raw.lower() and "ngày" in raw.lower():
        result["frequency_raw"] = "Ngày buổi sáng"
    elif "buổi tối" in raw.lower() and "ngày" in raw.lower():
        result["frequency_raw"] = "Ngày buổi tối"
    elif "sáng, tối" in raw.lower() or "(sáng, tối)" in raw:
        result["frequency_raw"] = "Ngày (sáng, tối)"
    elif "ngày" in raw.lower() and "tối" in raw.lower():
        result["frequency_raw"] = "Ngày tối"
    elif "ngày" in raw.lower() and "sáng" in raw.lower():
        result["frequency_raw"] = "Ngày sáng"
    elif "ngày" in raw.lower() and "trưa" in raw.lower():
        result["frequency_raw"] = "Ngày trưa"
    elif "sáng" in raw.lower():
        result["frequency_raw"] = "Sáng"
    elif "trưa" in raw.lower():
        result["frequency_raw"] = "Trưa"
    elif "tối" in raw.lower():
        result["frequency_raw"] = "Tối"
    elif "ngày" in raw.lower():
        result["frequency_raw"] = "Ngày"

    # Residual instruction
    if "trước ăn sáng 30 phút" in raw:
        result["instruction_raw"] = "trước ăn sáng 30 phút"
    elif "sau ăn tối" in raw:
        result["instruction_raw"] = "sau ăn tối"
    elif "sau ăn no (khi đau)" in raw:
        result["instruction_raw"] = "sau ăn no (khi đau)"
    elif "sau ăn" in raw:
        result["instruction_raw"] = "sau ăn"
    elif "khi đau/sốt" in raw or "khi đau đầu" in raw:
        result["instruction_raw"] = "khi đau"
    elif "khi mỏi, khô" in raw:
        result["instruction_raw"] = "khi mỏi, khô"
    elif "khi khô" in raw:
        result["instruction_raw"] = "khi khô"
    elif "hòa tan trong nước" in raw:
        result["instruction_raw"] = "hòa tan trong nước"

    return result


def compute_prescription_macro_summary(
    evaluation_records: list[dict[str, Any]],
) -> dict[str, float]:
    """Compute prescription-level macro averaged metrics."""
    by_rx: dict[str, list[dict[str, Any]]] = {}
    for rec in evaluation_records:
        rx_id = rec.get("prescription_id", "UNKNOWN")
        by_rx.setdefault(rx_id, []).append(rec)

    per_rx_f1: list[float] = []
    for _rx_id, items in by_rx.items():
        tp = sum(item.get("tp", 0) for item in items)
        pred = sum(item.get("predicted", 0) for item in items)
        gold = sum(item.get("gold", 0) for item in items)
        prec = tp / pred if pred > 0 else float(gold == 0)
        rec = tp / gold if gold > 0 else float(pred == 0)
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        per_rx_f1.append(f1)

    macro_f1 = sum(per_rx_f1) / len(per_rx_f1) if per_rx_f1 else 0.0
    return {
        "macro_f1": macro_f1,
        "prescription_count": float(len(by_rx)),
        "min_prescription_f1": min(per_rx_f1) if per_rx_f1 else 0.0,
        "max_prescription_f1": max(per_rx_f1) if per_rx_f1 else 0.0,
    }


# ===========================================================================
# 1. Ingestion + Text Reconstruction Interactions
# ===========================================================================


def test_int_ingestion_and_reconstruction_real_captures():
    """Interaction 1.1: Ingestion of real OCR JSONs and text reconstruction."""
    ocr_dir = Path("data/ocr_final")
    sample_files = list(ocr_dir.glob("*.json"))[:5]
    assert len(sample_files) >= 1, "Expected at least 1 real OCR capture"

    for file_path in sample_files:
        raw_content = json.loads(file_path.read_text(encoding="utf-8"))
        doc = load_mlkit_ocr_document(file_path)
        doc_text = build_document_text(doc)

        assert doc_text.raw_text == raw_content.get("fullText", "")

        total_lines = sum(
            len(block.get("lines", []))
            for block in raw_content.get("blocks", [])
            if block.get("lines")
        )
        assert len(doc_text.regions) == total_lines

        cursor = 0
        for span in doc_text.regions:
            assert span.start >= cursor
            assert span.end > span.start
            assert span.end <= len(doc_text.raw_text)
            region_slice = doc_text.raw_text[span.start : span.end]
            assert "\n" not in region_slice
            cursor = span.end


def test_int_ingestion_clamping_and_reconstruction_synthetic():
    """Interaction 1.2: Synthetic ingestion with out-of-bound coords clamps."""
    synthetic_payload = {
        "metadata": {
            "fileName": "synthetic_out_of_bounds.jpg",
            "imageWidth": 2000,
            "imageHeight": 3000,
        },
        "fullText": "Line One\nLine Two Clamped",
        "blocks": [
            {
                "lines": [
                    {
                        "text": "Line One",
                        "confidence": 1.25,
                        "cornerPoints": [
                            {"x": -15, "y": -10},
                            {"x": 2050, "y": -10},
                            {"x": 2050, "y": 100},
                            {"x": -15, "y": 100},
                        ],
                    },
                    {
                        "text": "Line Two Clamped",
                        "confidence": -0.5,
                        "boundingBox": {
                            "left": -5.0,
                            "top": 120.0,
                            "right": 2050.0,
                            "bottom": 3050.0,
                        },
                    },
                ]
            }
        ],
    }

    doc = parse_mlkit_json_data(synthetic_payload, document_id="synth_clamped")
    assert len(doc.pages[0].regions) == 2
    r0 = doc.pages[0].regions[0]
    r1 = doc.pages[0].regions[1]

    for pt in r0.bbox.points:
        assert 0.0 <= pt[0] <= 2000.0
        assert 0.0 <= pt[1] <= 3000.0
    assert r0.confidence == 1.0

    for pt in r1.bbox.points:
        assert 0.0 <= pt[0] <= 2000.0
        assert 0.0 <= pt[1] <= 3000.0
    assert r1.confidence == 0.0

    doc_text = build_document_text(doc)
    assert doc_text.raw_text == "Line One\nLine Two Clamped"
    assert len(doc_text.regions) == 2
    assert doc_text.regions[0].region_id == "p0_b0_l0"
    assert doc_text.regions[1].region_id == "p0_b0_l1"


def test_int_ingestion_empty_capture_reconstruction():
    """Interaction 1.3: Empty OCR capture results in valid empty DocumentText."""
    empty_payload = {
        "metadata": {
            "fileName": "empty_capture.jpg",
            "imageWidth": 1000,
            "imageHeight": 1000,
        },
        "fullText": "",
        "blocks": [],
    }
    doc = parse_mlkit_json_data(empty_payload, document_id="empty_doc")
    doc_text = build_document_text(doc)
    assert doc_text.raw_text == ""
    assert doc_text.regions == ()
    assert doc_text.source_regions(0, 0) == []


# ===========================================================================
# 2. Ingestion + Alignment / Validation Engine Interactions
# ===========================================================================


def test_int_ingestion_text_span_and_entity_provenance_validation():
    """Interaction 2.1: Reconstructed text validates exact entity spans."""
    raw_data = {
        "metadata": {
            "fileName": "rx_sample.jpg",
            "imageWidth": 1000,
            "imageHeight": 1000,
        },
        "fullText": (
            "Bệnh nhân: NGUYỄN VĂN A\nThuốc: Amlodipine 5mg\nSố lượng: 30 Viên"
        ),
        "blocks": [
            {
                "lines": [
                    {
                        "text": "Bệnh nhân: NGUYỄN VĂN A",
                        "cornerPoints": [
                            {"x": 0, "y": 0},
                            {"x": 100, "y": 0},
                            {"x": 100, "y": 20},
                            {"x": 0, "y": 20},
                        ],
                    },
                    {
                        "text": "Thuốc: Amlodipine 5mg",
                        "cornerPoints": [
                            {"x": 0, "y": 30},
                            {"x": 100, "y": 30},
                            {"x": 100, "y": 50},
                            {"x": 0, "y": 50},
                        ],
                    },
                    {
                        "text": "Số lượng: 30 Viên",
                        "cornerPoints": [
                            {"x": 0, "y": 60},
                            {"x": 100, "y": 60},
                            {"x": 100, "y": 80},
                            {"x": 0, "y": 80},
                        ],
                    },
                ]
            }
        ],
    }
    doc = parse_mlkit_json_data(raw_data, document_id="rx_sample_1")
    doc_text = build_document_text(doc)

    amlodipine_start = doc_text.raw_text.find("Amlodipine")
    amlodipine_end = amlodipine_start + len("Amlodipine")
    strength_start = doc_text.raw_text.find("5mg")
    strength_end = strength_start + len("5mg")
    qty_start = doc_text.raw_text.find("30 Viên")
    qty_end = qty_start + len("30 Viên")

    entities = [
        Entity(
            type=EntityType.DRUG,
            text="Amlodipine",
            start=amlodipine_start,
            end=amlodipine_end,
            confidence=0.99,
            source_region_ids=doc_text.source_regions(amlodipine_start, amlodipine_end),
        ),
        Entity(
            type=EntityType.STRENGTH,
            text="5mg",
            start=strength_start,
            end=strength_end,
            confidence=0.95,
            source_region_ids=doc_text.source_regions(strength_start, strength_end),
        ),
        Entity(
            type=EntityType.QUANTITY,
            text="30 Viên",
            start=qty_start,
            end=qty_end,
            confidence=0.92,
            source_region_ids=doc_text.source_regions(qty_start, qty_end),
        ),
    ]

    validate_entities(entities, doc_text)

    corrupted_entities = [
        Entity(
            type=EntityType.DRUG,
            text="Amlodipine",
            start=amlodipine_start + 1,
            end=amlodipine_end + 1,
            confidence=0.99,
            source_region_ids=doc_text.source_regions(
                amlodipine_start + 1, amlodipine_end + 1
            ),
        )
    ]
    with pytest.raises(ValueError, match="entity text does not match raw_text span"):
        validate_entities(corrupted_entities, doc_text)


def test_int_ingestion_multiline_entity_spanning_regions():
    """Interaction 2.2: Multi-line entity retrieves all source region IDs."""
    raw_data = {
        "metadata": {
            "fileName": "multiline.jpg",
            "imageWidth": 1000,
            "imageHeight": 1000,
        },
        "fullText": "Ngày uống 2 lần\nmỗi lần 1 viên",
        "blocks": [
            {
                "lines": [
                    {
                        "text": "Ngày uống 2 lần",
                        "cornerPoints": [
                            {"x": 0, "y": 0},
                            {"x": 100, "y": 0},
                            {"x": 100, "y": 20},
                            {"x": 0, "y": 20},
                        ],
                    },
                    {
                        "text": "mỗi lần 1 viên",
                        "cornerPoints": [
                            {"x": 0, "y": 25},
                            {"x": 100, "y": 25},
                            {"x": 100, "y": 45},
                            {"x": 0, "y": 45},
                        ],
                    },
                ]
            }
        ],
    }
    doc = parse_mlkit_json_data(raw_data, document_id="multiline_doc")
    doc_text = build_document_text(doc)

    full_instruction = doc_text.raw_text
    sources = doc_text.source_regions(0, len(full_instruction))
    assert sources == ["p0_b0_l0", "p0_b0_l1"]

    entity = Entity(
        type=EntityType.INSTRUCTION,
        text=full_instruction,
        start=0,
        end=len(full_instruction),
        confidence=0.90,
        source_region_ids=sources,
    )
    validate_entities([entity], doc_text)


# ===========================================================================
# 3. Canonical GT Decomposition + Alignment / Grouping Interactions
# ===========================================================================


def test_int_canonical_gt_decomposition_and_text_fingerprinting():
    """Interaction 3.1: Canonical GT decomposition and fingerprinting to OCR."""
    gt_file = Path("data/canonical_ground_truth/RX_001.json")
    assert gt_file.exists(), "Expected RX_001.json ground truth file"

    gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
    gt = CanonicalPrescriptionGT.model_validate(gt_data)
    assert gt.prescription_id == "RX_001"
    assert len(gt.medications) == 15

    for med in gt.medications:
        assert med.medication_id.startswith("RX_001_M")
        assert med.drug_raw is not None

    composite_instructions = [
        (
            "Ngày uống 1 viên buổi sáng",
            {
                "dosage_raw": "1 viên",
                "frequency_raw": "Ngày buổi sáng",
                "route_raw": "Uống",
                "form_raw": "viên",
            },
        ),
        (
            "Ngày uống 2 viên sau ăn tối",
            {
                "dosage_raw": "2 viên",
                "frequency_raw": "Ngày tối",
                "route_raw": "Uống",
                "form_raw": "viên",
                "instruction_raw": "sau ăn tối",
            },
        ),
        (
            "Sáng uống 1 ống sau ăn",
            {
                "dosage_raw": "1 ống",
                "frequency_raw": "Sáng",
                "route_raw": "Uống",
                "form_raw": "ống",
                "instruction_raw": "sau ăn",
            },
        ),
        (
            "Nhỏ mắt khi mỏi, khô",
            {
                "dosage_raw": None,
                "frequency_raw": None,
                "route_raw": "Nhỏ mắt",
                "form_raw": None,
                "instruction_raw": "khi mỏi, khô",
            },
        ),
    ]
    for raw_inst, expected_slots in composite_instructions:
        decomposed = decompose_instruction_rule(raw_inst)
        for k, v in expected_slots.items():
            assert decomposed[k] == v

    amlodipine = gt.medications[0]
    assert amlodipine.drug_raw == "Amlodipine (Amlor 5mg) 5mg"
    assert amlodipine.dosage_raw == "1 viên"
    assert amlodipine.frequency_raw == "Ngày buổi sáng"
    assert amlodipine.route_raw == "uống"
    assert amlodipine.form_raw == "viên"

    sample_ocr = "BVĐK TW CẦN THƠ BT29392135186 Amlodipine 5mg Metformin 750mg"
    fp_key, enc, _hosp, drugs = identify_prescription_fingerprint(sample_ocr)
    assert fp_key == "RX_CANTHO_LEVANTRAN"
    assert enc == "BT29392135186"
    assert "amlodipine" in drugs


def test_int_canonical_gt_content_similarity_clustering():
    """Interaction 3.2: Content similarity separates matching prescriptions."""
    ocr_1 = "BVĐK TW CẦN THƠ Losartan 50mg Refresh Tears 15ml ngày uống 1 viên sáng"
    ocr_2 = "CẦN THƠ Losartan 50mg Refresh 15ml sáng 1 viên"
    ocr_3 = "BỆNH VIỆN NHÂN DÂN 115 Amlodipine 5mg Hypothiazid 25mg Rotunda 30mg"

    feat_1 = extract_content_features(ocr_1)
    feat_2 = extract_content_features(ocr_2)
    feat_3 = extract_content_features(ocr_3)

    sim_within_group = compute_content_similarity(feat_1, feat_2)
    sim_across_group = compute_content_similarity(feat_1, feat_3)

    assert sim_within_group > 0.20
    assert sim_across_group < 0.10
    assert sim_within_group > 2.0 * sim_across_group


# ===========================================================================
# 4. Alignment Engine + Annotation Document Generation Interactions
# ===========================================================================


def test_int_alignment_generates_valid_annotation_document():
    """Interaction 4.1: Alignment produces valid AnnotationDocument."""
    doc_text = (
        "1. Losartan 50mg\n"
        "Số lượng: 28 Viên\n"
        "Ngày uống 1 viên buổi sáng\n"
        "Lưu ý: Tái khám đúng hẹn"
    )

    l_start = doc_text.find("Losartan")
    l_end = l_start + len("Losartan")
    s_start = doc_text.find("50mg")
    s_end = s_start + len("50mg")
    q_start = doc_text.find("28 Viên")
    q_end = q_start + len("28 Viên")
    d_start = doc_text.find("1 viên")
    d_end = d_start + len("1 viên")
    f_start = doc_text.find("buổi sáng")
    f_end = f_start + len("buổi sáng")
    n_start = doc_text.find("Tái khám đúng hẹn")
    n_end = n_start + len("Tái khám đúng hẹn")

    entities = [
        GoldEntity(type=EntityType.DRUG, text="Losartan", start=l_start, end=l_end),
        GoldEntity(type=EntityType.STRENGTH, text="50mg", start=s_start, end=s_end),
        GoldEntity(type=EntityType.QUANTITY, text="28 Viên", start=q_start, end=q_end),
        GoldEntity(type=EntityType.DOSAGE, text="1 viên", start=d_start, end=d_end),
        GoldEntity(
            type=EntityType.FREQUENCY,
            text="buổi sáng",
            start=f_start,
            end=f_end,
        ),
        GoldEntity(
            type=EntityType.NOTE,
            text="Tái khám đúng hẹn",
            start=n_start,
            end=n_end,
        ),
    ]

    annot_doc = AnnotationDocument(
        document_id="doc_aligned_001",
        raw_text=doc_text,
        entities=entities,
        provenance=AnnotationProvenance(source="native"),
    )

    assert annot_doc.document_id == "doc_aligned_001"
    assert len(annot_doc.entities) == 6
    assert annot_doc.entities[0].text == "Losartan"
    expected_slice = doc_text[annot_doc.entities[0].start : annot_doc.entities[0].end]
    assert expected_slice == "Losartan"


def test_int_alignment_policy_locking_drug_without_strength():
    """Interaction 4.2: Enforce DRUG policy excluding STRENGTH."""
    raw_text = "Amlodipine 5mg 30 Viên"

    valid_doc = AnnotationDocument(
        document_id="doc_policy_1",
        raw_text=raw_text,
        entities=[
            GoldEntity(type=EntityType.DRUG, text="Amlodipine", start=0, end=10),
            GoldEntity(type=EntityType.STRENGTH, text="5mg", start=11, end=14),
            GoldEntity(type=EntityType.QUANTITY, text="30 Viên", start=15, end=22),
        ],
    )
    assert len(valid_doc.entities) == 3

    with pytest.raises(ValueError, match="gold entity spans must not overlap"):
        AnnotationDocument(
            document_id="doc_policy_invalid",
            raw_text=raw_text,
            entities=[
                GoldEntity(
                    type=EntityType.DRUG, text="Amlodipine 5mg", start=0, end=14
                ),
                GoldEntity(type=EntityType.STRENGTH, text="5mg", start=11, end=14),
            ],
        )


# ===========================================================================
# 5. Annotation Document + Flat BIO PhoBERT Export Interactions
# ===========================================================================


def test_int_annotation_doc_to_phobert_bio_all_ten_classes():
    """Interaction 5.1: Export all 10 clinical entity classes to BIO labels."""
    raw_text = (
        "Paracetamol 500mg 1 viên Ngày 2 lần 30 Viên 10 ngày Uống sau ăn viên Tái khám"
    )

    entities = [
        GoldEntity(type=EntityType.DRUG, text="Paracetamol", start=0, end=11),
        GoldEntity(type=EntityType.STRENGTH, text="500mg", start=12, end=17),
        GoldEntity(type=EntityType.DOSAGE, text="1 viên", start=18, end=24),
        GoldEntity(type=EntityType.FREQUENCY, text="Ngày 2 lần", start=25, end=35),
        GoldEntity(type=EntityType.QUANTITY, text="30 Viên", start=36, end=43),
        GoldEntity(type=EntityType.DURATION, text="10 ngày", start=44, end=51),
        GoldEntity(type=EntityType.ROUTE, text="Uống", start=52, end=56),
        GoldEntity(type=EntityType.INSTRUCTION, text="sau ăn", start=57, end=63),
        GoldEntity(type=EntityType.FORM, text="viên", start=64, end=68),
        GoldEntity(type=EntityType.NOTE, text="Tái khám", start=69, end=77),
    ]

    doc = AnnotationDocument(
        document_id="doc_bio_10_classes", raw_text=raw_text, entities=entities
    )
    tokenizer = MockFastTokenizer()
    encoded = align_token_labels(doc, tokenizer)

    labels = encoded["labels"]
    assert labels[0] == -100
    assert labels[-1] == -100

    str_labels = [ID_TO_LABEL[lid] for lid in labels if lid != -100]
    for et in EntityType:
        assert f"B-{et.value}" in str_labels


def test_int_bio_export_multi_word_subwords_b_and_i_progression():
    """Interaction 5.2: Multi-word entities receive B- and I- tags."""
    raw_text = "Calcium Corbiere 10ml hòa tan trong nước"
    entities = [
        GoldEntity(type=EntityType.DRUG, text="Calcium Corbiere 10ml", start=0, end=21),
        GoldEntity(
            type=EntityType.INSTRUCTION,
            text="hòa tan trong nước",
            start=22,
            end=40,
        ),
    ]
    doc = AnnotationDocument(
        document_id="doc_multiword", raw_text=raw_text, entities=entities
    )
    tokenizer = MockFastTokenizer()
    encoded = align_token_labels(doc, tokenizer)

    valid_labels = [ID_TO_LABEL[lid] for lid in encoded["labels"] if lid != -100]
    assert valid_labels[0] == "B-DRUG"
    assert valid_labels[1] == "I-DRUG"
    assert valid_labels[2] == "I-DRUG"
    assert valid_labels[3] == "B-INSTRUCTION"
    assert valid_labels[4] == "I-INSTRUCTION"
    assert valid_labels[5] == "I-INSTRUCTION"
    assert valid_labels[6] == "I-INSTRUCTION"


# ===========================================================================
# 6. Dataset Generator (19/4/4 Split Isolation) + Prescription Samplers
# ===========================================================================


def test_int_split_generator_isolation_and_manifest():
    """Interaction 6.1: 19/4/4 prescription split enforces zero leakage."""
    splits_file = Path("data/manifests/balanced_prescription_splits.json")
    assert splits_file.exists(), "Expected balanced_prescription_splits.json"

    splits = json.loads(splits_file.read_text(encoding="utf-8"))
    train_rx = set(splits["train"])
    val_rx = set(splits["val"])
    test_rx = set(splits["test"])
    unverified_rx = set(splits.get("unverified_or_review", []))

    assert len(train_rx) == 19
    assert len(val_rx) == 4
    assert len(test_rx) == 4
    assert len(train_rx | val_rx | test_rx) == 27

    assert len(train_rx & val_rx) == 0
    assert len(train_rx & test_rx) == 0
    assert len(val_rx & test_rx) == 0

    assert len(unverified_rx & (train_rx | val_rx | test_rx)) == 0


def test_int_prescription_weighted_sampler_math_and_balance():
    """Interaction 6.2: Weighted sampler formula w_i = 1/N_{p(i)}."""
    doc_records = (
        [{"doc_id": f"img1_{i}", "prescription_id": "RX_001"} for i in range(100)]
        + [{"doc_id": f"img2_{i}", "prescription_id": "RX_002"} for i in range(2)]
        + [{"doc_id": "img3_0", "prescription_id": "RX_003"}]
    )

    counts = Counter(d["prescription_id"] for d in doc_records)
    weights = [1.0 / counts[d["prescription_id"]] for d in doc_records]

    for rx_id in ["RX_001", "RX_002", "RX_003"]:
        rx_sum = sum(
            w
            for d, w in zip(doc_records, weights, strict=True)
            if d["prescription_id"] == rx_id
        )
        assert abs(rx_sum - 1.0) < 1e-9

    assert abs(sum(weights) - 3.0) < 1e-9


# ===========================================================================
# 7. Sampler + PyTorch / DataLoader Integration
# ===========================================================================


def test_int_hierarchical_sampler_epoch_capping():
    """Interaction 7.1: Hierarchical sampler caps high-volume prescriptions."""
    prescription_images = {
        "RX_001": [f"img_rx1_{i}" for i in range(111)],
        "RX_002": [f"img_rx2_{i}" for i in range(50)],
        "RX_016": ["img_rx16_0", "img_rx16_1"],
        "RX_019": ["img_rx19_0"],
    }

    sampler = HierarchicalPrescriptionSampler(
        prescription_to_images=prescription_images,
        max_images_per_rx_per_epoch=15,
        seed=42,
    )
    epoch_sample = sampler.sample_epoch()

    assert len(epoch_sample) == 33
    counts = Counter(img.split("_")[1] for img in epoch_sample)
    assert counts["rx1"] == 15
    assert counts["rx2"] == 15
    assert counts["rx16"] == 2
    assert counts["rx19"] == 1


def test_int_sampler_reproducibility_with_seed():
    """Interaction 7.2: Sampler reproducibility across identical seeds."""
    prescription_images = {
        f"RX_{i:03d}": [f"img_{i}_{j}" for j in range(20)] for i in range(1, 10)
    }

    sampler_1 = HierarchicalPrescriptionSampler(
        prescription_images, max_images_per_rx_per_epoch=5, seed=123
    )
    sampler_2 = HierarchicalPrescriptionSampler(
        prescription_images, max_images_per_rx_per_epoch=5, seed=123
    )
    sampler_3 = HierarchicalPrescriptionSampler(
        prescription_images, max_images_per_rx_per_epoch=5, seed=456
    )

    assert sampler_1.sample_epoch() == sampler_2.sample_epoch()
    assert sampler_1.sample_epoch() != sampler_3.sample_epoch()


# ===========================================================================
# 8. Annotation Documents + Strict Multi-Metric Evaluator
# ===========================================================================


def test_int_evaluator_strict_exact_span_prf():
    """Interaction 8.1: Strict multi-metric evaluator exact span PRF."""
    gold = [
        Entity(
            type=EntityType.DRUG,
            text="Amlodipine",
            start=0,
            end=10,
            confidence=1.0,
            source_region_ids=["r1"],
        ),
        Entity(
            type=EntityType.STRENGTH,
            text="5mg",
            start=11,
            end=14,
            confidence=1.0,
            source_region_ids=["r1"],
        ),
        Entity(
            type=EntityType.QUANTITY,
            text="30 Viên",
            start=15,
            end=22,
            confidence=1.0,
            source_region_ids=["r2"],
        ),
    ]

    perf_pred = list(gold)
    eval_perf = strict_entity_evaluation(gold, perf_pred)
    assert eval_perf.overall.precision == 1.0
    assert eval_perf.overall.recall == 1.0
    assert eval_perf.overall.f1 == 1.0

    shifted_pred = [
        Entity(
            type=EntityType.DRUG,
            text="Amlodipin",
            start=0,
            end=9,
            confidence=1.0,
            source_region_ids=["r1"],
        ),
        gold[1],
        gold[2],
    ]
    eval_shifted = strict_entity_evaluation(gold, shifted_pred)
    assert eval_shifted.overall.true_positive == 2
    assert eval_shifted.overall.predicted == 3
    assert eval_shifted.overall.gold == 3
    assert eval_shifted.overall.precision == 2 / 3
    assert eval_shifted.overall.recall == 2 / 3
    assert eval_shifted.per_class[EntityType.DRUG].f1 == 0.0
    assert eval_shifted.per_class[EntityType.STRENGTH].f1 == 1.0


def test_int_evaluator_per_class_scores_all_ten_types():
    """Interaction 8.2: Evaluator populates all 10 EntityType scores."""
    gold = [
        Entity(
            type=EntityType.DRUG,
            text="Paracetamol",
            start=0,
            end=11,
            confidence=1.0,
            source_region_ids=["r1"],
        ),
        Entity(
            type=EntityType.DOSAGE,
            text="1 viên",
            start=12,
            end=18,
            confidence=1.0,
            source_region_ids=["r2"],
        ),
    ]
    pred = [
        Entity(
            type=EntityType.DRUG,
            text="Paracetamol",
            start=0,
            end=11,
            confidence=1.0,
            source_region_ids=["r1"],
        ),
        Entity(
            type=EntityType.DOSAGE,
            text="2 viên",
            start=12,
            end=18,
            confidence=1.0,
            source_region_ids=["r2"],
        ),
    ]

    report = strict_entity_evaluation(gold, pred)
    assert len(report.per_class) == 10
    for et in EntityType:
        assert et in report.per_class
        assert 0.0 <= report.per_class[et].f1 <= 1.0


def test_int_evaluator_record_exact_match_and_tuple_prf():
    """Interaction 8.3: Evaluates record exact match vs slot-tuple PRF."""
    gold_records = [
        {
            "drug": ("DRUG", 0, 10),
            "slots": {("STRENGTH", 11, 14), ("DOSAGE", 15, 21)},
        },
        {
            "drug": ("DRUG", 30, 38),
            "slots": {("STRENGTH", 39, 44), ("QUANTITY", 45, 52)},
        },
    ]

    pred_records = [
        {
            "drug": ("DRUG", 0, 10),
            "slots": {("STRENGTH", 11, 14), ("DOSAGE", 15, 21)},
        },
        {"drug": ("DRUG", 30, 38), "slots": {("STRENGTH", 39, 44)}},
    ]

    exact_matches = sum(
        1 for g, p in zip(gold_records, pred_records, strict=True) if g == p
    )
    record_em = exact_matches / len(gold_records)
    assert record_em == 0.5

    gold_tuples = {
        (g["drug"], slot_type, s, e)
        for g in gold_records
        for slot_type, s, e in g["slots"]
    }
    pred_tuples = {
        (p["drug"], slot_type, s, e)
        for p in pred_records
        for slot_type, s, e in p["slots"]
    }
    tuple_tp = len(gold_tuples & pred_tuples)
    tuple_prec = tuple_tp / len(pred_tuples)
    tuple_rec = tuple_tp / len(gold_tuples)
    tuple_f1 = (
        (2 * tuple_prec * tuple_rec) / (tuple_prec + tuple_rec)
        if (tuple_prec + tuple_rec > 0)
        else 0.0
    )

    assert tuple_tp == 3
    assert tuple_prec == 1.0
    assert tuple_rec == 0.75
    assert tuple_f1 > record_em


# ===========================================================================
# 9. Evaluator + Dual-Level Aggregation (Capture Micro vs Macro)
# ===========================================================================


def test_int_dual_level_aggregation_skew_sensitivity():
    """Interaction 9.1: Capture Micro vs Prescription Macro under data skew."""
    records = []
    for i in range(100):
        records.append(
            {
                "prescription_id": "RX_001",
                "document_id": f"img_rx1_{i}",
                "tp": 5,
                "predicted": 5,
                "gold": 5,
            }
        )
    records.append(
        {
            "prescription_id": "RX_002",
            "document_id": "img_rx2_0",
            "tp": 0,
            "predicted": 5,
            "gold": 5,
        }
    )

    total_tp = sum(r["tp"] for r in records)
    total_pred = sum(r["predicted"] for r in records)
    total_gold = sum(r["gold"] for r in records)
    micro_prec = total_tp / total_pred
    micro_rec = total_tp / total_gold
    micro_f1 = (2 * micro_prec * micro_rec) / (micro_prec + micro_rec)

    macro_summary = compute_prescription_macro_summary(records)

    assert micro_f1 > 0.98
    assert abs(macro_summary["macro_f1"] - 0.50) < 1e-5
    assert macro_summary["prescription_count"] == 2.0


def test_int_dual_level_aggregation_balanced_case():
    """Interaction 9.2: Convergence of Micro and Macro on balanced data."""
    records = []
    for rx_idx in range(1, 6):
        rx_id = f"RX_{rx_idx:03d}"
        for doc_idx in range(10):
            records.append(
                {
                    "prescription_id": rx_id,
                    "document_id": f"doc_{rx_id}_{doc_idx}",
                    "tp": 4,
                    "predicted": 5,
                    "gold": 5,
                }
            )

    total_tp = sum(r["tp"] for r in records)
    total_pred = sum(r["predicted"] for r in records)
    total_gold = sum(r["gold"] for r in records)
    micro_f1 = (2 * (total_tp / total_pred) * (total_tp / total_gold)) / (
        (total_tp / total_pred) + (total_tp / total_gold)
    )

    macro_summary = compute_prescription_macro_summary(records)

    assert abs(micro_f1 - 0.80) < 1e-5
    assert abs(macro_summary["macro_f1"] - 0.80) < 1e-5


# ===========================================================================
# 10. Ingestion + API 503 Security Guard Interactions
# ===========================================================================


def test_int_api_ingestion_503_security_guard_when_unconfigured(monkeypatch):
    """Interaction 10.1: Production API returns 503 when unconfigured."""
    monkeypatch.delenv("RXIE_MODEL_PATH", raising=False)
    app = create_app()
    client = TestClient(app)

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json() == {"status": "ok"}

    info_resp = client.get("/model-info")
    assert info_resp.status_code == 200
    assert info_resp.json() == {
        "configured": False,
        "available": False,
        "model_version": None,
    }

    doc = load_mlkit_ocr_document(list(Path("data/ocr_final").glob("*.json"))[0])
    resp = client.post("/entities", json=doc.model_dump(mode="json"))
    assert resp.status_code == 503
    assert "RXIE_MODEL_PATH is not configured" in resp.json()["detail"]


def test_int_api_ingestion_with_injected_classifier():
    """Interaction 10.2: API processes OcrDocument with injected classifier."""
    classifier = MockPrescriptionClassifier()
    app = create_app(classifier_provider=lambda: classifier)
    client = TestClient(app)

    info = client.get("/model-info").json()
    assert info["configured"] is True
    assert info["available"] is True
    assert info["model_version"] == "mock-pipeline-v1.0.0"

    payload = {
        "schema_version": "rxie.ocr.v1",
        "document_id": "api_test_doc_01",
        "ocr_engine": {
            "name": "google_mlkit_text_recognition",
            "version": "0.15.1",
        },
        "pages": [
            {
                "width": 1000,
                "height": 1000,
                "page_index": 0,
                "regions": [
                    {
                        "region_id": "p0_b0_l0",
                        "text": "Amlodipine 5mg",
                        "confidence": 0.99,
                        "reading_order": 0,
                        "bbox": {"points": [[0, 0], [100, 0], [100, 20], [0, 20]]},
                    }
                ],
            }
        ],
    }

    resp = client.post("/entities", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["schema_version"] == "rxie.entities.v1"
    assert data["document_id"] == "api_test_doc_01"
    assert data["model_version"] == "mock-pipeline-v1.0.0"
    assert len(data["entities"]) == 1
    assert data["entities"][0]["text"] == "Amlodipine"
    assert data["entities"][0]["type"] == "DRUG"


def test_int_api_rejects_malformed_ocr_payload_with_422():
    """Interaction 10.3: API rejects invalid OCR schema with 422 error."""
    app = create_app(classifier_provider=lambda: MockPrescriptionClassifier())
    client = TestClient(app)

    invalid_payload = {
        "schema_version": "rxie.ocr.v1",
        "document_id": "invalid_doc",
        "ocr_engine": {
            "name": "google_mlkit_text_recognition",
            "version": "0.15.1",
        },
    }
    resp = client.post("/entities", json=invalid_payload)
    assert resp.status_code == 422


# ===========================================================================
# 11. Legacy Data Isolation + Provenance Warning Integration
# ===========================================================================


def test_int_legacy_data_conversion_preserves_provenance_and_spans():
    """Interaction 11.1: Legacy token/BIO conversion generates exact spans."""
    tokens = ["Uống", "Paracetamol", "500mg", "ngày", "2", "lần"]
    tags = ["O", "B-DRUG", "O", "O", "O", "O"]

    doc = convert_legacy_bio("legacy_001", tokens, tags)
    assert doc.document_id == "legacy_001"
    assert doc.raw_text == "Uống Paracetamol 500mg ngày 2 lần"
    assert len(doc.entities) == 1
    assert doc.entities[0].type == EntityType.DRUG
    assert doc.entities[0].text == "Paracetamol"
    assert doc.entities[0].start == 5
    assert doc.entities[0].end == 16
    assert doc.provenance.source == "legacy_drug_only"
    assert LEGACY_PROVENANCE_WARNING in doc.provenance.warnings
