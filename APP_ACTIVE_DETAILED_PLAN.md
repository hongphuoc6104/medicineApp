# Active Detailed Plan

## Initiative active

`Ổn định logic và UI/UX app mobile sau đợt audit`

File này là master execution plan và review spec để giao việc cho AI khác.

Mục tiêu của file này không phải để một AI ôm cả epic trong một lần, mà để:

1. chia toàn bộ vấn đề thành các slice nhỏ, rõ scope
2. chỉ rõ nên sửa gì, làm gì, làm ra sao
3. chỉ ra các lỗ hổng thường bị làm sai
4. cung cấp checklist review khắt khe để loại bài làm hời hợt

---

## Cách dùng file này

1. Planner chỉ giao đúng một slice cho mỗi AI execution trong một lần.
2. Khi giao việc, luôn gửi kèm phần `Quy tắc toàn cục`, `Protocol output bắt buộc`, và đúng section của slice đó.
3. Reviewer phải đối chiếu output của AI execution với section `Checklist review khắt khe` trước khi chấp nhận.
4. Nếu AI execution sửa ngoài scope slice hoặc claim pass mà không có bằng chứng test, coi như fail.

---

## Quy tắc toàn cục

1. Luôn đọc `AGENTS.md`, `AGENT_START_HERE.md`, `APP_ACTIVE_GENERAL_PLAN.md`, rồi mới đọc section slice tương ứng.
2. Không được sửa `scripts/run_pipeline.py`, `core/**`, `server/**` hoặc `server-node/**` trừ khi slice nói rõ backend contract là blocker thật.
3. Ưu tiên patch nhỏ, trực tiếp, không refactor rộng để “làm đẹp code”.
4. Không được tạo abstraction mới nếu chỉ để bọc một hành vi đơn lẻ.
5. Mọi text user-facing mới hoặc sửa lại phải là tiếng Việt có dấu.
6. Nếu đụng user-facing copy trên màn đã có l10n, ưu tiên đi qua l10n thay vì hardcode thêm.
7. Không được báo “đã xong” nếu chưa chạy `flutter analyze` và `flutter test` trong `mobile/`, trừ khi bị blocker thật và có nêu rõ.
8. Không được claim fix logic nếu chưa chỉ ra trạng thái trước và sau thay đổi.
9. Không được che giấu state xấu bằng UI wording dễ gây hiểu lầm.
10. Nếu phát hiện bug nằm ở backend contract, phải dừng, ghi blocker rõ ràng, không vá bừa ở mobile.

---

## Protocol output bắt buộc cho mọi AI execution

AI execution phải trả đúng các mục sau trong báo cáo cuối:

1. `Slice ID`
2. `Issue IDs đã xử lý`
3. `Files đã đọc`
4. `Files đã sửa`
5. `Cách sửa chính`
6. `Những gì cố ý không sửa`
7. `Lệnh test đã chạy`
8. `Kết quả test`
9. `Manual smoke đã kiểm tra / chưa kiểm tra`
10. `Rủi ro còn lại`

Nếu thiếu bất kỳ mục nào ở trên, reviewer có quyền reject ngay.

---

## Inventory vấn đề đã xác nhận

