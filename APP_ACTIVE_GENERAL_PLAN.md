# Active General Plan

## Initiative active

`Ổn định logic và UI/UX app mobile sau đợt audit`

Initiative này thay thế batch plan cũ vốn đang bị lệch trọng tâm sang reminder-only và các lát cắt nhỏ rời rạc.

Trọng tâm mới là đưa app mobile về trạng thái:

- hành vi trong app phản ánh đúng trạng thái thật của dữ liệu
- điều hướng, back flow và CTA không gây hiểu nhầm
- flow `quét đơn -> review -> lập lịch -> nhắc uống` mạch lạc và đáng tin hơn
- các vấn đề UI/UX được xử lý theo mức ưu tiên sản phẩm, không vá rời từng màn

---

## Những vấn đề đã được xác nhận từ audit

### Nhóm 1 — Truthfulness của state và sync

- đánh dấu liều khi offline đang báo thành công như thể đã sync xong
- token hết hạn có thể xóa storage nhưng không đẩy app về trạng thái logout đúng lúc
- tạo plan mới xong chưa chắc làm tươi `today schedule`
- end/reactivate plan chưa chặt với reschedule/cancel notification

### Nhóm 2 — Điều hướng và information architecture

- `/settings` đang ăn vào index của `History` trong shell
- back từ Settings đang nhảy cứng về `/home`
- một số flow đang dùng `context.go(...)` làm mất ngữ cảnh thay vì quay lại đúng stack

### Nhóm 3 — Create flow và scan/reuse clarity

- reuse flow đang dễ làm đẹp hóa dữ liệu scan cũ
- scan review có sort item cần review nhưng thiếu tín hiệu rõ ràng cho user
- camera flow chưa hướng dẫn framing tốt và dễ kích hoạt chụp ngoài ý muốn

### Nhóm 4 — Data scale và state completeness

- search thuốc không debounce/cancel request
- history và logs mới chỉ nối tới page đầu
- home có thể rơi vào empty state sai khi user đã xử lý hết liều trong ngày

### Nhóm 5 — UI/UX polish nền

- copy và l10n còn trộn giữa ARB với hardcoded text
- accessibility semantics gần như chưa có cho custom controls
- nhiều loading/error/empty state chưa thống nhất
- còn dead-end như `Hồ sơ` trong Settings

### Nhóm 6 — Phase B / pill verification

- route và màn đã tồn tại nhưng chưa được nối vào path chính
- cần quyết định rõ: ẩn hẳn khỏi flow chính hay hoàn thiện như một flow thật

### Nhóm 7 — Test coverage

- `mobile/test/widget_test.dart` hiện chưa bảo vệ được regression thực tế của app

---

## Quyết định sản phẩm đã khóa cho batch này

1. Phase A app flow vẫn là trọng tâm chính.
2. Sửa `logic đúng sự thật` và `navigation clarity` trước khi làm visual polish.
3. Không mở rộng Phase B trong batch này nếu chưa chốt được entry path rõ ràng.
4. Root chỉ nên giữ các plan active thật sự cần đọc; không duy trì board dài dòng cũ ở thư mục gốc.
5. Mọi text user-facing mới hoặc sửa lại phải là tiếng Việt có dấu và nên đi qua l10n khi phạm vi cho phép.

---

## Nhóm ưu tiên

### P0 — Reliability và state correctness

- auth expiry
- offline/sync truthfulness
- plan/today/reminder consistency
- settings/navigation correctness

### P1 — Flow clarity và UI/UX nền

- create/scan/reuse clarity
- search/history scale
- empty/error/loading consistency
- copy/l10n/accessibility cleanup

### P2 — Product shaping và hardening

- quyết định số phận Phase B mobile entry
- widget/integration tests cho các flow chính

---

## Thứ tự xử lý lớn

1. `MOBILE-P0-A` — truthful state và navigation baseline
2. `MOBILE-P0-B` — plan/today/reminder consistency
3. `MOBILE-P1-A` — create/scan/reuse clarity
4. `MOBILE-P1-B` — search/history completeness và state UX
5. `MOBILE-P1-C` — copy, l10n, accessibility, responsive cleanup
6. `MOBILE-P2-A` — Phase B entry decision trên mobile
7. `MOBILE-P2-B` — widget/integration regression tests

---

## Definition of done cho initiative này

- các lỗi P0 không còn làm app nói sai trạng thái thật với user
- flow Settings/Home/Create/Plans/History không còn back behavior gây lạc hướng
- search/history xử lý được các trạng thái cơ bản thay vì chỉ page đầu + spinner
- copy và affordance trên các màn chính nhất quán hơn
- có test đủ để chặn regression cho các flow đã sửa

---

## Không làm trong initiative này

- thay đổi Phase A Python pipeline
- mở rộng backend lớn nếu chỉ để polish UI nhỏ
- biến Phase B thành epic chính trong khi flow core của app chưa ổn định
