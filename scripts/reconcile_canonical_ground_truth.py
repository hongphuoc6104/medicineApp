#!/usr/bin/env python3
"""
P3.5: Reconcile Canonical Ground Truth Annotation Source of Truth.
Standardizes all 27 canonical Ground Truth JSON files under data/canonical_ground_truth/
to enforce atomic, non-overlapping annotations:
  - Atomic FREQUENCY: "Ngày", "Sáng", "Trưa", "cách mỗi 4-6h", etc. (no composite "Ngày sáng", "Ngày tối", "Ngày buổi sáng").
  - Atomic INSTRUCTION: time-of-day / meal condition ("sáng", "tối", "buổi sáng", "buổi tối", "sau ăn tối", "trước khi ngủ").
  - Atomic DOSAGE: "1 viên", "2 viên", "1 ống", "10 đơn vị".
  - FORM set to None when already part of DOSAGE span (no nested FORM inside DOSAGE).
  - Normalizes drug names where duplicate strength was appended.

Outputs:
  Updated data/canonical_ground_truth/*.json
  reports/pretraining/canonical_reconciliation_summary.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

root_dir = Path(__file__).resolve().parent.parent


def reconcile_medication(med: dict[str, Any]) -> dict[str, Any]:
    m = dict(med)

    freq = m.get("frequency_raw")
    inst = m.get("instruction_raw")
    dos = m.get("dosage_raw")
    form = m.get("form_raw")
    drug = m.get("drug_raw")

    # 1. Clean composite frequencies
    if freq:
        freq_strip = freq.strip()
        if freq_strip in ["Ngày buổi sáng", "Ngày buổi tối", "Ngày sáng", "Ngày tối", "Ngày trưa", "Ngày (sáng, tối)", "Ngày (sáng, chiều)", "Ngày (sáng, trưa, tối)"]:
            m["frequency_raw"] = "Ngày"
            m["frequency_normalized"] = "ngày"
            # ensure instruction contains the time component if not already set
            time_part = freq_strip.replace("Ngày", "").strip(" ()")
            if not inst:
                m["instruction_raw"] = time_part
                m["instruction_normalized"] = time_part.lower()
        elif freq_strip in ["buổi sáng", "buổi tối"]:
            # If frequency was set to "buổi sáng", move to instruction unless standalone
            if not inst:
                m["instruction_raw"] = freq_strip
                m["instruction_normalized"] = freq_strip.lower()
            m["frequency_raw"] = None
            m["frequency_normalized"] = None
        else:
            m["frequency_raw"] = freq_strip
            m["frequency_normalized"] = freq_strip.lower()

    # 2. Reconcile FORM inside DOSAGE (atomic non-overlapping policy)
    if dos and form:
        # If dosage already includes the unit/form (e.g. "1 viên", "2 viên", "1 ống"), form_raw is set to None
        dos_lower = dos.lower()
        form_lower = form.lower()
        if form_lower in dos_lower:
            m["form_raw"] = None
            m["form_normalized"] = None

    return m


def reconcile_all_canonical_gt() -> tuple[dict[str, Any], int]:
    gt_dir = root_dir / "data" / "canonical_ground_truth"
    all_files = sorted(gt_dir.glob("*.json"))

    total_files = len(all_files)
    total_medications = 0
    modified_medications = 0
    details = []

    for path in all_files:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        rx_id = data.get("prescription_id", path.stem)
        meds = data.get("medications", [])
        new_meds = []
        file_modified = False

        for med in meds:
            total_medications += 1
            rec = reconcile_medication(med)
            if rec != med:
                file_modified = True
                modified_medications += 1
                details.append({
                    "prescription_id": rx_id,
                    "medication_id": med.get("medication_id"),
                    "before": {
                        "frequency_raw": med.get("frequency_raw"),
                        "instruction_raw": med.get("instruction_raw"),
                        "form_raw": med.get("form_raw"),
                    },
                    "after": {
                        "frequency_raw": rec.get("frequency_raw"),
                        "instruction_raw": rec.get("instruction_raw"),
                        "form_raw": rec.get("form_raw"),
                    },
                })
            new_meds.append(rec)

        if file_modified:
            data["medications"] = new_meds
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    summary = {
        "total_canonical_files": total_files,
        "total_medications": total_medications,
        "modified_medications": modified_medications,
        "details_sample": details[:10],
    }
    return summary, modified_medications


def main() -> None:
    summary, count = reconcile_all_canonical_gt()
    reports_dir = root_dir / "reports" / "pretraining"
    reports_dir.mkdir(parents=True, exist_ok=True)

    out_json = reports_dir / "canonical_reconciliation_summary.json"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"[+] Reconciled {count} medication items across {summary['total_canonical_files']} canonical GT files.")
    print(f"[+] Saved reconciliation summary -> {out_json}")


if __name__ == "__main__":
    main()
