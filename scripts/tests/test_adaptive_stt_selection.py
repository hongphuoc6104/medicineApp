import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from core.pipeline import MedicinePipeline


def main():
    pipeline = MedicinePipeline()

    collapse_case = ROOT / "data" / "input" / "prescription_1" / "IMG_20260209_180410.jpg"
    noise_case = ROOT / "data" / "input" / "prescription_4" / "IMG_20260209_180744.jpg"

    collapse_result = pipeline.scan_prescription_app(str(collapse_case))
    collapse_stats = collapse_result.get("stats", {})
    assert collapse_stats.get("selection_strategy") == "raw_blocks", collapse_stats

    noise_result = pipeline.scan_prescription_app(str(noise_case))
    noise_stats = noise_result.get("stats", {})
    assert noise_stats.get("selection_strategy") == "stt_grouped", noise_stats

    print("PASS: adaptive STT selection preserves coverage and suppresses raw noise")


if __name__ == "__main__":
    main()
