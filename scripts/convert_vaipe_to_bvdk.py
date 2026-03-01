#!/usr/bin/env python3
"""
Convert VAIPE prescriptions 1:1 to BVĐK TW Cần Thơ format.

For each VAIPE prescription:
1. Extract drugs (drugname entries with mapping IDs)
2. Generate BVĐK-format prescription with SAME drugs
3. Render DOCX → PDF → PNG
4. Create new label JSON preserving mapping IDs

Usage:
    python scripts/convert_vaipe_to_bvdk.py --split train --batch-size 50
    python scripts/convert_vaipe_to_bvdk.py --split train --start 0 --end 100
"""

import json
import os
import sys
import re
import glob
import random
import shutil
import subprocess
import argparse
from datetime import datetime, timedelta

# Add project paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "createPrescription", "prescription_generator"))

from data_generator import MedicalKnowledgeBase

# ── Paths ────────────────────────────────────────────────
VAIPE_BASE = os.path.join(ROOT, "VAIPE_Full", "content", "dataset")
OUTPUT_BASE = os.path.join(ROOT, "data", "synthetic_train")
VAIPE_KB_PATH = os.path.join(ROOT, "data", "vaipe_drugs_kb.json")

# Load VAIPE drug KB for name mapping
with open(VAIPE_KB_PATH, encoding="utf-8") as f:
    VAIPE_KB = json.load(f)

# Load medical KB for drug info
MED_KB = MedicalKnowledgeBase()

# ── Drug mapping: VAIPE ID → data_generator drug key ─────
def build_vaipe_id_to_drug_key():
    """Map VAIPE drug IDs to data_generator drug keys."""
    mapping = {}
    for drug_key, drug_list in MED_KB.drugs.items():
        # Find which VAIPE ID this drug corresponds to
        for vid, vinfo in VAIPE_KB.items():
            name_lower = vinfo["name"].lower().replace("-", "_")
            key_lower = drug_key.lower()
            # Match by name similarity
            if name_lower == key_lower or name_lower.startswith(key_lower.split("_")[0]):
                mapping[int(vid)] = drug_key
                break
    return mapping

# Build a simpler mapping: VAIPE ID → drug info from KB
def build_vaipe_id_to_drug_info():
    """Direct mapping from VAIPE drug ID → drug entry for prescription."""
    result = {}
    for vid_str, vinfo in VAIPE_KB.items():
        vid = int(vid_str)
        name = vinfo["name"]
        brand = vinfo.get("brand", name)
        dosage = vinfo.get("dosage", "")
        
        # Find matching drug key in MED_KB
        drug_key = None
        for dk in MED_KB.drugs:
            dk_norm = dk.lower().replace("_", "")
            name_norm = name.lower().replace("-", "").replace("_", "")
            if dk_norm == name_norm or name_norm.startswith(dk_norm[:8]):
                drug_key = dk
                break
        
        if drug_key and drug_key in MED_KB.drugs:
            drug_info = MED_KB.drugs[drug_key][0]
            result[vid] = {
                "generic_name": drug_key.replace("_", " "),
                "brand_name": drug_info["brand"],
                "dosage": drug_info["dosage"],
                "unit": drug_info["unit"],
                "quantity": random.choice([7, 10, 14, 20, 28, 30]),
                "instructions": drug_info["instr"],
            }
        else:
            # Fallback: use VAIPE KB info directly
            result[vid] = {
                "generic_name": name.replace("-", " "),
                "brand_name": brand if brand else name.replace("-", " "),
                "dosage": dosage if dosage else "Tab",
                "unit": "Viên",
                "quantity": random.choice([7, 14, 28]),
                "instructions": "Ngày uống 2 lần, mỗi lần 1 viên",
            }
    return result

DRUG_INFO = build_vaipe_id_to_drug_info()

# ── Patient / Doctor generators ──────────────────────────
LAST_NAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh",
              "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ"]
MIDDLE_NAMES = ["Văn", "Thị", "Hữu", "Đức", "Minh", "Thu",
                "Ngọc", "Thanh", "Quang", "Mạnh", "Kim", "Xuân"]
FIRST_NAMES = ["An", "Bình", "Cường", "Dung", "Giang", "Hải",
               "Lan", "Mai", "Oanh", "Phúc", "Hùng", "Trang"]

DOCTORS = [
    {"name": "Nguyễn Văn A", "title": "BS.CKI"},
    {"name": "Trần Thị B", "title": "ThS.BS"},
    {"name": "Lê Vũ C", "title": "BS.CKII"},
    {"name": "Phạm Minh D", "title": "TS.BS"},
    {"name": "Hoàng Thị E", "title": "BS.CKI"},
    {"name": "Lê Thị Kim Đài", "title": "BS.CKI"},
]

