"""
Prepare evaluation-v2 assets for thesis reporting.

This script extends the existing labeled benchmark assets with a deterministic
unlabeled stress-test sample from the newly imported dataset.

Outputs:
  - data/eval_v2/phase_a_manifest_v2.csv
  - data/eval_v2/annotation_protocol_v2.md
  - data/eval_v2/sampling_log.json
  - data/eval_v2/exclusion_log_v2.md

Usage:
  venv/bin/python scripts/tests/test_phase_a_prepare_eval_v2_assets.py
  venv/bin/python scripts/tests/test_phase_a_prepare_eval_v2_assets.py --extended-sample 120
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[2]
EVAL_V1_DIR = ROOT / "data" / "eval"
EVAL_V2_DIR = ROOT / "data" / "eval_v2"
EXTENDED_ROOT = ROOT / "data" / "input" / "Data-20260420T154328Z-3-001" / "Data"


@dataclass(frozen=True)
class ManifestRow:
    image_id: str
    split: str
    subset: str
    group_id: str
    relative_path: str
    filename: str
    width: int
    height: int
    sha256: str
    include_eval: str
    label_status: str
    notes: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_shape(path: Path) -> tuple[int, int]:
    img = cv2.imread(str(path))
    if img is None:
        return 0, 0
    h, w = img.shape[:2]
    return int(w), int(h)


def load_core_rows() -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    with (EVAL_V1_DIR / "phase_a_manifest.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("include_eval", "").strip().lower() != "yes":
                continue
            rows.append(
                ManifestRow(
                    image_id=row["image_id"],
                    split="core_labeled",
                    subset="prescription_1_to_7",
                    group_id=row["group_id"],
                    relative_path=row["relative_path"],
                    filename=row["filename"],
                    width=int(row["width"]),
                    height=int(row["height"]),
                    sha256=row["sha256"],
                    include_eval="yes",
                    label_status="labeled_canonical",
                    notes="Phase A benchmark with canonical drug labels",
                )
            )
    return rows


def collect_extended_images() -> list[Path]:
    if not EXTENDED_ROOT.exists():
        raise FileNotFoundError(f"Extended dataset path not found: {EXTENDED_ROOT}")

    imgs: list[Path] = []
    for p in EXTENDED_ROOT.rglob("*"):
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"} and p.is_file():
            imgs.append(p)
    return sorted(imgs)


def sample_extended_images(paths: list[Path], sample_size: int, seed: int) -> list[Path]:
    if sample_size <= 0:
        return []
    if len(paths) <= sample_size:
        return paths

    by_folder: dict[str, list[Path]] = defaultdict(list)
    for p in paths:
        by_folder[p.parent.name].append(p)

    total = len(paths)
    remaining = sample_size
    selected: list[Path] = []
    rng = random.Random(seed)

    # proportional allocation by parent folder
    folders = sorted(by_folder.keys())
    provisional: dict[str, int] = {}
    for folder in folders:
        quota = round(sample_size * (len(by_folder[folder]) / total))
        quota = min(quota, len(by_folder[folder]))
        provisional[folder] = quota

    allocated = sum(provisional.values())
    # adjust to exact sample size
    while allocated < sample_size:
        for folder in folders:
            if allocated >= sample_size:
                break
            if provisional[folder] < len(by_folder[folder]):
                provisional[folder] += 1
                allocated += 1
    while allocated > sample_size:
        for folder in folders:
            if allocated <= sample_size:
                break
            if provisional[folder] > 0:
                provisional[folder] -= 1
                allocated -= 1

    for folder in folders:
        quota = provisional[folder]
        if quota <= 0:
            continue
        candidates = list(by_folder[folder])
        rng.shuffle(candidates)
        selected.extend(sorted(candidates[:quota]))

    if len(selected) > sample_size:
        selected = sorted(selected)[:sample_size]

    if len(selected) < sample_size:
        selected_set = set(selected)
        leftovers = [p for p in paths if p not in selected_set]
        selected.extend(sorted(leftovers)[: sample_size - len(selected)])

    return sorted(selected)


def build_extended_rows(paths: list[Path]) -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    for p in paths:
        rel = p.relative_to(ROOT)
        width, height = image_shape(p)
        rows.append(
            ManifestRow(
                image_id=p.stem,
                split="extended_unlabeled",
                subset=p.parent.name,
                group_id="extended_pool",
                relative_path=str(rel),
                filename=p.name,
                width=width,
                height=height,
                sha256=sha256_file(p),
                include_eval="yes",
                label_status="unlabeled",
                notes="Used for stress testing only; not included in extraction-accuracy metrics",
            )
        )
    return rows


def write_manifest(rows: list[ManifestRow]) -> None:
    EVAL_V2_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = EVAL_V2_DIR / "phase_a_manifest_v2.csv"

    fieldnames = [
        "image_id",
        "split",
        "subset",
        "group_id",
        "relative_path",
        "filename",
        "width",
        "height",
        "sha256",
        "include_eval",
        "label_status",
        "notes",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "image_id": row.image_id,
                    "split": row.split,
                    "subset": row.subset,
                    "group_id": row.group_id,
                    "relative_path": row.relative_path,
                    "filename": row.filename,
                    "width": row.width,
                    "height": row.height,
                    "sha256": row.sha256,
                    "include_eval": row.include_eval,
                    "label_status": row.label_status,
                    "notes": row.notes,
                }
            )


def write_protocol(total_core: int, total_extended: int) -> None:
    content = f"""# Phase A Evaluation Protocol v2

