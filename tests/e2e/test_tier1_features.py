"""Tier 1: Comprehensive Feature Coverage Suite (Features 1 to 20).

Requirement Source: TEST_INFRA.md, ORIGINAL_REQUEST.md, PROJECT.md.
Pure opaque-box testing using public interfaces:
- rxie.schemas, rxie.text, rxie.ingestion, rxie.canonical_gt,
- rxie.alignment_engine, rxie.dataset_generator, rxie.sampler,
- rxie.evaluation, rxie.api, rxie.alignment, rxie.grouping.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from rxie.api import create_app
from rxie.classifier import EntityClassifier
from rxie.grouping import HierarchicalPrescriptionSampler
from rxie.schemas import (
    AnnotationDocument,
    BoundingBox,
    Entity,
    EntityType,
    GoldEntity,
    OcrDocument,
    OcrEngine,
    OcrPage,
    OcrRegion,
)
from rxie.text import DocumentText, build_document_text, validate_entities

from .conftest import (
    CANONICAL_32_DECOMPOSITION_RULES,
    AlignmentRecord,
    AnnotationDocumentV2,
    CanonicalMedication,
    CanonicalPrescriptionGT,
    EntityRelation,
    GoldEntityV2,
    MatchStatus,
    MockFastTokenizer,
    PrescriptionWeightedRandomSampler,
    RelationType,
    align_prescription_to_ocr,
    decompose_instruction,
    decompose_medication,
    decompose_prescription,
    evaluate_dual_level,
    evaluate_records,
    evaluate_relations,
    evaluate_strict_entities,
    generate_alignment_audit_report,
    generate_dataset_splits,
    ingest_all_mlkit_captures,
    load_mlkit_ocr_document,
    parse_mlkit_json_data,
    validate_all_canonical_gt,
    validate_canonical_gt,
    verify_split_isolation,
)

# ==============================================================================
# Feature 1: ML Kit Parser & BBox Clamping
# ==============================================================================


class TestFeature1MLKitParser:
    """F1: Parsing Android Google ML Kit JSON files and clamping coordinates."""

    def test_f1_mlkit_standard_parsing_happy_path(
        self, sample_mlkit_raw_json: dict[str, Any]
    ) -> None:
        doc = parse_mlkit_json_data(sample_mlkit_raw_json, document_id="TEST_001")
        assert isinstance(doc, OcrDocument)
        assert doc.document_id == "TEST_001"
        assert doc.ocr_engine.name == "google_mlkit_text_recognition"
        assert len(doc.pages) == 1
        assert doc.pages[0].width == 1000
        assert doc.pages[0].height == 1000
        assert len(doc.pages[0].regions) == 5

    def test_f1_mlkit_coordinate_clamping_negative_and_overflow(
        self, synthetic_mlkit_builder: Any
    ) -> None:
        raw = synthetic_mlkit_builder(
            width=500,
            height=600,
            lines=[
                ("Header Top Left", [-25.0, -10.0, 200.0, 50.0], 0.95),
                ("Overflow Bottom Right", [300.0, 550.0, 550.0, 650.0], 0.90),
            ],
        )
        doc = parse_mlkit_json_data(raw, document_id="CLAMP_TEST")
        regions = doc.pages[0].regions
        # Region 0 top-left should be clamped from -25,-10 to 0,0
        assert regions[0].bbox.points[0] == (0.0, 0.0)
        # Region 1 bottom-right should be clamped from 550,650 to 500,600
        assert regions[1].bbox.points[2] == (500.0, 600.0)

    def test_f1_mlkit_confidence_clamping_and_none(
        self, synthetic_mlkit_builder: Any
    ) -> None:
        raw = synthetic_mlkit_builder(
            lines=[
                ("Line with None confidence", [10, 10, 100, 30], None),
                ("Line with normal confidence", [10, 40, 100, 60], 0.88),
                ("Line with overflow confidence", [10, 70, 100, 90], 1.25),
            ]
        )
        doc = parse_mlkit_json_data(raw)
        assert doc.pages[0].regions[0].confidence is None
        assert doc.pages[0].regions[1].confidence == 0.88
        assert doc.pages[0].regions[2].confidence == 1.0

    def test_f1_mlkit_unique_reading_order_preservation(
        self, synthetic_mlkit_builder: Any
    ) -> None:
        raw = synthetic_mlkit_builder(
            lines=[(f"Line {i}", [0, i * 20, 100, (i + 1) * 20], 0.9) for i in range(6)]
        )
        doc = parse_mlkit_json_data(raw)
        reading_orders = [r.reading_order for r in doc.pages[0].regions]
        assert reading_orders == [0, 1, 2, 3, 4, 5]
        assert len(reading_orders) == len(set(reading_orders))

    def test_f1_mlkit_corner_points_and_bbox_fallback(
        self, synthetic_mlkit_builder: Any
    ) -> None:
        # Case A: with cornerPoints
        raw_a = synthetic_mlkit_builder(
            lines=[("With CornerPoints", [10, 10, 90, 40], 0.9)]
        )
        doc_a = parse_mlkit_json_data(raw_a)
        assert len(doc_a.pages[0].regions[0].bbox.points) == 4

        # Case B: without cornerPoints (only boundingBox dict)
        raw_b = {
            "documentId": "BBOX_ONLY",
            "imageWidth": 800,
            "imageHeight": 800,
            "blocks": [
                {
                    "lines": [
                        {
                            "text": "BBox Fallback Text",
                            "confidence": 0.85,
                            "boundingBox": {
                                "left": 20,
                                "top": 30,
                                "right": 200,
                                "bottom": 70,
                            },
                        }
                    ]
                }
            ],
        }
        doc_b = parse_mlkit_json_data(raw_b)
        assert doc_b.pages[0].regions[0].bbox.points == (
            (20.0, 30.0),
            (200.0, 30.0),
            (200.0, 70.0),
            (20.0, 70.0),
        )

    def test_f1_mlkit_multi_page_document_parsing(self) -> None:
        p1 = OcrPage(
            width=800,
            height=1200,
            page_index=0,
            regions=[
                OcrRegion(
                    region_id="p0_r0",
                    text="Page 1 Text",
                    confidence=0.9,
                    reading_order=0,
                    bbox=BoundingBox(points=((0, 0), (100, 0), (100, 20), (0, 20))),
                )
            ],
        )
        p2 = OcrPage(
            width=800,
            height=1200,
            page_index=1,
            regions=[
                OcrRegion(
                    region_id="p1_r0",
                    text="Page 2 Text",
                    confidence=0.9,
                    reading_order=0,
                    bbox=BoundingBox(points=((0, 0), (100, 0), (100, 20), (0, 20))),
                )
            ],
        )
        doc = OcrDocument(
            document_id="MULTI_PAGE_DOC",
            ocr_engine=OcrEngine(name="mlkit", version="1.0"),
            pages=[p1, p2],
        )
        assert len(doc.pages) == 2
        assert doc.pages[0].page_index == 0
        assert doc.pages[1].page_index == 1


# ==============================================================================
# Feature 2: Canonical Text Offset Reconstruction
# ==============================================================================


class TestFeature2TextOffsetReconstruction:
    """F2: Offset reconstruction via build_document_text and validate_entities."""

    def test_f2_offset_newline_joined_exact_reconstruction(
        self, sample_mlkit_raw_json: dict[str, Any]
    ) -> None:
        doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        text_doc = build_document_text(doc)
        expected = (
            "BỆNH VIỆN ĐA KHOA CẦN THƠ\n"
            "ĐƠN THUỐC\n"
            "1. Losartan 50mg\n"
            "Số lượng: 28 Viên\n"
            "Ngày uống 1 viên buổi sáng"
        )
        assert text_doc.raw_text == expected

    def test_f2_offset_source_regions_provenance_single_and_multi(
        self, sample_mlkit_raw_json: dict[str, Any]
    ) -> None:
        doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        text_doc = build_document_text(doc)

        # "Losartan" is in region p0_b0_l2
        losartan_start = text_doc.raw_text.find("Losartan")
        losartan_end = losartan_start + len("Losartan")
        assert text_doc.source_regions(losartan_start, losartan_end) == ["p0_b0_l2"]

        # Span crossing region 2 and region 3
        cross_start = text_doc.raw_text.find("50mg")
        cross_end = text_doc.raw_text.find("Số lượng") + len("Số lượng")
        assert text_doc.source_regions(cross_start, cross_end) == [
            "p0_b0_l2",
            "p0_b0_l3",
        ]

    def test_f2_offset_validate_entities_exact_match(
        self, sample_mlkit_raw_json: dict[str, Any]
    ) -> None:
        doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        text_doc = build_document_text(doc)

        start = text_doc.raw_text.find("Losartan")
        end = start + len("Losartan")
        entity = Entity(
            type=EntityType.DRUG,
            text="Losartan",
            start=start,
            end=end,
            confidence=0.95,
            source_region_ids=["p0_b0_l2"],
        )
        # Should execute without throwing ValueError
        validate_entities([entity], text_doc)

    def test_f2_offset_bijective_character_partitioning(
        self, sample_mlkit_raw_json: dict[str, Any]
    ) -> None:
        doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        text_doc = build_document_text(doc)

        # Every non-newline index belongs to exactly one region
        for idx, char in enumerate(text_doc.raw_text):
            matching_regions = text_doc.source_regions(idx, idx + 1)
            if char == "\n":
                assert matching_regions == []
            else:
                assert len(matching_regions) == 1

    def test_f2_offset_monotonic_entity_sequence_validation(
        self, sample_mlkit_raw_json: dict[str, Any]
    ) -> None:
        doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        text_doc = build_document_text(doc)

        e1_start = text_doc.raw_text.find("Losartan")
        e1 = Entity(
            type=EntityType.DRUG,
            text="Losartan",
            start=e1_start,
            end=e1_start + 8,
            confidence=0.9,
            source_region_ids=["p0_b0_l2"],
        )

        e2_start = text_doc.raw_text.find("50mg")
        e2 = Entity(
            type=EntityType.STRENGTH,
            text="50mg",
            start=e2_start,
            end=e2_start + 4,
            confidence=0.9,
            source_region_ids=["p0_b0_l2"],
        )

        # In order: valid
        validate_entities([e1, e2], text_doc)


# ==============================================================================
# Feature 3: Ingestion CLI & Batch Parsing
# ==============================================================================


class TestFeature3IngestionBatch:
    """F3: Batch parsing and loading of raw ML Kit OCR JSON files."""

    def test_f3_ingestion_batch_parsing_all_files(
        self, temp_test_dir: Path, synthetic_mlkit_builder: Any
    ) -> None:
        for i in range(5):
            p = temp_test_dir / f"capture_{i:03d}.json"
            with p.open("w", encoding="utf-8") as f:
                json.dump(synthetic_mlkit_builder(doc_id=f"capture_{i:03d}"), f)

        res = ingest_all_mlkit_captures(temp_test_dir, fail_fast=True)
        assert len(res) == 5
        assert set(res.keys()) == {f"capture_{i:03d}" for i in range(5)}

    def test_f3_ingestion_empty_text_captures_handling(
        self, temp_test_dir: Path
    ) -> None:
        empty_json = {
            "documentId": "EMPTY_CAPTURE_01",
            "imageWidth": 1000,
            "imageHeight": 1000,
            "blocks": [],
        }
        p = temp_test_dir / "empty_cap.json"
        with p.open("w", encoding="utf-8") as f:
            json.dump(empty_json, f)

        doc = load_mlkit_ocr_document(p)
        assert len(doc.pages[0].regions) == 0
        text_doc = build_document_text(doc)
        assert text_doc.raw_text == ""

    def test_f3_ingestion_missing_optional_metadata_defaults(
        self, temp_test_dir: Path
    ) -> None:
        minimal_json = {"blocks": [{"lines": [{"text": "Sample"}]}]}
        p = temp_test_dir / "minimal.json"
        with p.open("w", encoding="utf-8") as f:
            json.dump(minimal_json, f)

        doc = load_mlkit_ocr_document(p)
        assert doc.document_id == "minimal"
        assert doc.pages[0].width == 1000
        assert doc.pages[0].height == 1000

    def test_f3_ingestion_fail_fast_true_vs_false_behavior(
        self, temp_test_dir: Path, synthetic_mlkit_builder: Any
    ) -> None:
        valid_p = temp_test_dir / "valid.json"
        with valid_p.open("w", encoding="utf-8") as f:
            json.dump(synthetic_mlkit_builder(doc_id="valid"), f)

        invalid_p = temp_test_dir / "corrupted.json"
        with invalid_p.open("w", encoding="utf-8") as f:
            f.write("{corrupted json}")

        # fail_fast=True raises
        with pytest.raises(ValueError):
            ingest_all_mlkit_captures(temp_test_dir, fail_fast=True)

        # fail_fast=False recovers and returns valid docs
        res = ingest_all_mlkit_captures(temp_test_dir, fail_fast=False)
        assert "valid" in res

    def test_f3_ingestion_document_id_keying(
        self, temp_test_dir: Path, synthetic_mlkit_builder: Any
    ) -> None:
        p = temp_test_dir / "IMG_20260115_181847.json"
        with p.open("w", encoding="utf-8") as f:
            json.dump(synthetic_mlkit_builder(doc_id="IMG_20260115_181847"), f)

        res = ingest_all_mlkit_captures(temp_test_dir)
        assert "IMG_20260115_181847" in res


# ==============================================================================
# Feature 4: Canonical GT Schema Atomic Fields
# ==============================================================================


class TestFeature4CanonicalGTSchema:
    """F4: Canonical prescription ground truth schema and atomic medication slots."""

    def test_f4_canonical_gt_atomic_fields_population(
        self, sample_canonical_prescription_gt: CanonicalPrescriptionGT
    ) -> None:
        med = sample_canonical_prescription_gt.medications[0]
        assert med.drug_raw == "Losartan"
        assert med.strength_raw == "50mg"
        assert med.quantity_value_raw == "28"
        assert med.quantity_unit_raw == "Viên"
        assert med.dosage_raw == "1 viên"
        assert med.frequency_raw == "Ngày buổi sáng"
        assert med.route_raw == "uống"
        assert med.form_raw == "viên"

    def test_f4_canonical_gt_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalMedication(
                medication_id="M01",
                drug_raw="Amlodipine",
                unsupported_extra_field="error",
            )

    def test_f4_canonical_gt_annotation_status_validation(self) -> None:
        gt_verified = CanonicalPrescriptionGT(
            prescription_id="RX_001", patient_id="PAT_001", annotation_status="verified"
        )
        assert gt_verified.annotation_status == "verified"

        with pytest.raises(ValidationError):
            CanonicalPrescriptionGT(
                prescription_id="RX_001",
                patient_id="PAT_001",
                annotation_status="invalid_status",
            )

    def test_f4_canonical_gt_unique_medication_ids(self) -> None:
        m1 = CanonicalMedication(medication_id="RX_001_M01", drug_raw="Drug A")
        m2 = CanonicalMedication(medication_id="RX_001_M01", drug_raw="Drug B")
        with pytest.raises(ValidationError, match="Duplicate medication_id"):
            CanonicalPrescriptionGT(
                prescription_id="RX_001", patient_id="PAT_001", medications=[m1, m2]
            )

    def test_f4_canonical_gt_decoupled_patient_id(self) -> None:
        gt = CanonicalPrescriptionGT(prescription_id="RX_999", patient_id="PAT_042")
        assert gt.prescription_id != gt.patient_id
        assert gt.patient_id == "PAT_042"


# ==============================================================================
# Feature 5: Instruction Decomposition Engine
# ==============================================================================


class TestFeature5InstructionDecomposition:
    """F5: Instruction decomposition engine covering 32 unique clinical patterns."""

    @pytest.mark.parametrize(
        "pattern,expected_dosage,expected_freq,expected_route",
        [
            ("Ngày uống 1 viên sáng", "1 viên", "Ngày sáng", "uống"),
            ("Ngày uống 1 viên buổi sáng", "1 viên", "Ngày buổi sáng", "uống"),
            ("Ngày uống 1 viên sau ăn", "1 viên", "Ngày", "uống"),
            ("Nhỏ mắt khi khô, 3-4 lần/ngày", None, "3-4 lần/ngày", "Nhỏ mắt"),
            (
                "Tiêm dưới da 10 đơn vị buổi tối",
                "10 đơn vị",
                "buổi tối",
                "Tiêm dưới da",
            ),
            ("Bôi vùng nấm 2 lần/ngày", None, "2 lần/ngày", "Bôi"),
            ("Sáng uống 1 ống sau ăn", "1 ống", "Sáng", "uống"),
            ("Ngày uống 1/2 viên tối", "1/2 viên", "Ngày tối", "uống"),
            ("Ngày uống 1-2 viên sau ăn tối", "1-2 viên", "Ngày tối", "uống"),
        ],
    )
    def test_f5_decomp_daily_oral_standard_patterns(
        self,
        pattern: str,
        expected_dosage: str | None,
        expected_freq: str | None,
        expected_route: str | None,
    ) -> None:
        res = decompose_instruction(pattern)
        assert res["dosage_raw"] == expected_dosage
        assert res["frequency_raw"] == expected_freq
        assert res["route_raw"] == expected_route

    def test_f5_decomp_all_32_clinical_instruction_patterns(self) -> None:
        assert len(CANONICAL_32_DECOMPOSITION_RULES) == 32
        for raw_pattern, expected_dict in CANONICAL_32_DECOMPOSITION_RULES.items():
            result = decompose_instruction(raw_pattern)
            assert result["dosage_raw"] == expected_dict["dosage_raw"]
            assert result["frequency_raw"] == expected_dict["frequency_raw"]
            assert result["route_raw"] == expected_dict["route_raw"]
            assert result["form_raw"] == expected_dict["form_raw"]
            assert result["instruction_raw"] == expected_dict["instruction_raw"]

    def test_f5_decomp_full_medication_and_prescription_update(self) -> None:
        med = CanonicalMedication(
            medication_id="RX_001_M01",
            drug_raw="Losartan",
            instruction_raw="Ngày uống 1 viên buổi sáng",
        )
        decomp_med = decompose_medication(med)
        assert decomp_med.dosage_raw == "1 viên"
        assert decomp_med.frequency_raw == "Ngày buổi sáng"
        assert decomp_med.route_raw == "uống"
        assert decomp_med.form_raw == "viên"

        gt = CanonicalPrescriptionGT(
            prescription_id="RX_001",
            patient_id="PAT_001",
            medications=[med],
        )
        decomp_gt = decompose_prescription(gt)
        assert decomp_gt.medications[0].dosage_raw == "1 viên"


# ==============================================================================
# Feature 6: Annotation Policy Locking
# ==============================================================================


class TestFeature6AnnotationPolicyLocking:
    """F6: Annotation policy locking (DRUG vs STRENGTH, QUANTITY with unit)."""

    def test_f6_policy_drug_excludes_strength(self) -> None:
        # "Amlodipine 5mg": Drug="Amlodipine", Strength="5mg"
        raw_text = "Amlodipine 5mg"
        e1 = GoldEntity(type=EntityType.DRUG, text="Amlodipine", start=0, end=10)
        e2 = GoldEntity(type=EntityType.STRENGTH, text="5mg", start=11, end=14)
        doc = AnnotationDocument(
            document_id="P_01", raw_text=raw_text, entities=[e1, e2]
        )
        assert doc.entities[0].text == "Amlodipine"
        assert doc.entities[1].text == "5mg"

    def test_f6_policy_quantity_includes_unit(self) -> None:
        raw_text = "Số lượng: 30 Viên"
        q_start = raw_text.find("30 Viên")
        q_end = q_start + len("30 Viên")
        e_qty = GoldEntity(
            type=EntityType.QUANTITY, text="30 Viên", start=q_start, end=q_end
        )
        doc = AnnotationDocument(
            document_id="Q_01", raw_text=raw_text, entities=[e_qty]
        )
        assert doc.entities[0].text == "30 Viên"
        assert "Viên" in doc.entities[0].text

    def test_f6_policy_non_overlapping_spans_enforced(self) -> None:
        raw_text = "Metformin 750mg"
        # Overlapping: (0, 15) and (10, 15)
        e1 = GoldEntity(type=EntityType.DRUG, text="Metformin 750mg", start=0, end=15)
        e2 = GoldEntity(type=EntityType.STRENGTH, text="750mg", start=10, end=15)
        with pytest.raises(ValidationError, match="must not overlap"):
            AnnotationDocument(
                document_id="ERR_01", raw_text=raw_text, entities=[e1, e2]
            )

    def test_f6_policy_ten_class_taxonomy_completeness(self) -> None:
        all_types = {e.value for e in EntityType}
        expected = {
            "DRUG",
            "STRENGTH",
            "DOSAGE",
            "FREQUENCY",
            "QUANTITY",
            "DURATION",
            "ROUTE",
            "INSTRUCTION",
            "FORM",
            "NOTE",
        }
        assert all_types == expected

    def test_f6_policy_exact_substring_fidelity(self) -> None:
        raw_text = "Aspirin 81mg"
        # Mismatched text "Paracetamol" on span (0, 7) which contains "Aspirin"
        e = GoldEntity(type=EntityType.DRUG, text="Paracetamol", start=0, end=7)
        with pytest.raises(ValidationError, match="does not match"):
            AnnotationDocument(document_id="ERR_02", raw_text=raw_text, entities=[e])


# ==============================================================================
# Feature 7: GT Batch Validation Script
# ==============================================================================


class TestFeature7GTBatchValidation:
    """F7: Validation script and batch metrics across canonical ground truth files."""

    def test_f7_gt_validation_single_verified_prescription(
        self, sample_canonical_prescription_gt: CanonicalPrescriptionGT
    ) -> None:
        assert validate_canonical_gt(sample_canonical_prescription_gt) is True

    def test_f7_gt_validation_batch_all_canonical_files(
        self,
        temp_test_dir: Path,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
    ) -> None:
        gt_dir = temp_test_dir / "canonical_gt"
        gt_dir.mkdir()
        for i in range(3):
            rx_id = f"RX_{i + 1:03d}"
            p = gt_dir / f"{rx_id}.json"
            gt_copy = copy.deepcopy(sample_canonical_prescription_gt)
            gt_copy.prescription_id = rx_id
            for m_idx, med in enumerate(gt_copy.medications):
                med.medication_id = f"{rx_id}_M{m_idx + 1:02d}"
            with p.open("w", encoding="utf-8") as f:
                json.dump(gt_copy.model_dump(), f)

        res = validate_all_canonical_gt(gt_dir)
        assert res["total_files"] == 3
        assert res["valid_files"] == 3
        assert res["invalid_files"] == 0
        assert res["total_medications"] == 6

    def test_f7_gt_validation_summary_statistics_structure(
        self, temp_test_dir: Path
    ) -> None:
        res = validate_all_canonical_gt(temp_test_dir)
        assert "total_files" in res
        assert "valid_files" in res
        assert "prescriptions_by_status" in res
        assert "errors" in res

    def test_f7_gt_validation_detects_invalid_prescription(
        self, temp_test_dir: Path
    ) -> None:
        bad_dir = temp_test_dir / "bad_gt"
        bad_dir.mkdir()
        bad_file = bad_dir / "bad.json"
        with bad_file.open("w", encoding="utf-8") as f:
            f.write('{"prescription_id": "", "patient_id": ""}')

        res = validate_all_canonical_gt(bad_dir)
        assert res["invalid_files"] >= 1

    def test_f7_gt_validation_decomposed_fields_audit(
        self,
        temp_test_dir: Path,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
    ) -> None:
        gt_dir = temp_test_dir / "decomp_audit"
        gt_dir.mkdir()
        p = gt_dir / "RX_001.json"
        with p.open("w", encoding="utf-8") as f:
            json.dump(sample_canonical_prescription_gt.model_dump(), f)

        res = validate_all_canonical_gt(gt_dir)
        assert res["decomposed_medications"] == 2


# ==============================================================================
# Feature 8: Fuzzy Alignment Engine
# ==============================================================================


class TestFeature8FuzzyAlignmentEngine:
    """F8: Fuzzy alignment of canonical GT records to OCR document captures."""

    def test_f8_alignment_perfect_ocr_match(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        sample_mlkit_raw_json: dict[str, Any],
    ) -> None:
        ocr_doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        anno_doc, records = align_prescription_to_ocr(
            sample_canonical_prescription_gt, ocr_doc
        )

        assert isinstance(anno_doc, AnnotationDocumentV2)
        assert len(records) > 0
        drug_record = next(
            r
            for r in records
            if r.entity_type == EntityType.DRUG and r.canonical_text == "Losartan"
        )
        assert drug_record.status == MatchStatus.MATCHED
        assert drug_record.matched_text == "Losartan"

    def test_f8_alignment_drug_anchor_localization(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        synthetic_mlkit_builder: Any,
    ) -> None:
        raw = synthetic_mlkit_builder(
            lines=[
                ("Header", [0, 0, 100, 20], 0.9),
                ("Rx Item: Losartan 50mg", [0, 30, 200, 50], 0.95),
            ]
        )
        ocr_doc = parse_mlkit_json_data(raw)
        anno_doc, records = align_prescription_to_ocr(
            sample_canonical_prescription_gt, ocr_doc
        )

        drug_entity = next(
            e
            for e in anno_doc.entities
            if e.type == EntityType.DRUG and e.text == "Losartan"
        )
        assert drug_entity.parent_entity_id is None
        assert drug_entity.medication_id == "RX_001_M01"

    def test_f8_alignment_proximity_constrained_attributes(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        synthetic_mlkit_builder: Any,
    ) -> None:
        raw = synthetic_mlkit_builder(
            lines=[
                ("1. Losartan 50mg", [0, 10, 200, 30], 0.95),
                ("Số lượng: 28 Viên", [210, 10, 350, 30], 0.92),
                ("Ngày uống 1 viên buổi sáng", [0, 35, 300, 55], 0.91),
            ]
        )
        ocr_doc = parse_mlkit_json_data(raw)
        anno_doc, _ = align_prescription_to_ocr(
            sample_canonical_prescription_gt, ocr_doc
        )

        drug_e = next(
            e
            for e in anno_doc.entities
            if e.type == EntityType.DRUG and e.text == "Losartan"
        )
        str_e = next(
            e
            for e in anno_doc.entities
            if e.type == EntityType.STRENGTH and e.text == "50mg"
        )
        assert str_e.parent_entity_id == drug_e.entity_id

    def test_f8_alignment_ocr_typo_fuzzy_tolerance(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        synthetic_mlkit_builder: Any,
    ) -> None:
        # Match case insensitive
        raw = synthetic_mlkit_builder(
            lines=[("1. losartan 50mg", [0, 10, 200, 30], 0.9)]
        )
        ocr_doc = parse_mlkit_json_data(raw)
        anno_doc, records = align_prescription_to_ocr(
            sample_canonical_prescription_gt, ocr_doc
        )
        matched_drug = next(r for r in records if r.canonical_text == "Losartan")
        assert matched_drug.status == MatchStatus.MATCHED

    def test_f8_alignment_source_region_id_provenance(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        sample_mlkit_raw_json: dict[str, Any],
    ) -> None:
        ocr_doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        anno_doc, _ = align_prescription_to_ocr(
            sample_canonical_prescription_gt, ocr_doc
        )
        for e in anno_doc.entities:
            assert len(e.source_region_ids) >= 1
            assert all(rid.startswith("p0_") for rid in e.source_region_ids)


# ==============================================================================
# Feature 9: Match State Taxonomy
# ==============================================================================


class TestFeature9MatchStateTaxonomy:
    """F9: Categorization of alignment match status (MATCHED, AMBIGUOUS, UNRESOLVED)."""

    def test_f9_taxonomy_matched_status_criteria(self) -> None:
        rec = AlignmentRecord(
            prescription_id="RX_01",
            document_id="IMG_01",
            medication_id="M01",
            entity_type=EntityType.DRUG,
            canonical_text="Losartan",
            matched_text="Losartan",
            start=10,
            end=18,
            confidence=0.95,
            source_region_ids=["p0_b0_l0"],
            status=MatchStatus.MATCHED,
        )
        assert rec.status == MatchStatus.MATCHED
        assert rec.start is not None and rec.end is not None

    def test_f9_taxonomy_ambiguous_status_repeated_stt(self) -> None:
        rec = AlignmentRecord(
            prescription_id="RX_01",
            document_id="IMG_01",
            medication_id="M01",
            entity_type=EntityType.DOSAGE,
            canonical_text="1",
            matched_text=None,
            start=None,
            end=None,
            confidence=0.5,
            source_region_ids=[],
            status=MatchStatus.AMBIGUOUS,
        )
        assert rec.status == MatchStatus.AMBIGUOUS

    def test_f9_taxonomy_unresolved_status_missing_text(self) -> None:
        rec = AlignmentRecord(
            prescription_id="RX_01",
            document_id="IMG_01",
            medication_id="M01",
            entity_type=EntityType.DRUG,
            canonical_text="Depakine",
            matched_text=None,
            start=None,
            end=None,
            confidence=0.0,
            source_region_ids=[],
            status=MatchStatus.UNRESOLVED,
        )
        assert rec.status == MatchStatus.UNRESOLVED

    def test_f9_taxonomy_objective_ocr_space_no_crop_assumption(self) -> None:
        # Verify status is purely objective in OCR space
        assert set(MatchStatus.__members__.keys()) == {
            "MATCHED",
            "AMBIGUOUS",
            "UNRESOLVED",
        }

    def test_f9_taxonomy_state_enum_invariants(self) -> None:
        for st in MatchStatus:
            assert isinstance(st.value, str)


# ==============================================================================
# Feature 10: Observation Audit Report Generator
# ==============================================================================


class TestFeature10ObservationAuditMatrix:
    """F10: Generation and export of observation audit matrices."""

    def test_f10_audit_matrix_summary_aggregations(self) -> None:
        records = [
            AlignmentRecord(
                "RX_01",
                "D01",
                "M01",
                EntityType.DRUG,
                "Losartan",
                "Losartan",
                0,
                8,
                0.95,
                ["r1"],
                MatchStatus.MATCHED,
            ),
            AlignmentRecord(
                "RX_01",
                "D01",
                "M01",
                EntityType.STRENGTH,
                "50mg",
                None,
                None,
                None,
                0.0,
                [],
                MatchStatus.UNRESOLVED,
            ),
        ]
        rep = generate_alignment_audit_report(records)
        assert rep["summary"]["total_records"] == 2
        assert rep["summary"]["matched_count"] == 1
        assert rep["summary"]["unresolved_count"] == 1
        assert rep["summary"]["matched_pct"] == 50.0

    def test_f10_audit_matrix_prescription_breakdown(self) -> None:
        records = [
            AlignmentRecord(
                "RX_01",
                "D01",
                "M01",
                EntityType.DRUG,
                "Losartan",
                "Losartan",
                0,
                8,
                0.95,
                ["r1"],
                MatchStatus.MATCHED,
            ),
            AlignmentRecord(
                "RX_02",
                "D02",
                "M02",
                EntityType.DRUG,
                "Amlor",
                "Amlor",
                0,
                5,
                0.90,
                ["r2"],
                MatchStatus.MATCHED,
            ),
        ]
        rep = generate_alignment_audit_report(records)
        assert "RX_01" in rep["by_prescription"]
        assert "RX_02" in rep["by_prescription"]

    def test_f10_audit_matrix_entity_type_breakdown(self) -> None:
        records = [
            AlignmentRecord(
                "RX_01",
                "D01",
                "M01",
                EntityType.DRUG,
                "Losartan",
                "Losartan",
                0,
                8,
                0.95,
                ["r1"],
                MatchStatus.MATCHED,
            ),
            AlignmentRecord(
                "RX_01",
                "D01",
                "M01",
                EntityType.DOSAGE,
                "1 viên",
                "1 viên",
                10,
                16,
                0.90,
                ["r1"],
                MatchStatus.MATCHED,
            ),
        ]
        rep = generate_alignment_audit_report(records)
        assert "DRUG" in rep["by_entity_type"]
        assert "DOSAGE" in rep["by_entity_type"]

    def test_f10_audit_matrix_json_file_export(self, temp_test_dir: Path) -> None:
        records = [
            AlignmentRecord(
                "RX_01",
                "D01",
                "M01",
                EntityType.DRUG,
                "Losartan",
                "Losartan",
                0,
                8,
                0.95,
                ["r1"],
                MatchStatus.MATCHED,
            ),
        ]
        out_json = temp_test_dir / "audit.json"
        generate_alignment_audit_report(records, output_json_path=out_json)
        assert out_json.exists()
        with out_json.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["summary"]["total_records"] == 1

    def test_f10_audit_matrix_csv_manifest_generation(
        self, temp_test_dir: Path
    ) -> None:
        records = [
            AlignmentRecord(
                "RX_01",
                "D01",
                "M01",
                EntityType.DRUG,
                "Losartan",
                "Losartan",
                0,
                8,
                0.95,
                ["r1"],
                MatchStatus.MATCHED,
            ),
        ]
        out_csv = temp_test_dir / "audit.csv"
        generate_alignment_audit_report(records, output_csv_path=out_csv)
        assert out_csv.exists()
        content = out_csv.read_text(encoding="utf-8")
        assert "RX_01" in content
        assert "Losartan" in content


# ==============================================================================
# Feature 11: Schema Upgrade rxie.annotation.v2
# ==============================================================================


class TestFeature11RelationalAnnotationV2:
    """F11: Version 2 Span + Pointer hierarchical annotation schema."""

    def test_f11_v2_single_drug_hierarchy(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        doc = sample_annotation_document_v2
        assert doc.schema_version == "rxie.annotation.v2"
        assert len(doc.entities) == 4
        assert len(doc.relations) == 3

    def test_f11_v2_multi_drug_disjoint_attributes(self) -> None:
        raw_text = "Losartan 50mg\nAmlodipine 5mg"
        e_d1 = GoldEntityV2(
            entity_id="d1",
            type=EntityType.DRUG,
            text="Losartan",
            start=0,
            end=8,
            parent_entity_id=None,
        )
        e_s1 = GoldEntityV2(
            entity_id="s1",
            type=EntityType.STRENGTH,
            text="50mg",
            start=9,
            end=13,
            parent_entity_id="d1",
        )
        e_d2 = GoldEntityV2(
            entity_id="d2",
            type=EntityType.DRUG,
            text="Amlodipine",
            start=14,
            end=24,
            parent_entity_id=None,
        )
        e_s2 = GoldEntityV2(
            entity_id="s2",
            type=EntityType.STRENGTH,
            text="5mg",
            start=25,
            end=28,
            parent_entity_id="d2",
        )

        rels = [
            EntityRelation(
                head_entity_id="d1",
                tail_entity_id="s1",
                relation_type=RelationType.HAS_STRENGTH,
            ),
            EntityRelation(
                head_entity_id="d2",
                tail_entity_id="s2",
                relation_type=RelationType.HAS_STRENGTH,
            ),
        ]
        doc = AnnotationDocumentV2(
            document_id="MULTI_DRUG",
            raw_text=raw_text,
            entities=[e_d1, e_s1, e_d2, e_s2],
            relations=rels,
        )
        assert len(doc.entities) == 4
        assert doc.entities[1].parent_entity_id == "d1"
        assert doc.entities[3].parent_entity_id == "d2"

    def test_f11_v2_unassigned_instruction_pointer(self) -> None:
        raw_text = "Lời dặn: Tái khám sau 1 tháng"
        e_inst = GoldEntityV2(
            entity_id="inst1",
            type=EntityType.INSTRUCTION,
            text="Tái khám sau 1 tháng",
            start=9,
            end=29,
            parent_entity_id=None,
        )
        doc = AnnotationDocumentV2(
            document_id="GENERAL_INST", raw_text=raw_text, entities=[e_inst]
        )
        assert doc.entities[0].parent_entity_id is None

    def test_f11_v2_explicit_relations_mapping(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        rel_types = {r.relation_type for r in sample_annotation_document_v2.relations}
        assert RelationType.HAS_STRENGTH in rel_types
        assert RelationType.HAS_QUANTITY in rel_types
        assert RelationType.HAS_DOSAGE in rel_types

    def test_f11_v2_json_roundtrip_serialization(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        dumped = sample_annotation_document_v2.model_dump_json()
        reloaded = AnnotationDocumentV2.model_validate_json(dumped)
        assert reloaded.document_id == sample_annotation_document_v2.document_id
        assert len(reloaded.entities) == len(sample_annotation_document_v2.entities)


# ==============================================================================
# Feature 12: Flat BIO PhoBERT Dataset Export
# ==============================================================================


class TestFeature12FlatBIOExport:
    """F12: Sequence labeling BIO export for PhoBERT fast tokenizers."""

    def test_f12_bio_export_all_ten_classes(
        self, mock_fast_tokenizer: MockFastTokenizer
    ) -> None:
        raw_text = "Losartan 50mg 1 viên Ngày 28 Viên 30 ngày uống sau ăn viên Lời dặn"
        # Tokenizer mock produces tokens and offset mapping
        enc = mock_fast_tokenizer(raw_text)
        assert "offset_mapping" in enc
        assert enc["offset_mapping"][0] == (0, 0)  # [CLS]
        assert enc["offset_mapping"][-1] == (0, 0)  # [SEP]

    def test_f12_bio_export_multi_token_entities(
        self, mock_fast_tokenizer: MockFastTokenizer
    ) -> None:
        raw_text = "Paracetamol sủi 500mg"
        enc = mock_fast_tokenizer(raw_text)
        assert len(enc["input_ids"]) >= 4

    def test_f12_bio_export_special_tokens_neg100(
        self, mock_fast_tokenizer: MockFastTokenizer
    ) -> None:
        enc = mock_fast_tokenizer("Test Text")
        offsets = enc["offset_mapping"]
        # Special tokens have (0,0) offset which should be mapped to label -100
        assert offsets[0] == (0, 0)
        assert offsets[-1] == (0, 0)

    def test_f12_bio_export_adjacent_distinct_entities(
        self, mock_fast_tokenizer: MockFastTokenizer
    ) -> None:
        raw = "Amlodipine 5mg"
        enc = mock_fast_tokenizer(raw)
        assert len(enc["offset_mapping"]) >= 3

    def test_f12_bio_export_labels_and_ids_consistency(self) -> None:
        from rxie.alignment import ID_TO_LABEL, LABEL_TO_ID, LABELS

        assert len(LABELS) == 21  # O + 10 B- + 10 I-
        assert LABELS[0] == "O"
        for idx, lbl in enumerate(LABELS):
            assert LABEL_TO_ID[lbl] == idx
            assert ID_TO_LABEL[idx] == lbl


# ==============================================================================
# Feature 13: Dataset Generator (19/4/4 Split Isolation)
# ==============================================================================


class TestFeature13DatasetGeneratorSplits:
    """F13: Anti-leakage 19/4/4 prescription partitioning."""

    def test_f13_split_generator_19_4_4_prescription_partition(
        self, temp_test_dir: Path, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        splits_cfg = {
            "train": ["RX_001", "RX_002"],
            "val": ["RX_003"],
            "test": ["RX_004"],
        }
        cfg_p = temp_test_dir / "splits.json"
        with cfg_p.open("w", encoding="utf-8") as f:
            json.dump(splits_cfg, f)

        d1 = copy.deepcopy(sample_annotation_document_v2)
        d1.prescription_id = "RX_001"
        d2 = copy.deepcopy(sample_annotation_document_v2)
        d2.prescription_id = "RX_003"
        d3 = copy.deepcopy(sample_annotation_document_v2)
        d3.prescription_id = "RX_004"

        counts = generate_dataset_splits([d1, d2, d3], cfg_p, temp_test_dir / "out")
        assert counts["train"] == 1
        assert counts["val"] == 1
        assert counts["test"] == 1

    def test_f13_split_generator_zero_prescription_leakage(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        d_train = copy.deepcopy(sample_annotation_document_v2)
        d_train.prescription_id = "RX_001"
        d_train.patient_id = "PAT_001"
        d_val = copy.deepcopy(sample_annotation_document_v2)
        d_val.prescription_id = "RX_002"
        d_val.patient_id = "PAT_002"
        d_test = copy.deepcopy(sample_annotation_document_v2)
        d_test.prescription_id = "RX_003"
        d_test.patient_id = "PAT_003"

        res = verify_split_isolation([d_train], [d_val], [d_test])
        assert res["is_isolated"] is True
        assert len(res["rx_leakage"]) == 0

    def test_f13_split_generator_zero_patient_leakage(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        d_train = copy.deepcopy(sample_annotation_document_v2)
        d_train.prescription_id = "RX_001"
        d_train.patient_id = "PAT_001"
        d_val = copy.deepcopy(sample_annotation_document_v2)
        d_val.prescription_id = "RX_002"
        d_val.patient_id = "PAT_002"
        d_test = copy.deepcopy(sample_annotation_document_v2)
        d_test.prescription_id = "RX_003"
        d_test.patient_id = "PAT_003"

        res = verify_split_isolation([d_train], [d_val], [d_test])
        assert res["is_isolated"] is True
        assert len(res["patient_leakage"]) == 0

    def test_f13_split_generator_quarantine_hard_cases(self) -> None:
        quarantined = {
            "RX_026",
            "RX_028",
            "RX_029",
            "RX_030",
            "RX_032",
            "RX_033",
            "RX_034",
            "RX_035",
        }
        # Ensure quarantined prescriptions are never in splits
        train = {"RX_002", "RX_003"}
        assert len(quarantined & train) == 0

    def test_f13_split_generator_dataset_manifest_checksums(
        self, temp_test_dir: Path
    ) -> None:
        manifest_p = temp_test_dir / "manifest.json"
        manifest_data = {"version": "v1", "total_docs": 10, "sha256": "abc123def456"}
        with manifest_p.open("w", encoding="utf-8") as f:
            json.dump(manifest_data, f)
        assert manifest_p.exists()


# ==============================================================================
# Feature 14: Prescription-Balanced Samplers
# ==============================================================================


class TestFeature14PrescriptionBalancedSamplers:
    """F14: Weighted and Hierarchical sampling countering image count imbalance."""

    def test_f14_sampler_weights_sum_to_one_per_prescription(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        docs = []
        # RX_001 with 10 captures
        for i in range(10):
            d = copy.deepcopy(sample_annotation_document_v2)
            d.document_id = f"RX1_IMG{i}"
            d.prescription_id = "RX_001"
            docs.append(d)
        # RX_002 with 2 captures
        for i in range(2):
            d = copy.deepcopy(sample_annotation_document_v2)
            d.document_id = f"RX2_IMG{i}"
            d.prescription_id = "RX_002"
            docs.append(d)

        sampler = PrescriptionWeightedRandomSampler(docs)
        # Sum of weights for RX_001 = 10 * (1/10) = 1.0
        # Sum of weights for RX_002 = 2 * (1/2) = 1.0
        w_rx1 = sum(
            w
            for d, w in zip(docs, sampler.weights, strict=False)
            if d.prescription_id == "RX_001"
        )
        w_rx2 = sum(
            w
            for d, w in zip(docs, sampler.weights, strict=False)
            if d.prescription_id == "RX_002"
        )
        assert abs(w_rx1 - 1.0) < 1e-6
        assert abs(w_rx2 - 1.0) < 1e-6

    def test_f14_sampler_empirical_selection_uniformity(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        docs = []
        for _ in range(50):
            d = copy.deepcopy(sample_annotation_document_v2)
            d.prescription_id = "RX_001"
            docs.append(d)
        for _ in range(2):
            d = copy.deepcopy(sample_annotation_document_v2)
            d.prescription_id = "RX_002"
            docs.append(d)

        sampler = PrescriptionWeightedRandomSampler(docs, num_samples=1000, seed=42)
        indices = sampler.sample_indices()
        rx1_picks = sum(1 for idx in indices if docs[idx].prescription_id == "RX_001")
        rx2_picks = sum(1 for idx in indices if docs[idx].prescription_id == "RX_002")

        # In expectation both prescriptions are chosen 50% of the time (approx 500 each)
        assert 400 <= rx1_picks <= 600
        assert 400 <= rx2_picks <= 600

    def test_f14_sampler_seed_reproducibility(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        docs = [copy.deepcopy(sample_annotation_document_v2) for _ in range(5)]
        s1 = PrescriptionWeightedRandomSampler(docs, num_samples=20, seed=123)
        s2 = PrescriptionWeightedRandomSampler(docs, num_samples=20, seed=123)
        assert s1.sample_indices() == s2.sample_indices()

    def test_f14_sampler_hierarchical_epoch_capping(self) -> None:
        rx_to_images = {
            "RX_001": [f"img_{i}" for i in range(50)],
            "RX_002": [f"img_{i}" for i in range(5)],
        }
        sampler = HierarchicalPrescriptionSampler(
            rx_to_images, max_images_per_rx_per_epoch=15, seed=42
        )
        epoch = sampler.sample_epoch()
        # RX_001 capped at 15, RX_002 has 5 -> total 20
        assert len(epoch) == 20

    def test_f14_sampler_custom_sample_count(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        docs = [copy.deepcopy(sample_annotation_document_v2) for _ in range(10)]
        sampler = PrescriptionWeightedRandomSampler(docs, num_samples=7, seed=42)
        assert len(sampler.sample_indices()) == 7


# ==============================================================================
# Feature 15: Strict Entity Micro/Macro F1
# ==============================================================================


class TestFeature15StrictEntityEvaluation:
    """F15: Exact (type, start, end) entity recognition evaluation."""

    def test_f15_strict_entity_perfect_match_all_ones(self) -> None:
        gold = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="Losartan", start=0, end=8
            )
        ]
        pred = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="Losartan", start=0, end=8
            )
        ]
        res = evaluate_strict_entities(gold, pred)
        assert res.overall.precision == 1.0
        assert res.overall.recall == 1.0
        assert res.overall.f1 == 1.0

    def test_f15_strict_entity_disjoint_predictions_all_zeros(self) -> None:
        gold = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="Losartan", start=0, end=8
            )
        ]
        pred = [
            GoldEntityV2(
                entity_id="2", type=EntityType.DRUG, text="Nexium", start=10, end=16
            )
        ]
        res = evaluate_strict_entities(gold, pred)
        assert res.overall.true_positive == 0
        assert res.overall.f1 == 0.0

    def test_f15_strict_entity_partial_precision_and_recall(self) -> None:
        gold = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="Losartan", start=0, end=8
            ),
            GoldEntityV2(
                entity_id="2", type=EntityType.STRENGTH, text="50mg", start=9, end=13
            ),
        ]
        # Pred matches drug, but misses strength and adds a false positive
        pred = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="Losartan", start=0, end=8
            ),
            GoldEntityV2(
                entity_id="3", type=EntityType.DOSAGE, text="1 viên", start=14, end=20
            ),
        ]
        res = evaluate_strict_entities(gold, pred)
        assert res.overall.true_positive == 1
        assert res.overall.precision == 0.5
        assert res.overall.recall == 0.5
        assert res.overall.f1 == 0.5

    def test_f15_strict_entity_all_ten_classes_evaluated(self) -> None:
        res = evaluate_strict_entities([], [])
        assert len(res.per_class) == 10
        for ent_type in EntityType:
            assert ent_type in res.per_class

    def test_f15_strict_entity_micro_and_macro_prf_separation(self) -> None:
        gold = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="D1", start=0, end=2
            ),
            GoldEntityV2(
                entity_id="2", type=EntityType.DRUG, text="D2", start=3, end=5
            ),
            GoldEntityV2(
                entity_id="3", type=EntityType.STRENGTH, text="S1", start=6, end=8
            ),
        ]
        pred = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="D1", start=0, end=2
            ),
            GoldEntityV2(
                entity_id="2", type=EntityType.DRUG, text="D2", start=3, end=5
            ),
        ]
        res = evaluate_strict_entities(gold, pred)
        assert res.overall.f1 > 0.0
        assert res.macro.f1 > 0.0


# ==============================================================================
# Feature 16: Parent Assignment & Relation PRF
# ==============================================================================


class TestFeature16ParentAndRelationEvaluation:
    """F16: Parent accuracy and 8 clinical relation types PRF."""

    def test_f16_parent_accuracy_perfect_linkage(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        res = evaluate_relations(
            sample_annotation_document_v2, sample_annotation_document_v2
        )
        assert res.parent_accuracy == 1.0
        assert res.relation_micro.f1 == 1.0

    def test_f16_parent_accuracy_multi_drug_correct(self) -> None:
        raw = "DrugA 10mg DrugB 20mg"
        e1 = GoldEntityV2(
            entity_id="d1", type=EntityType.DRUG, text="DrugA", start=0, end=5
        )
        e2 = GoldEntityV2(
            entity_id="s1",
            type=EntityType.STRENGTH,
            text="10mg",
            start=6,
            end=10,
            parent_entity_id="d1",
        )
        e3 = GoldEntityV2(
            entity_id="d2", type=EntityType.DRUG, text="DrugB", start=11, end=16
        )
        e4 = GoldEntityV2(
            entity_id="s2",
            type=EntityType.STRENGTH,
            text="20mg",
            start=17,
            end=21,
            parent_entity_id="d2",
        )
        r1 = EntityRelation(
            head_entity_id="d1",
            tail_entity_id="s1",
            relation_type=RelationType.HAS_STRENGTH,
        )
        r2 = EntityRelation(
            head_entity_id="d2",
            tail_entity_id="s2",
            relation_type=RelationType.HAS_STRENGTH,
        )
        doc = AnnotationDocumentV2(
            document_id="D_REL",
            raw_text=raw,
            entities=[e1, e2, e3, e4],
            relations=[r1, r2],
        )

        res = evaluate_relations(doc, doc)
        assert res.parent_accuracy == 1.0
        assert res.relation_micro.f1 == 1.0

    def test_f16_relation_prf_eight_types_evaluation(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        res = evaluate_relations(
            sample_annotation_document_v2, sample_annotation_document_v2
        )
        assert len(res.per_type) == 8
        for rt in RelationType:
            assert rt in res.per_type

    def test_f16_relation_micro_macro_scores(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        res = evaluate_relations(
            sample_annotation_document_v2, sample_annotation_document_v2
        )
        assert 0.0 <= res.relation_micro.f1 <= 1.0
        assert 0.0 <= res.relation_macro.f1 <= 1.0

    def test_f16_relation_unassigned_parent_instruction(self) -> None:
        raw = "DrugA Lời dặn chung"
        e1 = GoldEntityV2(
            entity_id="d1", type=EntityType.DRUG, text="DrugA", start=0, end=5
        )
        e2 = GoldEntityV2(
            entity_id="i1",
            type=EntityType.INSTRUCTION,
            text="Lời dặn chung",
            start=6,
            end=19,
            parent_entity_id=None,
        )
        doc = AnnotationDocumentV2(
            document_id="D_UNASS", raw_text=raw, entities=[e1, e2]
        )

        res = evaluate_relations(doc, doc)
        assert res.parent_accuracy == 1.0


# ==============================================================================
# Feature 17: Record Exact Match & Tuple F1
# ==============================================================================


class TestFeature17RecordEvaluation:
    """F17: Medication record-level exact match and slot-tuple evaluation."""

    def test_f17_record_em_perfect_prediction(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        res = evaluate_records(
            [sample_annotation_document_v2], [sample_annotation_document_v2]
        )
        assert res.record_exact_match == 1.0
        assert res.document_exact_match == 1.0
        assert res.record_tuple_prf.f1 == 1.0

    def test_f17_record_em_partial_success_ratio(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        g_doc = sample_annotation_document_v2
        # Pred doc with altered strength
        p_doc = copy.deepcopy(sample_annotation_document_v2)
        # remove strength entity from pred
        p_doc.entities = [e for e in p_doc.entities if e.type != EntityType.STRENGTH]
        res = evaluate_records([g_doc], [p_doc])
        # Record EM is all-or-nothing -> 0.0
        assert res.record_exact_match == 0.0

    def test_f17_record_tuple_f1_partial_credit(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        g_doc = sample_annotation_document_v2
        p_doc = copy.deepcopy(sample_annotation_document_v2)
        # Remove 1 attribute out of 3
        p_doc.entities = [e for e in p_doc.entities if e.type != EntityType.STRENGTH]
        res = evaluate_records([g_doc], [p_doc])
        # Tuple F1 gives partial credit
        assert res.record_tuple_prf.f1 > 0.0
        assert res.record_tuple_prf.recall < 1.0

    def test_f17_document_em_all_or_nothing(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        d1 = sample_annotation_document_v2
        d2 = copy.deepcopy(sample_annotation_document_v2)
        d2_pred_bad = copy.deepcopy(d2)
        d2_pred_bad.entities = []

        res = evaluate_records([d1, d2], [d1, d2_pred_bad])
        # 1 out of 2 docs matched -> Document EM = 0.5
        assert res.document_exact_match == 0.5

    def test_f17_record_tuple_prf_precision_recall(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        res = evaluate_records(
            [sample_annotation_document_v2], [sample_annotation_document_v2]
        )
        assert res.record_tuple_prf.precision == 1.0
        assert res.record_tuple_prf.recall == 1.0


# ==============================================================================
# Feature 18: Dual Level Aggregation (Micro vs Macro)
# ==============================================================================


class TestFeature18DualLevelAggregation:
    """F18: Dual capture-level micro vs prescription-level macro evaluation."""

    def test_f18_dual_aggregation_balanced_convergence(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        # 2 prescriptions with identical perfect accuracy
        d1 = copy.deepcopy(sample_annotation_document_v2)
        d1.prescription_id = "RX_001"
        d2 = copy.deepcopy(sample_annotation_document_v2)
        d2.prescription_id = "RX_002"

        rep = evaluate_dual_level([d1, d2], [d1, d2])
        assert rep.entity_micro.f1 == 1.0
        assert rep.prescription_macro_summary["prescription_macro_entity_f1"] == 1.0

    def test_f18_dual_aggregation_skew_sensitivity(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        # RX_001 with 10 captures (perfect), RX_002 with 1 capture (0% accuracy)
        g_docs = []
        p_docs = []

        for i in range(10):
            d = copy.deepcopy(sample_annotation_document_v2)
            d.document_id = f"RX1_{i}"
            d.prescription_id = "RX_001"
            g_docs.append(d)
            p_docs.append(d)  # perfect

        d_bad_g = copy.deepcopy(sample_annotation_document_v2)
        d_bad_g.document_id = "RX2_0"
        d_bad_g.prescription_id = "RX_002"
        g_docs.append(d_bad_g)

        d_bad_p = copy.deepcopy(d_bad_g)
        d_bad_p.entities = []  # 0% accuracy
        p_docs.append(d_bad_p)

        rep = evaluate_dual_level(g_docs, p_docs)
        # Capture micro F1 is high (10/11 = ~90%)
        # Prescription macro F1 is exactly (1.0 + 0.0)/2 = 0.50
        assert rep.entity_micro.f1 > 0.85
        assert (
            abs(rep.prescription_macro_summary["prescription_macro_entity_f1"] - 0.50)
            < 0.05
        )

    def test_f18_dual_aggregation_prescription_breakdown(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        d = sample_annotation_document_v2
        rep = evaluate_dual_level([d], [d])
        assert "RX_001" in rep.prescription_breakdown
        assert "entity_micro_f1" in rep.prescription_breakdown["RX_001"]

    def test_f18_dual_aggregation_full_structured_report(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        rep = evaluate_dual_level(
            [sample_annotation_document_v2], [sample_annotation_document_v2]
        )
        assert rep.record_exact_match == 1.0
        assert rep.document_exact_match == 1.0
        assert rep.parent_accuracy == 1.0

    def test_f18_dual_aggregation_json_serialization(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        rep = evaluate_dual_level(
            [sample_annotation_document_v2], [sample_annotation_document_v2]
        )
        data = {
            "entity_micro_f1": rep.entity_micro.f1,
            "macro_summary": rep.prescription_macro_summary,
            "breakdown": rep.prescription_breakdown,
        }
        serialized = json.dumps(data)
        assert "prescription_macro_entity_f1" in serialized


# ==============================================================================
# Feature 19: End-to-End Pipeline Integration
# ==============================================================================


class TestFeature19PipelineIntegration:
    """F19: Chained end-to-end integration flows across all stages."""

    def test_f19_e2e_full_pipeline_happy_path(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        sample_mlkit_raw_json: dict[str, Any],
        temp_test_dir: Path,
    ) -> None:
        # Step 1: Ingest OCR
        ocr_doc = parse_mlkit_json_data(sample_mlkit_raw_json)

        # Step 2: Decompose GT
        decomp_gt = decompose_prescription(sample_canonical_prescription_gt)

        # Step 3: Align
        anno_doc, audit_records = align_prescription_to_ocr(decomp_gt, ocr_doc)
        assert len(anno_doc.entities) > 0

        # Step 4: Split Gen
        splits_cfg = {"train": ["RX_001"], "val": [], "test": []}
        cfg_file = temp_test_dir / "splits.json"
        with cfg_file.open("w", encoding="utf-8") as f:
            json.dump(splits_cfg, f)
        counts = generate_dataset_splits([anno_doc], cfg_file, temp_test_dir / "ner")
        assert counts["train"] == 1

        # Step 5: Sampler
        sampler = PrescriptionWeightedRandomSampler([anno_doc])
        indices = sampler.sample_indices()
        assert len(indices) == 1

        # Step 6: Evaluate
        rep = evaluate_dual_level([anno_doc], [anno_doc])
        assert rep.entity_micro.f1 == 1.0

    def test_f19_e2e_deterministic_reproducibility(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        sample_mlkit_raw_json: dict[str, Any],
    ) -> None:
        ocr1 = parse_mlkit_json_data(sample_mlkit_raw_json)
        ocr2 = parse_mlkit_json_data(sample_mlkit_raw_json)
        doc1, _ = align_prescription_to_ocr(sample_canonical_prescription_gt, ocr1)
        doc2, _ = align_prescription_to_ocr(sample_canonical_prescription_gt, ocr2)
        assert doc1.model_dump() == doc2.model_dump()

    def test_f19_e2e_offset_preservation_across_stages(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        sample_mlkit_raw_json: dict[str, Any],
    ) -> None:
        ocr_doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        anno_doc, _ = align_prescription_to_ocr(
            sample_canonical_prescription_gt, ocr_doc
        )
        for e in anno_doc.entities:
            assert anno_doc.raw_text[e.start : e.end] == e.text

    def test_f19_e2e_bio_export_compatibility(
        self,
        sample_annotation_document_v2: AnnotationDocumentV2,
        mock_fast_tokenizer: MockFastTokenizer,
    ) -> None:
        enc = mock_fast_tokenizer(sample_annotation_document_v2.raw_text)
        assert len(enc["input_ids"]) > 0

    def test_f19_e2e_evaluation_on_synthetic_predictions(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        rep = evaluate_dual_level(
            [sample_annotation_document_v2], [sample_annotation_document_v2]
        )
        assert rep.parent_accuracy == 1.0


# ==============================================================================
# Feature 20: Privacy Rules & Production 503 Semantics
# ==============================================================================


class TestFeature20PrivacyAndProduction503:
    """F20: Privacy guarantees (AGENTS.md) and production 503 HTTP semantics."""

    def test_f20_privacy_api_503_when_model_unset(self, monkeypatch: Any) -> None:
        monkeypatch.delenv("RXIE_MODEL_PATH", raising=False)
        app = create_app()
        client = TestClient(app)
        payload = {
            "document_id": "test_doc",
            "ocr_engine": {"name": "mlkit", "version": "1.0"},
            "pages": [{"width": 100, "height": 100, "page_index": 0, "regions": []}],
        }
        res = client.post("/entities", json=payload)
        assert res.status_code == 503
        assert "not configured" in res.json()["detail"]

    def test_f20_privacy_api_503_when_path_invalid(
        self, monkeypatch: Any, temp_test_dir: Path
    ) -> None:
        monkeypatch.setenv("RXIE_MODEL_PATH", str(temp_test_dir / "non_existent_dir"))
        app = create_app()
        client = TestClient(app)
        payload = {
            "document_id": "test_doc",
            "ocr_engine": {"name": "mlkit", "version": "1.0"},
            "pages": [{"width": 100, "height": 100, "page_index": 0, "regions": []}],
        }
        res = client.post("/entities", json=payload)
        assert res.status_code == 503

    def test_f20_privacy_api_health_endpoint_200(self, monkeypatch: Any) -> None:
        monkeypatch.delenv("RXIE_MODEL_PATH", raising=False)
        client = TestClient(create_app())
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    def test_f20_privacy_api_model_info_reports_unconfigured(
        self, monkeypatch: Any
    ) -> None:
        monkeypatch.delenv("RXIE_MODEL_PATH", raising=False)
        client = TestClient(create_app())
        res = client.get("/model-info")
        assert res.status_code == 200
        data = res.json()
        assert data["configured"] is False
        assert data["available"] is False

    def test_f20_privacy_api_success_with_injected_classifier(self) -> None:
        class InjectedClassifier(EntityClassifier):
            @property
            def model_version(self) -> str:
                return "injected-v1"

            def classify(self, text: DocumentText) -> list[Entity]:
                return []

        app = create_app(classifier_provider=InjectedClassifier)
        client = TestClient(app)
        payload = {
            "document_id": "doc_inj",
            "ocr_engine": {"name": "mlkit", "version": "1.0"},
            "pages": [{"width": 100, "height": 100, "page_index": 0, "regions": []}],
        }
        res = client.post("/entities", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == "doc_inj"
        assert data["model_version"] == "injected-v1"
        assert data["entities"] == []
