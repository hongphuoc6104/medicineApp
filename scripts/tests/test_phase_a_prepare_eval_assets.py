"""
Prepare reproducible evaluation assets for Phase A thesis benchmarking.

This script creates:
- data/eval/phase_a_manifest.csv
- data/eval/exclusion_log.md
- data/eval/annotation_protocol.md
- data/eval/canonical_drug_aliases.json
- data/eval/gt_drugs_by_group.json
- data/eval/gt_drugs_by_image.json
- data/eval/gt_ocr_subset.jsonl

Usage:
    venv/bin/python scripts/tests/test_phase_a_prepare_eval_assets.py
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_INPUT = ROOT / "data" / "input"
DATA_EVAL = ROOT / "data" / "eval"


@dataclass(frozen=True)
class CanonicalDrug:
    canonical_id: str
    display_name: str
    aliases: list[str]


CANONICAL_DRUGS: list[CanonicalDrug] = [
    CanonicalDrug("ginkgo_biloba", "Ginkgo Biloba", ["ginkgo", "biloba", "tanakan"]),
    CanonicalDrug("calcium_d3", "Calcium D3", ["calcium d3", "calcium", "corbiere"]),
    CanonicalDrug("vitamin_c", "Vitamin C", ["vitamin c", "upsa c"]),
    CanonicalDrug("magnesium_b6", "Magnesium B6", ["magnesium b6", "magne-b6", "magne"]),
    CanonicalDrug("artificial_tears", "Artificial Tears", ["artificial tears", "refresh"]),
    CanonicalDrug("celecoxib", "Celecoxib", ["celecoxib", "celebrex"]),
    CanonicalDrug("eperisone", "Eperisone", ["eperisone", "eperison", "myonal"]),
    CanonicalDrug("mecobalamin", "Mecobalamin", ["mecobalamin", "methycobal", "drikryl"]),
    CanonicalDrug("loratadine", "Loratadine", ["loratadine", "clarityne"]),
    CanonicalDrug("paracetamol", "Paracetamol", ["paracetamol", "panadol", "uphadol"]),
    CanonicalDrug("rosuvastatin", "Rosuvastatin", ["rosuvastatin", "crestor"]),
    CanonicalDrug("atorvastatin", "Atorvastatin", ["atorvastatin", "lipitor"]),
    CanonicalDrug("ezetimibe", "Ezetimibe", ["ezetimibe", "ezetrol"]),
    CanonicalDrug("amlodipine", "Amlodipine", ["amlodipine", "amlor"]),
    CanonicalDrug("metformin", "Metformin", ["metformin", "glucophage"]),
    CanonicalDrug("bisoprolol", "Bisoprolol", ["bisoprolol", "concor"]),
    CanonicalDrug("esomeprazole", "Esomeprazole", ["esomeprazole", "nexium"]),
]


GROUP_GT: dict[str, list[str]] = {
    "prescription_1": [
        "ginkgo_biloba",
        "calcium_d3",
        "vitamin_c",
        "magnesium_b6",
        "artificial_tears",
    ],
    "prescription_2": [
        "celecoxib",
        "eperisone",
        "mecobalamin",
        "loratadine",
        "paracetamol",
    ],
    "prescription_3": [
        "celecoxib",
        "eperisone",
        "mecobalamin",
        "loratadine",
        "paracetamol",
    ],
    "prescription_4": [
        "rosuvastatin",
        "atorvastatin",
        "ezetimibe",
    ],
    "prescription_5": [
        "amlodipine",
        "metformin",
        "atorvastatin",
        "bisoprolol",
        "esomeprazole",
    ],
    "prescription_6": [
        "celecoxib",
        "eperisone",
        "mecobalamin",
        "loratadine",
        "paracetamol",
    ],
    "prescription_7": [
        "amlodipine",
        "metformin",
        "atorvastatin",
        "bisoprolol",
        "esomeprazole",
    ],
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_images() -> list[Path]:
    groups = sorted(GROUP_GT.keys())
    images: list[Path] = []
    for group in groups:
        group_dir = DATA_INPUT / group
        group_imgs = sorted(
            [
                p
                for p in group_dir.iterdir()
                if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
            ]
        )
        images.extend(group_imgs)
    return images


def write_manifest(images: list[Path]) -> None:
    DATA_EVAL.mkdir(parents=True, exist_ok=True)
    out_csv = DATA_EVAL / "phase_a_manifest.csv"

    fields = [
        "image_id",
        "group_id",
        "relative_path",
        "filename",
        "width",
        "height",
        "sha256",
        "include_eval",
        "exclude_reason",
    ]

    import cv2

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for img in images:
            matrix = cv2.imread(str(img))
            if matrix is None:
                width = ""
                height = ""
            else:
                height, width = matrix.shape[:2]

            image_id = img.stem
            group_id = img.parent.name
            rel = img.relative_to(ROOT)
            writer.writerow(
                {
                    "image_id": image_id,
                    "group_id": group_id,
                    "relative_path": str(rel),
                    "filename": img.name,
                    "width": width,
                    "height": height,
                    "sha256": sha256_file(img),
                    "include_eval": "yes",
                    "exclude_reason": "",
                }
            )


def write_exclusion_log() -> None:
    text = """# Phase A Evaluation Exclusion Log

