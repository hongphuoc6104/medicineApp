"""
ocr_fusion.py — Multi-frame OCR Fusion.

Tổng hợp kết quả OCR từ nhiều frames/ảnh của CÙNG 1 đơn thuốc
để lấy text chất lượng cao nhất.

Chiến lược:
  1. Confidence-based voting: với mỗi vùng text (bbox overlap ≥ 50%),
     chọn text có confidence cao nhất.
  2. Consensus filter: chỉ giữ block xuất hiện trong ≥ min_votes frames.

Dùng khi:
  - Camera: chụp 2-3 lần cùng đơn thuốc
  - Gallery: user chọn nhiều ảnh + xác nhận "cùng 1 toa"

Ví dụ:
    from core.ocr.ocr_fusion import OcrFusion
    from core.ocr.ocr_engine import HybridOcrModule

    engine = HybridOcrModule(device="cuda")
    fusion = OcrFusion(min_votes=2, iou_threshold=0.4)

    results = [engine.extract(img) for img in frames]
    fused = fusion.fuse(results)
    # fused là OcrResult tổng hợp tốt nhất từ tất cả frames
"""

import logging
from collections import defaultdict
from typing import List

import numpy as np

from core.ocr.base import OcrResult, TextBlock

logger = logging.getLogger(__name__)


def _bbox_to_xyxy(bbox) -> tuple:
    """Convert 4-point bbox [[x,y]×4] → (xmin, ymin, xmax, ymax)."""
    if not bbox:
        return (0, 0, 0, 0)
    pts = bbox if isinstance(bbox[0], (list, tuple)) else [[bbox[0], bbox[1]], [bbox[2], bbox[3]]]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _iou(a: tuple, b: tuple) -> float:
    """Tính IoU giữa 2 bbox (xmin, ymin, xmax, ymax)."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    return inter_area / (area_a + area_b - inter_area)


class OcrFusion:
    """
    Multi-frame OCR Fusion.

    Args:
        min_votes: Số frame tối thiểu 1 vùng text phải xuất hiện.
                   (default=1: giữ tất cả, dùng frame tốt nhất)
        iou_threshold: IoU tối thiểu để coi 2 bbox là cùng vùng text.
    """

    def __init__(
        self,
        min_votes: int = 1,
        iou_threshold: float = 0.4,
    ):
        self.min_votes = min_votes
        self.iou_threshold = iou_threshold

    def fuse(self, results: List[OcrResult]) -> OcrResult:
        """
        Tổng hợp nhiều OcrResult → 1 OcrResult chất lượng cao nhất.

        Thuật toán:
          1. Ghép tất cả block từ mọi frame.
          2. Nhóm các block có bbox overlap (IoU ≥ threshold) → cùng vùng.
          3. Trong mỗi nhóm: chọn text có confidence cao nhất.
          4. Lọc nhóm có < min_votes frame → bỏ (noise).

        Args:
            results: List OcrResult từ nhiều frames cùng đơn thuốc.

        Returns:
            OcrResult tổng hợp.
        """
        if not results:
            return OcrResult(module_name="fusion", text_blocks=[], elapsed_ms=0)

        if len(results) == 1:
            logger.info("OcrFusion: 1 frame, no fusion needed")
            return results[0]

        total_ms = sum(r.elapsed_ms for r in results)

        # Ghép tất cả block + đánh dấu từ frame nào
        all_blocks: List[tuple] = []  # (TextBlock, frame_idx)
        for i, res in enumerate(results):
            for b in res.text_blocks:
                all_blocks.append((b, i))

        logger.info(
            f"OcrFusion: {len(results)} frames, "
            f"{len(all_blocks)} total blocks"
        )

        # Nhóm các block cùng vùng bằng IoU
        used = [False] * len(all_blocks)
        groups = []

        for i, (bi, fi) in enumerate(all_blocks):
            if used[i]:
                continue
            bbox_i = _bbox_to_xyxy(bi.bbox)
            group = [(bi, fi)]
            used[i] = True

            for j, (bj, fj) in enumerate(all_blocks):
                if used[j] or i == j:
                    continue
                bbox_j = _bbox_to_xyxy(bj.bbox)
                if _iou(bbox_i, bbox_j) >= self.iou_threshold:
                    group.append((bj, fj))
                    used[j] = True

            groups.append(group)

        logger.info(f"OcrFusion: {len(groups)} unique regions after grouping")

        # Chọn best block trong mỗi nhóm
        fused_blocks = []
        for group in groups:
            # Đếm số frames khác nhau
            frame_ids = {fj for _, fj in group}
            if len(frame_ids) < self.min_votes:
                logger.debug(
                    f"  Dropped (votes={len(frame_ids)}<{self.min_votes}): "
                    f"'{group[0][0].text[:30]}'"
                )
                continue

            # Chọn block có confidence cao nhất
            best_block = max(group, key=lambda x: x[0].confidence)[0]
            fused_blocks.append(best_block)

            if len(frame_ids) > 1:
                texts = [b.text for b, _ in group]
                logger.debug(
                    f"  Merged {len(frame_ids)} frames: "
                    f"best='{best_block.text[:40]}' "
                    f"(conf={best_block.confidence:.2f})"
                )
                # Log nếu frames agree (chất lượng cao)
                if len(set(texts)) == 1:
                    logger.debug("    → All frames agree ✅")

        # Sort theo vị trí (top → bottom, left → right)
        fused_blocks.sort(key=lambda b: (
            min(pt[1] for pt in b.bbox) if b.bbox else 0,
            min(pt[0] for pt in b.bbox) if b.bbox else 0,
        ))

        logger.info(
            f"OcrFusion: {len(fused_blocks)} fused blocks "
            f"(from {len(all_blocks)} raw, {total_ms:.0f}ms total)"
        )

        return OcrResult(
            module_name=f"fusion({len(results)} frames)",
            text_blocks=fused_blocks,
            elapsed_ms=total_ms,
        )

    def fuse_images(self, images: list, engine) -> OcrResult:
        """
        Convenience: chạy OCR trên list ảnh rồi fuse luôn.

        Args:
            images: List ảnh BGR (numpy array).
            engine: OcrModule instance (có method .extract()).

        Returns:
            Fused OcrResult.
        """
        results = []
        for i, img in enumerate(images):
            logger.info(f"OcrFusion: running OCR on frame {i+1}/{len(images)}")
            r = engine.extract(img)
            results.append(r)
        return self.fuse(results)
