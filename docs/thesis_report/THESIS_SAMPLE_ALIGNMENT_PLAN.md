# Thesis Sample Alignment Plan

## 1. Muc tieu

Tai lieu nay chot mot plan thuc thi mot lan cho viec trinh bay lai `docs/thesis_report/main.tex` dua tren bai mau trong:

- `docs/mẫu bài luận/BÁO_CÁO_LUẬN_VĂN___Niên_luận__Copy_/bao_cao/Luan_van/Luan_van_thac_si.tex`

Day la nguon tham khao chinh ve format va cach dung hinh anh / so do.

Nguon phu de tham khao ky thuat LaTeX:

- `docs/mẫu bài luận/BÁO_CÁO_LUẬN_VĂN___Niên_luận__Copy_/main.tex`
- `docs/mẫu bài luận/BÁO_CÁO_LUẬN_VĂN___Niên_luận__Copy_/hcmuitthesis.cls`

Muc tieu sau cung:

- Bao cao cua do an MedicineApp phai giong tinh than cua bai mau: ro rang, hoc thuat, sach, de in, khong la "slide deck" doi mau.
- Noi dung chi bam luong app chinh thuc te.
- Hinh anh va so do du, dung cho, dung vai tro, khong thua.

## 2. Ket luan rut ra tu bai mau

### 2.1. Ve bo cuc tong the

Tu bai mau, cac dac diem can bam theo la:

1. Co hai trang bia ro rang.
2. Co khoi front matter day du:
   - muc luc
   - danh muc hinh anh
   - danh muc bang bieu
   - danh muc tu viet tat
   - abstract
   - tom tat
3. Chuong / muc / tieu muc duoc danh ro va cach nhau sach.
4. Figure duoc dat sat noi dung giai thich cua no, khong de figure treo khong co doan van dan vao.
5. Cac man hinh giao dien quan trong thuong co:
   - hinh chup giao dien
   - bang liet ke thanh phan ngay phia duoi.
6. Cac so do he thong / quy trinh duoc uu tien dang den trang, outline don gian, de in.
7. Bang duoc dung rat nhieu de tong hop, khong lam qua nhieu chart mau me.

### 2.2. Ve cach dung hinh anh

Trong bai mau co 3 nhom hinh ro rang:

1. Hinh mo ta khai niem / co so ly thuyet.
2. So do he thong / luong xu ly / quy trinh / CSDL.
3. Screenshot giao dien san pham.

Do an MedicineApp khong can nhom 1 nhieu nhu bai mau. Ta chi can giu mot vai hinh AI thuc te va tap trung nhom 2 + 3.

### 2.3. Ve phong cach do hoa

Bai mau cho thay mot chuan trinh bay rat ro:

- so do uu tien den trang / xam nhat
- vien den, mui ten den, nen trang
- it hoac khong dung palette mau phuc tap
- screenshot giao dien duoc danh so callout roi co bang giai thich ben duoi

=> Ket luan quan trong: bo so do hien tai cua MedicineApp nen duoc dieu chinh theo huong thesis-like hon, giam tinh "UI card / infographic pastel".

## 3. Chuan format can bam theo

### 3.1. Chuan front matter

Can dieu chinh luan van hien tai de bam trinh tu sau:

1. Bia 1
2. Bia 2
3. Loi cam on (neu giu)
4. Muc luc
5. Danh muc hinh anh
6. Danh muc bang bieu
7. Danh muc tu viet tat
8. Abstract
9. Tom tat
10. Noi dung chinh
11. Tai lieu tham khao

Neu khong du thoi gian de doi lai toan bo front matter, uu tien bat buoc la:

- muc luc
- danh muc hinh
- danh muc bang
- danh muc tu viet tat
- abstract
- tom tat

### 3.2. Chuan chapter layout

De tai cua chung ta nen duoc tai cau truc theo tinh than bai mau nhu sau:

1. Phan gioi thieu
2. Chuong 1. Mo ta bai toan va co so lien quan
3. Chuong 2. Thiet ke va cai dat giai phap
4. Chuong 3. Kiem thu va danh gia
5. Ket luan va huong phat trien

