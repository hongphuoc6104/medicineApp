"""
core/pipeline.py — Full end-to-end MedicineApp pipeline.

Orchestrates all modules:
    1. YOLO11-seg: detect & crop prescription from photo
    2. PaddleOCR: read text + bbox from cropped image
    3. Zero-PIMA GCN: classify drugname / other
    4. Drug mapper: map OCR text → standard drug names
    5. Pill detector (FRCNN): detect pills in pill image
    6. Zero-PIMA matching: match pill features ↔ drug names

Usage:
    from core.pipeline import MedicinePipeline
    pipe = MedicinePipeline()

    # Phase A: Scan prescription
    result = pipe.scan_prescription("prescription_photo.jpg")
    # → {"medications": [...], "ocr_blocks": [...]}

    # Phase B: Verify pills
    match = pipe.verify_pills("pill_photo.jpg", result["ocr_blocks"])
    # → {"matches": [...]}
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent


class MedicinePipeline:
    """
    Full pipeline: prescription scan → drug extraction → pill verification.

    Lazy loads all models on first use to minimize startup time.
    """

    def __init__(
        self,
        yolo_weights: Optional[str] = None,
        zero_pima_weights: Optional[str] = None,
        device: Optional[str] = None,
    ):
        from core.config import YOLO_WEIGHTS, ZERO_PIMA_WEIGHTS

        self._yolo_path = yolo_weights or str(ROOT / YOLO_WEIGHTS)
        self._zpima_path = zero_pima_weights or str(
            ROOT / ZERO_PIMA_WEIGHTS)
        self._device = device

        # Lazy-loaded modules
        self._detector = None      # YOLO prescription detector
        self._ocr = None           # PaddleOCR engine
        self._matcher = None       # Zero-PIMA GCN + matching
        self._pill_det = None      # Faster R-CNN pill detector
        self._drug_mapper = None   # Fuzzy drug name mapper

        logger.info("MedicinePipeline initialized")

    # ── Lazy loaders ─────────────────────────────────────

    def _get_detector(self):
        if self._detector is None:
            from core.detector import PrescriptionDetector
            self._detector = PrescriptionDetector(self._yolo_path)
            logger.info("YOLO detector loaded")
        return self._detector

    def _get_ocr(self):
        if self._ocr is None:
            from core.ocr.ocr_engine import HybridOcrModule
            device = "gpu" if self._device is None else self._device
            import torch
            if device is None:
                device = "gpu" if torch.cuda.is_available() else "cpu"
            self._ocr = HybridOcrModule(device=device)
            logger.info("HybridOCR (PaddleOCR det + VietOCR rec) loaded")
        return self._ocr

    def _get_matcher(self):
        if self._matcher is None:
            from core.matcher import ZeroPimaMatcher
            self._matcher = ZeroPimaMatcher(
                weights_path=self._zpima_path,
                device=self._device
            )
            logger.info("Zero-PIMA matcher loaded")
        return self._matcher

    def _get_pill_detector(self):
        if self._pill_det is None:
            from core.pill_detector import PillDetector
            self._pill_det = PillDetector(
                weights_path=self._zpima_path,
                device=self._device
            )
            logger.info("Pill detector loaded")
        return self._pill_det

    def _get_drug_mapper(self):
        if self._drug_mapper is None:
            from core.converter.drug_lookup import DrugLookup
            self._drug_mapper = DrugLookup()
            logger.info("Drug mapper loaded")
        return self._drug_mapper

    # ── Phase A: Scan Prescription ───────────────────────

    def scan_prescription(self, image, skip_yolo=False):
        """
        Full prescription scanning pipeline.

        Args:
            image: str path, numpy array (BGR), or PIL Image
            skip_yolo: If True, skip YOLO crop (image is already
                       a cropped prescription)

        Returns:
            dict:
                medications: list of detected drugs with names
                ocr_blocks: raw OCR blocks for Phase B
                gcn_results: GCN classification details
                image_size: (width, height)
        """
        # Load image
        if isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                return {"error": f"Cannot read: {image}"}
        elif hasattr(image, 'shape'):
            img = image
        else:
            img = np.array(image)

        # Step 1: YOLO detect & crop prescription
        if not skip_yolo:
            img = self._crop_prescription(img)
            if img is None:
                return {"error": "No prescription detected in image"}

        h, w = img.shape[:2]

        # Step 2: OCR (Hybrid: PaddleOCR detect + VietOCR recognize)
        ocr_blocks = self._run_ocr(img)
        if not ocr_blocks:
            return {"error": "OCR found no text",
                    "image_size": (w, h)}

        # Step 3: GCN classify drugname/other
        gcn_results = self._classify_blocks(ocr_blocks, w, h)

        # Step 4: Map drug names
        medications = self._extract_medications(gcn_results)

        return {
            "medications": medications,
            "ocr_blocks": gcn_results,
            "image_size": (w, h),
            "stats": {
                "total_blocks": len(ocr_blocks),
                "drugnames": len(medications),
                "others": len(ocr_blocks) - len(medications),
            }
        }

    def _crop_prescription(self, img):
        """Use YOLO to detect and crop prescription area."""
        from core.segmentation import crop_by_mask, crop_by_bbox
        detector = self._get_detector()
        results = detector.predict(img)
        if not results or len(results[0].boxes) == 0:
            return None

        cropped = crop_by_mask(img, results[0])
        if cropped is None:
            cropped = crop_by_bbox(img, results[0])
        return cropped

    def _run_ocr(self, img):
        """Run Hybrid OCR and return normalized blocks."""
        ocr = self._get_ocr()
        result = ocr.extract(img)
        if not result.text_blocks:
            return []

        blocks = []
        for tb in result.text_blocks:
            # Convert polygon bbox → [xmin, ymin, xmax, ymax]
            bbox = tb.bbox
            if isinstance(bbox, list) and len(bbox) == 4:
                if isinstance(bbox[0], list):
                    # 4-point polygon
                    xs = [p[0] for p in bbox]
                    ys = [p[1] for p in bbox]
                    bbox = [int(min(xs)), int(min(ys)),
                            int(max(xs)), int(max(ys))]
            blocks.append({
                "text": tb.text,
                "bbox": bbox,
                "confidence": round(tb.confidence, 4),
            })
        return blocks

    def _classify_blocks(self, ocr_blocks, img_w, img_h):
        """Use GCN to classify each block as drugname/other."""
        matcher = self._get_matcher()
        results = matcher.classify_prescription(
            ocr_blocks, img_w=img_w, img_h=img_h)
        return results

    def _extract_medications(self, gcn_results):
        """Extract drugname blocks and map to standard names."""
        mapper = self._get_drug_mapper()
        medications = []

        for block in gcn_results:
            if block.get("label") == "drugname":
                text = block["text"]
                match = mapper.lookup(text)
                medications.append({
                    "ocr_text": text,
                    "drug_name": match.get("name", text)
                        if match else text,
                    "match_score": match.get("score", 0)
                        if match else 0,
                    "confidence": block.get("confidence", 0),
                    "bbox": block.get("bbox"),
                })

        return medications

    # ── Phase B: Verify Pills ────────────────────────────

    def verify_pills(self, pill_image, prescription_blocks,
                     img_w=1000, img_h=1000):
        """
        Verify pills match the prescription.

        Args:
            pill_image: str path or numpy array (BGR)
            prescription_blocks: ocr_blocks from scan_prescription()
            img_w, img_h: prescription image dimensions

        Returns:
            dict:
                matches: list of {pill_idx, drug_name, confidence}
                detections: raw pill detections
                n_pills: number of pills detected
        """
        # Load pill image
        if isinstance(pill_image, str):
            pimg = cv2.imread(pill_image)
        else:
            pimg = pill_image

        if pimg is None:
            return {"error": "Cannot read pill image"}

        # Detect pills
        pill_det = self._get_pill_detector()
        detections = pill_det.detect(pimg)

        if not detections:
            return {
                "matches": [],
                "detections": [],
                "n_pills": 0,
                "warning": "No pills detected"
            }

        # Match pills to prescription drugs
        matcher = self._get_matcher()
        matches = matcher.verify_pills(
            pimg, prescription_blocks,
            img_w=img_w, img_h=img_h
        )

        return {
            "matches": matches,
            "detections": detections,
            "n_pills": len(detections),
        }

    # ── Utilities ────────────────────────────────────────

    def get_model_info(self):
        """Return info about loaded models."""
        info = {
            "yolo_weights": self._yolo_path,
            "zero_pima_weights": self._zpima_path,
            "yolo_loaded": self._detector is not None,
            "ocr_loaded": self._ocr is not None,
            "matcher_loaded": self._matcher is not None,
            "pill_detector_loaded": self._pill_det is not None,
        }
        if self._matcher is not None:
            info["checkpoint"] = self._matcher.checkpoint_info()
        return info
