import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from core.phase_a.s3_ocr.ocr_engine import group_by_stt
from core.phase_a.s3_ocr.base import TextBlock


def main():
    json_path = ROOT / "data/output/phase_a/IMG_20260209_180505/step-3.2_ocr.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    blocks = [
        TextBlock(
            text=item["text"],
            confidence=item.get("confidence", 1.0),
            bbox=item["bbox"],
        )
        for item in data
    ]

    merged = group_by_stt(blocks)
    merged_texts = [block.text for block in merged]

    assert len(merged_texts) >= 8, merged_texts
    assert not any(
        "Mecobalamin (Methycobal 500mcg)" in text
        and "Loratadine (Clarityne 10mg) 10mg" in text
        for text in merged_texts
    ), merged_texts

    print("PASS: group_by_stt keeps missing-anchor medications separate")


if __name__ == "__main__":
    main()
