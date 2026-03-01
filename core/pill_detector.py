"""
pill_detector.py — Pill Localization bằng Faster R-CNN.

Dùng model FRCNN từ zero_pima_best.pth (key: model_loc) để detect
vị trí từng viên thuốc trong ảnh.

Ví dụ:
    from core.pill_detector import PillDetector
    detector = PillDetector()
    detections = detector.detect("pill_image.jpg")
    # detections = [{"bbox": [x1,y1,x2,y2], "score": 0.95}, ...]
"""

import logging
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
import torch
import torchvision
from torchvision.models.detection.faster_rcnn import (
    FastRCNNPredictor,
    FasterRCNN_MobileNet_V3_Large_FPN_Weights,
)

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = str(
    Path(__file__).parent.parent / "models" / "weights" / "zero_pima_best.pth"
)


class PillDetector:
    """
    Faster R-CNN pill detector.

    Args:
        weights_path: Path to zero_pima_best.pth (or legacy standalone)
        score_thresh: Confidence threshold (default 0.5)
        device: "cuda" or "cpu"
    """

    def __init__(
        self,
        weights_path: str = DEFAULT_WEIGHTS,
        score_thresh: float = 0.5,
        device: Optional[str] = None,
    ):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.score_thresh = score_thresh
        self._model = None
        self._weights_path = weights_path
        logger.info(f"PillDetector init (device={device}, thresh={score_thresh})")

    def _load_model(self):
        if self._model is not None:
            return
        model = torchvision.models.detection.fasterrcnn_mobilenet_v3_large_fpn(
            weights=FasterRCNN_MobileNet_V3_Large_FPN_Weights.DEFAULT
        )
        in_features = model.roi_heads.box_predictor.cls_score.in_features
        model.roi_heads.box_predictor = FastRCNNPredictor(in_features, 2)

        if Path(self._weights_path).exists():
            state = torch.load(
                self._weights_path, map_location=self.device,
                weights_only=False,
            )
            # Handle Zero-PIMA combined checkpoint (model_loc key)
            if "model_loc" in state:
                state = state["model_loc"]
            elif "model_state_dict" in state:
                state = state["model_state_dict"]
            elif "loc_state_dict" in state:
                state = state["loc_state_dict"]
            model.load_state_dict(state)
            logger.info(f"Loaded weights: {self._weights_path}")
        else:
            logger.warning(
                f"Weights not found: {self._weights_path}\n"
                "Running with random weights (for testing only)"
            )

        model.to(self.device)
        model.eval()
        self._model = model

    def detect(
        self,
        image,
        score_thresh: Optional[float] = None,
    ) -> List[dict]:
        """
        Detect pills in image.

        Args:
            image: numpy array (BGR from cv2) or str path to image file
            score_thresh: Override default threshold

        Returns:
            List of dicts:
            [
                {
                    "bbox":  [x1, y1, x2, y2],   # pixel coords
                    "score": 0.95,                # confidence
                    "label": 1,                   # always 1 (pill)
                },
                ...
            ]
        """
        self._load_model()
        thresh = score_thresh or self.score_thresh

        # Load image
        if isinstance(image, str):
            image = cv2.imread(image)
        if image is None:
            logger.error("Image is None")
            return []

        # BGR → RGB → tensor [0,1]
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        tensor = tensor.to(self.device)

        with torch.no_grad():
            outputs = self._model([tensor])

        result = outputs[0]
        boxes  = result["boxes"].cpu().numpy()
        scores = result["scores"].cpu().numpy()
        labels = result["labels"].cpu().numpy()

        detections = []
        for box, score, label in zip(boxes, scores, labels):
            if score >= thresh:
                detections.append({
                    "bbox":  [int(x) for x in box],  # [x1,y1,x2,y2]
                    "score": round(float(score), 4),
                    "label": int(label),
                })

        logger.info(
            f"PillDetector: {len(detections)} pills detected "
            f"(thresh={thresh}, total_proposals={len(boxes)})"
        )
        return detections

    def draw(
        self,
        image: np.ndarray,
        detections: List[dict],
        color: tuple = (0, 255, 0),
    ) -> np.ndarray:
        """
        Vẽ bounding box lên ảnh.

        Returns:
            Ảnh BGR với bbox đã vẽ.
        """
        vis = image.copy()
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            score = det["score"]
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                vis, f"pill {score:.2f}",
                (x1, max(y1 - 5, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
            )
        return vis
