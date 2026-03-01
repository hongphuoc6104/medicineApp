"""
generate_vaipe_training_data.py
================================
Generate synthetic prescriptions in user's hospital format using VAIPE drugs.
Output: Zero-PIMA training format (prescription JSON + paired with VAIPE pill images).

Usage:
    python scripts/generate_vaipe_training_data.py --count 200
"""
import json
import os
import sys
import re
import random
import glob
from collections import defaultdict
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ── Paths ────────────────────────────────────────────────
VAIPE_KB = os.path.join(ROOT, "data", "vaipe_drugs_kb.json")
VAIPE_PRES = os.path.join(
    ROOT, "VAIPE_Full/content/dataset/train/prescription/labels"
)
VAIPE_PILLS = os.path.join(
    ROOT, "VAIPE_Full/content/dataset/train/pill"
)
OUTPUT_DIR = os.path.join(ROOT, "data", "synthetic_train")

# ── Load VAIPE drug KB ───────────────────────────────────
with open(VAIPE_KB, encoding="utf-8") as f:
    VAIPE_DRUGS = json.load(f)

print(f"Loaded {len(VAIPE_DRUGS)} VAIPE drugs")

# ── Instructions templates ───────────────────────────────
INSTRUCTIONS = [
    "Ngày uống {n} lần, mỗi lần 1 viên",
    "Uống {n} viên/ngày sau ăn",
    "Ngày uống {n} viên (sáng{extra})",
    "Sáng uống {n} viên sau ăn",
    "Uống {n} viên khi đau/sốt, cách 4-6h",
    "Ngày uống {n} lần, mỗi lần 1 viên sau ăn",
]

UNITS = ["Viên", "Viên", "Viên", "Viên", "Gói", "Ống", "Lọ",
         "Viên sủi", "Viên nang"]

HOSPITALS = [
    {"ministry": "BỘ Y TẾ", "name": "BVĐK TW CẦN THƠ",
     "phone": "0292.382.0071"},
    {"ministry": "BỘ Y TẾ", "name": "BỆNH VIỆN CHỢ RẪY",
     "phone": "028.3855.4137"},
    {"ministry": "SỞ Y TẾ TP.HCM", "name": "BỆNH VIỆN NHÂN DÂN 115",
     "phone": "028.3865.2368"},
    {"ministry": "BỘ Y TẾ", "name": "BỆNH VIỆN BẠCH MAI",
     "phone": "024.3869.3731"},
    {"ministry": "SỞ Y TẾ HÀ NỘI", "name": "BỆNH VIỆN XANH PÔN",
     "phone": "024.3823.3075"},
    {"ministry": "BỘ Y TẾ", "name": "BỆNH VIỆN ĐA KHOA TRUNG ƯƠNG",
     "phone": "024.3825.3531"},
]

DOCTORS = [
    "Nguyễn Văn A", "Trần Thị B", "Lê Vũ C", "Phạm Minh D",
    "Hoàng Thị E", "Vũ Văn F", "Đặng Quốc G", "Bùi Thị H",
    "Lê Thị Kim Đài", "Phan Văn K",
]

LAST_NAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh",
    "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ",
]
MIDDLE_NAMES = [
    "Văn", "Thị", "Hữu", "Đức", "Minh", "Thu",
    "Ngọc", "Thanh", "Quang", "Kim",
]
FIRST_NAMES = [
    "An", "Bình", "Cường", "Dung", "Giang", "Hải",
    "Lan", "Mai", "Oanh", "Khoa", "Phúc", "Tâm",
    "Thảo", "Hùng", "Sơn", "Tùng", "Trang",
]

DIAGNOSES = [
    ("J00", "Viêm mũi họng cấp"),
    ("J20.9", "Viêm phế quản cấp"),
    ("I10", "Tăng huyết áp vô căn"),
    ("I25.1", "Bệnh tim thiếu máu cục bộ mạn"),
    ("E11", "Đái tháo đường type 2"),
    ("E78.0", "Tăng cholesterol máu"),
    ("K21.9", "Trào ngược dạ dày-thực quản"),
    ("M17", "Thoái hóa khớp gối"),
    ("M54.5", "Đau thắt lưng"),
    ("G47.0", "Rối loạn giấc ngủ"),
    ("H04.1", "Hội chứng khô mắt"),
    ("K73.9", "Viêm gan mạn tính"),
    ("Z95.4", "Sự có mặt của van tim thay thế"),
]

