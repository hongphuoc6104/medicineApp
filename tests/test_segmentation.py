import numpy as np
import pytest
from core.segmentation import extract_polygon, crop_by_mask, crop_by_bbox

# ==========================================
# 1. MOCK OBJECTS (Fake YOLO Results)
# ==========================================

class MockTensor:
    """Giả lập một PyTorch Tensor cơ bản"""
    def __init__(self, data_array):
        self.data_array = data_array

    def cpu(self):
        return self  

    def numpy(self):
        return self.data_array

class MockMasks:
    """Giả lập result.masks của YOLO"""
    def __init__(self, xy_points, mask_data):
        self.xy = [np.array(xy_points)]
        self.data = [MockTensor(np.array(mask_data))]


class MockBoxes:
    """Giả lập result.boxes của YOLO"""
    def __init__(self, xyxy, conf=0.95):
        self.xyxy = np.array([xyxy])
        self.conf = np.array([conf])

    def __len__(self):
        return len(self.xyxy)

class MockResult:
    """Thùng chứa gom Masks và Boxes lại thành 1 YOLO Result giả"""
    def __init__(self, masks=None, boxes=None):
        self.masks = masks
        self.boxes = boxes


def test_extract_polygon_no_mask():
    """Edge Case: YOLO không tìm thấy mask nào (masks=None)"""

    fake_result = MockResult(masks=None)
    
    polygon = extract_polygon(fake_result)
    
    assert polygon == [], "Nên trả về [] khi masks là None"

def test_extract_polygon_with_mask():
    """Happy Path: YOLO tìm thấy mask hợp lệ"""

    fake_points = [[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]]
    fake_masks = MockMasks(xy_points=fake_points, mask_data=np.zeros((100, 100)))
    fake_result = MockResult(masks=fake_masks)
    

    polygon = extract_polygon(fake_result)
    

    expected = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    assert polygon == expected, f"Logic flatten sai. Got: {polygon}"
    assert isinstance(polygon, list), "Phải trả về kiểu list"


def test_crop_by_bbox_no_boxes():
    """Edge Case: YOLO không tìm thấy hộp nào (boxes=None)"""
    
    fake_image = np.zeros((100, 100, 3), dtype=np.uint8) 
    fake_result = MockResult(boxes=None)                
    
    crop = crop_by_bbox(fake_image, fake_result)         
    
    assert crop is None, "Phải trả về None khi không có detection" 

def test_crop_by_bbox_with_detection():
    """Happy Path: Cắt khung chữ nhật cơ bản"""

    fake_image = np.zeros((100, 100, 3), dtype=np.uint8)
    fake_boxes = MockBoxes(xyxy=[10, 20, 60, 80])
    fake_result = MockResult(boxes=fake_boxes)
    
    crop = crop_by_bbox(fake_image, fake_result)         
    
    assert crop.shape == (60, 50, 3), "Kích thước ảnh crop bằng Bounding Box đang bị sai logic"


def test_crop_by_mask_no_mask():
    """Edge Case: YOLO không tìm thấy mask"""
    fake_image = np.zeros((100, 100, 3), dtype=np.uint8)
    fake_result = MockResult(masks=None)
    
    crop = crop_by_mask(fake_image, fake_result)
    assert crop is None

def test_crop_by_mask_with_detection():
    """Happy Path: Phủ mask thành màu đen 2 bên và cắt có padding = 20"""
    fake_image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    fake_mask_data = np.zeros((100, 100))
    fake_masks = MockMasks(xy_points=[[0,0]], mask_data=fake_mask_data)
    fake_boxes = MockBoxes(xyxy=[30, 40, 60, 70])
    
    fake_result = MockResult(masks=fake_masks, boxes=fake_boxes)
    
    crop = crop_by_mask(fake_image, fake_result)         # Act
    
    assert crop.shape == (70, 70, 3), "Kích thước ảnh crop theo Mask + Padding bị sai!"


def test_crop_by_bbox_empty_boxes():
    """Edge Case: boxes tồn tại nhưng có 0 phần tử (len == 0)"""
    fake_image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Boxes tồn tại nhưng rỗng
    fake_boxes = MockBoxes(xyxy=[10, 20, 60, 80])
    fake_boxes.xyxy = np.array([])          # Ghi đè thành mảng rỗng
    
    fake_result = MockResult(boxes=fake_boxes)
    crop = crop_by_bbox(fake_image, fake_result)
    
    assert crop is None, "Phải trả về None khi boxes rỗng"


def test_crop_by_mask_padding_clamp():
    """Edge Case: bbox gần góc ảnh → padding phải bị giới hạn (clamped)"""
    fake_image = np.zeros((100, 100, 3), dtype=np.uint8)
    fake_mask_data = np.zeros((100, 100))
    fake_masks = MockMasks(xy_points=[[0, 0]], mask_data=fake_mask_data)
    
    # Bbox sát góc trên-trái: x1=5, y1=5. Padding 20 sẽ âm → phải clamp thành 0
    fake_boxes = MockBoxes(xyxy=[5, 5, 50, 50])
    fake_result = MockResult(masks=fake_masks, boxes=fake_boxes)
    
    crop = crop_by_mask(fake_image, fake_result)
    
    # x1 = max(0, 5-20) = 0. y1 = max(0, 5-20) = 0
    # x2 = min(100, 50+20) = 70. y2 = min(100, 50+20) = 70
    # Shape = (y2-y1, x2-x1, 3) = (70, 70, 3)
    assert crop.shape == (70, 70, 3), "Clamping logic bị bỏ qua, padding vượt biên ảnh!"
