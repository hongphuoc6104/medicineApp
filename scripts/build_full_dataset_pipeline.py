#!/usr/bin/env python3
"""
Full Dataset Pipeline for RxIE Sprint A:
1. Ingest all 437 ML Kit OCR JSON captures into rxie.ocr.v1 OcrDocuments.
2. Load and validate 27 atomic Canonical Ground Truth files.
3. Run anchor-based fuzzy alignment across all 437 documents.
4. Export relational V2 datasets (train.jsonl, val.jsonl, test.jsonl) into data/ner_dataset/.
5. Export flat BIO V1 datasets (bio_train.jsonl, bio_val.jsonl, bio_test.jsonl).
6. Export full alignment audit matrix into data/full_dataset_audit_matrix.json.
7. Verify zero-leakage split isolation.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Insert src into path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rxie.alignment import (
    align_prescription_to_ocr,
    generate_alignment_audit_report,
    generate_dataset_splits,
    verify_split_isolation,
)
from rxie.canonical_gt import (
    decompose_prescription,
    validate_canonical_gt,
)
from rxie.grouping import CanonicalPrescriptionGT
from rxie.ingestion import load_mlkit_ocr_document
from rxie.schemas import (
    AnnotationDocument,
    AnnotationDocumentV2,
    GoldEntity,
    OcrDocument,
)


def v2_to_flat_v1(doc_v2: AnnotationDocumentV2) -> AnnotationDocument:
    """Convert a relational V2 AnnotationDocument to a flat V1 AnnotationDocument."""
    v1_entities = [
        GoldEntity(
            type=e.type,
            text=e.text,
            start=e.start,
            end=e.end,
        )
        for e in doc_v2.entities
    ]
    return AnnotationDocument(
        schema_version="rxie.annotation.v1",
        document_id=doc_v2.document_id,
        raw_text=doc_v2.raw_text,
        entities=v1_entities,
    )


def main() -> None:
    root_dir = Path(__file__).resolve().parent.parent
    manifest_dir = root_dir / "data" / "manifests"
    ocr_dir = root_dir / "data" / "ocr_final"
    gt_dir = root_dir / "data" / "canonical_ground_truth"
    dataset_out_dir = root_dir / "data" / "ner_dataset"
    splits_cfg_path = manifest_dir / "balanced_prescription_splits.json"

    dataset_out_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================================")
    print("   RxIE Sprint A: Full Canonical Ingestion & Dataset Pipeline     ")
    print("==================================================================")

    # 1. Load Prescription Manifest
    manifest_path = manifest_dir / "prescriptions_manifest.json"
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Build image_id -> prescription_id mapping
    image_to_rx: dict[str, str] = {}
    for group in manifest_data.get("groups", []):
        rx_id = group["prescription_id"]
        for img in group.get("images", []):
            image_to_rx[img["image_id"]] = rx_id

    print(f"[*] Indexed {len(image_to_rx)} image-to-prescription mappings.")

    # 2. Load and validate 27 Canonical GTs
    canonical_gts: dict[str, CanonicalPrescriptionGT] = {}
    for gt_file in sorted(gt_dir.glob("RX_*.json")):
        with gt_file.open("r", encoding="utf-8") as f:
            gt_data = json.load(f)
        rx_gt = CanonicalPrescriptionGT.model_validate(gt_data)
        rx_gt = decompose_prescription(rx_gt)
        assert validate_canonical_gt(rx_gt), f"Invalid GT: {rx_gt.prescription_id}"
        canonical_gts[rx_gt.prescription_id] = rx_gt

    print(f"[+] Loaded and validated {len(canonical_gts)} atomic Canonical GT files.")

    # 3. Ingest and Align 437 OCR Captures
    aligned_docs_v2: list[AnnotationDocumentV2] = []
    all_alignment_records = []
    failed_ingest = []

    ocr_files = sorted(ocr_dir.glob("*.json"))
    print(f"[*] Ingesting and aligning {len(ocr_files)} OCR JSON files...")

    for ocr_path in ocr_files:
        doc_id = ocr_path.stem
        rx_id = image_to_rx.get(doc_id)

        if not rx_id or rx_id not in canonical_gts:
            # Hard cases or unmapped
            continue

        try:
            ocr_doc = load_mlkit_ocr_document(ocr_path, document_id=doc_id)
        except Exception as exc:
            failed_ingest.append((doc_id, str(exc)))
            continue

        rx_gt = canonical_gts[rx_id]
        anno_v2, records = align_prescription_to_ocr(rx_gt, ocr_doc)
        aligned_docs_v2.append(anno_v2)
        all_alignment_records.extend(records)

    print(f"[+] Successfully aligned {len(aligned_docs_v2)} captures.")
    if failed_ingest:
        print(f"[!] Ingestion failures: {len(failed_ingest)}")

    # 4. Generate Relational V2 Dataset Splits
    split_counts = generate_dataset_splits(
        aligned_documents=aligned_docs_v2,
        splits_config_path=splits_cfg_path,
        output_dir=dataset_out_dir,
    )
    print(f"[+] Exported V2 datasets -> {dataset_out_dir}:")
    print(f"    - train.jsonl: {split_counts['train']} documents")
    print(f"    - val.jsonl:   {split_counts['val']} documents")
    print(f"    - test.jsonl:  {split_counts['test']} documents")

    # 5. Export Flat BIO V1 Dataset Splits
    for split_name in ["train", "val", "test"]:
        v2_file = dataset_out_dir / f"{split_name}.jsonl"
        bio_v1_file = dataset_out_dir / f"bio_{split_name}.jsonl"

        v1_docs = []
        with v2_file.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    doc_v2 = AnnotationDocumentV2.model_validate_json(line)
                    v1_docs.append(v2_to_flat_v1(doc_v2))

        with bio_v1_file.open("w", encoding="utf-8") as f:
            for d in v1_docs:
                f.write(json.dumps(d.model_dump(mode="json"), ensure_ascii=False) + "\n")

    print(f"[+] Exported Flat V1 BIO datasets -> {dataset_out_dir}:")
    print(f"    - bio_train.jsonl, bio_val.jsonl, bio_test.jsonl")

    # 6. Generate and Export Alignment Audit Matrix
    audit_report = generate_alignment_audit_report(all_alignment_records)
    audit_path = root_dir / "data" / "full_dataset_audit_matrix.json"
    with audit_path.open("w", encoding="utf-8") as f:
        json.dump(audit_report, f, ensure_ascii=False, indent=2)

    print(f"[+] Exported Alignment Audit Matrix -> {audit_path}")
    print(f"    - Total records: {audit_report['total_records']}")
    print(f"    - Overall Match Rate: {audit_report['overall_match_rate']:.2%}")

    # 7. Verify Zero Leakage
    train_docs = [d for d in aligned_docs_v2 if d.prescription_id in set(json.load(open(splits_cfg_path))["train"])]
    val_docs = [d for d in aligned_docs_v2 if d.prescription_id in set(json.load(open(splits_cfg_path))["val"])]
    test_docs = [d for d in aligned_docs_v2 if d.prescription_id in set(json.load(open(splits_cfg_path))["test"])]

    isolation = verify_split_isolation(train_docs, val_docs, test_docs)
    print("==================================================================")
    print(f"Split Isolation Status: {'VERIFIED ZERO LEAKAGE' if isolation['is_isolated'] else 'LEAKAGE DETECTED!'}")
    print(f"Train RX: {isolation['train_rx_count']} | Val RX: {isolation['val_rx_count']} | Test RX: {isolation['test_rx_count']}")
    print("==================================================================")


if __name__ == "__main__":
    main()
