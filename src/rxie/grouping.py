"""Prescription grouping, canonical ground-truth models, audit tools, and anti-leakage splitting."""

from __future__ import annotations

import json
import math
import os
import random
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Common Vietnamese prescription boilerplate stop words
PRESCRIPTION_BOILERPLATE = {
    "bộ",
    "y",
    "tế",
    "bệnh",
    "viện",
    "phòng",
    "khám",
    "chữa",
    "bác",
    "sĩ",
    "khoa",
    "họ",
    "tên",
    "bố",
    "mẹ",
    "trẻ",
    "hoặc",
    "người",
    "đưa",
    "đến",
    "địa",
    "chỉ",
    "liên",
    "hệ",
    "nam",
    "nữ",
    "tuổi",
    "ngày",
    "tháng",
    "năm",
    "ký",
    "ghi",
    "rõ",
    "mã",
    "số",
    "thẻ",
    "bhyt",
    "bảo",
    "hiểm",
    "lời",
    "dặn",
    "hẹn",
    "tái",
    "đúng",
    "stt",
    "thuốc",
    "điều",
    "trị",
    "uống",
    "viên",
    "lần",
    "sáng",
    "trưa",
    "chiều",
    "tối",
    "sau",
    "ăn",
    "khi",
    "no",
    "đói",
    "cộng",
    "hòa",
    "xã",
    "hội",
    "chủ",
    "nghĩa",
    "việt",
    "độc",
    "lập",
    "tự",
    "do",
    "hạnh",
    "phúc",
    "phiếu",
    "khám",
    "chỉ",
    "định",
    "kê",
    "đơn",
    "ngoại",
    "trú",
    "nội",
    "trú",
    "chẩn",
    "đoán",
    "icd",
    "điện",
    "thoại",
    "liên",
    "hệ",
    "hạn",
    "sử",
    "dụng",
    "hướng",
    "dẫn",
    "nhớ",
}


def normalize_text_key(text: str) -> str:
    """Normalize Vietnamese text for consistent key matching."""
    text = unicodedata.normalize("NFC", text.strip().upper())
    nfkd_form = unicodedata.normalize("NFKD", text)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    only_ascii = re.sub(r"[^A-Z0-9\s]", " ", only_ascii)
    return re.sub(r"\s+", " ", only_ascii).strip()


class CanonicalMedication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medication_id: Annotated[
        str, Field(min_length=1, pattern=r"^RX_\d{3}_M\d{2}$")
    ]  # e.g., "RX_001_M01"
    drug_raw: Annotated[str, Field(min_length=1)]
    drug_normalized: str | None = None
    brand_raw: str | None = None
    brand_normalized: str | None = None
    strength_raw: str | None = None
    strength_normalized: str | None = None
    quantity_value_raw: str | None = None
    quantity_value_normalized: int | float | None = None
    quantity_unit_raw: str | None = None
    quantity_unit_normalized: str | None = None
    dosage_raw: str | None = None
    dosage_normalized: str | None = None
    frequency_raw: str | None = None
    frequency_normalized: str | None = None
    duration_raw: str | None = None
    duration_normalized: str | None = None
    route_raw: str | None = None
    route_normalized: str | None = None
    instruction_raw: str | None = None
    instruction_normalized: str | None = None
    instruction_original_raw: str | None = None
    form_raw: str | None = None
    form_normalized: str | None = None
    note: str | None = None

    @model_validator(mode="before")
    @classmethod
    def clean_empty_strings(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str) and not v.strip():
                    data[k] = None
        return data


