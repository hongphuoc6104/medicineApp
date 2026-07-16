# Phạm vi dọn dẹp

Chỉ xóa code khi không còn production call-site; cleanup tách riêng ML Kit/Progressive OCR; giữ reproducibility và fallback trước benchmark; không thay thế `scripts/run_pipeline.py`.

## Dọn Phase B trên baseline sạch

- Đã xóa `core/shared/visualizer.py`, `core/shared/__init__.py` và `core/shared/README.md` sau call-site audit. `core/shared/zero_pima_loader.py` vẫn còn và chỉ được xóa cùng Python core Phase B cleanup sau WP-03B.
- Node pill routes/services/tests, orphan gitlink `Web-Drugs-Interaction-Checker` và legacy `drug_mapper` đã xóa.
- Flutter lane đã xóa `mobile/lib/features/pill_verification/**` và hai route/deep link; CameraX, camera permission và `image_picker` vẫn giữ.
- FastAPI lane đã xóa `/api/scan-pills`, `/api/dose-verification` và helper chỉ phục vụ hai endpoint; `/api/scan-prescription`, WP-03A error contract và `/api/drug-metadata/{name}` vẫn giữ.
- Python `core/phase_b/**`, Zero-PIMA loader/model/config cleanup đã được mở sau WP-03B nhưng chưa triển khai.

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
| CLEAN-05 | DONE | Xóa visualizer/init/README không có call-site; không bao gồm `zero_pima_loader.py` |
| CLEAN-06 | IN_PROGRESS | Node, Flutter và FastAPI ingress đã xong; Python core/Zero-PIMA cleanup còn lại |
| CLEAN-07 | IN_PROGRESS | Implementation + disposable verification xong; backup/restore/production apply chưa thực hiện |
| CLEAN-08 | TODO | Fresh install sau dependency cleanup |

## CLEAN-07 schema retirement

Bảy bảng mục tiêu: `pill_verification_assignments`, `pill_verification_sessions`, `pill_reference_images`, `pill_reference_sets`, `dose_verification_feedback_events`, `dose_verification_detections`, `dose_verification_sessions`.

Fresh `migrate.js` không tạo các bảng này. Retirement là script riêng, mặc định dry-run; apply yêu cầu `--apply`, xác nhận chính xác database name, deployment identity có PostgreSQL `system_identifier` và backup-confirmed. Script không dùng `CASCADE`, drop trong một transaction dưới advisory lock và rollback nếu phát hiện external foreign key bất ngờ.

Wave hiện tại chỉ hoàn tất implementation và disposable PostgreSQL verification. CLEAN-07 chỉ được `DONE` hoàn toàn sau backup, restore test và apply thành công trên từng target environment; không chạy trên database hoặc volume dùng chung.

Verification cleanup: không import/call-site đến code xóa; Python, Node, Flutter tests pass; route/dependency/database/Docker đúng policy.

Run `foundation-parallel-20260716-01` xác nhận retired Node roots trả `404 NOT_FOUND`, không proxy Python; toàn bộ Node suite đạt `97/97` trên PostgreSQL disposable đã migrate và seed. Database Phase B tables vẫn được giữ cho CLEAN-07.

Run `foundation-wave-integration-20260716-02` xác nhận Flutter deep links và FastAPI Phase B endpoints trả fallback/404; Node full đạt `104/104`, CLEAN-07 unit tests chạy trong full suite và disposable schema tests đạt `6/6`. Không database/volume thật nào bị drop.
