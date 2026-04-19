# Thesis Update Report

## 1. Muc tieu dot cap nhat

Dot cap nhat nay giai quyet dong thoi 3 nhom viec:

- cap nhat noi dung `docs/thesis_report/main.tex` cho khop voi trang thai du an hien tai
- ve lai bo so do chinh theo chuan de doc tren 1 trang A4, giam do dam va giam cam giac bi den khi in
- chinh bo cuc media trong thesis de trinh bay sach hon va dung narrative cua luong core

Ket qua: da hoan thanh cap nhat source thesis va asset media. Compile PDF cuoi cung van bi chan boi moi truong LaTeX cua may.

## 2. Backup va copy an toan

### 2.1. Backup dot truoc

- `docs/thesis_report/backup/2026-04-19/main.tex.bak`
- `docs/thesis_report/backup/2026-04-19/main.pdf.bak`
- `docs/thesis_report/backup/2026-04-19/diagram_image_plan.md.bak`
- `docs/thesis_report/backup/2026-04-19/app_screenshot_checklist.md.bak`

### 2.2. Backup dot hien tai

- `docs/thesis_report/backup/2026-04-19-pass2/main.tex.bak`
- `docs/thesis_report/backup/2026-04-19-pass2/THESIS_MEDIA_REQUIREMENTS.md.bak`
- `docs/thesis_report/backup/2026-04-19-pass2/THESIS_UPDATE_REPORT.md.bak`
- `docs/thesis_report/backup/2026-04-19-pass2/use_case_core_v2.png.bak`
- `docs/thesis_report/backup/2026-04-19-pass2/scan_flow_core_v2_portrait.png.bak`
- `docs/thesis_report/backup/2026-04-19-pass2/erd_main_scope_v2.png.bak`

### 2.3. Ban sao lam viec

- `docs/thesis_report/main_media_update_work.tex`

## 3. File moi va file da cap nhat

### 3.1. File plan / requirement

- `docs/thesis_report/THESIS_EXECUTION_PLAN.md`
- `docs/thesis_report/THESIS_MEDIA_REQUIREMENTS.md`

### 3.2. Source ve so do moi

- `docs/thesis_report/diagrams/render_thesis_diagrams.py`

### 3.3. Asset so do moi theo chuan A4

- `docs/thesis_report/assets/diagrams/architecture_a4_v3.svg`
- `docs/thesis_report/assets/diagrams/architecture_a4_v3.png`
- `docs/thesis_report/assets/diagrams/use_case_a4_v3.svg`
- `docs/thesis_report/assets/diagrams/use_case_a4_v3.png`
- `docs/thesis_report/assets/diagrams/sequence_scan_a4_v3.svg`
- `docs/thesis_report/assets/diagrams/sequence_scan_a4_v3.png`
- `docs/thesis_report/assets/diagrams/scan_flow_a4_v3.svg`
- `docs/thesis_report/assets/diagrams/scan_flow_a4_v3.png`
- `docs/thesis_report/assets/diagrams/erd_main_a4_v3.svg`
- `docs/thesis_report/assets/diagrams/erd_main_a4_v3.png`

### 3.4. File thesis da cap nhat

- `docs/thesis_report/main.tex`

## 4. Noi dung da sua trong `main.tex`

### 4.1. Cap nhat cho dung repo hien tai

- doi wording ve benchmark thanh `benchmark snapshot noi bo`
- lam ro quan he `51 anh input trong repo` va `50 anh trong benchmark tieu bieu`
- bo claim cu ve so test `55/55` va `16/16`, thay bang mo ta repo dang co test tu dong
- sua mo ta scan screen cho dung code hien tai:
  - camera mo truc tiep
  - nguoi dung chu dong bam chup
  - co local quality gate
  - manual entry / reuse nam o `CreatePlanScreen`, khong nam duoi camera screen
- sua wording `lich su quet` tren mobile thanh `lich su ke hoach va nhat ky dung thuoc`
- cap nhat bang API de phan biet:
  - route core
  - route mo rong / experimental
- sua framing ve pill verification thanh:
  - repo da co artifact thu nghiem
  - chua la luong chinh da duoc kiem chung trong thesis

### 4.2. Rut gon va lam sach narrative

- giam bot lap y quanh benchmark va test count
- giam bot wording mo ta tinh nang chua nam trong pham vi danh gia trung tam
- chinh mot so cau cho sach hon va it mo ta "planned UX" hon

### 4.3. Chinh bo cuc media

- doi reference tu bo so do cu sang bo `*_a4_v3`
- doi `scan_flow` sang dat tren trang landscape A4 de giu co chu de doc
- giu `ERD` va `sequence` tren landscape voi asset moi
- tang width hien thi cua 4 screenshot app tu `0.38\textwidth` len `0.46\textwidth`
- doi placement screenshot tu `[H]` sang `[tbp]` de layout de tho hon
- cap nhat caption `set_schedule` theo y `so vien theo tung khung gio`

## 5. Danh gia media va quyet dinh

