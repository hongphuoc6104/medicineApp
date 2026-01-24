# Medicine App

Ứng dụng nhắc nhở uống thuốc.

## Các bước thiết lập ban đầu

### 1. Tạo Virtual Environment

```bash
# Tạo virtual environment với Python 3
python3 -m venv venv

# Kích hoạt virtual environment
# Trên Linux/macOS:
source venv/bin/activate

# Trên Windows:
# venv\Scripts\activate
```

### 2. Khởi tạo Git Repository

```bash
# Khởi tạo git repository
git init

# Đổi tên nhánh thành main (tùy chọn)
git branch -m main
```

### 3. Tạo file .gitignore

File `.gitignore` đã được tạo để loại trừ:
- `venv/` - thư mục virtual environment
- `__pycache__/` - cache Python
- `.env` - file biến môi trường
- Các file IDE và OS không cần thiết

### 4. Kết nối và đẩy lên GitHub

```bash
# Thêm remote repository
git remote add origin https://github.com/hongphuoc6104/medicineApp.git

# Thêm tất cả file vào staging
git add .

# Commit lần đầu
git commit -m "Initial commit: project setup with venv"

# Đẩy lên GitHub
git push -u origin main
```

## Cách chạy dự án

```bash
# Kích hoạt virtual environment
source venv/bin/activate

# Cài đặt dependencies (khi có requirements.txt)
pip install -r requirements.txt
```

## Cấu trúc thư mục

```
medicineApp/
├── venv/               # Virtual environment (không commit)
├── .gitignore          # Danh sách file bỏ qua
└── README.md           # Tài liệu hướng dẫn
```

---
*Ngày tạo: 24/01/2026*
