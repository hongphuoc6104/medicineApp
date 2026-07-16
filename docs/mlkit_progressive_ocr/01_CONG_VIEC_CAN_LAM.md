# Công việc cần làm

## 1. Mục tiêu

Nâng cấp luồng quét đơn thuốc để:

- Chuẩn hóa ảnh đầu vào trên Android bằng Google ML Kit Document Scanner.
- Giảm số vùng phải chạy VietOCR recognition bằng Progressive Spatial OCR.
- Chạy toàn bộ AI server trên CPU, không phụ thuộc CUDA.
- Giữ hoặc cải thiện recall tên thuốc so với full-page OCR hiện tại.
- Có fallback rõ ràng, không trả kết quả partial như kết quả hoàn chỉnh.
- Có đầy đủ trace để kiểm tra từng bước, debug lỗi và đối chiếu A/B/C.
- Xóa Phase B và dead code không liên quan đến luồng quét đơn thuốc thật sự.
- Giữ tài liệu, training, evaluation và model provenance cần cho khả năng tái lập.

## 2. Phạm vi

### Trong phạm vi

- Flutter Android prescription capture.
- Native Android bridge cho ML Kit Document Scanner.
- Metadata nguồn ảnh từ mobile qua Node đến Python.
- CPU-only Python prescription pipeline.
- Paddle text detection toàn trang.
- VietOCR recognition có chọn lọc theo không gian.
- PhoBERT NER, post-filter và DrugLookup.
- Error contract giữa Python, Node và mobile.
- Debug artifact, benchmark và regression test.
- Cleanup code xác minh viên thuốc và các thành phần không còn call-site.

### Ngoài phạm vi hiện tại

- OCR hoàn toàn trên điện thoại.
- iOS document scanner.
- Nhận dạng viên thuốc hoặc xác minh liều bằng hình ảnh.
- Tự động chấp nhận thuốc mà không qua màn hình review.
- Xóa YOLO, deskew hoặc orientation trước khi có benchmark ML Kit.
- Thay PhoBERT/VietOCR bằng model mới trước khi tối ưu batching, quantization và runtime.

## 3. Nguyên tắc bắt buộc

1. Baseline triển khai là `main@a6810a392c97593f073a9c5e2b8dfc47027c1911`.
2. Không làm mất hoặc ghi đè worktree thử nghiệm hiện tại.
3. Không cherry-pick nguyên commit thử nghiệm có nhiều concern không liên quan.
4. Tính năng mới phải có test riêng trước khi tích hợp.
5. Không thay thế logic mặc định của `scripts/run_pipeline.py`; chỉ được tích hợp theo hướng bổ sung có flag sau khi test đạt.
6. Không xóa fallback xử lý ảnh server trước khi benchmark chứng minh có thể bỏ.
7. Không dùng fuzzy lookup làm bằng chứng duy nhất để dừng OCR hoặc xác nhận thuốc.
8. Không ghi ảnh đơn thuốc thật và OCR text nhạy cảm vào log production.

## 4. Work packages

