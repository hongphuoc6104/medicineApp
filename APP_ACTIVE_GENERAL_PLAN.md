# Active General Plan

> Nguồn ưu tiên cho kế hoạch phát triển hiện tại của repo.
> File này thay thế các board và plan tạm thời rời rạc ở root.
> Quy tắc thực thi xem tại `APP_ACTIVE_DETAILED_PLAN.md`.
> Release gate và test matrix xem tại `docs/UONG_THUOC_FULL_TEST_PLAN.md`.

## 1. Mục tiêu sản phẩm hiện tại

Biến repo này từ một bản clone mạnh về engine thành một app nhắc uống thuốc có vòng lặp giá trị rõ ràng cho người dùng:

- `quét đơn -> review -> tạo lịch -> nhắc uống -> xác nhận -> lịch sử`
- reminder phải phản ánh đúng trạng thái thật của dữ liệu
- scan phải trở thành user journey chính, không chỉ là capability phụ
- AI phải giúp giảm nhập tay, tăng độ chắc và tăng an toàn, không tự động hóa mù quáng

## 2. Phạm vi đã khóa

1. Phase A vẫn là trọng tâm giao sản phẩm.
2. `Local notification` vẫn là lớp reminder chính; push/server-driven chỉ là bước sau.
3. Mọi cải tiến AI ưu tiên tận dụng các thành phần đã có: OCR, NER, drug lookup, drug metadata, scan session, review signals.
4. Phase B chỉ đi theo hướng `assisted verification`, không đẩy lên thành epic chính khi flow core chưa kín.
5. Tài liệu active ở root chỉ giữ những file thật sự phục vụ phát triển hiện tại; không duy trì nhiều plan song song cho cùng một việc.

## 3. Luồng sản phẩm đích

### 3.1 Luồng chính

`Quét đơn -> Review danh sách thuốc -> Tạo draft plan -> Cảnh báo an toàn cần thiết -> Lưu lịch -> Nhắc uống -> Đã uống/Bỏ qua/Nhắc lại -> History`

### 3.2 Luồng lặp lại hằng ngày

`Home hôm nay -> Notification -> Ghi nhận liều -> Sync -> Analytics/History -> Reuse plan nếu cần`

### 3.3 Luồng hỗ trợ

`Scan history -> Mở lại kết quả cũ -> Sửa -> Tạo plan lại`

## 4. Trục phát triển chính

### A. Reminder Core Truthfulness

Mục tiêu:

- app không được báo thành công giả khi mới chỉ queue offline
- auth/session phải sạch và dễ hiểu
- plan, today schedule và notification phải đồng bộ chặt
- Home phải phản ánh đúng `không có liều`, `đã xử lý hết`, `đang chờ xử lý`, `missed`

Giá trị cho user:

- dùng app hằng ngày mà không mất niềm tin vào trạng thái uống thuốc

### B. Scan As Primary Journey

Mục tiêu:

- đưa scan lên flow chính của sản phẩm
- làm camera guidance, reject/warning/retry rõ ràng
- giữ nguyên dữ liệu scan thật qua review, history, reuse
- productize `scan history` và `reopen/recreate plan`
- mở đường cho multi-shot scan dựa trên session API đã có

Giá trị cho user:

- quét đơn thuốc trở thành cách nhanh nhất để bắt đầu dùng app

### C. AI-Assisted Safety And Less Manual Input

Mục tiêu:

- review scoring tốt hơn từ `confidence`, `matchScore`, `qualityState`, `frequency`
- cảnh báo trùng hoạt chất và tương tác thuốc trước khi lưu plan
- enrichment card cho thuốc sau scan hoặc trước khi lưu
- correction memory theo user để lần sau gợi ý tốt hơn
- auto-create `draft plan` từ scan theo kiểu gợi ý, không auto-save

Giá trị cho user:

- AI giúp tiết kiệm thao tác và giảm rủi ro, thay vì chỉ đọc ra tên thuốc

