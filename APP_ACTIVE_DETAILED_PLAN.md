# Active Detailed Plan

> File này là execution spec cho `APP_ACTIVE_GENERAL_PLAN.md`.
> Chủ đích của file này là ngắn, rõ, ít nhiễu.
> Không dùng file này để nhét roadmap theo thời gian, board trạng thái, hoặc danh sách slice dài dòng.

## 1. Thứ tự đọc bắt buộc

1. `AGENTS.md`
2. `AGENT_START_HERE.md`
3. `APP_ACTIVE_GENERAL_PLAN.md`
4. `APP_ACTIVE_DETAILED_PLAN.md` (file này)
5. `docs/UONG_THUOC_FULL_TEST_PLAN.md`
6. `docs/phase_a_debug_runbook.md` nếu đụng app-path scan hoặc contract Phase A

## 2. Quy tắc toàn cục

1. Mỗi lần execution chỉ nên xử lý đúng một workstream hoặc một lát cắt nhỏ trong workstream đó.
2. Ưu tiên patch nhỏ, trực tiếp, không refactor rộng để “làm đẹp code”.
3. Không sửa `scripts/run_pipeline.py`, `core/**`, `server/**`, `server-node/**` nếu vấn đề chỉ nằm ở mobile/UI; chỉ đụng khi đã xác định rõ blocker contract hoặc capability cần tận dụng thật sự.
4. Không che giấu state xấu bằng copy hoặc affordance dễ gây hiểu lầm.
5. Mọi text user-facing mới hoặc sửa lại phải là tiếng Việt có dấu.
6. Nếu màn đã có l10n, ưu tiên cập nhật l10n thay vì hardcode thêm.
7. Nếu phát hiện bug gốc nằm ở backend contract, phải ghi rõ blocker hoặc đổi phạm vi có chủ đích; không vá bừa ở mobile.
8. Không mở rộng Phase B hoặc AI sâu khi lớp reminder truthfulness chưa qua được release gate chính.

## 3. Workstreams active

### WS1 — `CORE-TRUTH`

Mục tiêu:

- làm đúng trạng thái offline/sync/auth/navigation/reminder
- giữ `plan`, `today schedule`, `notification`, `history` đồng bộ với nhau

In scope điển hình:

- `mobile/lib/features/home/**`
- `mobile/lib/features/settings/**`
- `mobile/lib/features/plan/**`
- `mobile/lib/core/router/**`
- `mobile/lib/core/network/**`
- `mobile/lib/core/notifications/**`
- `mobile/lib/features/auth/**`

Done khi:

- user phân biệt được `đã đồng bộ`, `đã lưu tạm`, `thất bại`
- save/edit/end/reactivate plan làm tươi Home và reschedule notification đúng ngay trong cùng flow
- Home không còn empty state sai
- Settings và auth flow không còn điều hướng gây hiểu lầm

### WS2 — `SCAN-JOURNEY`

Mục tiêu:

- đưa scan thành đường vào chính để tạo plan
- giữ dữ liệu scan thật qua review, history, reuse
- hoàn thiện camera guidance, recovery path, scan history, reopen/recreate flow
- chuẩn bị hoặc productize multi-shot scan dựa trên session API đã có

In scope điển hình:

- `mobile/lib/features/create_plan/**`
- `mobile/lib/features/history/**`
- `mobile/lib/features/scan/**`
- `server-node/src/routes/scan.routes.js`
- `server-node/src/services/scan.service.js`

Done khi:

- flow `quét -> review -> schedule` liền mạch
- scan lỗi có guidance và recovery rõ
- scan history mở lại được và tạo plan lại mà không làm đẹp hóa dữ liệu gốc

### WS3 — `AI-SAFETY`

Mục tiêu:

- tăng giá trị AI theo hướng hỗ trợ quyết định và giảm nhập tay
- thêm interaction warnings, duplicate ingredient checks, enrichment card, correction memory, review scoring tốt hơn, draft plan suggestion

In scope điển hình:

- `server-node/src/services/drug.service.js`
- `server/services/drug_service.py`
- `mobile/lib/features/drug/**`
- `mobile/lib/features/create_plan/**`
- `mobile/lib/features/history/**`

Done khi:

- warning có giải thích được và không giả vờ chắc chắn
- mọi suggestion từ AI đều có điểm user confirm rõ ràng
- không có đường auto-save plan thật từ AI mà bỏ qua review

### WS3A — `MED-SNAPSHOT`

Mục tiêu:

- tạo `canonical medication snapshot` dùng chung cho scan result, active plan và dispensed package scan
- giữ một shape dữ liệu chuẩn trước khi làm reconciliation hoặc safety UI

Shape v1 tối thiểu:

- `rawName`
- `normalizedName`
- `matchedDrugName`
- `activeIngredients[]`
- `strength[]`
- `dosageForm`
- `manufacturer`
- `packaging`
- `mappingStatus`
- `confidence`
- `sourceType`
- `sourceRef`
- `evidence`

Ràng buộc v1:

- `manufacturer` và `packaging` là enrichment optional, không được làm engine fail nếu thiếu
- chưa cố hiểu sâu `instruction`, `quantity`, `unit`

Done khi:

- scan item và active plan item được chuẩn hóa về cùng một cấu trúc
- reconciliation engine có thể chạy trên snapshot mà không phải đọc shape gốc của từng nguồn

### WS3B — `RECONCILIATION`

Mục tiêu:

- so sánh `new scan vs active plan`
- so sánh `new scan vs previous scan`
- trả về diff có cấu trúc, không chỉ text mô tả

Output v1 kỳ vọng:

- `added_medications`
- `removed_medications`
- `possible_substitutions`
- `duplicate_active_ingredients`
- `strength_changed`
- `dosage_form_changed`
- `needs_manual_review`

