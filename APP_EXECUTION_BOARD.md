# App Execution Board

File này dùng để điều phối execution model cho từng lát cắt đang chạy.

Planner/reviewer là AI điều phối. Các file dưới đây là plan chi tiết theo từng model.

---

## Trạng thái hiện tại

- Batch cũ Phase A đã hoàn thành và đã archive.
- Initiative active mới: `Elderly-First Create Flow Simplification`.
- Batch hiện tại dùng cơ chế `parallel batch`: `7A / 7B / 7C` chạy song song, sau đó user test gộp một lần.

---

## Active execution plans

### 1. Gemini 3.1 Pro

- File: `APP_DETAIL_GEMINI_3_1_PRO_SLICE_7A_SCAN_AUTO.md`
- Handoff: `docs/agent_handoffs/gemini_3_1_pro_slice_7a_scan_auto.md`
- Mục tiêu: `Lát cắt 7A — Scan UX tự động hơn và thực dụng hơn`
- Trạng thái: `ready_to_restart_in_parallel_batch`

### 2. Claude Sonnet Thinking

- File: `APP_DETAIL_CLAUDE_SONNET_THINKING_SLICE_7B_DRUG_ENTRY_STABLE.md`
- Handoff: `docs/agent_handoffs/claude_sonnet_thinking_slice_7b_drug_entry_stable.md`
- Mục tiêu: `Lát cắt 7B — Sửa OCR mượt hơn`
- Trạng thái: `active`

### 3. GPT-5.3 Codex

- File: `APP_DETAIL_GPT_5_3_CODEX_SLICE_7C_SIMPLE_SCHEDULE.md`
- Handoff: `docs/agent_handoffs/gpt_5_3_codex_slice_7c_simple_schedule.md`
- Mục tiêu: `Lát cắt 7C — Lập lịch dễ hiểu hơn`
- Trạng thái: `active`

---

## Hàng chờ sau đợt này

### Claude Opus Thinking

- Chưa giao việc ở đợt này.
- Vai trò dự phòng cho blocker khó hoặc review sâu nếu một execution model dừng theo luật stop.

### Lát cắt 6

- `create entry + history reuse`
- `6A`, `6B`, `6C` đều đã hoàn thành và đã được archive.

### Lát cắt 7

- Đã mở dưới dạng `7A / 7B / 7C`.
- Cả `7A`, `7B`, `7C` được phép chạy song song trong batch hiện tại.

### Lát cắt 8

- Prescription-first UX
- Chưa mở.
- Chỉ xem xét sau khi `7A`, `7B`, `7C` được user test và đồng ý.

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
