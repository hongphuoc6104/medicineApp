# Detailed Plan — GPT-5.3 Codex — Lát Cắt 7C

## Trạng thái

`queued_waiting_user_review_of_7A_and_7B`

Không bắt đầu thực thi cho đến khi planner xác nhận user đã test và đồng ý các bước trước.

---

## Mục tiêu

Đơn giản hóa màn lập lịch để người dùng không phải “mò” và suy nghĩ quá nhiều.

---

## Phạm vi được sửa

- `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`

## Không được sửa

- `scan_camera_screen.dart`
- `drug_entry_sheet.dart`
- backend Node/Python
- file Phase B

---

## Việc phải làm

1. Làm lại cách trình bày theo hướng ít suy nghĩ hơn.
2. Dùng ngôn ngữ dễ hiểu hơn cho người dùng phổ thông.
3. Giảm cảm giác app đang bắt user hiểu mô hình kỹ thuật của slot/plan.

---

## Tiêu chí xong

- màn lập lịch dễ hiểu hơn rõ rệt
- ít bước nhận thức hơn
- `flutter analyze` và `flutter test` pass

---

## Luật dừng

Phải dừng nếu cần đụng backend hoặc file ngoài scope để hoàn thành.
