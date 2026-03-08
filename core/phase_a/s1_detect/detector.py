import numpy as np
from ultralytics import YOLO
from core.config import MODEL_PATH, CONF_THRESHOLD

class PrescriptionDetector:
    def __init__(self, model_path: str = MODEL_PATH) -> None:
        """
        Load the YOLOv11 segmentation model. 
        Args:
            model_path: Path to the .pt weight file.
        """
        self.model = YOLO(model_path)

    def predict(self, frame: np.ndarray) -> list:
        """
        Run inference on a single image frame.
        Args:
            frame: A BGR image as a numpy array (from cv2).
        Returns:
            Yolo results list. Empty list [] if no detection.
        """
        result = self.model.predict(source=frame, conf=CONF_THRESHOLD, verbose=False)
        return result

