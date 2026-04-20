# Thesis Presentation Review And Fix Plan

## 1. Muc tieu

Tai lieu nay tong hop 3 viec trong 1 lan chay:

- danh gia chat luong trinh bay hien tai cua thesis
- chi ro phan nao kho hieu, bi roi, bi che, hoac du thua
- chot cach sua cu the de giai quyet tung van de

Pham vi danh gia dua tren cac file dang dung thuc te:

- `docs/thesis_report/main.tex`
- `docs/thesis_report/main.pdf`
- `docs/thesis_report/assets/diagrams/*`
- `docs/thesis_report/assets/app/*`
- `docs/thesis_report/diagrams/render_thesis_diagrams.py`
- `docs/thesis_report/image/annotate_app_screenshots.py`
- schema that su trong `server-node/src/config/migrate.js`
- luong app/backend that su trong `mobile/lib/core/router/app_router.dart`, `server-node/src/routes/*.js`, `server-node/src/services/*.js`

## 2. Ket luan nhanh

### 2.1. Diem tot

- PDF hien tai da build tren kho A4.
- So do dang co do phan giai cao, khong co dau hieu mo net do xuat file.
- Screenshot app dang co do phan giai du de in, khong phai loai asset 500px nguy hiem.
- Luong core cua thesis da duoc gioi han dung tam: scan -> review -> schedule -> today/history.

### 2.2. Diem can sua

- ERD hien tai truoc khi sua co quan he sai so voi schema that va co line cat qua khu vuc doc noi dung.
- Use case truoc khi sua co duong noi cat xuyen ellipse, lam hinh nhin roi va kem giong mau thesis sach.
- Mot so so danh dau tren screenshot de len noi dung that cua giao dien, nhat la `scan_review`, `set_schedule`, `home_today`.
- Phan ERD trong `main.tex` truoc khi sua chua co bang tom tat vai tro tung thuc the, nen nguoi doc kho doi chieu schema.
- Van con rui ro typography do build bang `pdfLaTeX` fallback: TOC dang hien `Tom tat` khong dau va text extraction co the xau hon `XeLaTeX`.

## 3. Danh gia chi tiet theo tieu chi user yeu cau

### 3.1. Cau tu va do kho hieu

Danh gia:

- Nhieu doan trong `main.tex` da ro y, nhung phan ERD truoc khi sua chua tach bach ro bang nao la core, bang nao la bang ho tro.
- Neu chi xem Hinh ERD ma khong doc code/schema, nguoi doc de hieu nham rang `scan_sessions` la bang trung tam ngang hang voi `prescription_plans`.
- Chua co bang mo ta nhanh tung thuc the theo style "ten bang - vai tro - dung de lam gi" nen phan du lieu van can qua nhieu suy luan.

Can sua de giai quyet van de gi:

- Them bang tom tat thuc the de giai quyet van de "nguoi doc nhin hinh ma khong biet bang nay dung de lam gi".
- Noi ro `scan_sessions` la bang ho tro cho nhanh mo rong de giai quyet van de "ERD co ve mang bang phu tro vao qua dam".
- Giu cach dien dat theo vai tro nghiep vu, khong theo kieu ke ten implementation qua nang.

### 3.2. Hinh anh trinh bay, co che khuat hay qua nho khong

Du lieu kiem tra:

- App screenshots goc: rong khoang `946-962px`, ban annotate rong `952-962px`.
- Khi embed vao PDF, `pdfimages -list main.pdf` cho thay cac screenshot annotate dang in o muc xap xi `291-294 ppi`.

Ket luan:

- Ve mat pixel, cac screenshot khong qua nho va khong bi vo net.
- Ve mat bo cuc, van con mot so callout dang de len noi dung that cua UI. Van de nay khong phai mo net, ma la che thong tin.

Can sua de giai quyet van de gi:

- Doi vi tri so danh dau sang vung trong hon de giai quyet van de "so danh dau che text/nut that".
- Giu kich thuoc so danh dau gon hon de giai quyet van de "circle chiem qua nhieu dien tich".

### 3.3. Du lieu trong ERD co du thua khong

Danh gia theo schema that:

