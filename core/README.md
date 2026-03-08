# Core — Source Code Chính

Module chứa toàn bộ logic nghiệp vụ MedicineApp.

## Cấu trúc

| Thư mục | Mô tả |
|---------|-------|
| `phase_a/` | Quét đơn thuốc — 4 bước (xem `phase_a/README.md`) |
| `phase_b/` | Xác minh viên thuốc — 2 bước (chưa hoạt động) |
| `shared/` | Module dùng chung: load model, visualizer |
| `config.py` | Cấu hình paths và thresholds |
| `pipeline.py` | Orchestrator tích hợp cả 2 phase |
