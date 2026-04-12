# App Execution Board

File này dùng để điều phối execution model cho từng lát cắt đang chạy.

Planner/reviewer là AI điều phối. Root hiện chỉ giữ bộ plan active mới nhất để tránh đọc nhầm scope.

---

## Trạng thái hiện tại

- Initiative active hiện tại: `Việt hóa toàn bộ phần hiển thị cho người dùng trong app`.
- Trọng tâm là `mobile/`, không phải redesign data model hay backend.
- Bộ plan active cũ đã được park vào `archive/plan_bin/2026-04-12_prescription-plan-group-redesign_superseded/`.
- Các file slice legacy còn sót ở root đã được chuyển vào `archive/plan_bin/2026-04-12_legacy_root_slice_plans/`.
- Trạng thái thực tế đã đi xa hơn plan cũ: `L10N-1` và phần lớn `L10N-2` đã xong.

---

## Active execution plans

### Active ngay lúc này

- `MVT-1 — Manual verify gate cho core flow sau L10N-2 clean pass`
- Mục tiêu: chuẩn bị checklist test thủ công và expected outcome để user tự verify core flow
- Trạng thái: `ready_to_assign`
- Model khuyến nghị: `Gemini 3.1 Pro`

### Gating sau khi xong lát cắt active

- user chạy manual verify core flow `Đăng nhập/Đăng ký -> Trang chủ -> Tạo kế hoạch -> Quét đơn thuốc -> Xác nhận -> Lập lịch`
- nếu flow ổn mới mở `L10N-3A`
- nếu flow lỗi thì mở đúng một hotfix nhỏ theo màn bị lỗi

---

## Đã hoàn thành trong initiative hiện tại

- `L10N-1A` — Foundation localization
- `L10N-1B` — Shared copy
- `L10N-2A` — Auth + Home + Create entry
- `Analyzer unblock baseline` — lint cleanup để trả `flutter analyze` về xanh
- `L10N-2B` — Scan + Review + Edit drugs + Schedule đã localize xong và đã qua review
- `L10N-2B-HF1` — clean pass hotfix sau review

---

## Hàng chờ sau lát cắt active

### L10N-3A

- `drug / plan`
- Trạng thái: `queued_after_manual_verify`
- Model khuyến nghị: `Gemini 3.1 Pro`

### L10N-3B

- `history / settings`
- Trạng thái: `queued_after_L10N-3A`
- Model khuyến nghị: `Gemini 3.1 Pro`

### Claude Opus Thinking

- Review sâu sau khi xong `L10N-3`
- Trạng thái: `queued_review`

### L10N-4

- `pill verification` copy + repo-wide sweep cuối
- Trạng thái: `queued_after_L10N-3_review`
- Model khuyến nghị: `Claude Sonnet Thinking`

---

## Archive tham chiếu

- `archive/plan_bin/2026-04-12_prescription-plan-group-redesign_superseded/APP_ACTIVE_GENERAL_PLAN.md`
- `archive/plan_bin/2026-04-12_prescription-plan-group-redesign_superseded/APP_ACTIVE_DETAILED_PLAN.md`
- `archive/plan_bin/2026-04-12_legacy_root_slice_plans/APP_DETAIL_GEMINI_3_1_PRO_SLICE_7A_SCAN_AUTO.md`
- `archive/plan_bin/2026-04-12_legacy_root_slice_plans/APP_DETAIL_CLAUDE_SONNET_THINKING_SLICE_7B_DRUG_ENTRY_STABLE.md`
- `archive/plan_bin/2026-04-12_legacy_root_slice_plans/APP_DETAIL_GPT_5_3_CODEX_SLICE_7C_SIMPLE_SCHEDULE.md`

---

## Quy tắc điều phối

- Mỗi execution model chỉ làm đúng một lát cắt `L10N-x` đã được giao.
- Không được sửa file nằm ngoài danh sách cho phép trong lát cắt tương ứng.
- Nếu cần đụng sang backend, Phase B logic hoặc pipeline để hoàn thành việc Việt hóa, phải dừng và trả blocker.
- Sau mỗi lát cắt, planner/reviewer sẽ nghiệm thu lại copy, phạm vi sửa và test.
- Sau khi xong `L10N-2B-HF1`, phải manual verify lại core flow trước khi mở `L10N-3A`.
- Chỉ khi toàn initiative hoàn tất và user nghiệm thu mới được archive general plan active.
