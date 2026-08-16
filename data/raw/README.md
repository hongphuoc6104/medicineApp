# Raw OCR and Capture Archive (`data/raw/`)

## Mục đích và Mô tả
Thư mục này lưu trữ các bản ghi nhận diện OCR thô ban đầu từ mobile device trước khi được chuẩn hóa thành schema `rxie.ocr.v1`.

## Lý do tệp nhị phân và dữ liệu chưa lọc bị Gitignore
- Các tệp ảnh gốc (`*.jpg`) và dữ liệu nháp có thể chứa thông tin nhạy cảm chưa qua xử lý ẩn danh.
- Dữ liệu OCR chuẩn hóa và an toàn để huấn luyện mô hình được lưu trữ chính thức tại `data/ocr_final/` và `data/ner_dataset/`.