ADDRESSES = [
    "Ấp 3, Xã Vị Thủy, TP Cần Thơ",
    "123 Nguyễn Huệ, Q.1, TP.HCM",
    "456 Trần Hưng Đạo, Hà Nội",
    "789 Lê Lợi, Đà Nẵng",
    "12 Đường CMT8, Cần Thơ",
]

DIAGNOSES = [
    "J00: Viêm mũi họng cấp", "J20.9: Viêm phế quản cấp",
    "I10: Tăng huyết áp vô căn", "E11: Đái tháo đường type 2",
    "K21.9: Trào ngược dạ dày", "M54.5: Đau thắt lưng",
    "G47.0: Rối loạn giấc ngủ", "K73.9: Viêm gan mạn tính",
    "M17: Thoái hóa khớp gối", "L20.9: Viêm da cơ địa",
]


def generate_patient():
    gender = random.choice(["Nam", "Nữ"])
    mid = random.choice(MIDDLE_NAMES)
    if gender == "Nam" and mid == "Thị":
        mid = "Văn"
    elif gender == "Nữ" and mid == "Văn":
        mid = "Thị"
    name = f"{random.choice(LAST_NAMES)} {mid} {random.choice(FIRST_NAMES)}"
    return {
        "name": name.upper(),
        "age": random.randint(20, 85),
        "gender": gender,
        "address": random.choice(ADDRESSES),
        "insurance_code": f"DN{random.randint(4000000000, 9999999999)}",
    }


def extract_drugs_from_vaipe(label_path):
    """Extract drug entries from a VAIPE prescription label."""
    with open(label_path, encoding="utf-8") as f:
        entries = json.load(f)
    
    drugs = []
    for entry in entries:
        if entry.get("label") == "drugname" and "mapping" in entry:
            drugs.append({
                "text": entry["text"],
                "mapping": entry["mapping"],
                "box": entry["box"],
            })
    return drugs


def create_bvdk_prescription(pres_id, vaipe_drugs):
    """Create a BVĐK-format prescription data dict from VAIPE drugs."""
    patient = generate_patient()
    doctor = random.choice(DOCTORS)
    
    # Build medications from VAIPE drugs
    medications = []
    for drug in vaipe_drugs:
        mid = drug["mapping"]
        if mid in DRUG_INFO:
            med = dict(DRUG_INFO[mid])  # copy
            med["quantity"] = random.choice([7, 10, 14, 20, 28, 30])
        else:
            # Unknown drug - use text directly
            med = {
                "generic_name": drug["text"],
                "brand_name": drug["text"],
                "dosage": "Tab",
                "unit": "Viên",
                "quantity": 14,
                "instructions": "Theo chỉ định bác sĩ",
            }
        medications.append(med)
    
    # Random date
    start = datetime(2025, 12, 1)
    end = datetime(2026, 12, 31)
    today = start + timedelta(days=random.randint(0, (end - start).days))
    follow_up_days = random.choice([7, 14, 28])
    follow_date = (today + timedelta(days=follow_up_days)).strftime("%d/%m/%Y")
    
    # Random diagnosis
    n_diag = random.choices([1, 2], weights=[0.6, 0.4])[0]
    diag = "; ".join(random.sample(DIAGNOSES, min(n_diag, len(DIAGNOSES))))
    
    return {
        "id": pres_id,
        "patient": patient,
        "prescription_code": f"25{random.randint(100000, 999999)}",
        "diagnosis": diag,
        "doctor": doctor,
        "medications": medications,
        "follow_up_date": follow_date,
        "prescription_date": today.strftime("ngày %d tháng %m năm %Y"),
        "notes": "",
        "lab_tests": "",
        "barcode_bottom": f"0000{pres_id:08d}",
        "duration_days": follow_up_days,
    }


def render_docx_to_png(docx_path, png_path, dpi=200):
    """Convert DOCX → PDF → PNG using LibreOffice + pdftoppm."""
    out_dir = os.path.dirname(docx_path)
    
    # DOCX → PDF
    subprocess.run([
        "libreoffice", "--headless", "--convert-to", "pdf",
        "--outdir", out_dir, docx_path
    ], capture_output=True, timeout=30)
    
    pdf_path = docx_path.replace(".docx", ".pdf")
    if not os.path.exists(pdf_path):
        return False
    
    # PDF → PNG
    png_prefix = png_path.replace(".png", "")
    subprocess.run([
        "pdftoppm", "-png", "-r", str(dpi), "-singlefile",
        pdf_path, png_prefix
    ], capture_output=True, timeout=30)
    
    # Cleanup PDF
    os.remove(pdf_path)
    
    return os.path.exists(png_path)


