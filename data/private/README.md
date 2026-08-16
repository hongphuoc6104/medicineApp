# Private Data Directory (`data/private/`)

## Mục đích và Mô tả
Thư mục này dành riêng cho các tệp dữ liệu nhạy cảm, bảng ánh xạ danh tính bệnh nhân thật (patient identity maps), thông tin liên hệ phòng khám/bệnh viện chưa được khử định danh, hoặc các file cấu hình API keys nội bộ.

## Lý do bị Gitignore (Bảo vệ thông tin cá nhân & Bí mật)
1. **Tuân thủ quy chuẩn y tế:** Bảo vệ 100% danh tính bệnh nhân ngoài đời thực, không để lộ thông tin lịch sử khám chữa bệnh hay đơn thuốc chưa ẩn danh.
2. **Không commit bí mật (No Secrets):** Đảm bảo an toàn không rò rỉ token truy cập cơ sở dữ liệu hoặc thông tin riêng tư lên GitHub.

## Quy định đối với Nhà nghiên cứu
- Mọi dữ liệu phục vụ nghiên cứu và công bố khoa học trong dự án phải sử dụng định danh giả lập/ẩn danh (`PAT_001`, `RX_001_M01`) nằm trong `data/canonical_ground_truth/` và `data/ner_dataset/`.
