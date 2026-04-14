# Uong Thuoc Full Test Plan

> File này là `test matrix` và `release gate` cho flow chính của app.
> Không dùng file này làm product development plan.
> Kế hoạch phát triển active xem tại `APP_ACTIVE_GENERAL_PLAN.md`.
> Quy tắc thực thi xem tại `APP_ACTIVE_DETAILED_PLAN.md`.

## 1. Muc tieu

Tai lieu nay la strict test matrix cho app `Uong thuoc`.

Muc tieu:

- Khong chi chup du screenshot, ma phai test dung hanh vi, dung du lieu, dung luong xu ly.
- Bao phu day du `happy`, `unhappy`, `recovery`, va `impossible/defensive` cho cac flow quan trong.
- Tach ro release gate cho `Phase A / medication reminder flow` va nhom route `experimental/direct-only`.
- Co bang chung cho UI, UX, du lieu local, du lieu backend, notification, va contract mobile-Node-Python.
- Co thu tu uu tien va tieu chi hoan tat de QA khong test theo cam tinh.

## 2. Nguyen tac bat buoc

- Screenshot chi la bang chung, khong duoc xem la ket qua test.
- Moi flow P0 bat buoc phai co 4 nhom case: `happy`, `unhappy`, `recovery`, `impossible/defensive`.
- Moi case bat buoc co 3 phan: `Expected UI`, `Expected data/state`, `Evidence`.
- Moi bug ve `notification`, `offline queue`, `auth/session`, `scan contract`, `plan save`, `history weekly grid` deu la bug nghiem trong.
- Cac route co ton tai nhung chua nam trong primary user journey phai duoc danh dau `direct-only` hoac `experimental`, khong duoc tron vao release gate chinh.
- Test mobile phai tach theo 4 lop: `widget/UI`, `state/notifier`, `API contract`, `real-device E2E`.
- Notification, exact alarm, camera permission, gallery picker, va OS popup phai test tren thiet bi that.
- Offline-first phai test voi mat mang that, app restart, va sync lai that. Khong duoc chi gia lap bang screenshot.
- Tat ca case co tinh thoi gian phai test bien, khong duoc chi test 1 moc chung chung.

## 3. Pham vi implementation da doi chieu

Phan nay duoc cap nhat theo code hien tai de tranh test theo tai lieu cu hoac theo suy doan:

- App title hien tai: `Uong thuoc`.
- Main shell co 3 tab chinh: `/home`, `/plans`, `/history`.
- `/settings` ton tai nhung nam ngoai 3 tab chinh, mo tu icon settings.
- Create flow gom: `/create`, `/create/scan`, `/create/review`, `/create/edit`, `/create/schedule`, `/create/reuse`.
- Drug flow gom: `/drugs`, `/drugs/detail`.
- Route fallback co ton tai va phai test.
- App co `auth restore session`, `refresh token`, `offline dose queue`, `today schedule cache`, `local notification`, `exact alarm permission`, `mark dose from notification action`.
- Home hien co logic `due now`, `upcoming`, `later today`, `auto missed sau 45 phut`, `pending sync warning`.
- Scan camera hien tai la primary `1 anh/lan`; backend van con session API cho multi-image, nhung do la contract/backend path, khong phai primary UI path.
- `/history/scan/:id` co route detail nhung khong thay entry-point ro rang trong primary UI hien tai; test theo direct route/deep link/dev navigation.
- `/pill-verify` va `/pill-reference/enroll` co route, nhung hien la `direct-only / experimental`, khong duoc chan release Phase A neu P0 da pass.

## 4. Muoi Sau Cach Test Du An Nay

