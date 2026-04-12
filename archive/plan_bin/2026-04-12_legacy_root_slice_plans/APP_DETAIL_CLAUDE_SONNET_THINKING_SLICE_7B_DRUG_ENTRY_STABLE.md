# Detailed Plan — Claude Sonnet Thinking — Lát Cắt 7B

## Trạng thái

`queued_waiting_user_review_of_7A`

Không bắt đầu thực thi cho đến khi planner xác nhận user đã test và đồng ý với kết quả của `7A`.

---

## Mục tiêu

Làm cho trải nghiệm sửa tên thuốc / chọn gợi ý DB ổn định hơn, không còn giật layout.

---

## Phạm vi được sửa

- `mobile/lib/features/create_plan/presentation/widgets/drug_entry_sheet.dart`

## Không được sửa

- `scan_camera_screen.dart`
- `set_schedule_screen.dart`
- backend Node/Python
- file Phase B

---

## Việc phải làm

1. Thêm debounce cho search.
2. Giữ vùng suggestion ổn định, tránh nhảy layout.
3. Cải thiện trạng thái loading/gợi ý để ít gây khó chịu hơn khi sửa OCR.

---

## Tiêu chí xong

- sửa thuốc mượt hơn
- không giật lên giật xuống khi gợi ý xuất hiện
- `flutter analyze` và `flutter test` pass

---

## Luật dừng

Phải dừng nếu cần sửa ngoài file scope hoặc phải đổi review flow lớn hơn.
