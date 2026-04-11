"""
drug_lookup.py — Drug name lookup using Vietnamese drug database (9,284 drugs).

Priority: Local fuzzy match only (no API calls).
Database: data/drug_db_vn_full.json (9,284 thuốc từ ddi.lab.io.vn)
Fallback:  data/drug_db_vn.csv        (316 thuốc cũ)

Usage:
    from core.phase_a.s6_drug_search.drug_lookup import DrugLookup
    lu = DrugLookup()
    result = lu.lookup("Celecoxib 200mg")
    # {'name': 'Celecoxib', 'generic': 'celecoxib', 'score': 0.97, ...}
"""

import csv
import json
import logging
import os
import re
from typing import Optional

from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

MIN_SCORE = 65   # Minimum fuzzy score to accept match

# Paths relative to project root (3 levels up from this file)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
_DEFAULT_JSON_DB = os.path.join(_ROOT, "data", "drug_db_vn_full.json")
_DEFAULT_CSV_DB  = os.path.join(_ROOT, "data", "drug_db_vn.csv")


class DrugLookup:
    """
    Local Vietnamese drug name lookup via fuzzy matching.
    Ưu tiên drug_db_vn_full.json (9,284 thuốc), fallback sang CSV cũ.
    """

    def __init__(self, db_path: Optional[str] = None):
        self._entries: list = []
        self._search_keys: list = []
        # Thử JSON đầy đủ trước, fallback CSV
        json_path = db_path or _DEFAULT_JSON_DB
        if os.path.exists(json_path) and json_path.endswith(".json"):
            self._load_json(json_path)
        else:
            self._load_csv(_DEFAULT_CSV_DB)

    # ── Loaders ──────────────────────────────────────────────────────────────

    def _load_json(self, path: str) -> None:
        """Load drug_db_vn_full.json — 9,284 thuốc VN."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"DrugLookup: lỗi đọc JSON {path}: {e}")
            return

        drugs = data.get("drugs", []) if isinstance(data, dict) else data
        for drug in drugs:
            ten_thuoc = drug.get("tenThuoc", "").strip()
            if not ten_thuoc:
                continue

            hoat_chats = drug.get("hoatChat", [])
            if isinstance(hoat_chats, list):
                generic_names = [
                    hc.get("tenHoatChat", "") for hc in hoat_chats
                    if isinstance(hc, dict) and hc.get("tenHoatChat")
                ]
                nong_do = ", ".join(
                    hc.get("nongDo", "") for hc in hoat_chats
                    if isinstance(hc, dict) and hc.get("nongDo")
                )
            else:
                generic_names = []
                nong_do = ""

            entry = {
                "brand_name":  ten_thuoc,
                "generic_name": ", ".join(generic_names),
                "so_dang_ky":  drug.get("soDangKy", ""),
                "nong_do":     nong_do,
                "source":      "drug_db_vn_full",
            }

            self._entries.append(entry)
            self._search_keys.append(ten_thuoc.lower())

            for g in generic_names:
                g_lo = g.strip().lower()
                if g_lo and g_lo != ten_thuoc.lower():
                    self._entries.append(entry)
                    self._search_keys.append(g_lo)

        logger.info(
            f"DrugLookup (JSON): {len(self._entries)} search keys "
            f"từ {len(drugs)} thuốc"
        )

    def _load_csv(self, path: str) -> None:
        """Fallback: load drug_db_vn.csv."""
        if not os.path.exists(path):
            logger.warning(f"Drug DB không tìm thấy: {path}")
            return
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                brand   = row.get("brand_name", "").strip()
                generic = row.get("generic_name", "").strip()
                if not brand:
                    continue
                row["source"] = "drug_db_vn_csv"
                row["so_dang_ky"] = ""
                row["nong_do"] = ""
                self._entries.append(row)
                self._search_keys.append(brand.lower())
                if generic and generic.lower() != brand.lower():
                    self._entries.append(row)
                    self._search_keys.append(generic.lower())
        logger.info(
            f"DrugLookup (CSV fallback): {len(self._entries)} search keys"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _clean(text: str) -> str:
        """Làm sạch OCR text trước khi fuzzy search."""
        t = re.sub(
            r"\b\d+\s*(mg|ml|tab|cap|iu|mcg|g|viên|ống|lọ)?\b",
            " ", text, flags=re.IGNORECASE,
        )
        t = re.sub(r"^\d{1,3}\s+", "", t)
        t = re.sub(r"\s+\d{1,3}$", "", t)
        return " ".join(t.split()).strip().lower()

    @staticmethod
    def _has_root_overlap(query: str, candidate: str) -> bool:
        """Yêu cầu ít nhất 1 token có nghĩa chung."""
        stop = {
            "", "mg", "ml", "mcg", "g", "iu", "tab", "cap",
            "viên", "ống", "lọ", "chai", "gói", "sủi",
            "thuốc", "và", "the", "for",
        }
        q_words = {w for w in re.split(r"\W+", query.lower()) if w not in stop and len(w) >= 3}
        c_words = {w for w in re.split(r"\W+", candidate.lower()) if w not in stop and len(w) >= 3}
        return bool(q_words & c_words)

    @staticmethod
    def _extract_strength_tokens(text: str) -> set[str]:
        matches = re.findall(
            r"(\d+(?:[.,]\d+)?)\s*(mg|ml|mcg|g|iu)",
            text.lower(),
        )
        return {f"{value.replace(',', '.')} {unit}" for value, unit in matches}

    @classmethod
    def _strength_compatible(
        cls,
        query_text: str,
        entry: dict,
        match_key: str,
    ) -> bool:
        query_strengths = cls._extract_strength_tokens(query_text)
        if not query_strengths:
            return True

        candidate_text = " ".join(
            filter(
                None,
                [
                    entry.get("brand_name", ""),
                    entry.get("generic_name", ""),
                    entry.get("nong_do", ""),
                    match_key,
                ],
            )
        )
        candidate_strengths = cls._extract_strength_tokens(candidate_text)
        if not candidate_strengths:
            return True
        return bool(query_strengths & candidate_strengths)

    # ── Public API ────────────────────────────────────────────────────────────

    def lookup(self, text: str) -> dict:
        """Fuzzy match tên thuốc OCR → tên chuẩn trong DB."""
        if not self._search_keys:
            return self._empty(text)

        query_clean  = self._clean(text)
        query_raw    = text.strip().lower()
        paren_m      = re.search(r"\(([^)]+)\)", text)
        query_paren  = paren_m.group(1).strip().lower() if paren_m else ""
        no_paren     = re.sub(r"\([^)]*\)", " ", text)
        query_no_par = self._clean(no_paren)

        best_result = None
        variant_priority = {
            "query_clean": 1,
            "query_raw": 0,
            "query_paren": 3,
            "query_no_par": 2,
        }

        for variant_name, query in [
            ("query_clean", query_clean),
            ("query_raw", query_raw),
            ("query_paren", query_paren),
            ("query_no_par", query_no_par),
        ]:
            if not query or len(query) < 3:
                continue
            results = process.extract(
                query,
                self._search_keys,
                scorer=fuzz.token_sort_ratio,
                limit=5,
            )
            for match_key, score, idx in results:
                if score < MIN_SCORE:
                    continue
                if not self._has_root_overlap(query_clean or query_raw, match_key):
                    continue
                entry = self._entries[idx]
                strength_ok = self._strength_compatible(text, entry, match_key)
                candidate_rank = (
                    1 if strength_ok else 0,
                    variant_priority[variant_name],
                    score,
                )
                if best_result is None or candidate_rank > best_result[0]:
                    best_result = (candidate_rank, match_key, score, idx)

        if not best_result:
            return self._empty(text)

        _, match_key, score, idx = best_result

        entry = self._entries[idx]
        return {
            "original":    text,
            "name":        entry.get("brand_name", "").strip(),
            "generic":     entry.get("generic_name", "").strip(),
            "score":       round(score / 100.0, 3),
            "so_dang_ky":  entry.get("so_dang_ky", ""),
            "nong_do":     entry.get("nong_do", ""),
            "source":      entry.get("source", ""),
        }

    def lookup_batch(self, texts: list) -> list:
        return [self.lookup(t) for t in texts]

    @staticmethod
    def _empty(original: str) -> dict:
        return {
            "original":   original,
            "name":       None,
            "generic":    None,
            "score":      0.0,
            "so_dang_ky": "",
            "nong_do":    "",
            "source":     None,
        }

    @property
    def db_size(self) -> int:
        """Số lượng thuốc unique trong DB."""
        return len(set(e.get("brand_name", "") for e in self._entries))
