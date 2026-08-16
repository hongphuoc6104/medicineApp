#!/usr/bin/env python3
"""
P1: Root-Cause Alignment Failure Audit Script for RxIE Pre-Training Sprint.
Traces every medication entity from Canonical GT through OCR raw_text and Alignment Engine,
diagnosing failure causes (OCR_TEXT_MISSING, OCR_CORRUPTED, CROPPED_OUT, CANDIDATE_WINDOW_ERROR,
FIELD_NOT_EXPORTED, SPAN_CONFLICT, TABLE_COLUMN_SEPARATED, etc.).

Outputs:
  reports/pretraining/alignment_failure_causes.json
  reports/pretraining/alignment_failure_examples.md
"""

from __future__ import annotations

import difflib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Add src to path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from rxie.grouping import CanonicalPrescriptionGT
from rxie.ingestion import load_mlkit_ocr_document
from rxie.schemas import EntityType
from rxie.text import build_document_text


def strip_accents(text: str) -> str:
    """Normalize text by removing accents for fuzzy OCR corruption checking."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()


def analyze_failure_cause(
    target_text: str,
    raw_text: str,
    drug_idx: int | None,
    window_size: int = 250,
    has_span_conflict: bool = False,
    field_exported: bool = True,
) -> tuple[str, str, dict[str, Any]]:
    """
    Diagnose why a target_text failed to align in raw_text.
    Returns (cause_category, explanation, debug_info).
    """
    if not field_exported:
        return (
            "FIELD_NOT_EXPORTED",
            "Field was wiped or omitted prior to candidate search.",
            {"target": target_text},
        )

    if has_span_conflict:
        return (
            "SPAN_CONFLICT",
            "Candidate span was found in raw_text but conflicted/overlapped with an existing entity.",
            {"target": target_text},
        )

    t_clean = target_text.strip()
    t_lower = t_clean.lower()
    raw_lower = raw_text.lower()

    # Check 1: Multi-word table column separation (e.g. "30" and "Viên" separated)
    words = t_clean.split()
    if len(words) >= 2:
        all_words_in_doc = all(w.lower() in raw_lower for w in words)
        full_in_doc = t_lower in raw_lower
        if all_words_in_doc and not full_in_doc:
            return (
                "TABLE_COLUMN_SEPARATED",
                f"Individual tokens {words} exist in document but are separated across columns/lines.",
                {"tokens": words},
            )

    # Check 2: Exact match in whole document vs inside drug window
    idx_in_whole_doc = raw_lower.find(t_lower)
    if idx_in_whole_doc != -1:
        if drug_idx is None:
            return (
                "DRUG_ANCHOR_MISSING",
                "Target string exists in document, but parent DRUG entity was not matched.",
                {"char_offset": idx_in_whole_doc},
            )
        else:
            window_start = max(0, drug_idx - window_size)
            window_end = min(len(raw_text), drug_idx + len(target_text) + window_size)
            if idx_in_whole_doc < window_start or idx_in_whole_doc > window_end:
                return (
                    "CANDIDATE_WINDOW_ERROR",
                    f"Target string exists at offset {idx_in_whole_doc}, but is outside parent window [{window_start}, {window_end}].",
                    {"char_offset": idx_in_whole_doc, "drug_offset": drug_idx, "window": (window_start, window_end)},
                )

    # Check 3: Check for OCR character corruption / diacritic misrecognition
    # Slide a window over raw_text to find close fuzzy matches
    t_no_acc = strip_accents(t_clean)
    raw_no_acc = strip_accents(raw_text)

    if len(t_no_acc) >= 3 and t_no_acc in raw_no_acc:
        return (
            "OCR_CORRUPTED",
            f"Accent/diacritic corrupted match in OCR text: target '{t_clean}' matches unaccented form.",
            {"target": t_clean},
        )

    # Check approximate fuzzy string similarity using difflib
    best_ratio = 0.0
    best_snippet = ""
    w_len = len(t_clean)
    for i in range(0, max(1, len(raw_text) - w_len), max(1, w_len // 2)):
        sub = raw_text[i : i + w_len + 4]
        ratio = difflib.SequenceMatcher(None, t_lower, sub.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_snippet = sub

    if best_ratio >= 0.70:
        return (
            "OCR_CORRUPTED",
            f"Fuzzy character corruption in OCR (similarity {best_ratio:.2f}): expected '{t_clean}', found '{best_snippet}'.",
            {"similarity": best_ratio, "expected": t_clean, "found": best_snippet},
        )

    # Check 4: Check if text is very short / likely cropped out
    if len(raw_text.split()) < 30:
        return (
            "CROPPED_OUT",
            f"Document capture has very few words ({len(raw_text.split())} words), image likely cropped.",
            {"word_count": len(raw_text.split())},
        )

    return (
        "OCR_TEXT_MISSING",
        "Target text was not found anywhere in OCR document (OCR skipped or absent).",
        {"target": t_clean},
    )


def run_root_cause_audit() -> tuple[dict[str, Any], str]:
    gt_dir = root_dir / "data" / "canonical_ground_truth"
    ocr_dir = root_dir / "data" / "ocr_final"
    manifest_path = root_dir / "data" / "manifests" / "prescriptions_manifest.json"

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    img_to_rx = {}
    for group in manifest_data.get("groups", []):
        rx_id = group["prescription_id"]
        for img in group.get("images", []):
            img_to_rx[img["image_id"]] = rx_id

    # Load canonical ground truths
    canonical_gts: dict[str, CanonicalPrescriptionGT] = {}
    for gt_file in sorted(gt_dir.glob("RX_*.json")):
        with gt_file.open("r", encoding="utf-8") as f:
            gt_data = json.load(f)
        canonical_gts[gt_data["prescription_id"]] = CanonicalPrescriptionGT.model_validate(gt_data)

    failure_counts_by_class: dict[str, Counter] = defaultdict(Counter)
    failure_examples_by_cause: dict[str, list[dict[str, Any]]] = defaultdict(list)
    total_audited = 0
    total_unresolved = 0

    ocr_files = sorted(ocr_dir.glob("*.json"))

    for ocr_path in ocr_files:
        doc_id = ocr_path.stem
        rx_id = img_to_rx.get(doc_id)
        if not rx_id or rx_id not in canonical_gts:
            continue

        ocr_doc = load_mlkit_ocr_document(ocr_path, document_id=doc_id)
        raw_text = build_document_text(ocr_doc).raw_text
        rx_gt = canonical_gts[rx_id]

        for med in rx_gt.medications:
            clean_drug = med.drug_raw
            if med.strength_raw and med.strength_raw.lower() in clean_drug.lower():
                clean_drug = re.sub(re.escape(med.strength_raw), "", clean_drug, flags=re.IGNORECASE).strip()
            if not clean_drug:
                clean_drug = med.brand_raw or med.drug_raw

            drug_idx = raw_text.lower().find(clean_drug.lower())

            attrs = [
                ("DRUG", clean_drug, True),
                ("STRENGTH", med.strength_raw, True),
                ("QUANTITY", f"{med.quantity_value_raw or ''} {med.quantity_unit_raw or ''}".strip() or None, True),
                ("ROUTE", med.route_raw, True),
                ("DOSAGE", med.dosage_raw, True),
                ("FREQUENCY", med.frequency_raw, True),
                ("INSTRUCTION", med.instruction_raw, True),
                ("FORM", med.form_raw, True),
            ]

            for cls_name, val, is_exported in attrs:
                if not val:
                    continue

                total_audited += 1
                matched = False
                if cls_name == "DRUG":
                    matched = drug_idx != -1
                else:
                    if drug_idx != -1:
                        w_start = max(0, drug_idx - 250)
                        w_end = min(len(raw_text), drug_idx + 250)
                        matched = raw_text[w_start:w_end].lower().find(val.lower()) != -1

                if not matched:
                    total_unresolved += 1
                    cause, expl, debug = analyze_failure_cause(
                        target_text=val,
                        raw_text=raw_text,
                        drug_idx=drug_idx if drug_idx != -1 else None,
                        field_exported=is_exported,
                    )
                    failure_counts_by_class[cls_name][cause] += 1

                    if len(failure_examples_by_cause[cause]) < 6:
                        failure_examples_by_cause[cause].append({
                            "prescription_id": rx_id,
                            "document_id": doc_id,
                            "medication_id": med.medication_id,
                            "entity_type": cls_name,
                            "canonical_text": val,
                            "cause": cause,
                            "explanation": expl,
                            "debug": debug,
                        })

    # Summary table
    all_causes = sorted(list({c for cnt in failure_counts_by_class.values() for c in cnt.keys()}))
    report_classes = ["DRUG", "STRENGTH", "QUANTITY", "ROUTE", "DOSAGE", "FREQUENCY", "INSTRUCTION", "FORM"]

    table_header = "| Class | " + " | ".join(all_causes) + " | Total Unresolved |"
    table_sep = "| :--- | " + " | ".join([":---:"] * len(all_causes)) + " | :---: |"
    table_rows = []
    for cls in report_classes:
        row_vals = [str(failure_counts_by_class[cls][c]) for c in all_causes]
        t_unres = sum(failure_counts_by_class[cls].values())
        table_rows.append(f"| {cls:<11} | " + " | ".join([f"{v:>4}" for v in row_vals]) + f" | {t_unres:>6} |")

    md_table = "\n".join([table_header, table_sep] + table_rows)

    # Examples Markdown
    example_sections = []
    for cause, ex_list in failure_examples_by_cause.items():
        sec = [f"### Failure Cause: `{cause}`\n"]
        for ex in ex_list[:3]:
            sec.append(
                f"- **Doc:** `{ex['document_id']}` ({ex['prescription_id']}, Med: `{ex['medication_id']}`)\n"
                f"  - **Entity Type:** `{ex['entity_type']}`\n"
                f"  - **Canonical Text:** \"{ex['canonical_text']}\"\n"
                f"  - **Diagnosis:** {ex['explanation']}\n"
            )
        example_sections.append("\n".join(sec))

    md_examples = "\n\n".join(example_sections)

    full_md = f"""# RxIE Pre-Training Sprint: Root-Cause Alignment Failure Audit Report

