"""
ocr_engine.py — Hybrid OCR: PaddleOCR detect + VietOCR recognize.

Pipeline:
1. PaddleOCR PP-OCRv5 detect → line-level bbox polygons (GPU)
2. Crop từng vùng text bằng Perspective Transform (±5px padding)
3. VietOCR recognize (batch, greedy) → text tiếng Việt

Improvements v5:
- VĐ1: Perspective Transform thay boundingRect (crop chính xác chữ nghiêng)
- C3: PaddleOCR PP-OCRv5 thay CRAFT (line-level, tách STT riêng)
- C2: Crop padding ±5px (giữ nét biên chữ)
- C1: VietOCR beamsearch=False (tránh hallucination)
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


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left
    rect[2] = pts[np.argmax(s)]   # bottom-right
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]   # top-right
    rect[3] = pts[np.argmax(d)]   # bottom-left
    return rect


def _crop_polygon(
    image: np.ndarray, poly_pts: list
) -> Optional[np.ndarray]:
    """Crop vùng text theo bbox polygon.

    - 4 điểm: dùng Perspective Transform (chính xác cho chữ nghiêng).
    - Khác 4 điểm: fallback về boundingRect.
    - Có padding ±CROP_PADDING px.
    """
    try:
        pts = np.array(poly_pts, dtype=np.float32)
        pad = CROP_PADDING

        if len(pts) == 4:
            # ── Perspective Transform (VĐ1 fix) ──
            ordered = _order_points(pts)
            width = int(max(
                np.linalg.norm(ordered[1] - ordered[0]),
                np.linalg.norm(ordered[2] - ordered[3]),
            ))
            height = int(max(
                np.linalg.norm(ordered[3] - ordered[0]),
                np.linalg.norm(ordered[2] - ordered[1]),
            ))
            # Thêm padding vào kích thước đích
            width = width + pad * 2
            height = height + pad * 2
            if width <= 4 or height <= 4:
                return None

            # Dịch nguồn để tạo padding
            dst = np.array([
                [pad, pad],
                [width - pad, pad],
                [width - pad, height - pad],
                [pad, height - pad],
            ], dtype=np.float32)
            M = cv2.getPerspectiveTransform(ordered, dst)
            return cv2.warpPerspective(image, M, (width, height))
        else:
            # ── Fallback: boundingRect cho polygon != 4 điểm ──
            pts_int = pts.astype(np.int32)
            x, y, w, h = cv2.boundingRect(pts_int)
            x = max(0, x - pad)
            y = max(0, y - pad)
            x2 = min(image.shape[1], x + w + pad * 2)
            y2 = min(image.shape[0], y + h + pad * 2)
            if x2 - x < 4 or y2 - y < 4:
                return None
            return image[y:y2, x:x2]
    except Exception as e:
        # ── Ultimate fallback: boundingRect nếu perspective lỗi ──
        logger.warning(f"_crop_polygon error: {e}, falling back to boundingRect")
        try:
            pts_int = np.array(poly_pts, dtype=np.int32)
            x, y, w, h = cv2.boundingRect(pts_int)
            h = max(h, 1)
            w = max(w, 1)
            return image[y:y+h, x:x+w]
        except Exception:
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
            f" on {self._torch_device} (beamsearch=False)"
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


# ── Group by STT: Gộp theo cột rồi theo dòng (Dynamic Columns) ─────────────────

def _detect_dynamic_col_bounds(blocks, num_cols=4):
    """
    Tự động tìm (num_cols - 1) ranh giới cột dựa trên khoảng trống (gap)
    lớn nhất theo trục X. (Khắc phục việc hardcode tỉ lệ cứng).
    """
    import logging
    logger = logging.getLogger(__name__)

    if len(blocks) < num_cols:
        return None

    # Thu thập tất cả hộp bao (bounding boxes)
    all_x_bounds = []
    for b in blocks:
        xs = [pt[0] for pt in b.bbox]
        min_x = min(xs)
        max_x = max(xs)
        # Chỉ xét block ngắn (ví dụ <500px) để dò gap tốt hơn
        if max_x - min_x < 500:
            all_x_bounds.append((min_x, max_x))

    if len(all_x_bounds) < num_cols:
        return None

    # Sắp xếp các đoạn X theo điểm bắt đầu
    all_x_bounds.sort(key=lambda x: x[0])

    gaps = []
    current_max_x = all_x_bounds[0][1]

    for i in range(1, len(all_x_bounds)):
        next_min_x, next_max_x = all_x_bounds[i]

        # Có khoảng trống
        if next_min_x > current_max_x:
            gap_size = next_min_x - current_max_x
            gap_center = (next_min_x + current_max_x) / 2.0
            gaps.append((gap_size, gap_center))

        current_max_x = max(current_max_x, next_max_x)

    # Lấy top N gaps
    gaps.sort(key=lambda x: x[0], reverse=True)
    if len(gaps) < num_cols - 1:
        return None

    top_gaps = [g[1] for g in gaps[:num_cols - 1]]
    top_gaps.sort()
    logger.debug(f"Dynamic Column Bounds (Absolute X): {top_gaps}")
    return top_gaps


def group_by_stt(blocks: list) -> list:
    """
    Gộp TextBlock thành các dòng hoàn chỉnh với thứ tự ngữ nghĩa đúng.

    Thứ tự đầu ra mỗi ô thuốc:
        STT | [Tên thuốc ↓ Hướng dẫn dùng] | Số lượng | Đơn vị

    Thuật toán (Dynamic):
        1. Tìm ranh giới cột bằng cách nhận diện các khoảng trống lớn trên trục X.
           (Nếu thất bại do ảnh mờ/lộn xộn, fallback về tỉ lệ tương đối 0.13, 0.75, 0.88).
        2. Tìm Anchor STT (cột 1 trái cùng, là số nguyên thuần).
        3. Phân vùng bands theo Y-midpoint giữa các Anchor.
        4. Trong mỗi band: phân block vào từng cột.
        5. Trong mỗi cột: sort từ trên xuống dưới (Y).
        6. Ghép các cột từ trái sang phải, phân cách bằng " | ".

    Args:
        blocks: Danh sách TextBlock từ OCR.
    Returns:
        Danh sách TextBlock đã gộp theo thứ tự ngữ nghĩa đúng.
    """
    import re
    from core.phase_a.s3_ocr.base import TextBlock
    import logging
    logger = logging.getLogger(__name__)

    if not blocks:
        return []

    def _y_center(bbox):
        ys = [pt[1] for pt in bbox]
        return (min(ys) + max(ys)) / 2.0

    def _x_center(bbox):
        xs = [pt[0] for pt in bbox]
        return (min(xs) + max(xs)) / 2.0

    all_x = [pt[0] for b in blocks for pt in b.bbox]
    min_x = min(all_x)
    max_x = max(all_x)
    board_width = max(max_x - min_x, 1)

    # Thử lấy Absolute Column Bounds động
    abs_col_bounds = _detect_dynamic_col_bounds(blocks, num_cols=4)

    def _col_idx(block):
        if abs_col_bounds:
            xc = _x_center(block.bbox)
            for i, bound in enumerate(abs_col_bounds):
                if xc <= bound:
                    return i
            return len(abs_col_bounds)
        else:
            # Fallback tương đối (v2 cũ)
            rx = (_x_center(block.bbox) - min_x) / board_width
            FALLBACK_BOUNDS = [0.13, 0.75, 0.88]
            for i, bnd in enumerate(FALLBACK_BOUNDS):
                if rx <= bnd:
                    return i
            return len(FALLBACK_BOUNDS)

    # 1. Tìm Anchor STT
    stt_re = re.compile(r"^\d+$")
    anchors = [
        b for b in blocks
        if _col_idx(b) == 0 and stt_re.match(b.text.strip())
    ]
    anchors.sort(key=lambda b: _y_center(b.bbox))

    if not anchors:
        logger.warning("group_by_stt: Không tìm thấy STT anchor → trả về blocks gốc.")
        return blocks

    # 2. Xây Boundaries và Bands
    boundaries = [
        (_y_center(anchors[i].bbox) + _y_center(anchors[i + 1].bbox)) / 2.0
        for i in range(len(anchors) - 1)
    ]
    bands: list[list] = [[] for _ in range(len(anchors))]
    headers = []

    for b in blocks:
        yc = _y_center(b.bbox)
        if yc < _y_center(anchors[0].bbox) - 20:
            headers.append(b)
            continue
        assigned = False
        for i, bound in enumerate(boundaries):
            if yc <= bound:
                bands[i].append(b)
                assigned = True
                break
        if not assigned:
            bands[-1].append(b)

    # 3-5. Gộp
    merged = []
    headers.sort(key=lambda b: _y_center(b.bbox))
    merged.extend(headers)

    num_cols = len(abs_col_bounds) + 1 if abs_col_bounds else 4
    for band in bands:
        if not band:
            continue

        col_groups: dict[int, list] = {i: [] for i in range(num_cols)}
        for b in band:
            col_groups[_col_idx(b)].append(b)

        for cg in col_groups.values():
            cg.sort(key=lambda b: _y_center(b.bbox))

        parts = []
        for col_i in sorted(col_groups.keys()):
            col_texts = [b.text.strip() for b in col_groups[col_i] if b.text.strip()]
            if col_texts:
                parts.append(" ".join(col_texts))

        merged_text = " | ".join(parts)

        all_pts = [pt for b in band for pt in b.bbox]
        xs = [pt[0] for pt in all_pts]
        ys = [pt[1] for pt in all_pts]
        merged_bbox = [
            [min(xs), min(ys)],
            [max(xs), min(ys)],
            [max(xs), max(ys)],
            [min(xs), max(ys)],
        ]
        avg_conf = sum(b.confidence for b in band) / len(band)
        merged.append(TextBlock(
            text=merged_text.strip(),
            confidence=round(avg_conf, 4),
            bbox=merged_bbox,
        ))

    mode = "Dynamic" if abs_col_bounds else "StaticFallback"
    logger.info(
        f"group_by_stt [{mode}]: {len(blocks)} blocks → {len(merged)} lines "
        f"(Found {len(anchors)} STTs)"
    )
    return merged
