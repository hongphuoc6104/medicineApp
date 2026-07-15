# Hồ sơ nâng cấp ML Kit và Progressive Spatial OCR

Thư mục này là nơi duy nhất lưu tài liệu đang hoạt động cho đợt nâng cấp pipeline quét đơn thuốc theo hai hướng:

1. Chuẩn hóa ảnh trên Android bằng Google ML Kit Document Scanner.
2. Tối ưu OCR trên CPU bằng Progressive Spatial OCR with Adaptive Neighborhood Expansion.

Không tạo thêm tài liệu cùng chủ đề ở vị trí khác. Nếu cần bổ sung nội dung, cập nhật một file hiện có hoặc thêm file mới ngay trong thư mục này.

## Nguồn chuẩn

| Mục | Giá trị |
|---|---|
| GitHub | `https://github.com/hongphuoc6104/medicineApp` |
| Baseline chính thức | `main@a6810a392c97593f073a9c5e2b8dfc47027c1911` |
| Hướng triển khai | Tạo nhánh/worktree mới từ baseline chính thức |
| Mobile scanner | Native Android bridge, ML Kit Document Scanner `16.0.0` |
| Đầu ra scanner | Một trang JPEG, `SCANNER_MODE_FULL` |
| OCR chính | Paddle text detection + VietOCR recognition |
| Mục tiêu runtime | Chạy AI server hoàn toàn trên CPU với latency chấp nhận được |
| Nguyên tắc cleanup | Giữ khả năng tái lập, xóa dead code, chưa xóa fallback trước benchmark |

## Thứ tự đọc

| Thứ tự | File | Vai trò |
|---:|---|---|
| 1 | `01_CONG_VIEC_CAN_LAM.md` | Phạm vi, thứ tự thực hiện, checklist và tiêu chí hoàn thành |
| 2 | `02_HIEN_TRANG_VA_BASELINE.md` | Hiện trạng Git, pipeline và số liệu baseline cần khóa |
| 3 | `03_KIEN_TRUC_MUC_TIEU.md` | Kiến trúc ML Kit, Progressive OCR và chính sách CPU |
| 4 | `04_KE_HOACH_KIEM_THU.md` | Danh sách test bắt buộc và điều kiện pass/fail |
| 5 | `05_DEBUG_VA_QUAN_SAT.md` | Artifact, trace, log, bảo vệ dữ liệu và quy trình debug |
| 6 | `06_BENCHMARK_VA_DOI_CHIEU.md` | Cấu hình A/B/C, ablation, metrics và cách so sánh |
| 7 | `07_PHAM_VI_DON_DEP.md` | Phần xóa ngay, xóa có điều kiện và phần bắt buộc giữ |
| 8 | `08_NHAT_KY_QUYET_DINH.md` | Các quyết định kỹ thuật đã khóa và thay đổi sau này |
| 9 | `09_BAO_CAO_KET_QUA.md` | Mẫu tổng hợp kết quả mỗi đợt chạy test/benchmark |

## Quy tắc cập nhật

1. Trước khi code, cập nhật trạng thái work package trong `01_CONG_VIEC_CAN_LAM.md`.
2. Trước khi tích hợp tính năng mới, tạo test riêng theo `04_KE_HOACH_KIEM_THU.md`.
3. Mọi lần chạy có tạo số liệu phải ghi `run_id`, commit, cấu hình và môi trường vào `09_BAO_CAO_KET_QUA.md`.
4. Mọi thay đổi về kiến trúc hoặc tiêu chí giữ/xóa phải ghi vào `08_NHAT_KY_QUYET_DINH.md`.
5. Không dùng artifact cũ làm bằng chứng nếu không xác định được commit, model và cấu hình sinh ra nó.
6. Không lưu ảnh đơn thuốc thật hoặc OCR text chứa dữ liệu bệnh nhân trong Git.

## Trạng thái

| Ký hiệu | Ý nghĩa |
|---|---|
| `TODO` | Chưa bắt đầu |
| `IN_PROGRESS` | Đang thực hiện |
| `BLOCKED` | Bị chặn và cần quyết định hoặc dữ liệu |
| `DONE` | Đã hoàn thành và có bằng chứng kiểm chứng |
| `REJECTED` | Đã thử nhưng không đạt tiêu chí |
