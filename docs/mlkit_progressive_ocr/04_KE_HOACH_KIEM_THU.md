# Kế hoạch kiểm thử

Mỗi tính năng có test độc lập trước integration; ưu tiên fake detector/recognizer không tải model.

## Mobile

- `prescription_image_acquirer_test.dart`: success, cancel, unsupported, failure.
- `document_scanner_test.dart`: option mapping, duplicate launch.
- `scan_camera_screen_test.dart`: fallback, lifecycle, stale result.
- `scan_repository_test.dart`: multipart JPEG, metadata, timeout, error mapping.

Kiểm tra ML Kit JPEG, cancel, thiếu GMS, duplicate launch, rotate/background, file quá 10 MB, cache bị xóa, CameraX fallback và retake không bị stale overwrite.

## Progressive OCR pure tests

- `test_progressive_spatial_ocr_contract.py`
- `test_progressive_spatial_ocr_geometry.py`
- `test_progressive_spatial_ocr_expansion.py`
- `test_progressive_spatial_ocr_batching.py`
- `test_progressive_spatial_ocr_confidence.py`
- `test_progressive_spatial_ocr_downstream_equivalence.py`
- `test_progressive_spatial_ocr_flag_isolation.py`

Layout coverage gồm bảng có/thiếu STT, free-text, tên tách box, quantity bên phải, usage lơ lửng, đầu/cuối trang, seed miss, low confidence và crop error.

## Safety regression

- Không mock medication khi model lỗi.
- OCR rỗng không là scan `GOOD`.
- Generic không tự biến thành biệt dược; strength không tương thích không `confirmed`.
- Không gán usage giữa Loratadine và Paracetamol.
- `PROVISIONAL_PARTIAL` không là complete; lookup-only không là medication.
- Mỗi medication giữ `source_region_ids`.

Integration chain: Flutter fake scanner -> Node multipart -> Python fake/full pipeline -> canonical response -> mobile review. Python HTTP error phải được Node giữ nguyên; Node không chấp nhận `mock: true`.

## Test run log

| Run ID | Commit | Phạm vi | Kết quả |
|---|---|---|---|
| `foundation-parallel-20260716-01` | `9bf03be` | WP-03A, WP-03D, WP-04, Node Phase B ingress cleanup | Python targeted `9/9`; Node `97/97`; Flutter acquirer `5/5`, targeted analyze sạch |

Giới hạn của run: full Python đạt `39 pass, 3 fail` do hai test cần PhoBERT weights không có trong worktree sạch và một assertion `drug_name_raw` thuộc WP-03B. Full Flutter đạt `24 pass, 2 fail` tại `home_screen_test.dart`, ngoài phạm vi WP-04.
