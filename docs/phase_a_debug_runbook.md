# Phase A Debug Runbook

Runbook này dùng để debug nhanh và nhất quán cho luồng chính của app:

- quét đơn thuốc
- xác nhận danh sách thuốc
- lập lịch uống thuốc

Mục tiêu của runbook là giảm việc phải suy nghĩ lại từ đầu mỗi lần có lỗi, và giảm phụ thuộc vào MCP/tool ngoài cho những việc debug lặp đi lặp lại.

---

## 1. Khi nào dùng runbook này

Dùng khi gặp một trong các tình huống sau:

- scan flow bị lỗi hoặc hành vi lạ
- mobile UI thay đổi nhưng chưa chắc có làm vỡ flow tạo kế hoạch hay không
- contract giữa mobile, Node và Python có thể đang lệch nhau
- cần kiểm tra nhanh xem repo còn ổn để tiếp tục code hay không

Không dùng runbook này để debug Phase B hoặc training model.

---

## 2. Trình tự debug chuẩn

Luôn đi theo thứ tự này:

1. xem `git status --short`
2. chạy bộ kiểm tra nhanh
3. nếu cần, chạy smoke cho app-path Python scan
4. nếu cần, chạy manual verify trên điện thoại thật
5. chỉ khi xác định được tầng lỗi mới bắt đầu sửa

Đi ngược thứ tự này thường làm mất thời gian và tăng nguy cơ sửa sai tầng.

---

## 3. Script chính

Script dùng để chạy kiểm tra Phase A:

```bash
bash scripts/debug_phase_a_checks.sh --quick
```

### Dev setup khuyến nghị cho Android thật

Để tránh phải đổi IP mỗi khi đổi Wi-Fi, dùng workflow `adb reverse` qua USB:

```bash
bash dev.sh
```

Script này sẽ:

- preflight local Python runtime (`venv/bin/python`, Python >= 3.10; khuyến nghị 3.12, có FastAPI/Uvicorn)
- fail fast nếu `:8000` đang bị chiếm, kèm thông tin listener để tránh chạy nhầm runtime
- cập nhật `mobile/.env` về `http://127.0.0.1:3001/api`
- khởi động Node API local ở `3001`
- khởi động Python AI server bằng interpreter trong `venv`
- verify `/api/health` của Python có đúng runtime local (`inside_docker=false`, `using_expected_venv=true`, `ai_ready=true`)
- chạy `adb reverse tcp:3001 tcp:3001`

Kết quả:

- app Android thật sẽ gọi `127.0.0.1:3001`
- nhưng request được reverse về máy dev qua USB
- đổi Wi-Fi không còn làm hỏng kết nối nếu điện thoại vẫn cắm USB và `adb reverse` còn hiệu lực

Các mode hỗ trợ:

```bash
# Kiểm tra nhanh tập trung vào Phase A
bash scripts/debug_phase_a_checks.sh --quick

# Kiểm tra rộng hơn
bash scripts/debug_phase_a_checks.sh --full

# Có chạy smoke app-path Python
bash scripts/debug_phase_a_checks.sh --quick --scan-smoke

# Có chạy thêm protected CLI pipeline cho 1 ảnh
bash scripts/debug_phase_a_checks.sh --quick --image "data/input/prescription_3/IMG_20260209_180505.jpg"
```

---

## 4. Script sẽ làm gì

### 4.1 `--quick`

Chạy các kiểm tra nhanh, chi phí thấp hơn:

- `git status --short`
- `py_compile` cho `core/pipeline.py` và `server/main.py`
- health check `http://127.0.0.1:8000/api/health` và validate runtime local
- `server-node` focused tests:
  - `tests/unit/scan.service.test.js`
  - `tests/integration/scan.routes.test.js`
- `flutter analyze`
- `flutter test`

### 4.2 `--full`

Chạy tất cả những gì ở `--quick`, nhưng thay focused Node tests bằng full suite:

- `cd server-node && npm test`

### 4.3 `--scan-smoke`

Nếu file `scripts/tests/test_phase_a_api_alignment.py` có tồn tại, script sẽ gọi nó để kiểm tra app-path Python scan.

