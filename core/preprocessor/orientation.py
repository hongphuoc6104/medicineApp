"""
Orientation Corrector — Force Portrait + AI 180° Fix.

LƯU Ý: Đơn thuốc là tờ giấy ĐỨNG THẲNG (portrait: height > width).
Ngược với dự án tham khảo (nhãn sản phẩm nằm ngang - landscape).

Bước 1: force_portrait() — xoay 90° nếu ảnh đang nằm ngang (w > h)
Bước 2: fix_orientation_ai() — dùng PP-LCNet phát hiện lộn ngược 180°

Lưu ý về PP-LCNet:
- Chỉ phân loại 4 góc cố định: 0°, 90°, 180°, 270°
- KHÔNG phát hiện góc nghiêng tùy ý (15°, 30°...)
- Góc nghiêng nhỏ đã được xử lý bởi warpAffine ở bước trước
"""

import logging
import os
from typing import Optional, Tuple

import cv2
import numpy as np

from core.preprocessor.geometric import deskew  # noqa: F401 (re-exported)

logger = logging.getLogger(__name__)

# Fix PaddlePaddle 3.3.0 MKLDNN/PIR bug
os.environ.setdefault("FLAGS_enable_pir_api", "0")

# Kiểm tra PaddleOCR có sẵn không
try:
    from paddleocr import DocImgOrientationClassification
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logger.warning("PaddleOCR chưa được cài. AI orientation fix bị tắt.")

# Singleton classifier — tránh load model mỗi lần gọi (~2-3s/lần)
_classifier_cache: Optional["DocImgOrientationClassification"] = None


def _get_classifier(model_path: Optional[str] = None):
    """Singleton DocImgOrientationClassification."""
    global _classifier_cache
    if _classifier_cache is not None:
        return _classifier_cache
    if model_path and os.path.exists(model_path):
        _classifier_cache = DocImgOrientationClassification(
            model_dir=model_path
        )
    else:
        _classifier_cache = DocImgOrientationClassification(
            model_name="PP-LCNet_x1_0_doc_ori"
        )
    logger.info("DocImgOrientationClassification loaded (singleton).")
    return _classifier_cache


def force_portrait(
    image: np.ndarray,
    save_path: Optional[str] = None,
    stem: str = "image"
) -> Tuple[np.ndarray, bool]:
    """
    Đảm bảo ảnh ở dạng portrait (height >= width).
    Nếu ảnh đang nằm ngang (w > h) → xoay 90° theo chiều kim đồng hồ.

    LƯU Ý: Logic NGƯỢC với dự án tham khảo (force_landscape).
    Đơn thuốc là tờ giấy đứng thẳng.

    Args:
        image: Ảnh BGR.
        save_path: Thư mục lưu. None = không lưu.
        stem: Tên file.

    Returns:
        (image, was_rotated) — True nếu đã xoay.
    """
    h, w = image.shape[:2]

    if w > h:
        # Đang nằm ngang → xoay về đứng
        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        rotated = True
        logger.debug(f"force_portrait {stem}: Xoay 90° (was {w}x{h})")
    else:
        rotated = False
        logger.debug(f"force_portrait {stem}: Đã portrait ({w}x{h}), giữ nguyên")

    if save_path is not None:
        os.makedirs(save_path, exist_ok=True)
        out_file = os.path.join(save_path, f"{stem}_portrait.png")
        cv2.imwrite(out_file, image)

    return image, rotated


