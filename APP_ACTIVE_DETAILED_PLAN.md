# Active Detailed Plan

## Initiative active

`Prescription Plan Group Redesign`

---

## 0. Mục tiêu giao sản phẩm

Đưa app sang mô hình:

- `1 kế hoạch`
- `n` khung giờ
- mỗi khung giờ có `n` thuốc
- mỗi thuốc có `pills` riêng theo giờ

Người dùng phải cảm thấy đang tạo **một kế hoạch thuốc hoàn chỉnh**, không phải nhiều record thuốc rời rạc.

---

## 1. Thứ tự đọc bắt buộc

1. `AGENTS.md`
2. `AGENT_START_HERE.md`
3. `APP_ACTIVE_GENERAL_PLAN.md`
4. `APP_ACTIVE_DETAILED_PLAN.md`
5. `docs/phase_a_debug_runbook.md`
6. `mobile/lib/features/create_plan/domain/plan.dart`
7. `mobile/lib/features/create_plan/data/plan_repository.dart`
8. `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
9. `mobile/lib/features/home/domain/today_schedule.dart`
10. `mobile/lib/features/home/presentation/home_screen.dart`
11. `mobile/lib/features/plan/presentation/plan_list_screen.dart`
12. `mobile/lib/features/plan/presentation/plan_detail_screen.dart`
13. `mobile/lib/core/notifications/notification_service.dart`
14. `server-node/src/config/migrate.js`
15. `server-node/src/routes/plan.routes.js`
16. `server-node/src/services/plan.service.js`
17. `server-node/tests/unit/plan.service.test.js`
18. `server-node/tests/integration/plan.routes.test.js`

---

## 2. Phạm vi được sửa

### In scope

- `mobile/lib/features/create_plan/domain/plan.dart`
- `mobile/lib/features/create_plan/data/plan_repository.dart`
- `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
- `mobile/lib/features/home/domain/today_schedule.dart`
- `mobile/lib/features/home/presentation/home_screen.dart`
- `mobile/lib/features/home/data/today_schedule_notifier.dart`
- `mobile/lib/features/plan/presentation/plan_list_screen.dart`
- `mobile/lib/features/plan/presentation/plan_detail_screen.dart`
- `mobile/lib/core/notifications/notification_service.dart`
- `server-node/src/config/migrate.js`
- `server-node/src/routes/plan.routes.js`
- `server-node/src/services/plan.service.js`
- `server-node/tests/unit/plan.service.test.js`
- `server-node/tests/integration/plan.routes.test.js`

### Out of scope

- scan camera
- scan review
- Phase B
- auth
- `scripts/run_pipeline.py`

---

## 3. Thiết kế mục tiêu

### Backend

Nguồn sự thật mới phải là plan group với các thực thể:

- `prescription_plans`
- `prescription_plan_drugs`
- `prescription_plan_slots`
- `prescription_plan_slot_drugs`
- `prescription_plan_logs`

Không tiếp tục dựa nghiệp vụ vào `medication_plans` cũ.

### Mobile

Nguồn sự thật mới phải là:

- `Plan` có nhiều `drugs`
- `Plan` có nhiều `slots`
- mỗi `slot` có nhiều `drug items`

---

## 4. Lát cắt triển khai

## 9A — Backend foundation mới

Mục tiêu:

- tạo schema mới và route/service mới cho plan group

Việc phải làm:

1. migration cho bảng mới
2. create/update/get/delete/log/today dùng bảng mới
3. route schema nhận payload plan group mới

Điều kiện xong:

- backend save/read/log/today summary theo group plan hoạt động

## 9B — Mobile domain/repository mới

Mục tiêu:

- mobile parse và gửi đúng payload plan group

Việc phải làm:

1. model `Plan` mới
2. repository create/update/get theo model mới
3. giữ create flow dùng được với schedule screen

Điều kiện xong:

- mobile giao tiếp được với backend model mới

## 9C — Schedule screen mới

Mục tiêu:

- schedule screen save một `plan group` duy nhất

Việc phải làm:

1. schedule dùng `khung giờ -> thuốc -> số viên`
2. save ra một request duy nhất
3. summary trước khi lưu đúng với model mới

Điều kiện xong:

- user tạo được một kế hoạch nhiều thuốc nhiều giờ và lưu thành công

## 9D — Home / today / list / detail

Mục tiêu:

- hiển thị đúng mô hình mới

Việc phải làm:

1. home hiển thị theo `dose slot`
2. plan list/detail hiển thị theo `plan group`
3. log dose theo slot occurrence đúng

Điều kiện xong:

- app nhất quán với mô hình mới ở các màn chính

---

## 5. Luật dừng

Phải dừng nếu:

1. thay đổi bắt đầu lan sang scan flow hoặc Phase B
2. schema mới cần rộng hơn mức đã chốt
3. test fail ở phần không liên quan mà chưa rõ nguyên nhân
4. workspace xung đột trực tiếp với file đang làm

Khi dừng phải báo:

1. đã làm gì
2. file đã sửa
3. test đã chạy
4. blocker là gì
5. bước nhỏ nhất tiếp theo

---

## 6. Test bắt buộc

### Mobile

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

### Node

```bash
cd server-node && npm test -- tests/unit/plan.service.test.js tests/integration/plan.routes.test.js
```

### Manual checkpoint

1. tạo một kế hoạch có nhiều thuốc và nhiều giờ
2. lưu thành công
3. home/today hiển thị đúng theo slot

---

## 7. Trạng thái hiện tại

- `9A`, `9B`, `9C` đang được triển khai.
- `9D` mới chỉ vá tạm một số hiển thị, chưa hoàn chỉnh theo group plan.
- Sau khi xong `9A + 9B + 9C`, phải dừng để user test create/save trước khi hoàn thiện `9D`.