def create_label_from_vaipe(vaipe_label_path, new_format="bvdk"):
    """
    Create a new label JSON preserving mapping IDs but adjusting text+boxes
    for the new BVĐK format.
    
    Since we can't get exact bboxes from DOCX rendering, we create synthetic
    labels with approximate bboxes based on the BVĐK layout.
    """
    with open(vaipe_label_path, encoding="utf-8") as f:
        original = json.load(f)
    
    # Extract drug entries from original
    drugs = []
    other_entries = []
    for entry in original:
        if entry.get("label") == "drugname":
            drugs.append(entry)
        elif entry.get("label") in ("quantity", "usage"):
            other_entries.append(entry)
    
    # Build new label keeping drug info
    new_label = []
    entry_id = 1
    
    # Header entries (BVĐK format)
    img_w, img_h = 1165, 1653  # A5 at 200dpi
    
    new_label.append({
        "id": entry_id, "text": "BỘ Y TẾ",
        "label": "other", "box": [20, 20, 200, 50]
    })
    entry_id += 1
    
    new_label.append({
        "id": entry_id, "text": "BVĐK TW CẦN THƠ",
        "label": "other", "box": [20, 50, 250, 80]
    })
    entry_id += 1
    
    new_label.append({
        "id": entry_id, "text": "ĐƠN THUỐC",
        "label": "other", "box": [400, 30, 650, 70]
    })
    entry_id += 1
    
    # Patient info
    patient = generate_patient()
    new_label.append({
        "id": entry_id,
        "text": f"Họ tên: {patient['name']}",
        "label": "other",
        "box": [20, 110, 500, 140]
    })
    entry_id += 1
    
    # Diagnosis
    diag = random.choice(DIAGNOSES)
    new_label.append({
        "id": entry_id,
        "text": f"Chẩn Đoán: {diag}",
        "label": "diagnose",
        "box": [20, 200, 700, 230]
    })
    entry_id += 1
    
    # Drug entries - preserve mapping IDs
    y_start = 280
    y_step = 60
    for i, drug in enumerate(drugs):
        mid = drug.get("mapping", -1)
        
        # Get drug text in BVĐK format
        if mid in DRUG_INFO:
            info = DRUG_INFO[mid]
            text = f"{info['generic_name']} ({info['brand_name']} {info['dosage']}) {info['dosage']}"
        else:
            text = drug["text"]
        
        y = y_start + i * y_step
        entry = {
            "id": entry_id,
            "text": text,
            "label": "drugname",
            "box": [40, y, 700, y + 30],
            "mapping": mid
        }
        new_label.append(entry)
        entry_id += 1
        
        # Usage/instruction
        if mid in DRUG_INFO:
            instr_text = DRUG_INFO[mid]["instructions"]
        else:
            instr_text = "Theo chỉ định bác sĩ"
        
        new_label.append({
            "id": entry_id,
            "text": instr_text,
            "label": "usage",
            "box": [50, y + 25, 600, y + 50]
        })
        entry_id += 1
        
        # Quantity
        if mid in DRUG_INFO:
            qty = random.choice([7, 14, 20, 28])
            qty_text = f"SL: {qty} {DRUG_INFO[mid]['unit']}"
        else:
            qty_text = "SL: 14 Viên"
        
        new_label.append({
            "id": entry_id,
            "text": qty_text,
            "label": "quantity",
            "box": [700, y, 850, y + 30]
        })
        entry_id += 1
    
    # Footer
    new_label.append({
        "id": entry_id,
        "text": f"Ngày {datetime.now().strftime('ngày %d tháng %m năm %Y')}",
        "label": "date",
        "box": [500, img_h - 200, 800, img_h - 170]
    })
    
    return new_label