| ID | Mức độ | Vấn đề | File chính |
|---|---|---|---|
| `STATE-1` | P0 | Đánh dấu liều offline báo như đã sync xong | `mobile/lib/features/home/data/today_schedule_notifier.dart`, `mobile/lib/features/home/presentation/home_screen.dart` |
| `STATE-2` | P0 | `Sync now` ở Settings có thể báo thành công giả | `mobile/lib/features/settings/presentation/settings_screen.dart`, `mobile/lib/features/home/data/plan_notifier.dart`, `mobile/lib/features/home/data/today_schedule_notifier.dart` |
| `AUTH-1` | P0 | Refresh token fail không đồng bộ auth state với router | `mobile/lib/core/network/dio_client.dart`, `mobile/lib/features/auth/data/auth_notifier.dart`, `mobile/lib/core/router/app_router.dart` |
| `PLAN-1` | P0 | Save plan mới xong không làm tươi `today schedule` | `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart` |
| `PLAN-2` | P0 | End/reactivate plan chưa chặt với notification scheduling | `mobile/lib/features/plan/presentation/plan_detail_screen.dart`, `mobile/lib/core/notifications/notification_service.dart` |
| `NAV-1` | P0 | `/settings` làm sáng tab `History` sai ngữ cảnh | `mobile/lib/shared/widgets/main_shell.dart` |
| `NAV-2` | P0 | Back từ Settings nhảy cứng về `/home` | `mobile/lib/features/settings/presentation/settings_screen.dart` |
| `HOME-1` | P0 | Home hiện empty state sai khi user đã xử lý hết liều trong ngày | `mobile/lib/features/home/presentation/home_screen.dart` |
| `CREATE-1` | P1 | Reuse/back flow làm đẹp hóa dữ liệu scan cũ | `mobile/lib/features/history/presentation/scan_history_detail_screen.dart`, `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart` |
| `CREATE-2` | P1 | Scan review thiếu badge/lý do rõ ràng cho item cần kiểm tra | `mobile/lib/features/create_plan/presentation/scan_review_screen.dart`, `mobile/lib/features/create_plan/domain/scan_result.dart` |
| `CAM-1` | P1 | Preview tap là capture, dễ chụp nhầm | `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart` |
| `CAM-2` | P1 | Camera flow thiếu framing guidance và recovery UX đủ rõ | `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart` |
| `SEARCH-1` | P1 | Search thuốc bị race condition do không debounce/cancel | `mobile/lib/features/drug/data/drug_search_notifier.dart`, `mobile/lib/features/drug/presentation/drug_search_screen.dart` |
| `HISTORY-1` | P1 | History/logs mới chỉ nối page đầu | `mobile/lib/features/history/data/scan_history_notifier.dart`, `mobile/lib/features/history/data/medication_logs_notifier.dart`, repositories liên quan |
| `UX-1` | P1 | Loading/error/empty state chưa đồng bộ | nhiều màn `mobile/lib/features/**/presentation/*.dart` |
| `UX-2` | P1 | Copy/l10n còn hardcoded và không nhất quán | `history`, `settings`, `drug`, `plan`, `pill_verification` |
| `UX-3` | P1 | Accessibility semantics gần như chưa có cho custom controls | `mobile/lib/shared/widgets/main_shell.dart`, `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart` |
| `UX-4` | P1 | Một số màn không đủ scroll/responsive | `mobile/lib/features/auth/presentation/login_screen.dart`, `mobile/lib/features/create_plan/presentation/create_plan_screen.dart` |
| `UX-5` | P1 | `Hồ sơ` trong Settings là dead-end | `mobile/lib/features/settings/presentation/settings_screen.dart` |
| `DRUG-1` | P1 | Drug search/detail dùng title giống nhau và show raw score khó hiểu | `mobile/lib/features/drug/presentation/drug_search_screen.dart`, `mobile/lib/features/drug/presentation/drug_detail_screen.dart` |
| `PILL-1` | P2 | Pill verification tồn tại nhưng chưa nối vào path chính | `mobile/lib/core/router/app_router.dart`, `mobile/lib/features/home/presentation/home_screen.dart` |
| `PILL-2` | P2 | Confirm pill verification còn gate yếu và dễ sinh state không nhất quán | `mobile/lib/features/pill_verification/presentation/pill_verification_screen.dart` |
| `TEST-1` | P2 | Test coverage gần như không bảo vệ regression thật | `mobile/test/widget_test.dart` và test mới cần thêm |

---

## Thứ tự slice bắt buộc

1. `MOBILE-P0-A` — truthful state, auth, shell navigation
2. `MOBILE-P0-B` — plan/today/reminder integrity
3. `MOBILE-P1-A` — create/scan/reuse truthfulness
4. `MOBILE-P1-B` — search/history completeness và async safety
5. `MOBILE-P1-C` — state UX, copy, l10n, accessibility, responsive cleanup
6. `MOBILE-P2-A` — Phase B mobile entry decision và gating
7. `MOBILE-P2-B` — regression tests

Planner không được giao `P1` hoặc `P2` nếu `P0` chưa qua review.

---

## Slice 1 — `MOBILE-P0-A`

### Tên slice

`truthful state, auth, shell navigation`

### Issue IDs

`STATE-1`, `STATE-2`, `AUTH-1`, `NAV-1`, `NAV-2`

### Mục tiêu

Sửa các điểm làm app nói sai trạng thái thật hoặc điều hướng sai ngữ cảnh cơ bản.

### Đọc bắt buộc trước khi sửa

