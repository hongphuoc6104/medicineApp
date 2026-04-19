# Thesis Media Requirements

## 1. Muc dich

File nay khoa pham vi va tieu chi chap nhan cho tat ca hinh anh, screenshot va so do duoc chen vao `docs/thesis_report/main.tex`.

Muc tieu chinh:

- Tranh ve lai so do nhung cuoi cung khong dua vao thesis.
- Tranh chen hinh co chu qua nho, in ra khong doc duoc.
- Tranh sua cac phan khong lien quan den noi dung du an hien tai.
- Tranh ghi de asset cu khi chua validate xong.

## 2. Nguyen tac pham vi

Chi xu ly media phuc vu truc tiep cho truc chinh cua de tai:

- quet don thuoc
- ra soat ket qua AI
- lap ke hoach dung thuoc
- theo doi lich hom nay va ghi nhat ky dung thuoc

Khong mo rong sang cac he thong phu neu khong phai trong tam narrative cua thesis:

- chi tiet pill verification
- chi tiet drug interaction subsystem
- chi tiet offline sync queue
- class diagram Flutter / Node.js
- so do ky thuat qua vi mo khong duoc mo ta trong `main.tex`

## 3. Backup va copy an toan

Da tao backup text files tai:

- `docs/thesis_report/backup/2026-04-19/main.tex.bak`
- `docs/thesis_report/backup/2026-04-19/main.pdf.bak`
- `docs/thesis_report/backup/2026-04-19/diagram_image_plan.md.bak`
- `docs/thesis_report/backup/2026-04-19/app_screenshot_checklist.md.bak`

Da tao ban sao lam viec cua file chinh:

- `docs/thesis_report/main_media_update_work.tex`

Nguyen tac thuc thi:

- Khong ghi de asset cu neu item con rui ro.
- Uu tien tao asset moi voi hau to an toan, sau do moi cap nhat `main.tex`.
- Neu khong the tu tao duoc asset hop le, phai danh dau `BLOCKED` thay vi che hinh tam bo.

## 4. Cong thuc ra quyet dinh trong luc thuc thi

Moi item media phai qua du 3 gate duoi day:

1. `SCOPE_OK`
2. `PRINT_READABLE`
3. `CHAPTER_MAPPED`

Chi khi ca 3 dieu kien deu dat thi item moi duoc chen vao thesis.

Pseudo-flow:

```text
FOR each_media_item:
  IF not in_thesis_scope:
    REJECT_OUT_OF_SCOPE()
  ELSE IF not print_readable:
    REGENERATE_OR_RETAKE()
  ELSE IF not mapped_to_main_tex:
    DEFER_OR_ADD_SUPPORTING_TEXT()
  ELSE:
    READY_FOR_INSERT()
```

## 5. Tieu chi chap nhan khi in tren A4

Day la phan bat buoc nhat.

### 5.1. Tieu chi doc duoc

- Chu sau khi scale trong PDF nen dat muc doc thoai mai tuong duong `>= 9pt`.
- `Hard fail` neu du kien nho hon khoang `8pt`.
- Khong duoc dua vao hinh ma nguoi doc phai zoom PDF moi doc duoc.
- Neu diagram qua dong, phai tach hinh hoac don gian hoa noi dung, khong duoc co ep vao cung mot trang.

### 5.2. Tieu chi layout

- Moi so do chi nen phuc vu 1 y chinh.
- Khong dung mau sac la cach duy nhat de phan biet thong tin.
- Phai doc duoc ca khi in xam den trang.
- Neu landscape moi doc duoc thi phai danh dau ngay tu dau.

### 5.3. Tieu chi ky thuat

- So do line-art: uu tien `SVG` la source chinh, `PNG` chi la export.
- `PNG` full-width: muc tieu toi thieu khoang `1800px` be ngang.
- Screenshot app: uu tien cao hon `1200px` be ngang cho ban goc; bo screenshot `500px` hien tai vao nhom can kiem tra dac biet.
- Anh thuc te OCR / preprocess phai giu du net de doc duoc diem nhan thi giac chinh.

## 6. Danh sach item va quyet dinh hien tai

