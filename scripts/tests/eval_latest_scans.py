"""
scripts/tests/eval_latest_scans.py

Run current MedicinePipeline on recent debug scan OCR texts and print detailed evaluation.
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.pipeline import MedicinePipeline


def test_live_evaluation_on_debug_scans():
    pipe = MedicinePipeline()
    files = sorted(glob.glob(str(ROOT / "data" / "output" / "debug_scans" / "scan_*_debug.json")))[-10:]

    print(f"--- Evaluating {len(files)} Recent Debug Scans with AI Semantic Filter ---\n")

    for fpath in files:
        fname = Path(fpath).name
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        ocr_text = data.get("ocr_text", "")
        if not ocr_text.strip():
            continue

        result = pipe.scan_prescription_app(ocr_text)
        meds = result.get("medications", [])

        print("=" * 70)
        print("FILE:", fname)
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
    test_live_evaluation_on_debug_scans()
