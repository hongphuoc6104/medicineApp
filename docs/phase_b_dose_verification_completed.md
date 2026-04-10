# Kế hoạch Phase B — Xác minh thuốc theo từng khung giờ

Đây là file plan đang hoạt động ở thư mục gốc cho Phase B.

Plan này thay thế hướng MVP-lite cũ trong `docs/phase_b_mvp_lite_plan.md` bằng kiến trúc mới phù hợp hơn với dữ liệu thật của dự án.

File này phải đủ rõ để **một AI agent mới vào repo có thể đọc, hiểu, triển khai đúng phạm vi, không làm thừa, không phá code sẵn có, và tự kiểm lại kết quả trước khi báo xong**.

---

## A. Thứ tự đọc bắt buộc trước khi viết code

AI triển khai phải đọc theo đúng thứ tự sau:

1. `AGENTS.md`
2. `PHASE_B_DOSE_VERIFICATION_PLAN.md` (file này)
3. `core/pipeline.py`
4. `core/phase_b/s1_pill_detect/pill_detector.py`
5. `core/phase_b/s2_match/gcn_matcher.py`
6. `server/main.py`
7. `server-node/src/routes/pillVerification.routes.js`
8. `server-node/src/services/pillVerification.service.js`
9. `server-node/src/services/plan.service.js`
10. `server-node/src/app.js`

Sau đó mới đọc tiếp các file UI hoặc schema liên quan đến phần đang làm.

### A.1 Nếu làm Mobile

Đọc thêm các file đang dùng cho flow kế hoạch và lịch uống hiện tại, rồi mới tạo màn mới hoặc sửa màn cũ.

Ưu tiên đọc:

- màn lịch uống hôm nay
- màn tạo kế hoạch / chỉnh thuốc
- model plan / dose / medication log đang có
- route điều hướng hiện tại trong app

### A.2 Nếu làm Node / Python

Phải đọc toàn bộ request-response flow hiện tại từ route -> service -> Python API -> pipeline trước khi đổi contract.

Không được suy đoán contract từ tên biến hoặc từ trí nhớ.

---

## B. Hard rules — chống làm thừa và chống phá code

### B.1 Không được đụng những phần ngoài scope nếu không thật sự cần

- không đổi kiến trúc Phase A
- không sửa `scripts/run_pipeline.py`
- không refactor lại scan session của Phase A chỉ vì tiện tay
- không đổi luồng nhắc thuốc cả ngày thành luồng mới toàn phần
- không làm full-auto matcher production claim trong giai đoạn này

### B.2 Phải ưu tiên thay đổi theo kiểu additive

- thêm schema mới thay vì phá schema cũ nếu chưa có migration an toàn
- thêm field mới trước khi xóa field cũ
- nếu đổi contract thì phải đổi tất cả consumer liên quan trong cùng một đợt

### B.3 Không được quay lại tư duy GCN làm lõi

Không được tự ý:

- đưa `GCN matcher` trở lại làm luồng mặc định
- làm prescription graph matching là bước bắt buộc
- thiết kế verify theo toàn bộ đơn thuốc thay vì theo `occurrenceId`

### B.4 Không được để lọt text hiển thị không dấu

Nếu AI chạm vào màn hình nào thì phải rà luôn toàn bộ text user-facing trong màn đó.

Text không dấu trong phần vừa sửa được xem là chưa hoàn thành.

---

## 0. Mục tiêu

Xây dựng Phase B theo hướng:

- xác minh thuốc cho **một khung giờ đang đến**
- dùng **ảnh viên thuốc thật của chính user**
- gắn profile ảnh theo **từng plan thuốc của user**
- không dùng GCN prescription-matching làm lõi sản phẩm
- mọi nội dung hiển thị trong app phải là **tiếng Việt có dấu**

Mục tiêu của V1 là tạo ra flow hữu ích, dễ dùng, có thể triển khai sớm, đồng thời thu được dữ liệu thật để cải thiện model về sau.

---

## 1. Quyết định sản phẩm đã chốt

### 1.1 Phạm vi xác minh

Phase B chỉ xác minh cho **một liều / một khung giờ đang đến**, không quét tất cả thuốc của cả ngày trong một lần.

Ví dụ:

- `08:00` -> chỉ so với danh sách thuốc expected ở liều `08:00`
- không so với toàn bộ 8-10 thuốc user đang có trong ngày

### 1.2 Đơn vị profile ảnh

