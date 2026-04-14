# Phase A - Quét Đơn Thuốc (Active Pipeline)

Đây là Pipeline sản xuất phục vụ lõi trích xuất dữ liệu y tế từ ảnh chụp đơn thuốc. Luồng bao gồm **5 bước logic**, chạy tự động và liền mạch:

## Pipeline Architecture (5 Steps)

1. **`s1_detect/`**: Định vị vị trí bảng đơn thuốc.
   - YOLOv11 model phát hiện Multi-Polygon bounding box, sau đó thu nhỏ (Crop) bằng giải thuật Convex Hull để cắt vùng an toàn lồi, loại rác viền nhưng không ăn lẹm chữ bên trong.

2. **`s2_preprocess/`**: Chuẩn hoá ảnh.
   - Loại bỏ độ nghiêng / Deskewing (với Modulo 90).
   - Kiểm tra AI-orientation bằng PP-LCNet (xoay thẳng 0, 90, 180, 270). Bước này khử hoàn toàn nhu cầu dùng force_portrait gây lẹm ảnh như trước đó.

3. **`s3_ocr/`**: Nhận dạng ký tự (Hybrid OCR).
   - PaddleOCR (detect lines) + VietOCR (đọc nội dung tiếng Việt sinh metadata chính xác dấu chữ).
   - **Step 3.5 (Group by STT):** Tiền xử lý gộp nhóm dữ liệu dựa trên Số Thứ Tự (STT: 1, 2, 3..). Tất cả các khối block trôi nổi không ổn định sẽ bị ép phải nằm trên một mảng Text dài tuần tự khớp định dạng Train cho bước sau. Các cơ chế Gộp Y-Axis cũ đã bị loại bỏ hoặc vô hiệu hóa.

4. **`s5_classify/`**: Phân loại y khoa (NER - Named Entity Recognition).
   - Truyền dãy 1-dòng thu được từ Step 3.5 sang mô hình PhoBERT NER. 
   - Nó bóc tách Label DRUG (TenThuoc) cũng như có thể nhận được thông tin Số lượng, Cách dùng, Hàm lượng.

5. **`s6_drug_search/` (Quy đổi Chuẩn Hóa)**:
   - Match chuỗi TenThuoc/HoatChat thu lượm từ OCR/NER sang kho `drug_db_vn_full.json` (9,284 thuốc) thông qua Fuzzy Search. 
   - Đảm bảo đầu ra JSON map chuẩn format để Node backend lưu DB không bị rỗng nhãn.
