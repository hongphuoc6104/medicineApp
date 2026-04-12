# Active General Plan

## Initiative hiện tại

`Ổn định và tái cấu trúc app nhắc uống thuốc`

Mục tiêu của initiative này là đưa app từ trạng thái `scan demo + UI đang vá dần` sang một sản phẩm rõ ràng, ổn định và dễ hiểu cho nhu cầu `lập lịch và nhắc uống thuốc`.

Kết quả mong muốn ở mức sản phẩm:

- app local/dev path ổn định, không còn lỗi kiểu `không kết nối được với máy chủ` một cách mơ hồ
- tên app, copy, launcher label và background/splash nhất quán theo một brand tiếng Việt ngắn gọn
- màn Home chỉ ưu tiên thuốc `tới giờ uống` và `sắp tới giờ`, không dàn đều toàn bộ dữ liệu trong ngày
- luồng `Tạo kế hoạch` rõ ràng hơn cho 3 đường: quét đơn, nhập thủ công, dùng lại dữ liệu cũ
- lịch sử phản ánh hành vi dùng thuốc hợp lý hơn, không để `lịch sử quét` làm trung tâm chính
- reminder phải nổi ngoài điện thoại khi tới giờ uống
- các phần phù hợp sẽ đi theo hướng local-first, nhưng scan AI vẫn giữ server-side ở giai đoạn này

---

## Baseline hiện có

### Đã có nền tốt

- localization foundation đã có (`L10N-1`)
- core flow copy đã được làm đáng kể (`L10N-2`)
- local reminder scheduling cơ bản đã có trong mobile
- offline queue cho thao tác đánh dấu uống thuốc đã có
- local Python AI runtime đã được phục hồi để tiếp tục manual verify

### Vì sao cần reset initiative

Manual verify vừa qua cho thấy vấn đề không còn nằm trong phạm vi `dịch chữ` nữa.

Các lỗi và khoảng trống hiện tại nằm ở nhiều tầng cùng lúc:

- runtime / dev reliability
- home logic
- history information architecture
- create flow UX
- branding / copy / app naming
- notification delivery
- local-first data strategy

---

## Quyết định sản phẩm đã chốt

### 1. Trọng tâm vẫn là Phase A app flow

- ưu tiên flow chính: `quét đơn -> xác nhận thuốc -> lập lịch -> lưu -> nhắc uống`
- không để Phase B kéo lệch roadmap chính

### 2. Scan AI vẫn giữ server-side ở giai đoạn này

- không cố kéo OCR/NER về local device trong đợt này
- local-first chỉ áp dụng cho phần phù hợp như plan snapshot, today schedule, logs, reminders

### 3. Home phải ưu tiên hành động đúng thời điểm

- chỉ foreground các thuốc `tới giờ uống` và `sắp tới giờ`
- phần đã uống / scan history / CTA phụ không được lấn át nhiệm vụ chính

### 4. History chính phải là lịch sử dùng thuốc

- `lịch sử quét` trở thành lớp phụ để reuse/audit
- `lịch sử uống thuốc` mới là trọng tâm sản phẩm lâu dài

### 5. Branding phải đổi sang tên tiếng Việt ngắn, dễ hiểu

- working direction trong plan: app name phải xoay quanh `lịch / nhắc uống thuốc`
- tên cuối cùng sẽ được user chốt trước khi implement branding slice

### 6. Notification ngoài app là yêu cầu bắt buộc

- không chỉ schedule trong app nội bộ
- phải có đường thông báo nổi ra ngoài thiết bị khi tới giờ uống

---

## Vấn đề tổng quát cần giải quyết

### Nhóm 1 — Reliability và local dev/runtime

- sau cleanup, local runtime và startup path đã từng gãy
- lỗi mạng trong app hiện lên nhưng không đủ giúp user/dev biết tầng nào hỏng

### Nhóm 2 — Branding và copy sản phẩm

- app đang có nhiều tên khác nhau: `medicine_app`, `MedicineApp`, `Thuốc Của Tôi`
- còn nhiều câu copy vô nghĩa hoặc không cần thiết
- còn sót nhiều chỗ tiếng Việt không dấu

### Nhóm 3 — Logic màn Home chưa đúng trọng tâm

- chưa ưu tiên rõ `tới giờ` và `sắp tới giờ`
- còn lộ CTA và logic Phase B ở home path

### Nhóm 4 — Luồng Tạo kế hoạch chưa mạch lạc

