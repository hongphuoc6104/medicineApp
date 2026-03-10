#!/usr/bin/env python3
"""
Benchmark script: Chạy pipeline Phase A trên toàn bộ ảnh test
và ghi kết quả ra JSON để so sánh trước/sau bug fix.

Usage:
    python scripts/benchmark_pipeline.py          # Chạy tất cả
    python scripts/benchmark_pipeline.py --sample 3  # 3 ảnh mẫu
    python scripts/benchmark_pipeline.py --dir data/input/prescription_1
"""
import argparse
import json
import time
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def run_benchmark(image_paths: list[Path], output_json: Path):
    """Chạy pipeline trên danh sách ảnh, ghi kết quả."""
    print(f"\n{'='*60}")
    print(f"BENCHMARK: {len(image_paths)} ảnh")
    print(f"{'='*60}")

    # Load pipeline
    print("Loading pipeline...")
    t0 = time.time()
    from core.pipeline import MedicinePipeline
    pipe = MedicinePipeline()
    load_time = time.time() - t0
    print(f"Pipeline loaded in {load_time:.1f}s\n")

    results = []
    total_drugs = 0
    errors = []
    zero_drug_images = []

    for i, img_path in enumerate(image_paths, 1):
        print(f"[{i:02d}/{len(image_paths)}] {img_path.name}", end=" ... ")
        t_start = time.time()

        try:
            result = pipe.scan_prescription(str(img_path))
            elapsed = time.time() - t_start

            if "error" in result:
                print(f"ERROR: {result['error']}")
                errors.append({"image": img_path.name, "error": result["error"]})
                results.append({
                    "image": img_path.name,
                    "path": str(img_path),
                    "error": result["error"],
                    "elapsed_s": round(elapsed, 2),
                    "drugs": [],
                    "drug_count": 0,
                })
            else:
                meds = result.get("medications", [])
                n_drugs = len(meds)
                total_drugs += n_drugs

                if n_drugs == 0:
                    zero_drug_images.append(img_path.name)
                    print(f"⚠️  0 drugs  ({elapsed:.1f}s)")
                else:
                    drug_names = [m["drug_name"] for m in meds]
                    print(f"✅ {n_drugs} drugs: {drug_names[:3]} ({elapsed:.1f}s)")

                results.append({
                    "image": img_path.name,
                    "path": str(img_path),
                    "drug_count": n_drugs,
                    "elapsed_s": round(elapsed, 2),
                    "medications": meds,
                    "stats": result.get("stats", {}),
                    "ocr_block_count": len(result.get("ocr_blocks", [])),
                })

        except Exception as e:
            elapsed = time.time() - t_start
            print(f"EXCEPTION: {e}")
            errors.append({"image": img_path.name, "exception": str(e)})
            results.append({
                "image": img_path.name,
                "path": str(img_path),
                "exception": str(e),
                "elapsed_s": round(elapsed, 2),
                "drug_count": 0,
                "drugs": [],
            })

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total images  : {len(image_paths)}")
    print(f"Total drugs   : {total_drugs}")
    print(f"Avg drugs/img : {total_drugs/len(image_paths):.1f}")
    print(f"Errors        : {len(errors)}")
    print(f"Zero-drug imgs: {len(zero_drug_images)}")
    if zero_drug_images:
        print(f"  → {zero_drug_images}")

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_images": len(image_paths),
        "total_drugs": total_drugs,
        "avg_drugs_per_image": round(total_drugs/len(image_paths), 2),
        "error_count": len(errors),
        "zero_drug_count": len(zero_drug_images),
        "zero_drug_images": zero_drug_images,
        "results": results,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved → {output_json}")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", help="Specific folder to scan")
    parser.add_argument("--sample", type=int, help="Limit to N images")
    parser.add_argument("--out", default="data/output/benchmark_after_fix.json")
    args = parser.parse_args()

    input_dir = ROOT / "data" / "input"

    if args.dir:
        d = Path(args.dir)
        image_paths = sorted(
            list(d.glob("*.jpg")) + list(d.glob("*.jpeg")) + list(d.glob("*.png"))
        )
    else:
        image_paths = sorted(
            list(input_dir.rglob("*.jpg")) +
            list(input_dir.rglob("*.jpeg")) +
            list(input_dir.rglob("*.png"))
        )

    if args.sample:
        image_paths = image_paths[:args.sample]

    if not image_paths:
        print("No images found!")
        return

    output_json = ROOT / args.out
    run_benchmark(image_paths, output_json)


if __name__ == "__main__":
    main()
