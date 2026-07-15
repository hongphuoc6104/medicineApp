# Benchmark và đối chiếu

| Mã | Luồng |
|---|---|
| A | CameraX/raw image -> safe full OCR server |
| B | ML Kit JPEG -> safe full OCR server |
| C | ML Kit JPEG -> Progressive Spatial OCR guarded |

## ML Kit server ablation

| Mã | YOLO | Deskew | Orientation |
|---|---|---|---|
| B0 | On | On | On |
| B1 | Off | On | On |
| B2 | On | Off | Off |
| B3 | Off | Off | Off |

Chỉ xóa stage khi cấu hình không có stage đó không giảm correctness và tốt hơn CPU latency.

Progressive ablation: C0 shadow, C1 progressive order/exhaustive coverage, C2 guarded với unresolved fallback, C3 thêm batch/quantized PhoBERT, C4 thêm ONNX/OpenVINO OCR nếu cần.

Đo TP/FP/FN, micro/macro F1, exact set match, template recall, wrong-row, false-complete, mapping states; prediction không khớp alias phải là FP hoặc vào adjudication queue. Đo detected/recognized region, OCR reduction, source-region recall, CER/WER, empty/crop/low confidence. `OCR reduction = 1 - recognized_regions / total_detected_regions`.

Fairness: cùng manifest/model, warm-up rõ ràng, cold process mới, interleave fixed seed, ít nhất ba warm run mỗi ảnh, không full debug, ghi CPU/load/thread và tách scanner latency.

Go/no-go: ML Kit không recall regression; C1 equivalent full OCR; C2 không FN mới, false-complete/wrong-row bằng 0; OCR reduction >= 50%, fallback <= 25%; CPU warm P50 <= 4s và P95 <= 8s, không CUDA.

| Run ID | Mode | F1 | Exact match | OCR reduction | Fallback | P50 | P95 | Kết luận |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Chưa chạy | A | | | 0% | 100% full | | | |
| Chưa chạy | B | | | 0% | 100% full | | | |
| Chưa chạy | C | | | | | | | |
