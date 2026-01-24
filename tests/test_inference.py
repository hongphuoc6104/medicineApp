"""
Test Inference Module
"""
import pytest
import sys
from pathlib import Path

# Thêm root directory vào path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


class TestInference:
    """Test cases cho module inference"""
    
    def test_import_predict(self):
        """Test import predict module"""
        from inference.predict import run_inference
        assert run_inference is not None
    
    def test_run_inference_no_source(self):
        """Test chạy inference không có source"""
        # This should fail gracefully
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