| Item | Dang dung trong `main.tex` | Muc do lien quan | Hanh dong | Ly do |
|---|---|---|---|---|
| `assets/real_data/input_prescription.jpg` | Co | Cao | Keep | Anh dau vao cuc ky quan trong cho bai toan |
| `assets/real_data/preprocessed.png` | Co | Cao | Keep | Chung minh buoc crop + preprocess |
| `assets/real_data/ocr_det.png` | Co | Cao | Keep | Chung minh OCR detect |
| `assets/app/scan_camera.png` | Co | Cao | Keep with print check | Dung scope, nhung do phan giai nho can kiem tra khi in |
| `assets/app/scan_review.png` | Co | Cao | Keep with print check | Hinh quan trong ve buoc ra soat an toan |
| `assets/app/set_schedule.png` | Co | Cao | Keep with print check | Hinh dau ra chinh cua luong lap lich |
| `assets/app/home_today.png` | Co | Cao | Keep with print check | Hinh vong kin theo doi trong ngay |
| `assets/diagrams/architecture_a4_v3.png` | Co | Cao | Regenerate | Ve lai nhe hon, fit A4 hon va cap nhat narrative hien tai |
| `assets/diagrams/sequence_scan_a4_v3.png` | Co | Cao | Regenerate | Ve lai de bo text sai ve gallery va giam do dam khi in |
| `assets/diagrams/activity_create_plan.png` | Co | Cao | Keep | So do cho luong lap ke hoach ro rang |
| `assets/diagrams/use_case_a4_v3.png` | Co | Trung binh | Regenerate | Can lam gon lai de chi giu flow chinh va de doc tren A4 |
| `assets/diagrams/scan_flow_a4_v3.png` | Co | Cao | Regenerate | Ve lai theo layout ngang de de doc tren 1 trang A4 landscape |
| `assets/diagrams/erd_main_a4_v3.png` | Co | Cao | Regenerate | Ve lai de thu hep dung group bang thesis va giam mat do |
| `diagrams/6_tuan_tu_lap_lich.*` | Khong | Trung binh | Omit | Trung y voi activity diagram dang dung |
| `diagrams/7_tuan_tu_tuong_tac_thuoc.*` | Khong | Thap doi voi thesis | Omit | Ngoai truc chinh cua thesis hien tai |
| `diagrams/8_hoat_dong_dong_bo_offline.*` | Khong | Thap doi voi thesis | Omit | Ngoai truc chinh va de lam phinh narrative |

## 7. Mapping chuong -> media

### 7.1. Nhom bat buoc

| Chuong | Media | Vai tro |
|---|---|---|
| Chuong 2 | `input_prescription.jpg` | Dat van de bang du lieu thuc |
| Chuong 3 | `architecture.*` | Kien truc tong the |
| Chuong 3 | `use_case.*` | Minh hoa chuc nang he thong o muc cao |
| Chuong 3 | `sequence_scan.*` | Dong du lieu giua app, Node.js, AI |
| Chuong 3 | `scan_flow.*` | Hoat dong ben trong pipeline nhan dien |
| Chuong 3 | `erd_main.*` | Cau truc du lieu cho luong ke hoach va quet |
| Chuong 3 | `activity_create_plan.*` | Thao tac tao ke hoach |
| Chuong 4 | `preprocessed.png` | Bang chung cai dat AI |
| Chuong 4 | `scan_camera.png` | Giao dien quet |
| Chuong 4 | `scan_review.png` | Giao dien ra soat |
| Chuong 4 | `set_schedule.png` | Giao dien lap lich |
| Chuong 4 | `home_today.png` | Giao dien theo doi trong ngay |
| Chuong 5 | `ocr_det.png` | Bang chung ket qua OCR |

### 7.2. Nhom chi them neu co bang chung va co cho

| Media | Trang thai mac dinh | Ghi chu |
|---|---|---|
| So do tong quan bai toan | Defer | Chi them neu can mo chuong 1 bang mot overview ro rang |
| Hinh gioi han pill verification | Blocked | Chi duoc them o Chuong 5 voi framing la limitation, khong phai feature chinh |

## 8. Rule rieng cho screenshot app

