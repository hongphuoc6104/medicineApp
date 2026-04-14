# Mobile App (Flutter)

Đây là client dành cho người dùng cuối của MedicineApp. Ứng dụng tập trung vào việc hiển thị lịch uống thuốc và luồng chụp ảnh thông minh.

## Các Feature Chính (Clean Architecture)

Cấu trúc dự án theo Feature-first + Clean Architecture:
- `auth`: Đăng nhập tĩnh và xử lý JWT token.
- `home`: Danh sách thuốc cần uống hôm nay, hỗ trợ Cache SWR và chức năng đánh dấu thuốc (Taken/Skipped/Snoozed).
- `create_plan`: Chụp đơn thuốc gửi sang Server Node (Node sẽ gọi AI Bridge), review kết quả JSON trả về. Cảnh báo quá liều, tương tác thuốc.
- `history`: Xem các đơn thuốc đã quét trong quá khứ.
- `reconciliation`: Module safety (Transition-of-Care cards, Checklist) để xác minh độ an toàn của chu trình thuốc.

## User Flows Chính

1. **Đăng nhập**: User nhập thông tin (hiện tại skip qua auto-login account tĩnh) -> nhận JWT lưu vào Secure Storage.
2. **Review Lịch Trong Ngày (Home)**: App fetch danh sách Reminder -> Cache vào SQLite. Fetch background (SWR) -> Update UI.
3. **Scan Đơn Thuốc (Create Plan)**: User chụp hình/upload ảnh -> `POST` tới Node backend -> AI FastAPI bóc tách dữ liệu -> Trả về màn hình Scan Review.
4. **Scan Review Process**: Hiển thị bảng Edit UI. User sửa lỗi OCR nếu có. Kiểm tra Checklist an toàn. Confirm lưu DB.
5. **Hiển thị thông báo (Notifications)**: Cronjob hoặc Local Notification tự động ping nhắc nhở.

## Hướng dẫn Chạy App (Dev Environment)

Ứng dụng đang cấu hình chạy với môi trường Local Backend qua IP LAN. Tuy nhiên, thay vì đổi cứng IP vào mã nguồn, dự án hỗ trợ `dev.sh` port-forward.

### Bước 1: Khởi động Backend
Tại thư mục gốc của dự án (`/medicineApp`), chạy script gom:
```bash
bash dev.sh
```
*(Script này sẽ chép IP cục bộ 127.0.0.1 và forward Node port sang 3101, lưu vào file `.env` của mobile).*

### Bước 2: Chạy Flutter với thiết bị thật (Khuyến nghị)
Khi kiểm thử Camera hoặc Thông báo, hãy chạy qua thiết bị thật cấp quyền USB Debugging:
```bash
# Xem id device
flutter devices

# Chạy vào app
flutter run -d <device-id>
```
Script `dev.sh` đã thay mặt bạn gọi `adb reverse` cho `3101` (Node) và `8100` (FastAPI) nên sẽ gọi Backend bình thường như trên máy tính.

Tệp tin cấu hình (`.env`) sẽ trông như sau:
```
API_BASE_URL=http://127.0.0.1:3101/api
```

## Câu Lệnh Test

Mobile App có setup Analyzer và Test framework:
```bash
# Kiểm tra lỗi cú pháp và lints
flutter analyze

# Chạy Widget và Unit tests 
flutter test
```
