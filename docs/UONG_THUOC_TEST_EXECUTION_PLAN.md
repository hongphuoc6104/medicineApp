# Uong Thuoc Test Execution Plan

Last updated: 2026-04-14

## 1. Muc tieu dot sua nay

- Dua `Phase A` benchmark `data/input/prescription_3/IMG_20260209_180505.jpg` ve lai muc tieu `5/5 drugs`.
- Dua Python automated suite ve xanh hoac chi con cac test da duoc cap nhat hop ly theo contract hien tai.
- On dinh mobile boot/auth restore de QA integration smoke bat dau tu state sach, khong bi token cu day vao `/home`.
- Giu Node backend test suite tiep tuc xanh de lam guardrail.

## 2. Dau vao tu dot test vua chay

### 2.1 Da pass

- `server-node`: `npm run migrate && npm test` -> `74/74` pass.
- `mobile`: `flutter analyze` -> pass.
- `mobile`: `flutter test test/widget_test.dart` -> pass.
- `python`: `scripts/test_preprocess_robustness.py` -> `36/36` pass.

### 2.2 Dang loi / can xu ly

1. `Phase A` CLI smoke chi ra `4` thuoc thay vi `5` tren anh benchmark `IMG_20260209_180505.jpg`.
2. `pytest tests` fail 4 case:
   - `_run_ocr(..., bbox_offset=...)` khong con dung contract cu.
   - `_extract_medications()` khong con tra `(medications, candidates)` nhu test cu.
   - `crop_by_mask()` tra `None` voi fixture mask cu.
   - `crop_by_mask()` clamp padding test fail cung ly do tren.
3. `mobile` integration smoke fail som do boot/session state khong on dinh tren emulator.

## 3. Thu tu thuc hien

### Phase 1. Fix regression Phase A

Status: completed

Muc tieu:

- Xac dinh vi sao `group_by_stt()` gom nham `Mecobalamin` va `Loratadine`.
- Them regression test cho truong hop thieu STT anchor nhung van phai tach 2 dong thuoc.
- Sua voi thay doi toi thieu trong `core/phase_a/s3_ocr/ocr_engine.py` hoac diem goi lien quan.
- Chay lai:
  - `venv/bin/python scripts/run_pipeline.py --image data/input/prescription_3/IMG_20260209_180505.jpg`
  - kiem tra `summary.json`

Exit criteria:

- anh benchmark tra lai du `5` thuoc.

### Phase 2. Dua Python tests ve xanh

Status: completed

Muc tieu:

- Tach ro test nao la regression dung, test nao da lech contract noi bo.
- Neu contract cu van can giu -> khong pha public behavior.
- Neu test cu da stale -> cap nhat test de assert public behavior hien tai.

Pham vi uu tien:

1. `tests/test_bug_fixes.py`
2. `tests/test_segmentation.py`

Exit criteria:

- `venv/bin/python -m pytest tests -q -p no:cacheprovider` xanh.

### Phase 3. On dinh mobile boot/session cho QA smoke

Status: in_progress

Muc tieu:

- Neu secure storage co token/user cu hoac token het han, app khong duoc coi la authenticated mot cach lac quan.
- Boot phai clear session hong/het han va quay lai `/login` an toan.
- Giam phu thuoc vao state cu cua emulator.

Pham vi doc/sua du kien:

- `mobile/lib/features/auth/data/auth_repository.dart`
- `mobile/lib/features/auth/data/auth_notifier.dart`
- `mobile/lib/core/network/dio_client.dart`
- `mobile/android/app/src/main/AndroidManifest.xml`

Exit criteria:

- QA smoke co the bat dau tu login thay vi roi vao state cu khong on dinh.

### Phase 4. Re-run targeted suites

Status: completed

Can chay lai:

- `venv/bin/python -m pytest tests -q -p no:cacheprovider`
- `venv/bin/python scripts/test_preprocess_robustness.py`
- `venv/bin/python scripts/run_pipeline.py --image data/input/prescription_3/IMG_20260209_180505.jpg`
- `cd server-node && npm test`
- `cd mobile && flutter analyze`
- `cd mobile && flutter test test/widget_test.dart`
- `cd mobile && flutter test integration_test/qa_smoke_test.dart ...` neu da co state sach va credentials QA hop le

### Phase 5. Chot QA smoke navigation va selector

Status: completed

Muc tieu:

- Dua `mobile/integration_test/qa_smoke_test.dart` qua duoc cac man shell va non-shell mot cach on dinh.
- Loai bo cac selector gian va cac buoc dieu huong phu thuoc vao `back stack` mong manh.

Pham vi uu tien:

1. Dung helper dieu huong ro rang cho shell tabs: `/home`, `/plans`, `/history`.
2. Khi dung cac man ngoai shell (`/create`, `/create/reuse`, `/create/edit`) phai quay lai shell mot cach explicit truoc khi tap bottom nav.
3. Sau moi buoc dieu huong, assert anchor cua man hinh truoc khi tiep tuc.

Exit criteria:

- QA smoke khong con fail vi `No element`, `findsWidgets` timeout, hoac tap nham item do selector mong manh.

## 4. Ghi chu thuc thi

- Uu tien sua nho, khong lan sang cac phan dang xanh.
- Voi `scripts/run_pipeline.py`: khong refactor, chi them neu can.
- Moi regression moi phat hien trong qua trinh sua phai duoc ghi them vao file nay truoc khi tiep tuc.

## 5. Log cap nhat

- 2026-04-14: Tao plan tu ket qua dot test full matrix low-cost + smoke.
- 2026-04-14: Them regression script `scripts/tests/test_group_by_stt_missing_anchor.py` cho case thieu STT anchor.
- 2026-04-14: Sua fallback trong `group_by_stt()` de tach duoc `Mecobalamin` va `Loratadine` tren anh benchmark `IMG_20260209_180505.jpg`.
- 2026-04-14: Chay lai Phase A CLI smoke -> quay lai `5/5 drugs`.
- 2026-04-14: Dua Python suite ve xanh `42 passed`.
- 2026-04-14: Bo request permission thong bao khoi `NotificationService.initialize()`; permission gio chi xin khi user bat reminders.
- 2026-04-14: Them co `QA_RESET_SESSION_ON_BOOT` de QA integration smoke co the khoi dong tu state sach.
- 2026-04-14: Tach `qa_smoke_test.dart` thanh nhieu test ngan theo flow de giam flake va tranh ket noi mong manh giua shell/non-shell routes.
- 2026-04-14: Sua overflow that trong `mobile/lib/features/history/presentation/history_screen.dart` cho weekly grid cell.
- 2026-04-14: QA smoke pass toan bo tren emulator voi `QA_RESET_SESSION_ON_BOOT=true`.
