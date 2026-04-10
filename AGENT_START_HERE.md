# Agent Start Here

Đây là file entrypoint duy nhất nên gửi trong các cuộc trò chuyện mới.

Mục tiêu của file này là để AI hiểu đúng cách làm việc trong repo này mà không cần user phải nhắc lại toàn bộ quy trình mỗi lần.

Nếu chỉ gửi **một file**, hãy gửi file này.

---

## 1. Vai trò các AI

### 1.1 AI lập plan và rà soát dự án

AI đang đọc file này có vai trò:

- phân tích repo
- rà soát vấn đề tổng quát
- tạo và cập nhật plan
- chia việc thành các lát cắt nhỏ
- quyết định nên giao lát cắt đó cho model nào
- kiểm tra lại kết quả sau khi execution model hoàn thành

AI này **không được** đẩy việc lập plan sang execution model nếu chưa khóa rõ phạm vi.

### 1.2 Các execution model

Các model thực thi code chỉ nên được giao việc sau khi đã có detailed plan rõ ràng:

- `GPT-5.3 Codex` trong GitHub Copilot / OpenCode
- `Gemini 3.1 Pro`
- `Gemini 3 Flash`
- `Claude Sonnet Thinking`
- `Claude Opus Thinking`

Các model này dùng để:

- code theo plan đã khóa
- sửa bug theo lát cắt đã chốt
- chạy test/analyze theo yêu cầu

Không nên giao cho chúng nhiệm vụ “tự nghĩ toàn bộ roadmap” nếu chưa có plan.

---

## 2. Thứ tự đọc bắt buộc

Sau file này, AI phải đọc tiếp theo đúng thứ tự:

1. `AGENTS.md`
2. `APP_ACTIVE_GENERAL_PLAN.md`
3. `APP_ACTIVE_DETAILED_PLAN.md`
4. `docs/phase_a_debug_runbook.md`

Nếu một trong các file plan active không còn phù hợp với vấn đề hiện tại, AI phải cập nhật hoặc tạo plan mới theo quy trình ở mục 4.

---

## 3. Trạng thái repo hiện tại

Ưu tiên sản phẩm hiện tại là:

- hoàn thiện app theo flow chính `quét đơn thuốc -> xác nhận danh sách thuốc -> lập lịch -> lưu kế hoạch`

Những nguyên tắc nền phải luôn giữ:

- không đụng `scripts/run_pipeline.py` nếu không có lý do bắt buộc và được chốt rõ
- Phase A là trọng tâm giao sản phẩm
- Phase B là lớp nghiên cứu/tiếp theo, không được làm lệch mục tiêu chính
- mọi text user-facing ở các màn đã sửa phải là tiếng Việt có dấu

---

## 4. Quy trình chuẩn cho mọi vấn đề mới

Khi có một yêu cầu mới hoặc cần nâng cấp/sửa lỗi lớn, AI phải đi theo đúng quy trình này:

### Bước 1 — Phân tích trước

- đọc code liên quan
- xem `git status --short`
- xác định đây là vấn đề thuộc Phase A, Phase B, contract, UX hay infra

### Bước 2 — Tạo hoặc cập nhật general plan ở root

Nếu đây là một cụm vấn đề mới hoặc một đợt nâng cấp mới, AI phải:

- tạo mới hoặc cập nhật `APP_ACTIVE_GENERAL_PLAN.md`

General plan chỉ ghi:

- vấn đề tổng quát
- nhóm ưu tiên
- thứ tự xử lý lớn

### Bước 3 — Tạo hoặc cập nhật detailed plan ở root

Trước khi giao execution model code, AI phải:

- tạo mới hoặc cập nhật `APP_ACTIVE_DETAILED_PLAN.md`

Detailed plan phải có:

- phạm vi được sửa
- phạm vi cấm sửa
- thứ tự đọc file
- lát cắt hiện tại
- file cần đụng tới
- tiêu chí xong
- luật dừng nếu lỗi lớn

### Bước 4 — Chỉ giao đúng một lát cắt

Execution model chỉ được giao:

- một lát cắt nhỏ
- một mục tiêu rõ ràng
- một nhóm file vừa phải

Không giao cả epic lớn trong một lần.

### Bước 5 — Sau khi xong lát cắt

Phải kiểm tra:

- code đã đúng chưa
- test/analyze đã chạy chưa
- có vượt phạm vi không
- có cần mở detailed plan tiếp theo không

---

## 5. Quy tắc archive plan

### 5.1 Khi detailed plan xong

Nếu một detailed plan đã hoàn thành tốt, test ổn và không còn active nữa:

- chuyển file detailed plan đã hoàn thành vào `archive/plan_bin/`

### 5.2 Khi toàn bộ general plan xong

Chỉ khi toàn bộ các lát cắt thuộc general plan đã hoàn thành ổn định thì mới:

- chuyển general plan vào `archive/plan_bin/`