1. `mobile/lib/core/router/app_router.dart`
2. `mobile/lib/shared/widgets/main_shell.dart`
3. `mobile/lib/core/network/dio_client.dart`
4. `mobile/lib/features/auth/data/auth_notifier.dart`
5. `mobile/lib/features/home/data/today_schedule_notifier.dart`
6. `mobile/lib/features/home/presentation/home_screen.dart`
7. `mobile/lib/features/settings/presentation/settings_screen.dart`

### In scope

- `mobile/lib/core/router/app_router.dart`
- `mobile/lib/shared/widgets/main_shell.dart`
- `mobile/lib/core/network/dio_client.dart`
- `mobile/lib/features/auth/data/auth_notifier.dart`
- `mobile/lib/features/home/data/today_schedule_notifier.dart`
- `mobile/lib/features/home/presentation/home_screen.dart`
- `mobile/lib/features/settings/presentation/settings_screen.dart`

### Out of scope

- create flow sâu
- history/drug/pill verification
- thay đổi backend contract

### Nên sửa gì

1. Đổi contract nội bộ của thao tác `markDose` để phân biệt ít nhất 3 kết quả: `synced`, `queuedOffline`, `failed`.
2. Cập nhật snackbar ở `HomeScreen` để không còn dùng wording thành công giả khi thực tế mới chỉ queue offline.
3. Sửa `Sync now` trong Settings để chỉ báo thành công khi refresh/sync thực sự thành công; nếu fail phải báo fail rõ ràng.
4. Làm cho refresh-token failure cập nhật auth state thật, không chỉ xóa secure storage.
5. Sửa shell index để `/settings` không làm sáng tab `History`.
6. Sửa back từ Settings theo hướng stack-aware: ưu tiên `pop`, nếu không pop được mới fallback route hợp lý.

### Nên làm như thế nào

1. Ưu tiên một result type nhỏ, rõ nghĩa cho `markDose`, thay vì tiếp tục trả `bool` mơ hồ.
2. Auth invalidation phải có một đường owner rõ ràng. Cách chấp nhận được:
   - interceptor gọi vào một state owner dùng chung để đưa app về `unauthenticated`
   - hoặc tạo một session invalidation hook nhỏ ở tầng core/auth
3. Không chấp nhận giải pháp tiếp tục dựa vào “xóa storage rồi chờ cold start sau”.
4. Settings back không được đổi sang route khác nếu trong stack đã có màn trước hợp lệ.

### Lỗ hổng hay bị làm sai

1. Chỉ đổi copy snackbar nhưng vẫn giữ `markDose()` trả `true` cho cả sync lẫn offline queue.
2. Interceptor tự import trực tiếp UI widget hoặc tạo dependency vòng lung tung.
3. Settings không sáng `History` nữa nhưng lại không có trạng thái selected nào rõ ràng.
4. Dùng `context.go('/history')` hay `context.go('/home')` làm “back giả” thay vì back thật.
5. Fix auth bằng cách force redirect nhưng không dọn sạch state auth.

### Tiêu chí accept

1. User phân biệt được `đã đồng bộ` với `đã lưu tạm/chờ đồng bộ`.
2. 401 do refresh fail phải đưa app về unauthenticated một cách ổn định.
3. `/settings` không làm người dùng tưởng đang ở `History`.
4. Back từ Settings không còn nhảy cứng về `/home` trong trường hợp có stack hợp lệ.

### Checklist review khắt khe

1. Có thay `bool` mơ hồ bằng result rõ nghĩa chưa.
2. Có bằng chứng code cho đường `queuedOffline` không.
3. Có đường cập nhật auth state thật khi refresh fail không.
4. Có sửa `MainShell` để `/settings` không sáng `History` không.
5. Có dùng `pop/maybePop` hợp lý thay vì `go('/home')` cho back không.
6. Có giữ patch nhỏ trong scope không.

### Test bắt buộc

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

### Manual smoke bắt buộc

1. Mất mạng khi đánh dấu `Đã uống` hoặc `Bỏ qua` phải ra message kiểu chờ sync.
2. Bật app với token hết hạn phải không kẹt lại trong shell protected.
3. Vào Settings từ Home và từ History đều không còn cảm giác đang ở tab History.

---

## Slice 2 — `MOBILE-P0-B`

### Tên slice

`plan/today/reminder integrity`

### Issue IDs

