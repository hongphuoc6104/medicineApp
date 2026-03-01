"""
converter/ — OCR output → Zero-PIMA format bridge.

Modules:
    ocr_to_pima  : Convert PaddleOCR JSON → Zero-PIMA prescription JSON
    drug_mapper  : Fuzzy-match OCR drug text → ALL_PILL_LABELS standard names
"""

from .ocr_to_pima import OcrToPimaConverter
from .drug_mapper import DrugMapper

__all__ = ["OcrToPimaConverter", "DrugMapper"]
