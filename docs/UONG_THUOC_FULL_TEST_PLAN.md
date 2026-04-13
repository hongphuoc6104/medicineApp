# Uong Thuoc Full Test Plan

## 1. Muc tieu

Tai lieu nay tong hop day du tat ca chuc nang va tat ca giao dien can test cho app `Uong thuoc`.

Muc tieu:

- Dam bao app dung theo yeu cau nghiep vu da cap nhat.
- Dam bao tat ca man hinh quan trong deu duoc test va chup anh.
- Dam bao app khong vo giao dien tren cac kich thuoc man hinh pho bien.
- Dam bao co bang chung screenshot cho tung man hinh va tung state quan trong.

## 2. Pham vi yeu cau can xac nhan

### 2.1 Yeu cau moi

- Doi ten app thanh `Uong thuoc`.
- Trong `Ke hoach` co the chinh sua thuoc sau khi ke hoach da lap.
- App phai responsive, khong vo bat ky giao dien nao o cac kich thuoc man hinh thong dung.

### 2.2 Yeu cau cu van phai dat

- App co 3 tab chinh:
  - `Trang chu`
  - `Ke hoach`
  - `Lich su`
- `Trang chu` hien nhac thuoc va huong tao lich neu chua co ke hoach.
- Neu da co lich hom nay thi home phai hien dung cac lan can uong.
- Logic nhac nho:
  - Nhac truoc 30 phut.
  - Nhac dung gio.
  - Neu chua uong thi nhac them 3 lan, moi lan cach 15 phut.
  - Sau 45 phut khong co thao tac thi chuyen `da quen`.
  - Khi gan toi lan tiep theo thi uu tien lan tiep theo len dau home.
- Thong bao phai la local notification va dong bo backend khi co mang neu co the.
- Thong bao phai hien tren man hinh dien thoai va co nut `Da uong`.
- Co 3 cach lap lich:
  - Nhap thu cong.
  - Chup hinh don thuoc, moi lan 1 tam.
  - Dung lai lich su ke hoach cu.
- Tab thu 3 la `Lich su` cua ke hoach cu, co bieu do tuan theo `Thu 2 -> CN` va `Sang / Trua / Chieu / Toi` de the hien lan da uong va lan bi miss.

## 3. Nguyen tac chup anh

Tat ca giao dien duoi day deu phai chup anh lai.

Quy dinh toi thieu:

- Moi man hinh chinh: chup it nhat 1 anh full screen.
- Moi state quan trong cua tung man: chup rieng.
- Moi popup/dialog/bottom sheet/picker: chup rieng.
- Moi man hinh co form: chup ca luc keyboard dong va keyboard mo neu co anh huong layout.
- Moi notification he thong can chup rieng.

## 4. Tat ca chuc nang can test

1. Mo app lan dau.
2. Hien thi ten app `Uong thuoc`.
3. Boot/loading ban dau.
4. Dang ky tai khoan.
5. Dang nhap.
6. Dang xuat.
7. Dieu huong 3 tab chinh.
8. Home khi chua co ke hoach.
9. Home khi da co ke hoach hom nay.
10. Uu tien lieu `den gio` va `sap toi`.
11. Chuyen `da quen` sau 45 phut.
12. Bam `Da uong` trong app.
13. Bam `Bo qua` trong app.
14. Local notification nhac truoc 30 phut.
15. Local notification dung gio.
16. Ba lan nhac lai moi 15 phut.
17. Notification co nut `Da uong`.
18. Bam `Da uong` tu notification.
19. Offline queue khi mat mang.
20. Dong bo backend lai khi co mang.
21. Tao ke hoach tu man chon cach tao.
22. Tao ke hoach bang nhap thu cong.
23. Tao ke hoach bang chup don 1 anh/lan.
24. Review ket qua OCR sau khi scan.
25. Tao ke hoach bang dung lai ke hoach cu.
26. Chinh them/bot thuoc truoc khi lap lich.
27. Thiet lap ngay bat dau, so ngay, gio uong, so vien.
28. Luu ke hoach moi.
29. Danh sach ke hoach dang chay.
30. Danh sach ke hoach cu.
31. Xem chi tiet ke hoach.
32. Sua ke hoach sau khi da lap.
33. Sua danh sach thuoc sau khi da lap.
34. Ket thuc ke hoach.
35. Kich hoat lai ke hoach.
36. Lich su ke hoach cu.
37. Bieu do tuan `T2-CN`.
38. Chia khung `Sang / Trua / Chieu / Toi`.
39. Hien thi trang thai `da uong / miss / bo qua / cho`.
40. Dung lai tu ke hoach cu trong lich su.
41. Tra cuu thuoc.
42. Xem chi tiet thuoc.
43. Cai dat bat/tat nhac thuoc.
44. Cap quyen notification/exact alarm.
45. Dong bo du lieu thu cong tu cai dat.
46. Cac man loi/loading/empty.
47. Responsive tren nhieu kich thuoc man hinh.
48. Keyboard khong che form hay nut chinh.
49. Dialog, bottom sheet, picker, permission popup.
50. Route loi/fallback co ban.