Neu van giu `report` structure hien tai, thi phai dam bao mapping y tuong tuong duong:

- `Gioi thieu`
- `Co so ly thuyet / cong nghe`
- `Phan tich va thiet ke he thong`
- `Cai dat he thong`
- `Thuc nghiem va danh gia`
- `Ket luan va huong phat trien`

### 3.3. Chuan caption

Rut ra tu bai mau:

- Caption ngan, dung vai tro, khong viet thanh doan van.
- Figure caption dat duoi hinh.
- Table caption dat tren bang.
- Caption phai noi dung nguoi doc can thay, khong chi lap lai ten file.

## 4. Danh sach hinh / so do can co cho do an MedicineApp

### 4.1. Bat buoc phai co

#### Nhom du lieu thuc va AI

1. `input_prescription.jpg`
   - muc dich: chung minh bai toan dau vao la don thuoc thuc
2. `preprocessed.png`
   - muc dich: chung minh buoc crop / deskew / orientation
3. `ocr_det.png`
   - muc dich: chung minh OCR detect da tim duoc vung van ban

#### Nhom so do he thong

4. So do kien truc tong the he thong
5. So do use case muc he thong
6. So do tuan tu luong quet don thuoc core
7. So do pipeline AI Phase A
8. So do ERD core scan + plan + log
9. So do activity create plan

#### Nhom screenshot app core

10. Man hinh quet don
11. Man hinh ra soat ket qua
12. Man hinh lap lich
13. Man hinh theo doi hom nay

### 4.2. Nen co neu con cho va co doan van tuong ung

14. Man hinh lich su ke hoach va nhat ky

### 4.3. Chi dua vao neu mo mot subsection phu tro rieng

15. Man hinh thong bao nhac uong
16. Man hinh tra cuu / kiem tra hop chat
17. Man hinh warning review

### 4.4. Khong dua vao narrative trung tam

18. Hinh lien quan pill verification
19. So do scan session nhieu anh
20. So do interaction subsystem
21. Bat ky hinh nao chi de minh hoa code, route, file tree

## 5. Chien luoc dung hinh theo bai mau

### 5.1. Nguyen tac tong quat

Moi hinh trong bao cao phai thuoc 1 trong 3 vai tro:

1. Minh hoa bai toan thuc te
2. Minh hoa thiet ke / quy trinh / kien truc
3. Minh hoa giao dien nguoi dung

Neu mot hinh khong thuoc 3 vai tro nay thi khong dua vao.

### 5.2. Pattern can hoc tu bai mau

#### Pattern A: So do -> Doan van dien giai

Ap dung cho:

- architecture
- sequence
- scan flow
- ERD
- activity

Form:

1. Mo mot subsection ngan
2. Dat hinh
3. 1-3 doan van phan tich hinh

#### Pattern B: Screenshot UI -> Bang thanh phan

Ap dung cho:

- scan camera
- scan review
- set schedule
- home today
- history week (neu giu)

Form:

1. Mo ta ngan y nghia man hinh
2. Dat screenshot da annotate
3. Dat bang "Cac thanh phan cua giao dien"

Day la pattern can ap dung nghiem tuc nhat neu muon thesis cua chung ta trong giong bai mau.

## 6. Yeu cau cu the cho screenshot app

### 6.1. Cach thiet ke lai screenshot

Can lam theo kieu bai mau:

1. Screenshot dat tren nen sach.
2. Co 2-4 dau tron den / dam danh so cac vung quan trong.
3. Neu can, dung mui ten do hoac den rat gon, khong keo dai ngoan ngoheo.
4. Sau screenshot phai co bang giai thich tung so.

### 6.2. Cac man hinh can annotate

#### A. Man hinh quet don

Can danh so cac thanh phan sau neu ton tai trong UI:

1. vung preview camera
2. nut chup anh
3. thong bao / guidance ve chat luong anh
4. thanh quay lai hoac dieu huong

Bang thanh phan ben duoi nen co cot:

- STT
- Thanh phan
- Mo ta

#### B. Man hinh ra soat ket qua

Can danh so:

1. danh sach thuoc duoc AI nhan ra
2. thao tac sua / xoa / them thuoc
3. nut tiep tuc sang lap lich

