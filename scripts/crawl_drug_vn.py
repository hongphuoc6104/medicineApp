#!/usr/bin/env python3
"""
Crawl toàn bộ thuốc VN từ ddi.lab.io.vn API.

Tính năng:
- Crawl /api/drugs/search-detailed?q=&page=X&limit=50
- Anti-bot: Random delay 1.5-3.5s + User-Agent rotation
- Retry: 3 lần với exponential backoff
- HTTP 429: chờ 30s
- Checkpoint: lưu mỗi 50 trang (resume từ checkpoint)
- Deduplicate: theo soDangKy
- Output: data/drug_db_vn_full.json

Usage:
    python scripts/crawl_drug_vn.py                # Crawl mới
    python scripts/crawl_drug_vn.py --resume       # Resume từ checkpoint
    python scripts/crawl_drug_vn.py --test          # Test 2 trang
"""
import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────
API_BASE = "https://ddi.lab.io.vn/api/drugs/search-detailed"
PAGE_LIMIT = 50  # thuốc/trang (tối ưu tốc độ)
MAX_RETRIES = 3
CHECKPOINT_INTERVAL = 50  # lưu checkpoint mỗi N trang

OUTPUT_FILE = ROOT / "data" / "drug_db_vn_full.json"
CHECKPOINT_FILE = ROOT / "data" / "crawl_checkpoint.json"

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) "
    "Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) "
    "Gecko/20100101 Firefox/131.0",
]


