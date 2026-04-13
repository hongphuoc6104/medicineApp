# AI Review Checklist

File này dùng để nghiệm thu output của AI execution khác.

File nguồn phải đọc kèm:

1. `APP_ACTIVE_GENERAL_PLAN.md`
2. `APP_ACTIVE_DETAILED_PLAN.md`

Nếu AI execution làm khác hai file trên, ưu tiên reject.

---

## Cách dùng

1. Xác định `Slice ID` mà AI được giao.
2. Mở đúng section tương ứng trong `APP_ACTIVE_DETAILED_PLAN.md`.
3. Đối chiếu output của AI với checklist file này.
4. Chỉ accept khi qua đủ 4 cổng: scope, logic, test, quality.

---

## 0. Thông tin bắt buộc phải có trong output của AI

Reject ngay nếu thiếu bất kỳ mục nào sau đây:

1. `Slice ID`
2. `Issue IDs đã xử lý`
3. `Files đã đọc`
4. `Files đã sửa`
5. `Cách sửa chính`
6. `Những gì cố ý không sửa`
7. `Lệnh test đã chạy`
8. `Kết quả test`
9. `Manual smoke đã kiểm tra / chưa kiểm tra`
10. `Rủi ro còn lại`

---

## 1. Cổng Scope

### Pass khi

1. AI chỉ sửa đúng slice được giao.
2. Các file sửa nằm trong `In scope` của slice.
3. Không đụng `server/**`, `server-node/**`, `core/**`, `scripts/run_pipeline.py` nếu slice không cho phép.
4. Không mở rộng task sang redesign/refactor lớn ngoài yêu cầu.

### Reject ngay khi

1. Sửa ngoài scope mà không báo blocker trước.
2. Refactor rộng chỉ để “đẹp code”.
3. Tự mở thêm feature không nằm trong slice.
4. Chạm native/backend/pipeline ngoài scope rồi mới báo sau.

### Câu hỏi reviewer phải tự hỏi

1. AI có đang giải quyết đúng issue ID được giao không?
2. Có file nào bị sửa nhưng không xuất hiện trong `In scope` không?
3. Có dấu hiệu “tiện tay dọn luôn” không?

---

## 2. Cổng Logic

### Pass khi

1. Fix đúng bản chất lỗi, không chỉ đổi wording bề mặt.
2. Trạng thái trước và sau sửa được giải thích rõ.
3. Không fabricate data để UI trông đẹp hơn.
4. Không che giấu state xấu bằng copy gây hiểu nhầm.

### Reject ngay khi

1. Chỉ đổi snackbar/text nhưng logic sai vẫn còn.
2. Giấu lỗi offline/sync bằng message thành công.
3. Ép `confidence`, `mappingStatus`, `rejected`, `qualityState` hoặc data tương tự về trạng thái đẹp hơn thực tế.
4. Redirect cưỡng bức nhưng state thật bên dưới chưa sạch.

### Câu hỏi reviewer phải tự hỏi

1. Đây là fix logic thật hay chỉ là fix cảm giác UI?
2. Nếu bỏ phần copy mới đi, bug cũ có còn nguyên không?
3. Có chỗ nào đang “make it look successful” thay vì “make it correct” không?

---

## 3. Cổng Test

### Pass khi

1. AI đã chạy:

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

2. Nếu có manual smoke quan trọng, AI ghi rõ đã kiểm tra gì và chưa kiểm tra gì.
3. Nếu test không chạy được, AI nêu blocker thật và không claim done.

### Reject ngay khi

1. Không có lệnh test cụ thể.
2. Chỉ nói “đã test” nhưng không ghi command/result.
3. Test fail nhưng vẫn kết luận xong.
4. Né test bằng lý do mơ hồ như “thay đổi nhỏ nên không cần”.

### Câu hỏi reviewer phải tự hỏi

1. Có bằng chứng chạy test không?
2. Kết quả test có khớp với những file bị sửa không?
3. Với bug loại P0, AI có ghi manual smoke tương ứng không?

---

## 4. Cổng Quality

### Pass khi

1. Patch nhỏ, trực tiếp, dễ đọc.
2. Không thêm abstraction mới không cần thiết.
3. Copy user-facing là tiếng Việt có dấu.
4. Nếu màn đã có l10n, không hardcode thêm vô tội vạ.
5. Không làm phát sinh dead-end hoặc navigation lạ.

### Reject ngay khi

1. Tạo helper/class mới không cần thiết chỉ để bọc vài dòng.
2. Thêm hardcoded string mới ở màn đang cleanup l10n mà không có lý do.
3. Làm flow phức tạp hơn trong khi bug chỉ cần patch nhỏ.
4. Sửa một chỗ nhưng làm lệch hành vi chỗ liên quan.

### Câu hỏi reviewer phải tự hỏi

1. Có cách nào đơn giản hơn patch này không?
2. AI có over-engineer không?
3. Patch có tạo gánh nặng review không cần thiết không?

---

## 5. Red Flags đặc biệt theo loại lỗi

### A. Truthful state / offline / sync

Reject nếu:

