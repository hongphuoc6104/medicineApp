"""
core/pipeline.py — Full end-to-end MedicineApp pipeline.

Orchestrates all modules:
    Phase A: prescription scan → drug extraction
    Phase B: pill detection → prescription matching

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
        self._detector = None
        self._ocr = None
        self._classifier = None
        self._pill_det = None
        self._drug_mapper = None
        self._matcher = None

        logger.info("MedicinePipeline initialized")

    # ── Lazy loaders ─────────────────────────────────────

    def _get_detector(self):
        if self._detector is None:
            from core.phase_a.s1_detect.detector import (
                PrescriptionDetector,
            )
            self._detector = PrescriptionDetector(self._yolo_path)
            logger.info("YOLO detector loaded")
        return self._detector

    def _get_ocr(self):
        if self._ocr is None:
            from core.phase_a.s3_ocr.ocr_engine import HybridOcrModule
            import torch
            # Ưu tiên device được truyền vào, fallback theo CUDA
            if self._device is not None:
                device = self._device
            else:
                device = (
                    "gpu" if torch.cuda.is_available() else "cpu"
                )
            self._ocr = HybridOcrModule(device=device)
            logger.info("HybridOCR loaded")
        return self._ocr

    def _get_classifier(self):
        if self._classifier is None:
            from core.phase_a.s5_classify.ner_extractor import (
                NerExtractor,
            )
            self._classifier = NerExtractor()
            logger.info("PhoBERT NER extractor loaded")
        return self._classifier

    def _get_pill_detector(self):
        if self._pill_det is None:
            from core.phase_b.s1_pill_detect.pill_detector import (
                PillDetector,
            )
            self._pill_det = PillDetector(
                weights_path=self._zpima_path,
                device=self._device,
            )
            logger.info("Pill detector loaded")
        return self._pill_det

    def _get_drug_mapper(self):
        if self._drug_mapper is None:
            from core.phase_a.s6_drug_search.drug_lookup import (
                DrugLookup,
            )
            self._drug_mapper = DrugLookup()
            logger.info("Drug mapper loaded")
        return self._drug_mapper

    def _get_matcher(self):
        if self._matcher is None:
            from core.phase_b.s2_match.gcn_matcher import GcnMatcher
            self._matcher = GcnMatcher()
            logger.info("GCN matcher loaded")
        return self._matcher

    # ── Phase A: Scan Prescription ───────────────────────

    def scan_prescription(self, image, skip_yolo=False):
        """
        Full prescription scanning pipeline.

        Args:
            image: str path, numpy array (BGR), or PIL Image
            skip_yolo: If True, skip YOLO crop

        Returns:
            dict: medications, ocr_blocks, image_size, stats
        """
        if isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                return {"error": f"Cannot read: {image}"}
        elif hasattr(image, 'shape'):
            img = image
        else:
            img = np.array(image)

        # Step 1: YOLO detect & crop (VĐ2: fallback to full image)
        if not skip_yolo:
            try:
                cropped = self._crop_prescription(img)
                if cropped is not None:
                    img = cropped
                    logger.info("YOLO crop successful")
                else:
                    logger.warning(
                        "YOLO detection failed, using full image as fallback"
                    )
            except Exception as e:
                logger.error(
                    f"YOLO detection error: {e}, using full image"
                )

        # Step 1.5: Preprocess — deskew & orientation (VĐ3)
        try:
            from core.phase_a.s2_preprocess.orientation import (
                preprocess_image,
            )
            img, prep_info = preprocess_image(img, stem="api")
            logger.info(f"Preprocess: {prep_info}")
        except Exception as e:
            logger.warning(
                f"Preprocess failed: {e}, continuing with original image"
            )

        h, w = img.shape[:2]

        # Step 2: OCR
        ocr_blocks = self._run_ocr(img)
        if not ocr_blocks:
            return {"error": "OCR found no text",
                    "image_size": (w, h)}

        # Step 3: NER classify
        ner_results = self._classify_blocks(ocr_blocks)

        # Step 4: Map drug names
        medications = self._extract_medications(ner_results)

        return {
            "medications": medications,
            "ocr_blocks": ner_results,
            "image_size": (w, h),
            "stats": {
                "total_blocks": len(ocr_blocks),
                "drugnames": len(medications),
                "others": len(ocr_blocks) - len(medications),
            },
        }

    def _crop_prescription(self, img):
        """Use YOLO to detect and crop prescription area."""
        from core.phase_a.s1_detect.segmentation import (
            crop_by_mask, crop_by_bbox,
        )
        detector = self._get_detector()
        results = detector.predict(img)
        if not results or len(results[0].boxes) == 0:
            return None

        r0 = results[0]

        # crop_by_mask returns (image, (x1, y1)) tuple — unpack it
        mask_result, _ = crop_by_mask(img, r0)
        if mask_result is not None and mask_result.size > 0:
            return mask_result

        # Fallback to bbox
        bbox_result = crop_by_bbox(img, r0)
        return bbox_result

    def _run_ocr(self, img):
        """Run Hybrid OCR and return normalized blocks."""
        ocr = self._get_ocr()
        result = ocr.extract(img)
        if not result.text_blocks:
            return []

        blocks = []
        for tb in result.text_blocks:
            bbox = tb.bbox
            if isinstance(bbox, list) and len(bbox) == 4:
                if isinstance(bbox[0], list):
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

    def _classify_blocks(self, ocr_blocks):
        """Use PhoBERT NER to classify each block as drugname/other."""
        classifier = self._get_classifier()
        results = classifier.classify(ocr_blocks)
        return results

    def _extract_medications(self, ner_results):
        """Extract drugname blocks and map to standard names."""
        mapper = self._get_drug_mapper()
        medications = []

        for block in ner_results:
            if block.get("label") == "drugname":
                text = block["text"]
                match = mapper.lookup(text)
                # VĐ4: NER trả key "box", cần đọc cả "bbox" lẫn "box"
                bbox = block.get("bbox") or block.get("box")
                medications.append({
                    "ocr_text": text,
                    "drug_name": (
                        match.get("name", text) if match else text
                    ),
                    "match_score": (
                        match.get("score", 0) if match else 0
                    ),
                    "confidence": block.get("confidence", 0),
                    "bbox": bbox,
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
            dict: matches, detections, n_pills
        """
        if isinstance(pill_image, str):
            pimg = cv2.imread(pill_image)
        else:
            pimg = pill_image

        if pimg is None:
            return {"error": "Cannot read pill image"}

        pill_det = self._get_pill_detector()
        detections = pill_det.detect(pimg)

        if not detections:
            return {
                "matches": [],
                "detections": [],
                "n_pills": 0,
                "warning": "No pills detected",
            }

        matcher = self._get_matcher()
        matches = matcher.match(
            pimg, prescription_blocks,
            img_w=img_w, img_h=img_h,
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
            "classifier_loaded": self._classifier is not None,
            "pill_detector_loaded": self._pill_det is not None,
        }
        if self._classifier is not None:
            info["checkpoint"] = self._classifier.checkpoint_info
        return info
