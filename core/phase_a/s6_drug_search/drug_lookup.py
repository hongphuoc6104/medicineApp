"""
drug_lookup.py — Drug name lookup using local Vietnamese DB.

Priority: Local fuzzy match only (no API calls).
Database: data/drug_db_vn.csv (190+ thuốc phổ biến VN).

Usage:
    from core.converter.drug_lookup import DrugLookup
    lu = DrugLookup()
    result = lu.lookup("Tanakan 40mg")
    # {'name': 'tanakan', 'generic': 'ginkgo biloba extract',
    #  'score': 0.95, 'category': 'tuần hoàn não'}
"""

import csv
import logging
import os
import re
from typing import Optional

from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

MIN_SCORE = 65   # Minimum fuzzy score to accept match

# Default DB path (project_root/data/drug_db_vn.csv)
# __file__ is core/phase_a/s6_drug_search/drug_lookup.py
# → 3 levels up = project root
_DEFAULT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data", "drug_db_vn.csv",
)


class DrugLookup:
    """Local Vietnamese drug name lookup via fuzzy matching."""

    def __init__(self, db_path: Optional[str] = None):
        self._entries: list[dict] = []
        self._search_keys: list[str] = []
        self._load(db_path or _DEFAULT_DB)

    def _load(self, path: str) -> None:
        if not os.path.exists(path):
            logger.warning(f"Drug DB not found: {path}")
            return
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                brand = row.get("brand_name", "").strip().lower()
                generic = row.get("generic_name", "").strip().lower()
                self._entries.append(row)
                # Search against both brand and generic name
                self._search_keys.append(brand)
                if generic and generic != brand:
                    self._entries.append(row)
                    self._search_keys.append(generic)
        logger.info(
            f"DrugLookup: {len(self._entries)} search keys "
            f"from {path}"
        )

    @staticmethod
    def _clean(text: str) -> str:
        """Extract drug name from OCR text."""
        t = text
        # Remove standalone numbers and units (keep brand names)
        t = re.sub(
            r"\b\d+\s*(mg|ml|tab|cap|iu|mcg|g|viên|ống|lọ)?\b",
            " ", t, flags=re.IGNORECASE,
        )
        # Remove STT patterns like "11" at start/end
        t = re.sub(r"^\d{1,3}\s+", "", t)
        t = re.sub(r"\s+\d{1,3}$", "", t)
        return " ".join(t.split()).strip().lower()

    def lookup(self, text: str) -> dict:
        """
        Lookup drug name from OCR text.

        Uses dual-match: tries both raw and cleaned text,
        returns the best score.
        """
        if not self._search_keys:
            return self._empty(text)

        # Strategy 1: clean text (parens kept)
        query_clean = self._clean(text)
        # Strategy 2: just lowercase the raw text
        query_raw = text.strip().lower()
        # Strategy 3: extract content in complete parentheses
        paren_match = re.search(r"\(([^)]+)\)", text)
        query_paren = paren_match.group(1).strip().lower() \
            if paren_match else ""
        # Strategy 4: clean text with parens REMOVED
        no_paren = re.sub(r"\([^)]*\)", " ", text)
        query_no_paren = self._clean(no_paren)
        # Strategy 5: partial open-paren (e.g., "Ginkgo Biloba (Tanakan")
        # EasyOCR sometimes splits the closing ')' into a separate block
        partial_match = re.search(r"\(([^)]{3,})\s*$", text)
        query_partial = partial_match.group(1).strip().lower() \
            if partial_match else ""

        best_score = 0
        best_result = None

        candidates = [
            query_clean, query_raw,
            query_paren, query_no_paren,
            query_partial,
        ]
        for query in candidates:
            if not query or len(query) < 3:
                continue
            result = process.extractOne(
                query,
                self._search_keys,
                scorer=fuzz.token_sort_ratio,
            )
            if result and result[1] > best_score:
                best_score = result[1]
                best_result = result

        if not best_result or best_score < MIN_SCORE:
            return self._empty(text)

        match_key, score, idx = best_result
        entry = self._entries[idx]
        return {
            "original": text,
            "name": entry.get("brand_name", "").strip(),
            "generic": entry.get("generic_name", "").strip(),
            "score": round(score / 100.0, 3),
            "category": entry.get("category", ""),
            "source": "local_vn",
        }

    def lookup_batch(self, texts: list[str]) -> list[dict]:
        return [self.lookup(t) for t in texts]

    @staticmethod
    def _empty(original: str) -> dict:
        return {
            "original": original,
            "name": None,
            "generic": None,
            "score": 0.0,
            "category": None,
            "source": None,
        }
