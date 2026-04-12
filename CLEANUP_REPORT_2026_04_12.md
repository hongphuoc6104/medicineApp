# Bao Cao Don Dep Workspace 2026-04-12

Tai lieu nay ghi lai nhung gi da duoc xoa hoac giu lai trong qua trinh don dep workspace de giam lag cho OpenCode/IDE.

## 1. Da xoa

### Xoa de giai phong dung luong lon

- `archive/` (noi dung cu, da thay bang file mo ta moi)
- `venv/` (moi truong Python cuc bo)

### Xoa thu muc sinh tu dong

- `mobile/build/`
- `mobile/.dart_tool/`
- `mobile/.idea/`
- `mobile/medicine_app.iml`
- `data/output/`
- `server-node/node_modules/`
- `.pytest_cache/` (co the duoc tao lai boi test tool)
- `docs/thesis_report/diagram_tools/`
- `docs/thesis_report/mcp_tools/`

## 2. Giai thich ngan gon

### `archive/`

Thu muc nay chu yeu chua du lieu va ma cu khong con nam trong luong chinh cua san pham. Da xoa de giam tai workspace. Da de lai file `archive/README.md` mo ta noi dung cu.

### `venv/`

Day la moi truong Python cuc bo co the tao lai. Thu muc nay rat lon va khong can de IDE doc ma nguon. Neu can dung lai Python environment, co the tao moi.

### `mobile/build/`, `mobile/.dart_tool/`

Day la thu muc sinh tu dong cua Flutter, xoa an toan vi se duoc tao lai khi build hoac chay app.

### `mobile/.idea/`, `mobile/medicine_app.iml`

Day la tep va thu muc cau hinh IDE cuc bo, khong can thiet cho ma nguon cua du an.

### `data/output/`

Day la thu muc ket qua dau ra sinh ra trong qua trinh chay thu nghiem, khong phai du lieu goc.

### `server-node/node_modules/`

Day la thu muc phu thuoc Node.js co the cai lai bang `npm install` khi can.

### `docs/thesis_report/diagram_tools/`, `docs/thesis_report/mcp_tools/`

Day la thu muc cong cu tam thoi de tim va dung cong cu ve so do. Co the tao lai khi can.

## 3. Da giu lai

### `data/`

Khong xoa toan bo vi day la du lieu thuc cua du an, gom:

- `synthetic_train/`
- `input/`
- cac tep co so du lieu thuoc

Chi xoa `data/output/` vi la ket qua sinh ra.

### `models/`

Khong xoa vi day la trong so mo hinh can cho he thong AI. Neu xoa se anh huong truc tiep den kha nang chay pipeline.

### `mobile/`

Khong xoa thu muc chinh vi day la ma nguon ung dung. Chi don phan sinh tu dong.

### `server-node/`

Khong xoa thu muc chinh vi day la ma nguon may chu chinh. Chi xoa `node_modules/` vi la thu muc phu thuoc sinh ra.

### Nhung phan hien tai chua nen xoa

Sau khi doi chieu voi code va tai lieu hien tai, co mot so phan trong repo tuy nhin cu hoac mang tinh nghien cuu, nhung van con duoc tham chieu trong code:

- `core/phase_b/`
- `Zero-PIMA/`
- `mobile/lib/features/pill_verification/`
- `server-node/src/routes/pillReference.routes.js`
- `server-node/src/routes/pillVerification.routes.js`
- `server-node/src/services/pillReference.service.js`
- `server-node/src/services/pillVerification.service.js`
- cac bang cu nhom `medication_plans`, `pill_reference_*`, `pill_verification_*` trong migration

Ly do chua xoa:

- van con route, service, test, hoac import truc tiep trong ung dung;
- neu xoa se lam hong phan xac minh vien thuoc hoac mot so test hien co;
- phan nay dung la khong con uu tien, nhung chua duoc tach han khoi he thong.

Neu muon repo gon hon nua, can mot dot don dep co chu dich de loai bo toan bo nhanh chuc nang xac minh vien thuoc, khong nen xoa tung tep le.

## 4. Neu can tao lai moi truong Python

Co the tham khao quy trinh tong quat sau:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_dev.txt
```

Luu y: do du an co thanh phan AI va mo hinh lon, trong thuc te co the can cai them cac goi phu thuoc phu hop voi GPU/CPU cua may.

## 5. Muc tieu cua dot don dep nay

- giam dung luong workspace;
- giam so thu muc lon bi OpenCode/IDE quet;
- giu lai nhung thanh phan cot loi can cho phat trien app va bao cao.
