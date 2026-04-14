# Phase B - Xác Minh Thuốc Trực Quan (On Hold)

**Tình trạng:** Quá trình phát triển luồng này đang nằm ở mục **HOLD** và đóng vai trò như code cơ sở nghiên cứu (Experimental). Hệ thống MVP và backend scan app đang chú trọng vào Reminder và OCR.

## Tổng Quan

Mục tiêu ban đầu của Phase này là chạy Zero-Shot FRCNN detection để dò tìm các viên rời rạc có trên tay hoặc rải trên bàn, tiếp theo sử dụng Graph Convolutional Network (GCN) cùng Contrastive Learning so khớp chúng với ảnh Pill chuẩn.

Tuy nhiên, hướng tiếp cận hiện tại thay đổi. Module này không còn thiết kế theo kiểu GCN nhận diện chủ động khép kín. Hướng tới tương lai:
**Assisted Verification/Reference-based (Xác minh có trợ giúp):**
- System sẽ cung cấp Database hình ảnh và ID viên thuốc.
- Người dùng chỉ chụp lại hoặc so sánh tham chiếu. AI sẽ chỉ gợi ý Reference/Lookup Match, tránh tình trạng rủi ro y tế khi mạng GCN đưa ra quyết định sai hoàn toàn cho viên thuốc có màu tương đương.

## Tại Sao Hold Core B?
1. Tập trung tối ưu Backend thuốc, luồng Reconciliation & Luồng nhắc nhở bệnh nhân.
2. Thiếu dataset hình dạng các viên thuốc nội địa (VAIPE có hạn chế độ tin cậy ở Pill detection model).
3. Đòi hỏi fix code lõi sâu (patched `roi_heads.py`) cho zero-PIMA, không thích hợp ở mức Production v1 hiện tại.