Reference pill profile phải gắn theo **từng plan thuốc của user**, không dùng chung toàn tài khoản theo tên thuốc.

Lý do:

- cùng tên thuốc có thể đổi hãng, đổi màu, đổi hình dạng
- user có thể đổi lô thuốc giữa chừng
- gắn theo plan giúp giảm nhầm và dễ reset dữ liệu hơn

### 1.3 Nguồn nhận diện chính

Không lấy prescription graph matching của Zero-PIMA làm lõi.

Thay vào đó dùng:

- `pill detector` để phát hiện viên thuốc
- `reference images` của chính user để đối sánh
- `business rules` để tính đủ / thiếu / dư / viên lạ

### 1.4 Ngôn ngữ giao diện

**Tất cả text hiển thị cho người dùng trong app phải là tiếng Việt có dấu.**

Không chấp nhận text như:

- `Xac nhan`
- `Nhap tay`
- `Quet don thuoc`

Phải đổi thành:

- `Xác nhận`
- `Nhập tay`
- `Quét đơn thuốc`

---

## 2. Vì sao phải đổi kiến trúc

### 2.1 Zero-PIMA full pipeline không phù hợp để dùng nguyên trạng

Dữ liệu thực tế của dự án khác giả định train ban đầu của Zero-PIMA:

- đơn thuốc thật chụp ngoài đời nhiễu hơn nhiều
- OCR blocks và bbox không ổn định
- GCN prescription-side phụ thuộc mạnh vào graph từ OCR
- nhiều viên thuốc ngoài thực tế không có hộp, không có vỉ, chỉ là viên rời

Kết luận:

- có thể giữ lại detector nếu hoạt động ổn
- không dùng `GCN matcher` làm lõi sản phẩm cho V1

### 2.2 Bài toán thực của sản phẩm đơn giản hơn

Sau khi Phase A đã tạo plan, bài toán ở Phase B không còn là:

- match viên thuốc với toàn bộ đơn thuốc

Mà là:

- trong ảnh liều hiện tại, viên nào thuộc nhóm thuốc expected của khung giờ này

Candidate set nhỏ hơn rất nhiều, nên phù hợp hơn với personalized matching.

---

## 3. Luồng sản phẩm mục tiêu

## 3.1 Sau khi tạo plan

User thấy lời nhắc:

- `Bạn có muốn chụp mẫu viên thuốc để xác minh cho lần sau không?`

Enrollment là **khuyến nghị mạnh**, chưa bắt buộc ngay lúc tạo plan.

### 3.2 Enrollment từng thuốc theo plan

Với mỗi thuốc trong plan:

1. User chọn đúng thuốc trong plan.
2. App mở camera với vùng guide rõ ràng.
3. User đưa **một viên thuốc** vào giữa khung.
4. Hệ thống tự lấy burst/video ngắn `1-2 giây`.
5. Hệ thống chọn ra `3-5 frame` tốt nhất.
6. Nếu viên có 2 mặt khác nhau, app đề nghị quét thêm mặt còn lại.

User không phải bấm chụp 5 lần thủ công.

### 3.3 Xác minh khi đến giờ uống

Khi tới khung giờ đang đến:

1. User mở `thẻ liều` của khung giờ đó.
2. App hiển thị danh sách thuốc expected và số viên cần uống.
3. User bấm `Xác minh liều này`.
4. User chụp **1 ảnh chứa tất cả viên thuốc** đã chuẩn bị uống.
5. Hệ thống detect từng viên.
6. Hệ thống đối sánh từng viên với reference images của các thuốc expected trong liều đó.
7. Hệ thống trả kết quả:
   - đúng
   - thiếu
   - dư
   - viên lạ
   - không chắc
8. User sửa nếu cần, rồi xác nhận.

---

## 4. Scope triển khai

### 4.1 P0 — MVP phải có

- verify theo **một khung giờ đang đến**
- enrollment ảnh mẫu theo **từng plan thuốc**
- detect viên thuốc trong ảnh nhóm
- trả danh sách detection để review
- đối sánh baseline với reference images
- đếm đủ / thiếu / dư / viên lạ
- user sửa tay được
- lưu feedback để dùng cho cải thiện sau này
- toàn bộ UI là tiếng Việt có dấu

### 4.2 P1 — Nên có ngay sau MVP

- quality gate cho enrollment
- gợi ý top-3 cho mỗi viên nếu điểm không quá chắc
- đánh dấu `không chắc` thay vì ép gán nhãn
- cảnh báo thuốc trong liều chưa có reference profile