| # | Cach test | Muc dich | Tu dong duoc? | Bat buoc cho release? |
|---|---|---|---|---|
| 1 | Flutter pure unit test | Test logic time/status/parser/network mapper | Co | Co |
| 2 | Flutter notifier/state test | Test auth, today schedule, queue, settings state | Co | Co |
| 3 | Flutter widget test | Test UI tung man va tung state | Co | Co |
| 4 | Flutter golden/screenshot test | Bat vo layout, text overflow, visual regression | Co | Nen co |
| 5 | Flutter integration voi backend mock | Test flow lon nhung assert duoc ket qua | Co | Co |
| 6 | Flutter real-device E2E | Test camera, notification, permission, exact alarm | Co mot phan | Co |
| 7 | Router/deep-link test | Bat crash do route extra sai/null, fallback sai | Co | Co |
| 8 | Auth/session recovery test | Restore session, refresh token, logout, 401 | Co | Co |
| 9 | Offline/cache/persistence test | Queue, cache, restart app, stale data | Co | Co |
| 10 | Notification/time-travel test | Boundary -30/0/+15/+45, cancel, reschedule | Co mot phan | Co |
| 11 | Node unit test | Service/business rules cua auth/plan/scan/drug | Co | Co |
| 12 | Node integration test | Route validation, auth, DB, idempotency | Co | Co |
| 13 | Python unit/regression test | Quality gate, OCR filter, lookup, pipeline regression | Co | Co |
| 14 | Python API alignment smoke | Bat contract lech app-path scan | Co | Co |
| 15 | Cross-layer contract test | Mobile model <-> Node <-> Python shape consistency | Co | Co |
| 16 | Manual exploratory UX/accessibility/perf | Bat loi kho lap trinh san, loi cam nhan su dung | Khong | Co |

## 5. Release Gate

### 5.1 P0 bat buoc chan release

- Boot + auth/session + redirect.
- 3 tab chinh va dieu huong co ban.
- Home empty / co lich / due / upcoming / missed / taken / skipped.
- Notification local + notification action `Da uong`.
- Offline queue + sync lai + app restart khong mat thao tac.
- 3 cach tao ke hoach: manual / scan / reuse.
- Save plan, edit plan, end plan, reactivate plan.
- History weekly grid va chi tiet trong tuan.
- Settings bat/tat reminder + permission + sync + logout.
- Responsive + keyboard + long text + state error/loading/empty.
- Cross-layer contract cho auth, plans, scan, drugs.

### 5.2 P1 quan trong nhung khong chan release neu P0 da pass va da co workaround

- Drug detail/search ranking va empty/error states nang cao.
- Direct route `/history/scan/:id`.
- Golden regression cho man hinh chinh.
- Accessibility semantically acceptable, text scale lon, touch target, contrast review.
- Performance warm-path va retry behavior.

### 5.3 P2 experimental/direct-only

- `/pill-verify`.
- `/pill-reference/enroll`.
- Backend scan session multi-image flow neu khong co entry-point UI chinh.

## 6. Inventory Man Hinh Va Route Bat Buoc

| ID | Route | Uu tien | State bat buoc | Ghi chu |
|---|---|---|---|---|
| 01 | `/boot` | P0 | Loading, redirect authenticated, redirect unauthenticated | Cold start |
| 02 | `/login` | P0 | Default, empty, wrong credentials, timeout, no connection, loading, too many requests | Auth entry |
| 03 | `/register` | P0 | Default, validate, duplicate email, loading, auto-login success, auto-login fail | Auth entry |
| 04 | `/home` empty | P0 | Empty onboarding, CTA scan, CTA manual, CTA history, quick action drug/plans | No active plan |
| 05 | `/home` with data | P0 | Loading, error, due now, upcoming, later today, no dose today, missed, taken, skipped, pending sync banner | Most critical screen |
| 06 | `/plans` | P0 | Loading, error, active empty, archived empty, mixed list, refresh | CRUD list |
| 07 | `/plans/:id` single | P0 | Loading, error, save success, validate fail, end plan dialog, reactivate, notes, date/time change | Single-drug branch |
| 08 | `/plans/:id` multi | P0 | Loading, error, summary, open edit flow, end plan, reactivate | Multi-drug branch |
| 09 | `/create` | P0 | 3 options visible, disclaimer visible, back navigation | Entry chooser |
| 10 | `/create/scan` | P0 | Camera init, ready, permission denied, unavailable, local reject, local warning, guide sheet, uploading, no drug, timeout, no connection, server reject, retry last upload | Real-device priority |
| 11 | `/create/review` | P0 | Normal list, search filter, filter empty, add, edit, remove, rescan, continue disabled when no drug | OCR review |
| 12 | `/create/edit` | P0 | Empty, populated, add, edit, delete, keyboard open, suggestion loading, suggestion select | Manual and advanced edit |
| 13 | `/create/schedule` | P0 | Default, existing-plan edit, date picker, time picker, preset 1/2/3, add slot, remove slot, no drug in slot, per-slot pills, save loading, save success, save no connection, save 401, save generic error | Most complex form |
| 14 | `/create/reuse` | P0 | Loading, empty, error, list success, refresh, choose old plan | Reuse flow |
| 15 | `/history` | P0 | Loading, empty, error, select plan, previous week, next week, weekly grid, daily details, reuse | Weekly history |
| 16 | `/drugs` | P1 | Hint, loading, results, empty, error, clear query, open detail | Lookup |
| 17 | `/drugs/detail` | P1 | Success, network error, fallback detail object | Open from search |
| 18 | `/settings` | P0 | Loading, toggle on/off, permission denied, sync success, logout, back to home | Outside bottom tabs |
| 19 | `/history/scan/:id` | P1 | Loading, error, success, recreate plan, direct route only | Direct-only test |
| 20 | `/pill-verify` | P2 | Loading, start session fail, no detections, assign, unknown/extra/uncertain, confirm success/fail | Experimental |
| 21 | `/pill-reference/enroll` | P2 | Loading, create/load set, add image, empty list, finalize success/fail | Experimental |
| 22 | Fallback route | P0 | Unknown route, safe message, no crash | Defensive route |

