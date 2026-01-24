"""
YOLOv8 Segmentation Wrapper

Sử dụng YOLOv8n-seg (nano version) cho segmentation task.
Có thể thay thế bằng custom trained model (.pt file).
"""

from pathlib import Path
from typing import Union, List, Optional
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    raise ImportError("Chưa cài ultralytics. Chạy: pip install ultralytics")


class YOLOSegmentation:
    """
    Wrapper class cho YOLO Segmentation model.
    
    Hỗ trợ:
    - YOLOv8n-seg (pretrained)
    - Custom trained model (.pt file)
    
    Example:
        # Sử dụng pretrained model
        model = YOLOSegmentation()
        
        # Sử dụng custom model
        model = YOLOSegmentation("models/weights/best.pt")
        
        # Inference
        results = model.predict("image.jpg")
    """
    
    # Các phiên bản YOLO segmentation có sẵn
    AVAILABLE_MODELS = {
        "nano": "yolov8n-seg.pt",      # Nhanh nhất, nhẹ nhất
        "small": "yolov8s-seg.pt",     # Cân bằng
        "medium": "yolov8m-seg.pt",    # Trung bình
        "large": "yolov8l-seg.pt",     # Chính xác hơn
        "xlarge": "yolov8x-seg.pt",    # Chính xác nhất
    }
    
    def __init__(
        self, 
        model_path: Optional[str] = None,
        model_size: str = "nano",
        device: str = "auto"
    ):
        """
        Khởi tạo YOLO Segmentation model.
        
        Args:
            model_path: Đường dẫn tới file .pt (custom model).
                        Nếu None, sử dụng pretrained model.
            model_size: Kích thước model pretrained ("nano", "small", "medium", "large", "xlarge").
                        Chỉ áp dụng khi model_path=None.
            device: Device chạy model ("auto", "cpu", "cuda", "0", "1", ...).
        """
        self.device = device
        
        if model_path:
            # Sử dụng custom trained model
            self.model_path = Path(model_path)
            if not self.model_path.exists():
                raise FileNotFoundError(f"Không tìm thấy model: {model_path}")
            self.model = YOLO(str(self.model_path))
            self.model_name = self.model_path.name
        else:
            # Sử dụng pretrained model
            if model_size not in self.AVAILABLE_MODELS:
                raise ValueError(f"model_size phải là một trong: {list(self.AVAILABLE_MODELS.keys())}")
            self.model_name = self.AVAILABLE_MODELS[model_size]
            self.model = YOLO(self.model_name)
            self.model_path = None
        
        print(f"✅ Loaded model: {self.model_name}")
    
    def predict(
        self,
        source: Union[str, Path, np.ndarray, List],
        conf: float = 0.25,
        iou: float = 0.7,
        save: bool = False,
        save_dir: Optional[str] = None,
        show: bool = False,
        **kwargs
    ):
        """
        Chạy inference/prediction trên ảnh.
        
        Args:
            source: Ảnh đầu vào (path, numpy array, list of paths).
            conf: Ngưỡng confidence (0-1).
            iou: Ngưỡng IoU cho NMS (0-1).
            save: Lưu kết quả visualization.
            save_dir: Thư mục lưu kết quả.
            show: Hiển thị kết quả trên màn hình.
            **kwargs: Các tham số khác cho YOLO predict.
        
        Returns:
            results: Kết quả prediction từ YOLO.
        """
        predict_args = {
            "source": source,
            "conf": conf,
            "iou": iou,
            "save": save,
            "show": show,
            "device": self.device,
            **kwargs
        }
        
        if save_dir:
            predict_args["project"] = save_dir
        
        results = self.model.predict(**predict_args)
        return results
    
    def get_masks(self, results) -> List[Optional[np.ndarray]]:
        """
        Trích xuất segmentation masks từ kết quả prediction.
        
        Args:
            results: Kết quả từ method predict().
        
        Returns:
            List các mask arrays. None nếu không có mask.
        """
        masks = []
        for result in results:
            if result.masks is not None:
                # Lấy mask data dạng numpy array
                mask_data = result.masks.data.cpu().numpy()
                masks.append(mask_data)
            else:
                masks.append(None)
        return masks
    
    def get_boxes(self, results) -> List[Optional[np.ndarray]]:
        """
        Trích xuất bounding boxes từ kết quả prediction.
        
        Args:
            results: Kết quả từ method predict().
        
        Returns:
            List các box arrays [x1, y1, x2, y2, conf, class].
        """
        boxes = []
        for result in results:
            if result.boxes is not None:
                box_data = result.boxes.data.cpu().numpy()
                boxes.append(box_data)
            else:
                boxes.append(None)
        return boxes
    
    def get_class_names(self) -> dict:
        """
        Lấy danh sách class names của model.
        
        Returns:
            Dict mapping class_id -> class_name.
        """
        return self.model.names
    
    def __repr__(self):
        return f"YOLOSegmentation(model={self.model_name}, device={self.device})"


# Quick test khi chạy trực tiếp
if __name__ == "__main__":
    print("=" * 50)
    print("Testing YOLOSegmentation")
    print("=" * 50)
    
    # Test với pretrained model
    model = YOLOSegmentation(model_size="nano")
    print(f"Model: {model}")
    print(f"Classes: {model.get_class_names()}")
    print("\n✅ Test passed!")
