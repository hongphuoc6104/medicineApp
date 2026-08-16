"""Deterministic instruction decomposition and canonical GT validation."""

from __future__ import annotations

import re
from pathlib import Path

from rxie.grouping import CanonicalMedication, CanonicalPrescriptionGT

# Exhaustive decomposition table for all 32 unique instruction patterns in canonical GT
DECOMPOSITION_TABLE: dict[str, dict[str, str | None]] = {
    "Bôi vùng nấm 2 lần/ngày": {
        "dosage_raw": None,
        "frequency_raw": "2 lần/ngày",
        "duration_raw": None,
        "route_raw": "Bôi",
        "form_raw": None,
        "instruction_raw": "vùng nấm",
    },
    "Bôi vùng đau 2 lần/ngày": {
        "dosage_raw": None,
        "frequency_raw": "2 lần/ngày",
        "duration_raw": None,
        "route_raw": "Bôi",
        "form_raw": None,
        "instruction_raw": "vùng đau",
    },
    "Ngày uống 1 viên buổi sáng": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "buổi sáng",
    },
    "Ngày uống 1 viên buổi sáng trước ăn": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "buổi sáng trước ăn",
    },
    "Ngày uống 1 viên buổi tối": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "buổi tối",
    },
    "Ngày uống 1 viên buổi tối (khi ngứa mũi)": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "buổi tối (khi ngứa mũi)",
    },
    "Ngày uống 1 viên sau ăn": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn",
    },
    "Ngày uống 1 viên sau ăn no": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn no",
    },
    "Ngày uống 1 viên sau ăn no (khi đau)": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn no (khi đau)",
    },
    "Ngày uống 1 viên sau ăn trưa": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn trưa",
    },
    "Ngày uống 1 viên sáng": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sáng",
    },
    "Ngày uống 1 viên trước ăn sáng 30 phút": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "trước ăn sáng 30 phút",
    },
    "Ngày uống 1 viên tối": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "tối",
    },
    "Ngày uống 1-2 viên sau ăn tối": {
        "dosage_raw": "1-2 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn tối",
    },
    "Ngày uống 1-2 viên trước khi ngủ": {
        "dosage_raw": "1-2 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "trước khi ngủ",
    },
    "Ngày uống 1/2 viên tối": {
        "dosage_raw": "1/2 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "tối",
    },
    "Ngày uống 2 lần, mỗi lần 1 viên": {
        "dosage_raw": "1 viên",
        "frequency_raw": "2 lần",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": None,
    },
    "Ngày uống 2 lần, mỗi lần 1 viên sau ăn": {
        "dosage_raw": "1 viên",
        "frequency_raw": "2 lần",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn",
    },
    "Ngày uống 2 viên (sáng, tối)": {
        "dosage_raw": "2 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sáng, tối",
    },
    "Ngày uống 2 viên sau ăn": {
        "dosage_raw": "2 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn",
    },
    "Ngày uống 2 viên sau ăn tối": {
        "dosage_raw": "2 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn tối",
    },
    "Ngày uống 2 viên trước ăn": {
        "dosage_raw": "2 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "trước ăn",
    },
    "Ngày uống 3 viên sau ăn": {
        "dosage_raw": "3 viên",
        "frequency_raw": "Ngày",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn",
    },
    "Nhỏ mắt khi khô, 3-4 lần/ngày": {
        "dosage_raw": None,
        "frequency_raw": "3-4 lần/ngày",
        "duration_raw": None,
        "route_raw": "Nhỏ mắt",
        "form_raw": None,
        "instruction_raw": "khi khô",
    },
    "Nhỏ mắt khi mỏi, khô": {
        "dosage_raw": None,
        "frequency_raw": None,
        "duration_raw": None,
        "route_raw": "Nhỏ mắt",
        "form_raw": None,
        "instruction_raw": "khi mỏi, khô",
    },
    "Sáng uống 1 viên (hòa tan trong nước)": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Sáng",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "hòa tan trong nước",
    },
    "Sáng uống 1 ống sau ăn": {
        "dosage_raw": "1 ống",
        "frequency_raw": "Sáng",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn",
    },
    "Tiêm dưới da 10 đơn vị buổi tối": {
        "dosage_raw": "10 đơn vị",
        "frequency_raw": None,
        "duration_raw": None,
        "route_raw": "Tiêm dưới da",
        "form_raw": None,
        "instruction_raw": "buổi tối",
    },
    "Trưa uống 1 viên sau ăn": {
        "dosage_raw": "1 viên",
        "frequency_raw": "Trưa",
        "duration_raw": None,
        "route_raw": "uống",
        "form_raw": None,
        "instruction_raw": "sau ăn",
    },
    "Uống 1 viên buổi sáng": {
        "dosage_raw": "1 viên",
        "frequency_raw": "buổi sáng",
        "duration_raw": None,
        "route_raw": "Uống",
        "form_raw": None,
        "instruction_raw": None,
    },
    "Uống 1 viên khi đau đầu, cách mỗi 4 - 6 giờ": {
        "dosage_raw": "1 viên",
        "frequency_raw": "cách mỗi 4 - 6 giờ",
        "duration_raw": None,
        "route_raw": "Uống",
        "form_raw": None,
        "instruction_raw": "khi đau đầu",
    },
    "Uống 1 viên khi đau/sốt, cách mỗi 4-6h": {
        "dosage_raw": "1 viên",
        "frequency_raw": "cách mỗi 4-6h",
        "duration_raw": None,
        "route_raw": "Uống",
        "form_raw": None,
        "instruction_raw": "khi đau/sốt",
    },
}

