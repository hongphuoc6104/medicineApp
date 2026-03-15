"""
scripts/tests/test_new_features.py — Test file độc lập cho các tính năng mới

QUY TẮC VÀNG:
- File này chỉ TEST, không được import hoặc thay đổi logic của run_pipeline.py
- Nếu file này lỗi → pipeline chính vẫn hoạt động bình thường
- Chạy: venv/bin/python scripts/tests/test_new_features.py

Tính năng được test:
  [1] group_by_stt  — Gom nhóm OCR blocks theo số thứ tự (Bước 3.5)
  [2] DrugLookup   — Tra cứu thuốc fuzzy trong DB 9,284 thuốc (Bước 5)
  [3] Full Pipeline (1 ảnh) với --no-drug-lookup để so sánh
"""

import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

PASS = "✅"
FAIL = "❌"
SKIP = "⏭"

results = []

# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: group_by_stt
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TEST 1: group_by_stt")
print("="*70)

try:
    from core.phase_a.s3_ocr.ocr_engine import group_by_stt
    from core.phase_a.s3_ocr.base import TextBlock

    # Tạo mock blocks giả lập đơn thuốc 2 dòng
    mock_blocks = [
        TextBlock(text="1", confidence=0.99, bbox=[[10,50],[30,50],[30,70],[10,70]]),
        TextBlock(text="Amoxicillin 500mg", confidence=0.95, bbox=[[100,50],[300,50],[300,70],[100,70]]),
        TextBlock(text="28 Viên", confidence=0.90, bbox=[[310,55],[400,55],[400,75],[310,75]]),
        TextBlock(text="Ngày uống 2 lần", confidence=0.88, bbox=[[100,80],[300,80],[300,100],[100,100]]),
        TextBlock(text="2", confidence=0.99, bbox=[[10,130],[30,130],[30,150],[10,150]]),
        TextBlock(text="Paracetamol 500mg", confidence=0.95, bbox=[[100,130],[300,130],[300,150],[100,150]]),
        TextBlock(text="14 Viên", confidence=0.90, bbox=[[310,135],[400,135],[400,155],[310,155]]),
    ]
    merged = group_by_stt(mock_blocks)
    assert len(merged) >= 2, f"Expected >= 2 groups but got {len(merged)}"
    # Kiểm tra dòng đầu chứa Amoxicillin
    first_drug_line = [m for m in merged if "Amoxicillin" in m.text]
    assert len(first_drug_line) > 0, "Amoxicillin should be in first group"
    print(f"  {PASS} group_by_stt hoạt động: {len(mock_blocks)} blocks → {len(merged)} groups")
    for m in merged:
        print(f"       → {m.text[:70]}")
    results.append(("group_by_stt", True))
except Exception as e:
    print(f"  {FAIL} group_by_stt FAILED: {e}")
    import traceback; traceback.print_exc()
    results.append(("group_by_stt", False))


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: DrugLookup
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TEST 2: DrugLookup — Tra cứu tên thuốc")
print("="*70)

try:
    from core.phase_a.s6_drug_search.drug_lookup import DrugLookup
    lu = DrugLookup()
    print(f"  Loaded {lu.db_size:,} thuốc")

    test_cases = [
        ("Amoxicillin 500mg", True),   # Phải tìm thấy
        ("Paracetamol 500mg", True),   # Phải tìm thấy
        ("xyz_không_tồn_tại_abc", False),  # Không tìm thấy
    ]
    for text, expect_found in test_cases:
        result = lu.lookup(text)
        found = result.get("name") is not None
        ok = found == expect_found
        icon = PASS if ok else FAIL
        match_info = f"→ {result['name']} [{result['score']:.0%}]" if found else "→ không tìm thấy"
        print(f"  {icon} '{text[:40]}' {match_info}")
        results.append((f"DrugLookup-{text[:20]}", ok))
except Exception as e:
    print(f"  {FAIL} DrugLookup FAILED: {e}")
    import traceback; traceback.print_exc()
    results.append(("DrugLookup", False))


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: Pipeline đầy đủ trên 1 ảnh (chỉ OCR + NER, không DrugLookup)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TEST 3: Pipeline 1 ảnh (dừng sau NER, bỏ qua DrugLookup)")
print("="*70)

import subprocess
test_img = os.path.join(ROOT, "data", "createPrescription", "Pasted image.png")
if not os.path.exists(test_img):
    # Thử ảnh khác
    import glob
    imgs = glob.glob(os.path.join(ROOT, "data", "input", "**", "*.jpg"), recursive=True)
    test_img = imgs[0] if imgs else None

if test_img:
    try:
        proc = subprocess.run(
            ["venv/bin/python", "scripts/run_pipeline.py",
             "--image", test_img,
             "--no-drug-lookup"],
            capture_output=True, text=True, cwd=ROOT, timeout=120
        )
        if proc.returncode == 0:
            print(f"  {PASS} Pipeline chạy thành công (exit 0)")
            # Kiểm tra có file output không
            stem = os.path.splitext(os.path.basename(test_img))[0]
            out_dir = os.path.join(ROOT, "data", "output", "phase_a", stem)
            files = os.listdir(out_dir) if os.path.exists(out_dir) else []
            for f in ["step-0_raw.jpg", "step-1_cropped.jpg", "step-3.json", "step-4_ner_classify.json"]:
                exists = f in files
                print(f"  {'  '+PASS if exists else '  '+FAIL} {f}")
            results.append(("Pipeline-no-drug-lookup", True))
        else:
            print(f"  {FAIL} Pipeline lỗi (exit {proc.returncode})")
            print(proc.stderr[-500:])
            results.append(("Pipeline-no-drug-lookup", False))
    except Exception as e:
        print(f"  {FAIL} Exception: {e}")
        results.append(("Pipeline-no-drug-lookup", False))
else:
    print(f"  {SKIP} Không tìm thấy ảnh test, bỏ qua")
    results.append(("Pipeline-no-drug-lookup", None))


# ─────────────────────────────────────────────────────────────────────────────
# TÓM TẮT
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("KẾT QUẢ TEST")
print("="*70)
passed = sum(1 for _, ok in results if ok is True)
failed = sum(1 for _, ok in results if ok is False)
skipped = sum(1 for _, ok in results if ok is None)
for name, ok in results:
    icon = PASS if ok is True else (SKIP if ok is None else FAIL)
    print(f"  {icon} {name}")
print(f"\n  Tổng: {passed} pass / {failed} fail / {skipped} skip")
if failed > 0:
    print(f"\n  ⚠️  Có lỗi — nhưng pipeline chính (run_pipeline.py) KHÔNG bị ảnh hưởng.")
    sys.exit(1)
else:
    print(f"\n  🎉 Tất cả test pass!")
