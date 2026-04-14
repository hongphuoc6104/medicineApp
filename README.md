# MedicineApp

Hệ thống quản lý tuân thủ dùng thuốc và an toàn kê đơn: **Mobile App + Node Backend + Python AI Bridge**.

> **Trạng thái**:
> - **Active**: Reminder core, Scan history, Reconciliation backend.
> - **AI Integration**: Trích xuất thông tin tự động từ đơn thuốc (Phase A - Hoạt động).
> - **Hold**: Xác minh hình chụp viên thuốc so với đơn gốc (Phase B - MVP lite completed, tính năng sản phẩm đang hold).

---

## Tính năng

### 📱 Hệ thống phân phối chính (Mobile App + Node Backend)
- **Quản lý lịch uống thuốc**: Nhắc nhở, theo dõi lịch trình, đánh dấu trạng thái (Skipped/Taken/Snoozed).
- **Scan & Review Journey**: Chụp ảnh đơn thuốc, trích xuất danh sách thuốc, review & mapping thông tin.
- **Medication Reconciliation (Mới)**: Transition-of-Care cards, Know/Check/Ask checklist, và safety checking.
- Caching và offline data resilience (SWR cache mechanism).

### 🧠 Python AI Bridge - Quét đơn thuốc (Phase A)
Dịch vụ trích xuất ảnh chụp đơn thuốc -> nhận diện danh sách tên thuốc tự động:
1. **YOLO Detect & Crop**: Cắt vùng bảng chứa thuốc (Convex Hull).
2. **Preprocess**: Deskew Modulo 90, tự động nắn xoay phẳng với AI orientation (PP-LCNet).
3. **Hybrid OCR**: PaddleOCR polygon detect + VietOCR recognize.
4. **Group by STT**: Gom tất cả các khối text lọt thỏm giữa hai số STT liên tiếp (1, 2, 3...) thành 1 dòng liên tục, đưa về định dạng data huấn luyện.
5. **PhoBERT NER & Drug Lookup**: Bóc tách tên thuốc, SL, hàm lượng và fuzzy matched (9,284 thuốc).

---

## Cài đặt & Dev (Isolated Experimental Local Runtime)

**Workflow DEV không phụ thuộc IP LAN**:
Khi test app Android thật, khuyến nghị cắm USB dùng `adb reverse` qua `dev.sh`.

```bash
# Clone
git clone git@github.com:hongphuoc6104/medicineApp.git
cd medicineApp

# Khởi chạy toàn bộ hệ thống back-end + AI (Isolated runtime)
bash dev.sh
```

**`dev.sh` bao gồm:**
- Khởi chạy PostgreSQL trên Docker (Host port `55432`).
- Chạy Node API trên `3101`.
- Chạy Python AI trên `8100`.
- Chỉnh sửa file `mobile/.env` tự động cập nhật url `API_BASE_URL=http://127.0.0.1:3101/api`.

**Chạy Mobile Debug**:
```bash
cd mobile && flutter run -d <device-id>
```

---

## Kiến trúc Endpoint Chính

Node.js đóng vai trò là Backend chính. FastAPI đóng vai trò AI Bridge độc lập.

### Server Node.js (Main Backend)
- Các route chính: `/api/auth/*` | `/api/drugs/*` | `/api/scan-sessions/*` | `/api/medication-plans/*`

### Server Python (AI Bridge)
- `POST /api/scan-prescription`: Nhận logic upload từ Node backend, trả về danh sách đã bóc tách.

_Lưu ý: Các endpoint lookup thuốc trực tiếp trên Python đã được chuyển dần logic về Node backend hoặc loại bỏ._

---

## Tài liệu Dự Án

### Tài liệu Active Chính (Đọc đầu tiên)
- [AGENTS.md](AGENTS.md) - Bối cảnh repo, guardrails kỹ thuật, rules bắt buộc cho Agents.
- [APP_ACTIVE_GENERAL_PLAN.md](APP_ACTIVE_GENERAL_PLAN.md) - Kế hoạch phát triển chung.
- [APP_ACTIVE_DETAILED_PLAN.md](APP_ACTIVE_DETAILED_PLAN.md) - Kế hoạch công việc chi tiết.
- [docs/UONG_THUOC_FULL_TEST_PLAN.md](docs/UONG_THUOC_FULL_TEST_PLAN.md) - Release gate, test matrix.
- [docs/README.md](docs/README.md) - Mục lục tài liệu cho hệ thống.

### Theo dõi Tiến độ & Lịch sử
- [docs/project_status.md](docs/project_status.md) - Tiến độ hiện tại của sản phẩm.
- [PIPELINE_STATUS.md](PIPELINE_STATUS.md) - Trạng thái kỹ thuật cụ thể của OCR AI Pipeline.

---

## Cấu trúc thư mục

```
medicineApp/
├── server-node/                 # Main Backend API (Express, Postgres)
├── mobile/                      # Mobile application (Flutter)
├── server/                      # FastAPI AI Proxy server
├── core/                        # Source code AI Pipeline (Phase A)
├── scripts/                     # CLI Scripts (chạy AI, đánh giá dataset, database scripts)
├── data/                        # Dữ liệu local JSON database
├── docs/                        # Tài liệu dự án
├── .agent/                      # Tài liệu riêng cho LLM agents
└── archive/                     # Code quá hạn & Archive lịch sử kế hoạch
```

---

## License

MIT License - xem file [LICENSE](LICENSE).
