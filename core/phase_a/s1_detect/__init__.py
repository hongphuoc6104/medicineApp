"""S1: YOLO detect + crop vùng đơn thuốc."""
from core.phase_a.s1_detect.detector import PrescriptionDetector
from core.phase_a.s1_detect.segmentation import crop_by_mask, crop_by_bbox
