# Active General Plan

## Initiative hiện tại

`Việt hóa toàn bộ phần hiển thị cho người dùng trong app`

Mục tiêu của initiative này là đưa toàn bộ app Flutter về một mặt chữ thống nhất, dễ hiểu và đúng tiếng Việt có dấu:

- mọi tiêu đề, nút bấm, helper text, dialog, snackbar, empty state, error state và notification phải là tiếng Việt
- loại bỏ các chuỗi tiếng Anh hoặc tiếng Việt không dấu như `Thong tin thuoc`, `Da dong bo...`, `Den gio uong thuoc`
- gom text về một lớp quản lý tập trung thay vì để hard-code rải rác ở từng màn

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

### Nhóm B — Global chrome và core flow

- app shell, điều hướng, notification
- auth, home, create plan, scan, review, schedule

### Nhóm C — Surface phụ nhưng vẫn user-facing

- drug search/detail
- plan list/detail
- history
- settings

### Nhóm D — Pill verification và cleanup cuối

- copy ở các màn pill verification đang lộ trong app
- sweep toàn bộ string còn sót lại

---

## Thứ tự xử lý lớn

1. dựng foundation localization và entry wiring trong app
2. chuyển shared UI, app shell và notification copy sang lớp tập trung
3. việt hóa luồng chính `auth -> home -> create plan -> scan -> review -> schedule`
4. việt hóa các màn `drug / plan / history / settings`
5. việt hóa `pill verification` ở mức copy và chạy sweep cuối để loại bỏ text sót

---

## Quy tắc nghiệm thu trong initiative này

- `MaterialApp` phải có localization delegates và locale support rõ ràng
- mọi text user-facing trong các file đã chạm phải đi qua lớp localization hoặc message catalog tập trung
- không còn English hoặc tiếng Việt không dấu trên luồng chính
- `cd mobile && flutter analyze` và `cd mobile && flutter test` phải pass
- sau batch core flow phải manual verify lại các màn chính của Phase A app path

Plan active trước đó được park tại:

- `archive/plan_bin/2026-04-12_prescription-plan-group-redesign_superseded/`
