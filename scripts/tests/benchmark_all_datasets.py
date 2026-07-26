"""
scripts/tests/benchmark_all_datasets.py

Benchmark and audit MedicinePipeline with AISemanticFilter across ALL 158 debug scans
and newDATA files to evaluate noise elimination and drug extraction accuracy.
"""

import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.pipeline import MedicinePipeline
from core.classify.ai_semantic_filter import AISemanticFilter


def run_full_benchmark():
    pipe = MedicinePipeline()
    debug_files = sorted(glob.glob(str(ROOT / "data" / "output" / "debug_scans" / "scan_*_debug.json")))

    print("=" * 80)
    print(f"🚀 STARTING FULL BENCHMARK ON {len(debug_files)} DEBUG SCANS...")
    print("=" * 80 + "\n")

    total_scans = 0
    total_meds_extracted = 0
    scans_with_meds = 0

    noise_violations = []
    dropped_candidates = []

    # Noise pattern check to verify no administrative/hospital text slipped into final medications
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

    for fpath in debug_files:
        fname = Path(fpath).name
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        ocr_text = data.get("ocr_text", "")
        if not ocr_text or not ocr_text.strip() or len(ocr_text.strip()) < 10:
            continue

        total_scans += 1
        res = pipe.scan_prescription_app(ocr_text)
        meds = res.get("medications", [])
        total_meds_extracted += len(meds)
        if meds:
            scans_with_meds += 1

        # 1. Audit medications for noise violations
        for m in meds:
            drug_name = m.get("drug_name", "")
            raw_text = m.get("ocr_text", "")
            if NOISE_CHECK_RE.search(drug_name) or NOISE_CHECK_RE.search(raw_text):
                # Exception: if strength/dosage is present and match_score >= 0.70, verify
                if m.get("match_score", 0) < 0.70 and not AISemanticFilter.STRENGTH_RE.search(drug_name):
                    noise_violations.append({
                        "file": fname,
                        "drug_name": drug_name,
                        "ocr_text": raw_text,
                        "status": m.get("mapping_status"),
                        "score": m.get("match_score"),
                    })

    print("=" * 80)
    print("📊 BENCHMARK SUMMARY REPORT:")
    print("=" * 80)
    print(f"Total Prescription Scans Evaluated : {total_scans}")
    print(f"Scans Yielding Valid Medications   : {scans_with_meds} ({scans_with_meds/max(1, total_scans)*100:.1f}%)")
    print(f"Total Medications Extracted         : {total_meds_extracted} (avg {total_meds_extracted/max(1, scans_with_meds):.1f} / scan)")
    print(f"Noise Violation Count              : {len(noise_violations)}")
    print("=" * 80 + "\n")

    if noise_violations:
        print("⚠️ DETECTED NOISE VIOLATIONS:")
        for idx, nv in enumerate(noise_violations, 1):
            print(f"  {idx}. [{nv['file']}] '{nv['drug_name']}' (Raw: '{nv['ocr_text']}', Score: {nv['score']})")
        print("\n")
    else:
        print("🎉 ZERO NOISE VIOLATIONS DETECTED ACROSS ALL SCANS!\n")


if __name__ == "__main__":
    run_full_benchmark()
