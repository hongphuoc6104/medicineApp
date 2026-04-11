# App Execution Board

File này dùng để điều phối execution model cho từng lát cắt đang chạy.

Planner/reviewer là AI điều phối. Các file dưới đây là plan chi tiết theo từng model.

---

## Trạng thái hiện tại

- Batch cũ Phase A đã hoàn thành và đã archive.
- Initiative active hiện tại: `Prescription Plan Group Redesign`.
- Mục tiêu đang triển khai: bỏ hẳn mô hình `1 plan = 1 thuốc`, chuyển sang `1 kế hoạch nhiều thuốc nhiều khung giờ`.

---

## Active execution plans

Hiện tại planner đang trực tiếp triển khai nền tảng cho initiative mới (9A/9B/9C hợp nhất) để tạo được flow khả dụng trước khi chia lại cho execution models.

---

## Hàng chờ sau đợt này

### Claude Opus Thinking

- Chưa giao việc ở đợt này.
- Vai trò dự phòng cho blocker khó hoặc review sâu nếu một execution model dừng theo luật stop.

### Lát cắt 6

- `create entry + history reuse`
- `6A`, `6B`, `6C` đều đã hoàn thành và đã được archive.

### Lát cắt 9A / 9B / 9C

- Backend foundation plan group mới
- Mobile domain/repository mới
- Schedule screen save theo plan group mới
- Trạng thái: `in_progress`

### Lát cắt 9D

- Home / plan list / detail theo model mới
- Trạng thái: `partially_in_progress`

### Lát cắt 10

- Prescription-first UX sâu hơn
- Chưa mở

---

## Completed in previous batches

- `APP_DETAIL_GEMINI_3_1_PRO_SLICE_3.md`
- `APP_DETAIL_CLAUDE_SONNET_THINKING_SLICE_4.md`
- `APP_DETAIL_CLAUDE_SONNET_THINKING_HOTFIX_ANALYZE.md`
- `APP_DETAIL_GPT_5_3_CODEX_SLICE_5.md`
- `APP_DETAIL_GPT_5_3_CODEX_SLICE_6A_CREATE_ENTRY.md`
- `APP_DETAIL_GEMINI_3_1_PRO_SLICE_6B_SCAN_HISTORY_REUSE.md`
- `APP_DETAIL_CLAUDE_SONNET_THINKING_SLICE_6C_HISTORY_LIST.md`

---

## Quy tắc điều phối

- Mỗi execution model chỉ làm đúng file plan của mình.
- Không được sửa file nằm ngoài danh sách cho phép trong plan model tương ứng.
- Nếu cần đụng sang file đang thuộc model khác, phải dừng và trả blocker.
- Sau khi xong, planner/reviewer sẽ nghiệm thu từng lát cắt.
- Sau khi đủ `7A + 7B + 7C`, planner mới mời user test gộp một lần.
