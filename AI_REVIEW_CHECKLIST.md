# AI Review Checklist

File này dùng để nghiệm thu output của AI execution khác theo plan active hiện tại.

## File nguồn phải đọc kèm

1. `APP_ACTIVE_GENERAL_PLAN.md`
2. `APP_ACTIVE_DETAILED_PLAN.md`

Nếu AI execution làm lệch hai file trên mà không ghi rõ đổi phạm vi hoặc blocker, ưu tiên reject.

## Cách dùng

1. Xác định `Workstream ID` mà AI đang xử lý.
2. Mở đúng workstream tương ứng trong `APP_ACTIVE_DETAILED_PLAN.md`.
3. Đối chiếu output của AI với checklist file này.
4. Chỉ accept khi qua đủ 4 cổng: `scope`, `logic`, `test`, `quality`.

## 0. Thông tin bắt buộc phải có trong output của AI

Reject ngay nếu thiếu bất kỳ mục nào sau đây:

1. `Workstream ID`
2. `Phạm vi đã xử lý`
3. `Files đã đọc`
4. `Files đã sửa`
5. `Cách sửa chính`
6. `Những gì cố ý không sửa`
7. `Lệnh test đã chạy`
8. `Kết quả test`
9. `Manual smoke đã kiểm tra / chưa kiểm tra`
10. `Rủi ro còn lại`

## 1. Cổng Scope

Pass khi:

1. AI chỉ sửa đúng workstream hoặc lát cắt nhỏ đã được giao.
2. Các file sửa phù hợp với `In scope điển hình` của workstream.
3. Không mở rộng task sang feature khác ngoài mục tiêu đang xử lý.
4. Nếu có đổi phạm vi, AI ghi rõ lý do và tác động.

Reject ngay khi:

1. Sửa ngoài scope mà không báo trước.
2. Refactor rộng chỉ để “đẹp code”.
3. Tự mở thêm feature không nằm trong plan active.
4. Chạm pipeline/backend/native ngoài ý định rồi mới giải thích sau.

## 2. Cổng Logic

Pass khi:

1. Fix đúng bản chất lỗi hoặc đúng mục tiêu người dùng.
2. Trạng thái trước và sau sửa được giải thích rõ.
3. Không fabricate data để UI trông đẹp hơn thực tế.
4. Không che giấu state xấu bằng copy gây hiểu lầm.

Reject ngay khi:

1. Chỉ đổi wording bề mặt nhưng logic cũ vẫn sai.
2. UI báo thành công dù thực tế mới chỉ queue offline hoặc chưa verify.
3. Ép `confidence`, `mappingStatus`, `qualityState`, `rejected` hoặc state tương tự về trạng thái đẹp hơn thực tế.
4. Redirect cưỡng bức nhưng state thật bên dưới chưa sạch.

## 3. Cổng Test

Pass khi:

1. AI có chạy test tương xứng với phạm vi đã sửa.
2. Command và kết quả test được ghi rõ.
3. Nếu chưa thể chạy hết, AI nêu blocker thật và không claim done quá mức.

Reject ngay khi:

1. Không có lệnh test cụ thể.
2. Chỉ nói “đã test” nhưng không ghi command/result.
3. Test fail nhưng vẫn kết luận xong.
4. Né test bằng lý do mơ hồ như “thay đổi nhỏ nên không cần”.

## 4. Cổng Quality

Pass khi:

1. Patch nhỏ, trực tiếp, dễ đọc.
2. Không thêm abstraction mới không cần thiết.
3. Copy user-facing là tiếng Việt có dấu.
4. Nếu màn đã có l10n, không hardcode thêm vô tội vạ.
5. Không làm flow rối hơn trong khi mục tiêu chỉ là patch hành vi.

Reject ngay khi:

1. Tạo helper/class mới không cần thiết chỉ để bọc vài dòng.
2. Thêm hardcoded string mới ở màn đang cleanup l10n mà không có lý do.
3. Làm flow phức tạp hơn trong khi bug chỉ cần patch nhỏ.
4. Sửa một chỗ nhưng làm lệch hành vi chỗ liên quan mà không nói rõ.

## 5. Red flags theo workstream

### A. `CORE-TRUTH`

Reject nếu:

1. Hàm vẫn trả outcome mơ hồ cho nhiều trạng thái khác nhau.
2. UI vẫn báo thành công cho thao tác mới chỉ queue offline.
3. Save/end/reactivate plan không làm tươi Home và notification trong cùng flow.

### B. `SCAN-JOURNEY`

Reject nếu:

1. Làm đẹp hóa dữ liệu scan cũ thay vì giữ metadata gốc.
2. Scan fail nhưng không có guidance hoặc recovery path rõ ràng.
3. Reopen/reuse làm mất `scanId`, `qualityState`, `guidance`, `mappingStatus` hoặc dữ liệu quan trọng tương tự.

### C. `AI-SAFETY`

Reject nếu:

1. Warning hoặc suggestion được trình bày như sự thật chắc chắn.
2. Auto-save plan từ AI mà bỏ qua bước review/confirm.
3. Ranking/score thay đổi nhưng không giải thích được logic.

### C1. `MED-SNAPSHOT`

Reject nếu:

1. Mỗi nguồn dữ liệu vẫn giữ shape riêng, không gom về snapshot chuẩn.
2. Snapshot v1 phụ thuộc bắt buộc vào enrichment optional như `manufacturer` hoặc `packaging` nên dễ fail toàn flow.
3. Snapshot tự suy diễn `instruction`, `quantity`, `unit` dù nguồn chưa chắc.

### C2. `RECONCILIATION`

Reject nếu:

1. Diff chỉ là text mô tả, không có output cấu trúc.
2. Engine kết luận mạnh khi OCR yếu hoặc mappingStatus chưa chắc.
3. `same active ingredient` bị trình bày như chắc chắn cùng mục đích kê đơn.

### C3. `TOC-SAFETY`

Reject nếu:

1. UI/surface safety tự tạo business logic riêng, không bám output của reconciliation.
2. Risk labels quá nặng tính khẳng định lâm sàng.

### C4. `DISPENSED-TEXT`

Reject nếu:

1. Flow text-first bị mô tả hoặc implement như loose-pill verification.
2. Kết quả yếu vẫn bị đẩy sang `confirmed` thay vì candidate/manual review.

### D. `ADHERENCE`

Reject nếu:

1. Analytics không truy ra được từ logs thật.
2. UI summary mâu thuẫn với weekly grid hoặc daily details.

### E. `PILL-ASSIST`

Reject nếu:

1. Verify fail làm hỏng reminder/log chính.
2. Không có manual path rõ ràng khi matcher không chắc.
3. Đẩy flow experimental vào release gate chính mà không nói rõ.

### F. `REGRESSION-GUARDS`

Reject nếu:

1. Test mới chỉ chụp screenshot mà không assert hành vi.
2. Contract test không kiểm tra shape dữ liệu thật giữa các tầng.

## 6. Câu hỏi reviewer nên tự hỏi

1. Patch này có giải quyết đúng mục tiêu trong workstream không?
2. Nếu bỏ phần copy mới đi, bug cũ còn nguyên không?
3. Có dấu hiệu “make it look successful” thay vì “make it correct” không?
4. Có cách nào đơn giản hơn patch này không?
5. Với workstream này, test đã đủ để chặn hồi quy tương tự chưa?
