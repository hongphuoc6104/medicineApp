"""
scripts/tests/test_noise_filter_and_schedule.py

Test noise filtering on debug scan OCR texts and verify drug extraction accuracy.
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.classify.post_filter import NerPostFilter
from core.pipeline import MedicinePipeline


def test_noise_filter_on_debug_scans():
    debug_dir = ROOT / "data" / "output" / "debug_scans"
    scan_files = [
        debug_dir / "scan_20260722_000027_065865_debug.json",
        debug_dir / "scan_20260722_000124_290677_debug.json",
    ]

    pipe = MedicinePipeline()

    for sf in scan_files:
        if not sf.exists():
            print(f"Skipping {sf.name} (not found)")
            continue

        print(f"\n--- Testing {sf.name} ---")
        with open(sf, "r", encoding="utf-8") as f:
            data = json.load(f)

        ocr_text = data.get("ocr_text", "")
        res = pipe.scan_prescription_app(ocr_text)

        meds = res.get("medications", [])
        print(f"Extracted {len(meds)} medications:")
        for m in meds:
            print(f"  - [{m.get('mapping_status')}] {m.get('drug_name')} (Raw: {m.get('ocr_text')})")

        med_names = [m.get("drug_name") for m in meds]

        # Verify no false positives (hospital names, patient names, addresses)
        assert not any("TRÂN LÊ" in name or "TRAN LÊ" in name for name in med_names), "Failed: Patient name extracted as drug"
        assert not any("MEDIC" in name or "BVDK" in name or "BVÐK" in name or "TNHH" in name for name in med_names), "Failed: Hospital/Company name extracted as drug"
        assert not any("Tháng Tám" in name or "Thâng Tám" in name for name in med_names), "Failed: Address extracted as drug"

        # Verify real drugs are present
        assert any("Lansoprazol" in name for name in med_names), "Failed: Lansoprazol missing"
        assert any("Magnesi" in name for name in med_names), "Failed: Magnesi trisilicat missing"

        print("-> PASS for", sf.name)

if __name__ == "__main__":
    test_noise_filter_on_debug_scans()