## 7. Ma Tran Chuc Nang Va Luong Xu Ly Bat Buoc

### 7.1 Boot, Auth, Session

- `AUTH-01` Happy: Dang ky hop le -> auto-login -> redirect `/home`.
- `AUTH-02` Happy: Dang nhap hop le -> vao `/home`.
- `AUTH-03` Happy: Cold start co token + user hop le -> restore session -> vao `/home`.
- `AUTH-04` Unhappy: Email/password rong -> snackbar validate.
- `AUTH-05` Unhappy: Wrong password -> snackbar dung thong diep.
- `AUTH-06` Unhappy: Duplicate email -> thong diep trung email.
- `AUTH-07` Unhappy: Password < 8, khong co chu hoa, khong co so, confirm mismatch -> validate dung tung truong hop.
- `AUTH-08` Unhappy: Timeout / no connection / server error / 429 tren login va register.
- `AUTH-09` Recovery: Access token het han khi dang dung app -> interceptor refresh token -> request goc thanh cong.
- `AUTH-10` Recovery: Refresh token fail -> clear storage -> redirect ve `/login`.
- `AUTH-11` Recovery: Logout khi server fail van phai clear local session.
- `AUTH-12` Defensive: Secure storage user JSON bi hong -> app tu clear va ve unauthenticated, khong crash.

### 7.2 Home, Today Dose, Priority Logic

- `HOME-01` Happy: Home empty state hien dung 3 CTA va quick actions.
- `HOME-02` Happy: Home co data hien hero summary, due section, upcoming section, later today section.
- `HOME-03` Happy: Bam `Da uong` trong due card -> snackbar success -> data refresh -> dose thanh `taken`.
- `HOME-04` Happy: Bam `Bo qua` trong due card -> snackbar -> dose thanh `skipped`.
- `HOME-05` Happy: Khi co pending offline queue -> hien banner `pending sync`.
- `HOME-06` Happy: RefreshIndicator load lai plan va today summary.
- `HOME-07` Unhappy: Khong tai duoc plans -> error view + retry.
- `HOME-08` Unhappy: Khong tai duoc today schedule -> error card + retry.
- `HOME-09` Unhappy: Mark dose fail voi loi khong phai offline/timeout -> snackbar error, khong ghi sai state.
- `HOME-10` Recovery: Mark dose khi offline -> queue local -> UI doi sang state moi -> luc co mang refresh thi sync lai.
- `HOME-11` Recovery: App mo lai khi van con queue pending -> state local van phan anh thao tac da bam.
- `HOME-12` Defensive: Cache hom truoc con ton tai -> app bo cache cu, khong hien sai lich hom nay.
- `HOME-13` Priority: `due now` phai dung tren `upcoming`.
- `HOME-14` Priority: `upcoming` phai dung tren `later today`.
- `HOME-15` Priority: `missed` khong duoc dung tren `due now` dang cho xu ly.

### 7.3 Notification, Exact Alarm, Va Moc Bien Thoi Gian

