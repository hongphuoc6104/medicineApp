# Data

Thư mục này chứa dataset, database files và các output script liên quan đến việc nhận dạng và quản lý đơn thuốc.

## Cấu Trúc Chung
- `input/`: Các file ảnh test đơn thuốc người dùng nạp vào. Để rỗng dần cũng được.
- `output/phase_a/`: Dữ liệu đầu ra sinh tự động từ các luồng test pipeline. Mỗi lần run script test pipeline, thư mục con theo tên ảnh sẽ sinh ra. **Đây là file generated sinh tự động và hoàn toàn có thể xóa an toàn (Safe to delete).**
- `pres/` và `pills/`: Dữ liệu test nội bộ, được giữ lại cho các bài benchmark đánh giá model Pipeline và thử nghiệm nhận dạng ảnh Phase B.

## Databases & Nguồn Dữ Liệu Thuốc (Source-of-Truth)

Hệ thống sử dụng các database tĩnh dạng JSON/CSV phân loại như sau (Database thật nằm trên Postgres, đây là kho metadata tra cứu của AI Python):

1. **`drug_db_vn_full.json` (Database Chính)**: 
   - Đây là CSDL gốc của toàn bộ sản phẩm. File có kích thước lớn, chứa hơn 9,284 loại thuốc lưu hành tại Việt Nam. AI Pipeline (Phase A) sử dụng bảng này nội bộ để fuzzy-search nhận diện tên hoạt chất / thuốc thương mại và sửa sai chính tả.
   - Nó thay thế cho tệp `drug_db_vn.csv` (316 bản ghi cũ) hồi MVP ban đầu. Mọi update cần focus vào file này hoặc gọi crawler API nếu thêm.
2. `vaipe_drugs_kb.json`:
   - Knowledge Base bóc tách từ tập VAIPE cũ, không còn là CSDL cốt lõi của MedicineApp. Nó được giữ lại để tham khảo chéo kiến trúc cũ và làm lookup bổ trợ, nếu cần nhưng không phải DB tìm kiếm chính.

## Training Datasets

- `synthetic_train/`: **Dataset Train NER quan trọng nhất hiện tại**. Bộ ảnh giả lập 938 ảnh có nhãn đã được chuẩn hóa mô phỏng đúng cấu trúc gãy dòng, cách trình bày y hệt bảng thuốc ngoài đời thực (Có số thứ tự, Tên, Số lượng, Lời dặn). PhoBERT sử dụng tập này để bóc tách 1 cột chữ nối liền thành Tên thuốc/Cách dùng chính xác.
- `ner_dataset/`: Tập train PhoBERT cũ hơn tạo từ dữ liệu VAIPE gốc, cấu trúc từng ô rời rạc.

## Generator Scripts
- `createPrescription/prescription_generator/README.md`: Hướng dẫn script lập trình tự sinh ảnh đơn thuốc giả lập để bổ sung vào `synthetic_train`.
