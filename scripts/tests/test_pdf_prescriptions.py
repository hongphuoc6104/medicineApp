"""
scripts/tests/test_pdf_prescriptions.py

Evaluate MedicinePipeline with AISemanticFilter on PDF prescriptions in data/newDATA.
"""

import subprocess
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.pipeline import MedicinePipeline


def test_pdf_prescriptions():
    pipe = MedicinePipeline()
    new_data_dir = ROOT / "data" / "newDATA"
    pdf_files = list(new_data_dir.glob("*.pdf"))

    print(f"=== TESTING {len(pdf_files)} PDF PRESCRIPTIONS IN data/newDATA ===\n")

    for pdf_path in pdf_files:
        print("=" * 70)
        print(f"FILE: {pdf_path.name}")
        cmd = ["pdftotext", str(pdf_path), "-"]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        ocr_text = proc.stdout

        res = pipe.scan_prescription_app(ocr_text)
        meds = res.get("medications", [])

        print(f"Extracted {len(meds)} Medications:")
        for idx, m in enumerate(meds, 1):
            status = m.get("mapping_status")
            name = m.get("drug_name")
            matched = m.get("matched_drug_name")
            score = m.get("match_score")
            raw = m.get("ocr_text")
            print(f"  {idx}. [{status}] '{name}' (Matched: '{matched}', Score: {score}) | Raw: '{raw}'")
        print("\n")


if __name__ == "__main__":
    test_pdf_prescriptions()