- `NOTI-01` Happy: Tao plan moi khi reminders enabled -> schedule du thong bao.
- `NOTI-02` Happy: Sua plan -> cancel notification cu, reschedule notification moi.
- `NOTI-03` Happy: End plan -> cancel het notification cua plan.
- `NOTI-04` Happy: Toggle reminder off -> cancel all notifications tren thiet bi.
- `NOTI-05` Happy: Toggle reminder on -> request permission neu can va reschedule active plans.
- `NOTI-06` Happy: Notification `due` co action `Da uong`.
- `NOTI-07` Happy: Bam `Da uong` tu notification -> mark dose, refresh state, snackbar dung mau thong diep.
- `NOTI-08` Unhappy: User tu choi notification permission -> toggle khong duoc bat gia, UI khong duoc noi da bat thanh cong neu chua co quyen.
- `NOTI-09` Unhappy: Exact alarm bi tu choi tren Android -> phai ghi nhan va xem la permission fail.
- `NOTI-10` Recovery: App launch tu notification action khi chua auth xong -> event duoc queue va xu ly sau khi auth xong.
- `NOTI-11` Defensive: Notification payload thieu `planId` hoac `occurrenceId` -> app bo qua an toan, khong crash.

| ID | Moc thoi gian | Ky vong notification | Ky vong UI/data |
|---|---|---|---|
| `TIME-01` | `T-31` | Chua co notification pre-reminder | Dose chua nam trong upcoming window |
| `TIME-02` | `T-30` | Co notification pre-reminder | Dose vao nhom `upcoming` |
| `TIME-03` | `T-29` | Khong schedule them duplicate | Van `upcoming` |
| `TIME-04` | `T+00` | Co notification due | Dose vao nhom `due now` |
| `TIME-05` | `T+14` | Chua follow-up 15 phut | Van `due now` |
| `TIME-06` | `T+15` | Follow-up lan 1 | Van `due now` neu chua xu ly |
| `TIME-07` | `T+30` | Follow-up lan 2 | Van `due now` neu chua xu ly |
| `TIME-08` | `T+44` | Chua auto-miss | Van `due now` |
| `TIME-09` | `T+45` | Follow-up lan 3 / canh bao sap quen | Bien gioi can test ro rang |
| `TIME-10` | `T+46` | Khong duoc xem la pending nua | Dose thanh `missed`, notification cua occurrence bi huy |

### 7.4 Offline Queue, Cache, Sync, Restart

- `OFF-01` Happy: Offline bam `Da uong` -> enqueue 1 log duy nhat theo `occurrenceId`.
- `OFF-02` Happy: Offline bam `Bo qua` -> enqueue 1 log duy nhat theo `occurrenceId`.
- `OFF-03` Happy: Khi mang tro lai -> `flush` thanh cong -> queue giam ve 0.
- `OFF-04` Happy: Home hien snackbar `Da dong bo X thao tac offline` sau khi sync thanh cong.
- `OFF-05` Unhappy: Offline queue flush gap loi tiep -> item con lai trong queue.
- `OFF-06` Unhappy: Queue co 3 item, sync duoc 2 item, 1 item loi -> 1 item con lai phai duoc giu dung.
- `OFF-07` Recovery: App dong/mo lai khi queue chua rong -> queue van ton tai.
- `OFF-08` Recovery: Cached schedule co san, server tam loi -> app van hien state cu hop ly.
- `OFF-09` Defensive: Queue JSON bi hong -> app xoa queue hong, khong crash.
- `OFF-10` Defensive: Cache hom qua con ton tai -> bo qua cache cu.
- `OFF-11` Defensive: Duplicate enqueue cung `occurrenceId` -> phai overwrite, khong nhan ban.

### 7.5 Scan Camera, OCR Review, Va Recovery Path

- `SCAN-01` Happy: Camera khoi dong duoc, preview hien dung.
- `SCAN-02` Happy: Chup anh tot -> upload -> sang `/create/review` voi danh sach thuoc.
- `SCAN-03` Happy: Chon anh tu gallery hop le -> upload thanh cong.
- `SCAN-04` Happy: Local quality `WARNING` -> hien bottom sheet -> `Proceed` vao upload.
- `SCAN-05` Happy: Local quality `WARNING` -> `Retake` o lai camera.
- `SCAN-06` Happy: Guide bottom sheet hien dung.
- `SCAN-07` Unhappy: Camera permission denied -> hien fallback + nut dung gallery.
- `SCAN-08` Unhappy: Camera unavailable -> hien fallback + nut dung gallery.
- `SCAN-09` Unhappy: File gallery > 10MB -> thong diep dung.
- `SCAN-10` Unhappy: Gallery read fail -> thong diep dung.
- `SCAN-11` Unhappy: Local quality `REJECT` -> khong upload, hien guidance.
- `SCAN-12` Unhappy: Server tra `drugs=[]` + `qualityState=REJECT` -> quay lai camera, hien reject guidance.
- `SCAN-13` Unhappy: Server tra `drugs=[]` nhung khong reject -> thong diep `khong tim thay thuoc`.
- `SCAN-14` Unhappy: Timeout / no connection / service unavailable -> error banner dung thong diep.
- `SCAN-15` Recovery: Sau loi upload co `retry last upload` -> bam retry thanh cong.
- `SCAN-16` Defensive: Anh khong decode duoc local -> local reject, khong crash.
- `SCAN-17` Contract: `/scan` luon tra duoc `scanId`, `drugs`, `qualityState`, `guidance`, `rejectReason?`, khong lech shape.
- `SCAN-18` Contract: Session API `/scan/session/start`, `/add-image`, `/stop` van pass o backend du khong phai primary UI path.

