# Data — Dữ Liệu I/O

## Input

| Thư mục | Mô tả |
|---------|-------|
| `input/` | Đặt ảnh đơn thuốc (.jpg, .png) vào đây → pipeline xử lý |

## Output (tự động tạo khi chạy pipeline)

| Thư mục | Mô tả |
|---------|-------|
| `output/phase_a/<tên_ảnh>/` | Kết quả Phase A — mỗi ảnh 1 folder riêng chứa `summary.json`, `step-*.json/jpg` |
| `output/phase_b/<tên_ảnh>/` | Kết quả Phase B — pill detection + matching |

## Drug Database

| File | Mô tả | Nguồn gốc |
|------|-------|-----------|
| `vaipe_drugs_kb.json` | **107 loại thuốc** VAIPE — trích từ training data. Chứa name, brand, dosage, sample_texts, count | Từ VAIPE dataset |
| `drug_db_vn.csv` | 316 dòng (192 thuốc phổ biến + 124 VAIPE). Columns: brand_name, generic_name, dosage, category | ⚠️ AI-generated, cần verify |
| `pill_info_vn.csv` | 126 dòng — thêm color, shape so với drug_db_vn.csv | ⚠️ AI-generated, cần verify |

> [!NOTE]
> **Khuyến nghị**: Nên dùng `vaipe_drugs_kb.json` (từ dữ liệu training thật) làm drug DB chính thức.
> Các file CSV hiện tại do AI generate, chưa được xác minh với nguồn y tế chính thống.

## Training Data

| Thư mục | Mô tả |
|---------|-------|
| `pills/` | Dataset ảnh viên thuốc — `train/` + `test/` (từ Kaggle VAIPE) |
| `pres/` | Dataset đơn thuốc JSON — `train/` + `test/` + `test_custom/` |
| `synthetic_train/` | Dữ liệu BVĐK synthetic — 938 train prescriptions, 118 test. Chứa PDF mẫu in thử (`print_20_samples.pdf`), zip archives (`pres_images_train.zip` ~153MB, `pres_labels_train.zip` ~1.4MB) |

## Tools

| Thư mục | Mô tả |
|---------|-------|
| `createPrescription/` | **Tool tạo đơn thuốc format BVĐK Cần Thơ**. Xem chi tiết: `createPrescription/prescription_generator/README.md` |

### createPrescription — Chi tiết

Bộ công cụ sinh đơn thuốc synthetic dùng cho training, gồm:

| File | Chức năng |
|------|----------|
| `prescription_generator/data_generator.py` | Sinh dữ liệu JSON từ Medical Knowledge Base (105 VAIPE drug classes) |
| `prescription_generator/generate_vaipe_data.py` | Inject thuốc VAIPE vào format đơn thuốc |
| `prescription_generator/generate_prescription.py` | Chuyển JSON → DOCX/PDF theo mẫu BVĐK Cần Thơ |
| `prescription_generator/error_injector.py` | Tiêm lỗi y khoa (sai liều, tương tác thuốc, chống chỉ định) |
| `prescription_generator/append_complex_cases.py` | Thêm ca bệnh phức tạp (đa bệnh lý) |

Xem hướng dẫn đầy đủ: [prescription_generator/README.md](createPrescription/prescription_generator/README.md)
