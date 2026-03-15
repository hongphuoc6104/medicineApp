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

        # --- 1. Ảnh detection: vẽ bbox và text ---
        from PIL import Image, ImageDraw, ImageFont
        
        # Chuyển từ BGR (OpenCV) sang RGB (PIL)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(image_rgb)
        draw = ImageDraw.Draw(pil_img)
        
        # Tìm font hỗ trợ tiếng Việt
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "Arial.ttf" # Fallback
        ]
        font = None
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, 20) # Font size 20 tương ứng font_scale~0.7
                    break
                except:
                    continue
        if font is None:
            font = ImageFont.load_default()

        # Vẽ từng block
        for block in result.text_blocks:
            if block.bbox:
                pts = np.array(block.bbox, dtype=np.int32)
                # OpenCV dùng để vẽ polyline cho nhanh và nét
                # Ta vẫn có thể vẽ bằng PIL nhưng draw.polygon yêu cầu list phẳng
                # Để giữ các nét vẽ cũ, ta sẽ vẽ bbox bằng cv2 trước rồi mới đưa qua PIL ghi chữ
                # Hoặc vẽ thẳng bằng PIL ở đây:
                flat_pts = [tuple(p) for p in block.bbox]
                draw.polygon(flat_pts, outline=(255, 0, 0), width=3)
                
                # Ghi text tiếng Việt
                x, y = block.bbox[0]
                label = f"{block.text[:30]}"
                
                # Tính toán kích thước nền text
                try:
                    # PIL mới dùng getbbox, PIL cũ dùng textsize
                    if hasattr(draw, 'textbbox'):
                        left, top, right, bottom = draw.textbbox((x, y), label, font=font)
                        w_text = right - left
                        h_text = bottom - top
                    else:
                        w_text, h_text = draw.textsize(label, font=font)
                except:
                    w_text, h_text = len(label)*12, 20
                
                # Vẽ nền đỏ cho chữ
                draw.rectangle([x, y - h_text - 5, x + w_text + 4, y], fill=(255, 0, 0))
                # Ghi chữ trắng
                draw.text((x + 2, y - h_text - 4), label, font=font, fill=(255, 255, 255))

        # Chuyển ngược lại BGR để cv2.imwrite
        final_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        cv2.imwrite(os.path.join(det_dir, f"{stem}_det.png"), final_img)

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
