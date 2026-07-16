# Debug và quan sát

Debug level: `off` chỉ status/tổng latency; `metadata` có timing/count/state không ảnh/text; `full` chỉ local được kiểm soát với JSON trace, overlay, text. Không benchmark latency chính bằng `full`.

Mỗi scan dùng `request_id` xuyên suốt mobile, Node, Python, artifact, database và benchmark. Không dùng filename người dùng làm ID duy nhất.

Progressive artifacts: detected regions, spatial lines, neighbor graph, rounds, recognized regions, final blocks, selection overlay và metrics. Trace round phải ghi queue/reason/batch, region recognized/candidate/frontier, timing và fallback decision.

Timing: scanner, upload, decode, YOLO, deskew, orientation, detection, graph, VietOCR, NER, lookup, controller, serialization, server/end-to-end total.

Debug một ảnh: xác nhận manifest, metadata, transform frame, coverage region, graph/seed, OCR rounds, PhoBERT/post-filter, lookup/strength, stop/fallback và full OCR comparison.

Không commit ảnh đơn thật, OCR text, crop, temporary scanner JPEG hoặc overlay. Không log OCR text production. Full debug chỉ dùng synthetic hoặc dữ liệu đã được phê duyệt, chỉ lưu trong thư mục local đã được ignore như `debug/`, không dùng filename/path gốc làm tracked metadata và không benchmark latency chính bằng artifact này.

Mỗi full-debug run phải ghi local-only owner, mục đích, thời điểm tạo và hạn xóa. Hạn giữ phải được chốt ở WP-01 preflight; policy khuyến nghị là xóa ngay sau khi aggregate report được duyệt. Aggregate report chỉ được commit sau privacy scan, phải dùng image ID ẩn danh và không chứa URI, absolute home path hoặc nội dung OCR.

Theo dõi: generic map sai biệt dược, wrong row ownership, OCR empty `IMG_180633`, confidence `1.0`, và Python error thành Node scan `GOOD`.
