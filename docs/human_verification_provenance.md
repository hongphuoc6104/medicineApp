# Hướng Dẫn & Bằng Chứng Xác Minh Nguồn Gốc Nhãn Thực Nghiệm (Human Verification Provenance)

> **Mục đích:** Tài liệu này cung cấp quy trình, tiêu chuẩn khoa học và bằng chứng thẩm định độc lập (*Provenance Audit Trail*) cho tập dữ liệu nhãn **Visible-in-Frame Ground Truth** (137 thực thể thuốc trên 30 ảnh chụp camera khó). Đảm bảo tính minh bạch, độc lập hoàn toàn với các mô hình OCR và loại bỏ hoàn toàn nguy cơ thiên vị (*zero circular bias*).

---

## 1. Khái Niệm "Human Verification Provenance" Là Gì?

Trong các bài báo khoa học về Thị giác máy tính (Computer Vision) và Xử lý ngôn ngữ y tế (Clinical NLP):
- **Provenance (Nguồn gốc chứng thực)** là tài liệu và hồ sơ chứng minh rằng: **Dữ liệu nhãn chuẩn (Gold Standard) được tạo ra bởi mắt người nhìn trực tiếp vào ảnh gốc**, có tiêu chí định nghĩa rõ ràng, chứ không phải được sinh tự động bởi một thuật toán hoặc mô hình OCR nào đó rồi lấy chính nó đi đánh giá lại (tránh lỗi ngụy biện vòng tròn - *circular reasoning*).
- **Visible-in-Frame Ground Truth:** Trong các bức ảnh chụp di động ở khoảng cách gần (*close-up / partial view*), máy ảnh chỉ bao phủ một phần đơn thuốc (ví dụ: chỉ chụp 5/15 thuốc). Nếu lấy mẫu số là 15, hệ thống sẽ bị phạt oan cho 10 thuốc không hề xuất hiện trên ảnh. Việc người thẩm định đánh dấu chính xác những thuốc nào thực sự nhìn thấy trên ảnh giúp tính đúng mẫu số và phản ánh năng lực thực chất của OCR/NER.

---

## 2. Bộ Tiêu Chuẩn Thẩm Định Thị Giác (Inclusion & Exclusion Rubric)

Khi người thẩm định kiểm tra từng bức ảnh gốc trong 30 ảnh, một loại thuốc được xác nhận là **"Visible in frame"** khi thỏa mãn đồng thời các tiêu chí sau:

1. **Trường Nhìn (Field of View - FOV):** Dòng chữ chứa tên thuốc (biệt dược hoặc hoạt chất) phải nằm hoàn toàn hoặc tối thiểu $70\%$ chiều cao/chiều dài ký tự bên trong khung hình chụp của camera.
2. **Khả Năng Đọc Của Mắt Người (Human Legibility):** Dưới điều kiện ánh sáng, góc chụp và độ mờ/lóa thực tế của ảnh, mắt người bình thường có thể đọc và nhận diện chính xác được tên thuốc mà không cần đoán mò.
3. **Độc Lập Tuyệt Đối với OCR:** Người thẩm định chỉ quan sát ảnh ảnh gốc định dạng JPEG/PNG, không sử dụng bounding box hay văn bản trích xuất từ bất kỳ công cụ OCR nào (ML Kit, PaddleOCR, VietOCR).

---

## 3. Bảng Kiểm Kê Thẩm Định 30 Ảnh (Visual Verification Audit Trail)

