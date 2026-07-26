"""
scripts/tests/audit_all_dropped_blocks.py

Audit every debug scan file to find any block tagged as 'drugname' by PhoBERT NER
that was dropped/rejected by AISemanticFilter or MedicinePipeline.
"""
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
scan_files = sorted(glob.glob(str(ROOT / "data" / "output" / "debug_scans" / "scan_*_debug.json")))

print(f"=== AUDITING DROPPED DRUG BLOCKS IN {len(scan_files)} DEBUG SCANS ===\n")

total_dropped_drugs = 0

for fpath in scan_files:
    fname = Path(fpath).name
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    meds = data.get("medications", [])
    ocr_blocks = data.get("ocr_blocks", [])

    extracted_raws = {m.get("ocr_text", "").strip().lower() for m in meds}
    extracted_names = {m.get("drug_name", "").strip().lower() for m in meds}

    for b in ocr_blocks:
        if b.get("label") == "drugname":
            txt = b.get("text", "").strip()
            orig = b.get("original_text", "").strip()
            conf = b.get("confidence", 0)

            # Check if this drugname block was included in medications
            in_meds = any(
                txt.lower() in raw or raw in txt.lower() or txt.lower() in name or name in txt.lower()
                for raw in extracted_raws
                for name in extracted_names
            )

            if not in_meds:
                total_dropped_drugs += 1
                print(f"[{fname}] DROPPED DRUGNAME BLOCK:")
                print(f"  - text: '{txt}' (original: '{orig}', conf: {conf})")

print(f"\nTotal dropped drugname blocks across all debug files: {total_dropped_drugs}")