### 4.3 Chưa làm trong giai đoạn này

- full auto production claim
- GCN prescription matching làm lõi
- verify toàn bộ thuốc của cả ngày trong một ảnh
- suy luận tương tác thuốc sâu
- family mode / đa bệnh nhân

### 4.4 Không được làm thêm ngoài plan này

Những việc sau được xem là làm thừa nếu không có yêu cầu mới từ user:

- redesign toàn bộ home hoặc create plan flow ngoài phần Phase B liên quan trực tiếp
- thêm tính năng social / caregiver / chia sẻ thuốc
- train model mới ngay từ đầu khi baseline chưa xong
- tối ưu hóa đa giờ, đa liều, đa ngày trong một phiên scan
- gom Phase A và Phase B thành một mega-refactor

---

## 5. Kiến trúc kỹ thuật mục tiêu

### 5.1 Python / AI layer

Giữ lại:

- `core/phase_b/s1_pill_detect/pill_detector.py`

Hạ vai trò hoặc bỏ khỏi luồng chính:

- `core/phase_b/s2_match/gcn_matcher.py`

Luồng mới cho `verify_pills`:

1. detect pills
2. crop pills
3. load reference images của các thuốc expected trong `occurrenceId`
4. sinh embedding cho crop và reference
5. so similarity trong candidate set nhỏ
6. trả `suggestions + confidence + status`
7. aggregate kết quả đủ / thiếu / dư

### 5.2 Node layer

Node phải là nơi điều phối session theo `occurrenceId`.

Node không gửi `prescription_json` giả cho Phase B nữa.

Thay vào đó gửi payload bám vào liều hiện tại:

- `occurrenceId`
- `scheduledTime`
- `expectedMedications[]`
- `referenceProfileIds[]` hoặc dữ liệu reference liên quan

### 5.3 Mobile layer

Mobile phải xoay quanh `dose card` / `thẻ liều`.

Màn chính của Phase B:

- màn hôm nay / sắp đến giờ
- màn enrollment ảnh mẫu
- màn quét ảnh nhóm viên thuốc
- màn review kết quả xác minh
- sheet kết quả xác minh cuối cùng

### 5.4 Nguyên tắc tương thích ngược

Khi nâng cấp flow hiện có:

- không làm hỏng các route `scan`, `plan`, `pill-verifications` đang hoạt động
- nếu response shape đổi thì phải cập nhật toàn bộ consumer + test tương ứng
- nếu cần chuyển trạng thái hoặc bảng dữ liệu, phải có migration rõ ràng
- ưu tiên giữ được detector hiện có ngay cả khi matcher mới chưa hoàn thiện

---

## 6. Mô hình dữ liệu đề xuất

### 6.1 Reference theo plan thuốc

`pill_reference_sets`

- `id`
- `user_id`
- `plan_id`
- `drug_name_snapshot`
- `status`
- `created_at`
- `updated_at`

`pill_reference_images`

- `id`
- `reference_set_id`
- `image_path`
- `side`
- `quality_score`
- `embedding`
- `confirmed_by_user`
- `created_at`

### 6.2 Session xác minh theo khung giờ

`dose_verification_sessions`

- `id`
- `user_id`
- `occurrence_id`
- `scheduled_time`
- `status`
- `result`
- `confirmed_at`
- `created_at`
- `updated_at`

`dose_verification_detections`

- `session_id`
- `detection_idx`
- `bbox`
- `score`
- `assigned_plan_id`
- `assigned_drug_name`
- `confidence`
- `status`
- `note`

---

## 7. API contract đề xuất

### 7.1 Enrollment

- `POST /api/pill-references/enroll/start`
- `POST /api/pill-references/:id/frame`
- `POST /api/pill-references/:id/finalize`
- `GET /api/pill-references?planId=...`

### 7.2 Dose verification

- `POST /api/pill-verifications/start`
- `POST /api/pill-verifications/:id/image`
- `POST /api/pill-verifications/:id/assign`
- `POST /api/pill-verifications/:id/confirm`
- `GET /api/pill-verifications/:id`

### 7.3 Today schedule integration

API lịch uống hôm nay cần bổ sung cờ như:

- `hasReferenceProfile`
- `referenceProfileStatus`
- `verificationReady`

để UI biết dose nào đã sẵn sàng xác minh.

