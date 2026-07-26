"""
Evaluate latest debug scan JSON files using the trained MedicinePipeline AI.
Extracts OCR text from data/output/debug_scans/ and re-runs end-to-end evaluation.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
from core.pipeline import MedicinePipeline
DEBUG_DIR = ROOT / "data" / "output" / "debug_scans"

def main():
    pipeline = MedicinePipeline(device="cpu")
    
    debug_files = sorted(list(DEBUG_DIR.glob("scan_*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
    # Take the 5 most recent real debug scans
    target_files = debug_files[:5]
    
    print(f"==================================================")
    print(f" 🧪 Re-running AI Evaluation on {len(target_files)} Latest Debug Scans")
    print(f"==================================================\n")
    
    total_drugs_found = 0
    total_confirmed = 0
    total_time = 0.0
    
    for i, file_path in enumerate(target_files, 1):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        ocr_text = data.get("ocr_text", "")
        if not ocr_text or len(ocr_text.strip()) < 10:
            continue
            
        print(f"--- [File {i}: {file_path.name}] ---")
        start_t = time.time()
        result = pipeline.scan_prescription_app(ocr_text=ocr_text)
        elapsed = time.time() - start_t
        total_time += elapsed
        
        meds = result.get("medications", [])
        confirmed_in_scan = 0
        
        print(f"⏱️  Thời gian xử lý: {elapsed:.2f}s | Tìm thấy {len(meds)} kết quả:")
        for idx, med in enumerate(meds, 1):
            status = med.get("mapping_status", "unknown")
            drug_name = med.get("drug_name") or med.get("ocr_text")
            matched = med.get("matched_drug_name") or med.get("mapped_drug_name") or "Chưa đối chiếu"
            reg_num = med.get("registration_number") or "N/A"
            score = med.get("match_score", 0.0) * 100
            
            if status == "confirmed" or score >= 70:
                confirmed_in_scan += 1
                
            print(f"   {idx}. Gốc: '{drug_name}' ➔ Match: '{matched}' | SĐK: {reg_num} | Status: {status} ({score:.0f}%)")
            
        total_drugs_found += len(meds)
        total_confirmed += confirmed_in_scan
        print()
        
    print(f"==================================================")
    print(f" 📊 TỔNG KẾT NĂNG LỰC NHẬN DIỆN AI:")
    print(f" - Tổng số file debug quét: {len(target_files)}")
    print(f" - Tổng số kết quả phát hiện: {total_drugs_found}")
    print(f" - Số thuốc đối chiếu thành công (Confirmed): {total_confirmed}")
    print(f" - Thời gian xử lý trung bình: {total_time / max(len(target_files), 1):.2f}s / đơn")
    print(f"==================================================")

if __name__ == "__main__":
    main()
