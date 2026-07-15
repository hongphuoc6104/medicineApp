# Nhật ký quyết định

Mọi quyết định kiến trúc, test, benchmark hoặc cleanup được thêm ở đây, không sửa lịch sử cũ.

| ADR | Trạng thái | Quyết định |
|---|---|---|
| ADR-001 | ACCEPTED | Baseline là `main@a6810a392c97593f073a9c5e2b8dfc47027c1911`; tạo worktree riêng, không sửa experiment |
| ADR-002 | ACCEPTED | Native Android bridge dùng ML Kit Document Scanner `16.0.0` |
| ADR-003 | ACCEPTED | Giữ YOLO, deskew, orientation đến sau B0/B1/B2/B3 benchmark |
| ADR-004 | ACCEPTED | Chỉ `docs/mlkit_progressive_ocr/` là docs active; giữ reproducibility, xóa dead code |
| ADR-005 | ACCEPTED | CPU-first: selective OCR, batching, quantization, ONNX/OpenVINO khi cần |
| ADR-006 | ACCEPTED | Progressive OCR đi `shadow`, `exhaustive`, rồi `guarded`; partial không là complete |
| ADR-007 | ACCEPTED | Xóa generated artifact/cache, giữ venv/model/Docker rollback |
| ADR-008 | ACCEPTED | Archive docs main ra sibling ngoài repo với hash kiểm chứng |

Mẫu: ngày, trạng thái (`PROPOSED|ACCEPTED|SUPERSEDED|REJECTED`), quyết định, lý do, bằng chứng, hệ quả và ADR thay thế.