### 7.6 Review OCR, Manual Edit, Drug Entry Sheet

- `REVIEW-01` Happy: Search filter trong review hoat dong, khong mat du lieu.
- `REVIEW-02` Happy: Edit 1 thuoc trong review -> mappingStatus ve `confirmed`.
- `REVIEW-03` Happy: Add 1 thuoc moi trong review.
- `REVIEW-04` Happy: Remove 1 thuoc trong review.
- `REVIEW-05` Happy: Continue bi disable khi danh sach rong.
- `REVIEW-06` Unhappy: Search khong khop -> state empty filter.
- `REVIEW-07` Recovery: Bam `Quet lai` -> quay ve `/create/scan`.
- `EDIT-01` Happy: Edit drugs empty -> add first drug.
- `EDIT-02` Happy: Drug entry sheet search suggestion loading on-type, select suggestion, keyboard khong che nut.
- `EDIT-03` Happy: Add/edit/delete nhieu thuoc lien tiep.
- `EDIT-04` Unhappy: Name rong -> khong submit duoc.
- `EDIT-05` Defensive: Long drug name, long dosage, pills/day invalid -> app clamp ve gia tri hop le, khong crash.
- `EDIT-06` UX: Layout khong nhay bat thuong khi suggestion zone xuat hien/bi an.

### 7.7 Create Plan, Schedule, Va Chinh Sua Sau Khi Da Lap

- `PLAN-01` Happy: Tao plan tu manual flow.
- `PLAN-02` Happy: Tao plan tu scan review flow.
- `PLAN-03` Happy: Tao plan tu reuse flow.
- `PLAN-04` Happy: Preset `1 lan`, `2 lan`, `3 lan` dat dung khung gio mac dinh.
- `PLAN-05` Happy: Them slot thu cong.
- `PLAN-06` Happy: Xoa slot khi van con it nhat 1 slot.
- `PLAN-07` Happy: Gan tung thuoc vao tung slot.
- `PLAN-08` Happy: Chinh so vien theo tung thuoc-tung slot.
- `PLAN-09` Happy: Date picker start/end cap nhat dung `totalDays`.
- `PLAN-10` Happy: Save plan moi -> snackbar success -> ve `/home`.
- `PLAN-11` Happy: Edit plan da lap tu single-drug branch -> save thanh cong.
- `PLAN-12` Happy: Edit plan nhieu thuoc -> mo advanced edit flow, khong lam mat cau truc group.
- `PLAN-13` Happy: End plan -> snackbar success -> list cap nhat.
- `PLAN-14` Happy: Reactivate plan -> snackbar success -> active list cap nhat.
- `PLAN-15` Unhappy: Save plan mat mang -> snackbar connection error, khong fake success.
- `PLAN-16` Unhappy: Save plan bi `401` -> thong diep session het han.
- `PLAN-17` Unhappy: Save plan generic error -> thong diep generic/unknown.
- `PLAN-18` Recovery: Back navigation tu schedule phai dung theo `source=manual`, `source=scan`, `source=plan_edit`.
- `PLAN-19` Defensive: Extra cua route `/create/schedule` sai shape/null -> man van mo an toan, khong crash.
- `PLAN-20` Defensive: Remove slot dang la slot duy nhat -> khong duoc xoa ve 0 slot.

### 7.8 History Weekly Grid, Archived Plan, Va Reuse

