# Active General Plan

## Initiative hiện tại

`Elderly-First Create Flow Simplification`

Mục tiêu của initiative này là tối giản app cho:

- người lớn tuổi
- người không rành ứng dụng hiện đại
- người muốn làm nhanh mà không phải suy nghĩ nhiều

Nguyên tắc chính:

- cái gì tự động được thì ưu tiên tự động
- một màn chỉ nên có một mục tiêu rõ ràng
- không bắt user phải hiểu model dữ liệu hay trạng thái kỹ thuật
- sau mỗi màn hoặc quy trình lớn được sửa xong, phải dừng để user test và duyệt trước khi sang bước kế tiếp

---

## Vấn đề tổng quát cần giải quyết

### 1. Màn quét đơn thuốc còn khó dùng

- user phải tự bấm chụp
- quality gate đang thiên về “phải thấy rõ toàn bộ đơn”
- camera preview/capture tạo cảm giác mờ và khó căn
- quy trình quét chưa đủ tự động

### 2. Màn sửa lỗi OCR bị giật khi hiện gợi ý

- vùng gợi ý tên thuốc thay đổi chiều cao liên tục
- cảm giác app giật lên giật xuống khi nhập

### 3. Màn lập lịch vẫn quá phức tạp

- user phải đọc, mò và suy nghĩ nhiều
- thuật ngữ và cách trình bày chưa đủ trực quan cho người lớn tuổi

### 4. UI đang lộ mô hình kỹ thuật theo từng thuốc quá nhiều

- user nghĩ theo `một đơn` và `một lần uống`
- app hiện vẫn lộ cảm giác đang thao tác trên nhiều record nhỏ

### 5. Phase B tạm dừng

- không mở thêm việc mới cho Phase B
- không đưa Phase B vào flow chính của sản phẩm trong initiative này

---

## Nhóm ưu tiên

### Nhóm A — Quét đơn thuốc thực dụng hơn

- continuous auto scan / auto capture
- quality gate bám vùng thuốc, không ép toàn bộ đơn hoàn hảo
- copy dễ hiểu hơn

### Nhóm B — Sửa lỗi OCR mượt hơn

- debounce
- suggestion ổn định
- không giật layout

### Nhóm C — Lập lịch dễ hiểu hơn

- ít bước hơn
- ít khái niệm hơn
- dễ nhìn theo buổi/lần uống

### Nhóm D — Prescription-first UX

- UI phải cho cảm giác đang làm việc với `một đơn thuốc`
- chỉ mở sau khi 3 nhóm trên đủ ổn

---

## Thứ tự xử lý lớn

1. sửa trải nghiệm quét đơn thuốc
2. sửa sheet nhập/tìm thuốc để không còn giật
3. sửa màn lập lịch cho dễ hiểu hơn
4. chỉ sau khi 1-3 đã được user test và đồng ý mới mở phần prescription-first UX sâu hơn

---

## Quy tắc nghiệm thu trong initiative này

- batch hiện tại (`7A / 7B / 7C`) được phép chạy song song
- sau khi cả 3 lát cắt hoàn thành, planner sẽ review và mời user test gộp trên app thật
- chỉ khi user đồng ý batch này mới mở initiative hoặc lát cắt tiếp theo

Initiative gần nhất đã hoàn thành và được archive tại:

- `archive/plan_bin/2026-04-10_phase-a_master/APP_REBUILD_GENERAL_PLAN.md`
