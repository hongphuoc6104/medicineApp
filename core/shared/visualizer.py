import numpy as np 
import cv2
from ultralytics.engine.results import Results

def draw_bbox(image: np.ndarray, result: Results, color: tuple = (0, 255, 0)) -> np.ndarray:
    """
    Draw bounding box and confidence score on image.
    Args:
        image: BGR frame.
        result: A single YOLO results object.
        color: BGR color tuple for the box. Default: green.
    Returns:
        image with bounding box drawn.
    """
    output = image.copy()
    if result.boxes is None or len(result.boxes) == 0:
        return output

    x1, y1, x2, y2 = map(int, result.boxes.xyxy[0])
    confidence = float(result.boxes.conf[0])
    string = f"prescription {confidence:.2f}"
    cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
    cv2.putText(output, string, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    return output

def draw_mask_overlay(image: np.ndarray, result: Results, alpha: float = 0.4) -> np.ndarray:
    """
    Draw semi-transparent green overlay on detected mask area.
    Args:
        image: BGR frame.
        result: A single YOLO results object. 
        alpha: Transparency of overlay (0=invisible, 1=solid). Default = 0.4. 
    Returns:
        Image: with mask overlay drawn. 
    """
    output = image.copy()
    if result.masks is None:
        return output
    
    mask = result.masks.data[0].cpu().numpy()
    mask = cv2.resize(mask, (image.shape[1], image.shape[0]))
    mask_3ch = np.stack([mask]*3, axis=-1)

    color_player = np.zeros_like(output)
    color_player[:] = (0, 255, 0)
    output = np.where(mask_3ch == 1, (output * (1 - alpha) + color_player * alpha).astype(np.uint8), output)

    return output

def draw_polygon_points(image: np.ndarray, result: Results, color: tuple = [0,0,255]) -> np.ndarray:
    """
    Draw polygon border on the detected prescription.
    Args:
        image: BGR frame.
        result: A single YOLO result object.
        color: BGR color for polygon line. Default red.
    Returns: 
        Image with polygon drawn.
    """
    output = image.copy()
    if result.masks is None:
        return output

    points = result.masks.xy[0]
    pts = points.reshape((-1, 1, 2)).astype(np.int32)
    cv2.polylines(output, [pts], isClosed=True, color=color, thickness=2)
    return output
