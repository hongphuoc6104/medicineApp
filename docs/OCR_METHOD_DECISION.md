# OCR Method Decision: PaddleOCR vs VietOCR Hybrid

## Kết quả thực nghiệm

Tested: 5 ảnh đơn thuốc thật (mask-cropped từ YOLO)

| Tiêu chí | PaddleOCR (PP-OCRv5) | VietOCR Hybrid |
|---|---|---|
| **Avg blocks/img** | 69 | 69 (cùng bbox) |
| **Avg time/img** | 27,548ms (CPU) | 3,304ms (GPU) |
| **Tốc độ** | 1x | 8.3x faster |
| **Text diffs (267 total)** | Mất dấu TV | Giữ dấu TV |

## Ví dụ text khác biệt (trích từ 5 ảnh)

```
PaddleOCR:  "Đa chi liên h:"        → VietOCR: "Địa chỉ liên hệ:"
PaddleOCR:  "Chn Đoán:"             → VietOCR: "Chấn Đoán:"  
PaddleOCR:  "Thuc điu tr:"          → VietOCR: "Thuốc điều trị:"
PaddleOCR:  "uöng"                   → VietOCR: "uống"
PaddleOCR:  "2 lān, mi lān 1 viên"  → VietOCR: "2 lần, mỗi lần 1 viên"
PaddleOCR:  "Viên sùi"              → VietOCR: "Viên sủi"
PaddleOCR:  "Nhó mt khi mi,"        → VietOCR: "Nhỏ mắt khi mỏi,"
PaddleOCR:  "Gii tính: Nam"         → VietOCR: "Giới tính: Nam"
PaddleOCR:  "ãp 3, X V thy"         → VietOCR: "ấp 3, Xã Vị thủy"
```

## Quyết định

**→ CHỌN: VietOCR Hybrid**

Lý do:
1. **Chất lượng tiếng Việt vượt trội**: 267/345 blocks khác nhau, 
   VietOCR giữ đúng dấu tiếng Việt (ắ, ẽ, ơ, ủ, ọ, ồ...)
2. **Nhanh hơn 8.3x**: 3.3s vs 27.5s (GPU RTX 3050)
3. **Cùng detection bbox**: Cả hai dùng PaddleOCR detection → cùng vùng text
4. **DrugMapper tốt hơn**: Text tiếng Việt chính xác → fuzzy match chính xác hơn

Nhược điểm VietOCR:
- Cần GPU (CPU chậm ~60s/img)
- Một số block dài bị cắt ngắn (truncation ở ~40 ký tự)  
- Vài trường hợp hallucinate (e.g., "BỘ Y TẾ" → "BỘ Y TẾ" OK, nhưng
  "BVDK TW CÄN THO" → "BVĐKTWORN THƠ" sai)

## Hành động

1. Xóa `core/ocr/paddle_ocr.py` (Pure PaddleOCR recognition)
2. Đổi tên `hybrid_ocr.py` → `ocr_engine.py` (module chính thức duy nhất)
3. OCR pipeline chỉ còn: PaddleOCR detect bbox → VietOCR recognize text
4. Cập nhật `test_ocr_comparison.py` → chỉ chạy 1 module

## File dữ liệu

- Chi tiết: `output/ocr_evaluation/evaluation_report.txt`
- Per-image: `output/ocr_evaluation/IMG_*/paddle.txt` vs `hybrid.txt`
