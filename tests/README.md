# Testing Infrastructure (Kiểm Gian)

Dự án MedicineApp được cấu trúc micro-architecture, dẫn đến việc Unit/Integration Testing được chi rẽ thành 3 phần độc lập. Bạn có thể test riêng lẻ ở mỗi môi trường:

## 1. Node.js Backend Tests (`/server-node`)
Node server chạy business logic chính chứa hơn 55 tests về Auth, Plans, Drug Sync và Reconciliation route.
- Framework: Jest + Supertest (Supermock).
- Lệnh chạy:
  ```bash
  cd server-node
  npm test
  ```

## 2. Python AI Pipeline Tests (`/tests`)
Các bài Unit Testing đánh giá function lõi của Python (Bounding box logic, Modulo 90 crop math).
- Framework: Pytest.
- Lệnh chạy:
  ```bash
  source venv/bin/activate
  pytest
  # Hoặc pytest tests/test_module_name.py
  ```

## 3. Flutter Mobile Tests (`/mobile`)
Kiểm toán Widget Logic UI và Test Provider Fetcher State Management tại nhánh Mobile.
- Framework: Flutter Test.
- Lệnh chạy:
  ```bash
  cd mobile
  flutter test
  ```