### 7.4 Quy tắc contract bắt buộc

Contract của Phase B phải luôn phản ánh đúng mô hình `dose-centric`:

- session gắn với `occurrenceId`
- reference gắn với `planId`
- summary trả theo `thuốc expected của khung giờ hiện tại`

Nếu implementation nào vẫn dựa vào `prescription_json` giả để verify thì được xem là **chưa đạt**.

---

## 8. Quy tắc ML / matching cho V1

### 8.1 Không train lại ngay từ đầu

V1 nên đi theo baseline thực dụng:

- embedding ảnh viên thuốc
- cosine similarity / nearest-neighbor
- chỉ match trong tập thuốc expected của khung giờ hiện tại

### 8.2 Trạng thái bắt buộc phải có

Mỗi detection phải có thể rơi vào một trong các trạng thái:

- `đã gán`
- `không chắc`
- `viên lạ`
- `dư`

Không được ép hệ thống kết luận chắc chắn khi score thấp.

### 8.3 Đếm đủ / thiếu / dư

Phần này dùng rule-based logic, không giao hoàn toàn cho model.

Ví dụ:

- expected: `Metformin = 2`, `Vitamin C = 1`
- actual assigned: `Metformin = 3`, `Vitamin C = 1`, `unknown = 1`

Kết quả:

- `Metformin: dư 1 viên`
- `Vitamin C: đủ`
- `Viên lạ: 1`

### 8.4 Nguyên tắc fallback

Nếu thiếu dữ liệu, thiếu embedding ổn định, hoặc chưa có benchmark đủ tốt thì không được bịa ra auto-final.

Fallback đúng trong V1 là:

- detect được viên thuốc
- gợi ý nếu có thể
- cho user sửa tay
- lưu feedback

---

## 9. Màn hình và copy tiếng Việt có dấu

### 9.1 Tên CTA khuyến nghị

- `Chụp mẫu viên thuốc`
- `Quét mặt còn lại`
- `Xác minh liều này`
- `Chụp lại ảnh`
- `Xác nhận đã uống`
- `Không chắc viên này là thuốc nào`

### 9.2 Copy không được thiếu dấu

Mọi text mới thêm vào app phải dùng tiếng Việt có dấu.

Nếu phát hiện text cũ chưa có dấu thì phải sửa trong cùng đợt triển khai màn hình liên quan.

Ví dụ không đạt:

- `Xac nhan ket qua`
- `Nhap tay`
- `Quet lai`

Ví dụ đạt:

- `Xác nhận kết quả`
- `Nhập tay`
- `Quét lại`

---

## 10. Trình tự triển khai bắt buộc

### 10.0 Preflight trước khi code

1. Chạy `git status --short` để biết workspace đang bẩn chỗ nào.
2. Ghi nhận các file bẩn không liên quan và **không đụng vào**.
3. Đọc đủ các file trong mục `A` trước khi sửa bất kỳ file nào.
4. Xác nhận rõ phần nào đang là placeholder, phần nào đang chạy production trong app.
5. Chỉ sau đó mới chọn phạm vi lát cắt đầu tiên để code.

1. Chốt contract `dose-centric` cho Phase B.
2. Tạo schema lưu reference theo `plan_id`.
3. Làm enrollment flow tối thiểu.
4. Refactor Phase B backend từ `prescription matching` sang `dose verification`.
5. Làm màn quét ảnh nhóm cho một khung giờ.
6. Làm màn review + chỉnh tay + summary.
7. Lưu feedback user correction.
8. Chạy test và benchmark trên dữ liệu thật.
9. Chỉ khi baseline ổn mới cân nhắc train metric-learning riêng.

### 10.1 Cách chia lát cắt triển khai an toàn

Không làm tất cả trong một lần sửa lớn nếu chưa hiểu hết luồng.

Thứ tự khuyến nghị:

- Lát cắt 1: schema + contract + mock response ổn định
- Lát cắt 2: enrollment flow theo `planId`
- Lát cắt 3: dose verification detector-first
- Lát cắt 4: baseline reference matching
- Lát cắt 5: polish UI tiếng Việt có dấu + regression tests

Mỗi lát cắt phải chạy test trước khi chuyển sang lát cắt tiếp theo.

---

## 11. File dự kiến sẽ đụng tới

### Python

- `core/pipeline.py`
- `core/phase_b/s1_pill_detect/pill_detector.py`
- file Phase B matcher mới theo hướng reference matching
- `server/main.py`

