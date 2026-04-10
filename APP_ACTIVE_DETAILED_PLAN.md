# Active Detailed Plan

## Initiative active

`Elderly-First Create Flow Simplification`

Detailed plan này chỉ phục vụ cho initiative active hiện tại.

---

## 0. Mục tiêu giao sản phẩm

Biến flow tạo kế hoạch thành một flow:

- ít bước
- ít suy nghĩ
- tự động hơn
- dễ dùng với người lớn tuổi

Mục tiêu thực tế của initiative này là cải thiện 3 màn hình chính trong cùng một batch song song (`7A / 7B / 7C`), sau đó dừng để user test gộp trước khi mở bước tiếp theo.

---

## 1. Thứ tự đọc bắt buộc

AI execution phải đọc đúng thứ tự sau:

1. `AGENTS.md`
2. `AGENT_START_HERE.md`
3. `APP_ACTIVE_GENERAL_PLAN.md`
4. `APP_ACTIVE_DETAILED_PLAN.md`
5. `docs/phase_a_debug_runbook.md`

Sau đó mới đọc code theo lát cắt được giao.

---

## 2. Phạm vi initiative này

### 2.1 In scope

- `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart`
- `mobile/lib/features/create_plan/data/scan_camera_controller.dart`
- `mobile/lib/features/create_plan/data/local_quality_gate.dart`
- `mobile/lib/features/create_plan/presentation/widgets/drug_entry_sheet.dart`
- `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
- nếu cần ở các lát cắt sau: các màn create/history/home liên quan UX của create flow

### 2.2 Out of scope

- Phase B
- backend lớn cho prescription batch
- train lại model
- `scripts/run_pipeline.py`
- thay đổi lớn ở auth hoặc hệ notification

---

## 3. Lát cắt chính của initiative này

## Lát cắt 7A — Scan UX thực dụng hơn

Mục tiêu:

- user không phải tự căn/chụp quá nhiều
- app tự động hơn
- quality gate bám nhu cầu thực tế: đọc được vùng thuốc là đủ

Việc phải làm:

1. rà camera preview để giảm cảm giác mờ
2. đổi copy màn quét sang ngắn gọn, dễ hiểu hơn
3. thêm `auto-capture` hoặc `semi-auto capture`:
   - khi mở camera lên, app liên tục tự đánh giá khung hình
   - gặp khung hình đủ tốt thì tự lấy ảnh và gửi quét
   - nút chụp tay chỉ còn là fallback phụ nếu cần
4. đổi quality gate để không ép phải thấy trọn toàn bộ đơn mới cho quét

File trọng tâm:

- `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart`
- `mobile/lib/features/create_plan/data/scan_camera_controller.dart`
- `mobile/lib/features/create_plan/data/local_quality_gate.dart`

Điều kiện xong:

- user chỉ cần đưa vùng thuốc vào khung là app hỗ trợ chụp/quét được dễ hơn
- flow chính không còn phụ thuộc vào việc user phải bấm nút chụp
- copy dễ hiểu hơn hiện tại

## Lát cắt 7B — OCR correction ổn định

Mục tiêu:

- sửa tên thuốc không còn giật layout

Việc phải làm:

1. thêm debounce cho search
2. giữ chiều cao vùng gợi ý ổn định
3. tránh giật layout khi gợi ý xuất hiện/biến mất

File trọng tâm:

- `mobile/lib/features/create_plan/presentation/widgets/drug_entry_sheet.dart`

Điều kiện xong:

- sheet sửa thuốc mượt hơn rõ rệt

## Lát cắt 7C — Lập lịch dễ hiểu hơn

Mục tiêu:

- user không phải ngồi mò và suy nghĩ nhiều

Việc phải làm:

1. đơn giản hóa ngôn ngữ và cấu trúc màn lập lịch
2. ưu tiên flow rất rõ theo từng bước
3. giảm độ kỹ thuật của summary và thao tác

File trọng tâm:

- `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`

Điều kiện xong:

- màn lập lịch dễ hiểu hơn cho user phổ thông

## Lát cắt 8 — Prescription-first UX

Chỉ mở sau khi user đã test và đồng ý các lát cắt 7A, 7B, 7C.

---

## 4. Quy tắc nghiệm thu batch hiện tại

### Rất quan trọng

Batch hiện tại gồm 3 lát cắt song song:

- `7A`
- `7B`
- `7C`

Quy tắc:

1. mỗi execution model chỉ làm đúng lát cắt của mình
2. planner sẽ review từng lát cắt sau khi model trả kết quả
3. chỉ khi cả 3 lát cắt đã xong và qua review thì mới mời user test gộp
4. chỉ khi user đồng ý batch này mới mở bước tiếp theo

Không được tự ý mở `Lát cắt 8` trước khi user đã test xong batch `7A/7B/7C`.

---

## 5. Luật dừng khi có lỗi lớn

Execution model phải dừng nếu:

1. cần sửa ngoài phạm vi lát cắt đang được giao
2. phải đụng backend hoặc contract lớn để hoàn thành một thay đổi UI nhỏ
3. test fail ở phần không liên quan
4. workspace bẩn gây xung đột trực tiếp với file đang làm

Khi dừng phải báo:

1. đã làm gì
2. file đã sửa
3. test đã chạy
4. blocker là gì
5. bước nhỏ nhất tiếp theo

---

## 6. Test bắt buộc sau mỗi lát cắt

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

Và nếu màn hình có thể test ngay trên máy thật thì planner phải mời user test trước khi mở lát cắt tiếp theo.

---

## 7. Trạng thái hiện tại

- Batch active hiện tại là `7A + 7B + 7C`.
- Cả 3 execution plan đều có thể bắt đầu ngay.
- Sau khi cả 3 xong, planner sẽ mời user test gộp một lần.
