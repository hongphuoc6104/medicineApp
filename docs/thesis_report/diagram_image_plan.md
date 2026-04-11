# Plan Hình Ảnh Và Sơ Đồ Cho Báo Cáo

## 1. Mục tiêu

Tài liệu này chốt các hình ảnh và sơ đồ cần bổ sung cho báo cáo niên luận của dự án `MedicineApp`.

Nguyên tắc chọn hình và sơ đồ:

- Chỉ thêm những hình thật sự giúp người đọc hiểu bài nhanh hơn.
- Mỗi hình hoặc sơ đồ phải thay thế được một phần chữ, không chỉ để trang trí.
- Ưu tiên luồng chính của đề tài: quét đơn thuốc, rà soát kết quả, lập lịch dùng thuốc, xem lịch hôm nay.
- Không dành quá nhiều dung lượng cho các chức năng chưa đưa vào phiên bản chính.

## 2. Danh sách hình ảnh cần có

### Hình 1. Ảnh đầu vào đơn thuốc thực tế

- Mục đích: cho người đọc thấy bài toán đầu vào là ảnh giấy thật, không phải dữ liệu quá sạch.
- Vị trí nên đặt: Chương 1 hoặc đầu Chương 2.
- Nguồn: chọn một ảnh mẫu từ `data/input/`.
- Lưu ý: che hoặc cắt bỏ thông tin cá nhân nếu ảnh có tên bệnh nhân.

### Hình 2. Kết quả sau bước phát hiện và cắt vùng đơn thuốc

- Mục đích: minh họa bước đầu của mô-đun AI.
- Vị trí nên đặt: Chương 4, phần cài đặt mô-đun quét đơn thuốc.
- Nguồn: xuất từ kết quả debug của pipeline hoặc từ thư mục `data/output/phase_a/...` nếu có ảnh trung gian.

### Hình 3. Kết quả OCR hoặc danh sách thuốc sau nhận diện

- Mục đích: minh họa đầu ra trung gian của hệ thống trước khi người dùng rà soát.
- Vị trí nên đặt: Chương 4 hoặc Chương 5.
- Nguồn: `summary.json`, ảnh debug, hoặc màn hình rà soát thuốc trong app.

### Hình 4. Màn hình quét đơn thuốc trên ứng dụng

- Mục đích: thể hiện giao diện đầu vào chính của người dùng.
- Vị trí nên đặt: Chương 4, phần cài đặt ứng dụng di động.
- Nguồn: chụp màn hình từ `scan_camera_screen.dart` hoặc `scan_screen.dart` khi chạy app.

### Hình 5. Màn hình xác nhận kết quả quét

- Mục đích: cho thấy đề tài không dùng kết quả AI một cách tuyệt đối mà có bước rà soát.
- Vị trí nên đặt: Chương 4 hoặc Chương 5.
- Nguồn: chụp màn hình từ `scan_review_screen.dart`.

### Hình 6. Màn hình lập lịch dùng thuốc

- Mục đích: minh họa đầu ra có giá trị thực tế của đề tài.
- Vị trí nên đặt: Chương 4.
- Nguồn: chụp màn hình từ `set_schedule_screen.dart`.

### Hình 7. Màn hình trang chủ hoặc lịch dùng thuốc hôm nay

- Mục đích: cho thấy hệ thống không chỉ quét đơn mà còn hỗ trợ theo dõi việc dùng thuốc.
- Vị trí nên đặt: Chương 4 hoặc Chương 5.
- Nguồn: chụp màn hình từ `home_screen.dart` hoặc `plan_detail_screen.dart`.

### Hình 8. Minh họa giới hạn của chức năng xác minh viên thuốc

- Mục đích: hỗ trợ cho lập luận vì sao chưa tích hợp chức năng này vào phiên bản chính.
- Vị trí nên đặt: Chương 5, phần giới hạn và hướng chưa tích hợp.
- Nguồn: có thể là ảnh mô tả hai viên thuốc gần giống nhau, hoặc hình minh họa tự dựng bằng sơ đồ đơn giản nếu chưa có ảnh thực tế phù hợp.

## 3. Danh sách sơ đồ nên có

### Sơ đồ 1. Sơ đồ tổng quan bài toán

- Loại sơ đồ: sơ đồ khối.
- Nội dung:
  - Đơn thuốc giấy
  - Quét và nhận diện thuốc
  - Rà soát kết quả
  - Lập lịch dùng thuốc
  - Theo dõi dùng thuốc
- Vị trí nên đặt: Chương 1.
- Mục đích: giúp người đọc nắm nhanh toàn bộ đề tài chỉ trong một hình.