## 5. Tat ca giao dien can test va can chup anh

| ID | Giao dien | Route | State can test | Anh bat buoc |
|---|---|---|---|---|
| 01 | Boot screen | `/boot` | Loading | 1 anh loading |
| 02 | Login | `/login` | Mac dinh, loi trong/sai, loading | 3 anh |
| 03 | Register | `/register` | Mac dinh, loi validate, loading | 3 anh |
| 04 | Home empty | `/home` | Chua co ke hoach | 1 anh |
| 05 | Home today success | `/home` | Co lich hom nay | 1 anh |
| 06 | Home due dose | `/home` | Co lieu den gio + nut `Da uong` | 1 anh |
| 07 | Home upcoming dose | `/home` | Co lieu sap toi | 1 anh |
| 08 | Home missed dose | `/home` | Lieu qua 45 phut thanh `da quen` | 1 anh |
| 09 | Home error/retry | `/home` | Loi tai du lieu | 1 anh |
| 10 | Ke hoach list | `/plans` | Co ke hoach dang chay va cu | 1 anh |
| 11 | Ke hoach list empty | `/plans` | Khong co du lieu | 1 anh |
| 12 | Chi tiet ke hoach 1 thuoc | `/plans/:id` | Form chinh sua | 1 anh |
| 13 | Chi tiet ke hoach nhieu thuoc | `/plans/:id` | Summary nhieu thuoc | 1 anh |
| 14 | Chi tiet ke hoach nut sua | `/plans/:id` | Co `Chinh sua thuoc va lich` | 1 anh |
| 15 | Dialog ket thuc ke hoach | `/plans/:id` | Confirm dialog | 1 anh |
| 16 | Lich su | `/history` | Danh sach ke hoach cu | 1 anh |
| 17 | Lich su empty | `/history` | Chua co ke hoach cu | 1 anh |
| 18 | Lich su error | `/history` | Loi tai du lieu | 1 anh |
| 19 | Bieu do tuan | `/history` | Grid `T2-CN x Sang/Trua/Chieu/Toi` | 1 anh |
| 20 | Chi tiet trong tuan | `/history` | List lieu theo ngay | 1 anh |
| 21 | Tao ke hoach | `/create` | 3 lua chon tao ke hoach | 1 anh |
| 22 | Dung lai ke hoach cu | `/create/reuse` | List ke hoach cu | 1 anh |
| 23 | Dung lai empty | `/create/reuse` | Khong co ke hoach cu | 1 anh |
| 24 | Dung lai error | `/create/reuse` | Loi tai du lieu | 1 anh |
| 25 | Chup don thuoc | `/create/scan` | Preview camera | 1 anh |
| 26 | Chup don loi quyen | `/create/scan` | Camera denied/unavailable | 1 anh |
| 27 | Chup don banner chat luong | `/create/scan` | Reject/warning | 1 anh |
| 28 | Chup don help sheet | `/create/scan` | Bottom sheet huong dan | 1 anh |
| 29 | Review OCR | `/create/review` | Co thuoc nhan dien | 1 anh |
| 30 | Review OCR empty | `/create/review` | Khong co thuoc | 1 anh |
| 31 | Nhap/sua danh sach thuoc | `/create/edit` | List thuoc | 1 anh |
| 32 | Nhap/sua thuoc empty | `/create/edit` | Chua co thuoc | 1 anh |
| 33 | Bottom sheet them/sua thuoc | Bottom sheet | Add/edit thuoc | 1 anh |
| 34 | Thiet lap lich | `/create/schedule` | State mac dinh | 1 anh |
| 35 | Thiet lap lich save/loading | `/create/schedule` | Dang luu | 1 anh |
| 36 | Thiet lap lich picker ngay | Date picker | Chon ngay | 1 anh |
| 37 | Thiet lap lich picker gio | Time picker | Chon gio | 1 anh |
| 38 | Tra cuu thuoc | `/drugs` | Mac dinh/loading/results/empty | 4 anh |
| 39 | Chi tiet thuoc | `/drugs/detail` | Detail thanh cong | 1 anh |
| 40 | Cai dat | `/settings` | State binh thuong | 1 anh |
| 41 | Cai dat sau bat/tat reminder | `/settings` | Toggle thay doi | 1 anh |
| 42 | Cai dat sync/logout | `/settings` | Snack/success state | 1 anh |
| 43 | Lich su scan detail | `/history/scan/:id` | Detail scan | 1 anh |
| 44 | Pill verification | `/pill-verify` | Main state | 1 anh |
| 45 | Pill verification empty/error | `/pill-verify` | Khong co anh/detection | 1 anh |
| 46 | Pill reference enroll | `/pill-reference/enroll` | List anh / save | 1 anh |
| 47 | Route fallback | Fallback | Route loi | 1 anh |

