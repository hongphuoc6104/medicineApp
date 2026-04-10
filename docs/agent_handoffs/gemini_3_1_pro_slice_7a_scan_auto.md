# Handoff — Gemini 3.1 Pro — Slice 7A

Đọc các file sau theo đúng thứ tự trước khi làm:

1. `AGENTS.md`
2. `AGENT_START_HERE.md`
3. `APP_ACTIVE_GENERAL_PLAN.md`
4. `APP_ACTIVE_DETAILED_PLAN.md`
5. `APP_EXECUTION_BOARD.md`
6. `APP_DETAIL_GEMINI_3_1_PRO_SLICE_7A_SCAN_AUTO.md`
7. `docs/phase_a_debug_runbook.md`

Nhiệm vụ của bạn:

- Chỉ thực hiện đúng `Lát cắt 7A`.
- Mục tiêu: làm màn quét đơn thuốc tự động hơn, thực dụng hơn, phù hợp cho người lớn tuổi.
- Ưu tiên:
  - khi mở camera lên, app liên tục tự đánh giá preview
  - gặp khung hình đủ tốt thì tự lấy ảnh và gửi quét
  - không ép phải thấy trọn cả đơn thuốc mới được quét
  - nút chụp tay chỉ là fallback phụ, không phải flow chính
  - copy dễ hiểu hơn

Phạm vi được sửa:

- `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart`
- `mobile/lib/features/create_plan/data/scan_camera_controller.dart`
- `mobile/lib/features/create_plan/data/local_quality_gate.dart`

Không được sửa:

- `mobile/lib/features/create_plan/presentation/widgets/drug_entry_sheet.dart`
- `mobile/lib/features/create_plan/presentation/set_schedule_screen.dart`
- bất kỳ file backend Node/Python nào
- bất kỳ file Phase B nào
- `scripts/run_pipeline.py`

Kết thúc công việc phải báo:

1. file đã sửa
2. thay đổi UX/chụp ảnh chính
3. kết quả lệnh:
   - `cd mobile && flutter analyze`
   - `cd mobile && flutter test`
4. blocker còn lại nếu có

Luật dừng:

- Nếu cần sửa file ngoài phạm vi trên, dừng lại.
- Nếu cần đụng contract/backend để hoàn thành, dừng lại.
- Nếu gặp blocker, báo:
  1. đã làm gì
  2. file đã sửa
  3. test đã chạy
  4. blocker là gì
  5. bước nhỏ nhất tiếp theo

Lưu ý vận hành:

- Đây là một phần của batch song song `7A / 7B / 7C`.
- Sau khi bạn hoàn thành, planner sẽ review lại cùng với các slice còn lại trước khi mời user test gộp.
- Không tự ý chuyển sang Slice 7B hoặc 7C.
