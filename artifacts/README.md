# Artifacts Directory (`artifacts/`)

## Mục đích và Mô tả
Thư mục này dùng để lưu trữ các sản phẩm phụ trợ phát sinh trong quá trình huấn luyện và tối ưu hóa mô hình, bao gồm:
- Ma trận nhúng (embedding caches: `.npy`, `.npz`).
- Trọng số xuất bản đã đóng băng (frozen inference graphs: `.onnx`, TorchScript).
- Báo cáo phân tích lỗi dạng bảng (error analysis `.csv`, `.parquet`).
- Các biểu đồ trực quan hóa kết quả đánh giá (confusion matrices, PR curves).

## Lý do bị Gitignore
1. **Dung lượng lớn (Large Binary Files):** Các tệp trọng số nhị phân và cache tensor có kích thước từ vài trăm MB đến nhiều GB, không phù hợp để lưu trữ trực tiếp trong Git commit history.
2. **Tách biệt Mã nguồn & Trọng số:** Quản lý mã nguồn (logic thuật toán) độc lập với trọng số mô hình (weights & binary artifacts).

## Hướng dẫn tái tạo / Tải về
- Trọng số mô hình chính thức được lưu trữ và tải về từ Hugging Face Hub hoặc Cloud Object Storage (S3 / GCS).
- Các tệp cache cục bộ sẽ tự động được sinh khi chạy pipeline đánh giá hoặc inference:
  ```bash
  python3 scripts/evaluate_models.py --save-artifacts
  ```