`PLAN-1`, `PLAN-2`, `HOME-1`

### Mục tiêu

Đảm bảo các thay đổi plan phản ánh ngay vào Home và notification scheduling, không để state chính bị stale hoặc misleading.

### Đọc bắt buộc trước khi sửa

1. `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
2. `mobile/lib/features/plan/presentation/plan_detail_screen.dart`
3. `mobile/lib/features/home/data/plan_notifier.dart`
4. `mobile/lib/features/home/data/today_schedule_notifier.dart`
5. `mobile/lib/features/home/presentation/home_screen.dart`
6. `mobile/lib/core/notifications/notification_service.dart`

### In scope

- `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
- `mobile/lib/features/plan/presentation/plan_detail_screen.dart`
- `mobile/lib/features/home/data/plan_notifier.dart`
- `mobile/lib/features/home/data/today_schedule_notifier.dart`
- `mobile/lib/features/home/presentation/home_screen.dart`
- `mobile/lib/core/notifications/notification_service.dart`

### Out of scope

- scan/reuse/history/drug flow
- backend schema change

### Nên sửa gì

1. Save plan mới xong phải invalidate/refresh đủ cả plans và `today schedule`.
2. End plan phải cancel notification của plan đó hoặc reschedule toàn bộ plans active ngay trong cùng flow.
3. Reactivate plan phải schedule lại notification ngay, không chỉ chờ provider reload mơ hồ.
4. Home không được hiện `_TodayEmptyCard` khi thực tế hôm nay có liều nhưng tất cả đã được xử lý.

### Nên làm như thế nào

1. Sau create/update/delete/reactivate plan, phải có một pattern nhất quán cho:
   - refresh `planNotifierProvider`
   - refresh `todayScheduleNotifierProvider`
   - sync `NotificationService`
2. Với Home, thêm một nhánh completed-day rõ ràng nếu không còn pending nhưng `today.doses` không rỗng.
3. Không được dựa vào side effect ngầm của `PlanNotifier.build()` để coi như scheduling đã đúng tức thời.

### Lỗ hổng hay bị làm sai

1. Chỉ invalidate provider nhưng không đảm bảo scheduling được update ngay.
2. Fix create path nhưng bỏ quên deactivate/reactivate path.
3. Home hết pending thì vẫn rơi vào empty card cũ.
4. Dùng wording “không có liều uống nào” cho một ngày mà user thực tế đã uống xong.

### Tiêu chí accept

1. Tạo plan mới xong về Home thấy dữ liệu hôm nay đúng hơn ngay.
2. End/reactivate plan không để notification cũ hoặc thiếu notification mới.
3. Home phân biệt `không có liều nào hôm nay` với `hôm nay đã xử lý xong tất cả liều`.

### Checklist review khắt khe

1. Có xử lý đủ create, deactivate, reactivate không.
2. Có sync explicit với `NotificationService` không.
3. Có refresh cả `plans` và `today schedule` không.
4. Empty state của Home có còn wording sai ngữ nghĩa không.

### Test bắt buộc

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

### Manual smoke bắt buộc

1. Tạo plan mới, quay về Home, kiểm tra dữ liệu hôm nay.
2. Kết thúc plan, kiểm tra notification không còn giữ plan đó.
3. Kích hoạt lại plan, kiểm tra reminder được schedule lại.

---

## Slice 3 — `MOBILE-P1-A`

### Tên slice

`create/scan/reuse truthfulness`

### Issue IDs

`CREATE-1`, `CREATE-2`, `CAM-1`, `CAM-2`

### Mục tiêu

Làm rõ luồng scan/review/reuse để user không bị dẫn bởi dữ liệu đã bị làm đẹp hóa hoặc affordance mơ hồ.

### Đọc bắt buộc trước khi sửa

1. `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart`
2. `mobile/lib/features/create_plan/presentation/scan_review_screen.dart`
3. `mobile/lib/features/history/presentation/scan_history_detail_screen.dart`
4. `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
5. `mobile/lib/features/create_plan/domain/scan_result.dart`

### In scope

- `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart`
- `mobile/lib/features/create_plan/presentation/scan_review_screen.dart`
- `mobile/lib/features/history/presentation/scan_history_detail_screen.dart`
- `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
- `mobile/lib/features/create_plan/domain/scan_result.dart`

### Out of scope

- settings/auth/history pagination/drug search
- backend OCR contract change