### Sơ đồ 2. Sơ đồ kiến trúc hệ thống

- Loại sơ đồ: sơ đồ khối kiến trúc.
- Nội dung:
  - Ứng dụng di động Flutter
  - Máy chủ Node.js
  - Dịch vụ AI FastAPI
  - PostgreSQL
  - Cơ sở dữ liệu thuốc
- Vị trí nên đặt: Chương 3.
- Ghi chú: đây là sơ đồ bắt buộc nên có.

### Sơ đồ 3. Sơ đồ luồng xử lý quét đơn thuốc

- Loại sơ đồ: lưu đồ hoặc sơ đồ khối theo chuỗi.
- Nội dung:
  - Ảnh đầu vào
  - Phát hiện vùng đơn
  - Tiền xử lý ảnh
  - OCR
  - Tách tên thuốc
  - Đối sánh cơ sở dữ liệu thuốc
  - Danh sách thuốc để rà soát
- Vị trí nên đặt: Chương 3 hoặc Chương 4.

### Sơ đồ 4. Sơ đồ tuần tự cho chức năng quét đơn thuốc

- Loại sơ đồ: sơ đồ tuần tự.
- Tác nhân:
  - Người dùng
  - Ứng dụng di động
  - Máy chủ Node.js
  - Dịch vụ AI FastAPI
  - Cơ sở dữ liệu
- Vị trí nên đặt: Chương 3.
- Mục đích: làm rõ dữ liệu đi qua các thành phần như thế nào.

### Sơ đồ 5. Sơ đồ use case mức hệ thống

- Loại sơ đồ: use case.
- Tác nhân chính: Người dùng.
- Chức năng nên thể hiện:
  - Đăng nhập
  - Quét đơn thuốc
  - Xác nhận thuốc
  - Lập lịch dùng thuốc
  - Xem kế hoạch hôm nay
  - Ghi nhận đã uống hoặc bỏ qua
  - Xem lịch sử quét
- Vị trí nên đặt: Chương 3.
- Ghi chú: chỉ nên có một use case tổng quát, không nên vẽ quá nhiều use case nhỏ.

### Sơ đồ 6. Sơ đồ hoạt động cho luồng tạo kế hoạch dùng thuốc

- Loại sơ đồ: activity diagram.
- Nội dung:
  - Người dùng quét đơn
  - Hệ thống trả kết quả
  - Người dùng sửa hoặc thêm thuốc nếu cần
  - Người dùng chọn ngày bắt đầu và số ngày dùng
  - Người dùng chọn khung giờ và số viên
  - Hệ thống lưu kế hoạch
- Vị trí nên đặt: Chương 3 hoặc Chương 4.

### Sơ đồ 7. Sơ đồ dữ liệu mức khái niệm hoặc mức logic

- Loại sơ đồ: CDM hoặc ERD.
- Nên ưu tiên nhóm bảng mới đang dùng cho luồng chính:
  - `prescription_plans`
  - `prescription_plan_drugs`
  - `prescription_plan_slots`
  - `prescription_plan_slot_drugs`
  - `prescription_plan_logs`
  - `users`
  - `scans`
  - `scan_sessions`
- Vị trí nên đặt: Chương 3.
- Ghi chú rất quan trọng:
  - Không nên đưa toàn bộ bảng phụ về xác minh viên thuốc vào sơ đồ chính.
  - Nếu muốn nhắc tới chức năng chưa tích hợp, chỉ mô tả bằng một đoạn chữ ở Chương 5 là đủ.

### Sơ đồ 8. Sơ đồ luồng dữ liệu cho chức năng lập lịch và ghi nhận dùng thuốc

- Loại sơ đồ: sơ đồ khối hoặc activity diagram.
- Nội dung:
  - Tạo kế hoạch
  - Sinh khung giờ dùng thuốc
  - Nhắc uống
  - Ghi nhận trạng thái
  - Lưu nhật ký
- Vị trí nên đặt: Chương 4 hoặc Chương 5.

## 4. Những sơ đồ không nên ưu tiên

- Không nên vẽ class diagram chi tiết cho Flutter hoặc Node.js vì dễ nặng kỹ thuật mà không tăng nhiều giá trị học thuật.
- Không nên vẽ sơ đồ riêng cho chức năng xác minh viên thuốc nếu phần đó chưa phải trọng tâm sản phẩm.
- Không nên vẽ quá nhiều sơ đồ nhỏ giống nhau giữa Chương 3 và Chương 4.

