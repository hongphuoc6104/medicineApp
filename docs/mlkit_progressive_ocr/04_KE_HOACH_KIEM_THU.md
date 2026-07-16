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

## Test matrix cho wave song song

| Lane | Test bắt buộc | Acceptance |
|---|---|---|
| WP-03B | Fixture DB nhỏ; `test_drug_lookup_resolution_safety.py`; scan lookup regression; WP-03A Python/Node contract và Node scan tests | Ingredient-only/ambiguous/strength mismatch không `confirmed`; `drug_name_raw`, `ocr_text` và rejected candidates còn đủ |
| WP-05A | Dart MethodChannel tests; Kotlin local contract tests; Gradle dependency resolution; Android debug build | Một request, một trang JPEG/full mode, gallery option, cache copy và 10 MB limit đúng contract; production CameraX chưa đổi |
| Flutter cleanup | `retired_phase_b_routes_test.dart`; targeted analyze; full Flutter suite | Hai deep link Phase B vào fallback/404; không còn pill import; không có failure mới ngoài hai Home baseline failures |
| FastAPI cleanup | `test_retired_fastapi_phase_b_routes.py`; WP-03A `4/4` | Hai endpoint trả 404 và không khởi tạo/gọi AI pipeline; prescription và drug metadata routes còn nguyên |
| CLEAN-07 | Fresh migrate/seed trên PostgreSQL disposable; schema assertion; retirement dry-run/apply/rollback tests | Fresh schema không có bảy bảng; mặc định dry-run; external FK làm rollback; không `CASCADE` |
| WP-01 | Asset locator/harness fake tests; preflight 170 ảnh/model hashes; evaluator privacy tests; CPU/GPU provenance validation | Preflight không import OCR/model packages; 50/120 tách metric; report không có PHI, OCR text hoặc path tuyệt đối |

## Kiểm chứng sau tích hợp

1. Chạy Python targeted safety, retired-route và failure-contract tests.
2. Chạy Python full suite; sau WP-03B lỗi `drug_name_raw` phải hết, model-dependent failures chạy lại với approved assets.
3. Chạy Node full suite trên PostgreSQL disposable đã migrate và seed.
4. Chạy Flutter targeted WP-04/WP-05A/retired routes và full suite; không chấp nhận failure mới ngoài hai Home baseline failures đã ghi.
5. Chạy Kotlin unit tests, dependency resolution và Android debug build.
6. Chạy `docker compose config --quiet`, `git diff --check` và xác nhận `scripts/run_pipeline.py` không đổi.

## Test run log

| Run ID | Commit | Phạm vi | Kết quả |
|---|---|---|---|
| `foundation-parallel-20260716-01` | `9bf03be` | WP-03A, WP-03D, WP-04, Node Phase B ingress cleanup | Python targeted `9/9`; Node `97/97`; Flutter acquirer `5/5`, targeted analyze sạch |
| `foundation-wave-integration-20260716-02` | worktree trên `7c66dc5` | WP-03B, WP-05A, Flutter/FastAPI cleanup, CLEAN-07 implementation, WP-01 tooling | Python targeted `52/52`; Node `104/104` + schema `6/6`; Flutter targeted `18/18`, full `37 pass, 2 baseline fail`; WP-01 `20/20` |

Giới hạn của run: full Python đạt `39 pass, 3 fail` do hai test cần PhoBERT weights không có trong worktree sạch và một assertion `drug_name_raw` thuộc WP-03B. Full Flutter đạt `24 pass, 2 fail` tại `home_screen_test.dart`, ngoài phạm vi WP-04.

Run `foundation-wave-integration-20260716-02`: Python full đạt `40 pass, 2 fail`, cả hai do thiếu `models/phobert_ner_model`; lỗi `drug_name_raw` đã được loại. Kotlin contract/API harness đạt `10/10` và ML Kit `16.0.0` resolve thành công, nhưng Android debug build dừng ở project configuration vì NDK `28.2.13676358` chưa cài/chấp nhận license. WP-01 tooling đạt `20/20`; chưa chạy OCR baseline vì preflight approval chưa đủ.
