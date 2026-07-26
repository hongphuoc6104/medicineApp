"""
scripts/tests/audit_datasets_summary.py

Fast evaluation of all datasets: data/newDATA, data/input, data/output/debug_scans
"""
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.pipeline import MedicinePipeline
from core.classify.ai_semantic_filter import AISemanticFilter


def audit_summary():
    pipe = MedicinePipeline()

    # 1. Audit newDATA PDFs
    new_data_dir = ROOT / "data" / "newDATA"
    pdfs = list(new_data_dir.glob("*.pdf"))

    print("=" * 80)
    print(f"📁 1. AUDITING data/newDATA ({len(pdfs)} PDF Files)")
    print("=" * 80)

    for pdf_path in pdfs:
        cmd = ["pdftotext", str(pdf_path), "-"]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        ocr_text = proc.stdout

        res = pipe.scan_prescription_app(ocr_text)
        meds = res.get("medications", [])

        print(f"\n[PDF: {pdf_path.name}] -> Extracted {len(meds)} Medications:", flush=True)
        for idx, m in enumerate(meds, 1):
            print(f"  {idx}. [{m.get('mapping_status')}] '{m.get('drug_name')}' (Matched: '{m.get('matched_drug_name')}', Score: {m.get('match_score')})", flush=True)

    # 2. Audit recent debug scans
    debug_files = sorted(glob.glob(str(ROOT / "data" / "output" / "debug_scans" / "scan_*_debug.json")))[-30:]
    print("\n" + "=" * 80, flush=True)
    print(f"📁 2. AUDITING data/output/debug_scans ({len(debug_files)} Recent JSON Debug Files)", flush=True)
    print("=" * 80, flush=True)

    NOISE_CHECK_RE = re.compile(
        r"("
        r"bệnh\s+viện|bvdk|bvđk|bv\b|sở\s+y\s+tế|phòng\s+khám|tnhh|cty|công\s+ty|medic|"
        r"họ\s+tên|bệnh\s+nhân|người\s+thân|bác\s+sĩ|bác\s+sỹ|người\s+giao|"
        r"cmnd|cccd|sđt|điện\s+thoại|tuổi|giới\s+tính|mã\s+bhyt|mã\s+bn|mã\s+bệnh|mã\s+đơn|số\s+toa|số\s+hồ\s+sơ|ms:|"
        r"địa\s+chỉ|đường|phường|quận|thành\s+phố|tpct|tp\.|khu\s+vực|lý\s+thái\s+tổ|vườn\s+lài|hùng\s+vương|cmt8|tháng\s+tám|"
        r"chẩn\s+đoán|chần\s+đoán|chần\s+đoản|chẩn\s+đoản|trào\s+ngược|dạ\s+dày|thực\s+quản|đau\s+bụng|rối\s+loạn|đái\s+tháo\s+đường|viêm\s+phế\s+quản|"
        r"lời\s+dặn|khám\s+lại|tái\s+khám|xin\s+mang\s+theo|cộng\s+khoản|ghi\s+chú|đánh\s+giá|kết\s+luận|chế\s+độ|đề\s+nghị|"
        r"mạch|nhiệt\s+độ|cân\s+nặng|chiều\s+cao|chíêu\s+cao|biểu\s+hiện|lâm\s+sàng|dị\s+ứng|bệnh\s+kèm|trung\s+bình|cc/t|cn/t|cn/cc|bmi|co\s+giật"
        r")",
        re.IGNORECASE,
    )

    valid_scans = 0
    total_meds = 0
    noise_leaks = []

    for idx_f, fpath in enumerate(debug_files, 1):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        ocr_text = data.get("ocr_text", "")
        if not ocr_text or len(ocr_text.strip()) < 10:
            continue

        valid_scans += 1
        res = pipe.scan_prescription_app(ocr_text)
        meds = res.get("medications", [])
        total_meds += len(meds)

        print(f"[{idx_f}/{len(debug_files)}] {Path(fpath).name} -> Extracted {len(meds)} meds", flush=True)

        for m in meds:
            drug_name = m.get("drug_name", "")
            raw_text = m.get("ocr_text", "")
            if NOISE_CHECK_RE.search(drug_name) and m.get("match_score", 0) < 0.70 and not AISemanticFilter.STRENGTH_RE.search(drug_name):
                noise_leaks.append((Path(fpath).name, drug_name, raw_text))

    print(f"\nDebug Scans Evaluated : {valid_scans}", flush=True)
    print(f"Total Medications Extracted : {total_meds} (avg {total_meds/max(1, valid_scans):.1f} / scan)", flush=True)
    print(f"Noise Leaks Count         : {len(noise_leaks)}", flush=True)

    if noise_leaks:
        print("\nNoise Leaks Details:", flush=True)
        for file_name, dname, raw in noise_leaks:
            print(f"  - [{file_name}] '{dname}' (raw: '{raw}')", flush=True)
    else:
        print("\n🎉 PERFECT RESULT: ZERO NOISE LEAKS IN ALL DEBUG SCANS!", flush=True)


if __name__ == "__main__":
    audit_summary()