| ID | Công việc | Trạng thái | Phụ thuộc | Bằng chứng hoàn thành |
|---|---|---|---|---|
| WP-00 | Tạo baseline sạch từ GitHub `main` | DONE | Không | Branch/worktree `feature/mlkit-progressive-ocr-foundation` từ `a6810a3` |
| WP-01 | Chụp approved-main baseline CPU và GPU | IN_PROGRESS | WP-00 | Cả hai run có manifest, hashes và provenance đầy đủ |
| WP-02 | Cleanup Phase B và dead code chắc chắn | IN_PROGRESS | WP-00 | Call-site audit và test không regression |
| WP-03 | Sửa error/API/drug resolution contract | IN_PROGRESS | WP-00 | WP-03A/B/D đã đạt; WP-03C còn lại |
| WP-04 | Tạo abstraction lấy ảnh prescription trên mobile | DONE | WP-00 | Pure-Dart contract và 5 fake-acquirer tests pass |
| WP-05 | Tích hợp ML Kit Document Scanner | IN_PROGRESS | WP-04 | WP-05A bridge và WP-05B device integration đều đạt |
| WP-06 | Thêm metadata nguồn ảnh và debug mobile | TODO | WP-05 | Metadata tới được Python, không log PHI |
| WP-07 | Benchmark đầu ra ML Kit với pipeline cũ | TODO | WP-05, WP-06 | Bảng ablation YOLO/preprocess |
| WP-08 | Tạo contract Progressive Spatial OCR | TODO | WP-03 | Contract/state tests pass |
| WP-09 | Tạo spatial line graph và seed scheduler | TODO | WP-08 | Geometry tests pass ở nhiều độ phân giải |
| WP-10 | Selective VietOCR batching và cache | TODO | WP-09 | Không OCR trùng region, batching tests pass |
| WP-11 | SEARCH và MEDICATION_CLUSTER state machine | TODO | WP-10 | Expansion/fallback tests pass |
| WP-12 | Batch và tối ưu PhoBERT CPU | TODO | WP-03 | Output tương đương và timing tốt hơn |
| WP-13 | Thêm mode `shadow` và `exhaustive` | TODO | WP-11 | Không thay đổi kết quả baseline |
| WP-14 | Thêm mode `guarded` | TODO | WP-13 | Không có false-complete trong test |
| WP-15 | Tích hợp API sau feature flag | TODO | WP-14 | End-to-end Python-Node-mobile pass |
| WP-16 | Benchmark A/B/C và CPU optimization | TODO | WP-07, WP-15 | Báo cáo correctness và P50/P95 |
| WP-17 | Quyết định giữ/xóa YOLO và preprocess | TODO | WP-16 | Decision log có bằng chứng |
| WP-18 | Cleanup cuối và cập nhật tài liệu | TODO | WP-17 | Không còn dead call-site, docs khớp code |

### Trạng thái work package đang tách lát cắt

| ID | Trạng thái | Phạm vi | Điều kiện chuyển trạng thái |
|---|---|---|---|
| WP-01A | DONE | Asset locator no-copy, approval-gated harness, evaluator và provenance capture | Tooling tests `20/20`; preflight không import OCR/model package |
| WP-01B | PENDING_PREFLIGHT | Approved-main GPU baseline tại đúng `a6810a3` | Run `wp01-approved-main-gpu-<timestamp>` có đủ provenance |
| WP-01C | PENDING_PREFLIGHT | Approved-main CPU-forced baseline tại đúng `a6810a3` | Run `wp01-approved-main-cpu-<timestamp>` có đủ provenance |
| WP-03A | DONE | Python/Node failure contract; không mock hoặc persist scan lỗi | Targeted contract tests đã pass |
| WP-03B | DONE | An toàn brand/ingredient/strength và raw candidate | Safety/regression/Node scan tests pass; không đổi protected CLI |
| WP-03C | TODO | Row ownership và source-region provenance | Đã được mở sau WP-03B; chưa triển khai |
| WP-03D | DONE | Prediction ngoài alias được tính là false positive | Evaluator targeted tests đã pass |
| WP-05A | BLOCKED_ENV | Native MethodChannel bridge dormant, chưa nối production UI | Dart/Kotlin contract đạt; Android debug build chờ NDK/license |
| WP-05B | TODO | Device integration và nối screen production | Chờ WP-05A; CameraX vẫn là production flow/fallback |

## 5. Cleanup tracking

| ID | Trạng thái | Công việc |
|---|---|---|
| CLEAN-01 | DONE | Archive tài liệu `main` ra ngoài repository |
| CLEAN-02 | DONE | Xóa generated output images, giữ reports |
| CLEAN-03 | DONE | Dọn Flutter/Node/Python cache |
| CLEAN-04 | DONE | Thêm root `.dockerignore` |
| CLEAN-05 | DONE | Xóa `core/shared` visualizer/init/README không có call-site; `zero_pima_loader.py` chờ Python Phase B cleanup |
| CLEAN-06 | IN_PROGRESS | Node, Flutter và FastAPI ingress đã xong; Python core/Zero-PIMA cleanup chưa triển khai |
| CLEAN-07 | IN_PROGRESS | Implementation và disposable verification đã xong; production retirement chờ backup/restore/apply từng môi trường |
| CLEAN-08 | TODO | Kiểm tra fresh install sau dependency cleanup |

## 6. Wave thực thi song song

Tất cả lane tạo từ `7c66dc5`. Worker không chỉnh tracker, ADR hoặc run log chung; coordinator cập nhật tài liệu sau khi merge.