### 5.3 Không được archive quá sớm

Không được dọn plan active khỏi root nếu:

- vẫn còn lát cắt chưa làm
- vẫn còn blocker chưa giải quyết
- user chưa chốt nghiệm thu hướng đó

---

## 6. Cách chọn model để thực thi

### 6.1 `GPT-5.3 Codex`

Đây là execution model chính cho code.

Dùng khi:

- đã có detailed plan rõ ràng
- cần implement lát cắt cụ thể
- sửa 4-8 file có liên hệ logic chặt
- viết/sửa test theo cùng lát cắt

### 6.2 `Gemini 3.1 Pro`

Dùng khi:

- cần đọc rất nhiều file
- cần giữ context repo lớn
- cần thay đổi chéo nhiều tầng ở mức vừa phải

### 6.3 `Gemini 3 Flash`

Dùng khi:

- triage nhanh
- đọc log, grep, summarize
- lọc sơ phạm vi

Không nên giao implementation khó cho model này.

### 6.4 `Claude Sonnet Thinking`

Dùng khi:

- execution khó vừa
- bug reasoning nhiều hơn code boilerplate
- UI/UX implementation cần suy nghĩ cẩn thận

### 6.5 `Claude Opus Thinking`

Dùng khi:

- blocker rất khó
- bug liên tầng phức tạp
- review/đánh giá kỹ thuật sâu

Không nên dùng làm execution model mặc định cho việc thường ngày.

---

## 7. Quy tắc chia nhỏ công việc để tránh quá token/output

Dù model nào, một detailed plan chỉ nên chứa:

- `1` mục tiêu người dùng
- `1` lát cắt chính
- `1` subsystem chính
- khoảng `4-8` file code chính
- tối đa `1` thay đổi contract nếu thật sự bắt buộc

Không giao task theo kiểu:

- “hoàn thiện cả app”
- “sửa toàn bộ flow scan + review + schedule + history trong một lần”

Nếu yêu cầu lớn, AI lập plan phải tách thành nhiều detailed plan nhỏ hơn.

---

## 8. Quy tắc dừng khi có lỗi lớn

Execution model hoặc AI điều phối phải **dừng lại** nếu gặp một trong các tình huống sau:

1. cần sửa `scripts/run_pipeline.py`
2. thay đổi bắt đầu lan sang phần ngoài phạm vi đã chốt
3. contract lệch quá rộng, không thể vá nhỏ an toàn
4. test fail ở phần không liên quan và chưa xác định được nguyên nhân
5. workspace bẩn gây xung đột trực tiếp với file đang làm

Khi dừng phải báo lại:

1. đang làm lát cắt nào
2. đã làm gì
3. file nào đã sửa
4. test nào đã chạy
5. blocker là gì
6. bước nhỏ nhất tiếp theo nên làm

---

## 9. Runbook debug chuẩn

Khi làm việc liên quan đến Phase A app flow, AI phải dùng runbook:

- `docs/phase_a_debug_runbook.md`

Lệnh kiểm tra nhanh chuẩn:

```bash
bash scripts/debug_phase_a_checks.sh --quick
```

Chỉ khi cần mới chạy mode nặng hơn như `--full` hoặc `--image`.

---

## 10. Prompt ngắn để giao execution model

Khi đã có detailed plan, AI điều phối nên giao bằng prompt kiểu này:

```text
Đọc AGENTS.md, APP_ACTIVE_DETAILED_PLAN.md và docs/phase_a_debug_runbook.md trước.

Chỉ làm đúng lát cắt đang được giao.
Không sửa ngoài phạm vi plan.
Nếu gặp blocker lớn hoặc phải lan sang phần ngoài scope, dừng lại và báo:
1. đã làm gì
2. file đã sửa
3. test đã chạy
4. blocker là gì
5. bước nhỏ nhất tiếp theo
```

---

## 11. Cách dùng file này trong cuộc trò chuyện mới

Lần sau, nếu muốn AI hiểu ngay cách làm việc, chỉ cần gửi file này và nói ngắn gọn:

- vấn đề mới là gì
- muốn bắt đầu ở Phase A hay Phase B
- muốn chỉ lập plan hay muốn bắt đầu thực hiện

AI phải tự dựa vào file này để:

- đọc đúng các file cần thiết
- tạo/cập nhật plan tổng quát
- tạo/cập nhật plan chi tiết
- chia việc đúng model và đúng lát cắt

---

## 12. Ghi chú thực tế

- User dùng `GPT-5.3 Codex` trong GitHub Copilot/OpenCode làm execution model chính.
- Trong Antigravity, cần ưu tiên nghĩ theo nhóm model:
  - `Gemini 3.1 Pro`
  - `Gemini 3 Flash`
  - `Claude Sonnet Thinking`
  - `Claude Opus Thinking`
- AI đang đọc file này là planner/reviewer/orchestrator, không phải execution model mặc định.
