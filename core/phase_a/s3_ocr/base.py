"""
OCR Base Interface — Chuẩn chung cho OCR module.

OCR Engine: ocr_engine.py (PaddleOCR detect + VietOCR recognize)
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

import cv2
import numpy as np


@dataclass
class TextBlock:
    """Một dòng/vùng text đã được nhận diện."""
    text: str              # Nội dung text, ví dụ: "Paracetamol 500mg"
    confidence: float      # Độ tin cậy 0.0-1.0
    bbox: list             # [[x1,y1],[x2,y1],[x2,y2],[x1,y2]] — 4 góc vùng text


@dataclass
class OcrResult:
    """Kết quả OCR toàn bộ ảnh."""
    text_blocks: List[TextBlock] = field(default_factory=list)
    raw_text: str = ""             # Toàn bộ text nối lại thành chuỗi
    module_name: str = ""          # "paddle" hoặc "hybrid"
    input_type: str = ""           # "bbox" hoặc "mask"
    elapsed_ms: float = 0.0        # Thời gian xử lý (milliseconds)

    def __post_init__(self):
        if not self.raw_text and self.text_blocks:
            self.raw_text = "\n".join(b.text for b in self.text_blocks)


class BaseOCR(ABC):
    """Base class cho cả 2 module OCR."""

    @abstractmethod
    def extract(self, image: np.ndarray) -> OcrResult:
        """Nhận diện text từ ảnh. Trả về OcrResult."""
        ...

    def save_results(
        self,
        result: OcrResult,
        image: np.ndarray,
        stem: str,
        det_dir: str,
        txt_dir: str,
        json_dir: str
    ) -> None:
        """
        Lưu kết quả OCR ra 3 loại file:
        - det_dir/stem_det.png  : ảnh vẽ bbox text
        - txt_dir/stem.txt      : raw text (mỗi dòng 1 text block)
        - json_dir/stem.json    : dữ liệu đầy đủ (text + confidence + bbox)

        Args:
            result: OcrResult từ extract().
            image: Ảnh đã qua preprocessing (input của OCR).
            stem: Tên file gốc (không có extension), ví dụ "IMG_20260209_180410".
            det_dir: Thư mục lưu ảnh detection.
            txt_dir: Thư mục lưu raw text.
            json_dir: Thư mục lưu JSON.
        """
        for d in [det_dir, txt_dir, json_dir]:
            os.makedirs(d, exist_ok=True)

        # --- 1. Ảnh detection: vẽ bbox lên ảnh ---
        det_img = image.copy()
        for block in result.text_blocks:
            if block.bbox:
                pts = np.array(block.bbox, dtype=np.int32)
                cv2.polylines(det_img, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
                # Ghi text nhỏ phía trên bbox
                x, y = pts[0]
                label = f"{block.text[:20]} ({block.confidence:.2f})"
                cv2.putText(det_img, label, (x, max(y - 5, 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        cv2.imwrite(os.path.join(det_dir, f"{stem}_det.png"), det_img)

        # --- 2. Raw text file ---
        with open(os.path.join(txt_dir, f"{stem}.txt"), "w", encoding="utf-8") as f:
            f.write(f"# Module: {result.module_name} | Input: {result.input_type}\n")
            f.write(f"# Time: {result.elapsed_ms:.1f}ms | Blocks: {len(result.text_blocks)}\n")
            f.write("-" * 40 + "\n")
            for block in result.text_blocks:
                f.write(f"{block.text}\n")

        # --- 3. JSON file ---
        data = {
            "module": result.module_name,
            "input_type": result.input_type,
            "elapsed_ms": result.elapsed_ms,
            "block_count": len(result.text_blocks),
            "blocks": [
                {
                    "text": b.text,
                    "confidence": round(b.confidence, 4),
                    "bbox": b.bbox
                }
                for b in result.text_blocks
            ]
        }
        with open(os.path.join(json_dir, f"{stem}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