- Khong chap nhan screenshot co text nho den muc nut chinh khong doc duoc khi in.
- Neu man hinh qua dai va chu nho, uu tien:
  - chup lai do phan giai cao hon
  - hoac tach crop vao khu vuc can nhan manh
- Khong de du lieu nhay cam xuat hien.
- Khong chen screenshot chi de trang tri.

Pseudo-check:

```text
IF screenshot_width <= 500px:
  REQUIRE_PRINT_PREVIEW()
  IF key_labels_not_readable:
    TODO_CAPTURE_HIGH_RES_SCREEN()
```

## 9. Rule rieng cho so do

- So do use case phai don gian, chi giu actor va use case phuc vu luong chinh.
- So do scan flow phai phan anh dung muc sau:
  - detect / crop
  - preprocess
  - OCR
  - trich xuat ten thuoc
  - doi sanh co so du lieu
  - tra ket qua cho man hinh ra soat
- So do ERD thesis phai uu tien nhom bang:
  - `users`
  - `scans`
  - `scan_sessions`
  - `prescription_plans`
  - `prescription_plan_drugs`
  - `prescription_plan_slots`
  - `prescription_plan_slot_drugs`
  - `prescription_plan_logs`
- Khong dua toan bo bang interaction hoac pill verification vao ERD chinh cua thesis.

## 10. Mau item chi tiet

```md
## ITEM: <id>
STATUS: <KEEP | REGENERATE | DEFER | BLOCKED | REJECTED>
PRIORITY: <MUST | SHOULD | NICE>
TYPE: <diagram | screenshot | photo | annotated-output>
CHAPTER_REF: <chuong / muc trong main.tex>
LATEX_REF: <figure label>
CURRENT_ASSET: <path or NONE>
EDITABLE_SOURCE: <path or NONE>
INTENDED_PLACEMENT: <full-width | half-width | landscape>
PURPOSE: <ly do ton tai>

REQUIREMENTS:
- ...
- ...

ACCEPTANCE_CHECK:
- [ ] Scope OK
- [ ] Print readable
- [ ] Source tracked
- [ ] Mapped to main.tex
- [ ] Caption khop y nghia

DECISION_IF_FAIL:
- <split / retake / export SVG / omit / block>
```

## 11. Placeholder cho phan chua tu lam duoc

Chi duoc dung placeholder o muc requirement / report, khong chen vao thesis chinh.

### 11.1. Placeholder block

```md
## ITEM: <id>
STATUS: BLOCKED
BLOCKER: <ly do>
ACTION_NEXT:
  - TODO_SOURCE_CONFIRM()
  - TODO_EXPORT_SVG()
  - TODO_VERIFY_WITH_PRINT_PREVIEW()
  - TODO_CAPTURE_HIGH_RES_SCREEN()

PLACEHOLDER_NOTE:
  BLOCKED_NO_SOURCE_FILE()
  NOT_READY_FOR_MAIN_TEX()
```

### 11.2. Marker cho cac truong hop thieu

- `TODO_CAPTURE_HIGH_RES_SCREEN()`
- `TODO_EXPORT_SVG()`
- `TODO_SPLIT_OVERCROWDED_DIAGRAM()`
- `TODO_VERIFY_WITH_PRINT_PREVIEW()`
- `BLOCKED_NO_SOURCE_FILE()`
- `REJECT_OUT_OF_SCOPE()`

## 12. Checklist chot truoc khi chen vao `main.tex`

- [ ] Item nam trong scope thesis
- [ ] Item da duoc map vao chuong phu hop
- [ ] Chu, nut, actor, bang chinh doc duoc khi in
- [ ] Khong co noi dung nhay cam
- [ ] Da xac dinh source editable cua item
- [ ] Neu la diagram thi co source uu tien `SVG` hoac file text goc
- [ ] Neu la screenshot nho thi da test print preview
- [ ] Item khong lap y voi hinh khac qua muc can thiet

## 13. Ket luan van hanh

Trong dot cap nhat nay, item nao khong qua duoc bo ba gate:

- `SCOPE_OK`
- `PRINT_READABLE`
- `CHAPTER_MAPPED`

thi phai bi `DEFER`, `BLOCKED` hoac `REJECTED`, khong duoc dua vao `main.tex` chi de co them hinh.
