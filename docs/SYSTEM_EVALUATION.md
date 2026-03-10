# Báo cáo Đánh giá Vòng 3 — Domain Y tế, Data Integrity & Edge Cases

> **Phiên bản:** 3.0 | **Ngày:** 2026-03-10  
> Vòng này tập trung vào các vấn đề **chưa được phân tích** ở 2 vòng trước: rủi ro y tế, data consistency, edge cases mobile, và thiếu sót quy trình.

---

## Tóm tắt Vòng 1+2 (Đã sửa — 11 điểm)

| Vòng | Đã sửa |
|------|--------|
| Vòng 1 (4 điểm) | GPU OOM, Anti-bot, Fuzzy Search, Offline Notification |
| Vòng 2 (7 điểm) | Circuit Breaker, Magic Bytes, JWT Revocation, DB Index, Pagination, Health Check, Docker |

---

## Vòng 3: 5 Điểm yếu mới

---

### 🔴 VẤN ĐỀ 12: Cảnh báo Tương tác Thuốc Nguy hiểm không được Highlight đúng mức

**Vấn đề:** API `ddi.lab.io.vn` trả 190 tương tác/thuốc với 3 mức: "Nghiêm trọng", "Trung bình", "Không xác định". Plan hiện chỉ ghi "hiển thị cảnh báo" — nhưng **KHÔNG nói rõ** cách xử lý khi phát hiện tương tác **Nghiêm trọng** giữa 2 thuốc trong cùng 1 đơn.

**Tác động:** Đây là app Y TẾ. Bệnh nhân uống 2 thuốc xung đột nghiêm trọng có thể **nguy hiểm đến tính mạng**. Nếu app chỉ hiện 1 dòng text nhỏ → user bỏ qua → hậu quả pháp lý và đạo đức.

**Trong MASTER_PLAN hiện tại:** Chỉ ghi "Tương tác thuốc hiển thị cảnh báo" — quá chung chung.

**Giải pháp:**
- **Mức Nghiêm trọng:** Hiển thị **popup toàn màn hình màu đỏ** (blocking UI) bắt buộc user đọc + bấm "Tôi đã hiểu" trước khi tiếp tục. Gợi ý "Hãy hỏi ý kiến bác sĩ hoặc dược sĩ".
- **Mức Trung bình:** Hiển thị banner cảnh báo vàng có thể dismiss.
- **Disclaimer pháp lý** (bắt buộc): App cần ghi rõ "Thông tin chỉ mang tính tham khảo. Không thay thế tư vấn y khoa."

---

### 🔴 VẤN ĐỀ 13: Ảnh đơn thuốc Upload lên Server không được xóa

**Vấn đề:** Khi user scan đơn thuốc, ảnh được gửi tới Python FastAPI → Node.js lưu `image_url` vào DB. Nhưng **KHÔNG có chính sách xóa ảnh** (data retention policy). Sau 1 năm, server sẽ chứa **hàng nghìn ảnh đơn thuốc** — dữ liệu y tế nhạy cảm.

**Trong MASTER_PLAN hiện tại:** Không đề cập data retention.

**Giải pháp:**
- Cho phép user tự xóa scan (API `DELETE /scans/:id` + xóa file ảnh trên disk/cloud storage).
- Tự động xóa ảnh gốc sau 30 ngày (giữ kết quả JSON, xóa ảnh). Hoặc cho user chọn thời gian giữ ảnh trong Settings.
- Khi user xóa tài khoản → xóa **toàn bộ** dữ liệu (GDPR: Right to be forgotten).

---

### 🟠 VẤN ĐỀ 14: Conflict khi Đồng bộ SQLite Local ↔ PostgreSQL Server

**Vấn đề:** Plan đề xuất lưu Medication Plan vào **cả SQLite local (Flutter) và PostgreSQL (Server)**. Nhưng không có chiến lược xử lý **sync conflict** khi:
- User A sửa Plan trên điện thoại (offline) → lưu SQLite
- Cùng lúc, User A đăng nhập trên tablet → sửa Plan khác đi → lưu PostgreSQL
- Khi điện thoại có mạng lại → **2 phiên bản khác nhau** → mất data nào?

**Trong MASTER_PLAN hiện tại:** Chỉ ghi "Đồng bộ với Backend API Node.js khi có mạng nền (Sync)" — quá mơ hồ.

**Giải pháp (Last-Write-Wins + Conflict Detection):**
- Mỗi record có `updated_at` timestamp. Khi sync, so sánh timestamp:
  - Nếu server mới hơn → ghi đè local.
  - Nếu local mới hơn → gửi lên server.
  - Nếu **cả hai thay đổi** (conflict thực sự) → hiển thị cho user chọn phiên bản nào giữ lại.