def process_split(split, start=0, end=None, render_images=True):
    """Process all prescriptions in a split."""
    label_dir = os.path.join(VAIPE_BASE, split, "prescription", "labels")
    
    # Get all label files sorted
    label_files = sorted(glob.glob(os.path.join(label_dir, "*.json")))
    if end is None:
        end = len(label_files)
    label_files = label_files[start:end]
    
    print(f"\n{'='*60}")
    print(f"Processing {split}: {len(label_files)} prescriptions [{start}:{end}]")
    print(f"{'='*60}")
    
    # Output dirs
    out_label_dir = os.path.join(OUTPUT_BASE, "pres", split)
    out_image_dir = os.path.join(OUTPUT_BASE, "pres_images", split)
    os.makedirs(out_label_dir, exist_ok=True)
    os.makedirs(out_image_dir, exist_ok=True)
    
    # Temp dir for DOCX rendering
    tmp_dir = os.path.join(OUTPUT_BASE, "tmp_docx")
    os.makedirs(tmp_dir, exist_ok=True)
    
    # Import prescription renderer
    sys.path.insert(0, os.path.join(ROOT, "createPrescription", "prescription_generator"))
    from generate_prescription import create_prescription_doc
    
    stats = {"total": 0, "success": 0, "failed": 0, "drugs_mapped": 0}
    
    for idx, label_path in enumerate(label_files):
        fname = os.path.basename(label_path)
        pres_name = fname.replace(".json", "")
        
        # 1. Extract drugs from VAIPE label
        vaipe_drugs = extract_drugs_from_vaipe(label_path)
        if not vaipe_drugs:
            print(f"  ⚠ {pres_name}: No drugs found, skipping")
            stats["failed"] += 1
            continue
        
        # 2. Create BVĐK prescription data
        pres_data = create_bvdk_prescription(idx + 1, vaipe_drugs)
        
        # 3. Create new label JSON (preserving mapping IDs)
        new_label = create_label_from_vaipe(label_path)
        
        # Save new label
        out_label_path = os.path.join(out_label_dir, fname)
        with open(out_label_path, "w", encoding="utf-8") as f:
            json.dump(new_label, f, ensure_ascii=False, indent=2)
        
        # 4. Render DOCX → PNG (if enabled)
        if render_images:
            docx_path = os.path.join(tmp_dir, f"{pres_name}.docx")
            png_path = os.path.join(out_image_dir, f"{pres_name}.png")
            
            try:
                create_prescription_doc([pres_data], docx_path)
                ok = render_docx_to_png(docx_path, png_path)
                if ok:
                    stats["success"] += 1
                    # Cleanup DOCX
                    if os.path.exists(docx_path):
                        os.remove(docx_path)
                else:
                    stats["failed"] += 1
                    print(f"  ✗ {pres_name}: PNG render failed")
            except Exception as e:
                stats["failed"] += 1
                print(f"  ✗ {pres_name}: {e}")
        else:
            stats["success"] += 1
        
        stats["total"] += 1
        stats["drugs_mapped"] += len(vaipe_drugs)
        
        if (idx + 1) % 50 == 0:
            print(f"  Progress: {idx+1}/{len(label_files)} "
                  f"(✓{stats['success']} ✗{stats['failed']})")
    
    # Cleanup tmp
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
    
    # Symlink pill images (reuse VAIPE pills directly)
    pill_src = os.path.join(VAIPE_BASE, split, "pill")
    pill_dst = os.path.join(OUTPUT_BASE, "pills", split)
    if not os.path.exists(pill_dst):
        os.makedirs(os.path.dirname(pill_dst), exist_ok=True)
        # Copy pill labels and create symlinks for images
        pill_label_src = os.path.join(pill_src, "labels")
        pill_label_dst = os.path.join(pill_dst, "labels")
        pill_img_src = os.path.join(pill_src, "images")
        pill_img_dst = os.path.join(pill_dst, "images")
        
        if os.path.exists(pill_label_src) and not os.path.exists(pill_label_dst):
            os.symlink(pill_label_src, pill_label_dst)
            print(f"  📎 Symlinked pill labels: {pill_label_dst}")
        if os.path.exists(pill_img_src) and not os.path.exists(pill_img_dst):
            os.symlink(pill_img_src, pill_img_dst)
            print(f"  📎 Symlinked pill images: {pill_img_dst}")
    
    print(f"\n{'='*60}")
    print(f"Results ({split}):")
    print(f"  Total processed: {stats['total']}")
    print(f"  Success: {stats['success']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Drugs mapped: {stats['drugs_mapped']}")
    print(f"  Output labels: {out_label_dir}")
    print(f"  Output images: {out_image_dir}")
    print(f"{'='*60}\n")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Convert VAIPE prescriptions to BVĐK format"
    )
    parser.add_argument("--split", default="train",
                       choices=["train", "val", "test"])
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--no-render", action="store_true",
                       help="Skip DOCX→PNG rendering (labels only)")
    args = parser.parse_args()
    
    stats = process_split(
        args.split,
        start=args.start,
        end=args.end,
        render_images=not args.no_render
    )
    
    print("\nNext steps:")
    print("  1. Upload data/synthetic_train/ to Colab")
    print("  2. Update train.py data path to synthetic_train/")
    print("  3. Load zero_pima_best.pth checkpoint")
    print("  4. Fine-tune with new format")


if __name__ == "__main__":
    main()