## 6. Giao dien he dieu hanh cung phai chup

1. Popup xin quyen notification.
2. Popup xin quyen camera.
3. Exact alarm permission neu Android yeu cau.
4. Notification local truoc 30 phut.
5. Notification local dung gio.
6. Notification local nhac lai 15 phut.
7. Notification co nut `Da uong`.
8. Date picker he thong.
9. Time picker he thong.
10. Gallery picker neu dung upload anh thay camera.

## 7. Chuc nang gan voi tung giao dien can tick Pass/Fail

### 7.1 Login

- Email dung.
- Email sai.
- Password dung.
- Password sai.
- Khong nhap gi.
- Loading.
- Redirect thanh cong.

### 7.2 Register

- Validate email.
- Validate password.
- Trung email.
- Auto-login sau dang ky.

### 7.3 Home

- Empty state.
- Today summary.
- Due dose.
- Upcoming dose.
- Missed dose.
- Thu tu uu tien dung.
- Bam `Da uong`.
- Bam `Bo qua`.

### 7.4 Notification

- Nhac truoc 30 phut.
- Nhac dung gio.
- Nhac lai 3 lan moi 15 phut.
- Co nut `Da uong`.
- Bam `Da uong` tu notification.
- Dong bo backend.
- Hoat dong khi offline va sync lai.

### 7.5 Create plan

- Tao tu manual.
- Tao tu scan.
- Tao tu reuse.
- Them thuoc.
- Sua thuoc.
- Xoa thuoc.
- Set gio.
- Set ngay.
- Set so vien.

### 7.6 Plan detail

- Xem chi tiet.
- Sua metadata.
- Sua thuoc sau khi da lap.
- Ket thuc ke hoach.
- Kich hoat lai ke hoach.

### 7.7 History

- Danh sach ke hoach cu.
- Chon ke hoach.
- Xem grid tuan.
- Xem chi tiet theo ngay.
- Reuse tu lich su.

### 7.8 Drug

- Search.
- Empty result.
- Chi tiet thuoc.

### 7.9 Settings

- Toggle reminder.
- Sync du lieu.
- Logout.

### 7.10 Responsive