- MVP đơn giản: **Server luôn thắng** (server-wins). Phiên bản phức tạp hơn làm sau.

---

### 🟠 VẤN ĐỀ 15: Thiếu Database Migration Tool

**Vấn đề:** Plan liệt kê SQL schema nhưng **không có migration tool**. Khi thay đổi schema (thêm cột, sửa index), phải chạy SQL thủ công → dễ quên, dễ sai, không rollback được.

**Trong MASTER_PLAN hiện tại:** Thư mục `migrations/` có liệt kê nhưng không chỉ rõ dùng tool gì.

**Giải pháp:**
- Dùng **Knex.js** (khuyên dùng cho Express + PostgreSQL) hoặc **Prisma** (nếu muốn ORM).
- Mỗi thay đổi DB = 1 file migration có `up()` và `down()`.
- Lệnh: `npx knex migrate:latest` (apply) / `npx knex migrate:rollback` (undo).

---

### 🟡 VẤN ĐỀ 16: Thiếu Disclaimer & Giới hạn Trách nhiệm Pháp lý

**Vấn đề:** Đây là ứng dụng Y tế. Nếu AI đọc sai tên thuốc (OCR error) → user uống sai thuốc → **trách nhiệm pháp lý thuộc ai?** Plan không đề cập đến disclaimer hoặc Terms of Service.

**Giải pháp (bắt buộc cho app Y tế):**
- **Màn hình Disclaimer** hiển thị 1 lần khi user mở app lần đầu: "Ứng dụng sử dụng AI để đọc đơn thuốc. Kết quả có thể sai sót. Luôn kiểm tra lại với dược sĩ hoặc bác sĩ trước khi sử dụng thuốc."
- Mỗi kết quả scan: hiện confidence score + dòng cảnh báo: "Kết quả OCR có thể không chính xác 100%. Vui lòng đối chiếu với đơn thuốc gốc."
- Trong Terms of Service: ghi rõ app **không phải thiết bị y tế**, chỉ mang tính tham khảo.

---

## Bảng Tổng hợp Toàn bộ 16 Điểm yếu (3 vòng)

| # | Vấn đề | Mức độ | Vòng | Trạng thái |
|---|--------|--------|------|-----------|
| 1 | GPU OOM | 🔴 | V1 | ✅ |
| 2 | Anti-bot block crawl | 🔴 | V1 | ✅ |
| 3 | OCR sai chính tả → SQL fail | 🔴 | V1 | ✅ |
| 4 | Báo thức phụ thuộc mạng | 🔴 | V1 | ✅ |
| 5 | API ddi.lab.io.vn down | 🔴 | V2 | ✅ |
| 6 | File upload bypass | 🔴 | V2 | ✅ |
| 7 | JWT không revocation | 🔴 | V2 | ✅ |
| 8 | DB thiếu Index | 🟠 | V2 | ✅ |
| 9 | API thiếu Pagination | 🟠 | V2 | ✅ |
| 10 | Thiếu Health Check | 🟠 | V2 | ✅ |
| 11 | Thiếu Docker/Deployment | 🟡 | V2 | ✅ |
| **12** | **Tương tác thuốc nguy hiểm không highlight** | 🔴 | **V3** | ❌ |
| **13** | **Ảnh y tế không có data retention policy** | 🔴 | **V3** | ❌ |
| **14** | **Sync conflict SQLite ↔ PostgreSQL** | 🟠 | **V3** | ❌ |
| **15** | **Thiếu DB migration tool** | 🟠 | **V3** | ❌ |
| **16** | **Thiếu Disclaimer pháp lý cho app y tế** | 🟡 | **V3** | ❌ |

---

## Đánh giá Tổng thể

Sau 3 vòng kiểm tra, MASTER_PLAN đã được phân tích **16 điểm yếu** từ 6 góc nhìn khác nhau:

| Góc nhìn | Điểm yếu tìm được |
|----------|-------------------|
| Hạ tầng & GPU | #1 OOM |
| Bảo mật & Xác thực | #6 File upload, #7 JWT, #10 Health |
| Database & Performance | #3 Fuzzy, #8 Index, #9 Pagination, #15 Migration |
| External API Dependency | #2 Anti-bot, #5 Circuit Breaker |
| Mobile & Offline | #4 Local Notification, #14 Sync Conflict |
| **Domain Y tế & Pháp lý** | **#12 Tương tác nguy hiểm, #13 Data retention, #16 Disclaimer** |

> **Kết luận:** Plan đã đạt mức chất lượng cao cho production deployment. Các vấn đề vòng 3 chủ yếu thuộc lĩnh vực domain Y tế và pháp lý — những thứ cần implement nhưng không block việc bắt đầu code.
