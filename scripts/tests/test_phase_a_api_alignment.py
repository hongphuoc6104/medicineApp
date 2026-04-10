import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

def test_api_alignment():
    from core.pipeline import MedicinePipeline
    pipeline = MedicinePipeline()
    
    img_path = str(ROOT / "data" / "input" / "prescription_3" / "IMG_20260209_180505.jpg")
    if not os.path.exists(img_path):
        print(f"Test image not found at {img_path}")
        return
        
    result = pipeline.scan_prescription_app(img_path)
    
    drugs = result.get("medications", [])
    print(f"Found {len(drugs)} drugs via new API path.")
    for d in drugs:
        print(f"  - {d.get('drug_name')} (score: {d.get('match_score')}) [bbox: {d.get('bbox')}] [ocr: {d.get('ocr_text')}]")

if __name__ == "__main__":
    test_api_alignment()
