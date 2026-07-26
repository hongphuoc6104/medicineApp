"""
scripts/tests/deep_debug_audit.py

Audit all recent debug scan outputs in detail to spot missing drugs or excess noise.
"""
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
scan_files = sorted(glob.glob(str(ROOT / "data" / "output" / "debug_scans" / "scan_*_debug.json")))[-15:]

print(f"=== DEEP AUDIT OF LAST {len(scan_files)} DEBUG SCANS ===\n")

for fpath in scan_files:
    fname = Path(fpath).name
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    ocr_text = data.get("ocr_text", "")
    meds = data.get("medications", [])
    cands = data.get("candidates", [])
    ocr_blocks = data.get("ocr_blocks", [])
    stats = data.get("stats", {})

    print("=" * 80)
    print(f"FILE: {fname}")
    print(f"Strategy: {stats.get('selection_strategy')} | Reason: {stats.get('selection_reason')}")
    print(f"Extracted Medications Count: {len(meds)}")
    for i, m in enumerate(meds, 1):
        print(f"  [MED #{i}] status={m.get('mapping_status')}, name='{m.get('drug_name')}', raw='{m.get('ocr_text')}', matched='{m.get('matched_drug_name')}', score={m.get('match_score')}")

    print(f"\nAll Candidate Blocks ({len(cands)} total):")
    for i, c in enumerate(cands, 1):
        print(f"  [CAND #{i}] status={c.get('mapping_status')}, raw='{c.get('ocr_text')}', score={c.get('match_score')}, conf={c.get('confidence')}")

    print("\n--- RAW OCR TEXT (full) ---")
    print(ocr_text.strip())
    print("=" * 80 + "\n")