Ràng buộc v1:

- chỉ so sánh chắc tay theo `tên`, `hoạt chất`, `strength nếu có`, `dosage form nếu có`
- không tự suy diễn khi OCR yếu hoặc metadata thiếu

Done khi:

- có backend service + API đầu tiên cho compare scan với baseline phù hợp
- có test fixtures cho case thêm thuốc, ngừng thuốc, đổi brand cùng hoạt chất, strength mismatch, unresolved OCR, duplicate active ingredient

### WS3C — `TOC-SAFETY`

Mục tiêu:

- render kết quả reconciliation thành `transition-of-care safety mode`
- biến diff kỹ thuật thành checklist, risk cards, CTA dễ hiểu

Render v1 kỳ vọng:

- `Know / Check / Ask`
- risk label kiểu `Cần hỏi lại`, `Có thể trùng thuốc`, `Có thể đổi thuốc`, `Cần xác nhận nhà thuốc`
- CTA theo tình huống `toa mới`, `tái khám`, `ra viện`, `mua thuốc ngoài`

Done khi:

- UI hoặc API response đủ rõ để user nhìn phát hiểu có gì thay đổi
- không cần model mới

### WS3D — `DISPENSED-TEXT`

Mục tiêu:

- so sánh `toa/expected meds` với `thuốc đã mua` theo hướng text-first
- dùng OCR nhãn/hộp/bao bì có text rõ, không đụng loose-pill ID ở v1

Scope v1:

- ảnh hộp thuốc
- ảnh nhãn thuốc
- ảnh bao bì có text rõ

Không làm trong v1:

- loose-pill recognition
- open-world pill identification
- authentication claim

Done khi:

- OCR text được normalize sang expected meds
- output có ít nhất `matched`, `possible_substitution`, `missing_from_purchase`, `unverified_package`
- mọi kết quả yếu đều hiện là candidate, không ép confirmed

### WS4 — `ADHERENCE`

Mục tiêu:

- làm Home/History có giá trị quay lại hằng ngày
- thêm adherence summary, weekly trend, breakdown taken/skipped/missed, reuse plan tốt hơn

In scope điển hình:

- `mobile/lib/features/history/**`
- `mobile/lib/features/home/**`
- `server-node/src/services/plan.service.js`
- `server-node/src/routes/plan.routes.js`

Done khi:

- user xem được tiến độ điều trị ngắn hạn từ dữ liệu thật
- analytics không mâu thuẫn với raw logs

### WS5 — `PILL-ASSIST`

Mục tiêu:

- giữ Phase B ở dạng assisted verification gắn với liều cụ thể
- chụp mẫu trước, verify sau, manual assignment luôn là lối thoát chuẩn

In scope điển hình:

- `mobile/lib/features/pill_verification/**`
- `server-node/src/routes/pillVerification.routes.js`
- `server-node/src/services/pillVerification.service.js`
- `server-node/src/services/pillReference.service.js`
- `core/phase_b/**` chỉ khi thật sự cần tận dụng capability đã có

Done khi:

- flow verify không làm bẩn state reminder/log
- chưa có ảnh mẫu thì app nói rõ là chưa sẵn sàng verify
- verify fail vẫn cho user hoàn tất liều bằng manual path

### WS6 — `REGRESSION-GUARDS`

Mục tiêu:

- thiết lập guardrails cho mobile, Node, Python app-path và contract cross-layer

In scope điển hình:

- `mobile/test/**`
- `mobile/integration_test/**`
- `server-node/tests/**`
- `tests/**`
- `scripts/tests/**`

Done khi:

- các flow P0/P1 chính có test bảo vệ tương xứng
- direct-only / experimental routes được tách khỏi release gate chính

## 4. Thứ tự thực thi

1. `WS1 — CORE-TRUTH`
2. `WS2 — SCAN-JOURNEY`
3. `WS3A — MED-SNAPSHOT`
4. `WS3B — RECONCILIATION`
5. `WS3C — TOC-SAFETY`
6. `WS3D — DISPENSED-TEXT`
7. `WS3 — AI-SAFETY`
8. `WS4 — ADHERENCE`
9. `WS5 — PILL-ASSIST`
10. `WS6 — REGRESSION-GUARDS`

Quy tắc:

- không bắt đầu workstream sau nếu workstream trước còn bug nền chưa khóa phạm vi hoặc chưa qua review
- test guard có thể được làm song song để bảo vệ các phần vừa sửa, nhưng không được thay thế cho việc giải quyết bug nền

## 5. Protocol output bắt buộc cho mọi execution

Mỗi execution phải trả ít nhất các mục sau:

1. `Workstream ID`
2. `Phạm vi đã xử lý`
3. `Files đã đọc`
4. `Files đã sửa`
5. `Cách sửa chính`
6. `Những gì cố ý không sửa`
7. `Lệnh test đã chạy`
8. `Kết quả test`
9. `Manual smoke đã kiểm tra / chưa kiểm tra`
10. `Rủi ro còn lại`

## 6. Luật dừng

Phải dừng và báo lại nếu gặp một trong các tình huống sau:

1. Cần sửa `scripts/run_pipeline.py` hoặc thay đổi Phase A core ngoài phạm vi đã khóa.
2. Cần đổi backend contract vượt quá patch nhỏ ban đầu.
3. Workspace bẩn xung đột trực tiếp với file đang làm.
4. Test fail ở phần không liên quan và chưa xác định được nguyên nhân.
5. Vấn đề thực tế hóa ra thuộc workstream khác có độ ưu tiên cao hơn.

Khi dừng phải nêu rõ:

- đang làm workstream nào
- đã làm gì
- file nào đã sửa
- test nào đã chạy
- blocker là gì
- bước nhỏ nhất tiếp theo nên làm
