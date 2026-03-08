# Phase A — Quét Đơn Thuốc

4 bước tuần tự. Output bước N là input bước N+1.

| # | Module | Input | Output |
|---|--------|-------|--------|
| s1 | `s1_detect/` | Ảnh gốc (BGR) | Ảnh crop vùng đơn thuốc |
| s2 | `s2_preprocess/` | Ảnh crop | Ảnh deskew + fixed orientation |
| s3 | `s3_ocr/` | Ảnh processed | List text blocks `[{text, bbox, conf}]` |
| s4 | `s5_classify/` | Text blocks | Blocks với label `drugname`/`other` (PhoBERT NER) |

> **Archived:** `s4_grouping/` (merge same-line) — đã bỏ, NER xử lý trực tiếp OCR output.

Chi tiết kỹ thuật từng bước: xem docstring trong file `.py` tương ứng.