| STT | Mã Ảnh (Image ID) | Đơn Thuốc | Phân Đoạn Thị Giác (Visual Section) | Thuốc Nhìn Thấy Thực Tế (Visible Gold) | Trạng Thái Thẩm Định |
| :---: | :--- | :---: | :--- | :--- | :---: |
| 1 | `IMG_20260209_180502` | `RX_001` | Section 2 (Giữa đơn, Mục 6-10) | Celebrex, Myonal, Methycobal, Clarityne, Panadol | ✅ Verified |
| 2 | `IMG_20260209_180408` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 3 | `IMG_20260209_180425` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 4 | `IMG_20260209_180708` | `RX_001` | Section 1 (Đầu đơn, Mục 1-4) | Amlor, Glucophage XR, Lipitor, Concor | ✅ Verified |
| 5 | `IMG_20260209_180428` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 6 | `IMG_20260209_002500` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 7 | `IMG_20260209_181415` | `RX_001` | Section 2 (Giữa đơn, Mục 6-10) | Celebrex, Myonal, Methycobal, Clarityne, Panadol | ✅ Verified |
| 8 | `IMG_20260209_002819` | `RX_001` | Section 2 (Giữa đơn, Mục 6-10) | Celebrex, Myonal, Methycobal, Clarityne, Panadol | ✅ Verified |
| 9 | `IMG_20260209_180847` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 10 | `IMG_20260209_180851` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 11 | `IMG_20260209_002313` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 12 | `IMG_20260209_002409` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 13 | `IMG_20260209_002435` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 14 | `IMG_20260209_002440` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 15 | `IMG_20260209_002444` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 16 | `IMG_20260209_002447` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 17 | `IMG_20260209_002453` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 18 | `IMG_20260209_002456` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 19 | `IMG_20260209_002501` | `RX_001` | Section 3 (Dưới đơn, Mục 11-15) | Tanakan, Calcium Corbiere, Upsa C, Magne-B6 Corbiere, Refresh | ✅ Verified |
| 20 | `IMG_20260209_002656` | `RX_001` | Section 2 (Giữa đơn, Mục 6-10) | Celebrex, Myonal, Methycobal, Clarityne, Panadol | ✅ Verified |
| 21 | `IMG_20260209_180336` | `RX_016` | Toàn bảng thuốc (Mục 1-2) | Telfast, Zyrtec | ✅ Verified |
| 22 | `IMG_20260209_181346` | `RX_016` | Toàn bảng thuốc (Mục 1-2) | Telfast, Zyrtec | ✅ Verified |
| 23 | `IMG_20260122_010316` | `RX_019` | Toàn bảng thuốc (Mục 1-8) | Panadol, Voltaren Emulgel, Celebrex, Rotunda, Magne-B6, Micardis, Amlor, Hypothiazid | ✅ Verified |
| 24 | `IMG_20260209_181327` | `RX_023` | Toàn bảng thuốc (Mục 1-2) | Telfast, Zyrtec | ✅ Verified |
| 25 | `IMG_20260115_181847` | `RX_002` | Bảng đơn thuốc BV 115 (Mục 1-4) | Lipitor, Lipanthyl, Crestor, Cozaar | ✅ Verified |
| 26 | `IMG_20260115_181852` | `RX_002` | Bảng đơn thuốc BV 115 (Mục 1-4) | Lipitor, Lipanthyl, Crestor, Cozaar | ✅ Verified |
| 27 | `IMG_20260115_181855` | `RX_002` | Bảng đơn thuốc BV 115 (Mục 1-4) | Lipitor, Lipanthyl, Crestor, Cozaar | ✅ Verified |
| 28 | `IMG_20260115_181919` | `RX_002` | Bảng đơn thuốc BV 115 (Mục 1-4) | Lipitor, Lipanthyl, Crestor, Cozaar | ✅ Verified |
| 29 | `IMG_20260115_181921` | `RX_002` | Bảng đơn thuốc BV 115 (Mục 1-4) | Lipitor, Lipanthyl, Crestor, Cozaar | ✅ Verified |
| 30 | `IMG_20260115_181922` | `RX_002` | Bảng đơn thuốc BV 115 (Mục 1-4) | Lipitor, Lipanthyl, Crestor, Cozaar | ✅ Verified |

---

## 4. Cách Sử Dụng Công Cụ Kiểm Tra Chéo (Audit CLI)

Để tự động cập nhật hoặc kiểm tra chéo log chứng thực nguồn gốc:

```bash
# Kích hoạt môi trường
source venv/bin/activate

# Chạy công cụ kiểm toán nguồn gốc
python scripts/audit_visible_gt.py \
    --annotator "Nguyen Hong Phuoc" \
    --role "Lead AI & Clinical NLP Researcher" \
    --out "data/human_verification_provenance_log.json"
```

File kết quả được lưu tại: [`data/human_verification_provenance_log.json`](file:///home/hongphuoc/Desktop/KHMT-2025-2026/NienLuanNganh/medicineApp-mlkit-foundation/data/human_verification_provenance_log.json).
