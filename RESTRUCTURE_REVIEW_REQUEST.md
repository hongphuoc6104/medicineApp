# Yeu Cau Kiem Tra Tai Cau Truc Repo

> Muc tieu cua file nay: tong hop ro rang nhung gi nen xoa, nen gom, nen doi cho, va nhung diem can chot kien truc truoc khi don dep repo `medicineApp`.
>
> File nay chi de review va chot huong. Chua phai log xoa/chuyen file thuc te.

---

## 1. Muc tieu dot tai cau truc

- lam root project gon va de doc hon
- tach ro phan active, phan legacy, phan research, phan artifact
- giu `Phase B` trong repo nhung co lap gon hon de khong gay nhieu flow chinh
- tach tai lieu thesis khoi khu vuc active
- giam trung lap tai lieu, binary, script, va thu muc generated
- khong lam anh huong pipeline chinh `scripts/run_pipeline.py`

---

## 2. Nguyen tac an toan

- khong thay the logic pipeline chinh, chi don dep cau truc xung quanh tru khi co ly do bat buoc
- khong xoa le tung file `Phase B` khi van con import, route, screen, test tham chieu
- uu tien xoa artifact, cache, duplicate truoc
- moi thay doi co anh huong docs/import/path phai duoc doi chieu truoc khi xoa hoac doi ten
- moi thay doi lien quan source-of-truth cua du lieu thuoc phai chot kien truc truoc

---

## 3. Nhom A - Co the xu ly ngay (an toan tuyet doi)

### 3.1 Generated / cache / build artifacts

Nhung muc sau co the xoa an toan vi co the tao lai:

- `venv/`
- `mobile/build/`
- `mobile/.dart_tool/`
- `server-node/node_modules/`
- `data/output/`
- `**/__pycache__/`
- `.ruff_cache/`

### 3.2 Duplicate binary o root

Da doi chieu hash, 2 file root sau trung 100% voi file trong `models/yolo/`:

- `best_YOLO-main.pt` == `models/yolo/best.pt`
- `best_YOLO-detect-table-temp.pt` == `models/yolo/table_best.pt`

De xuat:

- xoa 2 file duplicate o root
- giu duy nhat weights trong `models/yolo/`

### 3.3 Build files cua thesis

Nhung file phu sau khong nen nam trong workspace active:

- `docs/thesis_report/main.aux`
- `docs/thesis_report/main.log`
- `docs/thesis_report/main.out`
- `docs/thesis_report/main.toc`
- `docs/thesis_report/main.lof`
- `docs/thesis_report/main.lot`
- `docs/thesis_report/xelatex.log`

### 3.4 Thu muc rong / placeholder can xem xoa

- `server/routers/`
- `server/schemas/`

Ghi chu:

- neu chua co y dinh su dung that, nen xoa de tranh tao cam giac co kien truc ma thuc te khong dung

---

## 4. Nhom B - Nen tai cau truc, can cap nhat docs / import / duong dan

### 4.1 Tai lieu dang stale hoac chua dong bo

Nhung file sau dang can review va dong bo lai:

- `README.md`
- `PIPELINE_STATUS.md`
- `data/README.md`
- `server/README.md`
- `mobile/README.md`
- `CLEANUP_REPORT_2026_04_12.md`
- `docs/master_plan.md`
- `docs/MASTER_PLAN.md`

Van de hien tai:

- `CLEANUP_REPORT_2026_04_12.md` noi da xoa mot so thu muc nhung thuc te hien van ton tai
- `mobile/README.md` con la boilerplate Flutter
- `data/README.md` khong dong bo voi huong dung drug DB hien tai
- `server/README.md` mo ta cau truc va endpoint cu
- `docs/master_plan.md` va `docs/MASTER_PLAN.md` dang song song, de gay nham file nao la nguon uu tien

De xuat:

- chot 1 bo tai lieu active
- danh dau ro file `legacy`
- doi ten hoac chuyen file cu vao khu `archive`

### 4.2 Tai cau truc thu muc `docs/`

De xuat chia lai:

- `docs/active/`
- `docs/reports/`
- `docs/archive/`

Goi y phan bo:

