# Kiến trúc mục tiêu

```text
Android ML Kit scanner -> JPEG + acquisition metadata -> Node upload -> Python policy
-> full-page text detection once -> spatial line graph -> progressive scheduler
-> selective VietOCR batches -> PhoBERT + post-filter + lookup evidence
-> guarded stop hoặc unresolved fallback -> review thuốc -> lịch uống
```

## Acquisition contract

```text
AcquiredPrescriptionImage(bytes_or_cache_path, filename, mime_type, width, height,
  byte_size, acquisition_source, scanner_mode, scanner_version, scanner_elapsed_ms)
```

`acquisition_source`: `mlkit_document_scanner`, `camerax_fallback`, hoặc `gallery_fallback`.

## Chính sách server

`ImageProcessingPolicy` gồm `use_yolo_crop`, `use_deskew`, `use_orientation`, `detection_max_side`, `recognition_max_side`. Không bỏ stage chỉ dựa trên source ảnh; quyết định đến từ B0/B1/B2/B3 benchmark.

## Progressive OCR

Mỗi `DetectedRegion` giữ ID ổn định, polygon detection/recognition, detector confidence, line ID, state, round/queue reason, parent IDs, text, recognizer confidence và recognition error.

Region states: `DETECTED`, `QUEUED`, `RECOGNIZED`, `EMPTY_TEXT`, `LOW_CONFIDENCE`, `CROP_FAILED`, `FALLBACK_QUEUED`.

Coverage states: `FULL`, `FALLBACK_FULL`, `PROVISIONAL_PARTIAL`, `FAILED`.

Spatial graph được xây từ polygon detection theo `SAME_LINE_LEFT/RIGHT`, `ABOVE_OVERLAP`, `BELOW_OVERLAP`, `NEAREST_VERTICAL`, `SIMILAR_LEFT_MARGIN`, `SAME_Y_BAND`; khoảng cách chuẩn hóa theo median text height.

Seed thử nghiệm: 35%, 50%, 65% chiều cao. Batch benchmark: 4, 8, 12, 16.

Tách riêng detector, recognizer, PhoBERT, layout và lookup confidence. Lookup chỉ là evidence, không xác nhận thuốc hoặc dừng OCR.

Modes: `legacy_full`, `progressive_shadow`, `progressive_exhaustive`, `progressive_guarded`. Mặc định là `legacy_full` đến khi đạt go/no-go.