- `HIS-01` Happy: History loading thanh cong, auto select archived plan dau tien.
- `HIS-02` Happy: Chon plan khac -> summary + grid + chi tiet cap nhat.
- `HIS-03` Happy: Move previous week / next week dung logic.
- `HIS-04` Happy: Grid hien dung `T2 -> CN` va `Sang / Trua / Chieu / Toi`.
- `HIS-05` Happy: Daily details hien `taken / skipped / missed / pending` dung.
- `HIS-06` Happy: Reuse tu history -> sang flow edit/schedule dung du lieu.
- `HIS-07` Unhappy: Khong tai duoc history -> state error + retry.
- `HIS-08` Unhappy: Khong co archived plan -> state empty.
- `HIS-09` Recovery: RefreshIndicator tai lai du lieu.
- `HIS-10` Data correctness: Plan bat dau giua tuan -> chi hien tu ngay hop le tro di.
- `HIS-11` Data correctness: Plan ket thuc giua tuan -> cac ngay sau do khong duoc ve gia.
- `HIS-12` Data correctness: Khong co log cho occurrence da qua 45 phut -> derive `missed`.
- `HIS-13` Defensive: Archived plan co start/end null hoac time format xau -> bo qua item loi, khong crash toan man.

### 7.9 Drug Search Va Drug Detail

- `DRUG-01` Happy: Query >= 2 ky tu -> loading -> results.
- `DRUG-02` Happy: Mo detail thanh cong tu item search.
- `DRUG-03` Happy: Clear query -> ve hint state.
- `DRUG-04` Unhappy: Query < 2 -> khong goi search, hien hint state.
- `DRUG-05` Unhappy: Empty result -> state empty.
- `DRUG-06` Unhappy: Loi search -> thong diep network dung loai loi.
- `DRUG-07` Unhappy: Loi detail -> snackbar error, khong crash.
- `DRUG-08` Contract: `/drugs/search` reject query ngan, reject limit > 50, va mobile hien dung thong diep.
- `DRUG-09` Contract: `/drugs/:name` shape field hop voi model mobile.

### 7.10 Settings, Permission, Sync, Logout

- `SET-01` Happy: Toggle reminders off -> luu local state + cancel all notifications.
- `SET-02` Happy: Toggle reminders on khi da co permission -> reschedule active plans.
- `SET-03` Happy: `Dong bo ngay` -> refresh plans + today schedule + snackbar success.
- `SET-04` Happy: Logout -> clear auth state, quay ve login.
- `SET-05` Unhappy: Toggle on nhung user tu choi notification permission -> UI khong duoc noi la bat thanh cong.
- `SET-06` Unhappy: Toggle on nhung user tu choi exact alarm permission -> xu ly nhu permission fail.
- `SET-07` Recovery: Sau khi grant permission lai, toggle on -> notifications duoc reschedule.
- `SET-08` Defensive: Settings load cham hoac error state tam thoi -> khong disable vo ly toan man hinh.

### 7.11 Direct Route, Fallback, Va Impossible State

- `DEF-01` Unknown route -> vao fallback screen, khong crash.
- `DEF-02` `/create/review` khong co `extra` -> render state rong an toan.
- `DEF-03` `/drugs/detail` khong co `details` -> render fallback detail an toan.
- `DEF-04` `/pill-verify` khong co `extra` -> render placeholder safe, khong crash.
- `DEF-05` `/pill-reference/enroll` khong co `extra` -> render placeholder safe, khong crash.
- `DEF-06` `/plans/:id` id khong ton tai -> hien thong diep `Khong tai duoc ke hoach`.
- `DEF-07` `/history/scan/:id` id khong ton tai -> state error, khong crash.
- `DEF-08` Notification payload loi JSON -> bo qua im lang.
- `DEF-09` Server tra field thua/field thieu nhung van du field toi thieu -> mobile van parse duoc.
- `DEF-10` Response lech contract nghiem trong -> phai bi bat boi contract test, khong de den QA thu cong moi thay.

### 7.12 Phase B Experimental / Direct-Only

- `PILL-01` Happy: Start verification session -> upload image -> assign -> confirm.
- `PILL-02` Happy: Assign detection thanh `assigned`, `uncertain`, `unknown`, `extra`.
- `PILL-03` Happy: Confirm xong -> log dose `taken` va quay ve home.
- `PILL-04` Unhappy: Start session fail -> error state.
- `PILL-05` Unhappy: Upload fail -> error state.
- `PILL-06` Unhappy: Confirm fail -> thong diep loi, khong danh dau gia da uong.
- `PILL-07` Happy: Reference enroll start/load set -> add front/back/other -> finalize.
- `PILL-08` Unhappy: Finalize khi chua co anh -> button disabled.
- `PILL-09` Direct-only: Khong dung nhom test nay de chan release Phase A neu khong co entry-point UX chinh.

### 7.13 Cross-Layer Contract Va End-to-End

