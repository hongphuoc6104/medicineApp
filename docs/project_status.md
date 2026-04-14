# MedicineApp — Project Status (Active)

Bảng theo dõi trạng thái hiện tại của dự án theo từng trục sản phẩm. Đã cập nhật lại toàn bộ tiến độ tính đến hiện tại.

## 1. Trạng thái theo trục sản phẩm

### ⏰ Reminder Core
- **Trạng thái:** Đã hoạt động tốt (Mobile + Backend)
- **Hoàn thành:** 
  - Đăng nhập, xác thực hệ thống.
  - Quản lý lịch nhắc nhở uống thuốc (Create Plan + Home Screen hiển thị Dose list).
  - Đánh dấu trạng thái lịch uống (Skipped/Taken/Snoozed).
  - Local caching (SWR) cho các query trên màn hình chính.
- **Blocker / Tiếp tục theo dõi:** 
  - Notification trên một số dòng máy Android vẫn cần test kỹ hơn về auto-denial permissions.

### 📸 Scan Journey (Phase A)
- **Trạng thái:** Hoàn tất luồng back-end AI, Mobile đã tích hợp một phần
- **Hoàn thành:** 
  - Python AI Pipeline mượt mà 5 bước: YOLO crop → AI Orientation → OCR → Group by STT → NER & Drug Search trên 9,284 loại.
  - Node Backend đã lo việc proxy/lưu trữ session scan.
  - Giao diện mobile hiển thị History chi tiết.
- **Phần Backend xong nhưng thiếu Mobile Integration thực tế:**
  - Chức năng tự tay mapping, chỉnh sửa thuốc nếu kết quả AI bị sai lệch (Scan Editing).
  - Lưu bản ghi xác nhận Scan (Confirm Scan).

### 🛡 Medication Safety Expansion (Reconciliation)
- **Trạng thái:** Đang tích hợp UI/Tối ưu
- **Hoàn thành:** 
  - Chức năng kiểm tra tương tác thuốc, sinh thẻ an toàn (Transition-of-Care cards).
  - Bộ câu hỏi Know/Check/Ask checklist cho bệnh nhân.
- **Phần cần nâng cấp:**
  - Logic backend đã có nhưng chưa liên kết hoàn chỉnh cảnh báo vào mọi ngóc ngách của Create Plan flow.

### 📊 Adherence & History
- **Trạng thái:** Có API, thiếu UI chuyên sâu
- **Hoàn thành:** API backend trả về lịch sử uống thuốc và độ tuân thủ hàng ngày.
- **Thiếu Mobile Integration:** Màn hình Dashboard phân tích quá trình uống thuốc theo tuần/tháng (Chưa làm UI).

### 💊 Phase B (Xác minh viên thuốc)
- **Trạng thái:** HOLD (Tạm ngưng / Experimental)
- **Thực tế:** Các endpoint verification đã có, code Zero-PIMA model đã chạy thử nghiệm MVP, nhưng định hướng product hiện tại ưu tiên Reminder và Scan đơn. Phase B chỉ xem như một tính năng Reference hỗ trợ.

---

## 2. Các Chính sách Hệ thống Cần Nhớ (System Evaluation)

Để dự án vận hành an toàn và chuẩn Y tế, các thành viên cần tuân thủ cấu trúc sau khi phát triển tính năng:

1. **Severity Policy cho Cảnh báo (Interaction Warning):** 
   - Mọi tương tác thuốc mức độ *Nghiêm trọng* không được hiển thị mờ nhạt. Bắt buộc phải là màn hình đỏ/popup Blocking UI cảnh báo, ép user ấn "Tôi đã hiểu" trước khi bỏ qua.
2. **Chính sách Lưu giữ Dữ liệu (Data Retention):** 
   - Ảnh chụp đơn thuốc là thông tin y tế nhạy cảm. Backend cần cơ chế cronjob tự động xóa file ảnh khỏi storage sau 30 ngày, chỉ lưu lại metadata văn bản để giảm rủi ro pháp lý.
3. **Chiến lược Giải quyết Xung đột (Sync Conflict Policy):** 
   - Do mobile app có cache offline SWR, khi có Sync Conflict giữa local và remote (nhiều thiết bị), hiện tại dùng chiến lược "Last-write-wins" (phiên bản có thời gian update mới nhất) hoặc ưu tiên dữ liệu từ Server đè xuống.
4. **Trách nhiệm và Pháp lý (Disclaimer):** 
   - Trong màn hình hiển thị kết quả Scan (Scan Review Screen), **luôn phải có** dòng "Kết quả OCR/AI có thể không chính xác 100%. Thông tin mang tính chất tham khảo, không dùng thay thế tư vấn bác sĩ hoặc dược sĩ chuyên môn."