#### C. Man hinh lap lich

Can danh so:

1. ngay bat dau / so ngay
2. danh sach khung gio
3. so vien theo tung khung gio
4. nut luu ke hoach

#### D. Man hinh theo doi hom nay

Can danh so:

1. the tom tat lieu hom nay
2. danh sach lieu sap den gio / trong ngay
3. thao tac da uong / bo qua
4. lich tuan neu xuat hien ro rang

#### E. Man hinh lich su (neu giu)

Can danh so:

1. bo loc ngay / tuan / ke hoach
2. danh sach lich su
3. thong tin chi tiet mot muc

### 6.3. Cac screenshot khong nen dua vao than bao cao

- lookup_interaction_check
- notification_lockscreen
- notification_in_app_check
- scan_review_warning
- history_reuse_old_plan

nhung file nay co the giu lai cho phu luc hoac bao cao noi bo.

## 7. Yeu cau cu the cho so do

### 7.1. Chuan my thuat can bam theo bai mau

Tat ca so do phai duoc re-style theo huong sau:

- den trang la chu dao
- nen trang
- vien den / xam dam vua phai
- khong dung pastel dang card UI nhu bo so do hien tai
- mui ten thang, gon, it giao cat
- chu ngan gon, de doc khi in xam den

### 7.2. Bo so do can thiet va vai tro

#### 1. So do kien truc tong the

Muc dich:

- cho thay mobile, Node.js, FastAPI, PostgreSQL, drug DB

Canh bao:

- khong dung style card UI mau me
- khong mo ta route phu

#### 2. So do use case

Muc dich:

- cho thay actor va cac chuc nang trong pham vi luong chinh

Canh bao:

- khong dua lookup / pill verification / sync vao hinh nay

#### 3. So do sequence scan core

Muc dich:

- mo ta dung flow 1 anh -> review

Canh bao:

- bo gallery / auto capture / session branch neu lam roi

#### 4. So do pipeline AI Phase A

Muc dich:

- detect/crop -> preprocess -> quality gate -> ROI -> OCR -> STT -> NER -> lookup

Canh bao:

- phai de doc tren A4 landscape

#### 5. So do ERD core

Muc dich:

- mo ta nhom bang scan + plan + logs

Canh bao:

- khong dua bang interaction / pill verification vao ERD chinh

#### 6. So do activity create plan

Muc dich:

- minh hoa flow tu ket qua quet den luu ke hoach

Canh bao:

- khong nhet qua nhieu decision

### 7.3. Kiem tra mui ten va tu ngu tren so do

Moi so do phai qua checklist sau:

1. Mui ten chinh = net lien.
2. Mui ten response / tuy chon = net dut.
3. Khong de mui ten dam qua.
4. Khong de mui ten dam xuyen chu.
5. Label nhanh quyet dinh dat sat nhanh.
6. Khong de node co hon 3 dong text.
7. Khong lai Anh - Viet trong cung mot node neu khong can.

## 8. Phan noi dung can doi theo bai mau

### 8.1. Giam tinh implementation-heavy

So voi huong hien tai, bai mau cho thay:

- co giai thich ky thuat
- nhung van uu tien giai thich bai toan, quy trinh, vai tro he thong
- khong day dac ten file, ten folder, ten route vao than van

=> Luat chinh sua cho thesis cua chung ta:

1. Giu ten cong nghe quan trong.
2. Giam nhac den ten file / ten module noi bo.
3. Uu tien noi theo tinh nang va quy trinh su dung.

### 8.2. Them bang thanh phan giao dien

Day la diem can hoc manh nhat tu bai mau.

Cho moi screenshot UI chinh dua vao bao cao, can co 1 bang thanh phan ben duoi.

Mau bang:

| STT | Thanh phan | Mo ta |
|---|---|---|
| 1 | ... | ... |

So luong bang UI de xay dung:

- 4 bang bat buoc cho 4 man hinh core
- 1 bang them neu giu man hinh history

### 8.3. Them bang tong hop thay vi them nhieu hinh du thua

Tu bai mau co the rut ra:

- khong can nhet qua nhieu hinh giao dien
- nen thay bang tong hop / bang mo ta de giu tinh hoc thuat