### Nên sửa gì

1. Preserve metadata thật của scan khi đi từ history/reuse/back sang review.
2. Không được tự ép `rejected: false`, `confidence: 1.0`, hay `mappingStatus: confirmed` chỉ để flow đẹp hơn.
3. Card trong scan review phải hiển thị rõ item nào cần kiểm tra và vì sao.
4. Bỏ hoặc thay đổi cơ chế tap toàn preview để capture nếu nó không còn phù hợp với UX mục tiêu.
5. Bổ sung framing guidance rõ hơn, và recovery path rõ hơn khi permission bị chặn hoặc chất lượng ảnh kém.

### Nên làm như thế nào

1. Từ reuse/history detail, truyền lại `ScanResult` càng sát dữ liệu gốc càng tốt.
2. Metadata tối thiểu phải được giữ đúng nếu đã có ở nguồn: `scanId`, `qualityState`, `rejectReason`, `guidance`, `rejected`, `mappingStatus`, `confidence`, `ocrText`, `mappedDrugName`.
3. `needsReview` phải có UI signal hữu hình: badge, banner tổng, hoặc reason text ngắn gọn.
4. Camera screen nên để hành động chụp tập trung vào nút capture chính; nếu vẫn giữ tap-to-capture thì phải có lý do và affordance rất rõ.
5. Không thêm wizard nhiều bước mới nếu chỉ cần sửa signal và state hiện có.

### Lỗ hổng hay bị làm sai

1. Chỉ đổi copy nhưng vẫn dựng dữ liệu scan giả tốt hơn thực tế.
2. Thêm badge đẹp nhưng không gắn với `needsReview` thật.
3. Thêm overlay camera nhưng preview tap vẫn chụp nhầm như cũ.
4. Chỉ sửa reuse flow mà bỏ quên back từ schedule về review.

### Tiêu chí accept

1. Reuse và back flow không còn làm đẹp hóa dữ liệu scan.
2. User nhìn vào scan review biết ngay item nào cần xem lại.
3. Camera flow ít chụp nhầm hơn và hướng dẫn chụp rõ hơn.

### Checklist review khắt khe

1. Có loại bỏ các giá trị fabricated không.
2. Có giữ nguyên `qualityState`, `rejected`, `mappingStatus`, `confidence` hợp lý không.
3. UI signal cho review có bám vào data thật không.
4. Preview tap capture đã được xử lý dứt điểm chưa.
5. `ocrText` và DB suggestion có còn để user đối chiếu khi cần review không.

### Test bắt buộc

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

### Manual smoke bắt buộc

1. Reuse một scan `WARNING` hoặc `REJECT` và kiểm tra review state còn đúng.
2. Từ review sang schedule rồi back lại, metadata review không bị reset giả.
3. Camera screen không chụp nhầm khi user chỉ tap để focus/xem.

---

## Slice 4 — `MOBILE-P1-B`

### Tên slice

`search/history completeness và async safety`

### Issue IDs

`SEARCH-1`, `HISTORY-1`, `DRUG-1`, `UX-1`

### Mục tiêu

Làm cho search và history đủ an toàn ở quy mô dữ liệu lớn hơn, đồng thời bớt misleading về hierarchy và state UX.

### Đọc bắt buộc trước khi sửa

1. `mobile/lib/features/drug/data/drug_search_notifier.dart`
2. `mobile/lib/features/drug/presentation/drug_search_screen.dart`
3. `mobile/lib/features/drug/presentation/drug_detail_screen.dart`
4. `mobile/lib/features/history/data/scan_history_notifier.dart`
5. `mobile/lib/features/history/data/medication_logs_notifier.dart`
6. `mobile/lib/features/history/data/scan_history_repository.dart`
7. `mobile/lib/features/create_plan/data/plan_repository.dart`
8. `mobile/lib/features/history/presentation/history_screen.dart`

### In scope

- `mobile/lib/features/drug/**`
- `mobile/lib/features/history/**`
- `mobile/lib/features/create_plan/data/plan_repository.dart`

### Out of scope

- auth/settings/create camera/pill verification

### Nên sửa gì