## 1) Dataset composition

- Core labeled benchmark: `{total_core}` images from `data/input/prescription_1..7`
- Extended unlabeled pool sample: `{total_extended}` images sampled from `data/input/Data-20260420T154328Z-3-001/Data`

## 2) Evaluation tracks

### Track A — Extraction accuracy (labeled)

- Uses only split `core_labeled`
- Metrics: micro precision/recall/F1, FP/FN, exact-match, CER/WER
- Purpose: assess extraction correctness against canonical ground truth

### Track B — Operational stress test (unlabeled)

- Uses split `extended_unlabeled`
- Metrics: runtime distribution, non-empty output rate, OCR-empty error rate
- Purpose: assess pipeline robustness under wider capture variability

## 3) Reporting rules

- Track A and Track B must never be merged into one aggregate accuracy claim.
- Non-empty output rate is an operational metric, not a correctness metric.
- Any conclusion on extraction accuracy must reference Track A only.
"""
    (EVAL_V2_DIR / "annotation_protocol_v2.md").write_text(content, encoding="utf-8")


def write_sampling_log(total_pool: int, selected_paths: list[Path], seed: int) -> None:
    by_subset: dict[str, int] = defaultdict(int)
    for p in selected_paths:
        by_subset[p.parent.name] += 1

    payload = {
        "generated_at": datetime.now().isoformat(),
        "seed": seed,
        "extended_pool_total_images": total_pool,
        "extended_sample_size": len(selected_paths),
        "extended_sample_by_subset": dict(sorted(by_subset.items())),
        "sampled_relative_paths": [str(p.relative_to(ROOT)) for p in selected_paths],
    }
    (EVAL_V2_DIR / "sampling_log.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_exclusion_log(total_pool: int, selected_count: int) -> None:
    text = f"""# Phase A Evaluation v2 Exclusion Log

- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Extended pool size: {total_pool}
- Extended sampled size: {selected_count}

## Notes

1. Extended images not sampled remain excluded from this thesis run to bound runtime.
2. Extended split is intentionally unlabeled and excluded from extraction-accuracy metrics.
3. Phase B assets remain out of scope for Phase A thesis evaluation.
"""
    (EVAL_V2_DIR / "exclusion_log_v2.md").write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extended-sample", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    core_rows = load_core_rows()
    ext_pool = collect_extended_images()
    ext_sample = sample_extended_images(ext_pool, args.extended_sample, args.seed)
    ext_rows = build_extended_rows(ext_sample)

    all_rows = core_rows + ext_rows
    write_manifest(all_rows)
    write_protocol(total_core=len(core_rows), total_extended=len(ext_rows))
    write_sampling_log(total_pool=len(ext_pool), selected_paths=ext_sample, seed=args.seed)
    write_exclusion_log(total_pool=len(ext_pool), selected_count=len(ext_rows))

    print("PASS: eval_v2 assets prepared")
    print(f"- core_labeled: {len(core_rows)}")
    print(f"- extended_unlabeled: {len(ext_rows)}")
    print("- manifest: data/eval_v2/phase_a_manifest_v2.csv")


if __name__ == "__main__":
    main()