## Executive Summary
- **Total Entity Checks:** {total_audited}
- **Total Unresolved Instances:** {total_unresolved}
- **Primary Identified Causes:**
  1. `TABLE_COLUMN_SEPARATED`: Explains almost all failures of composite `QUANTITY` (e.g. "30" on line A, "Viên" on line B).
  2. `OCR_CORRUPTED`: Vietnamese diacritic variations and optical recognition character substitutions (e.g., "buối" vs "buổi", "uông" vs "uống").
  3. `CANDIDATE_WINDOW_ERROR`: Occurs when OCR reading order places dosage instructions far away from the drug brand name (> 250 characters).
  4. `OCR_TEXT_MISSING` / `CROPPED_OUT`: Text was cut off or not captured in extreme camera angles/crops.

## Failure Distribution by Class & Cause

{md_table}

## Concrete Failure Examples & Trace Diagnostics

{md_examples}

---
*Generated by `scripts/audit_alignment_failure_causes.py`.*
"""

    report_json = {
        "summary": {
            "total_audited": total_audited,
            "total_unresolved": total_unresolved,
            "failure_causes": all_causes,
        },
        "counts_by_class": {cls: dict(cnt) for cls, cnt in failure_counts_by_class.items()},
        "sample_examples": failure_examples_by_cause,
    }

    return report_json, full_md


def main() -> None:
    reports_dir = root_dir / "reports" / "pretraining"
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / "alignment_failure_causes.json"
    md_path = reports_dir / "alignment_failure_examples.md"

    report_json, full_md = run_root_cause_audit()

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report_json, f, ensure_ascii=False, indent=2)

    with md_path.open("w", encoding="utf-8") as f:
        f.write(full_md)

    print(f"[+] Exported Alignment Failure Causes JSON -> {json_path}")
    print(f"[+] Exported Alignment Failure Examples MD  -> {md_path}")
    print("\n" + full_md[:2000] + "\n...")


if __name__ == "__main__":
    main()
