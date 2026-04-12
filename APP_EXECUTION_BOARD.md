# App Execution Board

File này dùng để điều phối execution model cho từng lát cắt đang chạy.

Planner/reviewer là AI điều phối. Root hiện chỉ giữ bộ plan active mới nhất để tránh đọc nhầm scope.

---

## Trạng thái hiện tại

- Initiative active hiện tại: `Việt hóa toàn bộ phần hiển thị cho người dùng trong app`.
- Trọng tâm là `mobile/`, không phải redesign data model hay backend.
- Bộ plan active cũ đã được park vào `archive/plan_bin/2026-04-12_prescription-plan-group-redesign_superseded/`.
- Các file slice legacy còn sót ở root đã được chuyển vào `archive/plan_bin/2026-04-12_legacy_root_slice_plans/`.

---

## Active execution plans

Hiện tại planner vừa reset plan và chưa tách execution file riêng theo model.

Lát cắt sẵn sàng mở đầu tiên:

- `L10N-1 — Foundation và shared copy`
- Trạng thái: `ready_to_assign`

---

## Hàng chờ sau đợt này

### L10N-2

- Core flow `auth -> home -> create plan -> scan -> review -> schedule`
- Trạng thái: `queued_after_L10N-1`

### L10N-3

- `drug / plan / history / settings`
- Trạng thái: `queued_after_L10N-2`

### L10N-4

- `pill verification` copy + repo-wide sweep cuối
- Trạng thái: `queued_after_L10N-3`

### Claude Opus Thinking

- Chưa giao việc ở đợt này.
- Vai trò dự phòng cho blocker khó hoặc review sâu nếu một execution model dừng theo luật stop.

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
- Sau khi xong `L10N-2`, nên mời user kiểm tra riêng luồng chính trước khi mở rộng ra các màn còn lại.
