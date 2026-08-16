"""Image preprocessing and conditional rectification module for RxIE.

Implements:
1. 90/180/270 orientation normalization based on RAW OCR median angles / EXIF.
2. Small-angle deskew (~2°-15°).
3. Document quad detection and perspective rectification.
4. Margin-aware document cropping.
"""

from dataclasses import dataclass
import statistics
import cv2
import numpy as np


@dataclass(frozen=True)
class TransformMetadata:
    orientation_rotation: int  # 0, 90, 180, 270
    skew_angle: float
    deskew_applied: bool
    document_detected: bool
    document_confidence: float
    perspective_applied: bool
    cropped: bool


def detect_dominant_orientation_from_ocr(ocr_data: dict) -> int:
    """Estimates whether the image needs 0, 90, 180, or 270 degree rotation from line angles."""
    blocks = ocr_data.get("blocks", [])
    angles = []
    for b in blocks:
        for l in b.get("lines", []):
            angle = l.get("angle")
            conf = l.get("confidence", 1.0)
            if angle is not None and conf >= 0.3 and len(l.get("text", "")) >= 2:
                angles.append(angle)

    if not angles or len(angles) < 2:
        return 0

    med_angle = statistics.median(angles)
    norm_angle = (med_angle % 360 + 360) % 360

    if 45 <= norm_angle < 135:
        return 90
    elif 135 <= norm_angle < 225:
        return 180
    elif 225 <= norm_angle < 315:
        return 270
    return 0


def detect_skew_angle_from_ocr(ocr_data: dict, orientation: int = 0) -> float:
    """Estimates small skew angle (2°-15°) after orientation normalization."""
    blocks = ocr_data.get("blocks", [])
    angles = []
    for b in blocks:
        for l in b.get("lines", []):
            angle = l.get("angle")
            conf = l.get("confidence", 1.0)
            if angle is not None and conf >= 0.4 and len(l.get("text", "")) >= 2:
                # normalize angle relative to orientation
                rel_angle = angle - orientation
                while rel_angle > 180:
                    rel_angle -= 360
                while rel_angle < -180:
                    rel_angle += 360
                angles.append(rel_angle)

    if not angles or len(angles) < 2:
        return 0.0

    med_angle = statistics.median(angles)
    return float(med_angle)


def rotate_orthogonal(image: np.ndarray, degrees: int) -> np.ndarray:
    """Rotates image by 0, 90, 180, or 270 degrees without interpolation loss."""
    if degrees == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif degrees == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif degrees == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def deskew_affine(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotates image by a small angle (-angle to correct)."""
    if abs(angle) < 1.0:
        return image
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos = np.abs(m[0, 0])
    sin = np.abs(m[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    m[0, 2] += (new_w / 2) - center[0]
    m[1, 2] += (new_h / 2) - center[1]
    return cv2.warpAffine(
        image,
        m,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def order_points(pts: np.ndarray) -> np.ndarray:
    """Orders 4 points: [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def detect_document_quad(image: np.ndarray) -> tuple[np.ndarray | None, float]:
    """Detects quadrilateral document boundaries and returns (ordered_pts, confidence)."""
    h, w = image.shape[:2]
    img_area = h * w
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 30, 120)

    # Dilate slightly to close gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edged = cv2.dilate(edged, kernel, iterations=1)

    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > 0.35 * img_area:
                confidence = min(1.0, area / (img_area * 0.95))
                pts = approx.reshape(4, 2)
                return order_points(pts), confidence

    return None, 0.0


def perspective_rectify(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Applies four-point perspective transformation."""
    tl, tr, br, bl = pts
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = max(int(height_a), int(height_b))

    dst = np.array(
        [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
        dtype="float32",
    )
    m = cv2.getPerspectiveTransform(pts, dst)
    return cv2.warpPerspective(
        image,
        m,
        (max_w, max_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def process_image_pipeline(
    image: np.ndarray,
    ocr_raw_data: dict | None = None,
    enable_rotation: bool = True,
    enable_perspective: bool = True,
    enable_deskew: bool = True,
) -> tuple[np.ndarray, TransformMetadata]:
    """Applies conditional transformation pipeline based on geometric signals."""
    current_img = image.copy()
    orientation = 0
    skew_angle = 0.0
    deskew_applied = False
    doc_detected = False
    doc_conf = 0.0
    persp_applied = False
    cropped = False

    # 1. Orientation check
    if enable_rotation and ocr_raw_data:
        orientation = detect_dominant_orientation_from_ocr(ocr_raw_data)
        if orientation != 0:
            current_img = rotate_orthogonal(current_img, orientation)

    # 2. Document detection & Perspective
    if enable_perspective:
        quad_pts, conf = detect_document_quad(current_img)
        doc_conf = conf
        if quad_pts is not None and conf >= 0.65:
            doc_detected = True
            current_img = perspective_rectify(current_img, quad_pts)
            persp_applied = True
            cropped = True

    # 3. Deskew check
    if enable_deskew and ocr_raw_data:
        skew_angle = detect_skew_angle_from_ocr(ocr_raw_data, orientation)
        if 2.0 <= abs(skew_angle) <= 15.0:
            current_img = deskew_affine(current_img, -skew_angle)
            deskew_applied = True

    meta = TransformMetadata(
        orientation_rotation=orientation,
        skew_angle=skew_angle,
        deskew_applied=deskew_applied,
        document_detected=doc_detected,
        document_confidence=doc_conf,
        perspective_applied=persp_applied,
        cropped=cropped,
    )
    return current_img, meta