def _random_headers():
    """Tạo headers với User-Agent ngẫu nhiên."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        "Referer": "https://ddi.lab.io.vn/drugs",
    }


def fetch_page(page: int, limit: int = PAGE_LIMIT) -> dict:
    """
    Fetch 1 trang từ API. Có retry + backoff.

    Returns: dict {drugs: [...], totalPages, totalDrugs, currentPage}
    Raises: Exception nếu hết retry.
    """
    url = f"{API_BASE}?q=&page={page}&limit={limit}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url,
                headers=_random_headers(),
                timeout=15,
            )

            if resp.status_code == 429:
                wait = 30 + random.uniform(0, 10)
                logger.warning(
                    f"Rate limited (429). Chờ {wait:.0f}s..."
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()

            if "drugs" not in data:
                raise ValueError(
                    f"Response thiếu key 'drugs': "
                    f"{list(data.keys())}"
                )

            return data

        except requests.exceptions.Timeout:
            wait = 2 ** attempt + random.uniform(0, 1)
            logger.warning(
                f"Timeout page {page}, "
                f"retry {attempt}/{MAX_RETRIES} "
                f"(wait {wait:.1f}s)"
            )
            time.sleep(wait)

        except requests.exceptions.RequestException as e:
            wait = 2 ** attempt + random.uniform(0, 1)
            logger.warning(
                f"Error page {page}: {e}, "
                f"retry {attempt}/{MAX_RETRIES}"
            )
            time.sleep(wait)

    raise Exception(f"Failed after {MAX_RETRIES} retries: page {page}")


def clean_drug(raw: dict) -> dict:
    """Lọc và chuẩn hóa 1 record thuốc."""
    return {
        "soDangKy": (raw.get("soDangKy") or "").strip(),
        "tenThuoc": (raw.get("tenThuoc") or "").strip(),
        "hoatChat": raw.get("hoatChat", []),
        "phanLoai": (raw.get("phanLoai") or "").strip(),
        "baoChe": (raw.get("baoChe") or "").strip(),
        "dongGoi": (raw.get("dongGoi") or "").strip(),
        "congTySx": (raw.get("congTySx") or "").strip(),
        "nuocSx": (raw.get("nuocSx") or "").strip(),
        "diaChiSx": (raw.get("diaChiSx") or "").strip(),
        "congTyDk": (raw.get("congTyDk") or "").strip(),
        "nuocDk": (raw.get("nuocDk") or "").strip(),
        "nhomThuoc": (raw.get("nhomThuoc") or "").strip(),
        "taDuoc": (raw.get("taDuoc") or "").strip(),
        "tieuChuan": (raw.get("tieuChuan") or "").strip(),
        "tuoiTho": (raw.get("tuoiTho") or "").strip(),
        "pheDuyet": (raw.get("pheDuyet") or "").strip(),
    }


def save_checkpoint(page: int, drugs: list):
    """Lưu checkpoint để resume."""
    data = {
        "last_page": page,
        "drug_count": len(drugs),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Lưu drugs tạm
    save_drugs(drugs, OUTPUT_FILE)
    logger.info(
        f"Checkpoint: page={page}, drugs={len(drugs)}"
    )


def load_checkpoint() -> tuple[int, list]:
    """Load checkpoint để resume. Returns (start_page, drugs)."""
    if not CHECKPOINT_FILE.exists():
        return 1, []
    if not OUTPUT_FILE.exists():
        return 1, []

    with open(CHECKPOINT_FILE, encoding="utf-8") as f:
        cp = json.load(f)

    with open(OUTPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)
        drugs = data.get("drugs", [])

    start_page = cp.get("last_page", 0) + 1
    logger.info(
        f"Resuming from page {start_page}, "
        f"{len(drugs)} drugs loaded"
    )
    return start_page, drugs


def save_drugs(drugs: list, path: Path):
    """Lưu danh sách thuốc ra JSON."""
    # Deduplicate by soDangKy
    seen = set()
    unique = []
    for d in drugs:
        key = d.get("soDangKy", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(d)
        elif not key:
            unique.append(d)  # giữ lại nếu không có soDangKy

    output = {
        "totalDrugs": len(unique),
        "crawledAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "ddi.lab.io.vn",
        "drugs": unique,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return len(unique)


def crawl(
    start_page: int = 1,
    existing_drugs: list = None,
    max_pages: int = None,
):
    """
    Crawl toàn bộ thuốc VN.

    Args:
        start_page: Trang bắt đầu (1-indexed)
        existing_drugs: Danh sách drugs đã có (resume)
        max_pages: Giới hạn số trang (None = hết)
    """
    drugs = list(existing_drugs or [])

    # Fetch page 1 để biết totalPages
    logger.info("Fetching page 1 to check total...")
    first = fetch_page(1, limit=PAGE_LIMIT)
    total_pages = first.get("totalPages", 0)
    total_drugs = first.get("totalDrugs", 0)

    if max_pages:
        total_pages = min(total_pages, max_pages)

    logger.info(
        f"API: {total_drugs} thuốc, {total_pages} trang "
        f"(limit={PAGE_LIMIT})"
    )

    if start_page == 1:
        # Process page 1
        for raw in first.get("drugs", []):
            cleaned = clean_drug(raw)
            if cleaned["tenThuoc"]:
                drugs.append(cleaned)
        start_page = 2

    t_start = time.time()
    errors = []

    for page in range(start_page, total_pages + 1):
        try:
            data = fetch_page(page)
            page_drugs = data.get("drugs", [])

            added = 0
            for raw in page_drugs:
                cleaned = clean_drug(raw)
                if cleaned["tenThuoc"]:
                    drugs.append(cleaned)
                    added += 1
                else:
                    logger.debug(
                        f"Skip empty drug on page {page}"
                    )

            elapsed = time.time() - t_start
            rate = page / max(elapsed, 1) * 60
            logger.info(
                f"[{page}/{total_pages}] "
                f"+{added} drugs "
                f"(total: {len(drugs)}) "
                f"[{rate:.0f} pages/min]"
            )

            # Checkpoint
            if page % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(page, drugs)

            # Random delay (anti-bot)
            delay = random.uniform(1.0, 2.5)
            time.sleep(delay)

        except Exception as e:
            logger.error(f"Page {page} failed: {e}")
            errors.append({"page": page, "error": str(e)})
            # Save checkpoint ngay khi lỗi
            save_checkpoint(page - 1, drugs)
            # Chờ lâu hơn trước khi tiếp tục
            time.sleep(10)
            continue

    # Final save
    unique_count = save_drugs(drugs, OUTPUT_FILE)

    # Cleanup checkpoint
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    # Summary
    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print("CRAWL HOÀN THÀNH")
    print(f"{'='*60}")
    print(f"Tổng thuốc (unique): {unique_count}")
    print(f"Tổng trang:          {total_pages}")
    print(f"Lỗi:                 {len(errors)}")
    print(f"Thời gian:           {elapsed/60:.1f} phút")
    print(f"Output:              {OUTPUT_FILE}")
    if errors:
        print(f"Pages lỗi:           {[e['page'] for e in errors]}")

    return unique_count


def main():
    parser = argparse.ArgumentParser(
        description="Crawl thuốc VN từ ddi.lab.io.vn"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume từ checkpoint",
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Test chỉ 2 trang",
    )
    parser.add_argument(
        "--pages", type=int, default=None,
        help="Giới hạn số trang crawl",
    )
    args = parser.parse_args()

    if args.test:
        crawl(max_pages=2)
    elif args.resume:
        start, drugs = load_checkpoint()
        crawl(start_page=start, existing_drugs=drugs)
    else:
        crawl(max_pages=args.pages)


if __name__ == "__main__":
    main()