### Node

- `server-node/src/routes/pillVerification.routes.js`
- `server-node/src/services/pillVerification.service.js`
- `server-node/src/services/plan.service.js`
- migration / schema PostgreSQL cho reference profile

### Mobile

- màn lịch uống hôm nay / thẻ liều
- màn enrollment mẫu viên thuốc
- màn quét xác minh viên thuốc
- màn review kết quả xác minh

### Không được sửa nếu chưa có lý do rõ ràng

- `scripts/run_pipeline.py`
- các module Phase A không liên quan trực tiếp tới contract dùng chung
- các route auth / drug / health không phục vụ Phase B

---

## 12. Checklist tự kiểm trước khi báo xong

AI triển khai phải tự trả lời **có / không** cho từng câu sau trước khi kết thúc:

1. Flow hiện tại có verify theo đúng **một `occurrenceId`** không?
2. Reference profile có gắn theo đúng **`plan_id`** không?
3. Có chỗ nào còn dùng `prescription_json` giả để verify Phase B không?
4. Có chỗ nào còn phụ thuộc `GCN matcher` làm luồng chính không?
5. Trong các màn vừa sửa, còn text tiếng Việt nào thiếu dấu không?
6. Nếu chưa đủ tự tin match, hệ thống có trả `không chắc` thay vì ép đúng sai không?
7. Khi thiếu reference profile, UI có hướng dẫn user chụp mẫu thay vì fail mơ hồ không?
8. User có thể sửa tay trước khi xác nhận không?
9. Các route / consumer cũ liên quan có còn hoạt động không?
10. Test chính đã được chạy và kết quả đã được ghi rõ chưa?

Nếu có bất kỳ câu nào trả lời `không`, task chưa được xem là xong.

---

## 13. Tiêu chí hoàn thành

Task này chỉ được xem là xong khi tất cả điều sau đều đúng:

- user có thể chụp mẫu viên thuốc theo từng plan
- user có thể mở đúng một khung giờ đang đến và xác minh liều đó
- hệ thống detect được từng viên trong ảnh nhóm
- hệ thống báo được đủ / thiếu / dư / viên lạ / không chắc
- user sửa tay được trước khi xác nhận
- feedback được lưu lại
- text hiển thị trong app ở flow này là tiếng Việt có dấu
- không còn phụ thuộc vào GCN prescription matching cho flow chính

---

## 14. Bộ kiểm tra bắt buộc sau khi code

AI triển khai phải tự chạy hoặc nêu rõ lý do không chạy được các kiểm tra phù hợp với phần đã sửa.

### 14.1 Nếu sửa Node

Chạy tối thiểu:

```bash
cd server-node && npm test
```

Nếu có test riêng cho Phase B thì phải thêm và chạy ít nhất:

- test route `pill-verifications`
- test service mapping `occurrenceId` / `planId`
- test summary đủ / thiếu / dư / viên lạ

### 14.2 Nếu sửa Mobile

Chạy tối thiểu:

```bash
cd mobile && flutter analyze
cd mobile && flutter test
```

Nếu không chạy được trên máy hiện tại thì phải nói rõ phần nào chưa verify bằng tool và phần nào đã tự rà thủ công.

### 14.3 Nếu sửa Python

Phải có ít nhất một dạng smoke test hoặc unit test cho:

- detector-first flow
- response shape mới của verify
- fallback khi chưa match chắc

Không được chỉ sửa Python rồi kết luận bằng suy đoán.

---

## 15. Báo cáo bàn giao mà AI phải trả khi hoàn thành

Khi kết thúc, AI phải báo ngắn gọn nhưng đủ các ý sau:

1. các file đã đổi
2. phạm vi đã làm và phạm vi cố ý chưa làm
3. contract mới của Phase B đã thay đổi gì
4. cách đảm bảo không làm hỏng flow cũ
5. kết quả test / analyze / smoke test
6. điểm còn hạn chế hoặc cần user quyết định tiếp

---

## 16. Điều kiện archive plan

Khi plan này đã triển khai xong và được kiểm tra đạt tiêu chí hoàn thành:

1. chuyển file này vào `docs/`
2. đổi tên thành dạng completed record phù hợp
3. tạo plan gốc mới ở thư mục root nếu có nhiệm vụ active tiếp theo

Nếu chưa đạt đủ tiêu chí hoàn thành thì file này phải tiếp tục ở thư mục gốc.