1. Hàm vẫn trả `bool` mơ hồ cho nhiều outcome khác nhau.
2. UI vẫn báo thành công cho thao tác mới chỉ queue offline.
3. AI không phân biệt `synced`, `queuedOffline`, `failed` hoặc tương đương.

### B. Auth / router

Reject nếu:

1. Chỉ xóa secure storage nhưng không cập nhật auth state.
2. Chỉ ép `context.go(...)` mà không giải quyết session invalidation thật.
3. Tạo dependency vòng giữa network layer và UI.

### C. Plan / Home / reminder

Reject nếu:

1. Chỉ invalidate provider mà không đảm bảo refresh/schedule đúng lúc.
2. Fix create nhưng bỏ quên deactivate/reactivate.
3. Home vẫn hiện empty state sai ngữ nghĩa.

### D. Scan / reuse / review

Reject nếu:

1. Dữ liệu scan bị làm đẹp hóa khi quay lại review.
2. `needsReview` có badge nhưng không bám data thật.
3. Preview tap vẫn chụp nhầm như cũ.

### E. Search / history

Reject nếu:

1. Có debounce nhưng không chống stale result.
2. List vẫn chỉ page đầu nhưng UI không nói rõ.
3. Error state không có retry path.

### F. Copy / l10n / accessibility

Reject nếu:

1. Vẫn còn thêm hardcoded strings mới trong patch cleanup.
2. Thêm semantics tượng trưng, bỏ sót custom control chính.
3. Sửa responsive nhưng tạo layout rỗng hoặc khó dùng hơn.

### G. Phase B / pill verification

Reject nếu:

1. Chỉ thêm CTA/route mà không chốt `hide` hay `integrate`.
2. Confirm button vẫn enable chỉ dựa trên `detections.isEmpty`.
3. Xác minh xong nhưng mark taken fail mà không có xử lý nhất quán.

### H. Tests

Reject nếu:

1. Chỉ thay `widget_test.dart` bằng một smoke test vô nghĩa khác.
2. Test mới không gắn với regression cụ thể.
3. Over-mock đến mức test không còn kiểm tra behavior thật.

---

## 6. Checklist nghiệm thu theo từng slice

## `MOBILE-P0-A`

Pass khi reviewer trả lời `Có` cho tất cả câu sau:

1. User có phân biệt được `đã đồng bộ` và `đã lưu offline/chờ sync` không?
2. Refresh token fail có đẩy app về unauthenticated thật không?
3. `/settings` có thôi làm sáng tab `History` không?
4. Back từ Settings có ưu tiên `pop` thay vì `go('/home')` không?

## `MOBILE-P0-B`

1. Tạo plan mới xong có làm tươi `today schedule` không?
2. End/reactivate plan có sync reminder scheduling rõ ràng không?
3. Home có phân biệt ngày trống với ngày đã xử lý xong không?

## `MOBILE-P1-A`

1. Reuse/back flow có giữ dữ liệu scan thật không?
2. Review card có chỉ rõ item cần kiểm tra không?
3. Camera có giảm khả năng chụp nhầm không?

## `MOBILE-P1-B`

1. Search có stale-request guard thật không?
2. History/logs có còn cắt âm thầm page đầu không?
3. Drug search/detail có hierarchy rõ hơn không?

## `MOBILE-P1-C`

1. Copy mới có tiếng Việt có dấu và bớt hardcode không?
2. Custom controls chính có semantics cơ bản không?
3. Login/create có chịu được màn nhỏ tốt hơn không?
4. Settings có hết dead-end `Hồ sơ` chưa?

## `MOBILE-P2-A`

1. Đã chốt rõ `hide` hay `integrate` chưa?
2. Confirm gating có dựa trên readiness thật không?
3. Entry point Phase B có rõ ràng và không show bừa không?

## `MOBILE-P2-B`

1. Test mới có gắn với regression thật không?
2. Đã bỏ test placeholder vô nghĩa chưa?
3. Có ít nhất vài regression P0 được bảo vệ không?

---

## 7. Mẫu kết luận nghiệm thu

### Accept

```md
Kết luận: ACCEPT

Slice ID: <id>
Issue IDs: <ids>

Lý do accept:
1. <...>
2. <...>

Kiểm tra đã qua:
1. Scope
2. Logic
3. Test
4. Quality

Rủi ro còn lại:
1. <...>
```

### Reject

```md
Kết luận: REJECT

Slice ID: <id>
Issue IDs: <ids>

Lý do reject:
1. <vấn đề cụ thể>
2. <vấn đề cụ thể>

Bằng chứng:
1. File:line hoặc mô tả test thiếu
2. File:line hoặc hành vi còn sai

Yêu cầu làm lại:
1. <sửa gì>
2. <test gì>
3. <giới hạn scope>
```

---

## 8. Nguyên tắc cuối cùng

1. Nếu còn nghi ngờ giữa `có vẻ đúng` và `được chứng minh là đúng`, chọn reject.
2. Nếu patch làm UI đẹp hơn nhưng state thật vẫn sai, chọn reject.
3. Nếu AI nói quá nhiều nhưng không có bằng chứng code/test, chọn reject.
4. Nếu patch đúng nhưng vượt scope nhiều, vẫn reject và yêu cầu làm lại gọn hơn.
