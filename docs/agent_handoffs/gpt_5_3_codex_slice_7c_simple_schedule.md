# Handoff — GPT-5.3 Codex — Slice 7C

Trạng thái file này:

- `active_in_parallel_batch`

Có thể bắt đầu ngay trong batch hiện tại cùng với `7A` và `7B`.

Đọc các file sau theo đúng thứ tự trước khi làm:

1. `AGENTS.md`
2. `AGENT_START_HERE.md`
3. `APP_ACTIVE_GENERAL_PLAN.md`
4. `APP_ACTIVE_DETAILED_PLAN.md`
5. `APP_EXECUTION_BOARD.md`
6. `APP_DETAIL_GPT_5_3_CODEX_SLICE_7C_SIMPLE_SCHEDULE.md`
7. `docs/phase_a_debug_runbook.md`

Nhiệm vụ của bạn:

- Chỉ thực hiện đúng `Lát cắt 7C`.
- Mục tiêu: làm màn lập lịch dễ hiểu hơn cho người lớn tuổi / user không rành công nghệ.

Phạm vi được sửa:

- `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`

Không được sửa:

- `scan_camera_screen.dart`
- `drug_entry_sheet.dart`
- bất kỳ file backend Node/Python nào
- bất kỳ file Phase B nào
- `scripts/run_pipeline.py`

Kết thúc công việc phải báo:

1. file đã sửa
2. thay đổi UX/nghiệp vụ chính
3. kết quả lệnh:
   - `cd mobile && flutter analyze`
   - `cd mobile && flutter test`
4. blocker còn lại nếu có

Luật dừng:

- Nếu cần sửa file ngoài phạm vi trên, dừng lại.
- Nếu phải đụng backend hoặc contract lớn để hoàn thành, dừng lại.
- Nếu gặp blocker, báo:
  1. đã làm gì
  2. file đã sửa
  3. test đã chạy
  4. blocker là gì
  5. bước nhỏ nhất tiếp theo

Lưu ý vận hành:

- Đây là một phần của batch song song `7A / 7B / 7C`.
- Không tự ý chuyển sang slice khác ngoài phạm vi file này.
