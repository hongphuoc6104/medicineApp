"""
Tests cho 7 bugs Phase A đã fix.

VĐ1: _crop_polygon() perspective transform
VĐ4: NER key consistency (bbox vs box)
VĐ5: Log message fix
VĐ6: CONF_THRESHOLD
"""
import numpy as np
import pytest


# ── VĐ1: test _crop_polygon perspective transform ──

class TestCropPolygon:
    """Test _crop_polygon with perspective transform."""

    def test_normal_rectangle(self):
        """4-point rectangle → perspective crop succeeds."""
        from core.phase_a.s3_ocr.ocr_engine import _crop_polygon
        img = np.ones((200, 400, 3), dtype=np.uint8) * 128
        poly = [[10, 10], [100, 10], [100, 50], [10, 50]]
        result = _crop_polygon(img, poly)
        assert result is not None
        assert result.shape[0] > 0  # height > 0
        assert result.shape[1] > 0  # width > 0

    def test_rotated_text(self):
        """Rotated polygon → perspective crop produces proper shape."""
        from core.phase_a.s3_ocr.ocr_engine import _crop_polygon
        img = np.ones((200, 400, 3), dtype=np.uint8) * 128
        # Rotated ~15 degrees
        poly = [[20, 30], [120, 15], [125, 55], [25, 70]]
        result = _crop_polygon(img, poly)
        assert result is not None
        assert result.shape[0] > 0
        assert result.shape[1] > 0

    def test_non_4_point_polygon(self):
        """Non-4-point polygon → falls back to boundingRect."""
        from core.phase_a.s3_ocr.ocr_engine import _crop_polygon
        img = np.ones((200, 400, 3), dtype=np.uint8) * 128
        poly = [[10, 10], [100, 10], [100, 50]]  # 3 points
        result = _crop_polygon(img, poly)
        assert result is not None  # Should still work via fallback

    def test_zero_area_polygon(self):
        """Zero-area polygon (all same point) → returns small padding region or None."""
        from core.phase_a.s3_ocr.ocr_engine import _crop_polygon
        img = np.ones((200, 400, 3), dtype=np.uint8) * 128
        poly = [[10, 10], [10, 10], [10, 10], [10, 10]]
        result = _crop_polygon(img, poly)
        # warpPerspective may return a tiny padding-only image,
        # which is acceptable (VietOCR will reject it anyway)
        if result is not None:
            assert result.shape[0] <= 20  # only padding
            assert result.shape[1] <= 20

    def test_empty_input(self):
        """Empty polygon list → returns None."""
        from core.phase_a.s3_ocr.ocr_engine import _crop_polygon
        img = np.ones((200, 400, 3), dtype=np.uint8) * 128
        result = _crop_polygon(img, [])
        assert result is None


# ── VĐ2+VĐ3: test pipeline fallback + preprocess ──

class TestPipelineFallback:
    """Test YOLO fallback and preprocess integration."""

    def test_scan_with_skip_yolo_no_crash(self):
        """Pipeline doesn't crash with dummy image + skip_yolo."""
        from core.pipeline import MedicinePipeline
        pipe = MedicinePipeline()
        # Tiny image — OCR sẽ không tìm thấy text
        dummy = np.zeros((50, 50, 3), dtype=np.uint8)
        result = pipe.scan_prescription(dummy, skip_yolo=True)
        # Phải trả dict, không được crash
        assert isinstance(result, dict)
        # Có thể trả error "OCR found no text" — đó là OK
        assert "error" in result or "medications" in result


# ── VĐ4: NER key consistency ──

class TestNerKeys:
    """Test NER extractor returns 'bbox' key."""

    def test_ner_returns_bbox_key(self):
        """NER classify() output should have 'bbox' key, not 'box'."""
        from core.phase_a.s5_classify.ner_extractor import NerExtractor
        extractor = NerExtractor()
        blocks = [
            {"text": "Paracetamol 500mg", "bbox": [10, 20, 100, 40]},
        ]
        results = extractor.classify(blocks)
        assert len(results) > 0
        # Must have "bbox" key
        assert "bbox" in results[0]
        # Must NOT have "box" key
        assert "box" not in results[0]

    def test_ner_reads_box_input(self):
        """NER should also read 'box' key from input (backward compat)."""
        from core.phase_a.s5_classify.ner_extractor import NerExtractor
        extractor = NerExtractor()
        blocks = [
            {"text": "Paracetamol", "box": [10, 20, 100, 40]},
        ]
        results = extractor.classify(blocks)
        assert results[0]["bbox"] == [10, 20, 100, 40]


# ── VĐ6: CONF_THRESHOLD ──

class TestConfig:
    """Test config values are reasonable."""

    def test_conf_threshold_is_reasonable(self):
        """CONF_THRESHOLD should be between 0.3 and 0.7."""
        from core.config import CONF_THRESHOLD
        assert 0.3 <= CONF_THRESHOLD <= 0.7, (
            f"CONF_THRESHOLD={CONF_THRESHOLD} is too "
            f"{'high' if CONF_THRESHOLD > 0.7 else 'low'}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
