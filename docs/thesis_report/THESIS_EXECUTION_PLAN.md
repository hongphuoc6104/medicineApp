# Thesis Execution Plan

## 1. Muc tieu dot cap nhat

Dot cap nhat nay giai quyet dong thoi 4 nhom viec:

- cap nhat noi dung `main.tex` cho khop voi trang thai du an hien tai
- loai bo hoac rut gon cac doan mo ta sai, cu, lap y hoac khong con la narrative chinh
- ve lai / dieu chinh cac so do de doc duoc tren 1 trang A4 va doc duoc khi in
- danh gia lai trinh bay thesis theo huong it den, it dam, sach va de theo doi

## 2. Pham vi chinh

Chi sua cac phan lien quan den thesis:

- `docs/thesis_report/main.tex`
- media trong `docs/thesis_report/assets/diagrams/`
- source so do trong `docs/thesis_report/diagrams/`
- file yeu cau / bao cao markdown lien quan thesis

Khong mo rong sang sua code app/backend neu khong can cho tinh chinh xac cua bao cao.

## 3. Dau vao de doi chieu

Nguon su that uu tien:

1. `AGENTS.md`
2. `server-node/src/app.js`
3. `server-node/src/routes/*.js`
4. `server-node/src/config/migrate.js`
5. `mobile/lib/core/router/app_router.dart`
6. cac man hinh mobile dang duoc route den thuc te

## 4. Tieu chi noi dung

### 4.1. Giu

- cac doan mo ta dung luong core da duoc xac nhan: scan -> review -> schedule -> today tracking
- cac so do giai thich truc chinh cua thesis
- cac hinh minh hoa AI va app co gia tri hoc thuat ro rang

### 4.2. Cap nhat

- mo ta scan screen cho khop voi code hien tai
- wording ve history tren mobile
- wording ve pill verification: co artifact nhung khong phai validated core flow
- bang API de phan biet route chinh va route phu / experimental
- cac doan mo ta benchmark / test count neu la so cu

### 4.3. Loai bo hoac rut gon

- cac doan lap lai y “AI chi ho tro” qua nhieu lan
- cac doan lap lai kien truc 3 lop
- cac doan lap lai pipeline AI giua Ch.2, Ch.3, Ch.4, Ch.6
- cac doan mo ta planned UX nhung code hien tai chua co

## 5. Tieu chi media va so do

### 5.1. Tieu chi A4

- moi so do phai fit trong 1 trang A4 o che do portrait hoac landscape hop ly
- chu khi in phai doc duoc ma khong can zoom PDF
- khong nhung qua nhieu node vao mot so do den muc phai giam chu qua nho
- neu mot so do khong dat, uu tien tach thanh overview + detail hoac don gian hoa noi dung

### 5.2. Tieu chi visual

- nen trang hoac rat sang
- duong vien va mui ten khong qua dam
- han che den dac, xam dac, hoac do dam tao cam giac “bi den” khi in
- font dong deu, net vua phai, icon / mau chi o muc phu tro
- uu tien palette sang va trung tinh:
  - xanh nhat / xam xanh nhat / vang nhat / do nhat chi de canh bao

### 5.3. Tieu chi readability

- heading box phai ngan gon
- label trong node khong qua 2-3 dong
- khong dung paragraph dai trong so do
- neu so do line-art co ban SVG thi uu tien SVG la source
- PNG export phai du lon de in dep

## 6. Danh sach so do can xu ly

### 6.1. Bat buoc danh gia lai

- `use_case_core_v2`
- `scan_flow_core_v2_portrait`
- `erd_main_scope_v2`
- `architecture`
- `sequence_scan`
- `activity_create_plan`

### 6.2. Hanh dong du kien

- `use_case_core_v2`: kiem tra lai mat do actor/use case, giam do dam, dam bao fit A4 ngang
- `scan_flow_core_v2_portrait`: danh gia lai chieu cao va muc do dat chu; neu qua dai se ve lai theo layout A4 portrait can bang hon
- `erd_main_scope_v2`: ve lai theo huong nhe hon, boi mau nhat hon, nhan manh nhom bang core
- `architecture`, `sequence_scan`, `activity_create_plan`: giu neu dat tieu chi A4; neu qua dam thi export lai nhe hon

## 7. Trinh tu thuc thi 1 lan chay

1. Tao backup
2. Audit nhanh `main.tex` va danh dau cac claim sai / cu / lap y
3. Chot cac phan xoa bot truoc de giam do dai tai lieu
4. Danh gia kich thuoc va bo cuc so do hien tai
5. Ve lai / export lai so do uu tien theo tieu chi A4
6. Cap nhat `main.tex` de dung media moi va noi dung moi
7. Kiem tra tinh ton tai cua asset, line references, do phu hop bo cuc
8. Neu compile duoc thi compile; neu khong compile duoc thi ghi ro blocker moi truong
9. Cap nhat bao cao tong ket goc du an

## 8. Tieu chi chap nhan cua dot cap nhat

- `main.tex` khong con mo ta sai cac luong core cua du an
- cac so do chinh co bo cuc phu hop A4 va de doc khi in
- khong dua cac tinh nang ngoai scope vao narrative chinh mot cach nham lan
- co bao cao tong ket nêu ro da giu, da sua, da xoa bot, da ve lai gi

## 9. Cac diem can ghi ro trong bao cao cuoi

- benchmark / test counts nao da xac minh lai duoc
- benchmark / test counts nao chua xac minh duoc va da doi wording
- so do nao giu nguyen
- so do nao da ve lai
- phan nao da xoa bot de tranh lap hoac sai narrative
- blocker compile neu moi truong LaTeX van chua san sang
