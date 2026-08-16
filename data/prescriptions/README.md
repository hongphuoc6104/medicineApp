# Prescriptions Directory (`data/prescriptions/`)

## Mục đích và Mô tả
Thư mục này tổ chức các đơn thuốc theo cụm thực thể đơn (`RX_001` đến `RX_035`). Mỗi thư mục con đại diện cho một đơn thuốc thực tế, bao gồm:
- Thư mục ảnh cục bộ `images/` chứa các góc chụp camera khác nhau của cùng một đơn thuốc.
- Tệp metadata mô tả phân nhóm và điều kiện chụp (lighting, perspective, blur).

## Lý do các tệp ảnh (`*.jpg`, `*.png`) bị Gitignore
1. **Tuân thủ quyền riêng tư dữ liệu bệnh nhân:** Ảnh chụp thực tế không được phép commit lên GitHub theo quy chuẩn đạo đức nghiên cứu và điều khoản `AGENTS.md`.
2. **Dữ liệu đại diện (Representational Metadata):** Toàn bộ nội dung văn bản OCR và nhãn lâm sàng đã được khử định danh an toàn tại `data/canonical_ground_truth/`, `data/ocr_final/`, và `data/ner_dataset/`.
