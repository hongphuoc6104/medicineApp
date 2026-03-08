# Phase B — Xác Minh Viên Thuốc

2 bước. Yêu cầu: kết quả Phase A (prescription blocks) + ảnh viên thuốc.

| # | Module | Input | Output |
|---|--------|-------|--------|
| s1 | `s1_pill_detect/` | Ảnh viên thuốc | Bounding boxes các viên thuốc |
| s2 | `s2_match/` | Pill BBoxes + Prescription blocks | Pill ↔ Drug matching |

> **Lưu ý:** Full contrastive matching yêu cầu `roi_heads.py` đã patch.