- `Dùng lại lịch sử` đang đẩy sang history chung, không phải reuse flow đúng nghĩa
- nhập thủ công còn mỏng và UI/UX chưa hợp lý
- nhiều chỗ vẫn mang cảm giác `scan-shaped` dù đi manual path

### Nhóm 5 — History chưa phản ánh mô hình sản phẩm mong muốn

- lịch sử quét đang chiếm vai trò quá lớn
- thiếu một lịch sử hành vi dùng thuốc rõ ràng và có ích hơn cho user

### Nhóm 6 — Reminder chưa đủ tin cậy ngoài app

- mobile đã có local notifications cơ bản
- nhưng permission, reboot-reschedule, startup integrity và delivery path chưa đủ chặt

### Nhóm 7 — Local-first còn quá mỏng

- hiện mới có local reminder scheduling và offline queue hẹp cho dose logs
- home, plans, history vẫn phụ thuộc backend là nguồn sự thật duy nhất

---

## Nhóm ưu tiên

### Nhóm A — Reliability baseline

- startup/runtime local
- network/dev diagnostics
- trạng thái: `active`

### Nhóm B — Product framing và branding

- app naming
- copy cleanup
- launcher/splash/background
- trạng thái: `pending`

### Nhóm C — Home logic

- due now
- upcoming
- giảm nhiễu
- trạng thái: `pending`

### Nhóm D — Create flow UX

- entry hub
- manual entry
- reuse flow
- trạng thái: `pending`

### Nhóm E — History model

- medication behavior history
- scan history làm lớp phụ
- trạng thái: `pending`

### Nhóm F — Reminder delivery

- notification nổi ngoài app
- permission / reschedule / integrity
- trạng thái: `pending`

### Nhóm G — Local-first data

- local plan snapshot
- today schedule cache
- logs cache / sync
- trạng thái: `pending`

---

## Thứ tự xử lý lớn

1. `REL-1A` — harden local startup và scan runtime detection
2. `REL-1B` — cải thiện network diagnostics / reconnect UX ở mobile
3. `BRAND-1` — chốt tên app, copy, launcher/splash/background
4. `HOME-1` — làm lại Home theo `tới giờ / sắp tới giờ`
5. `FLOW-1A` — thiết kế lại entry hub và reuse history flow
6. `FLOW-1B` — sửa manual entry UX
7. `HISTORY-1` — thiết kế lại lịch sử
8. `REMIND-1` — hoàn thiện notification ngoài app
9. `LOCAL-1` — local-first cho plans / home / logs phù hợp

---

## Tracks song song được phép chạy ngay

### Track R1 — Reliability implementation

- model chính: `GPT-5.3 Codex`
- mục tiêu: implement `REL-1A`

### Track S1 — UX/IA spec

- model chính: `Claude Sonnet 4.6 Thinking`
- mục tiêu: spec cho home / create / history / manual / reuse

### Track A1 — Local-first / reminder architecture audit

- model chính: `Gemini 3.1 Pro High`
- mục tiêu: map phụ thuộc và đề xuất slice kỹ thuật cho local-first + notifications

### Track T1 — Branding / copy / remaining issue inventory

- model chính: `Gemini 3 Flash`
- mục tiêu: triage nhanh naming/copy/asset surface và các chuỗi còn lệch chuẩn

---

## Quy tắc nghiệm thu của initiative này

- local dev path phải lên ổn định cho mobile manual testing
- app không còn dùng brand/copy mâu thuẫn giữa launcher, login, home và shell
- các màn user-facing chính không còn tiếng Việt không dấu
- Home phải giải quyết đúng nhu cầu `uống ngay bây giờ` và `sắp đến giờ`
- create flow phải mạch lạc cho `scan / manual / reuse`
- history phải có cấu trúc hợp lý hơn cho việc dùng thuốc hằng ngày
- notification phải hiện ngoài app khi tới giờ uống
- local-first phải tăng độ bền của app ở các phần phù hợp mà không kéo scan AI về local

---

## Tiêu chí hoàn tất general plan

- `REL-1`, `BRAND-1`, `HOME-1`, `FLOW-1`, `HISTORY-1`, `REMIND-1`, `LOCAL-1` đều hoàn tất
- user manual verify lại flow chính và xác nhận app đã rõ ràng, ổn định hơn theo hướng `nhắc uống thuốc`
- plan active cũ về localization chỉ còn là baseline, không còn blocker chưa xử lý riêng
