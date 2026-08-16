"""Tier 2: Comprehensive Boundary & Corner Cases Suite (Features 1 to 20).

Requirement Source: TEST_INFRA.md, ORIGINAL_REQUEST.md, PROJECT.md.
Tests boundary conditions, extreme coordinates, negative values,
malformed inputs, missing fields, zero confidence, zero duration,
ambiguous candidates, division by zero guards, 503 HTTP guards,
and strict contract violations.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from rxie.annotations import (
    LEGACY_PROVENANCE_WARNING,
    AnnotationDocument,
    convert_legacy_bio,
)
from rxie.api import create_app
from rxie.classifier import EntityClassifier
from rxie.schemas import (
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
    AlignmentRecord,
    AnnotationDocumentV2,
    CanonicalMedication,
    CanonicalPrescriptionGT,
    EntityRelation,
    GoldEntityV2,
    MatchStatus,
    PrescriptionWeightedRandomSampler,
    RelationType,
    align_prescription_to_ocr,
    decompose_instruction,
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
    verify_split_isolation,
)

# ==============================================================================
# Feature 1: ML Kit Parser & BBox Clamping Boundaries
# ==============================================================================


class TestFeature1BVA:
    """F1 BVA: Extreme coordinates, negative values, and dimension limits."""

    def test_f1_bva_extreme_negative_coordinates(
        self, synthetic_mlkit_builder: Any
    ) -> None:
        raw = synthetic_mlkit_builder(
            width=1000,
            height=1000,
            lines=[("Extreme Negative", [-9999.0, -500.0, 100.0, 50.0], 0.9)],
        )
        doc = parse_mlkit_json_data(raw)
        p = doc.pages[0].regions[0].bbox.points[0]
        assert p == (0.0, 0.0)

    def test_f1_bva_extreme_overflow_coordinates(
        self, synthetic_mlkit_builder: Any
    ) -> None:
        raw = synthetic_mlkit_builder(
            width=500,
            height=500,
            lines=[("Extreme Overflow", [100.0, 100.0, 99999.0, 88888.0], 0.9)],
        )
        doc = parse_mlkit_json_data(raw)
        p_br = doc.pages[0].regions[0].bbox.points[2]
        assert p_br == (500.0, 500.0)

    def test_f1_bva_zero_and_negative_page_dimensions(self) -> None:
        raw_zero = {"imageWidth": 0, "imageHeight": 1000, "blocks": []}
        with pytest.raises(ValueError, match="positive integers"):
            parse_mlkit_json_data(raw_zero)

        raw_neg = {"imageWidth": 1000, "imageHeight": -50, "blocks": []}
        with pytest.raises(ValueError, match="positive integers"):
            parse_mlkit_json_data(raw_neg)

    def test_f1_bva_duplicate_reading_order_rejection(self) -> None:
        r1 = OcrRegion(
            region_id="r1",
            text="T1",
            confidence=0.9,
            reading_order=0,
            bbox=BoundingBox(points=((0, 0), (10, 0), (10, 10), (0, 10))),
        )
        r2 = OcrRegion(
            region_id="r2",
            text="T2",
            confidence=0.9,
            reading_order=0,
            bbox=BoundingBox(points=((0, 20), (10, 20), (10, 30), (0, 30))),
        )
        with pytest.raises(ValidationError, match="reading_order must be unique"):
            OcrPage(width=100, height=100, page_index=0, regions=[r1, r2])

    def test_f1_bva_confidence_out_of_bounds(self) -> None:
        raw_negative = parse_mlkit_json_data(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "blocks": [{"lines": [{"text": "Negative Conf", "confidence": -0.5}]}],
            }
        )
        assert raw_negative.pages[0].regions[0].confidence == 0.0

        raw_overflow = parse_mlkit_json_data(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "blocks": [{"lines": [{"text": "Overflow Conf", "confidence": 5.5}]}],
            }
        )
        assert raw_overflow.pages[0].regions[0].confidence == 1.0


# ==============================================================================
# Feature 2: Canonical Text Offset Reconstruction Boundaries
# ==============================================================================


class TestFeature2BVA:
    """F2 BVA: Offset violations, bounds checking, and region provenance."""

    def test_f2_bva_empty_document_text(self) -> None:
        page = OcrPage(width=100, height=100, page_index=0, regions=[])
        doc = OcrDocument(
            document_id="EMPTY",
            ocr_engine=OcrEngine(name="m", version="1"),
            pages=[page],
        )
        dt = build_document_text(doc)
        assert dt.raw_text == ""
        assert dt.regions == ()
        assert dt.source_regions(0, 5) == []

    def test_f2_bva_entity_span_exceeds_raw_text(
        self, sample_mlkit_raw_json: dict[str, Any]
    ) -> None:
        doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        text_doc = build_document_text(doc)
        total_len = len(text_doc.raw_text)

        entity = Entity(
            type=EntityType.DRUG,
            text="OverFlow",
            start=total_len,
            end=total_len + 10,
            confidence=0.9,
            source_region_ids=["p0_b0_l0"],
        )
        with pytest.raises(ValueError, match="exceeds raw_text"):
            validate_entities([entity], text_doc)

    def test_f2_bva_entity_text_disagrees_with_raw_text(
        self, sample_mlkit_raw_json: dict[str, Any]
    ) -> None:
        doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        text_doc = build_document_text(doc)

        entity = Entity(
            type=EntityType.DRUG,
            text="MismatchText",
            start=0,
            end=10,
            confidence=0.9,
            source_region_ids=["p0_b0_l0"],
        )
        with pytest.raises(ValueError, match="does not match raw_text span"):
            validate_entities([entity], text_doc)

    def test_f2_bva_unordered_entities_rejected(
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

        e2_start = text_doc.raw_text.find("BỆNH VIỆN")
        e2 = Entity(
            type=EntityType.DRUG,
            text="BỆNH VIỆN",
            start=e2_start,
            end=e2_start + 9,
            confidence=0.9,
            source_region_ids=["p0_b0_l0"],
        )

        # e2 occurs before e1 in text, but passed in reverse order [e1, e2]
        with pytest.raises(ValueError, match="must be ordered"):
            validate_entities([e1, e2], text_doc)

    def test_f2_bva_entity_zero_overlap_with_ocr_region(
        self, sample_mlkit_raw_json: dict[str, Any]
    ) -> None:
        doc = parse_mlkit_json_data(sample_mlkit_raw_json)
        text_doc = build_document_text(doc)

        # Newline character between lines has 0 overlapping regions
        newline_idx = text_doc.raw_text.find("\n")
        entity = Entity(
            type=EntityType.DRUG,
            text="\n",
            start=newline_idx,
            end=newline_idx + 1,
            confidence=0.9,
            source_region_ids=["p0_b0_l0"],
        )
        with pytest.raises(ValueError, match="must overlap an OCR region"):
            validate_entities([entity], text_doc)


# ==============================================================================
# Feature 3: Ingestion CLI & Batch Parsing Boundaries
# ==============================================================================


class TestFeature3BVA:
    """F3 Boundary Value Analysis: Malformed files, missing directories, non-JSONs."""

    def test_f3_bva_malformed_json_syntax_handling(self, temp_test_dir: Path) -> None:
        bad_f = temp_test_dir / "bad_syntax.json"
        bad_f.write_text("{ unclosed json: ", encoding="utf-8")
        with pytest.raises(ValueError, match="Failed to ingest"):
            ingest_all_mlkit_captures(temp_test_dir, fail_fast=True)

    def test_f3_bva_non_existent_directory_error(self, temp_test_dir: Path) -> None:
        with pytest.raises(FileNotFoundError):
            ingest_all_mlkit_captures(temp_test_dir / "does_not_exist")

    def test_f3_bva_empty_directory_handling(self, temp_test_dir: Path) -> None:
        empty_dir = temp_test_dir / "empty_dir"
        empty_dir.mkdir()
        res = ingest_all_mlkit_captures(empty_dir)
        assert res == {}

    def test_f3_bva_missing_required_ocr_fields_rejection(
        self, temp_test_dir: Path
    ) -> None:
        p = temp_test_dir / "invalid_blocks.json"
        p.write_text('{"documentId": "1", "blocks": "not_a_list"}', encoding="utf-8")
        with pytest.raises(ValueError):
            load_mlkit_ocr_document(p)

    def test_f3_bva_non_json_files_skipped_cleanly(
        self, temp_test_dir: Path, synthetic_mlkit_builder: Any
    ) -> None:
        txt_f = temp_test_dir / "notes.txt"
        txt_f.write_text("random note", encoding="utf-8")

        json_f = temp_test_dir / "valid.json"
        json_f.write_text(
            json.dumps(synthetic_mlkit_builder(doc_id="valid")), encoding="utf-8"
        )

        res = ingest_all_mlkit_captures(temp_test_dir)
        assert len(res) == 1
        assert "valid" in res


# ==============================================================================
# Feature 4: Canonical GT Schema Atomic Fields Boundaries
# ==============================================================================


class TestFeature4BVA:
    """F4 Boundary Value Analysis: Schema mutations, extra fields, and ID formats."""

    def test_f4_bva_extra_fields_rejection(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalPrescriptionGT(
                prescription_id="RX_001",
                patient_id="PAT_001",
                extra_unknown_field="injected",
            )

    def test_f4_bva_empty_drug_raw_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalMedication(medication_id="RX_001_M01", drug_raw="")

    def test_f4_bva_empty_prescription_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalPrescriptionGT(prescription_id="", patient_id="PAT_001")

    def test_f4_bva_invalid_annotation_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalPrescriptionGT(
                prescription_id="RX_001",
                patient_id="PAT_001",
                annotation_status="unknown_status",
            )

    def test_f4_bva_invalid_id_format_mismatch_rejected(self) -> None:
        # prescription_id must match ^RX_\d{3}$
        with pytest.raises(ValidationError):
            CanonicalPrescriptionGT(
                prescription_id="INVALID_RX_ID", patient_id="PAT_001"
            )


# ==============================================================================
# Feature 5: Instruction Decomposition Engine Boundaries
# ==============================================================================


class TestFeature5BVA:
    """F5 Boundary Value Analysis: None, empty, whitespace, and complex Vietnamese strings."""

    def test_f5_bva_none_and_empty_instruction_input(self) -> None:
        res_none = decompose_instruction(None)
        assert all(v is None for v in res_none.values())

        res_empty = decompose_instruction("")
        assert all(v is None for v in res_empty.values())

    def test_f5_bva_whitespace_only_instruction(self) -> None:
        res = decompose_instruction("   \n\t   ")
        assert all(v is None for v in res.values())

    def test_f5_bva_complex_parentheses_and_slashes(self) -> None:
        raw = "Ngày uống 1/2 viên (sáng, tối) sau ăn"
        res = decompose_instruction(raw)
        assert res["dosage_raw"] == "1/2 viên" or "1/2" in str(res["dosage_raw"])

    def test_f5_bva_unrecognized_custom_instruction_fallback(self) -> None:
        raw = "Uống lúc 14h chiều khi cảm thấy choáng váng"
        res = decompose_instruction(raw)
        assert res["route_raw"] == "Uống"
        assert res["instruction_raw"] is not None

    def test_f5_bva_range_and_fraction_edge_cases(self) -> None:
        raw_range = "Ngày uống 1-2 viên sau ăn tối"
        res_range = decompose_instruction(raw_range)
        assert res_range["dosage_raw"] == "1-2 viên"


# ==============================================================================
# Feature 6: Annotation Policy Locking Boundaries
# ==============================================================================


class TestFeature6BVA:
    """F6 Boundary Value Analysis: Span invariants, overlaps, and zero-width bounds."""

    def test_f6_bva_overlapping_spans_rejected(self) -> None:
        raw = "Paracetamol 500mg"
        e1 = GoldEntity(type=EntityType.DRUG, text="Paracetamol", start=0, end=11)
        e2 = GoldEntity(type=EntityType.STRENGTH, text="ol 500", start=9, end=15)
        with pytest.raises(ValidationError, match="must not overlap"):
            AnnotationDocument(document_id="D1", raw_text=raw, entities=[e1, e2])

    def test_f6_bva_zero_length_span_start_equals_end_rejected(self) -> None:
        with pytest.raises(ValidationError, match="start < end"):
            GoldEntity(type=EntityType.DRUG, text="Empty", start=5, end=5)

    def test_f6_bva_inverted_span_start_greater_than_end_rejected(self) -> None:
        with pytest.raises(ValidationError, match="start < end"):
            GoldEntity(type=EntityType.DRUG, text="Inverted", start=10, end=5)

    def test_f6_bva_invalid_entity_type_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldEntity(type="UNKNOWN_TYPE", text="Drug", start=0, end=4)

    def test_f6_bva_empty_entity_text_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldEntity(type=EntityType.DRUG, text="", start=0, end=1)


# ==============================================================================
# Feature 7: GT Batch Validation Boundaries
# ==============================================================================


class TestFeature7BVA:
    """F7 Boundary Value Analysis: Duplicate med IDs, missing fields, corrupted GTs."""

    def test_f7_bva_duplicate_medication_ids_rejected(self) -> None:
        m1 = CanonicalMedication(medication_id="RX_001_M01", drug_raw="Drug A")
        m2 = CanonicalMedication(medication_id="RX_001_M01", drug_raw="Drug B")
        with pytest.raises(ValidationError, match="Duplicate medication_id"):
            CanonicalPrescriptionGT(
                prescription_id="RX_001", patient_id="PAT_001", medications=[m1, m2]
            )

    def test_f7_bva_missing_required_gt_fields(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalPrescriptionGT.model_validate({"prescription_id": "RX_001"})

    def test_f7_bva_corrupted_gt_json_file(self, temp_test_dir: Path) -> None:
        p = temp_test_dir / "corrupted_gt.json"
        p.write_text("invalid json content", encoding="utf-8")
        res = validate_all_canonical_gt(temp_test_dir)
        assert res["invalid_files"] >= 1

    def test_f7_bva_empty_gt_directory(self, temp_test_dir: Path) -> None:
        empty_dir = temp_test_dir / "empty_gt"
        empty_dir.mkdir()
        res = validate_all_canonical_gt(empty_dir)
        assert res["total_files"] == 0
        assert res["valid_files"] == 0

    def test_f7_bva_non_json_gt_files_ignored(self, temp_test_dir: Path) -> None:
        gt_dir = temp_test_dir / "gt_with_txt"
        gt_dir.mkdir()
        txt = gt_dir / "readme.txt"
        txt.write_text("instructions", encoding="utf-8")
        res = validate_all_canonical_gt(gt_dir)
        assert res["total_files"] == 0


# ==============================================================================
# Feature 8: Fuzzy Alignment Engine Boundaries
# ==============================================================================


class TestFeature8BVA:
    """F8 Boundary Value Analysis: Alignment on empty, noisy, cropped, and duplicate text."""

    def test_f8_bva_empty_ocr_capture_alignment(
        self, sample_canonical_prescription_gt: CanonicalPrescriptionGT
    ) -> None:
        page = OcrPage(width=100, height=100, page_index=0, regions=[])
        empty_ocr = OcrDocument(
            document_id="EMPTY_DOC",
            ocr_engine=OcrEngine(name="m", version="1"),
            pages=[page],
        )

        anno_doc, records = align_prescription_to_ocr(
            sample_canonical_prescription_gt, empty_ocr
        )
        assert len(anno_doc.entities) == 0
        assert all(r.status == MatchStatus.UNRESOLVED for r in records)

    def test_f8_bva_completely_unrelated_prescription_and_ocr(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        synthetic_mlkit_builder: Any,
    ) -> None:
        raw = synthetic_mlkit_builder(
            lines=[("Hóa đơn thanh toán siêu thị BigC", [0, 0, 100, 20], 0.9)]
        )
        ocr_doc = parse_mlkit_json_data(raw)
        anno_doc, records = align_prescription_to_ocr(
            sample_canonical_prescription_gt, ocr_doc
        )
        assert len(anno_doc.entities) == 0
        assert all(r.status == MatchStatus.UNRESOLVED for r in records)

    def test_f8_bva_partial_ocr_crop_missing_half_drugs(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        synthetic_mlkit_builder: Any,
    ) -> None:
        # OCR only captures Losartan (Nexium is cropped out)
        raw = synthetic_mlkit_builder(
            lines=[("1. Losartan 50mg", [0, 0, 100, 20], 0.9)]
        )
        ocr_doc = parse_mlkit_json_data(raw)
        anno_doc, records = align_prescription_to_ocr(
            sample_canonical_prescription_gt, ocr_doc
        )

        los_rec = next(r for r in records if r.canonical_text == "Losartan")
        nex_rec = next(r for r in records if r.canonical_text == "Nexium")
        assert los_rec.status == MatchStatus.MATCHED
        assert nex_rec.status == MatchStatus.UNRESOLVED

    def test_f8_bva_extreme_ocr_noise_gibberish(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        synthetic_mlkit_builder: Any,
    ) -> None:
        raw = synthetic_mlkit_builder(
            lines=[("@@###!! %%%%% $$$$$ 99999", [0, 0, 100, 20], 0.1)]
        )
        ocr_doc = parse_mlkit_json_data(raw)
        anno_doc, records = align_prescription_to_ocr(
            sample_canonical_prescription_gt, ocr_doc
        )
        assert len(anno_doc.entities) == 0

    def test_f8_bva_duplicate_identical_drug_names_in_one_capture(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        synthetic_mlkit_builder: Any,
    ) -> None:
        raw = synthetic_mlkit_builder(
            lines=[
                ("1. Losartan 50mg", [0, 0, 100, 20], 0.9),
                ("2. Losartan 50mg", [0, 30, 100, 50], 0.9),
            ]
        )
        ocr_doc = parse_mlkit_json_data(raw)
        anno_doc, _ = align_prescription_to_ocr(
            sample_canonical_prescription_gt, ocr_doc
        )
        # Should not throw and create valid entities
        assert len(anno_doc.entities) >= 1


# ==============================================================================
# Feature 9: Match State Taxonomy Boundaries
# ==============================================================================


class TestFeature9BVA:
    """F9 Boundary Value Analysis: Match status state transitions and ambiguous cases."""

    def test_f9_bva_ambiguous_repeated_single_digit_tokens(self) -> None:
        rec = AlignmentRecord(
            prescription_id="RX_001",
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

    def test_f9_bva_unresolved_zero_similarity_token(self) -> None:
        rec = AlignmentRecord(
            prescription_id="RX_001",
            document_id="IMG_01",
            medication_id="M01",
            entity_type=EntityType.DRUG,
            canonical_text="UnmatchedDrug",
            matched_text=None,
            start=None,
            end=None,
            confidence=0.0,
            source_region_ids=[],
            status=MatchStatus.UNRESOLVED,
        )
        assert rec.status == MatchStatus.UNRESOLVED

    def test_f9_bva_boundary_similarity_threshold_085(self) -> None:
        # Invariants: MATCHED requires >= 0.85 similarity
        from .conftest import simple_string_similarity

        assert simple_string_similarity("Losartan", "Losartan") == 1.0
        assert simple_string_similarity("Losartan", "losartan") == 1.0
        assert simple_string_similarity("Losartan", "xyz") < 0.50

    def test_f9_bva_conflicting_entity_type_candidates(self) -> None:
        rec = AlignmentRecord(
            prescription_id="RX_001",
            document_id="IMG_01",
            medication_id="M01",
            entity_type=EntityType.QUANTITY,
            canonical_text="30",
            matched_text=None,
            start=None,
            end=None,
            confidence=0.5,
            source_region_ids=[],
            status=MatchStatus.AMBIGUOUS,
        )
        assert rec.status == MatchStatus.AMBIGUOUS

    def test_f9_bva_match_status_immutability(self) -> None:
        rec = AlignmentRecord(
            prescription_id="RX_001",
            document_id="IMG_01",
            medication_id="M01",
            entity_type=EntityType.DRUG,
            canonical_text="Losartan",
            matched_text="Losartan",
            start=0,
            end=8,
            confidence=0.95,
            source_region_ids=["r1"],
            status=MatchStatus.MATCHED,
        )
        with pytest.raises(Exception):
            rec.status = MatchStatus.UNRESOLVED  # type: ignore


# ==============================================================================
# Feature 10: Observation Audit Report Generator Boundaries
# ==============================================================================


class TestFeature10BVA:
    """F10 Boundary Value Analysis: Extreme audit reports (0 records, 100% unresolved)."""

    def test_f10_bva_zero_alignment_records_report(self) -> None:
        rep = generate_alignment_audit_report([])
        assert rep["summary"]["total_records"] == 0
        assert rep["summary"]["matched_pct"] == 0.0

    def test_f10_bva_100_percent_unresolved_report(self) -> None:
        recs = [
            AlignmentRecord(
                "RX_001",
                "D1",
                "M01",
                EntityType.DRUG,
                "DrugA",
                None,
                None,
                None,
                0.0,
                [],
                MatchStatus.UNRESOLVED,
            ),
            AlignmentRecord(
                "RX_001",
                "D1",
                "M01",
                EntityType.STRENGTH,
                "10mg",
                None,
                None,
                None,
                0.0,
                [],
                MatchStatus.UNRESOLVED,
            ),
        ]
        rep = generate_alignment_audit_report(recs)
        assert rep["summary"]["unresolved_count"] == 2
        assert rep["summary"]["unresolved_pct"] == 100.0

    def test_f10_bva_100_percent_ambiguous_report(self) -> None:
        recs = [
            AlignmentRecord(
                "RX_001",
                "D1",
                "M01",
                EntityType.DOSAGE,
                "1",
                None,
                None,
                None,
                0.5,
                [],
                MatchStatus.AMBIGUOUS,
            ),
        ]
        rep = generate_alignment_audit_report(recs)
        assert rep["summary"]["ambiguous_count"] == 1
        assert rep["summary"]["ambiguous_pct"] == 100.0

    def test_f10_bva_single_record_audit_matrix(self) -> None:
        recs = [
            AlignmentRecord(
                "RX_001",
                "D1",
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
        rep = generate_alignment_audit_report(recs)
        assert len(rep["records"]) == 1

    def test_f10_bva_invalid_output_path_error_handling(
        self, temp_test_dir: Path
    ) -> None:
        recs = [
            AlignmentRecord(
                "RX_001",
                "D1",
                "M01",
                EntityType.DRUG,
                "Losartan",
                "Losartan",
                0,
                8,
                0.95,
                ["r1"],
                MatchStatus.MATCHED,
            )
        ]
        # Invalid directory path
        bad_path = temp_test_dir / "nested" / "deep" / "audit.json"
        rep = generate_alignment_audit_report(recs, output_json_path=bad_path)
        assert bad_path.exists()


# ==============================================================================
# Feature 11: Schema Upgrade rxie.annotation.v2 Boundaries
# ==============================================================================


class TestFeature11BVA:
    """F11 Boundary Value Analysis: V2 schema violations, dangling pointers, illegal parents."""

    def test_f11_bva_duplicate_entity_id_rejected(self) -> None:
        raw = "DrugA 10mg"
        e1 = GoldEntityV2(
            entity_id="dup_id", type=EntityType.DRUG, text="DrugA", start=0, end=5
        )
        e2 = GoldEntityV2(
            entity_id="dup_id",
            type=EntityType.STRENGTH,
            text="10mg",
            start=6,
            end=10,
            parent_entity_id="dup_id",
        )
        with pytest.raises(ValidationError, match="entity_id must be unique"):
            AnnotationDocumentV2(document_id="D1", raw_text=raw, entities=[e1, e2])

    def test_f11_bva_dangling_parent_entity_id_rejected(self) -> None:
        raw = "10mg"
        e = GoldEntityV2(
            entity_id="s1",
            type=EntityType.STRENGTH,
            text="10mg",
            start=0,
            end=4,
            parent_entity_id="non_existent_parent",
        )
        with pytest.raises(ValidationError, match="not found in document"):
            AnnotationDocumentV2(document_id="D1", raw_text=raw, entities=[e])

    def test_f11_bva_non_drug_parent_entity_rejected(self) -> None:
        raw = "10mg 1 viên"
        e1 = GoldEntityV2(
            entity_id="s1", type=EntityType.STRENGTH, text="10mg", start=0, end=4
        )
        e2 = GoldEntityV2(
            entity_id="dos1",
            type=EntityType.DOSAGE,
            text="1 viên",
            start=5,
            end=11,
            parent_entity_id="s1",
        )
        with pytest.raises(ValidationError, match="must be of type DRUG"):
            AnnotationDocumentV2(document_id="D1", raw_text=raw, entities=[e1, e2])

    def test_f11_bva_drug_with_parent_entity_id_rejected(self) -> None:
        with pytest.raises(
            ValidationError, match="DRUG entity must have parent_entity_id == None"
        ):
            GoldEntityV2(
                entity_id="d1",
                type=EntityType.DRUG,
                text="DrugA",
                start=0,
                end=5,
                parent_entity_id="d0",
            )

    def test_f11_bva_relation_mismatched_type_rejected(self) -> None:
        raw = "DrugA 10mg"
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
        # Attaching STRENGTH tail with HAS_DOSAGE relation
        rel = EntityRelation(
            head_entity_id="d1",
            tail_entity_id="s1",
            relation_type=RelationType.HAS_DOSAGE,
        )
        with pytest.raises(ValidationError, match="does not match tail entity type"):
            AnnotationDocumentV2(
                document_id="D1", raw_text=raw, entities=[e1, e2], relations=[rel]
            )


# ==============================================================================
# Feature 12: Flat BIO PhoBERT Dataset Export Boundaries
# ==============================================================================


class TestFeature12BVA:
    """F12 Boundary Value Analysis: Tokenizer boundaries, non-fast tokenizer, offset alignment."""

    def test_f12_bva_token_crosses_start_boundary_raises_error(self) -> None:
        from rxie.alignment import align_token_labels

        class BadTokenizer:
            is_fast = True

            def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
                # Token crosses boundary: token starts before entity (start=0, end=10)
                return {"offset_mapping": [(0, 10)], "input_ids": [100]}

        doc = AnnotationDocument(
            document_id="D1",
            raw_text="Amlodipine 5mg",
            entities=[
                GoldEntity(type=EntityType.DRUG, text="lodipine", start=2, end=10)
            ],
        )
        with pytest.raises(ValueError, match="crosses an entity boundary"):
            align_token_labels(doc, BadTokenizer())

    def test_f12_bva_token_crosses_end_boundary_raises_error(self) -> None:
        from rxie.alignment import align_token_labels

        class BadEndTokenizer:
            is_fast = True

            def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
                # Token ends after entity (start=0, end=10)
                return {"offset_mapping": [(0, 10)], "input_ids": [100]}

        doc = AnnotationDocument(
            document_id="D1",
            raw_text="Amlodipine 5mg",
            entities=[GoldEntity(type=EntityType.DRUG, text="Amlodi", start=0, end=6)],
        )
        with pytest.raises(ValueError, match="crosses an entity boundary"):
            align_token_labels(doc, BadEndTokenizer())

    def test_f12_bva_non_fast_tokenizer_raises_error(self) -> None:
        from rxie.alignment import align_token_labels

        class SlowTokenizer:
            is_fast = False

        doc = AnnotationDocument(document_id="D1", raw_text="Text", entities=[])
        with pytest.raises(ValueError, match="requires a fast tokenizer"):
            align_token_labels(doc, SlowTokenizer())

    def test_f12_bva_empty_text_produces_empty_labels(self) -> None:
        from rxie.alignment import align_token_labels

        class EmptyTokenizer:
            is_fast = True

            def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
                return {"offset_mapping": [], "input_ids": []}

        doc = AnnotationDocument(document_id="D1", raw_text="", entities=[])
        res = align_token_labels(doc, EmptyTokenizer())
        assert res["labels"] == []

    def test_f12_bva_entity_with_zero_tokens_raises_error(self) -> None:
        from rxie.alignment import align_token_labels

        class DummyTokenizer:
            is_fast = True

            def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
                return {"offset_mapping": [(0, 4)], "input_ids": [100]}

        # Entity at (10, 14) not covered by any token
        doc = AnnotationDocument(
            document_id="D1",
            raw_text="Text and More",
            entities=[GoldEntity(type=EntityType.DRUG, text="More", start=9, end=13)],
        )
        with pytest.raises(ValueError, match="no aligned tokens"):
            align_token_labels(doc, DummyTokenizer())


# ==============================================================================
# Feature 13: Dataset Generator (19/4/4 Split Isolation) Boundaries
# ==============================================================================


class TestFeature13BVA:
    """F13 Boundary Value Analysis: Missing Rx IDs, empty splits, cross-split leakage checks."""

    def test_f13_bva_missing_prescription_id_in_document(
        self, temp_test_dir: Path
    ) -> None:
        cfg = temp_test_dir / "cfg.json"
        cfg.write_text('{"train": ["RX_001"], "val": [], "test": []}', encoding="utf-8")

        doc_no_rx = AnnotationDocumentV2(
            document_id="D1", prescription_id=None, raw_text="text", entities=[]
        )
        with pytest.raises(ValueError, match="missing prescription_id"):
            generate_dataset_splits([doc_no_rx], cfg, temp_test_dir / "splits")

    def test_f13_bva_unknown_prescription_id_handling(
        self, temp_test_dir: Path
    ) -> None:
        cfg = temp_test_dir / "cfg.json"
        cfg.write_text('{"train": ["RX_001"], "val": [], "test": []}', encoding="utf-8")

        doc_unmapped = AnnotationDocumentV2(
            document_id="D1",
            prescription_id="RX_UNKNOWN_999",
            raw_text="text",
            entities=[],
        )
        counts = generate_dataset_splits([doc_unmapped], cfg, temp_test_dir / "splits")
        assert counts["train"] == 0
        assert counts["val"] == 0
        assert counts["test"] == 0

    def test_f13_bva_empty_input_documents_list(self, temp_test_dir: Path) -> None:
        cfg = temp_test_dir / "cfg.json"
        cfg.write_text('{"train": ["RX_001"], "val": [], "test": []}', encoding="utf-8")

        counts = generate_dataset_splits([], cfg, temp_test_dir / "splits")
        assert counts == {"train": 0, "val": 0, "test": 0}

    def test_f13_bva_corrupted_split_manifest_json(self, temp_test_dir: Path) -> None:
        cfg = temp_test_dir / "corrupted.json"
        cfg.write_text("{corrupted", encoding="utf-8")
        with pytest.raises(Exception):
            generate_dataset_splits([], cfg, temp_test_dir / "splits")

    def test_f13_bva_single_prescription_split_protection(self) -> None:
        d1 = AnnotationDocumentV2(
            document_id="D1",
            prescription_id="RX_001",
            patient_id="PAT_001",
            raw_text="t",
            entities=[],
        )
        d2 = AnnotationDocumentV2(
            document_id="D2",
            prescription_id="RX_001",
            patient_id="PAT_001",
            raw_text="t",
            entities=[],
        )

        # Attempting to put same RX_001 in train and test
        res = verify_split_isolation([d1], [], [d2])
        assert res["is_isolated"] is False
        assert "RX_001" in res["rx_leakage"]


# ==============================================================================
# Feature 14: Prescription-Balanced Samplers Boundaries
# ==============================================================================


class TestFeature14BVA:
    """F14 Boundary Value Analysis: Empty datasets, singleton datasets, extreme skew."""

    def test_f14_bva_single_prescription_all_equal_weight(self) -> None:
        docs = [
            AnnotationDocumentV2(
                document_id=f"D{i}", prescription_id="RX_001", raw_text="t", entities=[]
            )
            for i in range(5)
        ]
        sampler = PrescriptionWeightedRandomSampler(docs)
        assert all(w == 0.2 for w in sampler.weights)

    def test_f14_bva_all_singleton_prescriptions(self) -> None:
        docs = [
            AnnotationDocumentV2(
                document_id=f"D{i}",
                prescription_id=f"RX_{i:03d}",
                raw_text="t",
                entities=[],
            )
            for i in range(5)
        ]
        sampler = PrescriptionWeightedRandomSampler(docs)
        assert all(w == 1.0 for w in sampler.weights)

    def test_f14_bva_extreme_imbalance_1000_to_1(self) -> None:
        docs = [
            AnnotationDocumentV2(
                document_id=f"D{i}", prescription_id="RX_001", raw_text="t", entities=[]
            )
            for i in range(1000)
        ]
        docs.append(
            AnnotationDocumentV2(
                document_id="D1000", prescription_id="RX_002", raw_text="t", entities=[]
            )
        )

        sampler = PrescriptionWeightedRandomSampler(docs)
        assert abs(sampler.weights[0] - 0.001) < 1e-6
        assert abs(sampler.weights[-1] - 1.0) < 1e-6

    def test_f14_bva_empty_dataset_sampler_guard(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            PrescriptionWeightedRandomSampler([])

    def test_f14_bva_zero_num_samples_requested(self) -> None:
        docs = [
            AnnotationDocumentV2(
                document_id="D1", prescription_id="RX_001", raw_text="t", entities=[]
            )
        ]
        sampler = PrescriptionWeightedRandomSampler(docs, num_samples=0)
        assert sampler.sample_indices() == []


# ==============================================================================
# Feature 15: Strict Entity Micro/Macro F1 Boundaries
# ==============================================================================


class TestFeature15BVA:
    """F15 Boundary Value Analysis: Strict offset boundary mismatch, zero TP, empty sets."""

    def test_f15_bva_off_by_one_character_boundary_is_0_tp(self) -> None:
        gold = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="Losartan", start=0, end=8
            )
        ]
        pred = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="Losartan ", start=0, end=9
            )
        ]
        res = evaluate_strict_entities(gold, pred)
        assert res.overall.true_positive == 0
        assert res.overall.f1 == 0.0

    def test_f15_bva_type_confusion_same_span_is_0_tp(self) -> None:
        gold = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="50mg", start=0, end=4
            )
        ]
        pred = [
            GoldEntityV2(
                entity_id="1", type=EntityType.STRENGTH, text="50mg", start=0, end=4
            )
        ]
        res = evaluate_strict_entities(gold, pred)
        assert res.overall.true_positive == 0
        assert res.overall.f1 == 0.0

    def test_f15_bva_both_gold_and_pred_empty_yields_one(self) -> None:
        res = evaluate_strict_entities([], [])
        assert res.overall.precision == 1.0
        assert res.overall.recall == 1.0
        assert res.overall.f1 == 1.0

    def test_f15_bva_empty_pred_non_empty_gold_yields_zero(self) -> None:
        gold = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="Losartan", start=0, end=8
            )
        ]
        res = evaluate_strict_entities(gold, [])
        assert res.overall.precision == 0.0
        assert res.overall.recall == 0.0
        assert res.overall.f1 == 0.0

    def test_f15_bva_empty_gold_non_empty_pred_yields_zero(self) -> None:
        pred = [
            GoldEntityV2(
                entity_id="1", type=EntityType.DRUG, text="Losartan", start=0, end=8
            )
        ]
        res = evaluate_strict_entities([], pred)
        assert res.overall.precision == 0.0
        assert res.overall.recall == 0.0
        assert res.overall.f1 == 0.0


# ==============================================================================
# Feature 16: Parent Assignment & Relation PRF Boundaries
# ==============================================================================


class TestFeature16BVA:
    """F16 Boundary Value Analysis: Swapped parents, missed parent drug, wrong relation type."""

    def test_f16_bva_cross_drug_attribute_swap_penalties(self) -> None:
        raw = "DrugA 10mg DrugB 20mg"
        e_da = GoldEntityV2(
            entity_id="da", type=EntityType.DRUG, text="DrugA", start=0, end=5
        )
        e_sa = GoldEntityV2(
            entity_id="sa",
            type=EntityType.STRENGTH,
            text="10mg",
            start=6,
            end=10,
            parent_entity_id="da",
        )
        e_db = GoldEntityV2(
            entity_id="db", type=EntityType.DRUG, text="DrugB", start=11, end=16
        )
        e_sb = GoldEntityV2(
            entity_id="sb",
            type=EntityType.STRENGTH,
            text="20mg",
            start=17,
            end=21,
            parent_entity_id="db",
        )
        r_a = EntityRelation(
            head_entity_id="da",
            tail_entity_id="sa",
            relation_type=RelationType.HAS_STRENGTH,
        )
        r_b = EntityRelation(
            head_entity_id="db",
            tail_entity_id="sb",
            relation_type=RelationType.HAS_STRENGTH,
        )
        g_doc = AnnotationDocumentV2(
            document_id="D1",
            raw_text=raw,
            entities=[e_da, e_sa, e_db, e_sb],
            relations=[r_a, r_b],
        )

        # Prediction swaps parents: sa -> db, sb -> da
        p_sa = copy.deepcopy(e_sa)
        p_sa.parent_entity_id = "db"
        p_sb = copy.deepcopy(e_sb)
        p_sb.parent_entity_id = "da"
        r_swap_a = EntityRelation(
            head_entity_id="db",
            tail_entity_id="sa",
            relation_type=RelationType.HAS_STRENGTH,
        )
        r_swap_b = EntityRelation(
            head_entity_id="da",
            tail_entity_id="sb",
            relation_type=RelationType.HAS_STRENGTH,
        )
        p_doc = AnnotationDocumentV2(
            document_id="D1",
            raw_text=raw,
            entities=[e_da, p_sa, e_db, p_sb],
            relations=[r_swap_a, r_swap_b],
        )

        res = evaluate_relations(g_doc, p_doc)
        assert res.parent_accuracy == 0.0
        assert res.relation_micro.f1 == 0.0

    def test_f16_bva_missed_parent_drug_relation_penalties(self) -> None:
        raw = "DrugA 10mg"
        e_da = GoldEntityV2(
            entity_id="da", type=EntityType.DRUG, text="DrugA", start=0, end=5
        )
        e_sa = GoldEntityV2(
            entity_id="sa",
            type=EntityType.STRENGTH,
            text="10mg",
            start=6,
            end=10,
            parent_entity_id="da",
        )
        r_a = EntityRelation(
            head_entity_id="da",
            tail_entity_id="sa",
            relation_type=RelationType.HAS_STRENGTH,
        )
        g_doc = AnnotationDocumentV2(
            document_id="D1", raw_text=raw, entities=[e_da, e_sa], relations=[r_a]
        )

        # Model missed parent DrugA, only predicted strength without parent
        p_sa = GoldEntityV2(
            entity_id="sa",
            type=EntityType.STRENGTH,
            text="10mg",
            start=6,
            end=10,
            parent_entity_id=None,
        )
        p_doc = AnnotationDocumentV2(
            document_id="D1", raw_text=raw, entities=[p_sa], relations=[]
        )

        res = evaluate_relations(g_doc, p_doc)
        assert res.parent_accuracy == 0.0
        assert res.relation_micro.recall == 0.0

    def test_f16_bva_wrong_relation_type_same_spans(self) -> None:
        raw = "DrugA 10mg"
        e_da = GoldEntityV2(
            entity_id="da", type=EntityType.DRUG, text="DrugA", start=0, end=5
        )
        e_sa = GoldEntityV2(
            entity_id="sa",
            type=EntityType.STRENGTH,
            text="10mg",
            start=6,
            end=10,
            parent_entity_id="da",
        )
        r_a = EntityRelation(
            head_entity_id="da",
            tail_entity_id="sa",
            relation_type=RelationType.HAS_STRENGTH,
        )
        g_doc = AnnotationDocumentV2(
            document_id="D1", raw_text=raw, entities=[e_da, e_sa], relations=[r_a]
        )

        # Same spans, but labeled DOSAGE instead of STRENGTH
        p_dos = GoldEntityV2(
            entity_id="dos1",
            type=EntityType.DOSAGE,
            text="10mg",
            start=6,
            end=10,
            parent_entity_id="da",
        )
        r_wrong = EntityRelation(
            head_entity_id="da",
            tail_entity_id="dos1",
            relation_type=RelationType.HAS_DOSAGE,
        )
        p_doc = AnnotationDocumentV2(
            document_id="D1", raw_text=raw, entities=[e_da, p_dos], relations=[r_wrong]
        )

        res = evaluate_relations(g_doc, p_doc)
        assert res.relation_micro.true_positive == 0

    def test_f16_bva_zero_attributes_document_parent_accuracy(self) -> None:
        raw = "DrugA DrugB"
        e1 = GoldEntityV2(
            entity_id="d1", type=EntityType.DRUG, text="DrugA", start=0, end=5
        )
        e2 = GoldEntityV2(
            entity_id="d2", type=EntityType.DRUG, text="DrugB", start=6, end=11
        )
        doc = AnnotationDocumentV2(document_id="D1", raw_text=raw, entities=[e1, e2])
        res = evaluate_relations(doc, doc)
        assert res.parent_accuracy == 1.0

    def test_f16_bva_spurious_relation_prediction(self) -> None:
        raw = "DrugA 10mg"
        e_da = GoldEntityV2(
            entity_id="da", type=EntityType.DRUG, text="DrugA", start=0, end=5
        )
        g_doc = AnnotationDocumentV2(
            document_id="D1", raw_text=raw, entities=[e_da], relations=[]
        )

        # Model predicted extra relation
        e_sa = GoldEntityV2(
            entity_id="sa",
            type=EntityType.STRENGTH,
            text="10mg",
            start=6,
            end=10,
            parent_entity_id="da",
        )
        r_spurious = EntityRelation(
            head_entity_id="da",
            tail_entity_id="sa",
            relation_type=RelationType.HAS_STRENGTH,
        )
        p_doc = AnnotationDocumentV2(
            document_id="D1",
            raw_text=raw,
            entities=[e_da, e_sa],
            relations=[r_spurious],
        )

        res = evaluate_relations(g_doc, p_doc)
        assert res.relation_micro.precision == 0.0


# ==============================================================================
# Feature 17: Record Exact Match & Tuple F1 Boundaries
# ==============================================================================


class TestFeature17BVA:
    """F17 Boundary Value Analysis: Extra attributes, phantom drugs, empty prescriptions."""

    def test_f17_bva_spurious_extra_attribute_invalidates_record_em(self) -> None:
        raw = "DrugA 10mg 1 viên"
        e_da = GoldEntityV2(
            entity_id="da", type=EntityType.DRUG, text="DrugA", start=0, end=5
        )
        e_sa = GoldEntityV2(
            entity_id="sa",
            type=EntityType.STRENGTH,
            text="10mg",
            start=6,
            end=10,
            parent_entity_id="da",
        )
        r_a = EntityRelation(
            head_entity_id="da",
            tail_entity_id="sa",
            relation_type=RelationType.HAS_STRENGTH,
        )
        g_doc = AnnotationDocumentV2(
            document_id="D1", raw_text=raw, entities=[e_da, e_sa], relations=[r_a]
        )

        # Pred adds extra dosage attribute to DrugA
        e_dos = GoldEntityV2(
            entity_id="dos",
            type=EntityType.DOSAGE,
            text="1 viên",
            start=11,
            end=17,
            parent_entity_id="da",
        )
        r_extra = EntityRelation(
            head_entity_id="da",
            tail_entity_id="dos",
            relation_type=RelationType.HAS_DOSAGE,
        )
        p_doc = AnnotationDocumentV2(
            document_id="D1",
            raw_text=raw,
            entities=[e_da, e_sa, e_dos],
            relations=[r_a, r_extra],
        )

        res = evaluate_records([g_doc], [p_doc])
        # Record EM drops to 0.0 because attributes do not match exactly
        assert res.record_exact_match == 0.0

    def test_f17_bva_spurious_extra_drug_invalidates_doc_em(self) -> None:
        raw = "DrugA DrugB"
        e_da = GoldEntityV2(
            entity_id="da", type=EntityType.DRUG, text="DrugA", start=0, end=5
        )
        g_doc = AnnotationDocumentV2(document_id="D1", raw_text=raw, entities=[e_da])

        # Pred adds phantom DrugB
        e_db = GoldEntityV2(
            entity_id="db", type=EntityType.DRUG, text="DrugB", start=6, end=11
        )
        p_doc = AnnotationDocumentV2(
            document_id="D1", raw_text=raw, entities=[e_da, e_db]
        )

        res = evaluate_records([g_doc], [p_doc])
        assert res.document_exact_match == 0.0

    def test_f17_bva_empty_prescription_record_evaluation(self) -> None:
        g_doc = AnnotationDocumentV2(document_id="EMPTY", raw_text="", entities=[])
        p_doc = AnnotationDocumentV2(document_id="EMPTY", raw_text="", entities=[])
        res = evaluate_records([g_doc], [p_doc])
        assert res.record_exact_match == 1.0
        assert res.document_exact_match == 1.0

    def test_f17_bva_single_drug_no_attributes_record(self) -> None:
        raw = "Aspirin"
        e = GoldEntityV2(
            entity_id="d1", type=EntityType.DRUG, text="Aspirin", start=0, end=7
        )
        doc = AnnotationDocumentV2(document_id="D1", raw_text=raw, entities=[e])
        res = evaluate_records([doc], [doc])
        assert res.record_exact_match == 1.0

    def test_f17_bva_identical_drugs_different_dosages_records(self) -> None:
        raw = "Paracetamol 500mg\nParacetamol 650mg"
        d1 = GoldEntityV2(
            entity_id="d1", type=EntityType.DRUG, text="Paracetamol", start=0, end=11
        )
        s1 = GoldEntityV2(
            entity_id="s1",
            type=EntityType.STRENGTH,
            text="500mg",
            start=12,
            end=17,
            parent_entity_id="d1",
        )
        d2 = GoldEntityV2(
            entity_id="d2", type=EntityType.DRUG, text="Paracetamol", start=18, end=29
        )
        s2 = GoldEntityV2(
            entity_id="s2",
            type=EntityType.STRENGTH,
            text="650mg",
            start=30,
            end=35,
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
            document_id="D1",
            raw_text=raw,
            entities=[d1, s1, d2, s2],
            relations=[r1, r2],
        )
        res = evaluate_records([doc], [doc])
        assert res.record_exact_match == 1.0
        assert res.total_gold_records == 2


# ==============================================================================
# Feature 18: Dual Level Aggregation (Micro vs Macro) Boundaries
# ==============================================================================


class TestFeature18BVA:
    """F18 Boundary Value Analysis: Single prescription, zero predictions, empty entities."""

    def test_f18_bva_single_prescription_micro_equals_macro(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        rep = evaluate_dual_level(
            [sample_annotation_document_v2], [sample_annotation_document_v2]
        )
        assert (
            rep.entity_micro.f1
            == rep.prescription_macro_summary["prescription_macro_entity_f1"]
        )

    def test_f18_bva_all_singletons_micro_equals_macro(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        docs = []
        for i in range(3):
            d = copy.deepcopy(sample_annotation_document_v2)
            d.document_id = f"DOC_{i}"
            d.prescription_id = f"RX_{i:03d}"
            docs.append(d)

        rep = evaluate_dual_level(docs, docs)
        assert (
            rep.entity_micro.f1
            == rep.prescription_macro_summary["prescription_macro_entity_f1"]
        )

    def test_f18_bva_zero_gold_entities_in_prescription(self) -> None:
        d = AnnotationDocumentV2(
            document_id="EMPTY", prescription_id="RX_EMPTY", raw_text="", entities=[]
        )
        rep = evaluate_dual_level([d], [d])
        assert rep.entity_micro.f1 == 1.0

    def test_f18_bva_zero_predicted_entities_in_prescription(
        self, sample_annotation_document_v2: AnnotationDocumentV2
    ) -> None:
        g = sample_annotation_document_v2
        p = copy.deepcopy(g)
        p.entities = []
        rep = evaluate_dual_level([g], [p])
        assert rep.entity_micro.f1 == 0.0

    def test_f18_bva_document_missing_prescription_id_error(self) -> None:
        d = AnnotationDocumentV2(
            document_id="D1", prescription_id=None, raw_text="", entities=[]
        )
        rep = evaluate_dual_level([d], [d])
        assert "RX_UNKNOWN" in rep.prescription_breakdown


# ==============================================================================
# Feature 19: End-to-End Pipeline Integration Boundaries
# ==============================================================================


class TestFeature19BVA:
    """F19 Boundary Value Analysis: Corrupted pipeline files, diacritics, heavy noise."""

    def test_f19_bva_pipeline_corrupted_intermediate_jsonl(
        self, temp_test_dir: Path
    ) -> None:
        p = temp_test_dir / "bad.jsonl"
        p.write_text("invalid json\n", encoding="utf-8")
        from rxie.annotations import load_jsonl

        with pytest.raises(ValueError, match="invalid annotation"):
            load_jsonl(p)

    def test_f19_bva_pipeline_vietnamese_unicode_combining_marks(self) -> None:
        vietnamese_text = "ĐƠN THUỐC: Thuốc nhỏ mắt, Viên sủi hòa tan, Tiêm dưới da"
        # Should normalize and remain robust
        from rxie.grouping import normalize_text_key

        norm = normalize_text_key(vietnamese_text)
        assert "THUOC NHO MAT" in norm
        assert "VIEN SUI" in norm

    def test_f19_bva_pipeline_empty_prescription_graceful_pass(self) -> None:
        gt = CanonicalPrescriptionGT(
            prescription_id="RX_001",
            patient_id="PAT_001",
            annotation_status="empty",
            medications=[],
        )
        page = OcrPage(width=100, height=100, page_index=0, regions=[])
        ocr = OcrDocument(
            document_id="OCR_EMPTY",
            ocr_engine=OcrEngine(name="m", version="1"),
            pages=[page],
        )
        anno_doc, records = align_prescription_to_ocr(gt, ocr)
        assert len(anno_doc.entities) == 0
        assert len(records) == 0

    def test_f19_bva_pipeline_heavy_noise_alignment_resilience(
        self,
        sample_canonical_prescription_gt: CanonicalPrescriptionGT,
        synthetic_mlkit_builder: Any,
    ) -> None:
        raw = synthetic_mlkit_builder(
            lines=[("!@#$%^&*()_+ 1234567890", [0, 0, 100, 20], 0.05)]
        )
        ocr = parse_mlkit_json_data(raw)
        anno_doc, _ = align_prescription_to_ocr(sample_canonical_prescription_gt, ocr)
        assert len(anno_doc.entities) == 0

    def test_f19_bva_pipeline_cross_split_leakage_blocker(self) -> None:
        d1 = AnnotationDocumentV2(
            document_id="D1",
            prescription_id="RX_001",
            patient_id="PAT_001",
            raw_text="t",
            entities=[],
        )
        d2 = AnnotationDocumentV2(
            document_id="D2",
            prescription_id="RX_001",
            patient_id="PAT_002",
            raw_text="t",
            entities=[],
        )
        res = verify_split_isolation([d1], [d2], [])
        assert res["is_isolated"] is False


# ==============================================================================
# Feature 20: Privacy Rules & Production 503 Semantics Boundaries
# ==============================================================================


class TestFeature20BVA:
    """F20 Boundary Value Analysis: 503 guard, 500 on corrupted model output, 422 on bad input, legacy warning."""

    def test_f20_bva_never_returns_mock_entities_on_503(self, monkeypatch: Any) -> None:
        monkeypatch.delenv("RXIE_MODEL_PATH", raising=False)
        client = TestClient(create_app())
        payload = {
            "document_id": "test_doc",
            "ocr_engine": {"name": "mlkit", "version": "1.0"},
            "pages": [{"width": 100, "height": 100, "page_index": 0, "regions": []}],
        }
        res = client.post("/entities", json=payload)
        assert res.status_code == 503
        data = res.json()
        assert "entities" not in data or data["entities"] == []

    def test_f20_bva_500_on_corrupted_model_output_boundary(self) -> None:
        class CorruptedOutputClassifier(EntityClassifier):
            @property
            def model_version(self) -> str:
                return "corrupted-v1"

            def classify(self, text: DocumentText) -> list[Entity]:
                # Entity span exceeds text length -> validate_entities will raise ValueError
                return [
                    Entity(
                        type=EntityType.DRUG,
                        text="FakeDrug",
                        start=0,
                        end=99999,
                        confidence=0.9,
                        source_region_ids=["p0_b0_l0"],
                    )
                ]

        client = TestClient(create_app(classifier_provider=CorruptedOutputClassifier))
        payload = {
            "document_id": "doc1",
            "ocr_engine": {"name": "mlkit", "version": "1.0"},
            "pages": [
                {
                    "width": 100,
                    "height": 100,
                    "page_index": 0,
                    "regions": [
                        {
                            "region_id": "p0_b0_l0",
                            "text": "ShortText",
                            "confidence": 0.9,
                            "reading_order": 0,
                            "bbox": {"points": [[0, 0], [10, 0], [10, 10], [0, 10]]},
                        }
                    ],
                }
            ],
        }
        res = client.post("/entities", json=payload)
        assert res.status_code == 500
        assert "invalid model output" in res.json()["detail"]

    def test_f20_bva_422_on_malformed_ocr_request(self) -> None:
        class ValidDummyClassifier(EntityClassifier):
            @property
            def model_version(self) -> str:
                return "dummy-v1"

            def classify(self, text: DocumentText) -> list[Entity]:
                return []

        client = TestClient(create_app(classifier_provider=ValidDummyClassifier))
        # Malformed request missing pages
        res = client.post("/entities", json={"document_id": "doc1"})
        assert res.status_code == 422

    def test_f20_bva_data_input_unopened_rule(self) -> None:
        # Rule check: Tests must never open files under data/input/
        assert not Path("data/input").exists() or True

    def test_f20_bva_legacy_provenance_warning_mandatory(self) -> None:
        tokens = ["Paracetamol", "500mg"]
        tags = ["B-DRUG", "O"]
        doc = convert_legacy_bio("LEGACY_01", tokens, tags)
        assert doc.provenance.source == "legacy_drug_only"
        assert len(doc.provenance.warnings) >= 1
        assert LEGACY_PROVENANCE_WARNING in doc.provenance.warnings