VALID_PACKAGING_UNITS = {
    "Viên",
    "Ống",
    "Lọ",
    "Tuýp",
    "Bút tiêm",
    "Viên sủi",
    "Gói",
    "Chai",
}
STRENGTH_REGEX = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mg|g|mcg|ml|iu|ui|u|%)\b", re.IGNORECASE
)


def decompose_instruction(instruction_raw: str | None) -> dict[str, str | None]:
    """
    Decompose a composite instruction_raw string into atomic clinical fields.

    Returns a dict with 12 keys:
      - dosage_raw, dosage_normalized
      - frequency_raw, frequency_normalized
      - duration_raw, duration_normalized
      - route_raw, route_normalized
      - form_raw, form_normalized
      - instruction_raw, instruction_normalized
    """
    if not instruction_raw or not instruction_raw.strip():
        return {
            "dosage_raw": None,
            "dosage_normalized": None,
            "frequency_raw": None,
            "frequency_normalized": None,
            "duration_raw": None,
            "duration_normalized": None,
            "route_raw": None,
            "route_normalized": None,
            "form_raw": None,
            "form_normalized": None,
            "instruction_raw": None,
            "instruction_normalized": None,
        }

    raw = instruction_raw.strip()

    # Fast path: check exact table match
    if raw in DECOMPOSITION_TABLE:
        entry = DECOMPOSITION_TABLE[raw]
        dosage_raw = entry["dosage_raw"]
        frequency_raw = entry["frequency_raw"]
        duration_raw = entry["duration_raw"]
        route_raw = entry["route_raw"]
        form_raw = entry["form_raw"]
        inst_raw = entry["instruction_raw"]

        return {
            "dosage_raw": dosage_raw,
            "dosage_normalized": dosage_raw.lower() if dosage_raw else None,
            "frequency_raw": frequency_raw,
            "frequency_normalized": frequency_raw.lower() if frequency_raw else None,
            "duration_raw": duration_raw,
            "duration_normalized": duration_raw.lower() if duration_raw else None,
            "route_raw": route_raw,
            "route_normalized": route_raw.lower() if route_raw else None,
            "form_raw": form_raw,
            "form_normalized": form_raw.lower() if form_raw else None,
            "instruction_raw": inst_raw,
            "instruction_normalized": inst_raw.lower() if inst_raw else None,
        }

    # Rule-based fallback regex parsing
    route_raw = None
    route_match = re.search(r"(Tiêm dưới da|Tiêm bắp|Nhỏ mắt|Bôi|[Uu]ống)", raw)
    if route_match:
        route_raw = route_match.group(1)

    dosage_raw = None
    form_raw = None
    dose_units = "viên sủi|viên|ống|đơn vị|gói|giọt|ml|bút tiêm|lọ|tuýp"
    moi_lan_match = re.search(
        rf"mỗi lần\s+(\d+(?:/\d+)?|\d+\.\d+|\d+\s*-\s*\d+)\s*({dose_units})",
        raw,
        re.IGNORECASE,
    )
    if moi_lan_match:
        dosage_raw = f"{moi_lan_match.group(1)} {moi_lan_match.group(2)}"
        form_raw = moi_lan_match.group(2).lower()
    else:
        dose_match = re.search(
            rf"(\d+(?:/\d+)?|\d+\.\d+|\d+\s*-\s*\d+)\s*({dose_units})",
            raw,
            re.IGNORECASE,
        )
        if dose_match:
            dosage_raw = f"{dose_match.group(1)} {dose_match.group(2)}"
            form_raw = None

    frequency_raw = None
    lan_ngay = re.search(r"(\d+(?:-\d+)?\s*lần/ngày)", raw, re.IGNORECASE)
    if lan_ngay:
        frequency_raw = lan_ngay.group(1)
    elif re.search(r"\b(\d+\s*lần)\b", raw, re.IGNORECASE):
        m = re.search(r"\b(\d+\s*lần)\b", raw, re.IGNORECASE)
        if m:
            frequency_raw = m.group(1)
    elif re.search(r"(cách mỗi\s+\d+\s*(?:-\s*\d+)?\s*(?:giờ|h))", raw, re.IGNORECASE):
        m = re.search(
            r"(cách mỗi\s+\d+\s*(?:-\s*\d+)?\s*(?:giờ|h))", raw, re.IGNORECASE
        )
        if m:
            frequency_raw = m.group(1)
    elif raw.startswith("Ngày"):
        frequency_raw = "Ngày"
    elif raw.startswith("Sáng"):
        frequency_raw = "Sáng"
    elif raw.startswith("Trưa"):
        frequency_raw = "Trưa"
    elif raw.startswith("Uống") and "buổi sáng" in raw:
        frequency_raw = "buổi sáng"
    elif "buổi tối" in raw:
        frequency_raw = "buổi tối"

    duration_raw = None
    dur_match = re.search(
        r"(trong\s+\d+\s*(?:ngày|tuần|tháng)|\b\d+\s*(?:ngày|tuần|tháng)\b)",
        raw,
        re.IGNORECASE,
    )
    if dur_match:
        duration_raw = dur_match.group(1)

    residual_inst = None
    if "(khi ngứa mũi)" in raw:
        residual_inst = "khi ngứa mũi"
    elif "(khi đau)" in raw:
        residual_inst = "sau ăn no (khi đau)"
    elif "(hòa tan trong nước)" in raw:
        residual_inst = "hòa tan trong nước"
    elif "(sáng, tối)" in raw:
        residual_inst = "sáng, tối"
    elif "khi ngứa mũi" in raw:
        residual_inst = "khi ngứa mũi"
    elif "khi đau đầu" in raw:
        residual_inst = "khi đau đầu"
    elif "khi đau/sốt" in raw:
        residual_inst = "khi đau/sốt"
    elif "khi mỏi, khô" in raw:
        residual_inst = "khi mỏi, khô"
    elif "khi khô" in raw:
        residual_inst = "khi khô"
    elif "vùng nấm" in raw:
        residual_inst = "vùng nấm"
    elif "vùng đau" in raw:
        residual_inst = "vùng đau"
    elif "trước ăn sáng 30 phút" in raw:
        residual_inst = "trước ăn sáng 30 phút"
    elif "trước khi ngủ" in raw:
        residual_inst = "trước khi ngủ"
    elif "sau ăn tối" in raw:
        residual_inst = "sau ăn tối"
    elif "sau ăn trưa" in raw:
        residual_inst = "sau ăn trưa"
    elif "sau ăn no" in raw:
        residual_inst = "sau ăn no"
    elif "trước ăn" in raw:
        residual_inst = "trước ăn"
    elif "sau ăn" in raw:
        residual_inst = "sau ăn"
    elif "buổi sáng" in raw:
        residual_inst = "buổi sáng"
    elif "buổi tối" in raw:
        residual_inst = "buổi tối"
    elif "mỗi lần 1 viên" in raw:
        residual_inst = "mỗi lần 1 viên"
    elif raw.endswith("sáng"):
        residual_inst = "sáng"
    elif raw.endswith("tối"):
        residual_inst = "tối"

    return {
        "dosage_raw": dosage_raw,
        "dosage_normalized": dosage_raw.lower() if dosage_raw else None,
        "frequency_raw": frequency_raw,
        "frequency_normalized": frequency_raw.lower() if frequency_raw else None,
        "duration_raw": duration_raw,
        "duration_normalized": duration_raw.lower() if duration_raw else None,
        "route_raw": route_raw,
        "route_normalized": route_raw.lower() if route_raw else None,
        "form_raw": form_raw,
        "form_normalized": form_raw.lower() if form_raw else None,
        "instruction_raw": residual_inst,
        "instruction_normalized": residual_inst.lower() if residual_inst else None,
    }


