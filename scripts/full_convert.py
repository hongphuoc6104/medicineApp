#!/usr/bin/env python3
"""
Full pipeline: Convert ALL VAIPE prescriptions to BVĐK format.
Combines: DOCX generation + PDF→PNG conversion + v4 bbox extraction.

Usage:
    python scripts/full_convert.py --split train
    python scripts/full_convert.py --split train --start 0 --end 100
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
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "createPrescription", "prescription_generator"))
from data_generator import MedicalKnowledgeBase
from generate_prescription import create_prescription_doc

MED_KB = MedicalKnowledgeBase()
VAIPE_BASE = os.path.join(ROOT, "VAIPE_Full", "content", "dataset")
OUTPUT_BASE = os.path.join(ROOT, "data", "synthetic_train")
VAIPE_KB_PATH = os.path.join(ROOT, "data", "vaipe_drugs_kb.json")

with open(VAIPE_KB_PATH) as f:
    VAIPE_KB = json.load(f)

# ── Drug info mapping ────────────────────────────────────
def build_drug_info():
    result = {}
    for vid_str, vinfo in VAIPE_KB.items():
        vid = int(vid_str)
        name = vinfo["name"]
        for dk in MED_KB.drugs:
            dk_norm = dk.lower().replace("_", "")
            name_norm = name.lower().replace("-", "").replace("_", "")
            if dk_norm == name_norm or name_norm.startswith(dk_norm[:8]):
                info = MED_KB.drugs[dk][0]
                result[vid] = {
                    "generic_name": dk.replace("_", " "),
                    "brand_name": info["brand"],
                    "dosage": info["dosage"],
                    "unit": info["unit"],
                    "instructions": info["instr"],
                }
                break
        if vid not in result:
            result[vid] = {
                "generic_name": name.replace("-", " "),
                "brand_name": vinfo.get("brand", name),
                "dosage": vinfo.get("dosage", "Tab"),
                "unit": "Viên",
                "instructions": "Ngày uống 2 lần, mỗi lần 1 viên",
            }
    return result

DRUG_INFO = build_drug_info()

# ── Patient/Doctor generators ────────────────────────────
LAST_NAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh",
              "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ"]
MIDDLE_NAMES = ["Văn", "Thị", "Hữu", "Đức", "Minh", "Thu",
                "Ngọc", "Thanh", "Quang", "Mạnh", "Kim", "Xuân"]
FIRST_NAMES = ["An", "Bình", "Cường", "Dung", "Giang", "Hải",
               "Lan", "Mai", "Oanh", "Phúc", "Hùng", "Trang",
               "Linh", "Tuấn", "Hoa", "Đạt"]
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
    "146 Đường Trần Hưng Đạo, Hà Nội",
    "55 Nguyễn Trãi, Quận 5, TP.HCM",
]
DIAGNOSES = [
    "J00: Viêm mũi họng cấp", "J20.9: Viêm phế quản cấp",
    "I10: Tăng huyết áp vô căn", "E11: Đái tháo đường type 2",
    "K21.9: Trào ngược dạ dày", "M54.5: Đau thắt lưng",
    "G47.0: Rối loạn giấc ngủ", "K73.9: Viêm gan mạn tính",
    "M17: Thoái hóa khớp gối", "L20.9: Viêm da cơ địa",
    "E78.0: Tăng cholesterol máu thuần",
]

USAGE_KEYWORDS = [
    "ngày uống", "ngày dùng", "uống ", "hòa tan",
    "nhỏ mắt", "theo chỉ định", "lần, mỗi",
    "trước ăn", "sau ăn", "buổi sáng", "buổi tối",
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


def extract_vaipe_drugs(label_path):
    with open(label_path, encoding="utf-8") as f:
        entries = json.load(f)
    return [
        {"text": e["text"], "mapping": e["mapping"], "box": e["box"]}
        for e in entries
        if e.get("label") == "drugname" and "mapping" in e
    ]


def create_prescription(pres_id, vaipe_drugs):
    patient = generate_patient()
    doctor = random.choice(DOCTORS)
    meds = []
    for drug in vaipe_drugs:
        mid = drug["mapping"]
        if mid in DRUG_INFO:
            info = dict(DRUG_INFO[mid])
            meds.append({
                "generic_name": info["generic_name"],
                "brand_name": info["brand_name"],
                "dosage": info["dosage"],
                "unit": info["unit"],
                "quantity": random.choice([7, 10, 14, 20, 28, 30]),
                "instructions": info["instructions"],
            })
        else:
            meds.append({
                "generic_name": drug["text"],
                "brand_name": drug["text"],
                "dosage": "Tab",
                "unit": "Viên",
                "quantity": 14,
                "instructions": "Theo chỉ định bác sĩ",
            })
    start = datetime(2025, 12, 1)
    end = datetime(2026, 12, 31)
    today = start + timedelta(days=random.randint(0, (end - start).days))
    fd = random.choice([7, 14, 28])
    diag = "; ".join(random.sample(DIAGNOSES,
                                    min(random.choice([1, 2]), len(DIAGNOSES))))
    return {
        "id": pres_id,
        "patient": patient,
        "prescription_code": f"25{random.randint(100000, 999999)}",
        "diagnosis": diag,
        "doctor": doctor,
        "medications": meds,
        "follow_up_date": (today + timedelta(days=fd)).strftime("%d/%m/%Y"),
        "prescription_date": today.strftime("ngày %d tháng %m năm %Y"),
        "notes": "", "lab_tests": "",
        "barcode_bottom": f"0000{pres_id:08d}",
        "duration_days": fd,
    }


# ── PDF bbox extraction (v4 logic) ───────────────────────
def pdf_to_text_boxes(pdf_path):
    xml_path = pdf_path.replace(".pdf", ".xml")
    subprocess.run(["pdftohtml", "-xml", pdf_path],
                   capture_output=True, timeout=10)
    if not os.path.exists(xml_path):
        return [], (0, 0)
    tree = ET.parse(xml_path)
    page = tree.getroot().find(".//page")
    if page is None:
        return [], (0, 0)
    pw = int(page.get("width", 595))
    ph = int(page.get("height", 842))
    boxes = []
    for t in page.findall(".//text"):
        x, y = int(t.get("left", 0)), int(t.get("top", 0))
        w, h = int(t.get("width", 0)), int(t.get("height", 0))
        parts = []
        if t.text:
            parts.append(t.text)
        for c in t:
            if c.text:
                parts.append(c.text)
            if c.tail:
                parts.append(c.tail)
        text = "".join(parts).strip()
        if text:
            boxes.append({"text": text, "pdf_box": [x, y, x+w, y+h]})
    for ext in [".xml", "s.html", "_ind.html"]:
        p = pdf_path.replace(".pdf", ext)
        if os.path.exists(p):
            os.remove(p)
    return boxes, (pw, ph)


def build_label(boxes, pw, ph, iw, ih, vaipe_mappings):
    sx, sy = iw / pw, ih / ph

    # Find table boundaries
    tstart, tend = None, None
    for b in boxes:
        tl = b["text"].lower()
        y = b["pdf_box"][1]
        if "thuốc điều trị" in tl and tstart is None:
            tstart = y
        if ("khám lại" in tl or "lời dặn" in tl) and y > 400:
            if tend is None or y < tend:
                tend = y
    if tstart is None:
        tstart = 280
    if tend is None:
        tend = ph

    table_boxes = [b for b in boxes if tstart < b["pdf_box"][1] < tend]
    non_table = [b for b in boxes if b["pdf_box"][1] <= tstart or b["pdf_box"][1] >= tend]
    table_boxes.sort(key=lambda b: (b["pdf_box"][1], b["pdf_box"][0]))

    # Skip headers
    start_idx = 0
    header_kw = ["stt", "thuốc điều trị", "bs.", "ths.", "ts.",
                 "ckii", "cki", "phạm minh", "lê vũ", "trần thị",
                 "nguyễn văn", "hoàng thị", "lê thị"]
    for i, b in enumerate(table_boxes):
        tl = b["text"].lower().strip()
        x = b["pdf_box"][0]
        if any(kw in tl for kw in header_kw) and x < 300:
            start_idx = i + 1
        else:
            break

    # Group by drug blocks (usage lines as separators)
    drug_blocks = []
    cur = {"drug_texts": [], "usage_texts": [], "qty_texts": [], "unit_texts": []}
    footer_kw = ["khám lại", "lời dặn", "bác sĩ", "ký, ghi", "tháng", "năm 20"]

    for b in table_boxes[start_idx:]:
        x = b["pdf_box"][0]
        text = b["text"].strip()
        tl = text.lower()

        if x < 100 and text.isdigit() and len(text) <= 1:
            continue
        if x >= 520:
            cur["unit_texts"].append(b)
            continue
        if 450 <= x < 520 and text.isdigit():
            cur["qty_texts"].append(b)
            continue
        if 100 <= x < 450:
            if any(kw in tl for kw in footer_kw):
                break
            if any(kw in tl for kw in USAGE_KEYWORDS):
                cur["usage_texts"].append(b)
                drug_blocks.append(cur)
                cur = {"drug_texts": [], "usage_texts": [],
                       "qty_texts": [], "unit_texts": []}
            else:
                cur["drug_texts"].append(b)

    if cur["drug_texts"]:
        drug_blocks.append(cur)

    # Build entries
    entries = []
    eid = 1
    for i, block in enumerate(drug_blocks):
        if block["drug_texts"]:
            pbs = [b["pdf_box"] for b in block["drug_texts"]]
            merged = [min(b[0] for b in pbs), min(b[1] for b in pbs),
                      max(b[2] for b in pbs), max(b[3] for b in pbs)]
            mapping = vaipe_mappings[i] if i < len(vaipe_mappings) else -1
            entries.append({
                "id": eid,
                "text": " ".join(b["text"] for b in block["drug_texts"]),
                "label": "drugname",
                "box": [int(merged[0]*sx), int(merged[1]*sy),
                        int(merged[2]*sx), int(merged[3]*sy)],
                "mapping": mapping,
            })
            eid += 1
        for b in block["usage_texts"]:
            entries.append({
                "id": eid, "text": b["text"], "label": "usage",
                "box": [int(b["pdf_box"][0]*sx), int(b["pdf_box"][1]*sy),
                        int(b["pdf_box"][2]*sx), int(b["pdf_box"][3]*sy)],
            })
            eid += 1
        for b in block["qty_texts"]:
            entries.append({
                "id": eid, "text": b["text"], "label": "quantity",
                "box": [int(b["pdf_box"][0]*sx), int(b["pdf_box"][1]*sy),
                        int(b["pdf_box"][2]*sx), int(b["pdf_box"][3]*sy)],
            })
            eid += 1
        for b in block["unit_texts"]:
            entries.append({
                "id": eid, "text": b["text"], "label": "other",
                "box": [int(b["pdf_box"][0]*sx), int(b["pdf_box"][1]*sy),
                        int(b["pdf_box"][2]*sx), int(b["pdf_box"][3]*sy)],
            })
            eid += 1

    for b in non_table:
        tl = b["text"].lower()
        if "chẩn đoán" in tl or "chấn đoán" in tl:
            label = "diagnose"
        elif re.match(r'^[A-Z]\d{2}', b["text"]):
            label = "diagnose"
        elif "tháng" in tl and "năm" in tl:
            label = "date"
        else:
            label = "other"
        entries.append({
            "id": eid, "text": b["text"], "label": label,
            "box": [int(b["pdf_box"][0]*sx), int(b["pdf_box"][1]*sy),
                    int(b["pdf_box"][2]*sx), int(b["pdf_box"][3]*sy)],
        })
        eid += 1
    return entries


# ── Main pipeline ────────────────────────────────────────
def process_split(split, start=0, end=None, batch_size=20):
    label_dir = os.path.join(VAIPE_BASE, split, "prescription", "labels")
    label_files = sorted(glob.glob(os.path.join(label_dir, "*.json")))
    if end is None:
        end = len(label_files)
    label_files = label_files[start:end]

    out_label_dir = os.path.join(OUTPUT_BASE, "pres", split)
    out_image_dir = os.path.join(OUTPUT_BASE, "pres_images", split)
    tmp_docx_dir = os.path.join(OUTPUT_BASE, "tmp_docx")
    tmp_pdf_dir = "/tmp/pdf_conv"
    os.makedirs(out_label_dir, exist_ok=True)
    os.makedirs(out_image_dir, exist_ok=True)
    os.makedirs(tmp_docx_dir, exist_ok=True)
    os.makedirs(tmp_pdf_dir, exist_ok=True)

    # Clean old synth files
    for old in glob.glob(os.path.join(out_label_dir, "synth_*.json")):
        os.remove(old)

    print(f"\n{'='*60}")
    print(f"  VAIPE → BVĐK: {split} [{start}:{end}] ({len(label_files)} files)")
    print(f"{'='*60}\n")

    stats = {"total": 0, "ok": 0, "fail": 0, "drugs": 0}

    # Process in batches (for LibreOffice stability)
    for batch_start in range(0, len(label_files), batch_size):
        batch = label_files[batch_start:batch_start + batch_size]

        # Step 1: Generate DOCX files for this batch
        docx_paths = []
        pres_data_map = {}
        for idx, lf in enumerate(batch):
            fname = os.path.basename(lf).replace(".json", "")
            vaipe_drugs = extract_vaipe_drugs(lf)
            if not vaipe_drugs:
                stats["fail"] += 1
                continue
            pres = create_prescription(batch_start + idx + 1, vaipe_drugs)
            docx_path = os.path.join(tmp_docx_dir, f"{fname}.docx")
            try:
                create_prescription_doc([pres], docx_path)
                docx_paths.append((fname, docx_path, lf))
                pres_data_map[fname] = pres
                stats["drugs"] += len(vaipe_drugs)
            except Exception as e:
                print(f"  ✗ DOCX {fname}: {e}")
                stats["fail"] += 1

        # Step 2: Batch convert DOCX → PDF (one LibreOffice call)
        if docx_paths:
            docx_files = [dp[1] for dp in docx_paths]
            subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "pdf",
                 "--outdir", tmp_pdf_dir] + docx_files,
                capture_output=True, timeout=120
            )

        # Step 3: PDF → PNG + bbox for each
        for fname, docx_path, vaipe_label_path in docx_paths:
            pdf_path = os.path.join(tmp_pdf_dir, f"{fname}.pdf")
            png_path = os.path.join(out_image_dir, f"{fname}.png")

            if not os.path.exists(pdf_path):
                stats["fail"] += 1
                continue

            # PDF → PNG
            png_prefix = png_path.replace(".png", "")
            subprocess.run(
                ["pdftoppm", "-png", "-r", "200", "-singlefile",
                 pdf_path, png_prefix],
                capture_output=True, timeout=30
            )

            if not os.path.exists(png_path):
                stats["fail"] += 1
                continue

            # Extract bboxes from PDF
            boxes, (pw, ph) = pdf_to_text_boxes(pdf_path)
            if not boxes:
                stats["fail"] += 1
                continue

            img = Image.open(png_path)
            iw, ih = img.size
            img.close()

            # Get VAIPE mappings
            with open(vaipe_label_path) as f:
                vo = json.load(f)
            mappings = [e.get("mapping", -1) for e in vo
                        if e.get("label") == "drugname"]

            entries = build_label(boxes, pw, ph, iw, ih, mappings)

            # Save label
            out_label = os.path.join(out_label_dir, f"{fname}.json")
            with open(out_label, "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)

            stats["ok"] += 1
            stats["total"] += 1

            # Cleanup
            os.remove(pdf_path)
            os.remove(docx_path)

        # Progress
        done = batch_start + len(batch)
        print(f"  [{done:4d}/{len(label_files)}] "
              f"✓ {stats['ok']} ✗ {stats['fail']} "
              f"({stats['drugs']} drugs mapped)")

    # Symlink pill images
    pill_src = os.path.join(VAIPE_BASE, split, "pill")
    pill_dst = os.path.join(OUTPUT_BASE, "pills", split)
    if not os.path.exists(pill_dst):
        os.makedirs(os.path.dirname(pill_dst), exist_ok=True)
        for sub in ["labels", "images"]:
            src = os.path.join(pill_src, sub)
            dst = os.path.join(pill_dst, sub)
            if os.path.exists(src) and not os.path.exists(dst):
                os.symlink(src, dst)
                print(f"  📎 Symlinked: {dst}")

    # Cleanup
    if os.path.exists(tmp_docx_dir):
        shutil.rmtree(tmp_docx_dir, ignore_errors=True)

    print(f"\n{'='*60}")
    print(f"  DONE: {stats['ok']}/{stats['total']+stats['fail']} "
          f"({stats['drugs']} drugs)")
    print(f"  Labels: {out_label_dir}")
    print(f"  Images: {out_image_dir}")
    print(f"{'='*60}\n")
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="train")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()
    process_split(args.split, args.start, args.end, args.batch_size)


if __name__ == "__main__":
    main()
