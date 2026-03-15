from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass
class QualityResult:
    state: str
    reject_reason: str | None
    guidance: str
    metrics: dict[str, Any]


def _blur_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _glare_ratio(gray: np.ndarray) -> float:
    bright = (gray >= 245).sum()
    total = gray.size
    return float(bright) / float(total)


def _content_bbox(gray: np.ndarray) -> tuple[int, int, int, int]:
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ys, xs = np.where(thr > 0)
    if len(xs) == 0 or len(ys) == 0:
        return 0, 0, gray.shape[1], gray.shape[0]
    x1, x2 = int(xs.min()), int(xs.max())
    y1, y2 = int(ys.min()), int(ys.max())
    return x1, y1, x2, y2


def assess_image_quality(image: np.ndarray) -> QualityResult:
    """Lightweight gate before OCR.

    Returns GOOD / WARNING / REJECT with guidance for user.
    """
    if image is None or image.size == 0:
        return QualityResult(
            state="REJECT",
            reject_reason="INVALID_IMAGE",
            guidance="Anh khong hop le. Vui long chup lai.",
            metrics={},
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]

    blur = _blur_score(gray)
    glare = _glare_ratio(gray)
    x1, y1, x2, y2 = _content_bbox(gray)

    margin = int(min(w, h) * 0.02)
    cutoff = (
        x1 <= margin
        or y1 <= margin
        or x2 >= (w - margin)
        or y2 >= (h - margin)
    )

    metrics = {
        "blur_score": round(blur, 2),
        "glare_ratio": round(glare, 4),
        "content_bbox": [x1, y1, x2, y2],
        "image_size": [w, h],
    }

    if blur < 55:
        return QualityResult(
            state="REJECT",
            reject_reason="BLURRY_IMAGE",
            guidance="Anh bi mo. Giu may on dinh va chup lai gan hon.",
            metrics=metrics,
        )

    if glare > 0.22:
        return QualityResult(
            state="REJECT",
            reject_reason="GLARE_IMAGE",
            guidance="Anh bi choi sang. Doi goc chup hoac giam phan chieu.",
            metrics=metrics,
        )

    if cutoff:
        return QualityResult(
            state="WARNING",
            reject_reason="CONTENT_CUTOFF",
            guidance="Co the bi cat thieu vung chu. Lui camera de lay tron don thuoc.",
            metrics=metrics,
        )

    if blur < 90 or glare > 0.12:
        return QualityResult(
            state="WARNING",
            reject_reason=None,
            guidance="Anh dung duoc nhung nen cai thien de ket qua on dinh hon.",
            metrics=metrics,
        )

    return QualityResult(
        state="GOOD",
        reject_reason=None,
        guidance="Anh tot. Dang xu ly nhan dien thuoc.",
        metrics=metrics,
    )
