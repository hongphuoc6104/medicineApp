# Active General Plan

## Initiative hiện tại

`Prescription Plan Group Redesign`

Mục tiêu là bỏ mô hình cũ `1 plan = 1 thuốc` và chuyển app sang mô hình đúng với cách người dùng nghĩ:

- `1 kế hoạch`
- có `1 hoặc nhiều khung giờ uống`
- mỗi khung giờ có `1 hoặc nhiều loại thuốc`
- mỗi thuốc trong khung giờ có `số lượng riêng`

---

## Quyết định sản phẩm đã chốt

### 1. Không giữ dữ liệu cũ như ràng buộc

- không cần tương thích ngược với schema cũ ở mức nghiệp vụ
- có thể bỏ cách hiểu cũ `medication_plans = từng thuốc`
- có thể dùng schema mới và route/service mới trong cùng app

### 2. Một lần uống là một khung giờ có nhiều thuốc

- home/today phải xoay quanh `dose slot`
- không xoay quanh từng thuốc riêng lẻ nữa

### 3. Phase B tiếp tục đứng ngoài luồng này

- không mở Phase B trong initiative này

---

## Vấn đề tổng quát cần giải quyết

### 1. Data model hiện tại sai với nghiệp vụ thật

- đang lưu theo từng thuốc riêng
- người dùng nghĩ theo từng đơn/kế hoạch có nhiều thuốc

### 2. Màn lập lịch bị bó buộc bởi model cũ

- chỉ mới vá được số viên theo từng giờ
- chưa phản ánh đúng `1 kế hoạch nhiều thuốc nhiều khung giờ`

### 3. Home / plan list / plan detail vẫn đang lộ mô hình cũ

- chưa nhìn ra đúng một kế hoạch tổng thể

---

## Nhóm ưu tiên

### Nhóm A — Backend foundation mới

- schema mới cho plan group
- service mới cho create/read/update/log/today

### Nhóm B — Mobile domain/repository mới

- mobile hiểu plan group mới

### Nhóm C — Schedule screen mới

- schedule xoay quanh `khung giờ -> thuốc -> số viên`

### Nhóm D — Home / plan list / plan detail mới

- hiển thị đúng theo kế hoạch nhóm

---

## Thứ tự xử lý lớn

1. backend foundation mới
2. mobile domain/repository mới
3. schedule screen save theo plan group
4. user test create/save
5. home/today/list/detail theo model mới

---

## Quy tắc nghiệm thu trong initiative này

- sau khi xong phần `backend + mobile domain + schedule save`, phải dừng để user test
- chỉ khi user xác nhận flow create/save ổn mới mở tiếp phần `home/list/detail`

Batch cũ đã hoàn thành và được archive tại:

- `archive/plan_bin/2026-04-10_phase-a_master/APP_REBUILD_GENERAL_PLAN.md`
