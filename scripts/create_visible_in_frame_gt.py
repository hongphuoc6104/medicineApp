"""
scripts/create_visible_in_frame_gt.py — Generates precise visible-in-frame ground truth
for all 30 hard real camera captures evaluated in the R0 vs R1 ROI benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path


def create_visible_gt(output_path: Path):
    """Create fine-grained visible-in-frame ground truth mapping."""
    # 1. Section definitions for RX_001
    rx001_sec1 = ["Amlor", "Glucophage XR", "Lipitor", "Concor"] # Top 4
    rx001_sec2 = ["Celebrex", "Myonal", "Methycobal", "Clarityne", "Panadol"] # Middle 5
    rx001_sec3 = ["Tanakan", "Calcium Corbiere", "Upsa C", "Magne-B6 Corbiere", "Refresh"] # Bottom 5

    # 2. RX_002 visible medications (printed on the 115 hospital prescription table)
    rx002_meds = ["Lipitor", "Lipanthyl", "Crestor", "Cozaar"]

    # 3. Mapping for all 30 captures
    visible_gt = {
        # RX_001 Captures (20)
        "IMG_20260209_180502": {"prescription_id": "RX_001", "visible_drugs": rx001_sec2},
        "IMG_20260209_180408": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_180425": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_180708": {"prescription_id": "RX_001", "visible_drugs": rx001_sec1},
        "IMG_20260209_180428": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002500": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_181415": {"prescription_id": "RX_001", "visible_drugs": rx001_sec2},
        "IMG_20260209_002819": {"prescription_id": "RX_001", "visible_drugs": rx001_sec2},
        "IMG_20260209_180847": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_180851": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002313": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002409": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002435": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002440": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002444": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002447": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002453": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002456": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002501": {"prescription_id": "RX_001", "visible_drugs": rx001_sec3},
        "IMG_20260209_002656": {"prescription_id": "RX_001", "visible_drugs": rx001_sec2},

        # RX_016 Captures (2)
        "IMG_20260209_180336": {"prescription_id": "RX_016", "visible_drugs": ["Telfast", "Zyrtec"]},
        "IMG_20260209_181346": {"prescription_id": "RX_016", "visible_drugs": ["Telfast", "Zyrtec"]},

        # RX_019 Capture (1)
        "IMG_20260122_010316": {
            "prescription_id": "RX_019",
            "visible_drugs": [
                "Panadol",
                "Voltaren Emulgel",
                "Celebrex",
                "Rotunda",
                "Magne-B6",
                "Micardis",
                "Amlor",
                "Hypothiazid",
            ],
        },

        # RX_023 Capture (1)
        "IMG_20260209_181327": {"prescription_id": "RX_023", "visible_drugs": ["Telfast", "Zyrtec"]},

        # RX_002 Captures (6)
        "IMG_20260115_181847": {"prescription_id": "RX_002", "visible_drugs": rx002_meds},
        "IMG_20260115_181852": {"prescription_id": "RX_002", "visible_drugs": rx002_meds},
        "IMG_20260115_181855": {"prescription_id": "RX_002", "visible_drugs": rx002_meds},
        "IMG_20260115_181919": {"prescription_id": "RX_002", "visible_drugs": rx002_meds},
        "IMG_20260115_181921": {"prescription_id": "RX_002", "visible_drugs": rx002_meds},
        "IMG_20260115_181922": {"prescription_id": "RX_002", "visible_drugs": rx002_meds},
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(visible_gt, f, ensure_ascii=False, indent=2)

    print(f"Saved visible-in-frame GT for {len(visible_gt)} captures to: {output_path.resolve()}")


if __name__ == "__main__":
    create_visible_gt(Path("data/visible_in_frame_gt.json"))