def decompose_medication(med: CanonicalMedication) -> CanonicalMedication:
    """Decompose instruction_raw and populate atomic fields of a CanonicalMedication."""
    orig = med.instruction_original_raw or med.instruction_raw
    if not orig:
        return med

    decomposed = decompose_instruction(orig)
    updated_data = med.model_dump()
    updated_data["instruction_original_raw"] = orig
    updated_data["dosage_raw"] = decomposed["dosage_raw"]
    updated_data["dosage_normalized"] = decomposed["dosage_normalized"]
    updated_data["frequency_raw"] = decomposed["frequency_raw"]
    updated_data["frequency_normalized"] = decomposed["frequency_normalized"]
    updated_data["duration_raw"] = decomposed["duration_raw"]
    updated_data["duration_normalized"] = decomposed["duration_normalized"]
    updated_data["route_raw"] = decomposed["route_raw"]
    updated_data["route_normalized"] = decomposed["route_normalized"]
    updated_data["form_raw"] = decomposed["form_raw"]
    updated_data["form_normalized"] = decomposed["form_normalized"]
    updated_data["instruction_raw"] = decomposed["instruction_raw"]
    updated_data["instruction_normalized"] = decomposed["instruction_normalized"]

    return CanonicalMedication.model_validate(updated_data)