- Nen giu: `users`, `scans`, `scan_sessions`, `prescription_plans`, `prescription_plan_drugs`, `prescription_plan_slots`, `prescription_plan_slot_drugs`, `prescription_plan_logs`.
- Nen bo khoi ERD chinh: `pill_verification_*`, `pill_reference_*`, `drug_interaction_*`, `drug_active_ingredients`, `interaction_active_ingredients`, `refresh_tokens`, `drug_cache`.

Nhan xet quan trong:

- `scan_sessions` la bang co that, nhung la bang phu tro cho nhanh scan session mo rong, khong phai nhanh core `/api/scan` duoc minh hoa o sequence chinh.
- Vi vay, bang nay co the giu trong ERD, nhung phai mo ta ro la "ho tro" thay vi de trong tam giong cac bang plan.

Can sua de giai quyet van de gi:

- Giu `scan_sessions` nhung ha muc uu tien bang wording de giai quyet van de "so do dung nhom bang phu tro lam mat trong tam".
- Khong dua bang interaction/pill verification vao ERD trung tam de giai quyet van de "ERD phinh to, loang narrative".

### 3.4. Sơ do co chong cheo, mat net, che mui ten hay khong

Use case:

- Ban cu co duong noi cat xuyen ellipse va chu `<<include>>` dat sat mui ten, lam hinh nhin roi.
- Ban moi nen uu tien line thang, khong cat vao hinh ellipse, moi use case la mot khoi ro rang.

ERD:

- Ban cu co line cat vao noi dung entity va the hien sai mot so quan he.
- Ten bang `plan_slot_drugs` khong khop schema that `prescription_plan_slot_drugs`.

Sequence / architecture / scan flow:

- Do net tot.
- Sequence va scan flow nhin chung doc duoc, nhung van phai giu nguyen tac: uu tien line thang hoac line gap khuc vuong, tranh cat qua text.

Can sua de giai quyet van de gi:

- Ve lai ERD va use case de giai quyet dong thoi 2 van de: dung nghiep vu va sach bo cuc.
- Giu ten bang dung 100% schema de giai quyet van de "nguoi doc doi chieu khong ra code/schema".

### 3.5. Tu ngu co nguy co bien dang khi in PDF khong

Danh gia:

- Khong thay dau hieu text trong hinh bi raster xau hay mo.
- Rui ro lon nhat hien tai khong nam o hinh, ma nam o toolchain build `pdfLaTeX` fallback.
- Dau hieu ro nhat: TOC dang de `Tom tat` khong dau de build on dinh.

Can sua de giai quyet van de gi:

- Neu co `XeLaTeX`, build lai bang font path on dinh de giai quyet van de encoding/TOC co dau.
- Neu chua co `XeLaTeX`, chap nhan build fallback nhung phai ghi ro day la compromise ky thuat, khong phai loi noi dung.

### 3.6. Hinh anh co hinh nao bien dang khong

Danh gia:

- Chua thay hinh nao bi keo gian sai ti le.
- Cac so do la SVG -> PNG, nen khong co dau hieu vo net do resize.
- Cac screenshot app dang duoc crop va chen theo ti le hop ly.

Can sua de giai quyet van de gi:

- Tiep tuc giu quy tac crop mem, khong cat qua sat thanh phan chinh.
- Neu ghep 2 phan giao dien thanh 1 anh thi can giu vien, canh va khoang trang nhat quan de tranh cam giac cat ghep tho.

## 4. Phat hien muc do uu tien cao

### Finding 1 - ERD truoc khi sua co quan he sai va ten bang sai

Muc do: cao

Bang chung:

- source cu trong `docs/thesis_report/diagrams/render_thesis_diagrams.py`
- hinh cu `docs/thesis_report/assets/diagrams/erd_main_a4_v3.png`

Van de:

- ve quan he khong dung schema that
- ten bang `plan_slot_drugs` sai ten schema
- line noi cat vao entity va cat qua nhau

Huong sua:

- ve lai ERD theo FK that su trong `server-node/src/config/migrate.js`
- chi giu 8 bang phuc vu luong chinh
- doi ten bang dung `prescription_plan_slot_drugs`
- doi line sang kieu orthogonal de tranh cat qua noi dung

### Finding 2 - Use case truoc khi sua bi line cat xuyen ellipse

Muc do: trung binh

Bang chung:

- `docs/thesis_report/assets/diagrams/use_case_a4_v3.png`

