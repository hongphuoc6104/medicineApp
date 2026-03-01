# MIN_TEXT_LEN: skip OCR text shorter than this (catches STT numbers, fragments)
MIN_TEXT_LEN = 4

"""
drug_mapper.py — Fuzzy-match OCR drug text → Zero-PIMA standard drug names.

Requires: rapidfuzz  (pip install rapidfuzz)

Usage:
    from core.converter.drug_mapper import DrugMapper
    mapper = DrugMapper()
    result = mapper.match("Paracetamol 500mg")
    # → {"matched_label": "Paracetamol-500mg", "score": 96.5, "status": "matched"}
"""

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "Zero-PIMA"))

from rapidfuzz import fuzz, process
import config as PIMA_CFG

# ── helpers ────────────────────────────────────────────────────────────────────

# Pure dosage/unit words that MUST NOT be the sole basis of a match.
_DOSAGE_NOISE = {
    "mg", "ml", "mcg", "g", "ug",
    "10", "20", "40", "50", "80", "100", "200", "250",
    "300", "400", "500", "750", "800", "1000", "1500",
    "tablet", "capsule", "vien", "ong", "goi", "chai",
}


def _tokenize(text: str) -> set:
    """Lower-case, split on non-alphanumeric, return token set."""
    return set(re.split(r"[^a-zA-Z0-9]+", text.lower())) - {"", " "}


def _significant_tokens(text: str) -> set:
    """Tokens that are NOT dosage noise."""
    return _tokenize(text) - _DOSAGE_NOISE


def _has_root_word_overlap(ocr_text: str, label_display: str) -> bool:
    """
    Guard: require ≥1 significant word from OCR to appear in the candidate label.
    Prevents "40mg" alone matching an unrelated drug that also carries "40mg".
    """
    return bool(_significant_tokens(ocr_text) & _tokenize(label_display))


# ── main class ─────────────────────────────────────────────────────────────────

class DrugMapper:
    """
    Maps raw OCR drug-name strings to canonical Zero-PIMA ALL_PILL_LABELS keys.

    Matching pipeline:
        1. token_sort_ratio  — handles reordered or partial OCR words
        2. partial_ratio     — handles substring OCR transcriptions
        3. Accept if score >= threshold  AND  root-word guard passes
        4. Otherwise → "unmatched" (user should verify manually)
    """

    def __init__(self, threshold: float = 80.0):
        """
        Args:
            threshold: Minimum fuzzy score (0-100).
                       80 balances OCR typos vs false positives.
                       Higher → fewer matches but more precise.
        """
        self.threshold = threshold

        # All canonical labels from Zero-PIMA config, e.g. "Paracetamol-500mg"
        self.drug_labels: list = list(PIMA_CFG.ALL_PILL_LABELS.keys())

        # Build display form (dashes → spaces, lower) → canonical mapping
        # "Paracetamol-500mg" → key "paracetamol 500mg"
        self._display_to_canonical: dict = {
            lbl.replace("-", " ").lower(): lbl
            for lbl in self.drug_labels
        }
        self._display_list: list = list(self._display_to_canonical.keys())

    # ── public API ─────────────────────────────────────────────────────────────

    def match(self, ocr_text: str) -> dict:
        """
        Match a single OCR drug string to a canonical label.

        Returns dict:
            ocr_text      : original input string
            matched_label : canonical label (str) or None
            score         : fuzzy score 0-100
            status        : "matched" | "unmatched"
        """
        if not ocr_text or not ocr_text.strip():
            return {"ocr_text": ocr_text, "matched_label": None,
                    "score": 0.0, "status": "unmatched"}

        # Guard: skip very short strings (STT numbers, fragments like '12', '40mg')
        if len(ocr_text.strip()) < MIN_TEXT_LEN:
            return {"ocr_text": ocr_text, "matched_label": None,
                    "score": 0.0, "status": "unmatched"}

        query = ocr_text.strip().lower()

        # Primary scorer: token_sort_ratio (handles reordered OCR words best)
        r1 = process.extractOne(query, self._display_list, scorer=fuzz.token_sort_ratio)
        # Secondary: partial_ratio — only used when token_sort also shows some agreement
        r2 = process.extractOne(query, self._display_list, scorer=fuzz.partial_ratio)

        best_display, best_score = None, 0.0
        # Accept partial_ratio winner only if token_sort for same candidate is >= 70
        for res in [r1, r2]:
            if res and res[1] > best_score:
                if res is r2:  # secondary (partial)
                    # Verify token_sort also agrees on this candidate
                    ts_score = fuzz.token_sort_ratio(query, res[0])
                    if ts_score < 70:
                        continue
                best_score, best_display = res[1], res[0]

        accepted = (
            best_score >= self.threshold
            and best_display is not None
            and _has_root_word_overlap(query, best_display)
        )

        if accepted:
            canonical = self._display_to_canonical[best_display]
            return {"ocr_text": ocr_text, "matched_label": canonical,
                    "score": round(best_score, 1), "status": "matched"}

        return {"ocr_text": ocr_text, "matched_label": None,
                "score": round(best_score, 1), "status": "unmatched"}

    def match_batch(self, texts: list) -> list:
        """Match a list of OCR texts, return list of result dicts."""
        return [self.match(t) for t in texts]

    def get_all_labels(self) -> list:
        """All canonical label names from Zero-PIMA config."""
        return self.drug_labels.copy()


# ── self-test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mapper = DrugMapper(threshold=75)

    # (ocr_text, expected_label or None)
    tests = [
        ("Paracetamol 500mg",            "Paracetamol-500mg"),
        ("Paracetamol 500 mg",           "Paracetamol-500mg"),
        ("Ginkgo Biloba (Tanakan 40mg)", None),            # not in 107 labels
        ("Aspirin 81mg",                 "Aspirin-81mg"),
        ("Vitamin C 500mg",              "Vitamin-C-500mg"),
        ("Omeprazole",                   "Omeprazole"),
        ("Glucophage 850mg",             "Glucophage-850mg"),
        ("completely random text",       None),            # noise
        ("Amlodipine 5mg",               "Amlodipine-5mg"),
        ("Calcium D3 Corbiere",          None),            # not in labels
        ("Atorvastatin 20mg",            "Atorvastatin-20mg"),
        ("Loratadine 10mg",              "Loratadine-10mg"),
        ("Diclofenac 50mg",              "Diclofenac-50mg"),
        ("Vitamin 3B",                   "Vitamin-3B"),
    ]

    print("=" * 68)
    print(f"DrugMapper  threshold={mapper.threshold}  labels={len(mapper.drug_labels)}")
    print("=" * 68)
    passed = 0
    for text, expected in tests:
        r = mapper.match(text)
        ok = r["matched_label"] == expected
        passed += ok
        icon = "✅" if ok else "❌"
        print(f"{icon} [{r['score']:5.1f}] {text!r}")
        if not ok:
            print(f"         got={r['matched_label']}  expected={expected}")
    print("=" * 68)
    print(f"Accuracy: {passed}/{len(tests)}")