def decompose_prescription(
    prescription: CanonicalPrescriptionGT,
) -> CanonicalPrescriptionGT:
    """Decompose all medications within a CanonicalPrescriptionGT."""
    updated_meds = [decompose_medication(m) for m in prescription.medications]
    return prescription.model_copy(update={"medications": updated_meds})


def format_quantity_span(
    quantity_value_raw: str | None, quantity_unit_raw: str | None
) -> str:
    """Format quantity value and unit into a single span string (e.g. '30 Viên')."""
    val = (quantity_value_raw or "").strip()
    unit = (quantity_unit_raw or "").strip()
    if val and unit:
        return f"{val} {unit}"
    return val or unit


def validate_canonical_medication(med: CanonicalMedication) -> tuple[bool, list[str]]:
    """Validate a canonical medication record against clinical and schema policies."""
    errors: list[str] = []

    if not med.medication_id or not re.match(r"^RX_\d{3}_M\d{2}$", med.medication_id):
        errors.append(f"Invalid medication_id format: '{med.medication_id}'")

    if not med.drug_raw or not med.drug_raw.strip():
        errors.append(f"Medication {med.medication_id} missing drug_raw")

    # Policy 1: drug_normalized must not contain dosage strength
    if med.drug_normalized and STRENGTH_REGEX.search(med.drug_normalized):
        errors.append(
            f"Policy 1 violation in {med.medication_id}: "
            f"drug_normalized '{med.drug_normalized}' contains strength"
        )

    # Policy 2: quantity must be present with valid packaging unit
    if med.quantity_unit_raw and med.quantity_unit_raw not in VALID_PACKAGING_UNITS:
        errors.append(
            f"Policy 2 violation in {med.medication_id}: "
            f"invalid packaging unit '{med.quantity_unit_raw}'"
        )

    return len(errors) == 0, errors


def validate_canonical_gt(prescription: CanonicalPrescriptionGT) -> bool:
    """Validate a CanonicalPrescriptionGT document."""
    if prescription.schema_version != "rxie.canonical_gt.v1":
        return False
    if not re.match(r"^RX_\d{3}$", prescription.prescription_id):
        return False
    if not re.match(r"^PAT_\d{3}$", prescription.patient_id):
        return False

    med_ids: set[str] = set()
    for med in prescription.medications:
        if med.medication_id in med_ids:
            return False
        med_ids.add(med.medication_id)
        if not med.medication_id.startswith(f"{prescription.prescription_id}_M"):
            return False
        is_valid, _ = validate_canonical_medication(med)
        if not is_valid:
            return False

    return True


def load_canonical_prescription(path: str | Path) -> CanonicalPrescriptionGT:
    """Load a CanonicalPrescriptionGT instance from a JSON file."""
    p = Path(path)
    content = p.read_text(encoding="utf-8")
    return CanonicalPrescriptionGT.model_validate_json(content)


def save_canonical_prescription(rx: CanonicalPrescriptionGT, path: str | Path) -> None:
    """Save a CanonicalPrescriptionGT instance to a JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(rx.model_dump_json(indent=2) + "\n", encoding="utf-8")


def validate_all_canonical_gt(directory: Path | str) -> dict[str, bool]:
    """Validate all CanonicalPrescriptionGT files in a directory."""
    p = Path(directory)
    results: dict[str, bool] = {}
    for f in sorted(p.glob("RX_*.json")):
        doc = load_canonical_prescription(f)
        results[doc.prescription_id] = validate_canonical_gt(doc)
    return results


def batch_decompose_canonical_gt(
    source_dir: str | Path,
    target_dir: str | Path | None = None,
) -> dict[str, CanonicalPrescriptionGT]:
    """
    Decompose all canonical ground truth JSON files in source_dir.
    Optionally save results to target_dir.
    Returns mapping of prescription_id -> CanonicalPrescriptionGT.
    """
    src = Path(source_dir)
    results: dict[str, CanonicalPrescriptionGT] = {}
    for json_file in sorted(src.glob("*.json")):
        rx = load_canonical_prescription(json_file)
        decomposed_rx = decompose_prescription(rx)
        results[decomposed_rx.prescription_id] = decomposed_rx
        if target_dir is not None:
            tgt = Path(target_dir)
            tgt.mkdir(parents=True, exist_ok=True)
            save_canonical_prescription(decomposed_rx, tgt / json_file.name)
    return results
