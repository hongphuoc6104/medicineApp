# Preprocessing Experiments Directory (`data/preprocessing_experiments/`)

## Mục đích và Mô tả
Thư mục này dùng để lưu trữ kết quả của các thử nghiệm tiền xử lý hình ảnh trên mobile/server (deskew, contrast enhancement, shadow removal, adaptive thresholding, Super-Resolution).

## Lý do các tệp ảnh biến đổi bị Gitignore
- Các ảnh sinh ra trong quá trình thử nghiệm biến đổi hình thái (`*.png`, `*.jpg`) có dung lượng lớn và mang tính chất tạm thời.
- Báo cáo số liệu đo lường CER/WER và độ tăng trưởng F1 tương ứng được lưu trong `reports/` và `docs/`.
