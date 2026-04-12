# App Execution Board

File này dùng để điều phối execution model cho từng lát cắt đang chạy.

Planner/reviewer là AI điều phối. Root hiện giữ initiative active mới nhất về `ổn định + tái cấu trúc app nhắc uống thuốc`.

---

## Trạng thái hiện tại

- Initiative active hiện tại: `Ổn định và tái cấu trúc app nhắc uống thuốc`.
- Localization nền và core flow copy đã hoàn thành phần lớn, nhưng hiện không còn là initiative đủ rộng để dẫn dắt roadmap.
- Runtime local đã được phục hồi và startup/debug path đã được harden ở mức code trong `REL-1A`.

---

## Active execution plans

### 1. Coding slice active

- `HOME-1A — Home priority fix`
- Trạng thái: `ready_to_assign`
- Model khuyến nghị: `Claude Sonnet 4.6 Thinking`

- `REMIND-1A-R1B — reschedule đúng khi bật lại reminder`
- Trạng thái: `ready_to_assign`
- Model khuyến nghị: `GPT-5.3 Codex`

### 2. Parallel research / spec slices

- `IA-0A — Home / History / Create flow redesign brief`
- Trạng thái: `completed`
- Model khuyến nghị: `Claude Sonnet 4.6 Thinking`

- `LOCAL-0A — Local-first / reminder architecture audit`
- Trạng thái: `completed`
- Model khuyến nghị: `Gemini 3.1 Pro High`

- `BRAND-0A — Branding / copy / naming / asset inventory`
- Trạng thái: `completed`
- Model khuyến nghị: `Gemini 3 Flash`

---

## Hàng chờ sau batch hiện tại

### Reliability

- `REL-1B — Mobile network diagnostics và reconnect UX`
- Trạng thái: `completed`

### Branding

- `BRAND-1 — Final app name + launcher/splash/background + brand copy`
- Trạng thái: `queued_after_BRAND-0A`
- Ghi chú planner: chưa đổi `mobile/pubspec.yaml:name` trong slice branding đầu tiên; chỉ đổi in-app title, launcher label, l10n copy, manifest/resource/web branding trừ khi có quyết định migration package riêng.

- `BRAND-1-PREP — exact rebrand brief with safe scope`
- Trạng thái: `completed`
- Model khuyến nghị: `Gemini 3 Flash`

- `HOME-1A-PREP — exact file/line brief cho home priority fix`
- Trạng thái: `completed`
- Model khuyến nghị: `Gemini 3 Flash`

- `BRAND-1A-ASSET-PREP — exact asset pipeline cho launcher/splash/background`
- Trạng thái: `ready_to_assign`
- Model khuyến nghị: `Gemini 3 Flash`

### Home

- `HOME-1 — Chỉ foreground thuốc tới giờ và sắp tới giờ`
- Trạng thái: `queued_after_IA-0A`

### Working defaults đã khóa từ planner

- Phase B CTAs sẽ bị ẩn hoàn toàn khỏi Home path chính
- due-now window mặc định là `±30 phút`
- reuse flow mặc định sẽ đi qua review/edit trước khi sang schedule
- History tab order sẽ đổi thành `uống thuốc trước, quét sau`
- tab `Thuốc` tạm thời được giữ trong bottom nav ở batch này

### Create Flow

- `FLOW-1A — Redesign entry hub và reuse history flow`
- `FLOW-1B — Manual entry UX cleanup`
- Trạng thái: `queued_after_IA-0A`

- `FLOW-1A-PREP — exact reuse flow contract và route brief`
- Trạng thái: `completed`
- Model khuyến nghị: `Claude Sonnet 4.6 Thinking`

- `FLOW-1A — Reuse flow implementation`
- Trạng thái: `completed`
- Ghi chú planner: repo đã có code thật (`reuse_history_screen.dart` + router/create/history detail updates) và đã verify `flutter analyze` + `flutter test` pass.

- `FLOW-1B-PREP — manual entry UX cleanup brief`
- Trạng thái: `completed`
- Model khuyến nghị: `Claude Sonnet 4.6 Thinking`

- `FLOW-1B-A — manual entry routing + empty state fix`
- Trạng thái: `completed`
- Ghi chú planner: `FLOW-1B-HF1` đã đưa key `editDrugsEmptyAddFirst` vào `app_vi.arb`, regenerate l10n và verify `flutter gen-l10n` + `flutter analyze` + `flutter test` pass.

### History

- `HISTORY-1 — Reframe history around medication behavior`
- Trạng thái: `queued_after_IA-0A`

- `HISTORY-1-DATA-PREP — mobile-only vs backend-touch assessment`
- Trạng thái: `completed`
- Model khuyến nghị: `Gemini 3.1 Pro High`

- `HISTORY-1A-S1 — mobile-only IA shift`
- Trạng thái: `ready_to_assign`
- Model khuyến nghị: `Gemini 3.1 Pro High`

### Reminders / Local-first

- `REMIND-1 — Out-of-app reminder delivery`
- `LOCAL-1 — Local-first plans/home/log cache`
- Trạng thái: `queued_after_LOCAL-0A`

- `LOCAL-1A-PREP — exact cache/storage brief cho stale-while-revalidate`
- Trạng thái: `completed`
- Model khuyến nghị: `Gemini 3.1 Pro High`

- `REMIND-1B-PREP — permission/recovery UX brief cho reminders`
- Trạng thái: `completed`
- Model khuyến nghị: `Claude Sonnet 4.6 Thinking`

### Prep slices mở tiếp khi có slot

- `REL-1B-PREP — exact mobile network/reconnect UX inventory`
- Trạng thái: `completed`
- Model khuyến nghị: `Gemini 3 Flash`

- `REMIND-1A-PREP — exact Android reminder delivery brief`
- Trạng thái: `completed`
- Model khuyến nghị: `Gemini 3.1 Pro High`

---

## Đã hoàn thành / baseline đã có

- `L10N-1A` — Foundation localization
- `L10N-1B` — Shared copy
- `L10N-2A` — Auth + Home + Create entry copy cleanup
- `L10N-2B` — Scan + Review + Edit drugs + Schedule copy cleanup
- `L10N-2B-HF1` — clean pass hotfix sau review
- `BUG-SCAN-0DRUGS-1A` — manual runtime recovery để tiếp tục test local
- `REL-1A` — harden local startup và scan runtime detection
- `REL-1B-PREP` — inventory mobile network/reconnect UX
- `REMIND-1A-PREP` — Android reminder delivery brief
- `BRAND-1-PREP` — safe rebrand brief
- `HISTORY-1-DATA-PREP` — mobile-only vs backend-touch assessment
- `REL-1B` — mobile network diagnostics và reconnect UX
- `FLOW-1B-PREP` — manual entry UX cleanup brief
- `FLOW-1B-HF1` — ARB/source-of-truth hotfix cho manual entry CTA
- `HOME-1A-PREP` — exact file/line brief cho home priority fix
- `LOCAL-1A-PREP` — exact cache/storage brief cho stale-while-revalidate
- `REMIND-1B-PREP` — permission/recovery UX brief cho reminders

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
- Coding slice active hiện tại là `HOME-1A`; `REMIND-1A-R1B` là coding slice song song nhỏ, ít phụ thuộc.
- Không được mở `BRAND-1`, `HOME-1`, `FLOW-1`, `HISTORY-1`, `REMIND-1`, `LOCAL-1` trước khi planner đọc xong output của batch hiện tại.
- Nếu một task phát hiện phải đụng `scripts/run_pipeline.py` hoặc logic scan core thì phải dừng và trả blocker.
