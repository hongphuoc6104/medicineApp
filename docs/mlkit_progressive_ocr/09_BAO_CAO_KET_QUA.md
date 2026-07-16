# Báo cáo kết quả

Không chèn ảnh đơn thuốc thật hoặc OCR text có dữ liệu bệnh nhân.

Mỗi run ghi: run ID, thời gian, commit, worktree clean, mode, model hashes, input manifest/hash, CPU/RAM/OS/runtime/thread/debug level; TP/FP/FN, F1, exact match, false-complete, wrong-row; detected/recognized region, reduction, rounds, fallback, failures; stage timing và resource usage.

## Lịch sử run

| Run ID | Commit | Mode | F1 | OCR reduction | Fallback | P50 | P95 | Kết luận |
|---|---|---|---:|---:|---:|---:|---:|---|
| Chưa chạy | | | | | | | | |

## Active wave run registry

Registry này chỉ giữ trạng thái điều phối. Kết quả chỉ được điền sau khi test/run thực sự hoàn thành; `IN_PROGRESS` không phải bằng chứng pass.

| Run ID pattern | Lane | Baseline commit | Trạng thái | Kết quả |
|---|---|---|---|---|
| `wp03b-drug-resolution-20260716-01` | WP-03B safety | `7c66dc5` | PASS | Python safety `16/16`; integrated targeted wave `52/52`; Node regressions trong full suite pass |
| `wp05a-mlkit-bridge-20260716-01` | WP-05A bridge | `7c66dc5` | BLOCKED_ENV | Dart/Kotlin contract pass, ML Kit `16.0.0` resolve; Android build chờ NDK/license |
| `cleanup-mobile-phase-b-20260716-01` | Flutter cleanup | `7c66dc5` | PASS | Retired routes `2/2`; full Flutter `37 pass, 2 baseline fail` |
| `cleanup-fastapi-phase-b-20260716-01` | FastAPI cleanup | `7c66dc5` | PASS | Retired endpoints `2/2`; WP-03A contract pass |
| `clean07-schema-retirement-20260716-01` | CLEAN-07 implementation/disposable verification | `7c66dc5` | IMPLEMENTATION_PASS | Node full `104/104`; disposable schema `6/6`; production chưa apply |
| `wp01-baseline-tooling-20260716-01` | WP-01 tooling/preflight | `7c66dc5` | TOOLING_PASS_PREFLIGHT_BLOCKED | Tooling `20/20`; assets/input hashes pass; approval và pinned clean code run còn thiếu |

## WP-01 baseline registry

| Run ID pattern | Code commit | Dataset split | Trạng thái | Metrics |
|---|---|---|---|---|
| `wp01-approved-main-gpu-<timestamp>` | `a6810a3` | 50 labeled + 120 operational | PENDING_PREFLIGHT | Chưa chạy |
| `wp01-approved-main-cpu-<timestamp>` | `a6810a3` | 50 labeled + 120 operational | PENDING_PREFLIGHT | Chưa chạy |

Mỗi baseline row sau khi chạy phải liên kết manifest/model hashes và provenance. F1/exact match chỉ ghi cho 50 labeled images; 120 operational chỉ ghi success/error/empty/timing. Tracked report không chứa ảnh, OCR text, crop, overlay, URI, filename gốc hoặc absolute home path.

## Integration run `foundation-wave-integration-20260716-02`

```text
Python targeted safety/cleanup/tooling: 52 passed
Python tests/: 40 passed, 2 failed
  - 2 failures: PhoBERT weights absent in clean worktree
  - drug_name_raw regression: resolved
Node full on disposable PostgreSQL 16: 104 passed, 6 CLEAN-07 integration tests skipped by default
CLEAN-07 disposable schema suite: 6 passed
Flutter WP-04/WP-05A/retired routes targeted: 18 passed; targeted analyze clean
Flutter full: 37 passed, 2 existing Home failures
Kotlin contract/API harness: 10 passed; ML Kit 16.0.0 dependency resolved
Android debug build: BLOCKED before compile by missing/unaccepted NDK 28.2.13676358 license
docker compose config --quiet: PASS
git diff --check: PASS
scripts/run_pipeline.py: UNCHANGED
```

WP-01 approved-main CPU/GPU và safe full OCR không chạy trong wave này. Không có ảnh, OCR text, crop, overlay hoặc baseline metrics được commit/ghi giả.

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

Đây là snapshot lịch sử trước WP-03B và wave integration. Các trạng thái/failure ghi dưới đây không mô tả trạng thái hiện tại; xem `foundation-wave-integration-20260716-02` ở trên để biết kết quả mới nhất.

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