ADDRESSES = [
    "Ấp 3, Xã Vị Thủy, TP Cần Thơ",
    "123 Nguyễn Huệ, Q.1, TP.HCM",
    "456 Trần Hưng Đạo, Hà Nội",
    "789 Lê Lợi, Đà Nẵng",
    "12 CMT8, Cần Thơ",
    "34 Võ Văn Kiệt, Q.5, TP.HCM",
]


def random_patient():
    gender = random.choice(["Nam", "Nữ"])
    name = (
        f"{random.choice(LAST_NAMES)} "
        f"{random.choice(MIDDLE_NAMES)} "
        f"{random.choice(FIRST_NAMES)}"
    )
    age = random.randint(20, 85)
    bhyt = f"BT{random.randint(2900000000, 9999999999)}"
    addr = random.choice(ADDRESSES)
    return name, age, gender, bhyt, addr


def random_instruction(n_per_day=None):
    n = n_per_day or random.choice([1, 2, 2, 3])
    extra = ", tối" if n >= 2 else ""
    tmpl = random.choice(INSTRUCTIONS)
    return tmpl.format(n=n, extra=extra)


def generate_prescription_json(pres_id, drug_ids):
    """
    Generate one prescription in Zero-PIMA training format.

    Returns: list of text block dicts (prescription label JSON)
    """
    hospital = random.choice(HOSPITALS)
    name, age, gender, bhyt, addr = random_patient()
    diag_codes = random.sample(DIAGNOSES, k=random.randint(1, 3))
    diag_str = "; ".join(
        f"{code}: {desc}" for code, desc in diag_codes
    )
    doctor = random.choice(DOCTORS)
    date = datetime(2026, 2, random.randint(1, 28))
    date_str = date.strftime("ngày %d tháng %m năm %Y")

    blocks = []
    y = 30
    line_h = 35

    def add_block(text, label="other", mapping=None, x=50, w=600):
        nonlocal y
        box = [x, y, x + w, y + line_h]
        b = {"text": text, "label": label, "box": box}
        if mapping is not None:
            b["mapping"] = mapping
        blocks.append(b)
        y += line_h + random.randint(2, 8)

    # Header
    add_block(hospital["ministry"], x=200, w=200)
    add_block(f"ĐƠN THUỐC {hospital['name']}", x=100, w=500)
    add_block(f"ĐIỆN THOẠI: {hospital['phone']}", x=100, w=300)

    # Patient info
    add_block(
        f"Họ tên: {name} Tuổi: {age} Giới tính: {gender}"
    )
    add_block(f"Mã số thẻ BHYT: {bhyt}")
    add_block(f"Địa chỉ liên hệ: {addr}")
    add_block(f"Chẩn Đoán: {diag_str}")
    add_block("Thuốc điều trị:")

    # Table header
    add_block("STT Thuốc điều trị")

    # Medications
    for i, did in enumerate(drug_ids, 1):
        did_str = str(did)
        drug = VAIPE_DRUGS.get(did_str, None)
        if drug is None:
            continue

        brand = drug["brand"]
        dosage = drug["dosage"]
        # Build drug text — similar to user's real prescriptions
        texts = drug.get("sample_texts", [])
        if texts:
            # Use the raw VAIPE text sometimes for variety
            if random.random() < 0.4 and len(texts) > 0:
                drug_text = random.choice(texts)
                # Remove number prefix
                drug_text = re.sub(r'^\d+[).\s]+', '', drug_text)
            else:
                drug_text = f"{brand} {dosage}".strip()
        else:
            drug_text = f"{brand} {dosage}".strip()

        # Add STT + drugname
        qty = random.choice([7, 10, 14, 20, 28, 30, 60])
        unit = random.choice(UNITS)
        instr = random_instruction()

        add_block(
            f"{drug_text} {dosage} {i:02d}",
            label="drugname",
            mapping=did,
        )

        # Sometimes add unit on same line, sometimes separate
        if random.random() < 0.5:
            add_block(unit)
        add_block(
            f"{qty} {instr}",
        )

    # Footer
    add_block(doctor)
    add_block(f"Cần Thơ, {date_str}")

    return blocks


