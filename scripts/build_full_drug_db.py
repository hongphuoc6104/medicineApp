"""
Build comprehensive drug database from free APIs.

Sources:
1. DDI Lab VN (ddi.lab.io.vn) — 9000+ Vietnamese drugs
2. Local VAIPE data (pill_information.csv) — color, shape
3. Mapping: baoChe → shape, taDuoc → color

Output: server/data/drug_db_full.json
"""

import asyncio
import csv
import json
import re
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent
DDI_BASE = "https://ddi.lab.io.vn/api"
OUTPUT = ROOT / "server" / "data" / "drug_db_full.json"
VAIPE_CSV = ROOT / "Zero-PIMA" / "data" / "pill_information.csv"

# ── Mapping tables ───────────────────────────────────

# Vietnamese dosage form → English shape
BAOCE_TO_SHAPE = {
    "viên nén": "round",
    "viên nén dài": "oblong",
    "viên nén bao phim": "oval",
    "viên nén bao đường": "round",
    "viên nén sủi": "round",
    "viên nén phân tán": "round",
    "viên nén nhai": "round",
    "viên nang cứng": "capsule",
    "viên nang mềm": "capsule",
    "viên nang": "capsule",
    "viên bao phim": "oval",
    "viên bao đường": "round",
    "thuốc cốm": "granule",
    "thuốc bột": "powder",
    "dung dịch": "liquid",
    "hỗn dịch": "liquid",
    "siro": "liquid",
    "nhũ tương": "liquid",
    "thuốc tiêm": "injection",
    "thuốc nhỏ mắt": "eye drops",
    "thuốc nhỏ mũi": "nasal drops",
    "thuốc mỡ": "ointment",
    "kem bôi": "cream",
    "gel bôi": "gel",
    "thuốc đặt": "suppository",
    "thuốc dán": "patch",
}

# Colorants in excipients → color
TADUOC_TO_COLOR = {
    "titan dioxyd": "white",
    "titanium dioxide": "white",
    "titan dioxide": "white",
    "erythrosin": "red",
    "ponceau 4r": "red",
    "allura red": "red",
    "màu đỏ": "red",
    "sắt oxyd đỏ": "red",
    "red iron oxide": "red",
    "ferric oxide red": "red",
    "iron oxide red": "red",
    "iron oxide black": "black",
    "ferrosoferric oxide": "black",
    "sắt oxyd vàng": "yellow",
    "iron oxide yellow": "yellow",
    "yellow iron oxide": "yellow",
    "quinoline yellow": "yellow",
    "sunset yellow": "orange",
    "tartrazine": "yellow",
    "indigotine": "blue",
    "indigo carmine": "blue",
    "brilliant blue": "blue",
    "patent blue": "blue",
    "màu xanh": "blue",
    "chlorophyll": "green",
    "màu nâu": "brown",
    "chocolate": "brown",
    "caramel": "brown",
}


def map_shape(bao_che: str) -> str:
    """Map Vietnamese dosage form to English shape."""
    if not bao_che:
        return ""
    bc = bao_che.lower().strip()
    for vn, en in BAOCE_TO_SHAPE.items():
        if vn in bc:
            return en
    # Fallback patterns
    if "nén" in bc:
        return "round"
    if "nang" in bc:
        return "capsule"
    return ""


def extract_color(ta_duoc: str) -> str:
    """Try to extract color from excipients list."""
    if not ta_duoc:
        return ""
    td = ta_duoc.lower()
    colors_found = []
    for keyword, color in TADUOC_TO_COLOR.items():
        if keyword in td:
            if color not in colors_found:
                colors_found.append(color)
    if len(colors_found) == 1:
        return colors_found[0]
    if len(colors_found) > 1:
        # If white + another color, prefer the other
        non_white = [c for c in colors_found if c != "white"]
        if non_white:
            return non_white[0]
        return "white"
    return ""


def load_vaipe_data() -> dict:
    """Load existing pill_information.csv (color, shape)."""
    vaipe = {}
    if VAIPE_CSV.exists():
        with open(VAIPE_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vaipe[row["Pill"]] = {
                    "color": row["Color"],
                    "shape": row["Shape"],
                }
    print(f"Loaded {len(vaipe)} pills from VAIPE")
    return vaipe


async def fetch_all_drugs(max_pages: int = 0):
    """
    Fetch all drugs from DDI Lab VN API.

    Args:
        max_pages: 0 = fetch all pages
    """
    all_drugs = []
    page = 1

    async with httpx.AsyncClient(timeout=15.0) as client:
        # First request to get total pages
        resp = await client.get(
            f"{DDI_BASE}/drugs/search-detailed",
            params={"q": "", "page": 1, "limit": 50}
        )
        if resp.status_code != 200:
            # Fallback: use paginated drugs endpoint
            resp = await client.get(
                f"{DDI_BASE}/drugs",
                params={"page": 1}
            )
        data = resp.json()
        total_pages = data.get("totalPages", 1)
        if max_pages > 0:
            total_pages = min(total_pages, max_pages)

        print(f"Total pages: {total_pages}")

        # First page results
        drugs = data.get("drugs", [])
        all_drugs.extend(drugs)
        print(f"Page 1/{total_pages}: {len(drugs)} drugs")

        # Remaining pages
        for page in range(2, total_pages + 1):
            try:
                resp = await client.get(
                    f"{DDI_BASE}/drugs",
                    params={"page": page}
                )
                if resp.status_code != 200:
                    print(f"  Page {page}: HTTP {resp.status_code}")
                    continue
                data = resp.json()
                drugs = data.get("drugs", [])
                all_drugs.extend(drugs)
                if page % 50 == 0 or page == total_pages:
                    print(
                        f"Page {page}/{total_pages}: "
                        f"total {len(all_drugs)} drugs"
                    )
                # Rate limiting: be nice
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"  Page {page} error: {e}")
                await asyncio.sleep(1)

    print(f"\nTotal drugs fetched: {len(all_drugs)}")
    return all_drugs