- `docs/active/`: runbook, project status, docs dang su dung
- `docs/reports/`: cleanup report, completion notes, rollout notes
- `docs/archive/`: master plan cu, handoff cu, docs khong con la nguon su that hien tai

### 4.3 Tai cau truc `scripts/`

Hien tai `scripts/` dang tron runtime, training, benchmark, debug, va test thu cong.

De xuat chia lai:

- `scripts/runtime/`
- `scripts/training/`
- `scripts/data_tools/`
- `scripts/debug/`
- `scripts/tests/manual/`
- `scripts/tests/phase_a/`
- `scripts/tests/phase_b/`

Nhung file dang nen duoc sap xep lai:

- `scripts/run_pipeline.py`
- `scripts/benchmark_pipeline.py`
- `scripts/debug_phase_a_checks.sh`
- `scripts/train_ner.py`
- `scripts/prepare_ner_data.py`
- `scripts/crawl_drug_vn.py`
- `scripts/build_drug_db.py`
- `scripts/build_full_drug_db.py`
- `scripts/test_full.py`
- `scripts/test_crop.py`
- `scripts/test_group_stt.py`
- `scripts/test_batch_group_stt.py`
- `scripts/test_stt_dynamic.py`
- `scripts/tests/test_phase_a_api_alignment.py`
- `scripts/tests/test_ocr_detailed_steps.py`
- `scripts/tests/test_new_features.py`
- toan bo test `Phase B` trong `scripts/tests/`

Luu y:

- buoc nay can cap nhat docs, lenh chay, va co the ca import neu co file tham chieu duong dan cu

### 4.4 Root clutter can xem gom lai

Nhung file dang lam root bi day:

- `AGENT_START_HERE.md`
- `APP_ACTIVE_GENERAL_PLAN.md`
- `APP_ACTIVE_DETAILED_PLAN.md`
- `APP_EXECUTION_BOARD.md`
- `CLEANUP_REPORT_2026_04_12.md`

Phuong an de xuat:

- giu `AGENTS.md`, `README.md`, `PIPELINE_STATUS.md` o root
- `CLEANUP_REPORT_2026_04_12.md` chuyen vao `docs/reports/`
- bo 4 file workflow AI vao `docs/agent_ops/` neu muon root gon hon

Can can nhac:

- hien co mot so file va workflow AI tham chieu truc tiep cac file nay tai root
- neu doi cho, phai cap nhat tat ca cac link va huong dan lien quan

---

## 5. Nhom C - Can chot kien truc truoc khi xoa hoac hop nhat

### 5.1 `Phase B` - Giu lai nhung co lap gon hon

Trang thai mong muon:

- giu `Phase B` trong repo
- khong de no gay nham la flow active chinh
- tach ro docs, tests, va khu vuc nghien cuu lien quan

Nhung khu vuc dang con rang buoc that:

- Python:
  - `core/phase_b/`
  - `core/pipeline.py`
  - `server/main.py`
  - `tests/test_phase_b_reference_matcher.py`
- Node:
  - `server-node/src/routes/pillReference.routes.js`
  - `server-node/src/routes/pillVerification.routes.js`
  - `server-node/src/services/pillReference.service.js`
  - `server-node/src/services/pillVerification.service.js`
  - `server-node/tests/integration/pillReference.routes.test.js`
  - `server-node/tests/integration/pillVerification.routes.test.js`
- Mobile:
  - `mobile/lib/features/pill_verification/`

Ket luan:

- khong xoa le tung file `Phase B`
- neu muon co lap, nen lam theo feature slice hoan chinh va cap nhat docs de danh dau `research / hold`

### 5.2 Thesis - Chuyen khoi khu active

Huong da chot:

- bo tai lieu thesis khong nen nam trong khu active
- nen chuyen sang khu `archive` hoac tach rieng

De xuat muc tieu:

- chuyen `docs/thesis_report/` vao `archive/thesis/`
- giu neu can:
  - `main.pdf`
  - `main.tex`
  - `assets/`
  - `diagrams/`
- bo build artifacts phu

Can xac nhan them khi thuc hien:

- co muon giu PDF final trong repo active khong, hay dua vao archive luon

