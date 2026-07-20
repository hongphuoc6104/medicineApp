# Scripts

| Script | Lệnh chạy | Mô tả |
|--------|----------|-------|
| `run_pipeline.py` | `python scripts/run_pipeline.py --text "Celecoxib 200mg"` | Chạy thử nghiệm trích xuất thuốc cho 1 đoạn text |
| `debug_checks.sh` | `bash scripts/debug_checks.sh --quick` | Chạy bộ kiểm tra nhanh cho toàn bộ workspace (Python, Node, Flutter) |
| `train_ner.py` | `python scripts/train_ner.py` | Train PhoBERT NER model |
| `prepare_ner_data.py` | `python scripts/prepare_ner_data.py` | Chuẩn bị data NER từ VAIPE |
| `crawl_drug_vn.py` | `python scripts/crawl_drug_vn.py` | Crawl danh mục thuốc VN từ ddi.lab.io.vn |
| `build_full_drug_db.py` | `python scripts/build_full_drug_db.py` | Xử lý và build CSDL 9,284 thuốc |

### Tham số `run_pipeline.py`

```bash
# Nhận text trực tiếp từ CLI
python scripts/run_pipeline.py --text "1) Celecoxib 200mg - 20 Viên\n2) Loratadine 10mg"

# Nhận text từ tệp tin văn bản (ví dụ kết quả OCR từ mobile)
python scripts/run_pipeline.py --text-file data/sample_ocr.txt
```
