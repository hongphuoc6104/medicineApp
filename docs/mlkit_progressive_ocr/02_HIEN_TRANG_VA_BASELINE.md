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

## Baseline cần ghi lại

Mỗi run phải lưu commit, trạng thái worktree, hash/phiên bản YOLO-Paddle-VietOCR-PhoBERT, môi trường CPU/runtime, manifest SHA-256 của input, timing cold/warm P50/P90/P95 theo stage, TP/FP/FN/F1, region OCR, false-complete và wrong-row ownership.

Hai baseline bắt buộc:

1. `approved_main`: hành vi đúng `main@a6810a3`.
2. `safe_full_ocr`: full OCR sau khi sửa mock/error/contract/resolution/evaluator. Đây là đối chứng cho tối ưu CPU.

| Run ID | Commit | Mode | Images | TP | FP | FN | F1 | P50 | P95 | Ghi chú |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Chưa chạy | | approved_main | | | | | | | | |
| Chưa chạy | | safe_full_ocr | | | | | | | | |