def find_pill_images_for_drugs(drug_ids):
    """
    Find VAIPE pill images that contain the given drug IDs.

    Returns: list of (image_file, label_file) tuples
    """
    pill_label_dir = os.path.join(VAIPE_PILLS, "labels")
    pill_img_dir = os.path.join(VAIPE_PILLS, "images")

    matched = []
    drug_set = set(drug_ids)

    label_files = sorted(os.listdir(pill_label_dir))
    random.shuffle(label_files)

    for lf in label_files[:200]:  # Sample for speed
        lpath = os.path.join(pill_label_dir, lf)
        with open(lpath) as fp:
            pills = json.load(fp)

        pill_labels = {p["label"] for p in pills}
        # Check if any pill matches our drugs
        if pill_labels & drug_set:
            img_name = lf.replace(".json", ".jpg")
            img_path = os.path.join(pill_img_dir, img_name)
            if os.path.exists(img_path):
                matched.append((img_path, lpath))
                if len(matched) >= 5:
                    break

    return matched


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=200,
                        help="Number of prescriptions to generate")
    parser.add_argument("--drugs-per-pres", type=int, default=0,
                        help="Drugs per prescription (0=random 3-7)")
    args = parser.parse_args()

    # Output directories (Zero-PIMA format)
    pres_out = os.path.join(OUTPUT_DIR, "pres", "train")
    pill_img_out = os.path.join(OUTPUT_DIR, "pills", "train", "imgs")
    pill_lbl_out = os.path.join(OUTPUT_DIR, "pills", "train", "labels")
    os.makedirs(pres_out, exist_ok=True)
    os.makedirs(pill_img_out, exist_ok=True)
    os.makedirs(pill_lbl_out, exist_ok=True)

    all_drug_ids = list(VAIPE_DRUGS.keys())
    all_drug_ids_int = [int(x) for x in all_drug_ids]

    # Build index: drug_id -> list of (img, label) files
    print("Building pill image index...")
    pill_label_dir = os.path.join(VAIPE_PILLS, "labels")
    pill_img_dir = os.path.join(VAIPE_PILLS, "images")
    drug_to_pills = defaultdict(list)

    for lf in sorted(os.listdir(pill_label_dir)):
        lpath = os.path.join(pill_label_dir, lf)
        with open(lpath) as fp:
            pills = json.load(fp)

        pill_labels = {p["label"] for p in pills}
        img_name = lf.replace(".json", ".jpg")
        img_path = os.path.join(pill_img_dir, img_name)
        if not os.path.exists(img_path):
            continue

        for pl in pill_labels:
            drug_to_pills[pl].append({
                "img": img_path,
                "label_file": lpath,
                "label_data": pills,
            })

    print(f"  Indexed {sum(len(v) for v in drug_to_pills.values())} "
          f"pill entries across {len(drug_to_pills)} drug classes")

    # Generate prescriptions
    print(f"\nGenerating {args.count} synthetic prescriptions...")
    stats = {"total": 0, "paired": 0, "drugs": defaultdict(int)}
    import shutil

    for i in range(1, args.count + 1):
        # Pick random drugs
        n_drugs = args.drugs_per_pres or random.randint(3, 7)
        drug_ids = random.sample(all_drug_ids_int, min(n_drugs, len(all_drug_ids_int)))

        # Generate prescription JSON
        pres_blocks = generate_prescription_json(i, drug_ids)

        # Save prescription
        pres_name = f"synth_{i:04d}.json"
        pres_path = os.path.join(pres_out, pres_name)
        with open(pres_path, "w", encoding="utf-8") as f:
            json.dump(pres_blocks, f, ensure_ascii=False, indent=2)

        # Find pill image for these drugs
        # Pick a pill image that has at least one matching drug
        paired = False
        for did in drug_ids:
            pills = drug_to_pills.get(did, [])
            if pills:
                pill_entry = random.choice(pills)
                # Copy pill image
                dst_img = os.path.join(
                    pill_img_out, pres_name.replace(".json", ".jpg")
                )
                shutil.copy2(pill_entry["img"], dst_img)

                # Save pill labels
                dst_lbl = os.path.join(pill_lbl_out, pres_name)

                # Convert pill labels to expected format
                pill_labels = []
                for p in pill_entry["label_data"]:
                    pill_labels.append({
                        "x": p["x"], "y": p["y"],
                        "w": p["w"], "h": p["h"],
                        "label": p["label"],
                    })

                with open(dst_lbl, "w") as f:
                    json.dump({"boxes": pill_labels}, f)

                paired = True
                break

        stats["total"] += 1
        if paired:
            stats["paired"] += 1
        for did in drug_ids:
            stats["drugs"][did] += 1

        if i % 50 == 0:
            print(f"  Generated {i}/{args.count} "
                  f"(paired: {stats['paired']}/{stats['total']})")

    # Summary
    print(f"\n{'='*60}")
    print(f"DONE: Generated {stats['total']} prescriptions")
    print(f"  Paired with pill images: {stats['paired']}/{stats['total']}")
    print(f"  Drug classes used: {len(stats['drugs'])}")
    print(f"  Output: {OUTPUT_DIR}/")
    print(f"    pres/train/  → {stats['total']} prescription JSONs")
    print(f"    pills/train/ → {stats['paired']} pill image+label pairs")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
