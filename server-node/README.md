# Backend (Node.js API)

Đây là **Backend Chính** của dự án MedicineApp.
Dự án sử dụng Express.js, PostgreSQL và Prisma/pg_trgm. Tất cả client request từ mobile devices đều giao tiếp qua đây. Node server có trách nhiệm quản lý state, user data, và đứng ra làm Proxy kết nối với hệ thống Python AI (FastAPI) những lúc cần xử lý Scan/Nhận diện.

## Cài đặt và Môi trường

```bash
cd server-node
npm install
```

Cấu hình `.env` cho kết nối PostgreSQL:
```env
# Lưu ý: Trong chế độ dev.sh local, DB chạy port 55432
DATABASE_URL="postgres://postgres:postgres@localhost:55432/medicineapp_experimental"
PORT=3101
PYTHON_AI_URL="http://localhost:8100/api"
JWT_SECRET="your_secret_key"
```

Khởi chạy Database qua Docker:
```bash
# Hoặc chạy bash dev.sh ở ngoài root
cd .. && bash dev.sh
```

Tiến hành tạo Table cấu trúc:
```bash
node src/config/migrate.js
# và thiết lập seed data
npm run seed
```

## Khởi chạy Server

```bash
npm run dev
```

## Các Nhóm API (Routes Group)

- **Auth** (`/api/auth`): Xác thực người dùng (Login, Register, JWT, Profile).
- **Trực tiếp (Drugs/Plans Core)**:
  - **Medication Plans** (`/api/plans`): Quản lý kho thuốc cá nhân, lịch uống, và log đánh dấu/tuân thủ. 
  - **Drugs Reference** (`/api/drugs`): Tra cứu thuốc trong database hệ thống, tìm từ khóa.
- **AI Integrations**:
  - **Scan** (`/api/scan`): Đại diện upload đơn thuốc, gọi sang FastAPI proxy trích xuất kết quả JSON trả về cho Mobile Client. Khởi tạo/Hoàn tất Scan sessions.
  - **Pill References / Verifications**: Nhóm endpoints thử nghiệm cho luồng chụp viên thuốc Phase B (Experimental).
- **Safety / Reconciliation (Mới)** (`/api/reconciliation`): Route mở rộng hỗ trợ Transition-of-Care, các luồng cảnh báo cấp độ cao, interaction checklist, risk overview card.

## Lệnh Test

Backend tích hợp Jest / Supertest API Unit + Integration tests:

```bash
# Chạy hơn 55 unit/integration test logic
npm test
```
