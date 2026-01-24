"""
Test YOLO Segmentation Model
"""
import pytest
import sys
from pathlib import Path

# Thêm root directory vào path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


class TestYOLOModel:
    """Test cases cho YOLOSegmentation class"""
    
    def test_import_model(self):
        """Test import YOLOSegmentation"""
        from models.yolo_segmentation import YOLOSegmentation
        assert YOLOSegmentation is not None
    
    def test_available_models(self):
        """Test danh sách models có sẵn"""
        from models.yolo_segmentation import YOLOSegmentation
        expected_sizes = ["nano", "small", "medium", "large", "xlarge"]
        for size in expected_sizes:
            assert size in YOLOSegmentation.AVAILABLE_MODELS
    
    def test_load_pretrained_model(self):
        """Test load pretrained model (requires ultralytics)"""
        try:
            from models.yolo_segmentation import YOLOSegmentation
            model = YOLOSegmentation(model_size="nano")
            assert model is not None
            assert "nano" in model.model_name.lower() or "n-seg" in model.model_name.lower()
        except ImportError:
            pytest.skip("ultralytics not installed")
    
    def test_get_class_names(self):
        """Test lấy class names từ model"""
        try:
            from models.yolo_segmentation import YOLOSegmentation
            model = YOLOSegmentation(model_size="nano")
            names = model.get_class_names()
            assert isinstance(names, dict)
            assert len(names) > 0
        except ImportError:
            pytest.skip("ultralytics not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
