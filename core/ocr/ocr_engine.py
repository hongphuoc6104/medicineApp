"""
ocr_engine.py — Hybrid OCR: PaddleOCR detect + VietOCR recognize.

Hybrid approach được chọn vì:
- PaddleOCR: detect vùng text rất nhanh và chính xác
- VietOCR: nhận diện tiếng Việt có dấu chính xác hơn PaddleOCR rec

Pipeline:
1. PaddleOCR detect → lấy bbox polygons
2. Crop từng vùng text
3. VietOCR recognize (batch) → text tiếng Việt chính xác

Optimizations (v2):
- PaddleOCR chỉ load detection model (skip rec/cls)
- VietOCR dùng predict_batch thay vì predict từng region
- Cả 2 engine đều lazy-load singleton
"""

import json
import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

from core.ocr.base import BaseOCR, OcrResult, TextBlock

logger = logging.getLogger(__name__)

# Fix PaddlePaddle 3.3.0 MKLDNN bug
os.environ.setdefault("FLAGS_enable_pir_api", "0")


def _crop_polygon(
    image: np.ndarray, poly_pts: list
) -> Optional[np.ndarray]:
    """Crop vùng text theo bbox polygon."""
    try:
        pts = np.array(poly_pts, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(pts)
        x = max(0, x)
        y = max(0, y)
        x2 = min(image.shape[1], x + w)
        y2 = min(image.shape[0], y + h)
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
        device:  'cpu', 'gpu', hoặc 'cuda'
        vietocr_model: 'vgg_transformer' (mặc định, chính xác nhất)
        batch_size: Số region VietOCR xử lý cùng lúc (default 32)
    """

    def __init__(
        self,
        vietocr_model: str = "vgg_transformer",
        device: str = "cpu",
        det_thresh: float = 0.3,
        det_box_thresh: float = 0.3,
        det_limit_side_len: int = 960,
        cpu_threads: int = 4,
        batch_size: int = 32,
    ):
        # Normalize device
        if device in ("cuda", "gpu"):
            self._device = "gpu"
            self._torch_device = "cuda"
        else:
            self._device = "cpu"
            self._torch_device = "cpu"

        self._vietocr_model_name = vietocr_model
        self._det_thresh = det_thresh
        self._det_box_thresh = det_box_thresh
        self._det_limit_side_len = det_limit_side_len
        self._cpu_threads = cpu_threads
        self._batch_size = batch_size
        self._rec_engine = None   # VietOCR (lazy)
        self._det_engine = None   # PaddleOCR (lazy)
        self._det_inner = None    # _OCRPipeline internals (det bypass)
        logger.info(
            f"HybridOcrModule init: "
            f"vietocr={vietocr_model}, device={self._device}, "
            f"batch_size={batch_size}"
        )

    def _ensure_detector(self):
        """Lazy load PaddleOCR detection engine."""
        if self._det_engine is not None:
            return
        from paddleocr import PaddleOCR
        logger.info(
            f"Loading PaddleOCR detector device={self._device}"
        )
        self._det_engine = PaddleOCR(
            lang="vi",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_det_thresh=self._det_thresh,
            text_det_box_thresh=self._det_box_thresh,
            text_rec_score_thresh=0.0,
            text_det_limit_type="max",
            text_det_limit_side_len=self._det_limit_side_len,
            enable_mkldnn=False,
            device=self._device,
            cpu_threads=self._cpu_threads,
        )
        # Cache internal det model for direct calls (saves ~5s rec time)
        try:
            self._det_inner = (
                self._det_engine.paddlex_pipeline._pipeline
            )
            logger.info("PaddleOCR: direct det bypass enabled.")
        except Exception:
            self._det_inner = None
            logger.warning("PaddleOCR: det bypass unavailable.")
        logger.info("PaddleOCR detector ready.")

    def _ensure_recognizer(self):
        """Lazy load VietOCR recognition engine."""
        if self._rec_engine is not None:
            return
        from vietocr.tool.config import Cfg
        from vietocr.tool.predictor import Predictor

        config = Cfg.load_config_from_name(self._vietocr_model_name)
        config["device"] = self._torch_device
        config["predictor"]["beamsearch"] = False

        local_weights = os.path.expanduser(
            f"~/.config/vietocr/{self._vietocr_model_name}.pth"
        )
        if os.path.isfile(local_weights):
            config["weights"] = local_weights
            logger.info(f"VietOCR weights: {local_weights}")
        else:
            logger.info("Downloading VietOCR weights...")

        self._rec_engine = Predictor(config)
        logger.info(
            f"VietOCR loaded: {self._vietocr_model_name}"
            f" on {self._torch_device}"
        )

    def _detect_polys(self, image: np.ndarray) -> list:
        """Run PaddleOCR detection → list of bbox polygons.

        Uses internal text_det_model directly to skip recognition
        (~5s saved vs full predict on each image).
        """
        self._ensure_detector()
        polys = []
        try:
            if self._det_inner is not None:
                # Direct det call — no rec overhead
                det_results = list(self._det_inner.text_det_model(
                    [image],
                    limit_side_len=self._det_limit_side_len,
                    limit_type="max",
                    thresh=self._det_thresh,
                    max_side_limit=4000,
                    box_thresh=self._det_box_thresh,
                    unclip_ratio=2.0,
                ))
                if det_results:
                    for poly in det_results[0].get(
                        "dt_polys", []
                    ):
                        pts = (
                            poly.tolist()
                            if hasattr(poly, "tolist") else poly
                        )
                        polys.append(pts)
            else:
                # Fallback: full predict()
                raw = self._det_engine.predict(image)
                if raw:
                    for res in raw:
                        if isinstance(res, dict):
                            for poly in res.get("dt_polys", []):
                                pts = (
                                    poly.tolist()
                                    if hasattr(poly, "tolist")
                                    else poly
                                )
                                polys.append(pts)
        except Exception as e:
            logger.error(f"PaddleOCR detect error: {e}")
        logger.info(f"Detected {len(polys)} text regions")
        return polys

    def _recognize_batch(
        self, image: np.ndarray, polys: list
    ) -> list[TextBlock]:
        """
        Crop regions + VietOCR batch recognize.

        Thay vì predict từng region riêng lẻ, gom thành batch
        để VietOCR xử lý nhanh hơn (đặc biệt trên GPU).
        """
        from PIL import Image as PILImage

        # Step 1: Crop tất cả regions
        crops = []
        crop_indices = []
        for i, poly_pts in enumerate(polys):
            cropped = _crop_polygon(image, poly_pts)
            if cropped is not None:
                try:
                    rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
                    pil_img = PILImage.fromarray(rgb)
                    crops.append(pil_img)
                    crop_indices.append(i)
                except Exception as e:
                    logger.debug(f"Crop convert error idx={i}: {e}")

        if not crops:
            return []

        # Step 2: VietOCR batch predict
        try:
            texts = self._rec_engine.predict_batch(crops)
        except Exception as e:
            logger.warning(f"predict_batch failed, falling back: {e}")
            # Fallback: predict one by one
            texts = []
            for pil_img in crops:
                try:
                    t = self._rec_engine.predict(pil_img)
                    texts.append(str(t).strip() if t else "")
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

    def extract(
        self,
        image: np.ndarray,
        input_type: str = "",
        paddle_json_path: Optional[str] = None,
    ) -> OcrResult:
        """
        Nhận diện text: PaddleOCR detect → VietOCR recognize (batch).

        Args:
            image:            Ảnh BGR numpy array.
            input_type:       Ghi vào kết quả.
            paddle_json_path: Nếu có, load polys từ JSON (skip detect).
        """
        self._ensure_recognizer()
        t_start = time.time()

        # Step 1: Get polygons
        if paddle_json_path:
            polys = self._load_polys_from_json(paddle_json_path)
        else:
            t_det = time.time()
            polys = self._detect_polys(image)
            det_ms = (time.time() - t_det) * 1000
            logger.info(f"Detection: {len(polys)} regions in {det_ms:.0f}ms")

        # Step 2: Batch recognize
        t_rec = time.time()
        text_blocks = self._recognize_batch(image, polys)
        rec_ms = (time.time() - t_rec) * 1000
        logger.info(f"Recognition: {len(text_blocks)} blocks in {rec_ms:.0f}ms")

        elapsed = (time.time() - t_start) * 1000
        logger.info(
            f"HybridOCR: {len(text_blocks)} blocks"
            f" in {elapsed:.1f}ms (device={self._device})"
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
            logger.info(f"Loaded {len(polys)} polys from {json_path}")
            return polys
        except Exception as e:
            logger.error(f"Failed to read JSON {json_path}: {e}")
            return []

    # Use BaseOCR.save_results() — no longer a stub
