# Detailed Plan — Gemini 3.1 Pro — Lát Cắt 7A

## Mục tiêu

Làm cho màn quét đơn thuốc thực dụng hơn, tự động hơn, và phù hợp người lớn tuổi hơn.

---

## Phạm vi được sửa

- `mobile/lib/features/create_plan/presentation/scan_camera_screen.dart`
- `mobile/lib/features/create_plan/data/scan_camera_controller.dart`
- `mobile/lib/features/create_plan/data/local_quality_gate.dart`

## Không được sửa

- `drug_entry_sheet.dart`
- `set_schedule_screen.dart`
- backend Node/Python
- file Phase B
- `scripts/run_pipeline.py`

---

## Việc phải làm

1. Làm rõ UX quét theo hướng:
   - đưa vùng thuốc vào khung
   - khi mở camera lên, app liên tục tự đánh giá preview
   - gặp khung hình đủ tốt thì tự lấy ảnh và gửi quét
   - nút chụp tay chỉ là fallback phụ, không phải flow chính
2. Rà và giảm cảm giác preview/capture bị mờ nếu có thể trong phạm vi mobile.
3. Đổi quality gate để không ép phải thấy trọn cả đơn thuốc, chỉ cần đủ rõ vùng thuốc/bảng thuốc.
4. Làm copy ngắn gọn, dễ hiểu hơn cho người lớn tuổi.

---

## Tiêu chí xong

- màn quét dễ dùng hơn rõ rệt
- flow chính là continuous auto scan / auto capture
- quality gate thực dụng hơn
- `flutter analyze` và `flutter test` pass

---

## Luật dừng

Phải dừng nếu:

- cần sửa file ngoài 3 file scope
- phải đụng contract scan/backend để hoàn thành
- thay đổi lan sang review/schedule flow

Khi xong lát cắt này, phải dừng để user test trước khi mở lát cắt tiếp theo.
