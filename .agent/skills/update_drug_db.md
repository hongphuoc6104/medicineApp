---
description: how to update the drug database CSV from external sources/lists
---

# Update Drug Database

## Mục đích
Khi có danh sách thuốc tiếng Việt mới cần thêm vào hệ thống (để dùng cho `s6_drug_search`), hoặc cần build lại file CSV từ VAIPE + nguồn ngoài.

## Bước 0: Backup trước khi thay đổi (BẮT BUỘC)
// turbo
1. Backup file CSV hiện tại:
```bash
cp data/drug_db_vn.csv data/drug_db_vn.csv.bak_$(date +%Y%m%d)
```

## Các Script Build Database

| Script | Mục đích | Input | Output |
|--------|----------|-------|--------|
| `scripts/build_drug_db.py` | Build DB cơ bản từ VAIPE JSON | `data/vaipe_drugs_kb.json` | `data/drug_db_vn.csv` |
| `scripts/build_full_drug_db.py` | Cào data từ API DDI Lab VN | Network (DDI API) | Ghi đè file CSV |

## Cách thực hiện

### Cách 1: Re-build từ VAIPE (nhanh, offline)
// turbo
2. Chạy script build cơ bản:
```bash
python scripts/build_drug_db.py
```

### Cách 2: Cập nhật từ API DDI Lab (chậm, cần internet)
3. Chạy script lấy full DB tiếng Việt — **CONFIRM VỚI USER TRƯỚC khi chạy (tốn bandwidth)**:
```bash
python scripts/build_full_drug_db.py
```
> ⚠️ Script này ghi đè trực tiếp file CSV. Không có undo nếu quên backup!

## Kiểm tra kết quả
// turbo
4. Xem số dòng và cột của file CSV mới:
```bash
wc -l data/drug_db_vn.csv && head -3 data/drug_db_vn.csv
```
- Kỳ vọng: >1,800 dòng (build_full) hoặc ~107 dòng (build cơ bản từ VAIPE)
- Cột quan trọng nhất: `name` (dùng cho fuzzy-match)

## Rollback nếu cần
// turbo
5. Khôi phục bản backup:
```bash
cp data/drug_db_vn.csv.bak_$(date +%Y%m%d) data/drug_db_vn.csv
```
