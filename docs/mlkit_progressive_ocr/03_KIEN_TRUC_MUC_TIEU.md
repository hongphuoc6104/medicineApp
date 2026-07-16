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

## Native MethodChannel boundary

WP-05A triển khai `MlKitPrescriptionImageAcquirer` qua một app-owned MethodChannel. Tên channel, method, argument keys, result keys và error codes phải được định nghĩa một lần trong Dart/Kotlin contract constants và khóa bằng contract tests, không rải string literal trong UI hoặc `MainActivity`.

Request contract của WP-05A:

- Một request đang chạy tại một thời điểm; request trùng trả `acquisition_in_progress`.
- Một trang, JPEG và ML Kit `SCANNER_MODE_FULL`.
- Gallery import chỉ bật theo `PrescriptionImageAcquisitionOptions.allowGalleryFallback`.
- ML Kit dependency khóa ở `16.0.0`.

Success contract chỉ trả internal cache path cùng `image/jpeg`, width, height, byte size, source, scanner mode/version và elapsed milliseconds. Native phải copy URI kết quả vào app-internal cache, validate JPEG và giới hạn `10 MB` trước khi trả Dart. `PrescriptionImageAcquirer.release()` quản lý cleanup qua abstraction; ML Kit cache có explicit release và stale cleanup, còn byte/CameraX/gallery không bị native bridge xóa nhầm. Cancel là outcome riêng; unsupported/GMS/error dùng các stable failure code của WP-04. Không log URI, filename gốc, bytes hoặc dữ liệu ảnh.

### Ranh giới WP-05

| Slice | Phạm vi | Không được làm |
|---|---|---|
| WP-05A | Dart adapter, Kotlin bridge/contract, `MainActivity` registration, dependency và contract/build tests | Không nối production screen, không thay CameraX flow, không xóa `image_picker` |
| WP-05B | Device integration, lifecycle/rotation/cancel, production screen selection và fallback UX | Không bắt đầu trước khi WP-05A tests/build pass |

CameraX và gallery contract hiện tại tiếp tục tồn tại làm fallback. WP-05 chỉ `DONE` khi WP-05A và WP-05B đều hoàn thành.

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
