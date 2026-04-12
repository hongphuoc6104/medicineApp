# Active General Plan

## Initiative hiện tại

`Việt hóa toàn bộ phần hiển thị cho người dùng trong app`

Mục tiêu của initiative này là đưa toàn bộ app Flutter về một mặt chữ thống nhất, dễ hiểu và đúng tiếng Việt có dấu:

- mọi tiêu đề, nút bấm, helper text, dialog, snackbar, empty state, error state và notification phải là tiếng Việt
- loại bỏ các chuỗi tiếng Anh hoặc tiếng Việt không dấu như `Thong tin thuoc`, `Da dong bo...`, `Den gio uong thuoc`
- gom text về một lớp quản lý tập trung thay vì để hard-code rải rác ở từng màn

---

## Tiến độ hiện tại

### Đã hoàn thành

- `L10N-1` — Foundation localization + shared copy
- `L10N-2A` — Auth + Home + Create entry
- `L10N-2B` — Scan + Review + Edit drugs + Schedule đã localize xong, đã qua review và đã được clean pass bằng hotfix nhỏ

### Đang active

- `MVT-1` — Manual verify gate cho core flow sau khi `L10N-2` đã clean pass

### Chưa mở

- `L10N-3A` — Drug + Plan
- `L10N-3B` — History + Settings
- `L10N-4` — Pill verification + final sweep

### Gating trước khi mở lát cắt tiếp theo

- user phải manual verify lại flow chính `Đăng nhập/Đăng ký -> Trang chủ -> Tạo kế hoạch -> Quét đơn thuốc -> Xác nhận -> Lập lịch`
- nếu manual verify pass mới mở `L10N-3A`
- nếu manual verify fail thì phải mở hotfix nhỏ đúng màn bị lỗi, không được nhảy thẳng sang `L10N-3A`

---

## Quyết định sản phẩm đã chốt

### 1. Scope là phần hiển thị user-facing của app

- ưu tiên `mobile/`
- không đổi schema, route, contract hay nghiệp vụ backend chỉ để dịch chữ
- không chạm `scripts/run_pipeline.py`

### 2. Tiếng Việt có dấu là mặc định bắt buộc

- không để English lẫn trong UI đang ship cho người dùng
- không để copy kiểu ASCII không dấu trên các màn đã sửa

### 3. Phase B logic vẫn đứng ngoài initiative này

- chỉ được sửa copy ở các màn Phase B đang lộ trong app nếu cần
- không mở thêm research hay thay đổi logic verification

---

## Vấn đề tổng quát cần giải quyết

### 1. String user-facing đang hard-code rải rác

- text nằm phân tán trong nhiều screen, notifier và service
- sửa một chỗ khó đảm bảo nhất quán toàn app

### 2. App chưa có nền localization thật sự

- đã có `intl` nhưng chưa có `flutter_localizations`, delegates hay ARB catalog
- `MaterialApp` chưa khai báo locale support

### 3. Copy hiện tại bị pha tạp

- có chỗ tiếng Việt có dấu
- có chỗ tiếng Việt không dấu
- có chỗ để English kỹ thuật hoặc message thô

### 4. Error/status/notification copy chưa được chuẩn hóa

- cùng một hành vi nhưng mỗi màn dùng một kiểu câu khác nhau
- một số lỗi đang lộ raw text kém thân thiện

---

## Nhóm ưu tiên

### Nhóm A — Foundation localization

- dựng hạ tầng `l10n` cho Flutter
- tạo catalog text tập trung
- trạng thái: `completed`

### Nhóm B — Global chrome và core flow

- app shell, điều hướng, notification
- auth, home, create plan, scan, review, schedule
- trạng thái: `code_complete_waiting_user_manual_verify`

### Nhóm C — Surface phụ nhưng vẫn user-facing

- drug search/detail
- plan list/detail
- history
- settings
- trạng thái: `pending`

### Nhóm D — Pill verification và cleanup cuối

- copy ở các màn pill verification đang lộ trong app
- sweep toàn bộ string còn sót lại
- trạng thái: `pending`

---

## Thứ tự xử lý lớn

1. user manual verify lại core flow của Phase A app path sau `L10N-2` clean pass
2. nếu pass, việt hóa `drug / plan` trong `L10N-3A`
3. việt hóa `history / settings` trong `L10N-3B`
4. review sâu các màn đã làm và rà residual risks
5. việt hóa `pill verification` và chạy final sweep trong `L10N-4`

---

## Quy tắc nghiệm thu trong initiative này

- `MaterialApp` phải có localization delegates và locale support rõ ràng
- mọi text user-facing trong các file đã chạm phải đi qua lớp localization hoặc message catalog tập trung
- không còn English hoặc tiếng Việt không dấu trên luồng chính sau khi đóng `L10N-2`
- `cd mobile && flutter analyze` và `cd mobile && flutter test` phải pass
- sau khi `L10N-2` được đóng sạch phải manual verify lại các màn chính của Phase A app path

### Residual risk đã biết

- `guidance` do server trả về ở scan flow có thể vẫn hiển thị text không hoàn toàn localize nếu backend trả chuỗi ngoài chuẩn UI. Điểm này được ghi nhận nhưng không chặn việc mở `L10N-3A` nếu manual verify flow chính vẫn ổn.

### Tiêu chí hoàn tất general plan

- `L10N-1`, `L10N-2`, `L10N-3`, `L10N-4` đều hoàn tất
- không còn chuỗi user-facing tiếng Anh hoặc không dấu trên các route active
- user xác nhận nghiệm thu hướng Việt hóa UI này trước khi archive

Plan active trước đó được park tại:

- `archive/plan_bin/2026-04-12_prescription-plan-group-redesign_superseded/`
