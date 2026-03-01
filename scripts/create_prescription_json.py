"""
create_prescription_json.py — Generate synthetic prescription JSON files for Zero-PIMA training.

What this does:
  - Uses the 107 drug labels from Zero-PIMA config.py
  - Generates realistic prescription layouts (hospital header, patient info,
    drug table rows, dosage/notes)
  - Outputs Zero-PIMA format: list of {text, label, box, mapping}
  - Saves to data/pres/train/ and data/pres/test/

Usage:
    python scripts/create_prescription_json.py --train 15 --test 5

Output:
    data/pres/train/pres_001.json ... pres_015.json
    data/pres/test/pres_001.json  ... pres_005.json
"""

import os
import sys
import json
import random
import argparse
from pathlib import Path

# Allow importing Zero-PIMA config
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "Zero-PIMA"))
import config as PIMA_CFG

# ── Constants ──────────────────────────────────────────────────────────────────

ALL_LABELS = list(PIMA_CFG.ALL_PILL_LABELS.keys())

HOSPITALS = [
    "BVĐK TW CẦN THƠ",
    "BV ĐA KHOA TỈNH ĐỒNG NAI",
    "BV CHỢ RẪY TP. HỒ CHÍ MINH",
    "BV NHÂN DÂN 115",
    "BV ĐẠI HỌC Y DƯỢC TP.HCM",
]

DOCTORS = [
    "Nguyễn Văn A", "Trần Thị B", "Lê Văn C",
    "Phạm Thị D", "Hoàng Văn E", "Đỗ Thị F",
]

PATIENTS = [
    ("Nguyễn Văn An", 45, "Nam"),
    ("Trần Thị Bình", 62, "Nữ"),
    ("Lê Văn Cường", 33, "Nam"),
    ("Phạm Thị Dung", 55, "Nữ"),
    ("Hoàng Văn Em", 70, "Nam"),
    ("Đỗ Thị Phương", 28, "Nữ"),
    ("Vũ Quốc Hùng", 48, "Nam"),
    ("Bùi Thị Lan", 59, "Nữ"),
]

SESSIONS = [
    "Sáng uống 1 viên sau ăn",
    "Tối uống 1 viên trước khi ngủ",
    "Ngày uống 1 viên sau ăn trưa",
    "Sáng và tối uống 1 viên",
    "Uống 1 gói trước ăn sáng",
    "Nhỏ mắt khi cần",
    "Ngày uống 2 lần, mỗi lần 1 viên",
    "Uống 1 viên trước ăn 30 phút",
]

UNITS = ["Viên", "Gói", "Lọ", "Ống", "Hộp"]

DIAGNOSES = [
    ("I10", "Tăng huyết áp vô căn"),
    ("E11", "Đái tháo đường type 2"),
    ("E78.0", "Tăng cholesterol máu"),
    ("I25.1", "Bệnh tim thiếu máu cục bộ mạn"),
    ("M17", "Thoái hóa khớp gối"),
    ("J44.9", "COPD"),
    ("K21", "Bệnh trào ngược dạ dày - thực quản"),
    ("Z95.4", "Có van tim nhân tạo"),
]

# ── Image canvas size (virtual prescription image 1000×1000) ──────────────────
IMG_W, IMG_H = 1000, 1000


# ── Builder ────────────────────────────────────────────────────────────────────

def _box(x1, y1, x2, y2):
    return [x1, y1, x2, y2]


def _block(text: str, label: str, box: list, mapping=None) -> dict:
    return {"text": text, "label": label, "box": box, "mapping": mapping}