def fix_orientation_ai(
    image: np.ndarray,
    confidence_threshold: float = 0.6,
    max_width: int = 1000,
    model_path: Optional[str] = None,
    save_path: Optional[str] = None,
    stem: str = "image"
) -> Tuple[np.ndarray, str]:
    """
    Sửa lộn ngược 180° bằng AI classifier PP-LCNet.

    Model PP-LCNet_x1_0_doc_ori phân loại: 0°, 90°, 180°, 270°.
    Chỉ xoay nếu phát hiện 180° với confidence > threshold.

    Args:
        image: Ảnh BGR (đã qua force_portrait).
        confidence_threshold: Ngưỡng tin cậy tối thiểu để xoay.
        max_width: Chiều rộng tối đa khi resize để inference nhanh hơn.
        model_path: Đường dẫn model local. None = tải tự động.
        save_path: Thư mục lưu kết quả cuối. None = không lưu.
        stem: Tên file.

    Returns:
        (image, status_message)
    """
    if not PADDLE_AVAILABLE:
        if save_path:
            os.makedirs(save_path, exist_ok=True)
            cv2.imwrite(os.path.join(save_path, f"{stem}_fixed.png"), image)
        return image, "PaddleOCR không có sẵn, bỏ qua AI fix"

    try:
        # Singleton classifier (tránh tạo mới mỗi lần)
        classifier = _get_classifier(model_path)

        # Resize nhỏ lại để inference nhanh hơn
        h, w = image.shape[:2]
        if w > max_width:
            scale = max_width / float(w)
            check_img = cv2.resize(image, (0, 0), fx=scale, fy=scale,
                                   interpolation=cv2.INTER_LINEAR)
        else:
            check_img = image

        # Dự đoán hướng
        results = classifier.predict(check_img)
        if not results:
            status = "Không có kết quả từ classifier"
            label, score = "0", 0.0
        else:
            res = results[0]
            if isinstance(res, dict) and 'label_names' in res:
                label = res['label_names'][0]
                score = res['scores'][0]
            else:
                label = str(getattr(res, 'label_names', ['0'])[0])
                score = float(getattr(res, 'scores', [0.0])[0])

        logger.debug(f"AI orientation {stem}: label={label}, score={score:.3f}")

        # Xoay 180° nếu cần
        if '180' in str(label) and score > confidence_threshold:
            image = cv2.rotate(image, cv2.ROTATE_180)
            status = f"Xoay 180° (conf={score:.2f})"
            logger.info(f"fix_orientation_ai {stem}: {status}")
        else:
            status = f"Giữ nguyên (label={label}, conf={score:.2f})"

    except Exception as e:
        logger.error(f"fix_orientation_ai error: {e}")
        status = f"Lỗi AI fix: {str(e)}"

    # Lưu ảnh cuối cùng (sẽ là input cho OCR)
    if save_path is not None:
        os.makedirs(save_path, exist_ok=True)
        out_file = os.path.join(save_path, f"{stem}_fixed.png")
        cv2.imwrite(out_file, image)
        logger.debug(f"Saved fixed: {out_file}")

    return image, status


def preprocess_image(
    image: np.ndarray,
    stem: str = "image",
    save_dir: Optional[str] = None,
) -> Tuple[np.ndarray, dict]:
    """
    Pipeline tiền xử lý đầy đủ — dùng cho cả camera lẫn upload.

    Thứ tự:
      1. Deskew      — Nắn thẳng nghiêng ±15°
      2. Portrait    — Xoay 90° nếu nằm ngang
      3. AI fix 180° — Phát hiện lộn ngược bằng PP-LCNet

    Args:
        image: Ảnh BGR gốc.
        stem: Tên dùng khi lưu intermediate files.
        save_dir: Nếu không None, lưu ảnh sau mỗi bước vào thư mục này.

    Returns:
        (processed_image, info_dict)
        info_dict = {
          "deskew_angle": float,
          "portrait_rotated": bool,
          "ai_status": str
        }
    """
    info: dict = {}

    # Bước 1: Deskew
    image, angle = deskew(image)
    info["deskew_angle"] = round(angle, 2)
    if save_dir and angle != 0.0:
        os.makedirs(save_dir, exist_ok=True)
        cv2.imwrite(
            os.path.join(save_dir, f"{stem}_deskewed.png"), image
        )

    # Bước 2: Portrait
    image, rotated = force_portrait(image)
    info["portrait_rotated"] = rotated

    # Bước 3: AI fix 180°
    image, ai_status = fix_orientation_ai(image, save_path=save_dir, stem=stem)
    info["ai_status"] = ai_status

    logger.info(
        f"preprocess_image: deskew={angle:.1f}°, "
        f"portrait={rotated}, ai={ai_status}"
    )
    return image, info