1. Add debounce và stale-request guard cho drug search.
2. Không để request cũ overwrite kết quả query mới.
3. Wire pagination hoặc load-more/see-more rõ ràng cho scan history và medication logs.
4. Nếu chưa làm full infinite scroll, vẫn phải làm rõ rằng list đang giới hạn, không được im lặng truncate.
5. Drug search và drug detail phải có title khác nhau.
6. Raw score `0.xx` không nên là UI cuối cho end user nếu không giải thích được giá trị của nó.
7. Chuẩn hóa loading/error/empty state ở các màn thuộc slice này.

### Nên làm như thế nào

1. Debounce nên ở notifier hoặc presentation layer nhưng phải có stale result protection.
2. Pagination nên giữ minimal: load more rõ ràng là đủ, không cần vội virtualized list hay architecture lớn.
3. Nếu vẫn chưa expose full pagination từ UI, phải có explicit note/CTA thay vì cắt cụt âm thầm.
4. Đổi hierarchy copy của màn Drug theo hướng `Tra cứu thuốc` và `Chi tiết thuốc` hoặc tương đương.

### Lỗ hổng hay bị làm sai

1. Debounce bằng `Future.delayed` nhưng không chống stale request.
2. Pagination chỉ đọc page 2 thử nghiệm rồi không có state merge sạch.
3. Đổi title nhưng vẫn show raw score mơ hồ.
4. Error state chỉ hiện text mà không có retry affordance.

### Tiêu chí accept

1. Search nhanh liên tiếp không còn kết quả nhảy ngược theo request cũ.
2. History/logs không còn silently truncate page đầu.
3. User hiểu rõ mình đang ở màn search hay detail thuốc.
4. Empty/error/loading state có recovery path cơ bản.

### Checklist review khắt khe

1. Có stale-request guard thật không.
2. Pagination state có merge đúng không hay reload mất dữ liệu.
3. UI có CTA rõ khi list chưa hết không.
4. Drug screen hierarchy đã bớt mơ hồ chưa.

### Test bắt buộc

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

### Manual smoke bắt buộc

1. Gõ nhanh nhiều query thuốc liên tiếp, đảm bảo kết quả cuối khớp query cuối.
2. Tài khoản có history dài phải không bị cắt cụt âm thầm ở page đầu.
3. Error state có retry hành động được.

---

## Slice 5 — `MOBILE-P1-C`

### Tên slice

`state UX, copy, l10n, accessibility, responsive cleanup`

### Issue IDs

`UX-1`, `UX-2`, `UX-3`, `UX-4`, `UX-5`

### Mục tiêu

Chuẩn hóa nền UX để app bớt cảm giác vá chắp vá sau khi các bug P0/P1 logic đã xong.

### Đọc bắt buộc trước khi sửa

1. `mobile/lib/l10n/app_localizations.dart`
2. `mobile/lib/l10n/app_localizations_vi.dart`
3. `mobile/lib/features/auth/presentation/login_screen.dart`
4. `mobile/lib/features/settings/presentation/settings_screen.dart`
5. `mobile/lib/shared/widgets/main_shell.dart`
6. `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart`
7. `mobile/lib/features/history/presentation/history_screen.dart`
8. `mobile/lib/features/drug/presentation/drug_search_screen.dart`
9. `mobile/lib/features/drug/presentation/drug_detail_screen.dart`
10. `mobile/lib/features/plan/presentation/plan_detail_screen.dart`

### In scope

- `mobile/lib/l10n/**`
- presentation files cần cleanup trong `mobile/lib/features/**`
- `mobile/lib/shared/widgets/main_shell.dart`

### Out of scope

- backend, Phase A pipeline, pill verification gating sâu

### Nên sửa gì

1. Dọn hardcoded strings ở các màn chính đã audit.
2. Sửa các chuỗi không dấu hoặc tone không nhất quán.
3. Thêm semantics cho custom controls quan trọng.
4. Sửa login/create layouts để chịu được màn nhỏ và keyboard tốt hơn.
5. Xử lý dead-end `Hồ sơ` theo một trong hai hướng:
   - ẩn tạm thời khỏi UI
   - hoặc disable có chú thích `sắp có`
6. Chuẩn hóa loading/error/empty components trong những màn đã đụng tới.

### Nên làm như thế nào

1. Chỉ đưa vào l10n các màn đã động tới trong slice; không cần chuyển cả codebase trong một nhát nếu quá rộng.
2. Semantics nên tập trung vào bottom nav custom item, center action, camera controls và các custom tappables quan trọng.
3. Responsive fix ưu tiên `SingleChildScrollView`, padding và keyboard-safe behavior; không cần redesign layout.