### 5.3 Drug DB - Can chot source-of-truth

Hien tai ton tai 2 cum du lieu:

- Phase A / runtime chinh:
  - `data/drug_db_vn_full.json`
  - `data/drug_db_vn.csv`
- FastAPI local service / server-side:
  - `server/data/drug_db.json`
  - `server/data/drug_db_full.json`

Van de:

- trung lap ve mat khai niem
- khong ro file nao la nguon su that
- de gay nham khi cap nhat data hoac docs

Huong can chot:

- co xem `data/drug_db_vn_full.json` la source-of-truth duy nhat khong
- co can `server/data/*` nhu snapshot rieng cho API khong
- neu giu `server/data/*`, phai ghi ro chung la generated/derived tu dau

### 5.4 Co giu khung `server/routers/` va `server/schemas/` khong

Can chot:

- xoa cho sach vi hien tai rong
- hoac bat dau dung that neu muon dua `server/` ve dung mau kien truc module hoa

---

## 6. De xuat cau truc muc tieu sau tai cau truc

```text
medicineApp/
├── AGENTS.md
├── README.md
├── PIPELINE_STATUS.md
├── core/
├── data/
├── docs/
│   ├── active/
│   ├── reports/
│   ├── archive/
│   └── agent_ops/                # neu quyet dinh doi file workflow AI khoi root
├── scripts/
│   ├── runtime/
│   ├── training/
│   ├── data_tools/
│   ├── debug/
│   └── tests/
│       ├── manual/
│       ├── phase_a/
│       └── phase_b/
├── server/
├── server-node/
├── mobile/
├── models/
└── archive/
    └── thesis/
```

---

## 7. Thu tu thuc hien de xuat

### Dot 1 - Dung vao phan an toan truoc

1. xoa cache, build, generated output
2. xoa duplicate weights o root
3. chuyen cleanup report khoi root
4. xoa thu muc rong neu quyet dinh khong giu

### Dot 2 - Chuan hoa docs

1. chot file nao la active, file nao la legacy
2. sap xep lai `docs/`
3. cap nhat README va cac duong dan lien quan

### Dot 3 - Sap xep lai scripts

1. chia nhom runtime / training / data_tools / tests
2. cap nhat docs va lenh chay
3. kiem tra cac script debug/test thu cong sau khi doi cho

### Dot 4 - Co lap `Phase B`

1. tach docs va test `Phase B` khoi luong active
2. danh dau ro trang thai hold / research
3. giu nguyen code runtime neu con tham chieu build/test

### Dot 5 - Chot drug DB va server structure

1. chot source-of-truth cua data thuoc
2. quyet dinh so phan cua `server/data/*`
3. quyet dinh giu hay bo `server/routers/`, `server/schemas/`

---

## 8. Danh sach can user review truoc khi bat tay vao chuyen file

Vui long check va chot tung muc sau:

- [ ] Dong y xoa toan bo artifact/cache/build o Nhom A
- [ ] Dong y xoa 2 file duplicate weights o root
- [ ] Dong y chuyen `CLEANUP_REPORT_2026_04_12.md` vao `docs/reports/`
- [ ] Dong y sap xep lai `scripts/` thanh nhieu nhom chuc nang
- [ ] Dong y tach `docs/thesis_report/` vao `archive/thesis/`
- [ ] Dong y giu `Phase B` trong repo nhung danh dau va co lap ro hon
- [ ] Dong y chot 1 bo docs active va day bo docs cu vao archive
- [ ] Dong y ra quyet dinh rieng cho source-of-truth cua drug DB
- [ ] Dong y quyet dinh rieng cho `server/routers/` va `server/schemas/`

---

## 9. Muc tieu nghiem thu

Dot tai cau truc duoc xem la dat khi:

- root project gon hon va de scan bang mat
- khong con binary duplicate va artifact lon khong can thiet
- docs co active/legacy ro rang
- scripts duoc nhom theo chuc nang
- thesis khong con nam trong khu active
- `Phase B` con trong repo nhung khong lam nhieu flow chinh
- khong gay regression cho `scripts/run_pipeline.py` va flow active hien tai
