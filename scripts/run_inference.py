#!/usr/bin/env python3
"""
Quick Run Script - YOLO Segmentation

Usage:
    python scripts/run_inference.py                    # Test với pretrained model
    python scripts/run_inference.py --help             # Xem hướng dẫn
"""

import sys
from pathlib import Path

# Thêm root directory vào path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from inference.predict import main

if __name__ == "__main__":
    main()