### C1. Medication Safety Expansion

Build focus mới được chốt thêm trên nền scan + plan + drug metadata hiện có:

- `canonical medication snapshot` dùng chung cho scan result, active plan và dispensed package scan
- `medication reconciliation engine` để so sánh toa mới với toa cũ hoặc kế hoạch đang dùng
- `transition-of-care safety mode` để render checklist/risk cards từ kết quả reconciliation
- `prescription -> dispensed reconciliation` bản text-first dựa trên OCR bao bì/nhãn/hộp thuốc có text rõ

Ràng buộc v1:

- không cố suy luận sâu `instruction / quantity / unit`
- chỉ so sánh chắc tay theo `tên`, `hoạt chất`, `strength nếu có`, `dosage form nếu có`
- không làm loose-pill identification hoặc open-world pill recognition trong nhánh này

### D. Adherence And History Depth

Mục tiêu:

- biến `History` từ nơi xem dữ liệu cũ thành nơi tạo giá trị lặp lại
- thêm adherence summary, weekly trend, missed/taken/skipped breakdown, reuse plan thông minh hơn

Giá trị cho user:

- thấy được tiến độ điều trị và quay lại app thường xuyên hơn

### E. Assisted Pill Verification

Mục tiêu:

- chỉ mở rộng theo hướng `reference-based`, gắn với liều cụ thể trong ngày
- nếu chưa có ảnh mẫu thì mời chụp mẫu
- nếu verify không chắc, luôn có manual path rõ ràng

Giá trị cho user:

- tăng an tâm ở những liều quan trọng mà không làm hỏng flow chính

### F. Regression Guards

Mục tiêu:

- có đủ test và contract guard để tiếp tục mở rộng mà không gãy flow
- tách rõ release gate chính với direct-only / experimental flows

Giá trị cho team:

- sửa nhanh hơn, ít hồi quy hơn, dễ giao việc hơn

## 5. Thứ tự ưu tiên bắt buộc

1. `Reminder Core Truthfulness`
2. `Scan As Primary Journey`
3. `Medication Safety Expansion`
4. `AI-Assisted Safety And Less Manual Input`
5. `Adherence And History Depth`
6. `Assisted Pill Verification`
7. `Regression Guards`

Quy tắc:

- không nhảy sang lớp AI sâu hoặc Phase B khi lớp truthfulness của reminder còn hở
- không mở rộng product surface nếu test và contract guard chưa đủ giữ ổn định

Now trong nhánh mở rộng medication safety:

1. `Canonical Medication Snapshot`
2. `Medication Reconciliation Engine`
3. `Transition-of-care Safety Mode`
4. `Prescription -> Dispensed Reconciliation` bản text-first

Next:

1. `JITI-lite` rule-based only

Later:

1. `Personal Pill Passport`

## 6. Definition Of Done

Plan active này chỉ được xem là hoàn thành khi:

- reminder flow không còn nói sai trạng thái thật với user
- scan trở thành flow chính để tạo kế hoạch, có review và recovery tử tế
- interaction/safety layer hoạt động theo hướng hỗ trợ quyết định, không làm phiền vô nghĩa
- history và adherence tạo được giá trị quay lại hằng ngày
- Phase B nếu xuất hiện trong app thì ở trạng thái `assisted` và được gate rõ ràng
- test matrix chính đủ chặn các hồi quy quan trọng của mobile, Node và Python app-path

## 7. Không làm trong plan active này

- push/server-driven reminder như lớp chính
- open-world pill recognition
- quay lại GCN cũ hoặc research-heavy matcher
- thêm LLM/VLM tổng quát để sinh hướng dẫn y khoa tự do
- mở rộng backend/pipeline lớn chỉ để che lấp vấn đề UX nhỏ
- refactor rộng không gắn trực tiếp với mục tiêu sản phẩm ở trên