| Item | Quyết định | Ghi chu |
|---|---|---|
| `input_prescription.jpg` | Giữ | Van phu hop, chung minh du lieu thuc |
| `preprocessed.png` | Giữ | Chung minh detect/crop/preprocess |
| `ocr_det.png` | Giữ | Chung minh OCR detect |
| `scan_camera.png` | Giữ, tang kich thuoc hien thi | Van can print preview that vi source goc nho |
| `scan_review.png` | Giữ, tang kich thuoc hien thi | Van can print preview that vi source goc nho |
| `set_schedule.png` | Giữ, tang kich thuoc hien thi | Van can print preview that vi source goc nho |
| `home_today.png` | Giữ, tang kich thuoc hien thi | Van can print preview that vi source goc nho |
| `architecture.png` | Thay bang `architecture_a4_v3.png` | Lam nhe visual va cap nhat narrative backend |
| `use_case_core_v2.png` | Thay bang `use_case_a4_v3.png` | Don gian hon, de doc hon tren A4 |
| `sequence_scan.png` | Thay bang `sequence_scan_a4_v3.png` | Bo text cu sai ve gallery va lam nhe bo cuc |
| `scan_flow_core_v2_portrait.png` | Thay bang `scan_flow_a4_v3.png` | Chuyen sang layout ngang de dung 1 trang A4 landscape |
| `erd_main_scope_v2.png` | Thay bang `erd_main_a4_v3.png` | Giam mat do, chi giu bang core |
| `activity_create_plan.png` | Giữ | Da dat readability tot, khong can ve lai |

## 6. Danh gia trinh bay so do moi

### 6.1. Tieu chi da ap dung

- nen trang hoac rat sang
- stroke nhe hon, tranh vien qua dam
- text ngan gon, uu tien 1-2 dong trong box
- bo cuc fit 1 trang A4 portrait hoac landscape
- cac so do rong duoc dua ve landscape neu can de giu co chu

### 6.2. Kich thuoc asset moi

- `architecture_a4_v3.png`: `2548 x 1664`
- `use_case_a4_v3.png`: `2548 x 1456`
- `sequence_scan_a4_v3.png`: `3068 x 1976`
- `scan_flow_a4_v3.png`: `3588 x 1872`
- `erd_main_a4_v3.png`: `3328 x 2132`

### 6.3. Danh gia A4 / print-readability

- `architecture_a4_v3`: dat cho trang portrait, mat do vua phai
- `use_case_a4_v3`: dat cho trang portrait, chi giu use case core
- `sequence_scan_a4_v3`: dat cho 1 trang A4 landscape, co chu ngan gon hon ban cu
- `scan_flow_a4_v3`: dat cho 1 trang A4 landscape, bo duoc tinh trang qua cao cua ban portrait truoc do
- `erd_main_a4_v3`: dat cho 1 trang A4 landscape, giam so bang va note ro scope

Danh gia tong quat:

- bo so do moi nhe hon ban truoc
- khong co vung den dac lon
- do dam vien va mui ten da giam
- cach to mau huong ve in de doc thay vi trang tri

## 7. Kiem tra tinh va ket qua

### 7.1. Reference trong `main.tex`

Da xac nhan `main.tex` dang tro den:

- `assets/diagrams/use_case_a4_v3.png`
- `assets/diagrams/architecture_a4_v3.png`
- `assets/diagrams/sequence_scan_a4_v3.png`
- `assets/diagrams/scan_flow_a4_v3.png`
- `assets/diagrams/erd_main_a4_v3.png`

Khong con reference cu den:

- `use_case_core_v2`
- `scan_flow_core_v2*`
- `erd_main_scope_v2`
- `architecture.png`
- `sequence_scan.png`

### 7.2. Kiem tra noi dung

Da sua cac diem lech quan trong nhat:

- benchmark wording
- test count wording
- scan screen behavior
- mobile history wording
- API table
- pill verification framing

### 7.3. Kiem tra compile

Da thu compile voi `lualatex`.

Ket qua:

- `xelatex` khong co trong PATH
- `lualatex` co ton tai nhung fail ngay tu dau vi moi truong thieu `luaotfload-main`
- `main.tex` hien van yeu cau `XeLaTeX`

Log blocker:

- `module 'luaotfload-main' not found`
- `Tài liệu này yêu cầu biên dịch bằng XeLaTeX.`
- `Fatal error occurred, no output PDF file produced`

Danh gia:

- blocker nay den tu moi truong build, khong phai do asset media vua tao
- can moi truong co `xelatex` day du de xac nhan PDF cuoi cung bang compile that

## 8. Phan con thieu / can xac nhan bang mat khi co PDF

### 8.1. Screenshot app

Da tang kich thuoc hien thi trong `main.tex`, nhung van can xac nhan print preview that do source goc chi khoang 500px be ngang.

Placeholder:

```text
IF print_preview_shows_small_text:
  TODO_CAPTURE_HIGH_RES_SCREEN()
  TODO_REPLACE_SCREENSHOT_ASSET()
ELSE:
  KEEP_CURRENT_SCREENSHOT()
```

### 8.2. Compile PDF

```text
BLOCKED: XELATEX_UNAVAILABLE()
NEXT:
  - INSTALL_OR_ENABLE_XELATEX()
  - RECOMPILE_TWICE(main.tex)
  - VERIFY_LAYOUT_ON_PDF()
  - VERIFY_PRINT_READABILITY()
```

## 9. Ket luan

Dot cap nhat nay da hoan thanh theo dung yeu cau mot lan chay:

- co plan chi tiet
- co backup moi
- co cap nhat noi dung thesis theo repo hien tai
- co ve lai bo so do chinh theo tieu chi A4
- co danh gia trinh bay / do dam / readability
- co cap nhat `main.tex` de dung asset moi va bo cuc moi
- co bao cao tong hop blocker compile

Phan chua the xac nhan den cuoi chi con buoc compile PDF bang `XeLaTeX`, vi moi truong hien tai chua co toolchain phu hop.
