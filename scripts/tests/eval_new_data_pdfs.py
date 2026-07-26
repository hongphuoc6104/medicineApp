"""
Evaluate new PDF prescription data (data/newDATA/) using MedicinePipeline.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.pipeline import MedicinePipeline

def extract_pdf_text(pdf_path):
    result = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True)
    return result.stdout

def main():
    pipeline = MedicinePipeline(device="cpu")
    pdf_dir = ROOT / "data" / "newDATA"
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    print("==================================================")
    print(f" 🧪 Evaluating New PDF Prescriptions ({len(pdf_files)} files in data/newDATA/)")
    print("==================================================\n")
    
    for pdf in pdf_files:
        text = extract_pdf_text(pdf)
        print(f"--- [Testing PDF File: {pdf.name}] ---")
        result = pipeline.scan_prescription_app(ocr_text=text)
        meds = result.get("medications", [])
        
        print(f"📋 Bóc tách được {len(meds)} kết quả:")
        for idx, m in enumerate(meds, 1):
            raw = m.get("drug_name_raw") or m.get("ocr_text")
            matched = m.get("matched_drug_name") or m.get("mapped_drug_name") or "Chưa đối chiếu"
            score = m.get("match_score", 0.0) * 100
            status = m.get("mapping_status", "unknown")
            reg = m.get("registration_number") or "N/A"
            print(f"  {idx}. Gốc: '{raw}' ➔ Match: '{matched}' | SĐK: {reg} | Score: {score:.0f}% ({status})")
        print()

if __name__ == "__main__":
    main()
