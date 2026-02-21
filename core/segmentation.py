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
    
def crop_by_mask(image: np.ndarray, result: Results) ->np.ndarray:
    """
    Crop prescription using segmentation mask. Background = black.
    Args:
        image: Original BGR frame from camera/file.
        result: A single YOLO Result object. 
    Returns: 
        Cropped image with black background. None if no mask.
    """
    if result.masks is None:
        return None

    mask = result.masks.data[0].cpu().numpy()
    mask_resize = cv2.resize(mask, (image.shape[1], image.shape[0]))
    mask_3ch = np.stack([mask_resize]*3, axis=-1)
    masked_image = (image * mask_3ch).astype(np.uint8)
    x1, y1, x2, y2 = map(int, result.boxes.xyxy[0])

    padding = CROP_PADDING
    x1 = max(0, x1 - padding)   # không âm
    y1 = max(0, y1 - padding)   # không âm
    x2 = min(image.shape[1], x2 + padding)   # không vượt chiều rộng
    y2 = min(image.shape[0], y2 + padding)   # không vượt chiều cao

    return masked_image[y1:y2, x1:x2]

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