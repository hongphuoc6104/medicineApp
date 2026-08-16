"""Comprehensive unit and integration test suite for canonical GT decomposition."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from rxie.canonical_gt import (
    DECOMPOSITION_TABLE,
    VALID_PACKAGING_UNITS,
    batch_decompose_canonical_gt,
    decompose_instruction,
    decompose_medication,
    decompose_prescription,
    format_quantity_span,
    load_canonical_prescription,
    save_canonical_prescription,
    validate_all_canonical_gt,
    validate_canonical_gt,
    validate_canonical_medication,
)
from rxie.grouping import CanonicalMedication, CanonicalPrescriptionGT
from rxie.schemas import AnnotationDocument, EntityType, GoldEntity

GT_DIR = Path("data/canonical_ground_truth")
PRESC_DIR = Path("data/prescriptions")

PATTERNS_32_TEST_DATA = list(DECOMPOSITION_TABLE.items())


# ==========================================
# Group 1: Unit Tests for Instruction Decomposition
# ==========================================


@pytest.mark.parametrize("instruction_raw, expected", PATTERNS_32_TEST_DATA)
def test_decompose_instruction_all_32_patterns(
    instruction_raw: str, expected: dict[str, str | None]
):
    result = decompose_instruction(instruction_raw)
    for field, expected_val in expected.items():
        assert result.get(field) == expected_val, (
            f"Mismatch in {field} for input '{instruction_raw}': "
            f"got {result.get(field)!r}, expected {expected_val!r}"
        )


def test_decompose_instruction_normalized_fields():
    res = decompose_instruction("Ngày uống 1 viên buổi sáng")
    assert res["dosage_normalized"] == "1 viên"
    assert res["frequency_normalized"] == "ngày"
    assert res["route_normalized"] == "uống"
    assert res["form_normalized"] is None
    assert res["instruction_normalized"] == "buổi sáng"


def test_decompose_medication_in_place():
    med = CanonicalMedication(
        medication_id="RX_001_M01",
        drug_raw="Amlodipine (Amlor 5mg) 5mg",
        drug_normalized="amlodipine",
        strength_raw="5mg",
        quantity_value_raw="30",
        quantity_unit_raw="Viên",
        instruction_raw="Ngày uống 1 viên buổi sáng",
    )
    decomposed = decompose_medication(med)
    assert decomposed.dosage_raw == "1 viên"
    assert decomposed.frequency_raw == "Ngày"
    assert decomposed.route_raw == "uống"
    assert decomposed.form_raw is None
    assert decomposed.instruction_raw == "buổi sáng"
    assert decomposed.instruction_original_raw == "Ngày uống 1 viên buổi sáng"
    assert decomposed.drug_raw == "Amlodipine (Amlor 5mg) 5mg"
    assert decomposed.quantity_value_raw == "30"


def test_decompose_prescription_batch():
    gt = CanonicalPrescriptionGT(
        prescription_id="RX_001",
        patient_id="PAT_001",
        medications=[
            CanonicalMedication(
                medication_id="RX_001_M01",
                drug_raw="Amlodipine",
                instruction_raw="Ngày uống 1 viên sáng",
            ),
            CanonicalMedication(
                medication_id="RX_001_M02",
                drug_raw="Metformin",
                instruction_raw="Ngày uống 2 viên sau ăn tối",
            ),
        ],
    )
    decomposed_gt = decompose_prescription(gt)
    assert len(decomposed_gt.medications) == 2
    assert decomposed_gt.medications[0].dosage_raw == "1 viên"
    assert decomposed_gt.medications[1].dosage_raw == "2 viên"


# ==========================================
# Group 2: Canonical Ground Truth Batch Validation
# ==========================================


def test_batch_validate_all_27_gt_files():
    files = sorted(GT_DIR.glob("*.json"))
    assert len(files) == 27, (
        f"Expected 27 canonical ground truth files, found {len(files)}"
    )

    total_meds = 0
    rx_ids = set()
    pat_ids = set()

    for f in files:
        raw_text = f.read_text(encoding="utf-8")
        gt = CanonicalPrescriptionGT.model_validate_json(raw_text)
        assert gt.schema_version == "rxie.canonical_gt.v1"
        assert gt.prescription_id not in rx_ids, (
            f"Duplicate prescription_id {gt.prescription_id}"
        )
        rx_ids.add(gt.prescription_id)
        pat_ids.add(gt.patient_id)

        assert validate_canonical_gt(gt) is True

        for med in gt.medications:
            total_meds += 1
            assert med.medication_id.startswith(f"{gt.prescription_id}_M")
            assert len(med.drug_raw) > 0
            assert med.quantity_value_raw is not None
            assert med.quantity_unit_raw is not None

    assert total_meds == 85, f"Expected 85 total medications, found {total_meds}"
    assert len(rx_ids) == 27


def test_medication_count_and_id_integrity():
    for f in sorted(GT_DIR.glob("*.json")):
        gt = CanonicalPrescriptionGT.model_validate_json(f.read_text(encoding="utf-8"))
        for idx, med in enumerate(gt.medications, start=1):
            expected_id = f"{gt.prescription_id}_M{idx:02d}"
            assert med.medication_id == expected_id, (
                f"Medication ID mismatch in {f.name}: "
                f"expected {expected_id}, got {med.medication_id}"
            )


def test_patient_id_decoupling():
    for f in sorted(GT_DIR.glob("*.json")):
        gt = CanonicalPrescriptionGT.model_validate_json(f.read_text(encoding="utf-8"))
        assert re.match(r"^PAT_\d{3}$", gt.patient_id)
        assert re.match(r"^RX_\d{3}$", gt.prescription_id)


def test_mirrored_prescriptions_directory_consistency():
    gt_files = sorted(GT_DIR.glob("*.json"))
    for f in gt_files:
        rx_id = f.stem
        mirrored_file = PRESC_DIR / rx_id / "canonical_gt.json"
        assert mirrored_file.exists(), f"Missing mirrored GT file: {mirrored_file}"
        gt_orig = CanonicalPrescriptionGT.model_validate_json(
            f.read_text(encoding="utf-8")
        )
        gt_mirr = CanonicalPrescriptionGT.model_validate_json(
            mirrored_file.read_text(encoding="utf-8")
        )
        assert gt_orig == gt_mirr, f"Content mismatch between {f} and {mirrored_file}"


# ==========================================
# Group 3: Roundtrip Serialization & Immutability
# ==========================================


def test_canonical_gt_json_roundtrip():
    for f in sorted(GT_DIR.glob("*.json")):
        raw = f.read_text(encoding="utf-8")
        gt1 = CanonicalPrescriptionGT.model_validate_json(raw)
        dumped = gt1.model_dump_json(indent=2)
        gt2 = CanonicalPrescriptionGT.model_validate_json(dumped)
        assert gt1 == gt2


def test_canonical_gt_dict_roundtrip():
    for f in sorted(GT_DIR.glob("*.json")):
        gt1 = CanonicalPrescriptionGT.model_validate_json(f.read_text(encoding="utf-8"))
        dumped_dict = gt1.model_dump()
        gt2 = CanonicalPrescriptionGT.model_validate(dumped_dict)
        assert gt1 == gt2


def test_canonical_gt_forbid_extra_fields():
    with pytest.raises(ValidationError, match="extra_fields_not_allowed|extra"):
        CanonicalMedication(
            medication_id="RX_001_M01",
            drug_raw="Amlodipine",
            unexpected_field="disallowed",
        )

    with pytest.raises(ValidationError, match="extra_fields_not_allowed|extra"):
        CanonicalPrescriptionGT(
            prescription_id="RX_001",
            patient_id="PAT_001",
            invalid_prop=123,
        )


def test_save_and_load_canonical_prescription(tmp_path: Path):
    sample_file = GT_DIR / "RX_001.json"
    rx = load_canonical_prescription(sample_file)
    tmp_out = tmp_path / "RX_001.json"
    save_canonical_prescription(rx, tmp_out)
    rx_loaded = load_canonical_prescription(tmp_out)
    assert rx == rx_loaded


def test_batch_decompose_canonical_gt_helper(tmp_path: Path):
    results = batch_decompose_canonical_gt(GT_DIR, target_dir=tmp_path)
    assert len(results) == 27
    assert (tmp_path / "RX_001.json").exists()
    rx_001 = load_canonical_prescription(tmp_path / "RX_001.json")
    assert validate_canonical_gt(rx_001) is True


# ==========================================
# Group 4: Annotation Policy Locking Assertions
# ==========================================


def test_policy_drug_excludes_strength():
    """Policy 1: In canonical GT normalized fields, DRUG must not contain strength."""
    strength_regex = re.compile(r"\b\d+\s*(?:mg|g|mcg|ml|iu|u|%|ui)\b", re.IGNORECASE)
    for f in sorted(GT_DIR.glob("*.json")):
        gt = CanonicalPrescriptionGT.model_validate_json(f.read_text(encoding="utf-8"))
        for med in gt.medications:
            if med.drug_normalized:
                assert not strength_regex.search(med.drug_normalized), (
                    f"Violation in {med.medication_id}: "
                    f"drug_normalized '{med.drug_normalized}' contains strength"
                )


def test_policy_quantity_includes_unit():
    """Policy 2: QUANTITY must include unit."""
    valid_units = {"Viên", "Ống", "Lọ", "Tuýp", "Bút tiêm", "Viên sủi", "Gói", "Chai"}
    for f in sorted(GT_DIR.glob("*.json")):
        gt = CanonicalPrescriptionGT.model_validate_json(f.read_text(encoding="utf-8"))
        for med in gt.medications:
            assert med.quantity_unit_raw in valid_units, (
                f"Invalid unit '{med.quantity_unit_raw}' in {med.medication_id}"
            )
            span_text = format_quantity_span(
                med.quantity_value_raw, med.quantity_unit_raw
            )
            assert med.quantity_value_raw in span_text
            assert med.quantity_unit_raw in span_text


def test_policy_non_overlapping_spans():
    """Policy 3: AnnotationDocument strictly rejects overlapping flat spans."""
    with pytest.raises(ValidationError, match="must not overlap"):
        AnnotationDocument(
            document_id="doc-overlap",
            raw_text="Amlodipine 5mg 30 Vien",
            entities=[
                GoldEntity(
                    type=EntityType.DRUG, text="Amlodipine 5mg", start=0, end=14
                ),
                GoldEntity(type=EntityType.STRENGTH, text="5mg", start=11, end=14),
            ],
        )


def test_validate_canonical_gt_helper():
    valid_gt = CanonicalPrescriptionGT(
        prescription_id="RX_001",
        patient_id="PAT_001",
        medications=[
            CanonicalMedication(
                medication_id="RX_001_M01",
                drug_raw="Amlodipine",
                drug_normalized="amlodipine",
                quantity_value_raw="30",
                quantity_unit_raw="Viên",
            )
        ],
    )
    assert validate_canonical_gt(valid_gt) is True


def test_validate_canonical_medication_helper():
    med_valid = CanonicalMedication(
        medication_id="RX_001_M01",
        drug_raw="Amlodipine",
        drug_normalized="amlodipine",
        quantity_value_raw="30",
        quantity_unit_raw="Viên",
    )
    is_valid, errs = validate_canonical_medication(med_valid)
    assert is_valid is True
    assert len(errs) == 0

    med_invalid_drug = CanonicalMedication(
        medication_id="RX_001_M01",
        drug_raw="Amlodipine",
        drug_normalized="amlodipine 5mg",
        quantity_value_raw="30",
        quantity_unit_raw="Viên",
    )
    is_valid, errs = validate_canonical_medication(med_invalid_drug)
    assert is_valid is False
    assert any("Policy 1 violation" in e for e in errs)


# ==========================================
# Group 5: Edge Cases & Robustness
# ==========================================


@pytest.mark.parametrize("empty_input", [None, "", "   ", "\t\n"])
def test_edge_case_none_and_empty_inputs(empty_input: str | None):
    res = decompose_instruction(empty_input)
    assert res["dosage_raw"] is None
    assert res["frequency_raw"] is None
    assert res["route_raw"] is None
    assert res["form_raw"] is None
    assert res["instruction_raw"] is None


@pytest.mark.parametrize(
    "raw_inst, exp_dosage, exp_form",
    [
        ("Uống 1/2 viên sau ăn", "1/2 viên", None),
        ("Uống 1-2 viên trước khi ngủ", "1-2 viên", None),
        ("Uống 1.5 viên sau ăn", "1.5 viên", None),
        ("Tiêm bắp 5 đơn vị sáng", "5 đơn vị", None),
    ],
)
def test_edge_case_fractional_and_range_dosages(
    raw_inst: str, exp_dosage: str, exp_form: str | None
):
    res = decompose_instruction(raw_inst)
    assert res["dosage_raw"] == exp_dosage
    assert res["form_raw"] == exp_form


def test_edge_case_duration_phrases():
    res = decompose_instruction("Ngày uống 1 viên sau ăn trong 10 ngày")
    assert res["dosage_raw"] == "1 viên"
    assert res["duration_raw"] == "trong 10 ngày"
    assert res["duration_normalized"] == "trong 10 ngày"


def test_edge_case_complex_routes_and_forms():
    res1 = decompose_instruction("Tiêm dưới da 10 đơn vị buổi tối")
    assert res1["route_raw"] == "Tiêm dưới da"
    assert res1["dosage_raw"] == "10 đơn vị"
    assert res1["form_raw"] is None

    res2 = decompose_instruction("Sáng uống 1 ống sau ăn")
    assert res2["route_raw"] == "uống"
    assert res2["dosage_raw"] == "1 ống"
    assert res2["form_raw"] is None

    res3 = decompose_instruction("Nhỏ mắt khi mỏi, khô")
    assert res3["route_raw"] == "Nhỏ mắt"
    assert res3["dosage_raw"] is None
    assert res3["form_raw"] is None


def test_edge_case_whitespace_and_punctuation_handling():
    res = decompose_instruction("   Ngày  uống 1 viên sau ăn   ")
    assert res["dosage_raw"] == "1 viên"
    assert res["route_raw"] == "uống"


def test_format_quantity_span_edge_cases():
    assert format_quantity_span("30", "Viên") == "30 Viên"
    assert format_quantity_span("30", None) == "30"
    assert format_quantity_span(None, "Viên") == "Viên"
    assert format_quantity_span(None, None) == ""
    assert format_quantity_span("  10  ", "  Ống  ") == "10 Ống"