### Lỗ hổng hay bị làm sai

1. Chuyển nửa vời sang l10n, thêm key nhưng vẫn để hardcoded cũ ở nhiều call site đã sửa.
2. Thêm semantics cho một nút nhưng bỏ các control custom quan trọng hơn.
3. Fix login scroll nhưng tạo layout dư khoảng trắng cực lớn.
4. Xóa `Hồ sơ` nhưng để gap/section vô nghĩa trong Settings.

### Tiêu chí accept

1. Các màn chính đã động tới không còn copy vô nghĩa hoặc không dấu.
2. Custom controls quan trọng có semantics cơ bản.
3. Login/create không vỡ trên màn nhỏ cơ bản.
4. Settings không còn dead-end gây hiểu nhầm.

### Checklist review khắt khe

1. Có liệt kê rõ file nào đã được cleanup copy/l10n không.
2. Có bằng chứng semantics được thêm vào những control quan trọng không.
3. Có tránh over-engineer component system mới không.
4. Dead-end `Hồ sơ` đã được xử lý rõ ràng chưa.

### Test bắt buộc

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

### Manual smoke bắt buộc

1. Kiểm tra login trên máy nhỏ hoặc text scale lớn.
2. Dùng TalkBack/VoiceOver cơ bản cho nav và camera controls nếu có điều kiện.
3. Rà nhanh toàn bộ chuỗi Việt ở các màn đã sửa.

---

## Slice 6 — `MOBILE-P2-A`

### Tên slice

`Phase B mobile entry decision và gating`

### Issue IDs

`PILL-1`, `PILL-2`

### Mục tiêu

Ra quyết định rõ số phận của pill verification trong app mobile thay vì để code tồn tại nửa kín nửa hở.

### Đọc bắt buộc trước khi sửa

1. `mobile/lib/core/router/app_router.dart`
2. `mobile/lib/features/home/domain/today_schedule.dart`
3. `mobile/lib/features/home/presentation/home_screen.dart`
4. `mobile/lib/features/pill_verification/presentation/pill_verification_screen.dart`
5. `mobile/lib/features/pill_verification/presentation/pill_reference_enrollment_screen.dart`
6. `mobile/lib/features/pill_verification/data/pill_verification_repository.dart`

### In scope

- `mobile/lib/features/pill_verification/**`
- router/home entry points nếu cần

### Out of scope

- OCR pipeline, model accuracy, backend redesign lớn

### Nên sửa gì

1. Chốt một trong hai hướng:
   - tạm thời ẩn hẳn khỏi path chính cho đến khi hoàn thiện
   - hoặc nối vào flow chính bằng CTA rõ ràng trên `Home`/dose card
2. Nếu giữ flow thật, button confirm không được enable khi còn assignment chưa rõ hoặc summary/reference coverage còn sai điều kiện.
3. Không được để bước `confirm verification` thành công nhưng `logDose` fail mà app chỉ show lỗi chung rồi bỏ mặc state lệch.

### Nên làm như thế nào

1. Nếu backend chưa hỗ trợ atomic/transactional confirm + log, phải nêu blocker rõ.
2. Nếu tạm ẩn Phase B, phải làm sạch affordance liên quan ở path chính, không chỉ bỏ CTA nửa vời.
3. Nếu bật Phase B, phải định nghĩa rõ rule enable/disable cho confirm button dựa trên data thật từ `TodayDose` và `PillVerificationSession`, tối thiểu xét các yếu tố: `verificationReady`, `expectedMedications`, `missingReferenceDrugNames`, `referenceCoverage`, `summary.missingExpected`, và trạng thái assignment của từng detection.
4. Nếu flow được nối vào `Home`, entry point chỉ được hiện khi dữ liệu thật cho phép, không được show đại trà trên mọi dose card.

### Lỗ hổng hay bị làm sai

1. Chỉ thêm entry route mà không fix gating.
2. Chỉ disable button dựa trên `detections.isEmpty` như hiện tại.
3. Gọi Phase B là “hoàn thiện” nhưng thực tế vẫn chưa có entry path hoặc recovery path đúng.

### Tiêu chí accept

1. Phase B không còn ở trạng thái “tồn tại nhưng không biết dùng ở đâu”.
2. Nếu flow còn active, confirm gating phải phản ánh đúng readiness.
3. State sau confirm không được dễ rơi vào tình trạng xác minh xong nhưng dose log fail âm thầm.