### 4.4 `--image`

Nếu truyền `--image`, script sẽ chạy thêm:

```bash
python scripts/run_pipeline.py --image <path>
```

Phần này nặng hơn và chỉ nên dùng khi thật sự cần smoke pipeline CLI.

---

## 5. Cách đọc lỗi theo từng tầng

### 5.1 Nếu `flutter analyze` hoặc `flutter test` fail

Khả năng cao lỗi ở:

- màn hình Flutter
- router
- model mobile
- state/UI copy

Ưu tiên kiểm tra:

- `create_plan` screens
- `app_router.dart`
- `scan_result.dart`

### 5.2 Nếu Node scan tests fail

Khả năng cao lỗi ở:

- `server-node/src/services/scan.service.js`
- `server-node/src/routes/scan.routes.js`
- shape response cho mobile

Ưu tiên kiểm tra:

- extracted name có còn là primary không
- field nào bị đổi shape
- route `/scan` có còn trả đúng contract không

### 5.3 Nếu Python smoke fail

Khả năng cao lỗi ở:

- `core/pipeline.py`
- `server/main.py`
- app-path scan response shape

Hoặc lỗi runtime local bị lệch:

- `:8000` trỏ vào runtime/container sai
- Python không chạy từ `venv` trong repo
- API lên được nhưng `ai_ready=false` (scan fallback mock)

Ưu tiên kiểm tra:

- `scan_prescription_app()`
- API endpoint scan
- field `medications`, `mapping_status`, `ocr_text`
- payload `GET /api/health`:
  - `runtime.inside_docker`
  - `runtime.using_expected_venv`
  - `scan_runtime.mode`
  - `scan_runtime.pipeline_last_error`

Lệnh nhanh:

```bash
curl http://127.0.0.1:8000/api/health
```

### 5.4 Nếu tất cả test pass nhưng app flow vẫn tệ

Đây thường là lỗi ở mức sản phẩm/UX chứ không phải compile/contract.

Khi đó cần manual verify theo flow:

1. vào `Tạo kế hoạch`
2. vào `Quét đơn thuốc`
3. quét 1 ảnh
4. xử lý danh sách thuốc
5. lập lịch
6. lưu kế hoạch

---

## 6. Checklist manual verify tối thiểu

Sau một thay đổi liên quan đến Phase A, nên kiểm tra:

1. mở `Tạo kế hoạch`
2. thấy rõ 3 đường vào: scan / nhập tay / lịch sử
3. mở `Quét đơn thuốc` thấy camera ngay
4. ảnh xấu có thể `Chụp lại`
5. ảnh tốt đi tới màn review
6. sửa được 1 thuốc
7. thêm được 1 thuốc
8. xóa được 1 thuốc
9. sang màn lập lịch
10. lưu được kế hoạch

---

## 7. Khi nào phải dừng và không sửa tiếp

Phải dừng nếu gặp một trong các trường hợp:

- cần sửa `scripts/run_pipeline.py`
- contract lệch quá rộng giữa mobile và backend, không thể vá nhỏ an toàn
- thay đổi bắt đầu lan sang Phase B hoặc phần auth/plan không liên quan
- test fail ở phần không liên quan và chưa xác định rõ nguyên nhân
- workspace bẩn xung đột với file mình đang cần sửa

Khi dừng, phải báo lại:

1. đang debug cái gì
2. đã chạy lệnh gì
3. lệnh nào fail
4. file nào đã sửa
5. bước nhỏ nhất tiếp theo nên làm

---

## 8. Giá trị lâu dài của bộ này

Runbook + script này giúp:

- giảm phụ thuộc vào trí nhớ của từng agent
- giảm token vì không phải lặp lại reasoning nền mỗi lần debug
- giảm nguy cơ sửa sai tầng
- tăng tốc xác định lỗi là ở mobile, Node hay Python
- tạo quy trình ổn định để tiếp tục mở rộng test/smoke scripts về sau

Đây là nền tốt hơn việc cài thêm nhiều MCP ngay từ đầu, vì nó gắn trực tiếp với repo và workflow thật của dự án.
