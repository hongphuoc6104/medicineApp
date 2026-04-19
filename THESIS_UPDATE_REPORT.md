# Thesis Update Report

## 1. Muc tieu dot cap nhat

Dot cap nhat nay chi tac dong den phan thesis media va cac doan mo ta sat media trong `docs/thesis_report`.

Phan ngoai scope khong bi sua.

Muc tieu da thuc hien:

- Tao file yeu cau media rieng de khoa pham vi va tieu chi dung duoc khi in.
- Tao backup/copy truoc khi sua.
- Lam moi 3 so do co rui ro lech so voi trang thai repo hien tai.
- Cap nhat `main.tex` chi o cac doan phuc vu media va giai thich media.
- Ghi nhan ro blocker cua buoc compile.

## 2. Backup va copy an toan

Da tao backup tai:

- `docs/thesis_report/backup/2026-04-19/main.tex.bak`
- `docs/thesis_report/backup/2026-04-19/main.pdf.bak`
- `docs/thesis_report/backup/2026-04-19/diagram_image_plan.md.bak`
- `docs/thesis_report/backup/2026-04-19/app_screenshot_checklist.md.bak`

Da tao ban sao de thu nghiem truoc khi ap vao file chinh:

- `docs/thesis_report/main_media_update_work.tex`

## 3. File moi da tao

### 3.1. File yeu cau / quy trinh

- `docs/thesis_report/THESIS_MEDIA_REQUIREMENTS.md`

### 3.2. Source so do moi

- `docs/thesis_report/diagrams/use_case_core_v2.mmd`
- `docs/thesis_report/diagrams/scan_flow_core_v2.mmd`
- `docs/thesis_report/diagrams/scan_flow_core_v2_portrait.mmd`
- `docs/thesis_report/diagrams/erd_main_scope_v2.mmd`
- `docs/thesis_report/diagrams/puppeteer-config.json`

### 3.3. Asset moi

- `docs/thesis_report/assets/diagrams/use_case_core_v2.svg`
- `docs/thesis_report/assets/diagrams/use_case_core_v2.png`
- `docs/thesis_report/assets/diagrams/scan_flow_core_v2.svg`
- `docs/thesis_report/assets/diagrams/scan_flow_core_v2.png`
- `docs/thesis_report/assets/diagrams/scan_flow_core_v2_portrait.svg`
- `docs/thesis_report/assets/diagrams/scan_flow_core_v2_portrait.png`
- `docs/thesis_report/assets/diagrams/erd_main_scope_v2.svg`
- `docs/thesis_report/assets/diagrams/erd_main_scope_v2.png`

## 4. File da cap nhat

- `docs/thesis_report/main.tex`

Cap nhat gom:

- doi reference cua `use_case`, `scan_flow`, `erd_main` sang asset moi
- cap nhat mo ta use case cho dung scope thesis
- cap nhat luong quet don thuoc de phan anh quality gate, table ROI va group by STT
- cap nhat bang cac buoc pipeline tu 5 muc len 8 muc
- cap nhat mo ta ERD de bao gom `scan_sessions` va `scans`

## 5. Quyết định media

| Item | Quyết định | Ghi chu |
|---|---|---|
| `input_prescription.jpg` | Giữ | Van phu hop va da duoc dung tot |
| `preprocessed.png` | Giữ | Hinh AI trung gian quan trong |
| `ocr_det.png` | Giữ | Bang chung OCR detect |
| `scan_camera.png` | Giữ | Canh bao: can test print preview vi source nho |
| `scan_review.png` | Giữ | Canh bao: can test print preview vi source nho |
| `set_schedule.png` | Giữ | Canh bao: can test print preview vi source nho |
| `home_today.png` | Giữ | Canh bao: can test print preview vi source nho |
| `architecture.png` | Giữ | Khong can lam moi |
| `sequence_scan.png` | Giữ | Khong can lam moi |
| `activity_create_plan.png` | Giữ | Khong can lam moi |
| `use_case.png` | Thay bang `use_case_core_v2.png` | Ban moi gon hon va sat narrative thesis |
| `scan_flow.png` | Thay bang `scan_flow_core_v2_portrait.png` | Ban moi phan anh quality gate, ROI va group by STT |
| `erd_main.png` | Thay bang `erd_main_scope_v2.png` | Ban moi chi giu nhom bang phuc vu thesis |
| `6_tuan_tu_lap_lich.*` | Khong dua vao main.tex | Trung y voi activity diagram dang dung |
| `7_tuan_tu_tuong_tac_thuoc.*` | Khong dua vao main.tex | Ngoai truc chinh cua thesis hien tai |
| `8_hoat_dong_dong_bo_offline.*` | Khong dua vao main.tex | Ngoai truc chinh cua thesis hien tai |