- `CON-01` Auth contract: login tra `user`, `accessToken`, `refreshToken`.
- `CON-02` Refresh contract: refresh tra cap token moi va request goc retry duoc.
- `CON-03` Plans contract: `/plans` va `/plans/:id` giu duoc shape cho single-drug va multi-drug.
- `CON-04` Today summary contract: `/plans/today/summary` bat buoc co `date`, `doses`, `summary`.
- `CON-05` Log contract: `/plans/:id/log` idempotent theo `occurrenceId`.
- `CON-06` History contract: `/plans/logs/all` va archived plans du de ve weekly grid dung.
- `CON-07` Scan contract: `/scan` bat buoc giu `scanId`, `drugs`, `qualityState`, `guidance`, `rejectReason?`.
- `CON-08` Drug contract: `/drugs/search` va `/drugs/:name` khop voi parser mobile.
- `CON-09` Notification contract: payload luu `planId`, `occurrenceId`, `scheduledTime`, `kind`, `title`.
- `E2E-01` End-to-end P0: Login -> scan 1 anh -> review OCR -> schedule -> save plan -> home due/upcoming -> local notification -> `Da uong` -> history cap nhat.
- `E2E-02` End-to-end P0 offline: Login -> tao plan -> toi gio -> tat mang -> `Da uong` -> app restart -> bat mang -> sync -> history dung.
- `E2E-03` End-to-end P0 auth recovery: Session het han giua luc load home/plan/scan -> refresh token thanh cong hoac redirect ve login dung.

## 8. Responsive, UI, UX, Va Accessibility

### 8.1 Device bat buoc

- Small phone: `360x640`.
- Normal phone: `390x844` hoac `393x852`.
- Large phone: `412x915`.
- Tablet doc: `768x1024`.
- Real Android device co notification + exact alarm.

### 8.2 Font scale va content stress

- Text scale `1.0`.
- Text scale `1.3`.
- Text scale `1.5`.
- Drug name rat dai.
- Dosage rat dai.
- Nhieu item trong list / grid / chips / suggestion list.

### 8.3 UX bat buoc

- Khong overflow.
- Khong cat text quan trong.
- Keyboard khong che nut primary.
- Snackbar khong che action quan trong lau bat thuong.
- Loading state phai de hieu, khong nhap nhang voi treo app.
- Error copy phai noi du nguoi dung can lam gi tiep theo.
- Mau `due`, `upcoming`, `missed`, `taken`, `skipped` phai phan biet duoc bang nhin nhanh.
- Touch target cua nut chinh va item click phai de bam tren dien thoai that.
- Back navigation phai nhat quan, khong bi ve nham man trong flow `manual`, `scan`, `plan_edit`.
- Suggestion zone trong `DrugEntrySheet` khong duoc lam layout nhay cuc manh.

### 8.4 Man uu tien cao cho responsive

- Login.
- Register.
- Home empty.
- Home co due/upcoming/missed.
- Plans list.
- Plan detail single.
- Plan detail multi.
- Scan camera.
- OCR review.
- Edit drugs + keyboard open.
- Set schedule + date/time picker + bottom button.
- History weekly grid.
- Settings.
- Drug search results.

## 9. Contract Data Assertions Bat Buoc

Day la phan plan cu thieu nhieu nhat. Moi case P0 khong chi check UI, ma con phai assert du lieu va contract:

- `DATA-01` Sau login, secure storage phai co `access_token`, `refresh_token`, `user`.
- `DATA-02` Sau logout, 3 key tren phai bi xoa.
- `DATA-03` Sau mark dose online, server log moi phai dung `occurrenceId`, `status`, `scheduledTime`.
- `DATA-04` Sau mark dose offline, queue local phai tang dung 1 item.
- `DATA-05` Sau sync lai, queue local phai giam dung, khong de duplicate.
- `DATA-06` Sau create plan, notifications pending tren thiet bi phai tang dung theo so occurrence sap toi.
- `DATA-07` Sau end plan hoac toggle off reminders, pending notifications lien quan phai bi huy.
- `DATA-08` `/plans/today/summary` phai tuong thich voi parser `TodaySchedule` va `TodayDose`.
- `DATA-09` `/scan` phai tuong thich voi parser `ScanResult` ke ca khi backend tra `mergedDrugs` hoac `drugs`.
- `DATA-10` `/drugs/:name` phai tuong thich voi parser detail mobile.
- `DATA-11` Cac route `direct-only` khong co `extra` phai co fallback an toan, khong `type cast crash`.

