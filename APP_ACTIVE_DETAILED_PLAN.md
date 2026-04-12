# Active Detailed Plan

## Initiative active

`Việt hóa toàn bộ phần hiển thị cho người dùng trong app`

---

## 0. Mục tiêu giao sản phẩm

App phải hiển thị tiếng Việt thống nhất, dễ hiểu và có dấu ở mọi nơi người dùng nhìn thấy, đồng thời dựng được nền quản lý text tập trung để các lần sửa sau không quay lại hard-code phân tán.

---

## 1. Thứ tự đọc bắt buộc

1. `AGENTS.md`
2. `AGENT_START_HERE.md`
3. `APP_ACTIVE_GENERAL_PLAN.md`
4. `APP_ACTIVE_DETAILED_PLAN.md`
5. `docs/phase_a_debug_runbook.md`
6. `mobile/pubspec.yaml`
7. `mobile/lib/main.dart`
8. `mobile/lib/app.dart`
9. `mobile/lib/core/router/app_router.dart`
10. `mobile/lib/core/constants.dart`
11. `mobile/lib/shared/widgets/main_shell.dart`
12. `mobile/lib/core/notifications/notification_service.dart`
13. `mobile/lib/features/auth/presentation/login_screen.dart`
14. `mobile/lib/features/auth/presentation/register_screen.dart`
15. `mobile/lib/features/auth/data/auth_notifier.dart`
16. `mobile/lib/features/create_plan/presentation/create_plan_screen.dart`
17. `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart`
18. `mobile/lib/features/create_plan/presentation/scan_review_screen.dart`
19. `mobile/lib/features/create_plan/presentation/edit_drugs_screen.dart`
20. `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
21. `mobile/lib/features/create_plan/presentation/widgets/drug_entry_sheet.dart`
22. `mobile/lib/features/home/presentation/home_screen.dart`
23. `mobile/lib/features/drug/presentation/drug_search_screen.dart`
24. `mobile/lib/features/drug/presentation/drug_detail_screen.dart`
25. `mobile/lib/features/plan/presentation/plan_list_screen.dart`
26. `mobile/lib/features/plan/presentation/plan_detail_screen.dart`
27. `mobile/lib/features/history/presentation/history_screen.dart`
28. `mobile/lib/features/history/presentation/scan_history_detail_screen.dart`
29. `mobile/lib/features/settings/presentation/settings_screen.dart`
30. `mobile/lib/features/pill_verification/presentation/pill_verification_screen.dart`
31. `mobile/lib/features/pill_verification/presentation/pill_reference_enrollment_screen.dart`

---

## 2. Phạm vi được sửa

### In scope

- `mobile/pubspec.yaml`
- `mobile/lib/main.dart`
- `mobile/lib/app.dart`
- `mobile/lib/core/router/app_router.dart`
- `mobile/lib/core/constants.dart`
- `mobile/lib/core/notifications/notification_service.dart`
- `mobile/lib/shared/widgets/main_shell.dart`
- `mobile/l10n.yaml`
- `mobile/lib/l10n/**`
- `mobile/lib/features/auth/**`
- `mobile/lib/features/create_plan/presentation/**`
- `mobile/lib/features/home/**`
- `mobile/lib/features/drug/**`
- `mobile/lib/features/plan/**`
- `mobile/lib/features/history/**`
- `mobile/lib/features/settings/**`
- `mobile/lib/features/pill_verification/**`
- các file `data/notifier/repository` trong `mobile/lib/` nếu chúng đang tạo error/status text hiển thị cho user

### Out of scope

- `server-node/**`
- `server/**`
- `core/**`
- mọi thay đổi schema, database, contract API hoặc business logic chỉ để phục vụ việc dịch chữ
- `mobile/lib/features/scan/presentation/scan_screen.dart` nếu route này vẫn không active
- `scripts/run_pipeline.py`

---

## 3. Thiết kế mục tiêu

### Foundation

- thêm hạ tầng Flutter localization tối thiểu nhưng đúng chuẩn
- app phải có `localizationsDelegates`, `supportedLocales` và default locale rõ ràng
- text phải đi qua `AppLocalizations` hoặc một catalog message tập trung tương đương

### Copy strategy

- ưu tiên tiếng Việt có dấu, ngắn, dễ hiểu với người dùng phổ thông
- không lộ message kỹ thuật hoặc raw exception nếu có thể map sang câu thân thiện hơn
- các trạng thái lặp lại như loading, empty, success, retry, confirm phải cùng một giọng văn

### Formatting

- ngày giờ và text động phải theo ngữ cảnh tiếng Việt
- status label và notification copy phải nhất quán giữa các màn

---

## 4. Lát cắt triển khai

## L10N-1 — Foundation và shared copy

Mục tiêu:

- dựng nền localization đủ dùng cho app hiện tại
- chuyển app shell và text dùng lại nhiều nơi sang lớp tập trung

File chính:

- `mobile/pubspec.yaml`
- `mobile/lib/main.dart`
- `mobile/lib/app.dart`
- `mobile/lib/core/router/app_router.dart`
- `mobile/lib/core/constants.dart`
- `mobile/lib/shared/widgets/main_shell.dart`
- `mobile/lib/core/notifications/notification_service.dart`
- `mobile/l10n.yaml`
- `mobile/lib/l10n/**`

Việc phải làm:

1. thêm cấu hình localization codegen và wiring vào app root
2. tạo catalog tiếng Việt ban đầu cho app title, nav labels, route fallback title, notification channel/title/body
3. bỏ các chuỗi shared đang hard-code hoặc không dấu khỏi shell/router/service

Điều kiện xong:

- app boot được với localization delegates hoạt động
- shared UI chính không còn hard-code user-facing text rải rác

## L10N-2 — Core flow của người dùng

Mục tiêu:

- việt hóa sạch luồng người dùng chạm nhiều nhất

File chính:

- `mobile/lib/features/auth/presentation/login_screen.dart`
- `mobile/lib/features/auth/presentation/register_screen.dart`
- `mobile/lib/features/auth/data/auth_notifier.dart`
- `mobile/lib/features/home/presentation/home_screen.dart`
- `mobile/lib/features/create_plan/presentation/create_plan_screen.dart`
- `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart`
- `mobile/lib/features/create_plan/presentation/scan_review_screen.dart`
- `mobile/lib/features/create_plan/presentation/edit_drugs_screen.dart`
- `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
- `mobile/lib/features/create_plan/presentation/widgets/drug_entry_sheet.dart`

Việc phải làm:

1. đưa toàn bộ title, helper text, CTA, dialog, snackbar, validation và loading copy sang lớp localization
2. chuẩn hóa câu chữ cho luồng `tạo kế hoạch -> quét -> xác nhận -> lập lịch`
3. thay các error text thô hoặc không dấu bằng copy tiếng Việt ngắn gọn

Điều kiện xong:

- luồng Phase A app path không còn text English hoặc ASCII không dấu
- user có thể đi hết luồng chính mà không gặp copy lệch tông

## L10N-3 — Surface phụ và trạng thái hệ thống

Mục tiêu:

- làm sạch các màn ngoài luồng chính nhưng vẫn là phần app user-facing hằng ngày

File chính:

- `mobile/lib/features/drug/**`
- `mobile/lib/features/plan/**`
- `mobile/lib/features/history/**`
- `mobile/lib/features/settings/**`
- các `repository/notifier` liên quan nếu đang đẩy error text ra UI

Việc phải làm:

1. việt hóa drug search/detail, plan list/detail, history và settings
2. chuẩn hóa empty state, retry state, confirmation dialog và snackbar ở các màn này
3. map các lỗi repository/notifier sang copy tiếng Việt phù hợp trước khi hiển thị

Điều kiện xong:

- toàn bộ các tab chính trong bottom nav hiển thị nhất quán bằng tiếng Việt có dấu

## L10N-4 — Pill verification và sweep cuối

Mục tiêu:

- dọn phần copy còn sót lại và chốt chất lượng toàn app

File chính:

- `mobile/lib/features/pill_verification/**`
- các file mobile còn sót lại sau grep sweep

Việc phải làm:

1. việt hóa các màn pill verification ở mức hiển thị, không đụng logic Phase B
2. rà toàn bộ `mobile/lib` để loại bỏ chuỗi user-facing tiếng Anh hoặc không dấu còn sót
3. chuẩn hóa lần cuối notification copy, status text và route fallback copy

Điều kiện xong:

- grep sweep không còn chuỗi user-facing lệch chuẩn trên các route active
- app có một giọng văn thống nhất từ đầu đến cuối

---

## 5. Luật dừng

Phải dừng nếu:

1. để hoàn thành việc Việt hóa mà bắt buộc phải đổi contract hoặc business logic backend
2. thay đổi bắt đầu lan sang refactor UX lớn ngoài mục tiêu copy/localization
3. cần sửa `scripts/run_pipeline.py` hoặc phần core pipeline
4. test fail ở phần không liên quan và chưa rõ nguyên nhân
5. workspace bẩn xung đột trực tiếp với file mobile đang làm

Khi dừng phải báo:

1. đang làm lát cắt nào
2. đã làm gì
3. file nào đã sửa
4. test nào đã chạy
5. blocker là gì
6. bước nhỏ nhất tiếp theo nên làm

---

## 6. Test bắt buộc

### Mobile

```bash
cd mobile && flutter gen-l10n
cd mobile && flutter analyze
cd mobile && flutter test
```

### App-path safety check

```bash
bash scripts/debug_phase_a_checks.sh --quick
```

### Manual checkpoint

1. mở app và kiểm tra bottom nav, app title, route chuyển màn đều là tiếng Việt
2. đi luồng `Đăng nhập/Đăng ký -> Trang chủ -> Tạo kế hoạch -> Quét đơn thuốc -> Xác nhận -> Lập lịch`
3. kiểm tra `Thuốc`, `Kế hoạch`, `Lịch sử`, `Cài đặt` không còn text English hoặc không dấu
4. kiểm tra snackbar, dialog và notification copy đều là tiếng Việt có dấu

---

## 7. Trạng thái hiện tại

- plan root cũ về `Prescription Plan Group Redesign` đã được park để tránh lẫn scope
- các file slice legacy `7A/7B/7C` đã được dọn khỏi root
- execution slice đầu tiên nên mở là `L10N-1`
