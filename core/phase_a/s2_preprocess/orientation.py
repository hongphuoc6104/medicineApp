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

from core.phase_a.s2_preprocess.geometric import deskew  # noqa: F401 (re-exported)

logger = logging.getLogger(__name__)

# PaddleOCR lazy import (tránh tốn ~2.5s import khi skip AI fix)
PADDLE_AVAILABLE = None  # None = chưa check

# Singleton classifier — tránh load model mỗi lần gọi (~2-3s/lần)
_classifier_cache = None


def _get_classifier(model_path: Optional[str] = None):
    """Singleton DocImgOrientationClassification (lazy import)."""
    global _classifier_cache, PADDLE_AVAILABLE
    if _classifier_cache is not None:
        return _classifier_cache
    # Lazy import PaddleOCR
    if PADDLE_AVAILABLE is None:
        os.environ.setdefault("FLAGS_enable_pir_api", "0")
        try:
            from paddleocr import DocImgOrientationClassification
            PADDLE_AVAILABLE = True
        except Exception as e:
            PADDLE_AVAILABLE = False
            logger.warning(
                f"PaddleOCR orientation load fail: {e}. AI orientation disabled."
            )
    if not PADDLE_AVAILABLE:
        return None
    import paddle
    from paddleocr import DocImgOrientationClassification
    
    # Cỗ máy ưu tiên GPU: Thiết lập thiết bị ở mức hệ thống
    try:
        # Kiểm tra xem có thể dùng GPU không
        if paddle.device.is_compiled_with_cuda():
            paddle.set_device('gpu')
            device_status = "GPU"
        else:
            paddle.set_device('cpu')
            device_status = "CPU (No CUDA)"
        
        if model_path and os.path.exists(model_path):
            _classifier_cache = DocImgOrientationClassification(
                model_dir=model_path
            )
        else:
            _classifier_cache = DocImgOrientationClassification(
                model_name="PP-LCNet_x1_0_doc_ori"
            )
        logger.info(f"Mô hình AI: PP-LCNet — Đã nạp thành công [{device_status}]")
    except Exception as e:
        logger.warning(f"Device load lỗi ({e}), lùi về [CPU] mặc định...")
        paddle.set_device('cpu')
        if model_path and os.path.exists(model_path):
            _classifier_cache = DocImgOrientationClassification(
                model_dir=model_path
            )
        else:
            _classifier_cache = DocImgOrientationClassification(
                model_name="PP-LCNet_x1_0_doc_ori"
            )

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


