# Scripts Toàn Tập (Môi Trường Python)

## Protected Pipeline (Luồng Tự Nổ)

File quan trọng nhất và đang được Lock logic (Không được thay đổi luồng trừ khi tạo test script pass trước).

1. `run_pipeline.py`: Pipeline chạy đầy đủ Phase A qua 5 bước. Cú pháp chạy:
   ```bash
   python scripts/run_pipeline.py --image <path>
   python scripts/run_pipeline.py --dir <path>
   python scripts/run_pipeline.py --all
   ```

## Test & Debug Scripts

Dùng để cô lập hoặc review các đoạn component con để xem có phải lỗi từ pipeline không:
- `test_preprocess_robustness.py`: Benchmark cho logic nắn ảnh và Modulo 90, tự động xoay ngang/dọc/lộn ngược ảnh gốc (Desktop test OCR accuracy).

## Database / Knowledge Base Scripts
Các Script dùng để Update CSDL, crawler data về thuốc:
- `crawl_drug_vn.py`: Crawl hơn 9k đơn thuốc từ `ddi.lab.io.vn`
- `build_full_drug_db.py`: Bóc tách và kết xuất JSON `drug_db_vn_full.json`.
- `build_drug_db.py`: Trình biên dịch CSV dự phòng.

## Data Preparation (Trí tuệ nhân tạo)
- `train_ner.py`: Dùng để train Model PhoBERT phân rã.
- `prepare_ner_data.py`: Trích xuất NER nhãn (BIO format) từ database (Dành cho bản VAIPE Cũ). Đã được thay thế bằng synthetic sequence nhưng vẫn giữ vì code logic.
