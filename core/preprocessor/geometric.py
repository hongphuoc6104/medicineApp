"""
Geometric Transformer — Crop & Rotate theo polygon mask.

Tham khảo từ:
YOLO11-Seg-Label-Detector-main/core/preprocessor/geometric_transformer.py

Mục đích: Sau khi YOLO detect tờ đơn thuốc và trả về polygon mask,
module này cắt vùng đơn ra rồi xoay thẳng về ảnh chữ nhật đứng thẳng.
"""

import logging
import os
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def deskew(
    image: np.ndarray,
    max_angle: float = 15.0,
) -> Tuple[np.ndarray, float]:
    """
    Nắn thẳng ảnh bị nghiêng ±max_angle độ.

    Dùng minAreaRect trên các điểm ảnh tối để tìm góc nghiêng.
    Nếu góc < 0.5° → bỏ qua (ảnh đã thẳng).

    Args:
        image: Ảnh BGR để nắn.
        max_angle: Góc nghiêng tối đa để xử lý (default ±15°).
                   Nếu góc lớn hơn → không nắn (tránh xoay sai).

    Returns:
        (deskewed_image, angle_corrected)
        angle_corrected = 0.0 nếu không xử lý.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Lấy tọa độ các pixel tối (text)
    dark_mask = gray < 180
    coords = np.column_stack(np.where(dark_mask))

    if len(coords) < 100:  # Quá ít điểm → không đủ thông tin
        return image, 0.0

    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    # cv2.minAreaRect trả về góc trong [-90, 0)
    # Chuẩn hóa về [-45, 45)
    if angle < -45:
        angle = 90 + angle

    # Chỉ xử lý nếu góc đáng kể và trong phạm vi hợp lý
    if abs(angle) < 0.5 or abs(angle) > max_angle:
        return image, 0.0

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),  # Nền trắng
    )
    logger.debug(f"Deskew: angle={angle:.2f}°")
    return deskewed, angle


def _order_points(pts: np.ndarray) -> np.ndarray:
    """
    Sắp xếp 4 điểm theo thứ tự: TL, TR, BR, BL.
    Dùng góc arctan2 tính từ tâm.
    """
    center = np.mean(pts, axis=0)

    def get_angle(p):
        return np.arctan2(p[1] - center[1], p[0] - center[0])

    sorted_pts = sorted(pts, key=get_angle)
    sorted_pts = np.array(sorted_pts, dtype="float32")
    sums = sorted_pts.sum(axis=1)
    top_left_idx = np.argmin(sums)
    return np.roll(sorted_pts, -top_left_idx, axis=0)


def crop_and_rotate(
    image: np.ndarray,
    mask_points: np.ndarray,
    save_path: Optional[str] = None,
    stem: str = "image"
) -> Tuple[Optional[np.ndarray], str]:
    """
    Cắt và xoay vùng ảnh theo polygon mask dùng warpAffine.

    Args:
        image: Ảnh gốc BGR (numpy array).
        mask_points: Polygon points [[x,y], ...] từ YOLO mask.
        save_path: Thư mục lưu kết quả. None = không lưu.
        stem: Tên file (không có extension).

    Returns:
        (warped_image, status_message)
        warped_image có thể là portrait hoặc landscape tùy góc tờ đơn.
    """
    if mask_points is None or len(mask_points) < 3:
        return None, "Insufficient mask points (need at least 3)"

    try:
        points = np.array(mask_points, dtype=np.int32)
        if len(points.shape) == 1:
            points = points.reshape(-1, 2)

        # Tìm hình chữ nhật diện tích nhỏ nhất bao quanh polygon
        rect = cv2.minAreaRect(points)
        box = cv2.boxPoints(rect)
        box = np.int32(box)
        src_pts = _order_points(box)
        (tl, tr, br, bl) = src_pts

        # Kích thước ảnh đầu ra
        max_width = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
        max_height = int(max(np.linalg.norm(tl - bl), np.linalg.norm(tr - br)))

        if max_width <= 0 or max_height <= 0:
            return None, "Invalid dimensions after transformation"

        # Affine transform (3 điểm)
        dst_pts = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
        ], dtype="float32")

        M = cv2.getAffineTransform(src_pts[:3], dst_pts)
        warped = cv2.warpAffine(
            image, M, (max_width, max_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE
        )

        # Lưu kết quả nếu có save_path
        if save_path is not None:
            os.makedirs(save_path, exist_ok=True)
            out_file = os.path.join(save_path, f"{stem}_rotated.png")
            cv2.imwrite(out_file, warped)
            logger.debug(f"Saved rotated: {out_file}")

        status = f"OK: {max_width}x{max_height}"
        logger.debug(f"crop_and_rotate {stem}: {status}")
        return warped, status

    except Exception as e:
        logger.error(f"crop_and_rotate error: {e}")
        return None, f"Error: {str(e)}"
