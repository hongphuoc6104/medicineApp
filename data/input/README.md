# Input Data Directory (`data/input/`)

## Mục đích và Mô tả
Thư mục này dùng để chứa các tệp ảnh đơn thuốc thô (raw image binaries: `.jpg`, `.jpeg`, `.png`, `.heic`) được chụp từ camera điện thoại hoặc thiết bị scan.

## Lý do bị Gitignore (Bảo mật & Quyền riêng tư Y tế)
1. **Tuân thủ quy định bảo mật dữ liệu bệnh nhân (PII / Healthcare Privacy):**
   - Ảnh chụp đơn thuốc thực tế có thể chứa thông tin định danh cá nhân (Họ tên, tuổi, địa chỉ, số CMND/CCCD, mã thẻ BHYT, chữ ký bác sĩ, chẩn đoán ICD).
   - Theo quy tắc của dự án (`AGENTS.md`), **tuyệt đối không commit hoặc đẩy ảnh đơn thuốc thô của bệnh nhân lên kho mã nguồn công khai (Git/GitHub)**.
2. **Dung lượng nhị phân:**
   - Tránh làm phình dung lượng repository Git với các tệp nhị phân lớn.

## Hướng dẫn sử dụng Local
- Khi chạy thử nghiệm OCR offline, người dùng có thể đặt ảnh đơn thuốc vào thư mục này để chạy pipeline ingestion:
  ```bash
  python3 scripts/run_ocr_pipeline.py --input-dir data/input/
  ```
- Kết quả OCR dạng JSON sau khi đã ẩn danh (de-identified) sẽ được lưu tại `data/ocr_final/`.