| Lane | Branch đề xuất | Công việc | Trạng thái |
|---|---|---|---|
| A | `work/wp03b-drug-resolution` | WP-03B brand/ingredient/strength safety | DONE |
| B | `work/wp05a-mlkit-bridge` | WP-05A native bridge dormant | BLOCKED_ENV |
| C | `work/cleanup-mobile-phase-b` | Flutter Phase B và deep-link cleanup | DONE |
| D | `work/cleanup-fastapi-phase-b` | FastAPI Phase B endpoint cleanup | DONE |
| E | `work/clean07-schema-retirement` | Fresh schema và retirement tool an toàn | IMPLEMENTATION_DONE |
| F | `work/wp01-baseline-tooling` | WP-01 locator, harness và provenance | TOOLING_DONE_PREFLIGHT_BLOCKED |

Không chạy song song các phần phụ thuộc sau:

- WP-03C và Python core Phase B cleanup đã được mở sau WP-03B nhưng chưa bắt đầu.
- WP-05B chờ WP-05A; WP-06 chờ toàn bộ WP-05.
- WP-08 và WP-12 chờ WP-03B/C.
- Safe full OCR baseline chờ WP-03B/C; hai approved-main run của WP-01 vẫn chạy đúng `a6810a3`.
- Drop bảng trên database thật chờ backup, restore test và deployment ingress cleanup.

## 7. Thứ tự triển khai

### Giai đoạn A: Khóa baseline và an toàn

- [x] Hoàn thành WP-00.
- [ ] Hoàn thành WP-01.
- [ ] Hoàn thành WP-02 bằng một change set riêng.
- [ ] Hoàn thành WP-03 trước khi dùng bộ lọc thuốc làm tín hiệu progressive stop.
- [x] Sửa evaluator để prediction ngoài alias không bị bỏ qua khi tính FP.

### Giai đoạn B: ML Kit Document Scanner

- [x] Hoàn thành WP-04.
- [ ] Hoàn thành WP-05 với `SCANNER_MODE_FULL`, JPEG, một trang và gallery import.
- [ ] Giữ CameraX làm fallback trong giai đoạn thử nghiệm.
- [ ] Chạy quality gate ML Kit ở chế độ observe-only trước khi hiệu chỉnh threshold.
- [ ] Hoàn thành WP-06 và WP-07.

### Giai đoạn C: Progressive Spatial OCR

- [ ] Hoàn thành contract và test WP-08 trước khi viết integration.
- [ ] Hoàn thành graph và scheduler WP-09.
- [ ] Hoàn thành batching/cache WP-10.
- [ ] Hoàn thành state machine WP-11.
- [ ] Hoàn thành CPU NER WP-12.
- [ ] Chứng minh mode `exhaustive` tương đương full OCR trong WP-13.
- [ ] Chỉ mở early stop sau khi WP-14 không có false-complete.

### Giai đoạn D: Tích hợp và quyết định cleanup

- [ ] Hoàn thành WP-15 sau feature flag mặc định tắt.
- [ ] Hoàn thành benchmark WP-16.
- [ ] Ghi quyết định giữ/xóa các stage cũ trong WP-17.
- [ ] Hoàn thành cleanup và tài liệu WP-18.

## 8. Mục tiêu CPU ban đầu

Các giá trị dưới đây là tiêu chí thử nghiệm, không phải kết quả đã đạt:

| Chỉ số | Mục tiêu |
|---|---:|
| Server warm P50 | `<= 4 giây` |
| Server warm P95 | `<= 8 giây` |
| OCR reduction | `>= 50%` |
| Full OCR fallback | `<= 25%` |
| FN mới so với safe full OCR | `0` |
| False-complete | `0` |
| Wrong row ownership | `0` |

## 9. Điều kiện hoàn thành dự án nâng cấp

- [ ] ML Kit có fallback cho thiết bị không hỗ trợ hoặc thiếu Google Play services.
- [ ] Pipeline chạy với CPU-only dependencies.
- [ ] Không load hoặc yêu cầu CUDA.
- [ ] Mỗi stage có timing và trạng thái lỗi rõ ràng.
- [ ] Progressive OCR không nhận dạng lại region đã cache.
- [ ] Partial result luôn có trạng thái `PROVISIONAL_PARTIAL`.
- [ ] Python, Node và mobile dùng cùng một scan response contract.
- [ ] Không còn mock medication.
- [ ] Không còn Phase B trong production route hoặc UI.
- [ ] Benchmark và kết luận cleanup được ghi trong thư mục tài liệu này.