### Checklist review khắt khe

1. Có chốt rõ `hide` hay `integrate` không.
2. Rule enable confirm có dựa trên assignment/reference/summary thật không.
3. Có xử lý consistency giữa confirm và mark taken không.
4. Nếu thêm CTA ở `Home`, có dựa trên field readiness thật thay vì hardcode không.

### Test bắt buộc

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

### Manual smoke bắt buộc

1. Với dose chưa sẵn sàng, user không thể bấm confirm sai thời điểm.
2. Với flow được bật, user biết rõ đi từ đâu vào và đi ra đâu.

---

## Slice 7 — `MOBILE-P2-B`

### Tên slice

`regression tests`

### Issue IDs

`TEST-1`

### Mục tiêu

Tạo lớp test tối thiểu nhưng có giá trị để chặn regression cho các fix quan trọng đã làm trước đó.

### Đọc bắt buộc trước khi sửa

1. `mobile/test/widget_test.dart`
2. `mobile/lib/features/home/data/today_schedule_notifier.dart`
3. `mobile/lib/features/home/presentation/home_screen.dart`
4. `mobile/lib/core/network/dio_client.dart`
5. `mobile/lib/features/auth/data/auth_notifier.dart`
6. `mobile/lib/shared/widgets/main_shell.dart`
7. `mobile/lib/features/settings/presentation/settings_screen.dart`
8. `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
9. `mobile/lib/features/drug/data/drug_search_notifier.dart`

### In scope

- `mobile/test/**`
- test helpers nếu cần nhỏ gọn

### Out of scope

- tạo test infra phức tạp không liên quan tới regression thật

### Nên sửa gì

1. Thay smoke test giả bằng test có ý nghĩa.
2. Ưu tiên test cho các điểm dễ tái vỡ:
   - mark dose result mapping
   - auth redirect/session invalidation
   - settings shell highlight/back behavior
   - create plan refresh/invalidations
   - drug search stale request guard

### Nên làm như thế nào

1. Viết test theo notifier/widget behavior trước, không cố full integration nếu quá đắt.
2. Mỗi test phải gắn với một regression từng được audit, không viết test hình thức.

### Lỗ hổng hay bị làm sai

1. Thêm nhiều test snapshot vô nghĩa nhưng không chạm regression thật.
2. Chỉ đổi `widget_test.dart` thành một smoke test khác cũng vô dụng.
3. Test pass nhờ mock quá rộng, không chứng minh được behavior chính.

### Tiêu chí accept

1. Test mới bảo vệ được ít nhất các regression P0 chính.
2. Test suite chạy pass ổn định.

### Checklist review khắt khe

1. Mỗi test mới có gắn với issue ID hoặc regression cụ thể không.
2. Có bỏ test placeholder cũ không.
3. Có tránh over-mocking làm mất ý nghĩa behavior không.

### Test bắt buộc

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

---

## Checklist review tổng quát để reject bài làm của AI khác

Reviewer phải reject nếu có bất kỳ dấu hiệu nào sau đây:

1. Sửa ngoài scope slice mà không được yêu cầu.
2. Refactor rộng không cần thiết.
3. Claim “đã fix” nhưng không nêu trước/sau thay đổi hành vi.
4. Không chạy `flutter analyze` và `flutter test` mà vẫn kết luận done.
5. Dùng wording che giấu state xấu như offline queue nhưng báo thành công thật.
6. Thay dữ liệu thực bằng dữ liệu fabricated để UI đẹp hơn.
7. Thêm hardcoded string mới ở màn đang được cleanup mà không có lý do rõ.
8. Fix UI nhưng bỏ logic gốc sai bên dưới.
9. Chạm backend/pipeline/native ngoài scope mà không báo blocker trước.
10. Không liệt kê `Files đã sửa` và `Issue IDs đã xử lý`.

---

## Quy tắc nghiệm thu cuối cùng

1. Mỗi slice chỉ được coi là xong khi qua cả execution checklist và reviewer checklist.
2. Sau mỗi slice pass, planner mới được mở slice kế tiếp.
3. Nếu một slice fail review, không mở slice mới; quay lại sửa slice đó cho đến khi pass.
4. Nếu execution model phát hiện blocker thật ở backend contract, planner phải cập nhật lại plan trước khi giao lại.