def process_drugs(raw_drugs: list, vaipe: dict) -> dict:
    """Process raw DDI drugs into our format."""
    db = {}

    for d in raw_drugs:
        name = d.get("tenThuoc", "").strip()
        if not name:
            continue

        # Active ingredients
        hoat_chat = []
        for h in d.get("hoatChat", []):
            hc = h.get("tenHoatChat", "").strip()
            nd = h.get("nongDo", "").strip()
            if hc:
                hoat_chat.append(
                    f"{hc} {nd}" if nd else hc)

        bao_che = (d.get("baoChe") or "").strip()
        ta_duoc = (d.get("taDuoc") or "").strip()

        # Map shape from dosage form
        shape = map_shape(bao_che)

        # Try to extract color from excipients
        color = extract_color(ta_duoc)

        # Override with VAIPE data if available
        # (more accurate for known drugs)
        name_norm = name.replace(" ", "-")
        for vaipe_name, vaipe_info in vaipe.items():
            vn = vaipe_name.lower().replace("-", "")
            nn = name_norm.lower().replace("-", "")
            # Check active ingredient match too
            hc_str = " ".join(hoat_chat).lower()
            if (vn == nn
                    or vn in nn
                    or nn in vn
                    or vn in hc_str):
                color = vaipe_info["color"]
                shape = vaipe_info["shape"]
                break

        entry = {
            "name": name,
            "soDangKy": d.get("soDangKy", ""),
            "hoatChat": hoat_chat,
            "baoChe": bao_che,
            "color": color,
            "shape": shape,
            "phanLoai": d.get("phanLoai", ""),
            "dongGoi": d.get("dongGoi", ""),
            "congTySx": d.get("congTySx", ""),
            "nuocSx": d.get("nuocSx", "").strip(),
            "nhomThuoc": d.get("nhomThuoc", ""),
        }

        # Use name as key (deduplicate)
        if name not in db:
            db[name] = entry

    return db


def print_stats(db: dict):
    """Print statistics about the built DB."""
    total = len(db)
    has_color = sum(1 for v in db.values() if v["color"])
    has_shape = sum(1 for v in db.values() if v["shape"])
    has_both = sum(
        1 for v in db.values()
        if v["color"] and v["shape"]
    )

    print(f"\n{'='*50}")
    print(f"Drug Database Statistics")
    print(f"{'='*50}")
    print(f"Total drugs:       {total}")
    print(f"With color:        {has_color} "
          f"({has_color/total*100:.1f}%)")
    print(f"With shape:        {has_shape} "
          f"({has_shape/total*100:.1f}%)")
    print(f"With color+shape:  {has_both} "
          f"({has_both/total*100:.1f}%)")

    # Shape distribution
    shapes = {}
    for v in db.values():
        s = v["shape"] or "(none)"
        shapes[s] = shapes.get(s, 0) + 1
    print(f"\nShape distribution:")
    for s, c in sorted(
        shapes.items(), key=lambda x: -x[1]
    ):
        print(f"  {s:20s} {c:5d}")

    # Color distribution
    colors = {}
    for v in db.values():
        c = v["color"] or "(none)"
        colors[c] = colors.get(c, 0) + 1
    print(f"\nTop 10 colors:")
    for c, n in sorted(
        colors.items(), key=lambda x: -x[1]
    )[:10]:
        print(f"  {c:20s} {n:5d}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Build full drug DB from APIs")
    parser.add_argument(
        "--pages", type=int, default=5,
        help="Max pages to fetch (0=all, default=5 for testing)"
    )
    args = parser.parse_args()

    print("=== Build Full Drug Database ===\n")

    # 1. Load existing VAIPE data
    vaipe = load_vaipe_data()

    # 2. Fetch from DDI Lab VN
    print(f"\nFetching from DDI Lab VN "
          f"(max {args.pages} pages)...")
    t0 = time.time()
    raw_drugs = await fetch_all_drugs(
        max_pages=args.pages)
    print(f"Fetch time: {time.time()-t0:.1f}s")

    # 3. Process and build DB
    print("\nProcessing...")
    db = process_drugs(raw_drugs, vaipe)

    # 4. Stats
    print_stats(db)

    # 5. Save
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to: {OUTPUT}")
    print(f"File size: {OUTPUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    asyncio.run(main())