Van de:

- duong noi actor chay xuyen use case
- nhan `include/extend` dat sat duong mui ten, nhin roi

Huong sua:

- rut gon thanh use case tong quat, moi ellipse mot dong y chinh
- noi actor bang line thang dung diem dung tai mep ellipse
- bo semantic `include/extend` neu no khong them gia tri hoc thuat ro rang

### Finding 3 - Screenshot annotate van che mot phan noi dung that cua UI

Muc do: trung binh

Bang chung:

- `docs/thesis_report/assets/app/scan_review_annotated.png`
- `docs/thesis_report/assets/app/set_schedule_annotated.png`
- `docs/thesis_report/assets/app/home_today_annotated.png`
- source tao anh: `docs/thesis_report/image/annotate_app_screenshots.py`

Van de:

- mot so so danh dau de tren text/nut that

Huong sua:

- doi toa do callout sang vung trong hon
- giam nhe kich thuoc circle
- neu can, tang frame/padding de dat callout o ria ngoai thay vi de len UI

### Finding 4 - Phan ERD trong chuong 3 truoc khi sua thieu bang mo ta bang/thuc the

Muc do: trung binh

Bang chung:

- `docs/thesis_report/main.tex`

Van de:

- nguoi doc co hinh nhung chua co bang tom tat role cua tung bang

Huong sua:

- them bang `Thuc the - Vai tro trong luong chinh`
- ghi ro bang nao core, bang nao ho tro

## 5. Quy tac trinh bay can chot cho dot chinh sua tiep theo

### 5.1. ERD

- Ve theo style hinh 1: entity box ro phan ten bang va thuoc tinh.
- Ten bang phai dung y schema that.
- Co phan mo ta bang/thuc the ngay sau hinh.
- Chi giu bang co trong luong chinh hoac can de giai thich schema that.

### 5.2. So do quy trinh / sequence / architecture

- Ve theo style hinh 3: chu nam gon trong khoi.
- Chu khong de len mui ten.
- Mui ten khong de len chu.
- Uu tien duong thang hoac gap khuc vuong, han che duong xeo.
- Neu buoc nao dai, rut gon text trong khoi va dua giai thich ra caption/doan van ben duoi.

### 5.3. Anh giao dien annotate

- So danh dau khong de len text quan trong, nut chinh, gia tri so, ten thuoc, hoac icon nghiep vu.
- Bang mo ta ben duoi phai co cot `STT` va vien bang ro rang.
- Neu ghep 2 phan giao dien thanh 1 anh, can giu canh ghep mem va khoang trang deu.
- Khong crop qua sat, khong cat hut icon/label o ria giao dien.

### 5.4. Kich thuoc va in PDF

- Diagram line-art: uu tien SVG source.
- Screenshot annotate: giu du net khi in, tranh nhung qua nhieu text trong 1 hinh.
- Neu 1 hinh van qua day, tach thanh overview + detail thay vi ep vao 1 trang.

## 6. Viec da thuc thi trong lan chay nay

- Da sua nguon ve use case de bo duong cat xuyen ellipse.
- Da sua nguon ve ERD theo quan he that su cua schema core va ten bang dung.
- Da them bang mo ta vai tro tung thuc the trong `main.tex`.
- Da chinh lai script annotate screenshot de giam muc do che noi dung that cua UI.

## 7. Phan can bo sung neu muon chot ban nop dep hon nua

- Cai dat `XeLaTeX` de xoa compromise `Tom tat` khong dau trong TOC.
- Them 1 vong print-preview thu cong sau khi build de chot chinh xac vi tri callout tren screenshot.
- Neu giang vien muon ERD theo dung style bang mo ta tung thuoc tinh nhu mau Word, can them bang chi tiet theo tung entity o muc phu luc hoac muc mo rong cua Chuong 3.

## 8. Tieu chi chap nhan sau cung

- Nguoi doc nhin ERD va biet ngay bang nao phuc vu luong chinh.
- Khong con line cat qua chu, cat qua khoi, hay cat qua mui ten mot cach roi mat.
- So danh dau trong screenshot khong che thong tin nghiep vu quan trong.
- PDF in ra khong can zoom moi doc duoc ten khoi, ten bang, nhan mui ten chinh.
