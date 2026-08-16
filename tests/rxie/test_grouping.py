import json
import pytest
from rxie.grouping import (
    CanonicalMedication,
    CanonicalPrescriptionGT,
    DifficultyTags,
    HierarchicalPrescriptionSampler,
    ImageCaptureMetadata,
    PrescriptionGroup,
    PrescriptionsManifest,
    cluster_prescriptions_patient_aware,
    compute_content_similarity,
    create_balanced_prescription_splits,
    create_prescription_splits,
    extract_content_features,
    extract_patient_name,
    identify_prescription_fingerprint,
)


def test_feature_extraction_and_similarity():
    text1 = "Bệnh viện đa khoa Losartan 50mg ngày uống 1 viên sáng"
    text2 = "Bệnh viện đa khoa Losartan 50mg uống 1v buổi sáng"
    text3 = "Phòng khám tư nhân Paracetamol 500mg ngày uống 2 viên"

    feat1 = extract_content_features(text1)
    feat2 = extract_content_features(text2)
    feat3 = extract_content_features(text3)

    sim_1_2 = compute_content_similarity(feat1, feat2)
    sim_1_3 = compute_content_similarity(feat1, feat3)

    assert sim_1_2 > sim_1_3
    assert sim_1_2 > 0.25


def test_extract_patient_name():
    text1 = "BỘ Y TẾ BỆNH VIỆN BẠCH MAI Họ tên: NGUYỄN VĂN AN Giới tính: Nam Tuổi: 45"
    name1 = extract_patient_name(text1)
    assert "NGUYEN VAN AN" in name1

    text2 = "ĐƠN THUỐC Bệnh nhân: LÊ THỊ BÌNH Mã số BHYT: GD123"
    name2 = extract_patient_name(text2)
    assert "LE THI BINH" in name2


def test_identify_prescription_fingerprint():
    text1 = "BỆNH VIỆN NHÂN DÂN 115 25338204 Amlodipine 5mg Hypothiazid 25mg"
    key1, enc1, hosp1, drugs1 = identify_prescription_fingerprint(text1)
    assert key1 == "RX_115_DUONGDUCPHUC"
    assert hosp1 == "BV NHÂN DÂN 115"
    assert "amlodipine" in drugs1


def test_canonical_ground_truth_validation():
    gt = CanonicalPrescriptionGT(
        prescription_id="RX_001",
        patient_id="PAT_001",
        annotation_status="verified",
        verified_by="expert_1",
        verified_at="2026-08-16T00:00:00Z",
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
                instruction_raw="Ngày uống 1 viên (sáng, tối) sau ăn",
                instruction_normalized="ngày uống 2 viên (sáng, tối) sau ăn",
            )
        ],
    )
    assert gt.prescription_id == "RX_001"
    assert gt.patient_id == "PAT_001"
    assert gt.annotation_status == "verified"
    assert len(gt.medications) == 1
    assert gt.medications[0].medication_id == "RX_001_M01"
    assert gt.medications[0].drug_raw == "Losartan"
    assert gt.medications[0].quantity_value_normalized == 28


def test_create_prescription_splits_anti_leakage():
    rx_ids = [f"RX_{i:03d}" for i in range(1, 41)]
    splits = create_prescription_splits(rx_ids, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)

    train_set = set(splits["train"])
    val_set = set(splits["val"])
    test_set = set(splits["test"])

    # Ensure no overlap (zero leakage)
    assert len(train_set & val_set) == 0
    assert len(train_set & test_set) == 0
    assert len(val_set & test_set) == 0

    # Ensure total coverage
    assert len(train_set | val_set | test_set) == 40


def test_hierarchical_prescription_sampler():
    data = {
        "RX_001": [f"img_{i}" for i in range(100)],
        "RX_002": [f"img2_{i}" for i in range(5)],
    }
    sampler = HierarchicalPrescriptionSampler(data, max_images_per_rx_per_epoch=10, seed=42)
    epoch_imgs = sampler.sample_epoch()

    # RX_001 capped at 10, RX_002 has 5 -> total 15
    assert len(epoch_imgs) == 15
    rx1_count = sum(1 for img in epoch_imgs if img.startswith("img_"))
    rx2_count = sum(1 for img in epoch_imgs if img.startswith("img2_"))
    assert rx1_count == 10
    assert rx2_count == 5
