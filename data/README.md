# RxIE Data Directory Structure

Cấu trúc thư mục dữ liệu chuẩn hóa của dự án RxIE:

```text
data/
├── prescriptions/                  # [CHÍNH] 35 thư mục đơn thuốc (RX_001 -> RX_027 + hard_cases)
│   ├── RX_001/                     # Đơn thuốc 1 (ảnh gốc trong images/ + OCR trong ocr_final/ + canonical_gt.json)
│   ├── RX_002/                     # Đơn thuốc 2
│   ├── ...
│   └── hard_cases/                 # 8 ca ảnh mờ/hỏng/thiếu thông tin được cách ly
│
├── canonical_ground_truth/         # [CHÍNH] 27 file nhãn chuẩn Ground Truth (Gold Standard) do người duyệt
│   ├── RX_001.json
│   ├── RX_002.json
│   └── ...
│
├── ocr_final/                      # [CHÍNH] 437 file OCR JSON chuẩn V1 sau bộ lọc chất lượng P6
│   ├── IMG_20260115_181847.json
│   └── ...
│
├── manifests/                      # [QUẢN LÝ] Bảng manifest gom nhóm, chia tập Train/Val/Test, quy chuẩn V1
│   ├── prescriptions_manifest.json
│   ├── prescriptions_manifest.csv
│   ├── balanced_prescription_splits.json
│   └── preprocessing_v1_frozen_spec.json
│
├── raw/                            # [DỮ LIỆU THÔ] Nguồn ảnh gốc và kết quả OCR thô nguyên bản
│   ├── images/                     # 437 file ảnh chụp gốc (.jpg, .png)
│   └── ocr_raw/                    # File kết quả OCR thô quét trực tiếp từ ML Kit (nhánh P0)
│
├── preprocessing_experiments/      # [THỰC NGHIỆM] Dữ liệu thực nghiệm 200 ảnh tiền xử lý (P1-P4)
│   ├── staging_200/                # 200 ảnh benchmark
│   ├── p1_rotation_200/            # Ảnh sau khi xoay đúng chiều
│   ├── p2_perspective_200/         # Ảnh sau khi nắn phối cảnh
│   ├── p3_deskew_200/              # Ảnh sau khi khử nghiêng
│   ├── rectified_200/              # Ảnh sau khi chạy chuỗi hình học
│   ├── output_p1/                  # Kết quả OCR nhánh P1
│   ├── output_p2/                  # Kết quả OCR nhánh P2
│   ├── output_p3/                  # Kết quả OCR nhánh P3
│   ├── output_rectified/           # Kết quả OCR nhánh P4
│   └── ablation_metadata_tracking.json
│
├── ner_dataset/                    # [HUẤN LUYỆN] Nơi lưu trữ tập dữ liệu NER 10 lớp cho mô hình
├── legacy/                         # Dữ liệu đối chứng cũ (chỉ có nhãn 1 class DRUG)
└── samples/                        # File mẫu phục vụ kiểm thử tự động
```
