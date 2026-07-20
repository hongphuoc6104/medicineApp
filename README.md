# MedicineApp

Hệ thống hỗ trợ quét đơn thuốc và trích xuất danh sách thuốc tự động thông minh bằng AI, tối ưu hóa chạy hoàn toàn trên CPU.

Dự án tích hợp **Google ML Kit Document Scanner** trên thiết bị di động để chuẩn hóa hình ảnh đơn thuốc trực tiếp, và sử dụng **PhoBERT NER + Drug Lookup** trên máy chủ (Server) để trích xuất và chuẩn hóa tên thuốc theo Cơ sở dữ liệu chuẩn của Cục Quản lý Dược Việt Nam.

---

## 🛠️ Yêu cầu Hệ thống & Cấu trúc Dự án

Dự án bao gồm 3 thành phần chính:
1.  **Mobile (Flutter App):** Ứng dụng di động chụp và quét chữ viết đơn thuốc tại chỗ (On-device OCR).
2.  **Node.js Server:** Máy chủ backend chính để quản lý dữ liệu, người dùng, kế hoạch uống thuốc.
3.  **FastAPI Server (Python AI Backend):** Máy chủ AI chịu trách nhiệm phân loại thực thể tên thuốc (NLP/NER) và tra cứu danh mục thuốc Việt Nam.

---

## 🚀 Hướng dẫn Cài đặt & Phục hồi Trạng thái

### 1. Cơ sở dữ liệu (PostgreSQL qua Docker)
Khởi động container cơ sở dữ liệu PostgreSQL 16:
```bash
docker start medicineapp_db
# Hoặc chạy mới: docker compose up -d postgres
```

### 2. FastAPI AI Server (Python Backend)
AI Server đã được cấu hình mặc định chạy **100% trên CPU**, không yêu cầu GPU CUDA.

*   **Chuẩn bị môi trường & Cài đặt thư viện:**
    ```bash
    # Kích hoạt virtual environment
    source venv/bin/activate
    # Cài đặt thư viện phụ thuộc
    pip install -r requirements.txt
    ```
*   **Trọng số Mô hình (Model Weights):**
    Hãy đảm bảo các file weights được copy đúng cấu trúc sau (nằm trong `.gitignore` nên cần phục hồi thủ công khi tạo thư mục làm việc mới):
    *   `models/yolo/best.pt` (Mô hình YOLOv11 cắt khung đơn thuốc)
    *   `models/phobert_ner_model/` (Thư mục chứa weights PhoBERT NER fine-tuned)
*   **Chạy FastAPI Server:**
    ```bash
    uvicorn server.main:app --host 0.0.0.0 --port 8000
    ```

### 3. Node.js Backend Server
*   **Cài đặt thư viện:**
    ```bash
    cd server-node
    npm install
    ```
*   **Khởi chạy máy chủ ở chế độ Development:**
    ```bash
    npm run dev
    ```
    *Server chạy tại: http://localhost:3001*

### 4. Mobile Client (Flutter App)
*   **Cài đặt các gói phụ thuộc:**
    ```bash
    cd mobile
    flutter pub get
    ```
*   **Chạy ứng dụng:**
    ```bash
    flutter run
    ```

---

## ⚡ Luồng xử lý quét đơn thuốc mới (Fast-Path CPU)

1.  **Chụp & Chuẩn hóa (Di động):** Ứng dụng di động gọi Google ML Kit Document Scanner để tự động nắn góc phẳng, căn thẳng góc nghiêng và xoay đứng ảnh chụp đơn thuốc.
2.  **OCR tại chỗ (Di động):** Chạy thư viện ML Kit Text Recognition để bóc tách chữ viết thô trực tiếp trên chip của điện thoại (không tốn tài nguyên server).
3.  **Fast-Path xử lý AI (Server):** 
    *   Điện thoại gửi ảnh + văn bản thô lên Server Node.js -> FastAPI.
    *   FastAPI bỏ qua hoàn toàn các bước YOLO crop, deskew, orientation và OCR trên máy chủ.
    *   Sử dụng **CPU** để chạy **PhoBERT NER** phân loại tên thuốc và chạy thuật toán **Drug Lookup** đối chiếu fuzzy search CSDL **9.284 thuốc chuẩn Việt Nam** để trả về kết quả an toàn.
