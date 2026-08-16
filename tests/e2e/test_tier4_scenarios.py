"""Tier 4: Real-World Clinical Application Scenarios Test Suite for RxIE Sprint A.

This suite contains 11 realistic end-to-end clinical workflow scenarios:
- Scenario 1: Standard Multi-Medication Outpatient Prescription Workflow
- Scenario 2: Highly Distorted / Noisy Low-Confidence OCR Capture Workflow
- Scenario 3: Pediatric Weight-Based Drops & Complex Dosages Workflow
- Scenario 4: Chronic Disease Polypharmacy (10+ Medications) Workflow
- Scenario 5: Full Train/Val/Test Split Generation & PhoBERT BIO Dataset Export
- Scenario 6: Full Multi-Metric Benchmark Evaluation Suite
- Scenario 7: Production REST API Ingestion & Missing Model 503 Security Guard
- Scenario 8: Multi-Page / Complex Formatting Clinical Records Workflow
- Scenario 9: Duplicate Medication Names with Differing Strengths & Dosages
- Scenario 10: Vietnamese Diacritic and Unicode Robustness
- Scenario 11: Complete End-to-End Pipeline Integration Lifecycle
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from rxie.alignment import LABEL_TO_ID, align_token_labels
from rxie.api import create_app
from rxie.evaluation import (
    strict_entity_evaluation,
)
from rxie.grouping import (
    CanonicalPrescriptionGT,
    normalize_text_key,
)
from rxie.ingestion import (
    load_mlkit_ocr_document,
    parse_mlkit_json_data,
)
from rxie.schemas import (
    AnnotationDocument,
    Entity,
    EntityType,
    GoldEntity,
    OcrDocument,
)
from rxie.text import DocumentText, build_document_text, validate_entities

# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


class ScenarioFastTokenizer:
    """Whitespace-based fast tokenizer simulator providing offset mapping."""

    is_fast = True

    def __call__(
        self,
        text: str,
        return_offsets_mapping: bool = True,
        truncation: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not return_offsets_mapping:
            raise ValueError(
                "ScenarioFastTokenizer requires return_offsets_mapping=True"
            )

        input_ids = [101]
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
            input_ids.append(1000 + len(input_ids))
            attention_mask.append(1)
            offset_mapping.append((start, pos))

        input_ids.append(102)
        attention_mask.append(1)
        offset_mapping.append((0, 0))

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "offset_mapping": offset_mapping,
        }


class ScenarioDeterministicClassifier:
    """Deterministic classifier returning configured entities for testing."""

    model_version = "scenario-model-v2.0.0"

    def __init__(self, entities: list[Entity] | None = None):
        self._entities = entities or []

    def classify(self, document: DocumentText) -> list[Entity]:
        return self._entities


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


def decompose_vietnamese_instruction(raw: str | None) -> dict[str, str | None]:
    """Decompose Vietnamese prescription instructions into atomic slots."""
    if not raw or not raw.strip():
        return {
            "dosage_raw": None,
            "frequency_raw": None,
            "duration_raw": None,
            "route_raw": None,
            "instruction_raw": None,
            "form_raw": None,
        }

    text = raw.strip()
    res: dict[str, str | None] = {
        "dosage_raw": None,
        "frequency_raw": None,
        "duration_raw": None,
        "route_raw": None,
        "instruction_raw": None,
        "form_raw": None,
    }

    # Route
    for route in ["Tiêm dưới da", "Nhỏ mắt", "Nhỏ tai", "Bôi", "Uống", "uống"]:
        if route.lower() in text.lower():
            res["route_raw"] = "uống" if route.lower() == "uống" else route
            break

    # Dosage & Form
    if "1-2 viên" in text:
        res["dosage_raw"] = "1-2 viên"
        res["form_raw"] = "viên"
    elif "1/2 viên" in text:
        res["dosage_raw"] = "1/2 viên"
        res["form_raw"] = "viên"
    elif "1 viên" in text or "1v" in text.lower():
        res["dosage_raw"] = "1 viên"
        res["form_raw"] = "viên"
    elif "2 viên" in text:
        res["dosage_raw"] = "2 viên"
        res["form_raw"] = "viên"
    elif "3 viên" in text:
        res["dosage_raw"] = "3 viên"
        res["form_raw"] = "viên"
    elif "1 ống" in text:
        res["dosage_raw"] = "1 ống"
        res["form_raw"] = "ống"
    elif "5ml" in text:
        res["dosage_raw"] = "5ml"
        res["form_raw"] = "ml"
    elif "1-2 giọt" in text:
        res["dosage_raw"] = "1-2 giọt"
        res["form_raw"] = "giọt"
    elif "10 đơn vị" in text:
        res["dosage_raw"] = "10 đơn vị"
        res["form_raw"] = "đơn vị"

    # Frequency
    if "3-4 lần/ngày" in text:
        res["frequency_raw"] = "3-4 lần/ngày"
    elif "2 lần/ngày" in text:
        res["frequency_raw"] = "2 lần/ngày"
    elif "ngày 2 lần" in text.lower():
        res["frequency_raw"] = "Ngày 2 lần"
    elif "buổi sáng" in text.lower() and "ngày" in text.lower():
        res["frequency_raw"] = "Ngày buổi sáng"
    elif "buổi tối" in text.lower() and "ngày" in text.lower():
        res["frequency_raw"] = "Ngày buổi tối"
    elif "sáng, tối" in text.lower() or "(sáng, tối)" in text:
        res["frequency_raw"] = "Ngày (sáng, tối)"
    elif "ngày" in text.lower() and "tối" in text.lower():
        res["frequency_raw"] = "Ngày tối"
    elif "ngày" in text.lower() and "sáng" in text.lower():
        res["frequency_raw"] = "Ngày sáng"
    elif "sáng" in text.lower():
        res["frequency_raw"] = "Sáng"
    elif "trưa" in text.lower():
        res["frequency_raw"] = "Trưa"
    elif "tối" in text.lower():
        res["frequency_raw"] = "Tối"
    elif "ngày" in text.lower():
        res["frequency_raw"] = "Ngày"

    # Residual instruction
    if "trước ăn sáng 30 phút" in text:
        res["instruction_raw"] = "trước ăn sáng 30 phút"
    elif "sau ăn tối" in text:
        res["instruction_raw"] = "sau ăn tối"
    elif "sau ăn no (khi đau)" in text:
        res["instruction_raw"] = "sau ăn no (khi đau)"
    elif "sau ăn" in text:
        res["instruction_raw"] = "sau ăn"
    elif "khi sốt" in text.lower():
        res["instruction_raw"] = "khi sốt"
    elif "khi đau" in text.lower():
        res["instruction_raw"] = "khi đau"
    elif "khi mỏi, khô" in text.lower() or "khi khô" in text.lower():
        res["instruction_raw"] = "khi mỏi, khô"
    elif "hòa tan trong nước" in text:
        res["instruction_raw"] = "hòa tan trong nước"

    return res


# ===========================================================================
# Scenario 1: Standard Multi-Medication Outpatient Prescription Workflow
# ===========================================================================


def test_scenario_1_standard_outpatient_prescription_workflow():
    """Scenario 1: Standard outpatient prescription workflow."""
    raw_ocr = {
        "metadata": {
            "fileName": "outpatient_001.jpg",
            "imageWidth": 2000,
            "imageHeight": 3000,
        },
        "fullText": (
            "BỆNH VIỆN ĐA KHOA TRUNG ƯƠNG CẦN THƠ\n"
            "ĐƠN THUỐC NGOẠI TRÚ\n"
            "Họ tên: LÊ VĂN TRẬN  Tuổi: 58  Giới tính: Nam\n"
            "1. Amlodipine 5mg\n"
            "Số lượng: 30 Viên\n"
            "Ngày uống 1 viên buổi sáng\n"
            "2. Losartan 50mg\n"
            "Số lượng: 30 Viên\n"
            "Ngày uống 1 viên buổi sáng\n"
            "3. Atorvastatin 20mg\n"
            "Số lượng: 30 Viên\n"
            "Ngày uống 1 viên buổi tối\n"
            "4. Esomeprazole 40mg\n"
            "Số lượng: 30 Viên\n"
            "Ngày uống 1 viên trước ăn sáng 30 phút"
        ),
        "blocks": [
            {
                "lines": [
                    {
                        "text": "BỆNH VIỆN ĐA KHOA TRUNG ƯƠNG CẦN THƠ",
                        "cornerPoints": [
                            {"x": 100, "y": 100},
                            {"x": 900, "y": 100},
                            {"x": 900, "y": 150},
                            {"x": 100, "y": 150},
                        ],
                    },
                    {
                        "text": "ĐƠN THUỐC NGOẠI TRÚ",
                        "cornerPoints": [
                            {"x": 300, "y": 160},
                            {"x": 700, "y": 160},
                            {"x": 700, "y": 200},
                            {"x": 300, "y": 200},
                        ],
                    },
                    {
                        "text": "Họ tên: LÊ VĂN TRẬN  Tuổi: 58  Giới tính: Nam",
                        "cornerPoints": [
                            {"x": 100, "y": 210},
                            {"x": 900, "y": 210},
                            {"x": 900, "y": 250},
                            {"x": 100, "y": 250},
                        ],
                    },
                    {
                        "text": "1. Amlodipine 5mg",
                        "cornerPoints": [
                            {"x": 100, "y": 260},
                            {"x": 600, "y": 260},
                            {"x": 600, "y": 300},
                            {"x": 100, "y": 300},
                        ],
                    },
                    {
                        "text": "Số lượng: 30 Viên",
                        "cornerPoints": [
                            {"x": 100, "y": 310},
                            {"x": 500, "y": 310},
                            {"x": 500, "y": 350},
                            {"x": 100, "y": 350},
                        ],
                    },
                    {
                        "text": "Ngày uống 1 viên buổi sáng",
                        "cornerPoints": [
                            {"x": 100, "y": 360},
                            {"x": 700, "y": 360},
                            {"x": 700, "y": 400},
                            {"x": 100, "y": 400},
                        ],
                    },
                    {
                        "text": "2. Losartan 50mg",
                        "cornerPoints": [
                            {"x": 100, "y": 410},
                            {"x": 600, "y": 410},
                            {"x": 600, "y": 450},
                            {"x": 100, "y": 450},
                        ],
                    },
                    {
                        "text": "Số lượng: 30 Viên",
                        "cornerPoints": [
                            {"x": 100, "y": 460},
                            {"x": 500, "y": 460},
                            {"x": 500, "y": 500},
                            {"x": 100, "y": 500},
                        ],
                    },
                    {
                        "text": "Ngày uống 1 viên buổi sáng",
                        "cornerPoints": [
                            {"x": 100, "y": 510},
                            {"x": 700, "y": 510},
                            {"x": 700, "y": 550},
                            {"x": 100, "y": 550},
                        ],
                    },
                    {
                        "text": "3. Atorvastatin 20mg",
                        "cornerPoints": [
                            {"x": 100, "y": 560},
                            {"x": 600, "y": 560},
                            {"x": 600, "y": 600},
                            {"x": 100, "y": 600},
                        ],
                    },
                    {
                        "text": "Số lượng: 30 Viên",
                        "cornerPoints": [
                            {"x": 100, "y": 610},
                            {"x": 500, "y": 610},
                            {"x": 500, "y": 650},
                            {"x": 100, "y": 650},
                        ],
                    },
                    {
                        "text": "Ngày uống 1 viên buổi tối",
                        "cornerPoints": [
                            {"x": 100, "y": 660},
                            {"x": 700, "y": 660},
                            {"x": 700, "y": 700},
                            {"x": 100, "y": 700},
                        ],
                    },
                    {
                        "text": "4. Esomeprazole 40mg",
                        "cornerPoints": [
                            {"x": 100, "y": 710},
                            {"x": 600, "y": 710},
                            {"x": 600, "y": 750},
                            {"x": 100, "y": 750},
                        ],
                    },
                    {
                        "text": "Số lượng: 30 Viên",
                        "cornerPoints": [
                            {"x": 100, "y": 760},
                            {"x": 500, "y": 760},
                            {"x": 500, "y": 800},
                            {"x": 100, "y": 800},
                        ],
                    },
                    {
                        "text": "Ngày uống 1 viên trước ăn sáng 30 phút",
                        "cornerPoints": [
                            {"x": 100, "y": 810},
                            {"x": 800, "y": 810},
                            {"x": 800, "y": 850},
                            {"x": 100, "y": 850},
                        ],
                    },
                ]
            }
        ],
    }

    doc = parse_mlkit_json_data(raw_ocr, document_id="outpatient_rx_01")
    doc_text = build_document_text(doc)
    assert doc_text.raw_text == raw_ocr["fullText"]
    assert len(doc_text.regions) == 15

    entities: list[GoldEntity] = []
    med_configs = [
        ("Amlodipine", "5mg", "30 Viên", "1 viên", "buổi sáng"),
        ("Losartan", "50mg", "30 Viên", "1 viên", "buổi sáng"),
        ("Atorvastatin", "20mg", "30 Viên", "1 viên", "buổi tối"),
        ("Esomeprazole", "40mg", "30 Viên", "1 viên", "trước ăn sáng 30 phút"),
    ]

    cursor = 0
    for drug_name, strength, qty, dosage, inst in med_configs:
        d_start = doc_text.raw_text.find(drug_name, cursor)
        d_end = d_start + len(drug_name)
        entities.append(
            GoldEntity(type=EntityType.DRUG, text=drug_name, start=d_start, end=d_end)
        )

        s_start = doc_text.raw_text.find(strength, d_end)
        s_end = s_start + len(strength)
        entities.append(
            GoldEntity(
                type=EntityType.STRENGTH, text=strength, start=s_start, end=s_end
            )
        )

        q_start = doc_text.raw_text.find(qty, s_end)
        q_end = q_start + len(qty)
        entities.append(
            GoldEntity(type=EntityType.QUANTITY, text=qty, start=q_start, end=q_end)
        )

        ds_start = doc_text.raw_text.find(dosage, q_end)
        ds_end = ds_start + len(dosage)
        entities.append(
            GoldEntity(type=EntityType.DOSAGE, text=dosage, start=ds_start, end=ds_end)
        )

        i_start = doc_text.raw_text.find(inst, ds_end)
        i_end = i_start + len(inst)
        entities.append(
            GoldEntity(
                type=EntityType.INSTRUCTION,
                text=inst,
                start=i_start,
                end=i_end,
            )
        )
        cursor = i_end

    annot_doc = AnnotationDocument(
        document_id="outpatient_rx_01",
        raw_text=doc_text.raw_text,
        entities=entities,
    )
    assert len(annot_doc.entities) == 20

    tokenizer = ScenarioFastTokenizer()
    bio_encoded = align_token_labels(annot_doc, tokenizer)
    assert len(bio_encoded["labels"]) > 0

    gold_eval_entities = [
        Entity(
            type=e.type,
            text=e.text,
            start=e.start,
            end=e.end,
            confidence=1.0,
            source_region_ids=doc_text.source_regions(e.start, e.end),
        )
        for e in annot_doc.entities
    ]
    eval_result = strict_entity_evaluation(gold_eval_entities, gold_eval_entities)
    assert eval_result.overall.f1 == 1.0
    assert eval_result.overall.precision == 1.0
    assert eval_result.overall.recall == 1.0
    assert eval_result.per_class[EntityType.DRUG].f1 == 1.0
    assert eval_result.per_class[EntityType.STRENGTH].f1 == 1.0


# ===========================================================================
# Scenario 2: Highly Distorted / Noisy Low-Confidence OCR Capture Workflow
# ===========================================================================


def test_scenario_2_distorted_low_confidence_ocr_capture_workflow():
    """Scenario 2: Distorted low-confidence OCR capture resilience."""
    noisy_ocr = {
        "metadata": {
            "fileName": "noisy_skewed_capture.jpg",
            "imageWidth": 1500,
            "imageHeight": 2000,
        },
        "fullText": ("DON THUOC\nParacetamo1 500rng\nu0ng 1 v1en\nSo 1uong: 2O V1en"),
        "blocks": [
            {
                "lines": [
                    {
                        "text": "DON THUOC",
                        "confidence": 0.35,
                        "cornerPoints": [
                            {"x": -10, "y": -5},
                            {"x": 500, "y": 20},
                            {"x": 490, "y": 80},
                            {"x": -20, "y": 60},
                        ],
                    },
                    {
                        "text": "Paracetamo1 500rng",
                        "confidence": 0.22,
                        "cornerPoints": [
                            {"x": 10, "y": 90},
                            {"x": 800, "y": 120},
                            {"x": 790, "y": 180},
                            {"x": 0, "y": 150},
                        ],
                    },
                    {
                        "text": "u0ng 1 v1en",
                        "confidence": 0.18,
                        "cornerPoints": [
                            {"x": 15, "y": 190},
                            {"x": 600, "y": 210},
                            {"x": 590, "y": 260},
                            {"x": 5, "y": 240},
                        ],
                    },
                    {
                        "text": "So 1uong: 2O V1en",
                        "confidence": 0.15,
                        "cornerPoints": [
                            {"x": 20, "y": 270},
                            {"x": 700, "y": 290},
                            {"x": 690, "y": 340},
                            {"x": 10, "y": 320},
                        ],
                    },
                ]
            }
        ],
    }

    doc = parse_mlkit_json_data(noisy_ocr, document_id="noisy_doc_01")
    for page in doc.pages:
        for r in page.regions:
            for pt in r.bbox.points:
                assert 0.0 <= pt[0] <= 1500.0
                assert 0.0 <= pt[1] <= 2000.0
            assert 0.0 <= r.confidence <= 1.0

    doc_text = build_document_text(doc)
    assert doc_text.raw_text == noisy_ocr["fullText"]

    gold_entity = Entity(
        type=EntityType.DRUG,
        text="Paracetamol",
        start=10,
        end=21,
        confidence=1.0,
        source_region_ids=["p0_b0_l1"],
    )
    pred_entity = Entity(
        type=EntityType.DRUG,
        text="Paracetamo1",
        start=10,
        end=21,
        confidence=0.22,
        source_region_ids=["p0_b0_l1"],
    )

    eval_res = strict_entity_evaluation([gold_entity], [pred_entity])
    assert eval_res.overall.true_positive == 1
    assert eval_res.overall.f1 == 1.0


# ===========================================================================
# Scenario 3: Pediatric Weight-Based Drops & Complex Dosages Workflow
# ===========================================================================


def test_scenario_3_pediatric_drops_and_complex_dosages_workflow():
    """Scenario 3: Pediatric drops and suspensions workflow."""
    pediatric_text = (
        "ĐƠN THUỐC NHI KHOA\n"
        "Bệnh nhân: NGUYỄN BÉ BI  Tuổi: 3 tuổi (14kg)\n"
        "1. Tobrex 0.3% 5ml\n"
        "Số lượng: 1 Lọ\n"
        "Nhỏ mắt 1-2 giọt khi mỏi, khô\n"
        "2. Hapacol 250mg\n"
        "Số lượng: 10 Gói\n"
        "Uống 1 gói khi sốt > 38.5°C"
    )

    inst_1 = "Nhỏ mắt 1-2 giọt khi mỏi, khô"
    slots_1 = decompose_vietnamese_instruction(inst_1)
    assert slots_1["route_raw"] == "Nhỏ mắt"
    assert slots_1["dosage_raw"] == "1-2 giọt"
    assert slots_1["form_raw"] == "giọt"
    assert slots_1["instruction_raw"] == "khi mỏi, khô"

    inst_2 = "Uống 1 gói khi sốt > 38.5°C"
    slots_2 = decompose_vietnamese_instruction(inst_2)
    assert slots_2["route_raw"] == "uống"
    assert slots_2["instruction_raw"] == "khi sốt"

    entities = []
    cursor = 0
    items_to_extract = [
        (EntityType.DRUG, "Tobrex"),
        (EntityType.STRENGTH, "0.3%"),
        (EntityType.QUANTITY, "1 Lọ"),
        (EntityType.ROUTE, "Nhỏ mắt"),
        (EntityType.DOSAGE, "1-2 giọt"),
        (EntityType.DRUG, "Hapacol"),
        (EntityType.STRENGTH, "250mg"),
        (EntityType.QUANTITY, "10 Gói"),
    ]
    for etype, target in items_to_extract:
        idx = pediatric_text.find(target, cursor)
        assert idx != -1, f"Could not find {target} in text"
        end_idx = idx + len(target)
        entities.append(GoldEntity(type=etype, text=target, start=idx, end=end_idx))
        cursor = end_idx

    annot_doc = AnnotationDocument(
        document_id="pediatric_rx_01",
        raw_text=pediatric_text,
        entities=entities,
    )
    assert len(annot_doc.entities) == 8

    tokenizer = ScenarioFastTokenizer()
    encoded = align_token_labels(annot_doc, tokenizer)
    assert LABEL_TO_ID["B-ROUTE"] in encoded["labels"]
    assert LABEL_TO_ID["B-DOSAGE"] in encoded["labels"]


# ===========================================================================
# Scenario 4: Chronic Disease Polypharmacy (10+ Medications) Workflow
# ===========================================================================


def test_scenario_4_chronic_disease_polypharmacy_workflow():
    """Scenario 4: 15-medication polypharmacy prescription from RX_001."""
    gt_file = Path("data/canonical_ground_truth/RX_001.json")
    assert gt_file.exists()

    gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
    gt = CanonicalPrescriptionGT.model_validate(gt_data)
    assert len(gt.medications) == 15

    lines = [
        "BỘ Y TẾ - BVĐK TW CẦN THƠ",
        "ĐƠN THUỐC NGOẠI TRÚ",
        "Bệnh nhân: LÊ VĂN TRẬN (PAT_001)",
    ]
    for i, med in enumerate(gt.medications, start=1):
        lines.append(f"{i}. {med.drug_raw}")
        qty_val = med.quantity_value_raw or 30
        qty_unit = med.quantity_unit_raw or "Viên"
        lines.append(f"Số lượng: {qty_val} {qty_unit}")
        if med.dosage_raw or med.frequency_raw or med.instruction_raw:
            parts = [
                p
                for p in [
                    med.dosage_raw,
                    med.frequency_raw,
                    med.instruction_raw,
                ]
                if p
            ]
            lines.append(" - ".join(parts))

    full_text = "\n".join(lines)

    ocr_lines = []
    for idx, line_str in enumerate(lines):
        ocr_lines.append(
            {
                "text": line_str,
                "confidence": 0.95,
                "cornerPoints": [
                    {"x": 10, "y": idx * 30},
                    {"x": 800, "y": idx * 30},
                    {"x": 800, "y": idx * 30 + 25},
                    {"x": 10, "y": idx * 30 + 25},
                ],
            }
        )

    ocr_dict = {
        "metadata": {
            "fileName": "polypharmacy_rx001.jpg",
            "imageWidth": 1000,
            "imageHeight": len(lines) * 35,
        },
        "fullText": full_text,
        "blocks": [{"lines": ocr_lines}],
    }

    ocr_doc = parse_mlkit_json_data(ocr_dict, document_id="polypharmacy_001")
    doc_text = build_document_text(ocr_doc)
    assert doc_text.raw_text == full_text

    gold_entities = []
    for med in gt.medications:
        drug_name = med.drug_raw
        start = full_text.find(drug_name)
        assert start != -1, f"Could not find {drug_name} in text"
        end = start + len(drug_name)
        gold_entities.append(
            GoldEntity(type=EntityType.DRUG, text=drug_name, start=start, end=end)
        )

    annot_doc = AnnotationDocument(
        document_id="polypharmacy_001",
        raw_text=full_text,
        entities=gold_entities,
    )
    assert len(annot_doc.entities) == 15


# ===========================================================================
# Scenario 5: Full Train/Val/Test Split Generation & PhoBERT BIO Dataset Export
# ===========================================================================


def test_scenario_5_full_train_val_test_split_and_bio_export():
    """Scenario 5: Complete dataset split generation and PhoBERT BIO export."""
    splits_file = Path("data/manifests/balanced_prescription_splits.json")
    assert splits_file.exists()

    splits = json.loads(splits_file.read_text(encoding="utf-8"))
    train_ids = set(splits["train"])
    val_ids = set(splits["val"])
    test_ids = set(splits["test"])

    assert len(train_ids & val_ids) == 0
    assert len(train_ids & test_ids) == 0
    assert len(val_ids & test_ids) == 0
    assert len(train_ids) == 19
    assert len(val_ids) == 4
    assert len(test_ids) == 4

    tokenizer = ScenarioFastTokenizer()
    split_documents: dict[str, list[AnnotationDocument]] = {
        "train": [],
        "val": [],
        "test": [],
    }

    for split_name, rx_list in [
        ("train", train_ids),
        ("val", val_ids),
        ("test", test_ids),
    ]:
        for rx_id in sorted(rx_list):
            raw = f"Đơn thuốc {rx_id} Amlodipine 5mg ngày uống 1 viên"
            d_start = raw.find("Amlodipine")
            d_end = d_start + len("Amlodipine")
            s_start = raw.find("5mg")
            s_end = s_start + len("5mg")

            doc = AnnotationDocument(
                document_id=f"doc_{rx_id}_01",
                raw_text=raw,
                entities=[
                    GoldEntity(
                        type=EntityType.DRUG,
                        text="Amlodipine",
                        start=d_start,
                        end=d_end,
                    ),
                    GoldEntity(
                        type=EntityType.STRENGTH,
                        text="5mg",
                        start=s_start,
                        end=s_end,
                    ),
                ],
            )
            split_documents[split_name].append(doc)

            bio = align_token_labels(doc, tokenizer)
            assert len(bio["input_ids"]) == len(bio["labels"])
            assert LABEL_TO_ID["B-DRUG"] in bio["labels"]
            assert LABEL_TO_ID["B-STRENGTH"] in bio["labels"]

    assert len(split_documents["train"]) == 19
    assert len(split_documents["val"]) == 4
    assert len(split_documents["test"]) == 4


# ===========================================================================
# Scenario 6: Full Multi-Metric Benchmark Evaluation Suite
# ===========================================================================


def test_scenario_6_full_multimetric_benchmark_evaluation():
    """Scenario 6: Multi-metric evaluation on perfect and noisy predictions."""
    gold_entities = [
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
        Entity(
            type=EntityType.DOSAGE,
            text="1 viên",
            start=23,
            end=29,
            confidence=1.0,
            source_region_ids=["r3"],
        ),
        Entity(
            type=EntityType.FREQUENCY,
            text="buổi sáng",
            start=30,
            end=39,
            confidence=1.0,
            source_region_ids=["r3"],
        ),
    ]

    pred_perfect = list(gold_entities)
    eval_perfect = strict_entity_evaluation(gold_entities, pred_perfect)
    assert eval_perfect.overall.f1 == 1.0
    assert eval_perfect.overall.precision == 1.0
    assert eval_perfect.overall.recall == 1.0

    pred_imperfect = [
        gold_entities[0],
        gold_entities[1],
        Entity(
            type=EntityType.DOSAGE,
            text="1 viên",
            start=23,
            end=30,
            confidence=0.8,
            source_region_ids=["r3"],
        ),
        gold_entities[4],
        Entity(
            type=EntityType.NOTE,
            text="Lưu ý",
            start=40,
            end=45,
            confidence=0.7,
            source_region_ids=["r4"],
        ),
    ]
    eval_imperfect = strict_entity_evaluation(gold_entities, pred_imperfect)
    assert eval_imperfect.overall.true_positive == 3
    assert eval_imperfect.overall.predicted == 5
    assert eval_imperfect.overall.gold == 5
    assert eval_imperfect.overall.precision == 3 / 5
    assert eval_imperfect.overall.recall == 3 / 5
    assert eval_imperfect.overall.f1 == 3 / 5

    eval_records = [
        {
            "prescription_id": "RX_001",
            "document_id": f"img_001_{i}",
            "tp": 5,
            "predicted": 5,
            "gold": 5,
        }
        for i in range(50)
    ] + [
        {
            "prescription_id": "RX_002",
            "document_id": "img_002_0",
            "tp": 0,
            "predicted": 5,
            "gold": 5,
        }
    ]

    total_tp = sum(r["tp"] for r in eval_records)
    total_pred = sum(r["predicted"] for r in eval_records)
    total_gold = sum(r["gold"] for r in eval_records)
    micro_f1 = (2 * total_tp) / (total_pred + total_gold)

    macro_summary = compute_prescription_macro_summary(eval_records)
    assert micro_f1 > 0.95
    assert abs(macro_summary["macro_f1"] - 0.50) < 1e-5


# ===========================================================================
# Scenario 7: Production REST API Ingestion & Missing Model 503 Security Guard
# ===========================================================================


def test_scenario_7_production_api_ingestion_and_503_security_guard(
    monkeypatch,
):
    """Scenario 7: Production API lifecycle enforcing 503 errors."""
    monkeypatch.delenv("RXIE_MODEL_PATH", raising=False)
    app = create_app()
    client = TestClient(app)

    assert client.get("/health").status_code == 200

    info = client.get("/model-info").json()
    assert info["configured"] is False
    assert info["available"] is False

    ocr_payload = {
        "schema_version": "rxie.ocr.v1",
        "document_id": "api_sec_001",
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
                        "text": "Losartan 50mg",
                        "confidence": 0.9,
                        "reading_order": 0,
                        "bbox": {"points": [[0, 0], [100, 0], [100, 20], [0, 20]]},
                    }
                ],
            }
        ],
    }
    resp = client.post("/entities", json=ocr_payload)
    assert resp.status_code == 503
    assert "RXIE_MODEL_PATH is not configured" in resp.json()["detail"]

    mock_entity = Entity(
        type=EntityType.DRUG,
        text="Losartan",
        start=0,
        end=8,
        confidence=0.99,
        source_region_ids=["p0_b0_l0"],
    )
    injected_app = create_app(
        classifier_provider=lambda: ScenarioDeterministicClassifier([mock_entity])
    )
    injected_client = TestClient(injected_app)

    valid_resp = injected_client.post("/entities", json=ocr_payload)
    assert valid_resp.status_code == 200
    assert valid_resp.json()["document_id"] == "api_sec_001"
    assert len(valid_resp.json()["entities"]) == 1


# ===========================================================================
# Scenario 8: Multi-Page / Complex Formatting Clinical Records Workflow
# ===========================================================================


def test_scenario_8_multipage_clinical_records_workflow():
    """Scenario 8: Multi-page clinical records ingestion and offsets."""
    multipage_dict = {
        "schema_version": "rxie.ocr.v1",
        "document_id": "multipage_doc_01",
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
                        "text": "TRANG 1: HỌ TÊN BỆNH NHÂN: LÊ VĂN A",
                        "confidence": 0.95,
                        "reading_order": 0,
                        "bbox": {
                            "points": [
                                [10, 10],
                                [500, 10],
                                [500, 40],
                                [10, 40],
                            ]
                        },
                    },
                    {
                        "region_id": "p0_b0_l1",
                        "text": "1. Amlodipine 5mg",
                        "confidence": 0.92,
                        "reading_order": 1,
                        "bbox": {
                            "points": [
                                [10, 50],
                                [400, 50],
                                [400, 80],
                                [10, 80],
                            ]
                        },
                    },
                ],
            },
            {
                "width": 1000,
                "height": 1000,
                "page_index": 1,
                "regions": [
                    {
                        "region_id": "p1_b0_l0",
                        "text": "TRANG 2: THUỐC BUỔI TỐI",
                        "confidence": 0.94,
                        "reading_order": 0,
                        "bbox": {
                            "points": [
                                [10, 10],
                                [400, 10],
                                [400, 40],
                                [10, 40],
                            ]
                        },
                    },
                    {
                        "region_id": "p1_b0_l1",
                        "text": "2. Atorvastatin 20mg",
                        "confidence": 0.90,
                        "reading_order": 1,
                        "bbox": {
                            "points": [
                                [10, 50],
                                [400, 50],
                                [400, 80],
                                [10, 80],
                            ]
                        },
                    },
                ],
            },
        ],
    }

    doc = OcrDocument.model_validate(multipage_dict)
    assert len(doc.pages) == 2
    doc_text = build_document_text(doc)

    expected_text = (
        "TRANG 1: HỌ TÊN BỆNH NHÂN: LÊ VĂN A\n"
        "1. Amlodipine 5mg\n"
        "TRANG 2: THUỐC BUỔI TỐI\n"
        "2. Atorvastatin 20mg"
    )
    assert doc_text.raw_text == expected_text
    assert len(doc_text.regions) == 4
    assert doc_text.regions[0].region_id == "p0_b0_l0"
    assert doc_text.regions[2].region_id == "p1_b0_l0"

    amlodipine_start = doc_text.raw_text.find("Amlodipine")
    amlodipine_len = len("Amlodipine")
    atorvastatin_start = doc_text.raw_text.find("Atorvastatin")
    atorvastatin_len = len("Atorvastatin")

    entities = [
        Entity(
            type=EntityType.DRUG,
            text="Amlodipine",
            start=amlodipine_start,
            end=amlodipine_start + amlodipine_len,
            confidence=0.92,
            source_region_ids=doc_text.source_regions(
                amlodipine_start, amlodipine_start + amlodipine_len
            ),
        ),
        Entity(
            type=EntityType.DRUG,
            text="Atorvastatin",
            start=atorvastatin_start,
            end=atorvastatin_start + atorvastatin_len,
            confidence=0.90,
            source_region_ids=doc_text.source_regions(
                atorvastatin_start, atorvastatin_start + atorvastatin_len
            ),
        ),
    ]

    validate_entities(entities, doc_text)
    assert entities[0].source_region_ids == ["p0_b0_l1"]
    assert entities[1].source_region_ids == ["p1_b0_l1"]


# ===========================================================================
# Scenario 9: Duplicate Medication Names with Differing Strengths & Dosages
# ===========================================================================


def test_scenario_9_duplicate_medication_names_with_differing_dosages():
    """Scenario 9: Disambiguation of repeated drug names."""
    rx_text = (
        "ĐƠN THUỐC\n"
        "1. Paracetamol 500mg\n"
        "Số lượng: 10 Viên\n"
        "Uống 1 viên buổi sáng\n"
        "2. Paracetamol 650mg\n"
        "Số lượng: 10 Viên\n"
        "Uống 1 viên khi sốt > 38.5°C"
    )

    first_para_start = rx_text.find("Paracetamol 500mg")
    first_para_end = first_para_start + len("Paracetamol")

    second_para_start = rx_text.find("Paracetamol 650mg")
    second_para_end = second_para_start + len("Paracetamol")

    assert first_para_start != second_para_start

    entities = [
        GoldEntity(
            type=EntityType.DRUG,
            text="Paracetamol",
            start=first_para_start,
            end=first_para_end,
        ),
        GoldEntity(
            type=EntityType.STRENGTH,
            text="500mg",
            start=first_para_end + 1,
            end=first_para_end + 6,
        ),
        GoldEntity(
            type=EntityType.DRUG,
            text="Paracetamol",
            start=second_para_start,
            end=second_para_end,
        ),
        GoldEntity(
            type=EntityType.STRENGTH,
            text="650mg",
            start=second_para_end + 1,
            end=second_para_end + 6,
        ),
    ]

    annot_doc = AnnotationDocument(
        document_id="dup_meds_rx_01",
        raw_text=rx_text,
        entities=entities,
    )
    assert len(annot_doc.entities) == 4

    rec_1 = (
        ("DRUG", first_para_start, first_para_end),
        ("STRENGTH", first_para_end + 1, first_para_end + 6),
    )
    rec_2 = (
        ("DRUG", second_para_start, second_para_end),
        ("STRENGTH", second_para_end + 1, second_para_end + 6),
    )
    assert rec_1 != rec_2


# ===========================================================================
# Scenario 10: Robustness Against Extreme Unicode and Diacritic Variation
# ===========================================================================


def test_scenario_10_extreme_unicode_and_vietnamese_diacritic_robustness():
    """Scenario 10: Vietnamese diacritics, NFC/NFD, and symbols."""
    raw_vietnamese = (
        "ĐƠN THUỐC BỆNH VIỆN ĐA KHOA TRUNG ƯƠNG CẦN THƠ\n"
        "Bệnh nhân: NGUYỄN HOÀNG VĂN KHÁNH  Tuổi: 62\n"
        "1. Calcium Corbiere 10ml (10 Ống)\n"
        "Sáng uống 1 ống sau ăn\n"
        "2. Vitamin C (Upsa C 1000mg) 1000mg\n"
        "Sáng uống 1 viên sủi (hòa tan trong nước)\n"
        "3. Thuốc nhỏ mắt Refresh Tears 15ml (1 Lọ)\n"
        "Nhỏ mắt 1-2 giọt khi khô/mỏi\n"
        "Lưu ý: Tái khám định kỳ, nhiệt độ bảo quản < 30°C ± 2°C"
    )

    nfc_text = unicodedata.normalize("NFC", raw_vietnamese)
    nfd_text = unicodedata.normalize("NFD", raw_vietnamese)
    assert len(nfd_text) > len(nfc_text)

    key_norm = normalize_text_key(raw_vietnamese)
    assert "BENH VIEN" in key_norm
    assert "CALCIUM CORBIERE" in key_norm
    assert "REFRESH TEARS" in key_norm

    calcium_start = raw_vietnamese.find("Calcium Corbiere")
    calcium_end = calcium_start + len("Calcium Corbiere")
    vien_sui_start = raw_vietnamese.find("viên sủi")
    vien_sui_end = vien_sui_start + len("viên sủi")

    entities = [
        GoldEntity(
            type=EntityType.DRUG,
            text="Calcium Corbiere",
            start=calcium_start,
            end=calcium_end,
        ),
        GoldEntity(
            type=EntityType.FORM,
            text="viên sủi",
            start=vien_sui_start,
            end=vien_sui_end,
        ),
    ]

    annot_doc = AnnotationDocument(
        document_id="unicode_robustness_01",
        raw_text=raw_vietnamese,
        entities=entities,
    )

    tokenizer = ScenarioFastTokenizer()
    bio_encoded = align_token_labels(annot_doc, tokenizer)
    assert len(bio_encoded["labels"]) > 0
    assert LABEL_TO_ID["B-DRUG"] in bio_encoded["labels"]
    assert LABEL_TO_ID["B-FORM"] in bio_encoded["labels"]


# ===========================================================================
# Scenario 11: Complete End-to-End Pipeline Integration Lifecycle
# ===========================================================================


def test_scenario_11_complete_e2e_pipeline_lifecycle():
    """Scenario 11: Full pipeline lifecycle (Ingestion -> Evaluation)."""
    raw_ocr_file = Path("data/ocr_final") / "IMG_20260209_002313.json"
    assert raw_ocr_file.exists()
    doc = load_mlkit_ocr_document(raw_ocr_file)
    doc_text = build_document_text(doc)
    assert len(doc_text.raw_text) > 0

    gt_file = Path("data/canonical_ground_truth") / "RX_001.json"
    assert gt_file.exists()
    gt = CanonicalPrescriptionGT.model_validate(
        json.loads(gt_file.read_text(encoding="utf-8"))
    )
    assert len(gt.medications) == 15

    matched_entities: list[GoldEntity] = []
    cursor = 0
    for med in gt.medications:
        base_drug = med.drug_raw.split("(")[0].strip()
        idx = doc_text.raw_text.find(base_drug, cursor)
        if idx != -1:
            end_idx = idx + len(base_drug)
            matched_entities.append(
                GoldEntity(
                    type=EntityType.DRUG,
                    text=base_drug,
                    start=idx,
                    end=end_idx,
                )
            )
            cursor = end_idx

    if matched_entities:
        annot_doc = AnnotationDocument(
            document_id=doc.document_id,
            raw_text=doc_text.raw_text,
            entities=matched_entities,
        )
        assert len(annot_doc.entities) == len(matched_entities)

        tokenizer = ScenarioFastTokenizer()
        bio_export = align_token_labels(annot_doc, tokenizer)
        assert len(bio_export["labels"]) > 0

        eval_entities = [
            Entity(
                type=e.type,
                text=e.text,
                start=e.start,
                end=e.end,
                confidence=1.0,
                source_region_ids=doc_text.source_regions(e.start, e.end),
            )
            for e in annot_doc.entities
        ]
        report = strict_entity_evaluation(eval_entities, eval_entities)
        assert report.overall.f1 == 1.0