def generate_prescription(drugs_in_pres: list[str]) -> list[dict]:
    """
    Generate one prescription JSON as a list of Zero-PIMA text blocks.

    Args:
        drugs_in_pres: List of canonical drug labels to include in this prescription.
                       Must all be keys in ALL_PILL_LABELS.

    Returns:
        list of Zero-PIMA block dicts.
    """
    blocks = []
    hospital = random.choice(HOSPITALS)
    doctor   = random.choice(DOCTORS)
    patient_name, patient_age, gender = random.choice(PATIENTS)
    diag_count = random.randint(1, 3)
    diagnoses  = random.sample(DIAGNOSES, min(diag_count, len(DIAGNOSES)))

    y = 30  # current y cursor

    # ── Header ──
    blocks.append(_block("BỘ Y TẾ", "other", _box(350, y, 650, y+30)))
    y += 35
    blocks.append(_block(hospital, "other", _box(100, y, 600, y+30)))
    y += 35
    blocks.append(_block("ĐƠN THUỐC", "other", _box(380, y, 620, y+35)))
    y += 45

    # ── Patient info ──
    blocks.append(_block(f"Họ tên: {patient_name}", "other", _box(80, y, 450, y+28)))
    blocks.append(_block(f"Tuổi: {patient_age}", "other", _box(460, y, 580, y+28)))
    blocks.append(_block(f"Giới tính: {gender}", "other", _box(590, y, 750, y+28)))
    y += 35

    # ── Diagnosis ──
    blocks.append(_block("Chẩn đoán:", "other", _box(80, y, 200, y+27)))
    for code, desc in diagnoses:
        y += 30
        blocks.append(_block(f"{code}: {desc}", "other", _box(210, y, 850, y+27)))
    y += 40

    # ── Drug table header ──
    blocks.append(_block("Thuốc điều trị:", "other", _box(80, y, 280, y+28)))
    y += 35
    blocks.append(_block("STT", "other", _box(80,  y, 150, y+27)))
    blocks.append(_block("Tên thuốc",      "other", _box(160, y, 500, y+27)))
    blocks.append(_block("SL",  "other", _box(510, y, 570, y+27)))
    blocks.append(_block("ĐVT", "other", _box(580, y, 650, y+27)))
    blocks.append(_block("Cách dùng",       "other", _box(660, y, 920, y+27)))
    y += 35

    # ── Drug rows ──
    for i, drug_label in enumerate(drugs_in_pres, start=1):
        # Convert canonical label to display-ish name
        display_name = drug_label.replace("-", " ")
        quantity = random.randint(10, 60)
        unit     = random.choice(UNITS)
        session  = random.choice(SESSIONS)

        # Drug name block (label=drugname)
        blocks.append(_block(
            display_name, "drugname",
            _box(160, y, 500, y+30),
            mapping=drug_label
        ))
        blocks.append(_block(str(i),       "other", _box(80,  y, 150, y+30)))
        blocks.append(_block(str(quantity), "other", _box(510, y, 570, y+30)))
        blocks.append(_block(unit,          "other", _box(580, y, 650, y+30)))
        y += 32
        blocks.append(_block(session, "other", _box(160, y, 800, y+27)))
        y += 35

    # ── Footer ──
    y += 10
    blocks.append(_block(f"Bác sĩ kê đơn: {doctor}", "other", _box(550, y, 900, y+28)))

    return blocks


def save_blocks(blocks: list, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(blocks, f, ensure_ascii=False, indent=2)
    drug_blocks = [b for b in blocks if b["label"] == "drugname"]
    print(f"  ✅ {output_path}  ({len(blocks)} blocks, {len(drug_blocks)} drugs)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic prescription JSONs for Zero-PIMA")
    parser.add_argument("--train", type=int, default=15, help="Number of training prescriptions")
    parser.add_argument("--test",  type=int, default=5,  help="Number of test prescriptions")
    parser.add_argument("--min-drugs", type=int, default=3, help="Min drugs per prescription")
    parser.add_argument("--max-drugs", type=int, default=7, help="Max drugs per prescription")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    output_root = project_root / "data" / "pres"

    splits = [
        ("train", args.train, output_root / "train"),
        ("test",  args.test,  output_root / "test"),
    ]

    print(f"\n{'='*60}")
    print(f"  Generating prescriptions (seed={args.seed})")
    print(f"  Available drugs: {len(ALL_LABELS)}")
    print(f"{'='*60}")

    for split_name, count, out_dir in splits:
        print(f"\n[{split_name.upper()}] — {count} prescriptions → {out_dir}")
        for idx in range(1, count + 1):
            n_drugs = random.randint(args.min_drugs, args.max_drugs)
            drugs   = random.sample(ALL_LABELS, min(n_drugs, len(ALL_LABELS)))
            blocks  = generate_prescription(drugs)
            out_file = str(out_dir / f"pres_{idx:03d}.json")
            save_blocks(blocks, out_file)

    print(f"\n{'='*60}")
    print(f"  Done!  {args.train} train + {args.test} test prescriptions saved.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