## 6. Kiem tra da thuc hien

### 6.1. Kiem tra ton tai asset moi

Da xac nhan ton tai day du:

- `use_case_core_v2.png` va `.svg`
- `scan_flow_core_v2_portrait.png` va `.svg`
- `erd_main_scope_v2.png` va `.svg`

### 6.2. Kiem tra kich thuoc asset

Ket qua:

- `use_case_core_v2.png`: `2352 x 1152`
- `scan_flow_core_v2_portrait.png`: `2181 x 5223`
- `erd_main_scope_v2.png`: `2352 x 2076`

Danh gia:

- Ca 3 asset moi dat nguong phan giai tot hon ro rang so voi cac file cu nho.
- Ban `scan_flow_core_v2_portrait.png` duoc chon thay vi ban ngang `scan_flow_core_v2.png` do phu hop hon voi cach dat full-page trong `main.tex`.

### 6.3. Kiem tra reference trong `main.tex`

Da xac nhan `main.tex` dang tro den:

- `assets/diagrams/use_case_core_v2.png`
- `assets/diagrams/scan_flow_core_v2_portrait.png`
- `assets/diagrams/erd_main_scope_v2.png`

Da xac nhan bang pipeline co them muc:

- `Kiểm tra chất lượng`
- `Table ROI (tùy chọn)`
- `Gom khối OCR theo STT`

## 7. Compile va blocker

### 7.1. Trang thai compile

Compile end-to-end chua xac nhan duoc trong moi truong hien tai.

### 7.2. Nguyen nhan

Da thu tren ban sao `main_media_update_work.tex`:

- `xelatex` khong co trong PATH
- `lualatex` co ton tai, nhung toolchain loi do thieu `luaotfload-main`

Log blocker da ghi nhan:

- `module 'luaotfload-main' not found`
- `Font ... not loadable`
- `Fatal error occurred, no output PDF file produced`

### 7.3. Danh gia tac dong

- Day la blocker cua moi truong build, khong phai blocker cua media source da tao.
- Phan cap nhat media va text lien quan da hoan tat o muc file source.
- Can mot moi truong TeX day du hon de xac nhan PDF cuoi cung bang compile that.

## 8. Muc con thieu / placeholder

### 8.1. Screenshot app

Chua chup lai screenshot phan giai cao hon vi chua co bang chung cho thay ban hien tai khong doc duoc khi in.

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
BLOCKED: TEX_TOOLCHAIN_UNAVAILABLE()
NEXT:
  - INSTALL_OR_ENABLE_XELATEX()
  - OR FIX_LUALATEX_FONTSTACK()
  - RECOMPILE_TWICE()
  - VERIFY_FIGURE_READABILITY_IN_PDF()
```

## 9. Ket luan

Dot cap nhat nay da hoan thanh phan chinh yeu theo plan:

- co backup
- co file requirement chi tiet
- co source moi cho media rui ro
- co asset moi khong ghi de asset cu
- co cap nhat `main.tex` dung pham vi media lien quan
- co bao cao tong hop blocker va phan con thieu

Phan duy nhat chua the xac nhan den cuoi la compile PDF, va ly do da duoc ghi ro la do moi truong LaTeX hien tai chua san sang.
