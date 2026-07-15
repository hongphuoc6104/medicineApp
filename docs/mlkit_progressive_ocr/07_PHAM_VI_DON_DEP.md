# Phạm vi dọn dẹp

Chỉ xóa code khi không còn production call-site; cleanup tách riêng ML Kit/Progressive OCR; giữ reproducibility và fallback trước benchmark; không thay thế `scripts/run_pipeline.py`.

## Dọn Phase B trên baseline sạch

- `core/phase_b/**`, loader `core/shared/zero_pima_loader.py`, Zero-PIMA model/config.
- FastAPI pill endpoints; Node pill routes/services; Flutter pill feature/routes/tests; Phase B tests.
- Orphan gitlink `Web-Drugs-Interaction-Checker` sau xác nhận không có `.gitmodules`/runtime use.

## Giữ trước benchmark

YOLO, deskew, orientation, quality gate, table ROI, full VietOCR, grouping và CameraX fallback.

## Bắt buộc giữ

Phase A OCR, PhoBERT, DrugLookup/database, Node scan API, mobile create-plan, training/evaluation/model provenance và thư mục tài liệu này.

Generated artifacts không commit: `data/output/**`, Python cache, Flutter outputs, temporary scanner JPEGs, debug overlays có dữ liệu nhạy cảm. Chỉ giữ aggregate reports có provenance.

## Cleanup tracking

| ID | Trạng thái | Công việc |
|---|---|---|
| CLEAN-01 | DONE | Archive 83 tài liệu `main` ngoài repository, SHA-256 đã kiểm chứng |
| CLEAN-02 | DONE | Xóa 3.105 output images, giữ 3.130 reports |
| CLEAN-03 | DONE | Dọn Flutter/Node/Python cache, giữ venv/models |
| CLEAN-04 | DONE | Root `.dockerignore`; Python context còn 1.065 MB |
| CLEAN-05 | DONE | Xóa `core/shared` sau call-site audit |
| CLEAN-06 | IN_PROGRESS | Đã gỡ Node routes/services/tests, orphan gitlink và legacy `drug_mapper`; còn Python/FastAPI/mobile |
| CLEAN-07 | TODO | Policy/migration database Phase B |
| CLEAN-08 | TODO | Fresh install sau dependency cleanup |

Verification cleanup: không import/call-site đến code xóa; Python, Node, Flutter tests pass; route/dependency/database/Docker đúng policy.

Run `foundation-parallel-20260716-01` xác nhận retired Node roots trả `404 NOT_FOUND`, không proxy Python; toàn bộ Node suite đạt `97/97` trên PostgreSQL disposable đã migrate và seed. Database Phase B tables vẫn được giữ cho CLEAN-07.