- Khong overflow.
- Khong cat text.
- Khong lech tab/nav.
- Keyboard khong che form.
- Khong co khoang trang ky quac.

## 8. Tap state bat buoc phai chup doi voi man hinh quan trong

Tat ca man hinh chinh nen duoc chup cac state sau neu co:

- Loading
- Empty
- Error
- Success
- Dialog
- Bottom sheet
- Picker
- Notification
- Keyboard mo

## 9. Test responsive bat buoc

### 9.1 Kich thuoc toi thieu can test

1. Small phone: `360x640`.
2. Normal phone: `390x844` hoac `393x852`.
3. Large phone: `412x915`.
4. Tablet doc: `768x1024`.

### 9.2 Trang thai responsive can test

1. Keyboard dong.
2. Keyboard mo.
3. Danh sach dai.
4. Grid lich su tuan.
5. Form dai.
6. Man co bottom sheet.

### 9.3 Man hinh uu tien test responsive o 3 size

1. Login.
2. Register.
3. Home empty.
4. Home co lich.
5. Plan list.
6. Plan detail.
7. Edit drugs.
8. Set schedule.
9. History list.
10. History weekly grid.
11. Settings.
12. Drug search.

## 10. Thu tu uu tien test

### 10.1 P1 bat buoc

- Login.
- 3 tab chinh.
- Home.
- Notification.
- 3 cach lap lich.
- Sua ke hoach sau khi lap.
- History weekly grid.
- Responsive.

### 10.2 P2 quan trong

- Drug search/detail.
- Settings.
- Reuse flow.
- Empty/error states.

### 10.3 P3 phu

- Pill verification.
- Pill reference enrollment.
- Fallback route.
- Scan history detail.

## 11. Quy uoc dat ten anh chup

1. `01_boot_loading.png`
2. `02_login_default.png`
3. `03_login_error.png`
4. `04_register_default.png`
5. `05_home_empty.png`
6. `06_home_due.png`
7. `07_home_upcoming.png`
8. `08_home_missed.png`
9. `09_plans_list.png`
10. `10_plan_detail_single.png`
11. `11_plan_detail_multi.png`
12. `12_plan_edit_drugs.png`
13. `13_history_list.png`
14. `14_history_week_grid.png`
15. `15_create_plan_options.png`
16. `16_create_manual_edit_drugs.png`
17. `17_create_schedule.png`
18. `18_reuse_old_plan.png`
19. `19_scan_camera.png`
20. `20_scan_review.png`
21. `21_drug_search_results.png`
22. `22_drug_detail.png`
23. `23_settings.png`
24. `24_notification_due.png`

## 12. Mau bang ghi ket qua test

| ID | Hang muc | Man hinh | State | Ket qua | Ghi chu | File anh |
|---|---|---|---|---|---|---|
| 01 | Login | `/login` | Default | Pass/Fail |  | `02_login_default.png` |
| 02 | Login | `/login` | Error | Pass/Fail |  | `03_login_error.png` |
| 03 | Home | `/home` | Due dose | Pass/Fail |  | `06_home_due.png` |
| 04 | History | `/history` | Weekly grid | Pass/Fail |  | `14_history_week_grid.png` |

## 13. Ghi chu thuc thi

- Tat ca giao dien phai co screenshot bang chung.
- Khong duoc bo qua state `empty`, `error`, `loading` neu man co ho tro.
- Notification va popup he thong phai chup truc tiep tren thiet bi.
- Responsive phai kiem tra tren nhieu size, khong chi tren 1 may.
- Neu 1 chuc nang qua nhieu buoc, can chup tung buoc chinh.

## 14. Ket luan

Tai lieu nay la checklist tong hop de test toan bo app `Uong thuoc` theo yeu cau nghiep vu da cap nhat.

Chi duoc xem la hoan tat khi:

- Tat ca chuc nang trong muc 4 da co ket qua test.
- Tat ca giao dien trong muc 5 va 6 da co screenshot.
- Responsive trong muc 9 da duoc xac nhan.
- Bang ket qua test trong muc 12 da duoc dien day du.
