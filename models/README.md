# Models Directory (Trọng Số Weights)

Thư mục này chưa bị Git bỏ qua, tuy nhiên nó không chứa các files nặng (Do đã list `.gitignore` `.pt`, `.bin`, `.pth`). **BẠN CẦN DOWNLOAD TRỌNG SỐ TỰ KHỚP BẰNG TAY** trước khi chạy pipeline. 

## Phase A (Ứng Dụng Thuật Toán Quét Đơn Thuốc)

Đây là các Model cần bắt buộc phải nạp nếu muốn Fast API chạy (không thì API sẽ văng Error):

1. **YOLO 11 Bounding Box (`yolo/`)**
   - `best.pt`: ~45MB. Nhận dạng được bounding crop chung quanh toàn bộ bảng thuốc (Convex Hull base).
   - `table_best.pt`: ~6MB. Model thực nghiệm mới (Table ROI OCR). Nhỏ nhưng chính xác.

2. **PhoBERT NER (`phobert_ner_model/`)**
   - ~500MB (PyTorch / Safetensors + tokenizer JSON). Đây là model tiếng Việt NLP phân loại NER. 

## Phase B (Thuật Toán Experimental - Đang Hold)

- **Zero PIMA (`zero_pima/`)**
  - Trọng số cho luồng xác định mặt thuốc (GCN / FRCNN). File `zero_pima_best.pth` (~521 MB). Hiện tại Phase B đã ngưng, có thể không cần thiết phải load để tăng tốc bộ nhớ Local.