- Evaluation date: {date}
- Manifest file: `data/eval/phase_a_manifest.csv`
- Policy: only finalized image files (`.jpg`, `.jpeg`, `.png`) under `data/input/prescription_1..7` are included.

## Excluded artifacts

1. `data/input/Unconfirmed 823414.crdownload`
   - Reason: incomplete browser download artifact, not a valid image file.
   - Impact: no impact on 50-image benchmark because file is outside prescription folders and unreadable by pipeline.

2. `data/input/Phase_B /...`
   - Reason: Phase B pill-verification assets, outside Phase A prescription extraction scope.
   - Impact: intentionally excluded from this thesis evaluation chapter.
""".format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    (DATA_EVAL / "exclusion_log.md").write_text(text, encoding="utf-8")


def write_annotation_protocol() -> None:
    text = """# Phase A Annotation Protocol (Drug Extraction)

## 1) Evaluation objective

The benchmark evaluates **drug-name extraction quality** from real prescription images,
not full-document information extraction.

## 2) Unit of analysis

- Primary unit: one prescription image.
- Ground truth target per image: set of canonical drug labels.

## 3) Ground-truth construction strategy

- The dataset contains seven prescription groups (`prescription_1..7`).
- The evaluation file used for scoring is `gt_drugs_by_image.json`, which stores one canonical drug set per image.
- Repeated-capture groups are retained only as provenance metadata because many images come from the same underlying prescription template.
- In the current 50-image benchmark, images within the same repeated-capture group still share the same canonical drug set; this reduces label ambiguity but does not remove the limitation of low template diversity.

## 4) Canonicalization rules

- Match by active ingredient or stable trade-name aliases.
- Ignore punctuation, casing, and dosage formatting differences.
- Do not count quantity/instruction text as drug entities.

## 5) Metrics

- Precision / Recall / F1 (micro) for extracted drug entities.
- False positive (FP) and false negative (FN) counts.
- Image exact-match rate (predicted set == reference set).
- Runtime: cold-start latency, warm latency mean, P50, P90.
- Drug-text CER/WER on the image-level OCR proxy reference set (`gt_ocr_subset.jsonl`).

## 6) Scope and limitations

- This protocol is designed for Phase A medication-list extraction.
- It does not claim full prescription OCR accuracy for administrative fields.
- Although scoring is performed at image level, the benchmark still contains repeated captures of only seven underlying prescriptions.
- Because of that repeated-capture structure, the benchmark is suitable for controlled comparison between configurations but should not be interpreted as a population-level estimate across all prescription layouts.
"""
    (DATA_EVAL / "annotation_protocol.md").write_text(text, encoding="utf-8")


def write_canonical_aliases() -> None:
    payload = {
        "generated_at": datetime.now().isoformat(),
        "canonical_drugs": [
            {
                "canonical_id": d.canonical_id,
                "display_name": d.display_name,
                "aliases": d.aliases,
            }
            for d in CANONICAL_DRUGS
        ],
    }
    (DATA_EVAL / "canonical_drug_aliases.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_ground_truth(images: list[Path]) -> None:
    display_by_id = {d.canonical_id: d.display_name for d in CANONICAL_DRUGS}

    by_group = {
        "generated_at": datetime.now().isoformat(),
        "group_ground_truth": {
            group: [
                {"canonical_id": cid, "display_name": display_by_id[cid]}
                for cid in cids
            ]
            for group, cids in GROUP_GT.items()
        },
    }
    (DATA_EVAL / "gt_drugs_by_group.json").write_text(
        json.dumps(by_group, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    image_rows = []
    for img in images:
        group = img.parent.name
        cids = GROUP_GT[group]
        image_rows.append(
            {
                "image_id": img.stem,
                "group_id": group,
                "relative_path": str(img.relative_to(ROOT)),
                "expected_drugs": [
                    {"canonical_id": cid, "display_name": display_by_id[cid]}
                    for cid in cids
                ],
            }
        )

    by_image = {
        "generated_at": datetime.now().isoformat(),
        "image_count": len(image_rows),
        "images": image_rows,
    }
    (DATA_EVAL / "gt_drugs_by_image.json").write_text(
        json.dumps(by_image, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_ocr_subset(images: list[Path]) -> None:
    display_by_id = {d.canonical_id: d.display_name for d in CANONICAL_DRUGS}

    out_path = DATA_EVAL / "gt_ocr_subset.jsonl"
    rows = []
    for img in images:
        group = img.parent.name
        for cid in GROUP_GT[group]:
            rows.append(
                {
                    "image_id": img.stem,
                    "group_id": group,
                    "relative_path": str(img.relative_to(ROOT)),
                    "canonical_id": cid,
                    "reference_text": display_by_id[cid],
                }
            )

    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    DATA_EVAL.mkdir(parents=True, exist_ok=True)
    images = collect_images()
    if len(images) != 50:
        raise RuntimeError(f"Expected 50 Phase A images but found {len(images)}")

    write_manifest(images)
    write_exclusion_log()
    write_annotation_protocol()
    write_canonical_aliases()
    write_ground_truth(images)
    write_ocr_subset(images)

    print("PASS: evaluation assets prepared")
    print(" - data/eval/phase_a_manifest.csv")
    print(" - data/eval/gt_drugs_by_image.json")
    print(" - data/eval/gt_ocr_subset.jsonl")


if __name__ == "__main__":
    main()
