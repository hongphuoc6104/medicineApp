import numpy as np
import pytest
from rxie.image_transforms import (
    deskew_affine,
    detect_dominant_orientation_from_ocr,
    detect_skew_angle_from_ocr,
    process_image_pipeline,
    rotate_orthogonal,
)


def test_detect_orientation():
    # Simulated OCR data with dominant 90 degree angle
    mock_ocr = {
        "blocks": [
            {
                "lines": [
                    {"text": "Line 1 Test", "angle": 89.5, "confidence": 0.8},
                    {"text": "Line 2 Test", "angle": 91.0, "confidence": 0.9},
                    {"text": "Line 3 Test", "angle": 90.2, "confidence": 0.85},
                ]
            }
        ]
    }
    rot = detect_dominant_orientation_from_ocr(mock_ocr)
    assert rot == 90


def test_detect_skew():
    mock_ocr = {
        "blocks": [
            {
                "lines": [
                    {"text": "Prescription Name", "angle": 5.4, "confidence": 0.8},
                    {"text": "Usage Instruction", "angle": 5.2, "confidence": 0.9},
                    {"text": "Quantity Count", "angle": 5.6, "confidence": 0.85},
                ]
            }
        ]
    }
    skew = detect_skew_angle_from_ocr(mock_ocr, orientation=0)
    assert abs(skew - 5.4) < 0.1


def test_rotate_and_deskew():
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    rot_img = rotate_orthogonal(img, 90)
    assert rot_img.shape[:2] == (200, 100)

    deskewed = deskew_affine(img, 5.0)
    assert deskewed.shape[0] > 0 and deskewed.shape[1] > 0


def test_process_pipeline():
    img = np.ones((400, 300, 3), dtype=np.uint8) * 255
    mock_ocr = {
        "blocks": [
            {
                "lines": [
                    {"text": "Prescription Line 1", "angle": 0.0, "confidence": 0.9},
                    {"text": "Prescription Line 2", "angle": 0.0, "confidence": 0.9},
                    {"text": "Prescription Line 3", "angle": 0.0, "confidence": 0.9},
                ]
            }
        ]
    }
    out_img, meta = process_image_pipeline(img, ocr_raw_data=mock_ocr)
    assert meta.orientation_rotation == 0
    assert not meta.deskew_applied