## 10. Screenshot, Video, Va Bang Chung

### 10.1 Nguyen tac

- Moi screenshot phai gan voi 1 test case ID.
- Screenshot khong thay the assertion.
- Cac luong co thay doi theo thoi gian, permission, notification, va offline phai co them video ngan hoac log thoi gian neu can.

### 10.2 Dat ten file bang chung

Dung format:

`<seq>_<layer>_<flow>_<route>_<state>_<device>.png`

Vi du:

- `01_mobile_auth_login_default_phone390.png`
- `02_mobile_home_due_phone390.png`
- `03_mobile_scan_warning_realdevice.png`
- `04_mobile_history_weekgrid_tablet768.png`
- `05_os_notification_due_realdevice.png`
- `06_api_contract_scan_shape.json`

### 10.3 Bang chung bat buoc phai co anh rieng

- Boot loading.
- Login default + wrong credentials + no connection.
- Register default + validate fail.
- Home empty / due / upcoming / missed / pending sync.
- Plans list active + archived.
- Plan detail single + multi.
- Create option chooser.
- Scan camera ready + permission denied + warning/reject + uploading + error.
- OCR review normal + empty filter.
- Edit drugs empty + keyboard open.
- Set schedule default + picker + save loading + save error.
- Reuse empty + error + list.
- History empty + error + weekly grid + daily details.
- Drug search hint + results + empty + error.
- Settings default + toggle result + sync success.
- OS notification pre-reminder + due + follow-up + action `Da uong`.
- Route fallback.

## 11. Thu Tu Thuc Thi Khuyen Nghi

1. Chay automated low-cost truoc: Python unit/regression, Node unit/integration, Flutter analyze, Flutter unit/widget.
2. Chay contract test cho auth/plans/scan/drugs.
3. Chay Flutter integration voi mocked/stable backend.
4. Chay real-device P0: auth, home, scan, schedule, notification, offline queue, history, settings.
5. Chay responsive + text-scale + keyboard matrix.
6. Chay exploratory UX/performance.
7. Chay direct-only P1/P2 neu can.

## 12. Mau Bang Ghi Ket Qua

| ID | Layer | Flow | Case type | Dieu kien / buoc chinh | Expected UI | Expected data/state | Evidence | Ket qua |
|---|---|---|---|---|---|---|---|---|
| `AUTH-02` | Mobile | Login | Happy | Nhap tai khoan hop le, bam dang nhap | Redirect `/home` | Token duoc luu | Screenshot + log | Pass/Fail |
| `TIME-06` | Mobile+OS | Reminder | Boundary | Den `T+15` khi chua xu ly | Follow-up lan 1 xuat hien | Dose van `due now` | Video + screenshot | Pass/Fail |
| `OFF-07` | Mobile | Offline queue | Recovery | Offline -> bam `Da uong` -> restart app | UI van phan anh da bam | Queue van con item | Video + log queue | Pass/Fail |
| `CON-07` | Cross-layer | Scan contract | Contract | Goi `/scan` voi anh hop le | Review mo duoc | Shape khop parser mobile | JSON artifact | Pass/Fail |

## 13. Tieu Chi Hoan Tat

Chi duoc xem la hoan tat khi tat ca dieu kien sau cung dat:

- Tat ca case `P0` da co ket qua `Pass` hoac da co waiver duoc phe duyet ro rang.
- Khong con bug `Sev1` hoac `Sev2` trong auth, notification, offline queue, scan create-plan flow, history weekly grid.
- Cac test boundary thoi gian `-30/0/+15/+45` da co bang chung.
- Cac test offline/restart/sync lai da co bang chung.
- Cac test auth refresh token da co bang chung.
- Cac contract test cho auth/plans/scan/drugs da pass.
- Tat ca man hinh P0 trong muc 6 da co screenshot cho state bat buoc.
- Route `direct-only / experimental` da duoc tach bao cao rieng, khong tron vao release gate P0.

## 14. Ket luan

Ban test plan nay thay the checklist cu theo huong khat khe hon:

- Khong chi test UI co mo len hay khong.
- Khong chi test happy path.
- Khong chi chup man hinh.
- Co test flow nghiep vu, flow loi, flow hoi phuc, va flow `khong the nhung van phai chiu duoc`.
- Co test tung lop: mobile, Node, Python, va end-to-end.

Day moi la muc tieu `full test plan` dung nghia cho du an `Uong thuoc` hien tai.
