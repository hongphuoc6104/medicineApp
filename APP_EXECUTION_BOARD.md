# App Execution Board

## Source of truth hiện tại

1. `APP_ACTIVE_GENERAL_PLAN.md`
2. `APP_ACTIVE_DETAILED_PLAN.md`

## Cách dùng

- `APP_ACTIVE_GENERAL_PLAN.md` giữ bức tranh lớn và thứ tự ưu tiên.
- `APP_ACTIVE_DETAILED_PLAN.md` là master handoff + review spec để giao slice cho AI execution khác.
- Không dùng file này để ghi dài dòng status từng task; chỉ dùng để nhắc active sequence.

## Active sequence

1. `MOBILE-P0-A` — truthful state, auth, shell navigation
2. `MOBILE-P0-B` — plan/today/reminder integrity
3. `MOBILE-P1-A` — create/scan/reuse truthfulness
4. `MOBILE-P1-B` — search/history completeness và async safety
5. `MOBILE-P1-C` — state UX, copy, l10n, accessibility, responsive cleanup
6. `MOBILE-P2-A` — Phase B mobile entry decision và gating
7. `MOBILE-P2-B` — regression tests

## Rule

- chỉ giao đúng một slice mỗi lần
- không mở slice sau nếu slice trước chưa qua review khắt khe
- mọi báo cáo của AI execution phải theo `Protocol output bắt buộc` trong `APP_ACTIVE_DETAILED_PLAN.md`
