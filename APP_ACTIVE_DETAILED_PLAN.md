# Active Detailed Plan

## Initiative active

`Việt hóa toàn bộ phần hiển thị cho người dùng trong app`

---

## 0. Lát cắt active hiện tại

`MVT-1 — Manual verify gate cho core flow sau L10N-2 clean pass`

Mục tiêu của lát cắt này là giữ nguyên trạng thái code hiện tại, để user manual verify core flow chính của app sau khi `L10N-2` đã clean pass.

Không mở `L10N-3A` cho đến khi manual verify pass hoặc có kết luận rõ ràng rằng cần một hotfix nhỏ trước.

---

## 1. Thứ tự đọc bắt buộc

1. `AGENTS.md`
2. `AGENT_START_HERE.md`
3. `APP_ACTIVE_GENERAL_PLAN.md`
4. `APP_ACTIVE_DETAILED_PLAN.md`
5. `docs/phase_a_debug_runbook.md`
6. `mobile/lib/l10n/app_vi.arb`
7. `mobile/lib/app.dart`
8. `mobile/lib/shared/widgets/main_shell.dart`
9. `mobile/lib/features/auth/presentation/login_screen.dart`
10. `mobile/lib/features/auth/presentation/register_screen.dart`
11. `mobile/lib/features/home/presentation/home_screen.dart`
12. `mobile/lib/features/create_plan/presentation/create_plan_screen.dart`
13. `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart`
14. `mobile/lib/features/create_plan/presentation/scan_review_screen.dart`
15. `mobile/lib/features/create_plan/presentation/edit_drugs_screen.dart`
16. `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
17. `mobile/lib/features/create_plan/presentation/widgets/drug_entry_sheet.dart`

---

## 2. Phạm vi được sửa

### In scope

- chuẩn bị checklist manual verify cho user
- rà lại đúng các màn thuộc core flow đã được Việt hóa
- tổng hợp expected outcome, pass/fail criteria và residual risks để user test thủ công

### Out of scope

- mọi code edit vào app ở lát cắt này
- `server-node/**`
- `server/**`
- `core/**`
- mọi thay đổi schema, database, contract API hoặc business logic chỉ để phục vụ việc dịch chữ
- `mobile/lib/features/drug/**`
- `mobile/lib/features/plan/**`
- `mobile/lib/features/history/**`
- `mobile/lib/features/settings/**`
- `mobile/lib/features/pill_verification/**`
- `scripts/run_pipeline.py`

---

## 3. Bối cảnh đã chốt trước khi vào lát cắt này

- `L10N-1` đã hoàn tất: foundation localization + shared copy
- `L10N-2A` đã hoàn tất: auth + home + create entry
- `L10N-2B` đã hoàn tất phần implement chính và đã qua review
- `L10N-2B-HF1` đã hoàn tất:
  1. bỏ 2 label `OK` hard-code trong `scan_camera_screen.dart`
  2. bỏ summary line ghép chuỗi thô trong `set_schedule_screen.dart`
- `cd mobile && flutter gen-l10n` đã pass
- `cd mobile && flutter analyze` đã pass
- `cd mobile && flutter test` đã pass
- còn 1 residual risk đã biết: `guidance` do server trả về trong scan flow có thể không hoàn toàn localize nếu backend trả text ngoài chuẩn UI

---

## 4. Việc phải làm trong lát cắt này

1. chốt checklist manual verify cho user theo đúng flow chính
2. mô tả expected text/behavior cần nhìn thấy ở từng màn để user test nhanh
3. nêu rõ pass condition để được mở `L10N-3A`
4. nêu rõ fail condition để mở lại hotfix nhỏ thay vì nhảy sang slice mới

---

## 5. Tiêu chí xong

- user có checklist test thủ công rõ ràng và đủ ngắn để đi hết core flow
- expected outcome ở từng bước đủ rõ để phân biệt pass/fail
- planner có thể dùng kết quả manual verify để quyết định mở `L10N-3A` hoặc hotfix nhỏ
- không phát sinh code edit trong lát cắt này

---

## 6. Luật dừng

Phải dừng nếu:

1. để trả lời manual gate mà phải sửa code mới
2. phát hiện issue mới nhưng chưa xác định được là copy/UI hay logic/contract
3. cần sửa `scripts/run_pipeline.py` hoặc code backend/server để tiếp tục
4. kết quả manual verify mâu thuẫn hoặc không đủ để quyết định mở slice tiếp theo

---

## 7. Test bắt buộc

### Baseline đã xanh trước khi user test

```bash
cd mobile && flutter gen-l10n
cd mobile && flutter analyze
cd mobile && flutter test
```

### Manual checkpoint user phải chạy

1. mở app và đi qua `Đăng nhập/Đăng ký -> Trang chủ -> Tạo kế hoạch`
2. vào `Quét đơn thuốc`, kiểm tra guide/banner/error không còn English hoặc không dấu
3. sang `Xác nhận danh sách thuốc`, kiểm tra title, CTA, search hint và empty state đọc tự nhiên
4. sang `Lập lịch`, kiểm tra section labels, snackbar và dòng summary thuốc đọc tự nhiên bằng tiếng Việt
5. xác nhận toàn flow không có regression rõ ràng do localization

---

## 8. Sau lát cắt này mở gì tiếp

Chỉ sau khi user báo manual verify pass thì mới mở:

- `L10N-3A — Drug + Plan`
- sau đó mới tới `L10N-3B — History + Settings`
- `L10N-4` vẫn để hàng chờ cuối

Nếu user báo lỗi ở core flow, phải mở đúng một hotfix nhỏ theo màn bị lỗi thay vì mở `L10N-3A`.
