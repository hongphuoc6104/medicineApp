# Hiện trạng và baseline

## Trạng thái Git đã xác nhận

| Mục | Giá trị |
|---|---|
| Repository | `hongphuoc6104/medicineApp` |
| Baseline chính thức | `main@a6810a392c97593f073a9c5e2b8dfc47027c1911` |
| Worktree thử nghiệm | `experiment/model-testing-2026-06-05` tại `ec1720d` |
| Worktree triển khai | `feature/mlkit-progressive-ocr-foundation` từ `a6810a3` |

Không dùng worktree thử nghiệm làm baseline và không đưa các xóa tài liệu hỗn hợp sang branch triển khai.

## Pipeline production hiện tại

```text
Mobile CameraX -> Node POST /api/scan -> Python POST /api/scan-prescription
-> YOLO crop -> deskew + PP-LCNet orientation -> Paddle detection
-> full VietOCR -> raw/grouped PhoBERT -> DrugLookup -> Node persistence -> mobile review
```

## Vấn đề cần xử lý

| Khu vực | Tác động |
|---|---|
| Mobile capture | CameraX chưa chuẩn hóa tài liệu |
| OCR | VietOCR chạy toàn bộ region; confidence đang là `1.0` |
| NER/layout | Có thể gán quantity/usage sang hàng thuốc khác |
| Lookup | Generic có thể trả biệt dược không an toàn |
| Error contract | Có mock medication và lỗi HTTP 200 |
| Evaluator | Có thể bỏ prediction ngoài alias khi tính FP |

## Phạm vi dữ liệu WP-01

WP-01 dùng một manifest duy nhất gồm đủ 170 ảnh đã chốt phạm vi. Việc chạy vẫn bị chặn đến khi approval thực thi và privacy approval được ghi cho đúng SHA-256 manifest này, đồng thời có debug-retention deadline:

| Nhóm | Số ảnh | Chỉ số được phép tính |
|---|---:|---|
| Labeled | 50 | TP, FP, FN, micro/macro F1, exact set match và lỗi mapping |
| Operational | 120 | Success, error, empty result, cold/warm timing và lỗi vận hành; không tính F1 |

Trước khi chạy phải xác nhận 170 ảnh được phép dùng và không để thông tin bệnh nhân thật xuất hiện trong tracked artifact. Input và model được tham chiếu read-only bằng asset locator từ vị trí đã duyệt; không copy hoặc symlink asset vào worktree sạch và không ghi absolute home path vào manifest/requirements.

## Approved-main baseline protocol

Mỗi run phải dùng code đúng `main@a6810a392c97593f073a9c5e2b8dfc47027c1911` và lưu commit, trạng thái worktree, SHA-256 input manifest, SHA-256/phiên bản YOLO-Paddle-VietOCR-PhoBERT, OS/runtime/hardware/thread policy, seed, evaluator version, debug level và timing cold/warm P50/P90/P95 theo stage.

Chạy hai process tách biệt với cùng manifest, evaluator, seed và thread policy:

1. `wp01-approved-main-gpu-<timestamp>`: GPU baseline.
2. `wp01-approved-main-cpu-<timestamp>`: CPU-forced baseline; phải chứng minh process không dùng CUDA.

Full debug chỉ được lưu local trong thư mục ignored và có hạn xóa. Tracked report chỉ chứa aggregate metrics, hashes, provenance và image ID đã ẩn danh; không chứa ảnh, OCR text, crop hoặc overlay.

## Baseline tracking

| Run ID | Commit | Runtime | Labeled | Operational | F1 | Exact match | P50 | P95 | Trạng thái |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| `wp01-approved-main-gpu-<timestamp>` | `a6810a3` | GPU | 50 | 120 | Chưa chạy | Chưa chạy | Chưa chạy | Chưa chạy | PENDING_PREFLIGHT |
| `wp01-approved-main-cpu-<timestamp>` | `a6810a3` | CPU-forced | 50 | 120 | Chưa chạy | Chưa chạy | Chưa chạy | Chưa chạy | PENDING_PREFLIGHT |
| `safe-full-ocr-<timestamp>` | Chưa chốt | CPU target | 50 | 120 | Chưa chạy | Chưa chạy | Chưa chạy | Chưa chạy | BLOCKED_BY_WP03B_WP03C |

WP-01A tooling đã đạt `20/20` tests và xác minh asset/input hashes, explicit model binding, exact 170-record coverage, cold-init/warm timing, worker/evaluator hashes và privacy-safe aggregate report. Hai approved-main run vẫn `PENDING_PREFLIGHT` vì chưa có approval file bind đúng manifest, privacy approval và debug-retention deadline; không có CPU/GPU metrics nào được ghi.

`safe_full_ocr` là full OCR sau khi hoàn tất mock/error/contract/resolution/evaluator và row ownership. WP-03B đã xong nhưng WP-03C chưa triển khai, nên safe full OCR vẫn bị chặn bởi WP-03C.
