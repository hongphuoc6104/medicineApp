# Active Detailed Plan

## Initiative active

`Ổn định và tái cấu trúc app nhắc uống thuốc`

---

## 0. Lát cắt active hiện tại

`REL-1A — Harden local startup và scan runtime detection`

Mục tiêu của lát cắt này là làm cho local dev path không còn silently rơi sang runtime sai sau cleanup hoặc sau khi port bị chiếm, từ đó giảm lỗi kiểu `không kết nối được với máy chủ` hoặc `scan 0 drugs` do hạ tầng local bị lệch.

Lát cắt này chỉ xử lý reliability baseline ở startup/runtime. Không xử lý home logic, branding, history hoặc UX create flow.

---

## 1. Thứ tự đọc bắt buộc

1. `AGENTS.md`
2. `AGENT_START_HERE.md`
3. `APP_ACTIVE_GENERAL_PLAN.md`
4. `APP_ACTIVE_DETAILED_PLAN.md`
5. `docs/phase_a_debug_runbook.md`
6. `CLEANUP_REPORT_2026_04_12.md`
7. `dev.sh`
8. `scripts/debug_phase_a_checks.sh`
9. `server/main.py`
10. `docker-compose.yml`

---

## 2. Phạm vi được sửa

### In scope

- `dev.sh`
- `scripts/debug_phase_a_checks.sh`
- `server/main.py`
- `docs/phase_a_debug_runbook.md`

### Out of scope

- mọi file mobile UI
- `server-node/**`
- `core/**`
- `scripts/run_pipeline.py`
- mọi thay đổi business logic scan / OCR / NER
- mọi thay đổi branding, history, home logic, notifications, create flow UX

---

## 3. Bối cảnh đã chốt trước khi vào lát cắt này

- `venv/` đã bị xóa trong cleanup
- `dev.sh` cũ hard-code `venv/bin/activate` và fail giữa chừng
- local Python AI đã từng không lên, khiến app-path scan rơi sang runtime sai
- container `medicineapp_ai` từng giữ `:8000` và trả OCR rỗng
- local Python AI runtime hiện đã được phục hồi thủ công để user test tiếp, nhưng startup path và debug path vẫn chưa được harden ở mức code/script
- mục tiêu của slice này là làm cho vấn đề đó khó tái diễn và dễ phát hiện hơn

---

## 4. Việc phải làm trong lát cắt này

1. thêm guard rõ ràng trong `dev.sh` khi thiếu `venv/` hoặc local interpreter phù hợp
2. thêm check xung đột port `8000` để không silently chạy nhầm runtime/container cũ
3. cải thiện tín hiệu health/runtime ở `server/main.py` để debug script và dev path phân biệt được trạng thái scan runtime rõ hơn
4. cập nhật `scripts/debug_phase_a_checks.sh` để failure mode về local Python runtime rõ ràng hơn
5. cập nhật `docs/phase_a_debug_runbook.md` để phản ánh startup path sau cleanup và các dấu hiệu lỗi runtime đúng tầng

---

## 5. Tiêu chí xong

- `bash dev.sh` khi thiếu `venv/` phải fail fast với hướng dẫn rõ ràng
- `bash dev.sh` khi `:8000` bị chiếm phải báo đúng conflict thay vì để app-path đi sang runtime sai
- `scripts/debug_phase_a_checks.sh` phải báo rõ nếu local AI/runtime path không sẵn sàng
- `curl /api/health` của Python AI phải cho thêm tín hiệu đủ để debug runtime tốt hơn hiện tại
- không phát sinh sửa ngoài 4 file đã chốt

---

## 6. Luật dừng

Phải dừng nếu:

1. để hoàn thành slice này mà phải sửa `core/pipeline.py` hoặc `scripts/run_pipeline.py`
2. cần thay đổi contract scan giữa mobile / node / python
3. bắt đầu lan sang mobile UI hoặc create flow UX
4. failure nằm ở package/runtime host ngoài phạm vi script hardening và chưa có đường vá nhỏ an toàn

Khi dừng phải báo:

1. đã làm gì
2. file đã sửa
3. test nào đã chạy
4. blocker là gì
5. bước nhỏ nhất tiếp theo

---

## 7. Test bắt buộc

### Runtime / scripts

```bash
bash scripts/debug_phase_a_checks.sh --quick
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:3001/api/health
```

### Manual smoke sau slice này

1. chạy `bash dev.sh`
2. xác nhận local stack lên đúng
3. quét lại 1 ảnh known-good trên điện thoại
4. xác nhận app không còn rơi vào lỗi runtime silent kiểu `0 drugs` do startup path lệch

---

## 8. Sau lát cắt này mở gì tiếp

Song song với execution của `REL-1A`, planner sẽ lấy kết quả từ các track đọc/spec:

- `IA-0A` — home/create/history redesign spec
- `LOCAL-0A` — local-first/reminder architecture audit
- `BRAND-0A` — branding/copy/naming shortlist

Sau khi `REL-1A` xong, slice code kế tiếp nên là:

- `REL-1B — Mobile network diagnostics và reconnect UX`

Chỉ sau khi reliability baseline ổn mới nên mở mạnh sang `BRAND-1`, `HOME-1`, `FLOW-1A`.
