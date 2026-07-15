# Báo cáo kết quả

Không chèn ảnh đơn thuốc thật hoặc OCR text có dữ liệu bệnh nhân.

Mỗi run ghi: run ID, thời gian, commit, worktree clean, mode, model hashes, input manifest/hash, CPU/RAM/OS/runtime/thread/debug level; TP/FP/FN, F1, exact match, false-complete, wrong-row; detected/recognized region, reduction, rounds, fallback, failures; stage timing và resource usage.

## Lịch sử run

| Run ID | Commit | Mode | F1 | OCR reduction | Fallback | P50 | P95 | Kết luận |
|---|---|---|---:|---:|---:|---:|---:|---|
| Chưa chạy | | | | | | | | |

## Cleanup run `cleanup-20260715-01`

| Mục | Trước | Sau | Kết quả |
|---|---:|---:|---|
| Worktree không tính `.git` | Khoảng 25 GB | 17 GB | Giảm khoảng 8 GB |
| `data/output` | 7,8 GB | 25 MB | Giữ report, xóa ảnh generated |
| Output image files | 3.105 | 0 | Đã xóa |
| Output JSON/JSONL/CSV/TXT | 3.130 | 3.130 | Giữ nguyên |
| Mobile generated | Khoảng 260 MB | Đã dọn | Có thể tái tạo |
| `server-node/node_modules` | 57 MB | Đã dọn | `npm ci` tái tạo |
| `venv` | 13 GB | 13 GB | Giữ rollback |
| Models | 564 MB | 564 MB | Giữ runtime |

Archive: `/home/hongphuoc/Desktop/KHMT-2025-2026/NienLuanNganh/medicineApp-archive/2026-07-15-pre-cleanup/`; baseline `a6810a3`; 83 files; SHA-256 `66f2f1c8ccb3fd7fabd9d7ec5511fb4f6a476c14a930861340f0cb2c07c97330`.

Verification: 19 targeted Python tests pass; prescription-only and retired-route assertions pass; `docker compose config --quiet` and `git diff --check` pass. Baseline full OCR must be rerun with complete provenance.

## Foundation run `foundation-parallel-20260716-01`

| Mục | Giá trị |
|---|---|
| Commit được kiểm tra | `9bf03be` |
| Branch | `feature/mlkit-progressive-ocr-foundation` |
| Phạm vi | WP-03A, WP-03D, WP-04, Node Phase B ingress cleanup |
| Python runtime | Venv hiện có Python 3.10; worktree sạch chưa có venv riêng |
| Node database | PostgreSQL 16 disposable, schema migrate mới, seed 9.227 thuốc |
| Dữ liệu đơn thuốc/model | Không chạy; WP-01 vẫn blocked |

Kết quả:

```text
Python targeted safety/cleanup tests: 9 passed
Python tests/: 39 passed, 3 failed
  - 2 failures: PhoBERT weights absent in clean worktree
  - 1 failure: drug_name_raw contract pending WP-03B
Node full suite: 12 suites, 97 tests passed
Flutter WP-04 targeted: 5 tests passed; targeted analyze no issues
Flutter full suite: 24 passed, 2 failed in existing home_screen_test.dart
docker compose config --quiet: PASS
git diff --check: PASS
```

Thay đổi hành vi chính:

- FastAPI không còn trả mock medication khi pipeline unavailable.
- Node giữ HTTP status/error code từ Python và không persist mock/error result.
- Evaluator tính prediction ngoài alias là false positive và lưu adjudication evidence.
- Mobile có contract thuần Dart cho ML Kit, CameraX và gallery acquisition outcomes.
- Node Phase B ingress, orphan gitlink và legacy Zero-PIMA `drug_mapper` đã được retire.

Chưa kết luận correctness/latency OCR vì chưa chạy approved input/model manifest.