def _ai_get_score(
    image: np.ndarray,
    max_width: int = 1000,
    model_path: Optional[str] = None,
) -> Tuple[str, float]:
    """
    Chỉ đo nhãn + điểm tự tin của AI classifier mà KHÔNG xoay ảnh.
    Dùng để so sánh confidence giữa nhiều phương án xoay.
    Returns: (label_str, score)
    """
    classifier = _get_classifier(model_path)
    if not PADDLE_AVAILABLE or classifier is None:
        return "0", 0.0
    try:
        h, w = image.shape[:2]
        if w > max_width:
            scale = max_width / float(w)
            check_img = cv2.resize(image, (0, 0), fx=scale, fy=scale,
                                   interpolation=cv2.INTER_LINEAR)
        else:
            check_img = image
        results = classifier.predict(check_img)
        if not results:
            return "0", 0.0
        res = results[0]
        if isinstance(res, dict) and 'label_names' in res:
            label = str(res['label_names'][0])
            score = float(res['scores'][0])
        else:
            label = str(getattr(res, 'label_names', ['0'])[0])
            score = float(getattr(res, 'scores', [0.0])[0])
        return label, score
    except Exception as e:
        logger.error(f"_ai_get_score error: {e}")
        return "0", 0.0


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
    # Khởi tạo classifier nếu chưa có
    classifier = _get_classifier(model_path)
    
    if not PADDLE_AVAILABLE or classifier is None:
        if save_path:
            os.makedirs(save_path, exist_ok=True)
            cv2.imwrite(os.path.join(save_path, f"{stem}_fixed.png"), image)
        return image, "PaddleOCR không có sẵn hoặc lỗi load model"

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

        logger.info(f"AI orientation raw: label={label}, score={score:.3f}")

        # Xoay theo góc được phát hiện (0°/90°/180°/270°)
        label_str = str(label)
        if score > confidence_threshold:
            if '180' in label_str:
                image = cv2.rotate(image, cv2.ROTATE_180)
                status = f"Xoay 180° (conf={score:.2f})"
                logger.info(f"fix_orientation_ai {stem}: {status}")
            elif '90' in label_str and '270' not in label_str:
                # Ảnh đang nằm ngang (90°) -> Xoay CCW để về đứng thẳng
                image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                status = f"Xoay 90° CCW (conf={score:.2f})"
                logger.info(f"fix_orientation_ai {stem}: {status}")
            elif '270' in label_str:
                # Ảnh đang nằm ngang (270°) -> Xoay CW để về đứng thẳng
                image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                status = f"Xoay 270° CW (conf={score:.2f})"
                logger.info(f"fix_orientation_ai {stem}: {status}")
            else:
                status = f"Giữ nguyên 0° (conf={score:.2f})"
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
    skip_ai_fix: bool = False,
) -> Tuple[np.ndarray, dict]:
    """
    Pipeline tiền xử lý — dùng cho cả camera lẫn upload.

    Thứ tự:
      1. Deskew      — Nắn thẳng nghiêng ±15°
      2. AI orientation — PP-LCNet phân loại 0°/90°/180°/270° và xoay đúng

    LƯU Ý: force_portrait() đã bị BỎ vì gây bug xoay sai ảnh YOLO-crop
    landscape (ảnh bảng thuốc nằm ngang bị xoay 90° → OCR chết).
    PP-LCNet tự detect đúng hướng chữ dù ảnh portrait hay landscape.

    Args:
        image: Ảnh BGR gốc.
        stem: Tên dùng khi lưu intermediate files.
        save_dir: Nếu không None, lưu ảnh sau mỗi bước.
        skip_ai_fix: Bỏ qua AI orientation (mặc định False — BẬT AI).

    Returns:
        (processed_image, info_dict)
        info_dict = {
          "deskew_angle": float,
          "portrait_rotated": bool,  # luôn False (force_portrait đã bỏ)
          "ai_status": str
        }
    """
    info: dict = {}

    # Bước 1: Tiền xử lý Deskew "Siêu Tự Động"
    # Nhờ thuật toán Modulo 90, tất cả hình ảnh bất kể bị xoay và nghiêng 
    # với bất cứ góc độ nào trên 360°, hệ thống sẽ tìm phương xoay TỐI ƯU NHẤT
    # để nắn tất cả các đường thẳng trong hình ảnh trở nên hoàn toàn vuông góc (thẳng đứng/nằm ngang).
    # Khắc phục hoàn toàn lỗi sai số > 15° và hiện tượng triệt tiêu nhau
    image_deskewed, angle = deskew(image)
    info["deskew_angle"] = round(angle, 2)

    if angle != 0.0:
        image = image_deskewed
        info["deskew_method"] = "hough_modulo_90_snap"
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            cv2.imwrite(
                os.path.join(save_dir, f"{stem}_deskewed.png"), image
            )
    else:
        info["deskew_method"] = "skipped"

    # force_portrait() ĐÃ BỎ
    info["portrait_rotated"] = False

    # Bước 2: AI orientation (PP-LCNet — 0°/90°/180°/270°)
    # Vì Bước 1 đã ĐẢM BẢO hình ảnh nằm dọc hoặc ngang tuyệt đối.
    # Nên giờ AI chỉ cần xoay 90/180/270 để đưa về 0° một cách cực kỳ tự tin và chuẩn xác.
    if skip_ai_fix:
        ai_status = "Skipped"
    else:
        image, ai_status = fix_orientation_ai(
            image, save_path=save_dir, stem=stem
        )
    info["ai_status"] = ai_status

    logger.info(
        f"preprocess_image: method={info.get('deskew_method')}, "
        f"deskew={info.get('deskew_angle')}°, ai={ai_status}"
    )
    return image, info
