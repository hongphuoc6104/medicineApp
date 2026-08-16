# Output Data Directory (`data/output/`)

## Mục đích và Mô tả
Thư mục này được sử dụng làm vùng đệm chứa các tệp đầu ra trung gian phát sinh trong quá trình chạy xử lý ảnh, OCR tạm thời, hoặc các báo cáo xuất dữ liệu thử nghiệm tại runtime.

## Lý do bị Gitignore
1. **Dữ liệu tạm thời (Ephemeral / Runtime artifacts):** Các tệp trong thư mục này được sinh ra và ghi đè liên tục khi chạy các script kiểm thử hoặc pipeline xử lý ảnh.
2. **Tránh xung đột Git (Merge conflicts):** Ngăn chặn việc các file tạm/log ghi đè gây xung đột khi nhiều nhà phát triển cùng chạy thực nghiệm.

## Hướng dẫn tái tạo
- Thư mục sẽ tự động được tạo và ghi bởi các script như `scripts/test_preprocess_robustness.py`, `scripts/build_full_dataset_pipeline.py`.
- Có thể xóa sạch toàn bộ nội dung trong thư mục này bất kỳ lúc nào mà không ảnh hưởng tới codebase:
  ```bash
  rm -rf data/output/*
  ```