Voi do an cua chung ta, can uu tien them cac bang sau:

1. Bang cac cong nghe chinh
2. Bang cac buoc pipeline AI
3. Bang nhom API chinh
4. Bang benchmark snapshot
5. Bang thanh phan cua cac man hinh UI

## 9. Mapping mot-mot giua bai mau va do an chung ta

### 9.1. Nhom figure he thong

Theo bai mau:

- Hinh 4: so do tong quan he thong
- Hinh 5: so do CSDL muc quan niem
- Hinh 6-18: cac quy trinh / luong xu ly

Ap vao do an chung ta:

- Hinh kien truc tong the
- Hinh ERD core
- Hinh sequence scan
- Hinh AI pipeline
- Hinh activity create plan

### 9.2. Nhom screenshot giao dien

Theo bai mau:

- Hinh 23-30 deu la UI screenshot + bang thanh phan

Ap vao do an chung ta:

- man hinh quet don
- man hinh ra soat
- man hinh lap lich
- man hinh hom nay
- man hinh history (neu giu)

### 9.3. Nhom hinh ly thuyet

Theo bai mau:

- dung nhieu hinh khai niem vi de tai goc la ve RAG / LLM / NLP.

Ap vao do an chung ta:

- khong can nhieu hinh ly thuyet.
- chi giu 3 hinh thuc te lien quan truc tiep den du lieu va AI:
  - input prescription
  - preprocessed
  - ocr detection

## 10. Plan thuc thi mot lan chay

### Phase 1. Dong bo format theo bai mau

1. Kiem tra front matter hien tai.
2. Dieu chinh thu tu front matter de gan voi bai mau hon.
3. Chuan hoa caption table / figure.
4. Chuan hoa chapter heading / spacing / font size neu can.

### Phase 2. Tai thiet ke bo so do

1. Ve lai toan bo so do theo style don sac thesis.
2. Dam bao A4 portrait / landscape ro rang.
3. Xoa hoac thay cac so do dang mang tinh infographic qua nhieu.

### Phase 3. Tai xay dung bo screenshot giao dien

1. Chon 4 screenshot core.
2. Them numbered callout len screenshot.
3. Export asset final ve `assets/app/`.
4. Tao bang thanh phan cho tung screenshot.

### Phase 4. Cap nhat noi dung chuong theo logic bai mau

1. Chuong thiet ke: dat so do he thong, ERD, luong xu ly.
2. Chuong cai dat / giao dien: dat screenshot UI + bang thanh phan.
3. Chuong danh gia: giu bang benchmark va bo sung neu can hinh ket qua OCR.

### Phase 5. Build va QA

1. Build PDF.
2. Kiem tra danh muc hinh / bang.
3. Kiem tra moi figure co duoc dan vao va duoc giai thich khong.
4. Kiem tra screenshot + so do co doc duoc khi in.

## 11. Definition of Done cho dot can chinh theo bai mau

Chi xem la xong khi dat du tat ca dieu kien sau:

1. Front matter cua thesis da du gan voi bai mau.
2. Bo so do duoc ve lai theo phong cach thesis don sac.
3. Co du 4 screenshot UI core va moi screenshot co bang thanh phan ben duoi.
4. Khong con screenshot / hinh / so do ngoai pham vi luong chinh.
5. Figure va table duoc danh so, xuat hien trong danh muc hinh / bang.
6. Bao cao doc giong mot bai luan hoc thuat ung dung, khong qua ky thuat.
7. PDF xuat ra doc duoc tren A4.

## 12. Danh sach cong viec uu tien cao nhat cho lan build tiep theo

1. Ve lai `architecture`, `use_case`, `sequence`, `scan_flow`, `ERD`, `activity` theo style den trang.
2. Chon va annotate 4 screenshot core.
3. Tao 4 bang thanh phan UI theo phong cach bai mau.
4. Dieu chinh front matter va caption numbering cho giong mau hon.
5. Build PDF va doi chieu voi bai mau o muc:
   - do sach cua bo cuc
   - tinh hoc thuat cua figure placement
   - do day cua screenshot + bang giai thich.
