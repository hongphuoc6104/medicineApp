import os
import glob
from pathlib import Path

# Thêm đường dẫn thư mục gốc vào path để import
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.phase_a.s3_ocr.ocr_engine import HybridOcrModule
from core.phase_a.s1_detect.detector import PrescriptionDetector
from scripts.run_pipeline import run_phase_a

print("Loading models (Pre-load for batch run)...")
shared_models = {
    "yolo": PrescriptionDetector(),
}
# PaddleOCR loads sluggishly, so initialize it as well
from core.phase_a.s3_ocr.ocr_engine import HybridOcrModule
import torch
_ocr_device = "gpu" if torch.cuda.is_available() else "cpu"
shared_models["ocr"] = HybridOcrModule(device=_ocr_device)

print("Models loaded successfully!")

data_sources = [
    {
        "name": "REAL DATASET",
        "patterns": [os.path.join(ROOT, "data", "input", "**", "*.jpg"), os.path.join(ROOT, "data", "input", "**", "*.jpeg")]
    },
    {
        "name": "SYNTHETIC DATASET",
        "patterns": [os.path.join(ROOT, "data", "synthetic_train", "pres_images", "train", "*.jpg")]
    }
]

out_dir = os.path.join(ROOT, "data", "output", "phase_a")

total_count = 0
for source in data_sources:
    print(f"\n{'='*80}")
    print(f"BẮT ĐẦU CHẠY: {source['name']}")
    print(f"{'='*80}")
    
    files = []
    for pattern in source["patterns"]:
        files.extend(glob.glob(pattern, recursive=True))
    
    # Xóa giới hạn 50 ảnh, chạy TOÀN BỘ theo yêu cầu người dùng
    if not files:
        print(f"No files found for {source['name']}")
        
    for i, img_path in enumerate(files):
        img_name = os.path.basename(img_path)
        img_stem = os.path.splitext(img_name)[0]
        tgt_dir = os.path.join(out_dir, img_stem)
        
        print(f"[{i+1}/{len(files)}] Khởi chạy: {img_stem}")
        
        # Stop after OCR process to test "Group by STT"
        try:
            run_phase_a(img_path, tgt_dir, shared=shared_models, stop_after_ocr=True)
            total_count += 1
        except Exception as e:
            print(f"LỖI (Skip): {img_stem} - {str(e)}")

print(f"\n{'='*80}\n✅ Đã hoàn thành quá trình trích xuất OCR - Đã xử lý tổng cộng {total_count} ảnh.")
print(f"Vui lòng xem các file step-3_ocr.json tại: {out_dir}")
