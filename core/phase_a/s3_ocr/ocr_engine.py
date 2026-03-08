"""
ocr_engine.py — Hybrid OCR: PaddleOCR detect + VietOCR recognize.

Pipeline:
1. PaddleOCR PP-OCRv5 detect → line-level bbox polygons (GPU)
2. Crop từng vùng text (với padding ±5px)
3. VietOCR recognize (batch, beamsearch) → text tiếng Việt

Improvements v4:
- C3: PaddleOCR PP-OCRv5 thay CRAFT (line-level, tách STT riêng)
- C2: Crop padding ±5px (giữ nét biên chữ)
- C1: VietOCR beamsearch=True (chính xác hơn greedy)
"""

import json
import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

from core.phase_a.s3_ocr.base import BaseOCR, OcrResult, TextBlock

logger = logging.getLogger(__name__)

# Crop padding (pixels) — C2
CROP_PADDING = 5


def _crop_polygon(
    image: np.ndarray, poly_pts: list
) -> Optional[np.ndarray]:
    """Crop vùng text theo bbox polygon với padding."""
    try:
        pts = np.array(poly_pts, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(pts)
        pad = CROP_PADDING
        x = max(0, x - pad)
        y = max(0, y - pad)
        x2 = min(image.shape[1], x + w + pad * 2)
        y2 = min(image.shape[0], y + h + pad * 2)
        if x2 - x < 4 or y2 - y < 4:
            return None
        return image[y:y2, x:x2]
    except Exception as e:
        logger.debug(f"_crop_polygon error: {e}")
        return None


class HybridOcrModule(BaseOCR):
    """
    Hybrid OCR: PaddleOCR detect + VietOCR recognize (batch).

    Args:
        device:         'cpu' hoặc 'gpu'
        vietocr_model:  'vgg_transformer' (mặc định)
        batch_size:     Số region VietOCR xử lý cùng lúc
        det_model:      PaddleOCR detection model name
    """

    def __init__(
        self,
        vietocr_model: str = "vgg_transformer",
        device: str = "gpu",
        batch_size: int = 32,
        det_model: str = "PP-OCRv5_mobile_det",
    ):
        import torch
        if device in ("cuda", "gpu"):
            self._use_gpu = torch.cuda.is_available()
            self._torch_device = (
                "cuda" if self._use_gpu else "cpu"
            )
        else:
            self._use_gpu = False
            self._torch_device = "cpu"
        self._paddle_device = (
            "gpu" if self._use_gpu else "cpu"
        )

        self._vietocr_model_name = vietocr_model
        self._batch_size = batch_size
        self._det_model = det_model
        self._rec_engine = None   # VietOCR (lazy)
        self._det_engine = None   # PaddleOCR (lazy)
        logger.info(
            f"HybridOcrModule init: "
            f"det={det_model}, rec={vietocr_model}, "
            f"device={self._paddle_device}"
        )

    # ── PaddleOCR Detection (C3) ──────────────────────────

    def _ensure_detector(self):
        """Lazy load PaddleOCR PP-OCRv5 detection."""
        if self._det_engine is not None:
            return

        os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

        from paddleocr import PaddleOCR
        logger.info(
            f"Loading PaddleOCR: {self._det_model} "
            f"on {self._paddle_device}"
        )
        self._det_engine = PaddleOCR(
            text_detection_model_name=self._det_model,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device=self._paddle_device,
            enable_mkldnn=False,
        )
        logger.info("PaddleOCR detector ready.")

    def _detect_polys(self, image: np.ndarray) -> list:
        """PaddleOCR TextDetection → line-level polygons.

        Line-level: 1 dòng text = 1 box.
        Không cần merge.
        """
        self._ensure_detector()
        polys = []
        try:
            results = list(self._det_engine.predict(image))
            for r in results:
                # TextDetection output: list of dicts with 'dt_polys'
                dt_polys = r.get("dt_polys", [])
                for poly in dt_polys:
                    p = (poly.tolist()
                         if hasattr(poly, "tolist") else poly)
                    pts = [
                        [int(pt[0]), int(pt[1])] for pt in p
                    ]
                    polys.append(pts)
        except Exception as e:
            logger.error(f"PaddleOCR detect error: {e}")

        logger.info(
            f"PaddleOCR detected {len(polys)} text regions"
        )
        return polys

    # ── VietOCR Recognition (C1: beamsearch) ──────────────

    def _ensure_recognizer(self):
        """Lazy load VietOCR recognition engine."""
        if self._rec_engine is not None:
            return
        from vietocr.tool.config import Cfg
        from vietocr.tool.predictor import Predictor

        config = Cfg.load_config_from_name(
            self._vietocr_model_name
        )
        config["device"] = self._torch_device
        config["predictor"]["beamsearch"] = False  # C1 reverted: beamsearch causes hallucination

        local_weights = os.path.expanduser(
            f"~/.config/vietocr/"
            f"{self._vietocr_model_name}.pth"
        )
        if os.path.isfile(local_weights):
            config["weights"] = local_weights
            logger.info(f"VietOCR weights: {local_weights}")
        else:
            logger.info("Downloading VietOCR weights...")

        self._rec_engine = Predictor(config)
        logger.info(
            f"VietOCR loaded: {self._vietocr_model_name}"
            f" on {self._torch_device} (beamsearch=True)"
        )

    def _recognize_batch(
        self, image: np.ndarray, polys: list
    ) -> list[TextBlock]:
        """
        Crop regions (C2: padding) + VietOCR batch recognize.
        """
        from PIL import Image as PILImage

        # Step 1: Crop tất cả regions
        crops = []
        crop_indices = []
        for i, poly_pts in enumerate(polys):
            cropped = _crop_polygon(image, poly_pts)
            if cropped is not None:
                try:
                    rgb = cv2.cvtColor(
                        cropped, cv2.COLOR_BGR2RGB
                    )
                    pil_img = PILImage.fromarray(rgb)
                    crops.append(pil_img)
                    crop_indices.append(i)
                except Exception as e:
                    logger.debug(
                        f"Crop convert error idx={i}: {e}"
                    )

        if not crops:
            return []

        # Step 2: VietOCR batch predict
        try:
            texts = self._rec_engine.predict_batch(crops)
        except Exception as e:
            logger.warning(
                f"predict_batch failed, falling back: {e}"
            )
            # Fallback: predict one by one
            texts = []
            for pil_img in crops:
                try:
                    t = self._rec_engine.predict(pil_img)
                    texts.append(
                        str(t).strip() if t else ""
                    )
                except Exception:
                    texts.append("")

        # Step 3: Build TextBlocks
        text_blocks = []
        for idx, text in zip(crop_indices, texts):
            text = str(text).strip() if text else ""
            if text:
                text_blocks.append(TextBlock(
                    text=text,
                    confidence=1.0,
                    bbox=polys[idx],
                ))

        return text_blocks

    # ── Main Entry Point ──────────────────────────────────

    def extract(
        self,
        image: np.ndarray,
        input_type: str = "",
        paddle_json_path: Optional[str] = None,
    ) -> OcrResult:
        """
        PaddleOCR detect → VietOCR recognize.

        Args:
            image:            Ảnh BGR numpy array.
            input_type:       Ghi vào kết quả.
            paddle_json_path: Load polys từ JSON (skip detect).
        """
        self._ensure_recognizer()
        t_start = time.time()

        # Step 1: Get polygons
        if paddle_json_path:
            polys = self._load_polys_from_json(
                paddle_json_path
            )
        else:
            t_det = time.time()
            polys = self._detect_polys(image)
            det_ms = (time.time() - t_det) * 1000
            logger.info(
                f"Detection: {len(polys)} regions "
                f"in {det_ms:.0f}ms"
            )

        # Step 2: Batch recognize
        t_rec = time.time()
        text_blocks = self._recognize_batch(image, polys)
        rec_ms = (time.time() - t_rec) * 1000
        logger.info(
            f"Recognition: {len(text_blocks)} blocks "
            f"in {rec_ms:.0f}ms"
        )

        elapsed = (time.time() - t_start) * 1000
        logger.info(
            f"HybridOCR: {len(text_blocks)} blocks"
            f" in {elapsed:.1f}ms "
            f"(device={self._paddle_device})"
        )
        return OcrResult(
            text_blocks=text_blocks,
            module_name="hybrid",
            input_type=input_type,
            elapsed_ms=elapsed,
        )

    def _load_polys_from_json(self, json_path: str) -> list:
        """Load bbox polygons từ JSON file."""
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            blocks = (
                data.get("blocks", [])
                if isinstance(data, dict) else data
            )
            polys = []
            for b in blocks:
                if isinstance(b, dict):
                    bbox = b.get("bbox", [])
                    if bbox and len(bbox) == 4:
                        polys.append(bbox)
            logger.info(
                f"Loaded {len(polys)} polys from {json_path}"
            )
            return polys
        except Exception as e:
            logger.error(
                f"Failed to read JSON {json_path}: {e}"
            )
            return []

    # Use BaseOCR.save_results() — no longer a stub
