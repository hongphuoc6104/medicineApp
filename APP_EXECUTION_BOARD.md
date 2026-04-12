# App Execution Board

File này dùng để điều phối execution model cho từng lát cắt đang chạy.

Planner/reviewer là AI điều phối. Root hiện giữ initiative active mới nhất về `ổn định + tái cấu trúc app nhắc uống thuốc`.

---

## Trạng thái hiện tại

- Initiative active hiện tại: `Ổn định và tái cấu trúc app nhắc uống thuốc`.
- Localization nền và core flow copy đã hoàn thành phần lớn, nhưng hiện không còn là initiative đủ rộng để dẫn dắt roadmap.
- Runtime local đã được phục hồi thủ công để user test tiếp, nhưng startup/debug path vẫn chưa được harden ở mức code.

---

## Active execution plans

### 1. Coding slice active

- `REL-1A — Harden local startup và scan runtime detection`
- Trạng thái: `ready_to_assign`
- Model khuyến nghị: `GPT-5.3 Codex`

### 2. Parallel research / spec slices

- `IA-0A — Home / History / Create flow redesign brief`
- Trạng thái: `ready_to_assign`
- Model khuyến nghị: `Claude Sonnet 4.6 Thinking`

- `LOCAL-0A — Local-first / reminder architecture audit`
- Trạng thái: `ready_to_assign`
- Model khuyến nghị: `Gemini 3.1 Pro High`

- `BRAND-0A — Branding / copy / naming / asset inventory`
- Trạng thái: `ready_to_assign`
- Model khuyến nghị: `Gemini 3 Flash`

---

## Hàng chờ sau batch hiện tại

### Reliability

- `REL-1B — Mobile network diagnostics và reconnect UX`
- Trạng thái: `queued_after_REL-1A`

### Branding

- `BRAND-1 — Final app name + launcher/splash/background + brand copy`
- Trạng thái: `queued_after_BRAND-0A`

### Home

- `HOME-1 — Chỉ foreground thuốc tới giờ và sắp tới giờ`
- Trạng thái: `queued_after_IA-0A`

### Create Flow

- `FLOW-1A — Redesign entry hub và reuse history flow`
- `FLOW-1B — Manual entry UX cleanup`
- Trạng thái: `queued_after_IA-0A`

### History

- `HISTORY-1 — Reframe history around medication behavior`
- Trạng thái: `queued_after_IA-0A`

### Reminders / Local-first

- `REMIND-1 — Out-of-app reminder delivery`
- `LOCAL-1 — Local-first plans/home/log cache`
- Trạng thái: `queued_after_LOCAL-0A`

---

## Đã hoàn thành / baseline đã có

- `L10N-1A` — Foundation localization
- `L10N-1B` — Shared copy
- `L10N-2A` — Auth + Home + Create entry copy cleanup
- `L10N-2B` — Scan + Review + Edit drugs + Schedule copy cleanup
- `L10N-2B-HF1` — clean pass hotfix sau review
- `BUG-SCAN-0DRUGS-1A` — manual runtime recovery để tiếp tục test local

---

## Legacy plan status

- `L10N-3A`, `L10N-3B`, `L10N-4` không còn được mở như một initiative độc lập.
- Các phần việc tương ứng đã được hấp thụ vào các slice mới: `BRAND-1`, `FLOW-1`, `HISTORY-1`, `REMIND-1`.

---

## Archive tham chiếu

- `archive/plan_bin/2026-04-12_prescription-plan-group-redesign_superseded/`
- `archive/plan_bin/2026-04-12_legacy_root_slice_plans/`
- `archive/plan_bin/2026-04-12_l10n-only-initiative_superseded/`

---

## Quy tắc điều phối

- Mỗi execution model chỉ làm đúng một task đã được planner khóa scope.
- Chỉ `REL-1A` là coding slice active ở đợt này; ba task còn lại là read/spec song song.
- Không được mở `BRAND-1`, `HOME-1`, `FLOW-1`, `HISTORY-1`, `REMIND-1`, `LOCAL-1` trước khi planner đọc xong output của batch hiện tại.
- Nếu một task phát hiện phải đụng `scripts/run_pipeline.py` hoặc logic scan core thì phải dừng và trả blocker.
