"""
ocr_engine.py — Hybrid OCR: EasyOCR CRAFT detect + VietOCR recognize.

Hybrid approach được chọn vì:
- EasyOCR CRAFT: detect vùng text trên GPU (PyTorch CUDA)
- VietOCR: nhận diện tiếng Việt có dấu chính xác

Pipeline:
1. EasyOCR CRAFT detect → lấy bbox polygons (GPU ~1s)
2. Crop từng vùng text
3. VietOCR recognize (batch) → text tiếng Việt chính xác

Optimizations (v3):
- EasyOCR CRAFT chạy GPU (từ PaddleOCR CPU 9s → 1s)
- VietOCR dùng predict_batch trên GPU
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
    Hybrid OCR: EasyOCR CRAFT detect + VietOCR recognize (batch).

    Args:
        device:  'cpu', 'gpu', hoặc 'cuda'
        vietocr_model: 'vgg_transformer' (mặc định, chính xác nhất)
        batch_size: Số region VietOCR xử lý cùng lúc (default 32)
    """

    def __init__(
        self,
        vietocr_model: str = "vgg_transformer",
        device: str = "cpu",
        batch_size: int = 32,
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
        self._device = "gpu" if self._use_gpu else "cpu"

        self._vietocr_model_name = vietocr_model
        self._batch_size = batch_size
        self._rec_engine = None   # VietOCR (lazy)
        self._det_engine = None   # EasyOCR (lazy)
        logger.info(
            f"HybridOcrModule init: "
            f"vietocr={vietocr_model}, device={self._device}, "
            f"batch_size={batch_size}"
        )

    def _ensure_detector(self):
        """Lazy load EasyOCR CRAFT detection engine."""
        if self._det_engine is not None:
            return
        import easyocr
        logger.info(
            f"Loading EasyOCR CRAFT detector "
            f"gpu={self._use_gpu}"
        )
        self._det_engine = easyocr.Reader(
            ['vi', 'en'],
            gpu=self._use_gpu,
        )
        logger.info("EasyOCR CRAFT detector ready.")

    # EasyOCR CRAFT detection parameters
    # link_threshold: higher → CRAFT links chars tighter → fewer, larger boxes
    # text_threshold: higher → skip low-confidence noise blocks
    _CRAFT_PARAMS = dict(
        text_threshold=0.75,   # default 0.7
        link_threshold=0.6,    # default 0.4 — key: links chars into words
        low_text=0.4,
        detail=1,
        # paragraph=False: let merge_same_line handle line merging
        # so GCN graph structure is preserved
        paragraph=False,
    )

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
        """Run EasyOCR CRAFT detection → list of bbox polygons.

        Uses CUDA GPU if available (~1s vs PaddleOCR CPU ~9s).
        """
        self._ensure_detector()
        polys = []
        try:
            # Convert BGR → RGB for EasyOCR
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self._det_engine.readtext(
                rgb, **self._CRAFT_PARAMS
            )
            for item in results:
                bbox = item[0]
                polys.append(
                    [[int(p[0]), int(p[1])] for p in bbox]
                )
        except Exception as e:
            logger.error(f"EasyOCR detect error: {e}")
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
        Nhận diện text: EasyOCR CRAFT detect → VietOCR recognize.

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