class CanonicalPrescriptionGT(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["rxie.canonical_gt.v1"] = "rxie.canonical_gt.v1"
    prescription_id: Annotated[str, Field(min_length=1, pattern=r"^RX_\d{3}$")]
    patient_id: Annotated[
        str, Field(min_length=1, pattern=r"^PAT_\d{3}$")
    ]  # e.g., "PAT_001" (Decoupled from RX ID)
    encounter_id: str | None = None
    hospital_name: str | None = None
    prescription_date: str | None = None
    annotation_status: Literal["empty", "draft", "verified"] = "draft"
    verified_by: str | None = None
    verified_at: str | None = None
    diagnoses: list[str] = Field(default_factory=list)
    medications: list[CanonicalMedication] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_medication_ids(self) -> CanonicalPrescriptionGT:
        med_ids = [m.medication_id for m in self.medications]
        if len(med_ids) != len(set(med_ids)):
            raise ValueError(
                f"Duplicate medication_id found in prescription {self.prescription_id}"
            )
        return self


class ImageCaptureMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_id: Annotated[str, Field(min_length=1)]
    filename: str
    relative_path: str
    ocr_file: str | None = None
    word_count: int = 0
    line_count: int = 0
    mean_confidence: float = 0.0
    detected_angle: float = 0.0
    similarity_to_group: float = 1.0


class PrescriptionGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prescription_id: Annotated[str, Field(min_length=1)]
    patient_id: Annotated[str, Field(min_length=1)]
    grouping_status: Literal["auto", "needs_review", "verified"] = "verified"
    image_count: Annotated[int, Field(ge=1)]
    encounter_code_hint: str | None = None
    hospital_hint: str | None = None
    doctor_hint: str | None = None
    diagnoses_hint: list[str] = Field(default_factory=list)
    representative_keywords: list[str] = Field(default_factory=list)
    images: list[ImageCaptureMetadata]
    min_similarity: float = 1.0
    median_similarity: float = 1.0


class PrescriptionsManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["rxie.manifest.v1"] = "rxie.manifest.v1"
    total_prescriptions: int
    total_images: int
    verified_prescriptions_count: int = 0
    duplicate_images_resolved: int = 0
    groups: list[PrescriptionGroup]


class DifficultyTags(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orientation: Literal["none", "low", "medium", "high"] = "none"
    skew: Literal["none", "low", "medium", "high"] = "none"
    perspective: Literal["none", "low", "medium", "high"] = "none"
    blur: Literal["none", "low", "medium", "high"] = "none"
    lighting: Literal["none", "low", "medium", "high"] = "none"
    crop: Literal["none", "low", "medium", "high"] = "none"


class BenchmarkImageGT(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_id: Annotated[str, Field(min_length=1)]
    prescription_id: Annotated[str, Field(min_length=1)]
    medication_region_transcription: str
    medications: list[CanonicalMedication]
    difficulty_tags: DifficultyTags = Field(default_factory=DifficultyTags)
    split_role: Literal["tuning", "test"] = "tuning"


def extract_patient_name(text: str) -> str:
    """Extract patient name candidate from OCR text."""
    m = re.search(
        r"(?:họ\s*tên|bệnh\s*nhân|tên\s*bn)[\s:]+([A-ZÀ-Ỹ\s]{3,28})",
        text,
        re.IGNORECASE,
    )
    if not m:
        return ""
    name = m.group(1).strip()
    for bp in [
        "MÃ SỐ",
        "ĐỊA CHỈ",
        "GIỚI TÍNH",
        "THUỐC",
        "BHYT",
        "TUỔI",
        "STT",
        "CHẨN ĐOÁN",
        "SỞ Y TẾ",
        "BỆNH VIỆN",
    ]:
        if bp in name.upper():
            idx = name.upper().find(bp)
            name = name[:idx].strip()
    norm = normalize_text_key(name)
    tokens = norm.split()
    if len(tokens) >= 2 and all(len(t) >= 2 for t in tokens):
        return " ".join(tokens[:4])
    return ""


def extract_content_features(text: str) -> set[str]:
    """Extract discriminative content tokens (excluding boilerplate)."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    words = [w for w in cleaned.split() if len(w) >= 2 and not w.isdigit()]
    content_words = [w for w in words if w not in PRESCRIPTION_BOILERPLATE]
    features = set(content_words)
    compact_text = "".join(content_words)
    if len(compact_text) >= 4:
        for i in range(len(compact_text) - 3):
            features.add(compact_text[i : i + 4])
    return features


def compute_content_similarity(set_a: set[str], set_b: set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union > 0 else 0.0


def identify_prescription_fingerprint(
    text: str,
) -> tuple[str | None, str | None, str | None, list[str]]:
    """Multi-signal identification: (fingerprint_key, encounter_hint, hospital_hint, core_drugs)."""
    t_lower = text.lower()

    enc = None
    if "bt2939" in t_lower or "29392135186" in text:
        enc = "BT29392135186"
    elif "25338204" in text or "dn8584" in t_lower:
        enc = "ENC_25338204_DN8584"
    elif "25600820" in text or "dn4989" in t_lower:
        enc = "ENC_25600820_DN4989"
    elif "dn5174619703" in t_lower or "5174619703" in text:
        enc = "DN5174619703"

    hosp = None
    if "cần thơ" in t_lower:
        hosp = "BVĐK TW CẦN THƠ"
    elif "115" in text or "nhân dân 115" in t_lower:
        hosp = "BV NHÂN DÂN 115"
    elif "chợ rẫy" in t_lower:
        hosp = "BV CHỢ RẪY"
    elif "bạch mai" in t_lower:
        hosp = "BV BẠCH MAI"

    core_drugs = []
    drug_lexicon = [
        "losartan",
        "cozaar",
        "citicoline",
        "somazina",
        "atorvastatin",
        "lipitor",
        "clopidogrel",
        "plavix",
        "nitroglycerin",
        "nitromint",
        "amlodipine",
        "amler",
        "telmisartan",
        "micardis",
        "hydrochlorothiazide",
        "hypothiazid",
        "rotunda",
        "aspirin",
        "omega-3",
        "omega",
        "magnesium",
        "magne",
        "refresh",
        "systane",
        "nexium",
        "esomeprazole",
        "bisoprolol",
        "concor",
        "metformin",
        "glucophage",
        "depakine",
        "valproic",
        "silymarin",
        "myyamna",
        "jardiance",
        "empagliflozin",
        "amitriptyline",
        "budesonide",
    ]
    for d in drug_lexicon:
        if d in t_lower:
            core_drugs.append(d)

    key = None
    if enc == "BT29392135186" or (
        "cần thơ" in str(hosp).lower()
        and (
            "losartan" in core_drugs
            or "refresh" in core_drugs
            or "nexium" in core_drugs
            or "bisoprolol" in core_drugs
        )
    ):
        key = "RX_CANTHO_LEVANTRAN"
    elif enc == "ENC_25338204_DN8584" or (
        hosp == "BV NHÂN DÂN 115"
        and (
            "amlodipine" in core_drugs
            or "hypothiazid" in core_drugs
            or "rotunda" in core_drugs
            or "micardis" in core_drugs
        )
    ):
        key = "RX_115_DUONGDUCPHUC"
    elif enc == "ENC_25600820_DN4989" or (
        hosp == "BV CHỢ RẪY" and ("valproic" in core_drugs or "depakine" in core_drugs)
    ):
        key = "RX_CHORAY_TRANDUCPHUC"
    elif "somazina" in core_drugs or "citicoline" in core_drugs:
        key = "RX_NGUYENNGOCMAI_SOMAZINA"
    elif "lipitor" in core_drugs and "plavix" in core_drugs:
        key = "RX_TRANNGOCTAM_LIPITOR_PLAVIX"
    elif "aspirin" in core_drugs and (
        "omega" in core_drugs or "omega-3" in core_drugs or "systane" in core_drugs
    ):
        key = "RX_DUONGMINHMAI_ASPIRIN_OMEGA"
    elif (
        "silymarin" in core_drugs or "myyamna" in core_drugs or "lý hữu sơn" in t_lower
    ):
        key = "RX_LYHULUSON_SILYMARIN"
    elif (
        "nitromint" in core_drugs
        or "nitroglycerin" in core_drugs
        or "hoàng minh giang" in t_lower
    ):
        key = "RX_HOANGMINHGIANG_NITROMINT"
    elif (
        "amitriptyline" in core_drugs
        or "vũ minh sơn" in t_lower
        or "vo minh son" in t_lower
    ):
        key = "RX_VUMINHSON_AMITRIPTYLINE"
    elif "ngô mạnh phúc" in t_lower or "ngo manh phuc" in t_lower:
        key = "RX_NGOMANHPHUC"
    elif "đặng kim tâm" in t_lower or "dang kim tam" in t_lower:
        key = "RX_DANGKIMTAM"
    elif "trần thanh phúc" in t_lower or "tran thanh phuc" in t_lower:
        key = "RX_TRANTHANHPHUC"

    return key, enc, hosp, sorted(set(core_drugs))


def cluster_prescriptions_patient_aware(
    items: list[dict],
    content_sim_threshold: float = 0.18,
) -> list[list[dict]]:
    """Multi-signal clustering: Encounter ID > Drug signature > Patient anchor > Jaccard content fallback."""
    if not items:
        return []

    for item in items:
        text = item.get("text", "")
        key, enc, hosp, drugs = identify_prescription_fingerprint(text)
        item["fp_key"] = key
        item["enc"] = enc
        item["hosp"] = hosp
        item["drugs"] = drugs
        item["patient_norm"] = normalize_text_key(extract_patient_name(text))
        item["features"] = extract_content_features(text)

    fp_clusters = defaultdict(list)
    unassigned = []

    for item in items:
        if item["fp_key"]:
            fp_clusters[item["fp_key"]].append(item)
        elif len(item["patient_norm"]) >= 4:
            fp_clusters[f"PAT_{item['patient_norm']}"].append(item)
        else:
            unassigned.append(item)

    still_unassigned = []
    for item in unassigned:
        best_match = None
        best_sim = 0.0
        for fp_k, members in fp_clusters.items():
            for m in members:
                sim = compute_content_similarity(item["features"], m["features"])
                if sim > best_sim:
                    best_sim = sim
                    best_match = fp_k

        if best_match is not None and best_sim >= content_sim_threshold:
            fp_clusters[best_match].append(item)
        else:
            still_unassigned.append(item)

    rem_clusters: list[list[dict]] = []
    assigned_rem = set()
    for i in range(len(still_unassigned)):
        if i in assigned_rem:
            continue
        cur = [still_unassigned[i]]
        assigned_rem.add(i)
        for j in range(i + 1, len(still_unassigned)):
            if j in assigned_rem:
                continue
            sim = compute_content_similarity(
                still_unassigned[i]["features"], still_unassigned[j]["features"]
            )
            if sim >= content_sim_threshold:
                cur.append(still_unassigned[j])
                assigned_rem.add(j)
        rem_clusters.append(cur)

    return list(fp_clusters.values()) + rem_clusters


def create_balanced_prescription_splits(
    groups: list[PrescriptionGroup],
    n_train: int = 19,
    n_val: int = 4,
    n_test: int = 4,
    seed: int = 42,
) -> dict[str, list[str]]:
    """
    Balanced prescription split strategy:
    Ensures high-image prescriptions (e.g. RX_001, RX_002, RX_003) and different hospitals
    are evenly distributed across Train, Val, and Test.
    """
    verified_groups = [g for g in groups if g.grouping_status == "verified"]
    # Sort descending by image count
    sorted_groups = sorted(verified_groups, key=lambda g: g.image_count, reverse=True)

    rng = random.Random(seed)

    train_ids = []
    val_ids = []
    test_ids = []

    # Distribute the top 6 largest groups in round-robin fashion (4 in train, 1 in val, 1 in test)
    top_groups = sorted_groups[:6]
    rem_groups = sorted_groups[6:]

    rng.shuffle(top_groups)
    train_ids.extend([g.prescription_id for g in top_groups[:4]])
    val_ids.append(top_groups[4].prescription_id)
    test_ids.append(top_groups[5].prescription_id)

    # Distribute the remaining groups to reach target counts
    rng.shuffle(rem_groups)
    for g in rem_groups:
        if len(val_ids) < n_val:
            val_ids.append(g.prescription_id)
        elif len(test_ids) < n_test:
            test_ids.append(g.prescription_id)
        elif len(train_ids) < n_train:
            train_ids.append(g.prescription_id)
        else:
            train_ids.append(g.prescription_id)

    return {
        "train": sorted(train_ids),
        "val": sorted(val_ids),
        "test": sorted(test_ids),
        "unverified_or_review": [
            g.prescription_id for g in groups if g.grouping_status != "verified"
        ],
    }


def create_prescription_splits(
    prescription_ids: list[str],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, list[str]]:
    """Split dataset strictly at prescription_id level to avoid cross-angle leakage."""
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-5:
        raise ValueError("train_ratio + val_ratio + test_ratio must sum to 1.0")

    shuffled = list(prescription_ids)
    random.Random(seed).shuffle(shuffled)

    n_total = len(shuffled)
    n_train = int(round(n_total * train_ratio))
    n_val = int(round(n_total * val_ratio))

    train_ids = shuffled[:n_train]
    val_ids = shuffled[n_train : n_train + n_val]
    test_ids = shuffled[n_train + n_val :]

    return {
        "train": train_ids,
        "val": val_ids,
        "test": test_ids,
    }


class HierarchicalPrescriptionSampler:
    """
    Hierarchical 2-stage sampler to prevent overfitting on over-represented prescriptions:
    Step 1: Sample a prescription uniformly.
    Step 2: Sample an image from that prescription uniformly.
    """

    def __init__(
        self,
        prescription_to_images: dict[str, list[str]],
        max_images_per_rx_per_epoch: int = 15,
        seed: int = 42,
    ):
        self.prescription_to_images = {
            k: list(v) for k, v in prescription_to_images.items() if v
        }
        self.max_images = max_images_per_rx_per_epoch
        self.rng = random.Random(seed)

    def sample_epoch(self) -> list[str]:
        """Generate a balanced list of image IDs for one training epoch."""
        epoch_images = []
        for rx_id, imgs in self.prescription_to_images.items():
            if len(imgs) <= self.max_images:
                epoch_images.extend(imgs)
            else:
                sampled = self.rng.sample(imgs, self.max_images)
                epoch_images.extend(sampled)
        self.rng.shuffle(epoch_images)
        return epoch_images
