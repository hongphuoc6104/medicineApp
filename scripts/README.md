# Scripts

| Script | Lệnh chạy | Mô tả |
|--------|----------|-------|
| `run_pipeline.py` | `python scripts/run_pipeline.py --image data/input/IMG.jpg` | Chạy Phase A cho 1 ảnh |
| `build_drug_db.py` | `python scripts/build_drug_db.py` | Build drug database CSV |
| `train_ner.py` | `python scripts/train_ner.py` | Train PhoBERT NER model |
| `prepare_ner_data.py` | `python scripts/prepare_ner_data.py` | Chuẩn bị data NER từ VAIPE |

### Tham số `run_pipeline.py`

```bash
# 1 ảnh
python scripts/run_pipeline.py --image data/input/IMG_20260209_180420.jpg

# 1 folder ảnh
python scripts/run_pipeline.py --dir data/input/prescription_3

# Tất cả ảnh trong data/input/ (recursive)
python scripts/run_pipeline.py --all

# Giới hạn số ảnh
python scripts/run_pipeline.py --all --limit 5

# Bỏ qua NER (fallback mode)
python scripts/run_pipeline.py --all --no-ner
```
