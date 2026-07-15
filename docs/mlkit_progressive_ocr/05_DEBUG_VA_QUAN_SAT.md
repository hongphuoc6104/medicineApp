# Debug và quan sát

Debug level: `off` chỉ status/tổng latency; `metadata` có timing/count/state không ảnh/text; `full` chỉ local được kiểm soát với JSON trace, overlay, text. Không benchmark latency chính bằng `full`.

Mỗi scan dùng `request_id` xuyên suốt mobile, Node, Python, artifact, database và benchmark. Không dùng filename người dùng làm ID duy nhất.

Progressive artifacts: detected regions, spatial lines, neighbor graph, rounds, recognized regions, final blocks, selection overlay và metrics. Trace round phải ghi queue/reason/batch, region recognized/candidate/frontier, timing và fallback decision.

Timing: scanner, upload, decode, YOLO, deskew, orientation, detection, graph, VietOCR, NER, lookup, controller, serialization, server/end-to-end total.

Debug một ảnh: xác nhận manifest, metadata, transform frame, coverage region, graph/seed, OCR rounds, PhoBERT/post-filter, lookup/strength, stop/fallback và full OCR comparison.

Không commit ảnh đơn thật, không log OCR text production. Full debug chỉ dùng synthetic hoặc dữ liệu có quyền; cache phải có TTL/cleanup.

Theo dõi: generic map sai biệt dược, wrong row ownership, OCR empty `IMG_180633`, confidence `1.0`, và Python error thành Node scan `GOOD`.
