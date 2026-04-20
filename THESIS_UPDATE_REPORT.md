# Thesis Update Report

## 1. Ket qua hien tai

Dot cap nhat nay da duoc thuc thi den muc co the nop va doc duoc:

- da khoi phuc day du asset thesis can thiet
- da cap nhat `docs/thesis_report/main.tex`
- da ve lai / render lai bo so do chinh
- da them va annotate bo screenshot giao dien theo pattern bai mau
- da build thanh cong `docs/thesis_report/main.pdf`

PDF hien tai duoc xuat thanh cong bang `pdfLaTeX` fallback va co `59` trang.

## 2. Chuan tham khao da bam theo

Dot nay lay bai mau trong:

- `docs/mẫu bài luận/BÁO_CÁO_LUẬN_VĂN___Niên_luận__Copy_/bao_cao/Luan_van/Luan_van_thac_si.tex`

Lam chuan trinh bay chinh.

Tinh than da ap dung tu bai mau:

- bia co khung
- front matter ro rang
- danh muc hinh anh / bang bieu rieng
- so do theo phong cach thesis don sac
- screenshot UI theo mau `hinh + bang thanh phan`

## 3. Asset da khoi phuc va tao moi

### 3.1. Asset AI / du lieu thuc

- `docs/thesis_report/assets/real_data/input_prescription.jpg`
- `docs/thesis_report/assets/real_data/preprocessed.png`
- `docs/thesis_report/assets/real_data/ocr_det.png`

### 3.2. So do final

- `docs/thesis_report/assets/diagrams/use_case_a4_v3.png`
- `docs/thesis_report/assets/diagrams/architecture_a4_v3.png`
- `docs/thesis_report/assets/diagrams/sequence_scan_a4_v3.png`
- `docs/thesis_report/assets/diagrams/scan_flow_a4_v3.png`
- `docs/thesis_report/assets/diagrams/erd_main_a4_v3.png`
- `docs/thesis_report/assets/diagrams/activity_create_plan.png`

SVG source cung da duoc render song song trong cung thu muc.

### 3.3. Screenshot giao dien final

Asset PNG chuan hoa:

- `docs/thesis_report/assets/app/scan_camera.png`
- `docs/thesis_report/assets/app/scan_review.png`
- `docs/thesis_report/assets/app/set_schedule.png`
- `docs/thesis_report/assets/app/home_today.png`
- `docs/thesis_report/assets/app/history_week_chart.png`

Asset annotate theo pattern bai mau:

- `docs/thesis_report/assets/app/scan_camera_annotated.png`
- `docs/thesis_report/assets/app/scan_review_annotated.png`
- `docs/thesis_report/assets/app/set_schedule_annotated.png`
- `docs/thesis_report/assets/app/home_today_annotated.png`
- `docs/thesis_report/assets/app/history_week_annotated.png`

### 3.4. Script phuc vu tai tao asset

- `docs/thesis_report/diagrams/render_thesis_diagrams.py`
- `docs/thesis_report/image/prepare_app_screenshots.py`
- `docs/thesis_report/image/annotate_app_screenshots.py`

## 4. Noi dung da cap nhat trong `main.tex`

### 4.1. Front matter va bìa

- them khung bia theo huong bai mau
- them logo CTU o hai trang bia
- bo sung dong tieu de tieng Anh tren bia
- doi ten:
  - `DANH MỤC HÌNH ẢNH`
  - `DANH MỤC BẢNG BIỂU`
- sap xep front matter theo huong gan bai mau hon:
  - loi cam doan
  - loi cam on
  - muc luc
  - danh muc hinh
  - danh muc bang
  - danh muc tu viet tat
  - abstract
  - tom tat

### 4.2. Noi dung hoc thuat

- tiep tuc giu scope chi cho luong core thuc te:
  - quet don
  - ra soat ket qua
  - lap lich dung thuoc
  - theo doi trong ngay
- giu history nhu man hinh ho tro
- khong day pill verification vao narrative trung tam
- giam lap y va wording qua implementation-heavy

### 4.3. Pattern `hinh + bang thanh phan`

Da ap dung cho 5 man hinh:

- scan camera
- scan review
- set schedule
- home today
- history week

Moi man hinh deu co:

- hinh annotate
- bang thanh phan ben duoi

## 5. Danh gia trinh bay

### 5.1. So do

So do da duoc chuyen theo huong thesis-like hon:

- giam mau sac pastel
- tang tinh don sac / grayscale
- vien va mui ten nhe hon
- bo cuc uu tien A4 landscape cho sequence / flow / ERD

### 5.2. Screenshot

Screenshot da duoc xu ly lai theo pattern bai mau:

- co khung nen xanh nhat
- co callout den danh so
- de danh chi so thanh phan trong bang ben duoi

### 5.3. Bia va front matter

- bia da gan hon bai mau hon truoc
- front matter ro hon va hop logic luan van hon

## 6. Kiem tra da thuc hien

### 6.1. Kiem tra asset path

Da xac nhan `main.tex` tro dung den:

- so do trong `assets/diagrams/`
- screenshot trong `assets/app/`
- anh AI trong `assets/real_data/`

### 6.2. Kiem tra build

Da build thanh cong bang:

- `pdflatex -interaction=nonstopmode -halt-on-error main.tex`

Build duoc chay lai sau khi xoa file phu tro cu (`main.aux`, `main.out`, `main.toc`, `main.lof`, `main.lot`) de on dinh lai front matter moi.

Ket qua:

- file dau ra: `docs/thesis_report/main.pdf`
- so trang: `59`
- kho giay: `A4`

### 6.3. Kiem tra truc quan nhanh

Da rasterize va kiem tra nhanh:

- bia
- muc luc
- danh muc hinh anh
- mot so trang chua so do
- trang screenshot giao dien annotate

## 7. Van de con lai

### 7.1. Toolchain

`XeLaTeX` van chua co san trong moi truong hien tai, nen ban build cuoi cung dang dung `pdfLaTeX` fallback.

Tac dong:

- PDF da xuat thanh cong
- nhung mot so chi tiet encoding / text extraction khong dep bang `XeLaTeX`

### 7.2. Muc luc `Tom tat`

De giu build `pdfLaTeX` on dinh, muc TOC hien tai dang de `Tom tat` khong dau thay vi `Tóm tắt`.

Day la compromise ky thuat cua moi truong build fallback, khong phai doi dung noi dung trang tom tat.

### 7.3. Warning nho con lai

Con mot so canh bao nho trong log:

- overfull nho o bia
- underfull o cac dong tai lieu tham khao co URL dai

Nhung khong chan build va khong lam vo PDF.

## 8. Ket luan

Dot cap nhat nay da dat duoc muc tieu thuc te:

- thesis co PDF build duoc
- bo asset da day du
- bo screenshot giao dien da duoc trinh bay theo huong bai mau
- bo so do chinh da duoc restyle theo phong cach luan van hon
- noi dung da tiep tuc duoc giu trong pham vi luong app chinh thuc te

Neu co mot buoc tiep theo nen lam, do se la:

1. cai `XeLaTeX` day du va build lai de co ban PDF dep hon ve encoding/font
2. neu can, chinh nhe front matter de `Tom tat` trong TOC tro lai co dau khi chuyen sang `XeLaTeX`
