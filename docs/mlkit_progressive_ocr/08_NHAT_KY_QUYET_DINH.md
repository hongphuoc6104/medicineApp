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
| ADR-009 | ACCEPTED | Scan failure dùng HTTP/code rõ ràng: unavailable `503`, execution failed `500`, processing failed `422`; Node không persist mock/error |
| ADR-010 | ACCEPTED | Prediction không khớp alias được giữ để adjudication, tính FP và làm `exact_match=false` |
| ADR-011 | ACCEPTED | WP-01 dùng đủ 170 ảnh: 50 labeled tính correctness, 120 operational chỉ tính vận hành/timing; chạy approved-main CPU và GPU riêng tại đúng `a6810a3` với cùng manifest/evaluator/seed/thread policy |
| ADR-012 | ACCEPTED | Asset WP-01 được tham chiếu read-only qua locator, không copy/symlink vào worktree; full debug chỉ local trong thư mục ignored, có hạn xóa và không commit ảnh/OCR/crop/overlay |
| ADR-013 | ACCEPTED | WP-05A dùng app-owned MethodChannel với contract Dart/Kotlin khóa bằng test: một trang JPEG, `SCANNER_MODE_FULL`, gallery theo options, single-flight, internal-cache copy và giới hạn 10 MB; production UI chờ WP-05B |
| ADR-014 | ACCEPTED | CLEAN-07 tách fresh-schema cleanup khỏi retirement script; script mặc định dry-run, apply cần database/backup confirmation, transaction, advisory lock, không `CASCADE`, rollback khi có external FK |
| ADR-015 | ACCEPTED | Chỉ exact unambiguous brand với strength đầy đủ, không mâu thuẫn mới được `confirmed`; product identity dùng registration/strength để không gộp hai hàm lượng cùng brand |
| ADR-016 | ACCEPTED | CLEAN-07 apply bind vào PostgreSQL `system_identifier` cùng database/user/transport/server/port; không lấy được system identifier thì fail closed |
| ADR-017 | ACCEPTED | WP-01 approval bind đúng manifest hash và split 50/120; receipt/report bind worker/tooling/evaluator/model/input hashes, exact repetitions, cold initialization + first inference, warm stage timing và resource metrics |

Mẫu: ngày, trạng thái (`PROPOSED|ACCEPTED|SUPERSEDED|REJECTED`), quyết định, lý do, bằng chứng, hệ quả và ADR thay thế.
