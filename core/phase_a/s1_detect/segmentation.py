import numpy as np
import cv2 
from ultralytics.engine.results import Results
from core.config import CROP_PADDING

def extract_polygon(result: Results) -> list[float]:
    """
    Extract flat polygon points from the first detect object.
    Args:
        result: A single YOLO result object.
    Returns: 
        Flat list [x1, y1, x2, y2, ...] Empty list if no mask.
    """
    if result.masks is None:
        return []

    return result.masks.xy[0].flatten().tolist()
    
def crop_by_mask(image: np.ndarray, result: Results):
    """
    Crop prescription using convex hull of segmentation mask.
    - Tính convex hull (đa giác lồi nhỏ nhất) từ polygon YOLO
    - Tô đen CHỈ phần nằm NGOÀI convex hull
    - Giữ nguyên 100% pixel bên trong, không bị lõm/xóa đen nội dung
    Args:
        image: Original BGR frame from camera/file.
        result: A single YOLO Result object. 
    Returns: 
        Tuple (cropped_image, (x1, y1)) where (x1, y1) is the
        crop offset in original image coordinates.
        Returns (None, (0, 0)) if no mask.
    """
    if result.masks is None:
        return None, (0, 0)

    # Lấy polygon gốc từ YOLO (tọa độ pixel thực trên ảnh gốc)
    polygon_xy = result.masks.xy[0]  # shape: (N, 2)
    if len(polygon_xy) < 3:
        return None, (0, 0)

    # Tính convex hull → đa giác lồi nhỏ nhất bao quanh tất cả điểm
    # Loại bỏ hoàn toàn các phần lõm/khuyết bên trong
    pts = polygon_xy.astype(np.float32).reshape(-1, 1, 2)
    hull = cv2.convexHull(pts)
    hull_int = hull.astype(np.int32)

    # Copy ảnh gốc để không làm thay đổi ảnh đầu vào
    output = image.copy()

    # Tạo mask từ convex hull trên kích thước ảnh gốc (full resolution)
    hull_mask = np.zeros(image.shape[:2], dtype=np.uint8)
    cv2.fillPoly(hull_mask, [hull_int.reshape(-1, 2)], 255)

    # Tô đen phần NGOÀI convex hull
    output[hull_mask == 0] = 0

    # Tính bounding box từ convex hull + padding
    hx, hy, hw, hh = cv2.boundingRect(hull_int.reshape(-1, 2))
    padding = CROP_PADDING
    x1 = max(0, hx - padding)
    y1 = max(0, hy - padding)
    x2 = min(image.shape[1], hx + hw + padding)
    y2 = min(image.shape[0], hy + hh + padding)

    return output[y1:y2, x1:x2], (x1, y1)

def crop_by_bbox(image: np.ndarray, result: Results) -> np.ndarray:
    """
    Crop prescription using bounding box rectangle only.
    Args:
        image: Original BGR frame.
        result: A single YOLO Result object. 
    Returns:
        Simple rectangle crop. None if no detection.
    """ 
    if result.boxes is None or len(result.boxes) == 0:
        return None

    x1, y1, x2, y2 = map(int, result.boxes.xyxy[0])

    return image[y1:y2, x1:x2]