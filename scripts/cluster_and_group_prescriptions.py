#!/usr/bin/env python3
"""
Multi-signal prescription clustering & audit tool.
Produces:
1. data/manifests/prescriptions_manifest.json
2. data/manifests/prescriptions_manifest.csv
3. data/canonical_ground_truth/RX_xxx.json (Canonical Ground Truth templates)
4. data/manifests/prescription_splits.json (Leakage-free train/val/test splits)
5. docs/grouping_audit_report.md (Audit report for review)
"""

import csv
import glob
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.abspath("src"))

from rxie.grouping import (
    CanonicalMedication,
    CanonicalPrescriptionGT,
    ImageCaptureMetadata,
    PrescriptionGroup,
    PrescriptionsManifest,
    cluster_prescriptions_patient_aware,
    compute_content_similarity,
    create_prescription_splits,
    extract_content_features,
    extract_patient_name,
)


def load_ocr_file(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    bname = os.path.splitext(os.path.basename(path))[0]
    blocks = data.get("blocks", [])
    lines = []
    text_parts = []
    confidences = []
    angles = []

    for b in blocks:
        for l in b.get("lines", []):
            lines.append(l)
            t = l.get("text", "")
            if t:
                text_parts.append(t)
            c = l.get("confidence")
            if c is not None:
                confidences.append(float(c))
            a = l.get("angle")
            if a is not None:
                angles.append(float(a))

    full_text = " ".join(text_parts)
    word_count = len(full_text.split())
    mean_conf = statistics.mean(confidences) if confidences else 0.0
    detected_angle = statistics.median(angles) if angles else 0.0

    return {
        "image_id": bname,
        "filename": f"{bname}.jpg",
        "relative_path": path,
        "ocr_file": path,
        "text": full_text,
        "word_count": word_count,
        "line_count": len(lines),
        "mean_confidence": mean_conf,
        "detected_angle": detected_angle,
    }


def find_representative_keywords(text_list: list[str], top_k: int = 6) -> list[str]:
    from rxie.grouping import PRESCRIPTION_BOILERPLATE
    words = []
    for text in text_list:
        tokens = re.findall(r"\b[a-zA-ZÀ-ỹ0-9_]{3,}\b", text.lower())
        words.extend([t for t in tokens if t not in PRESCRIPTION_BOILERPLATE and not t.isdigit()])
    counter = Counter(words)
    return [w for w, _ in counter.most_common(top_k)]


def extract_diagnoses_from_texts(text_list: list[str]) -> list[str]:
    diags = set()
    for text in text_list:
        m = re.findall(r"(?:chẩn\s*đoán|icd)[\s:]+([A-Z0-9\s;,.-]{3,35})", text, re.IGNORECASE)
        for d in m:
            clean = d.strip()
            if len(clean) >= 3:
                diags.add(clean)
    return list(diags)[:3]


def main():
    output_dir = "data/output"
    manifest_dir = "data/manifests"
    gt_dir = "data/canonical_ground_truth"
    docs_dir = "docs"

    os.makedirs(manifest_dir, exist_ok=True)
    os.makedirs(gt_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)

    print("==================================================================")
    print("   RxIE Multi-Signal Prescription Clustering & Audit Tool         ")
    print("==================================================================")

    all_json = sorted(glob.glob(f"{output_dir}/**/*.json", recursive=True))
    non_mirror = [p for p in all_json if "mlkit_ocr" not in p]

    # Resolve duplicates
    unique_map = {}
    duplicates = defaultdict(list)
    for p in non_mirror:
        bid = os.path.splitext(os.path.basename(p))[0]
        duplicates[bid].append(p)
        if bid not in unique_map:
            unique_map[bid] = p

    dup_count = sum(len(paths) - 1 for paths in duplicates.values() if len(paths) > 1)
    print(f"[*] Total non-mirror OCR JSONs found : {len(non_mirror)}")
    print(f"[*] Duplicate files resolved         : {dup_count} duplicates across mirror folders")
    print(f"[*] Unique captures to group         : {len(unique_map)}")

    items = []
    for bid, path in unique_map.items():
        item = load_ocr_file(path)
        if item:
            items.append(item)

    print(f"[*] Loaded OCR geometry & text for {len(items)} images.")
    print("[*] Running Multi-Signal Discriminative Clustering (Encounter > Drugs > Patient)...")

    raw_clusters = cluster_prescriptions_patient_aware(items, content_sim_threshold=0.18)
    raw_clusters.sort(key=lambda c: len(c), reverse=True)

    print(f"[+] Discovered {len(raw_clusters)} distinct prescription groups!")

    groups: list[PrescriptionGroup] = []
    csv_rows = []
    audit_rows = []

    for i, cluster in enumerate(raw_clusters, start=1):
        rx_id = f"RX_{i:03d}"
        pat_id = f"PAT_{i:03d}"
        cluster_texts = [item["text"] for item in cluster]
        keywords = find_representative_keywords(cluster_texts)
        diagnoses = extract_diagnoses_from_texts(cluster_texts)

        # Detect prominent encounter code / hospital / doctor
        enc_counter = Counter([item.get("enc") for item in cluster if item.get("enc")])
        hosp_counter = Counter([item.get("hosp") for item in cluster if item.get("hosp")])
        enc_hint = enc_counter.most_common(1)[0][0] if enc_counter else None
        hosp_hint = hosp_counter.most_common(1)[0][0] if hosp_counter else None

        # Grouping status: verified if multi-signal or count >= 2, needs_review if singleton with 0 text
        avg_words = statistics.mean([item["word_count"] for item in cluster])
        if len(cluster) >= 2 or avg_words >= 30:
            status = "verified"
        else:
            status = "needs_review"

        # Compute intra-cluster similarities
        features_list = [item["features"] for item in cluster]
        sims = []
        if len(cluster) > 1:
            for idx_a in range(len(cluster)):
                for idx_b in range(idx_a + 1, len(cluster)):
                    sims.append(compute_content_similarity(features_list[idx_a], features_list[idx_b]))
            min_sim = min(sims) if sims else 1.0
            med_sim = statistics.median(sims) if sims else 1.0
        else:
            min_sim = 1.0
            med_sim = 1.0

        image_metas = []
        for item in sorted(cluster, key=lambda x: x["image_id"]):
            sim_to_group = 1.0
            if len(cluster) > 1:
                group_union = set.union(*features_list)
                sim_to_group = compute_content_similarity(item["features"], group_union)

            meta = ImageCaptureMetadata(
                image_id=item["image_id"],
                filename=item["filename"],
                relative_path=item["relative_path"],
                ocr_file=item["ocr_file"],
                word_count=item["word_count"],
                line_count=item["line_count"],
                mean_confidence=item["mean_confidence"],
                detected_angle=item["detected_angle"],
                similarity_to_group=round(sim_to_group, 3),
            )
            image_metas.append(meta)

            csv_rows.append({
                "prescription_id": rx_id,
                "patient_id": pat_id,
                "image_id": item["image_id"],
                "filename": item["filename"],
                "grouping_status": status,
                "word_count": item["word_count"],
                "line_count": item["line_count"],
                "mean_confidence": f"{item['mean_confidence']:.3f}",
                "detected_angle": f"{item['detected_angle']:.1f}",
                "encounter_hint": enc_hint or "N/A",
                "hospital_hint": hosp_hint or "N/A",
                "ocr_path": item["ocr_file"],
            })

        group = PrescriptionGroup(
            prescription_id=rx_id,
            patient_id=pat_id,
            grouping_status=status,
            image_count=len(image_metas),
            encounter_code_hint=enc_hint,
            hospital_hint=hosp_hint,
            doctor_hint=None,
            diagnoses_hint=diagnoses,
            representative_keywords=keywords,
            images=image_metas,
            min_similarity=round(min_sim, 3),
            median_similarity=round(med_sim, 3),
        )
        groups.append(group)

        audit_rows.append({
            "prescription_id": rx_id,
            "patient_id": pat_id,
            "image_count": len(image_metas),
            "status": status,
            "encounter_hint": enc_hint or "N/A",
            "hospital_hint": hosp_hint or "N/A",
            "sample_images": [img.image_id for img in image_metas[:4]],
            "keywords": keywords,
            "med_sim": round(med_sim, 3),
            "min_sim": round(min_sim, 3),
        })

        # Generate / scaffold upgraded canonical ground truth file
        gt_file = os.path.join(gt_dir, f"{rx_id}.json")
        sample_gt = CanonicalPrescriptionGT(
            prescription_id=rx_id,
            patient_id=pat_id,
            encounter_id=enc_hint,
            hospital_name=hosp_hint,
            annotation_status="empty",
            diagnoses=diagnoses,
            medications=[
                CanonicalMedication(
                    medication_id=f"{rx_id}_M01",
                    drug_raw="[Nhập tên thuốc]",
                    drug_normalized=None,
                    brand_raw=None,
                    brand_normalized=None,
                    strength_raw=None,
                    strength_normalized=None,
                    quantity_value_raw=None,
                    quantity_value_normalized=None,
                    quantity_unit_raw=None,
                    quantity_unit_normalized=None,
                    dosage_raw=None,
                    frequency_raw=None,
                    duration_raw=None,
                    route_raw=None,
                    instruction_raw=None,
                    instruction_normalized=None,
                )
            ],
            metadata={
                "image_count": len(image_metas),
                "grouping_status": status,
                "representative_keywords": keywords,
                "sample_images": [img.image_id for img in image_metas[:5]],
            },
        )
        with open(gt_file, "w", encoding="utf-8") as f:
            json.dump(sample_gt.model_dump(), f, ensure_ascii=False, indent=2)

    # Manifests
    verified_count = sum(1 for g in groups if g.grouping_status == "verified")
    manifest = PrescriptionsManifest(
        total_prescriptions=len(groups),
        total_images=len(items),
        verified_prescriptions_count=verified_count,
        duplicate_images_resolved=dup_count,
        groups=groups,
    )

    manifest_json_path = os.path.join(manifest_dir, "prescriptions_manifest.json")
    with open(manifest_json_path, "w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(), f, ensure_ascii=False, indent=2)

    manifest_csv_path = os.path.join(manifest_dir, "prescriptions_manifest.csv")
    with open(manifest_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "prescription_id", "patient_id", "image_id", "filename", "grouping_status",
            "word_count", "line_count", "mean_confidence", "detected_angle",
            "encounter_hint", "hospital_hint", "ocr_path"
        ])
        writer.writeheader()
        writer.writerows(csv_rows)

    # Split config (Only verified groups used in official splits)
    verified_rx_ids = [g.prescription_id for g in groups if g.grouping_status == "verified"]
    splits = create_prescription_splits(verified_rx_ids, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    splits["unverified_or_review"] = [g.prescription_id for g in groups if g.grouping_status != "verified"]

    splits_path = os.path.join(manifest_dir, "prescription_splits.json")
    with open(splits_path, "w", encoding="utf-8") as f:
        json.dump(splits, f, ensure_ascii=False, indent=2)

    # Markdown audit report
    audit_md_path = os.path.join(docs_dir, "grouping_audit_report.md")
    with open(audit_md_path, "w", encoding="utf-8") as f:
        f.write("# RxIE Multi-Signal Prescription Grouping Audit Report\n\n")
        f.write(f"- **Total Non-mirror OCR JSONs**: {len(non_mirror)}\n")
        f.write(f"- **Duplicate Files Resolved**: {dup_count} (exact duplicate mirror captures)\n")
        f.write(f"- **Unique Physical Captures Grouped**: {len(items)}\n")
        f.write(f"- **Total Prescriptions Discovered**: {len(groups)}\n")
        f.write(f"- **Verified Prescriptions Count**: {verified_count}\n\n")
        f.write("## Detailed Cluster Breakdown\n\n")
        f.write("| Prescription ID | Patient ID | Status | Images | Encounter Hint | Hospital Hint | Keywords | Sample Captures |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for row in audit_rows:
            kw_str = ", ".join(row["keywords"][:3])
            samples_str = ", ".join(row["sample_images"][:2])
            f.write(f"| **{row['prescription_id']}** | `{row['patient_id']}` | `{row['status']}` | {row['image_count']} | {row['encounter_hint']} | {row['hospital_hint']} | {kw_str} | {samples_str} |\n")

    print("\n------------------------------------------------------------------")
    print(f"✅ Generated JSON Manifest : {manifest_json_path}")
    print(f"✅ Generated CSV Manifest  : {manifest_csv_path}")
    print(f"✅ Generated GT Templates  : {gt_dir} ({len(groups)} templates)")
    print(f"✅ Generated Split Config  : {splits_path}")
    print(f"✅ Generated Audit Report  : {audit_md_path}")
    print("------------------------------------------------------------------")
    print("\nPrescription Groups Summary:")
    print(f"{'Prescription ID':<16} | {'Patient ID':<11} | {'Status':<13} | {'Captures':<9} | {'Encounter / Hospital'}")
    print("-" * 80)
    for g in groups:
        enc_hosp = f"{g.encounter_code_hint or ''} - {g.hospital_hint or ''}".strip(" -") or "N/A"
        print(f"{g.prescription_id:<16} | {g.patient_id:<11} | {g.grouping_status:<13} | {g.image_count:<9} | {enc_hosp[:35]}")

    print("==================================================================\n")


if __name__ == "__main__":
    main()
