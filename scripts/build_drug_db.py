#!/usr/bin/env python3
"""
Build drug_db.json from real data sources:
- Zero-PIMA/data/pill_information.csv (color, shape)
- data/vaipe_drugs_kb.json (name, brand, dosage)
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PILL_CSV = os.path.join(ROOT, "Zero-PIMA", "data", "pill_information.csv")
VAIPE_KB = os.path.join(ROOT, "data", "vaipe_drugs_kb.json")
OUTPUT = os.path.join(ROOT, "server", "data", "drug_db.json")


def build():
    # Load pill_information.csv (color, shape)
    pill_info = {}
    with open(PILL_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Pill"].strip()
            pill_info[name.lower().replace("-", "")] = {
                "pill_name": name,
                "color": row.get("Color", "unknown"),
                "shape": row.get("Shape", "unknown"),
            }

    # Load vaipe_drugs_kb.json (name, brand, dosage)
    with open(VAIPE_KB, encoding="utf-8") as f:
        vaipe = json.load(f)

    # Merge
    db = {}
    for vid, vinfo in vaipe.items():
        name = vinfo["name"]
        key = name.lower().replace("-", "")

        entry = {
            "id": int(vid),
            "name": name,
            "brand": vinfo.get("brand", name),
            "dosage": vinfo.get("dosage", ""),
            "color": "unknown",
            "shape": "unknown",
            "usage": "",
            "side_effects": "",
            "source": "vaipe",
        }

        # Match with pill_information.csv
        if key in pill_info:
            entry["color"] = pill_info[key]["color"]
            entry["shape"] = pill_info[key]["shape"]
        else:
            # Try partial match
            for pkey, pval in pill_info.items():
                if pkey.startswith(key[:8]) or key.startswith(pkey[:8]):
                    entry["color"] = pval["color"]
                    entry["shape"] = pval["shape"]
                    break

        db[name] = entry

    # Add pill_information entries not in vaipe
    for pkey, pval in pill_info.items():
        pname = pval["pill_name"]
        if pname not in db:
            db[pname] = {
                "id": -1,
                "name": pname,
                "brand": pname,
                "dosage": "",
                "color": pval["color"],
                "shape": pval["shape"],
                "usage": "",
                "side_effects": "",
                "source": "pill_csv",
            }

    # Save
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"✅ Drug DB: {len(db)} drugs → {OUTPUT}")

    # Stats
    with_color = sum(1 for v in db.values() if v["color"] != "unknown")
    print(f"   With color/shape: {with_color}/{len(db)}")

    return db


if __name__ == "__main__":
    build()