## 5. Thứ tự ưu tiên khi bổ sung

### Nhóm bắt buộc

1. Sơ đồ tổng quan bài toán
2. Sơ đồ kiến trúc hệ thống
3. Sơ đồ luồng xử lý quét đơn thuốc
4. Sơ đồ dữ liệu mức khái niệm hoặc mức logic
5. Ảnh màn hình quét đơn thuốc
6. Ảnh màn hình xác nhận kết quả quét
7. Ảnh màn hình lập lịch dùng thuốc

### Nhóm nên có

1. Sơ đồ tuần tự quét đơn thuốc
2. Sơ đồ hoạt động của luồng tạo kế hoạch
3. Ảnh trang chủ hoặc lịch hôm nay
4. Hình minh họa đầu vào và đầu ra của mô-đun AI

### Nhóm chỉ thêm nếu còn chỗ

1. Use case tổng quát
2. Hình minh họa giới hạn của xác minh viên thuốc

## 6. Công cụ nên dùng để vẽ

## 6.1. Công cụ phù hợp nhất

### Draw.io hoặc diagrams.net

- Phù hợp nhất cho:
  - sơ đồ kiến trúc
  - use case
  - activity diagram
  - ERD hoặc CDM
- Ưu điểm:
  - dễ kéo thả
  - xuất PNG hoặc SVG tốt
  - chỉnh bằng tay nhanh
  - phù hợp cho báo cáo đại học
- Khuyến nghị: dùng công cụ này cho gần như toàn bộ sơ đồ chính của báo cáo.

## 6.2. Công cụ phù hợp nếu muốn quản lý bằng mã

### Mermaid

- Phù hợp cho:
  - flowchart
  - sequence diagram
  - ER diagram đơn giản
- Ưu điểm:
  - viết nhanh bằng text
  - dễ lưu trong repo
- Nhược điểm:
  - khó chỉnh đẹp bằng draw.io khi cần thẩm mỹ báo cáo

### PlantUML

- Phù hợp cho:
  - use case
  - sequence diagram
  - activity diagram
  - class diagram
- Ưu điểm:
  - mạnh và chuẩn cho UML
- Nhược điểm:
  - cần công cụ dựng hoặc máy chủ dựng riêng
  - mất thời gian hơn nếu chỉ cần vài sơ đồ cho báo cáo niên luận

## 6.3. Tình trạng công cụ trên máy hiện tại

Qua kiểm tra nhanh trong môi trường làm việc hiện tại, chưa thấy sẵn công cụ dòng lệnh rõ ràng cho:

- PlantUML
- Mermaid CLI
- Draw.io bản dòng lệnh
- Graphviz

Vì vậy, phương án thực tế nhất hiện tại là:

1. Dùng draw.io hoặc diagrams.net để vẽ thủ công các sơ đồ chính.
2. Xuất ra PNG hoặc SVG.
3. Chèn vào LaTeX sau cùng.

## 7. Về MCP để vẽ sơ đồ

Trong môi trường hiện tại, không có danh sách MCP chuyên biệt nào được cấu hình sẵn để tôi gọi trực tiếp cho việc vẽ sơ đồ kiểu CDM, use case hoặc activity diagram.

Nếu sau này bạn dùng môi trường có MCP, nhóm MCP nên tìm là:

- MCP cho `draw.io` hoặc `diagrams.net`
- MCP cho `Mermaid`
- MCP cho `PlantUML`
- MCP cho `Graphviz`

Nếu không có MCP, draw.io vẫn là lựa chọn tốt nhất cho báo cáo này.

## 8. Đề xuất cuối cùng cho báo cáo này

Đối với bài niên luận hiện tại, bộ sơ đồ và hình nên chốt như sau:

1. Một sơ đồ tổng quan bài toán
2. Một sơ đồ kiến trúc hệ thống
3. Một sơ đồ luồng xử lý quét đơn thuốc
4. Một sơ đồ dữ liệu cho nhóm bảng kế hoạch dùng thuốc và lịch sử quét
5. Một sơ đồ tuần tự cho chức năng quét đơn
6. Ba ảnh giao diện chính:
   - màn hình quét đơn
   - màn hình xác nhận kết quả quét
   - màn hình lập lịch dùng thuốc
7. Một ảnh màn hình lịch hôm nay hoặc chi tiết kế hoạch

Tổng cộng, báo cáo nên có khoảng 7 đến 9 hình hoặc sơ đồ là hợp lý. Số lượng này đủ để bài nhìn chặt chẽ và sinh động hơn, nhưng chưa quá nhiều so với phạm vi một niên luận.
