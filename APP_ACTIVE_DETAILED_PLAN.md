# Active Detailed Plan

## Initiative active

`Ổn định và tái cấu trúc app nhắc uống thuốc`

---

## 0. Lát cắt active hiện tại

`HOME-1A — Home priority fix`

Mục tiêu của lát cắt này là làm cho Home chỉ foreground các thuốc `tới giờ uống` và `sắp tới trong ngày`, đồng thời loại bỏ hoàn toàn CTA Phase B khỏi path chính trên Home.

Lát cắt này chỉ xử lý presentation và logic nhẹ ở Home. Không xử lý branding, history, create flow, notifications hay backend.

---

## 1. Thứ tự đọc bắt buộc

1. `AGENTS.md`
2. `AGENT_START_HERE.md`
3. `APP_ACTIVE_GENERAL_PLAN.md`
4. `APP_ACTIVE_DETAILED_PLAN.md`
5. `docs/phase_a_debug_runbook.md`
6. `mobile/lib/features/home/presentation/home_screen.dart`
7. `mobile/lib/features/home/domain/today_schedule.dart`
8. `mobile/lib/features/home/data/today_schedule_notifier.dart`
9. `mobile/lib/l10n/app_vi.arb`

---

## 2. Phạm vi được sửa

### In scope

- `mobile/lib/features/home/presentation/home_screen.dart`
- `mobile/lib/features/home/domain/today_schedule.dart`
- `mobile/lib/features/home/data/today_schedule_notifier.dart`
- `mobile/lib/l10n/app_vi.arb` nếu thật sự cần thêm key nhỏ để Home tự nhiên hơn
- tối đa 1 helper nhỏ ngay trong `mobile/lib/features/home/**` nếu thật sự cần để phân loại due-now / upcoming

### Out of scope

- `server-node/**`
- `server/**`
- `core/**`
- `scripts/run_pipeline.py`
- `mobile/lib/features/create_plan/**`
- `mobile/lib/features/history/**`
- `mobile/lib/features/settings/**`
- `mobile/lib/features/drug/**`
- `mobile/lib/core/router/app_router.dart`
- mọi thay đổi branding, reminders, history redesign, create flow UX, local-first storage

---

## 3. Bối cảnh đã chốt trước khi vào lát cắt này

- `REL-1A` đã xong và runtime local hiện ổn định
- `REL-1B` đã xong và mobile network diagnostics cơ bản đã được cải thiện
- `IA-0A` và `HOME-1A-PREP` đã chốt các vấn đề chính ở Home:
  1. Home đang foreground quá nhiều thứ cùng lúc
  2. CTA Phase B đang lộ trong path chính
  3. toàn bộ doses đang render phẳng, không ưu tiên theo thời điểm
  4. working default đã khóa: `due-now = ±30 phút`
- task này chưa đụng router, chưa xóa route Phase B, chỉ ẩn lối vào từ Home

---

## 4. Việc phải làm trong lát cắt này

1. Ẩn hoàn toàn CTA/nút Phase B khỏi các tile ở Home
2. Chia doses pending trên Home thành tối thiểu 2 nhóm hiển thị:
   - `Đến giờ uống`
   - `Sắp tới trong ngày`
3. Giữ lại các hành động chính cho due-now:
   - `Đã uống`
   - `Bỏ qua`
4. Chỉ làm thay đổi nhỏ nhất cần thiết ở presentation/data helper để đạt được việc foreground đúng thời điểm
5. Không mở rộng sang `HOME-1B` như auto-refresh, missed treatment sâu, hay nav refactor

---

## 5. Tiêu chí xong

- Home không còn hiện CTA Phase B
- Home foreground đúng 2 nhóm chính: due-now và upcoming
- due-now window dùng mặc định `±30 phút`
- analyze/test pass
- `flutter analyze` và `flutter test` pass
- không phát sinh sửa ngoài file scope đã chốt

---

## 6. Luật dừng

Phải dừng nếu:

1. để hoàn thành slice này mà phải đổi contract giữa mobile / node / python
2. bắt đầu lan sang redesign flow lớn của History / Create / Branding / Notifications
3. cần sửa `server-node/**`, `server/**`, `core/**`, `scripts/run_pipeline.py` hoặc `app_router.dart`
4. muốn xử lý luôn `missed` / auto-refresh / nav refactor trong cùng slice

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
cd mobile && flutter analyze
cd mobile && flutter test
```

### Manual smoke sau slice này

1. Home không còn thấy dòng/nút Phase B kiểu `Chụp mẫu` / `Xác minh`
2. Dose gần giờ uống nằm trong section `Đến giờ uống`
3. Dose còn xa hơn nằm trong `Sắp tới trong ngày`
4. Nút `Đã uống` và `Bỏ qua` vẫn hoạt động như cũ

---

## 8. Sau lát cắt này mở gì tiếp

Song song với execution của `HOME-1A`, planner sẽ lấy kết quả từ các track đọc/spec hoặc coding nhỏ:

- `REMIND-1A-R1B` — logic reschedule đúng khi bật lại reminder
- `HISTORY-1A-S1` — mobile-only IA shift
- `BRAND-1A-ASSET-PREP` — exact asset pipeline brief

Sau khi `HOME-1A` xong, slice code kế tiếp nên ưu tiên một trong hai hướng tùy planner chốt:

- `BRAND-1A — brand/copy cleanup không đụng package rename`
- hoặc `HISTORY-1A-S1` nếu planner muốn khóa information architecture trước

`HOME-1B`, `REMIND-1C`, `LOCAL-1A` chỉ nên mở sau khi planner đọc xong output từ batch tiếp theo.
