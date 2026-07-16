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
| `BLOCKED_ENV` | Code/contract đã kiểm tra nhưng môi trường thiếu dependency hoặc quyền cần thiết |
| `PENDING_PREFLIGHT` | Chưa được phép chạy vì approval, privacy, asset hoặc provenance gate chưa đạt |
| `IMPLEMENTATION_DONE` | Code và disposable verification xong; rollout production còn gate riêng |
| `TOOLING_DONE_PREFLIGHT_BLOCKED` | Tooling xong nhưng run thực tế vẫn bị preflight chặn |
| `DONE` | Đã hoàn thành và có bằng chứng kiểm chứng |
| `PASS` | Run hoặc lane verification đã đạt acceptance trong phạm vi ghi nhận |
| `IMPLEMENTATION_PASS` | Implementation/disposable verification đạt, nhưng không suy diễn là production rollout hoàn tất |
| `REJECTED` | Đã thử nhưng không đạt tiêu chí |

## Snapshot triển khai 2026-07-16

| Hạng mục | Trạng thái | Bằng chứng / blocker |
|---|---|---|
| WP-03B | DONE | Safety fixture `16/16`; integrated Python targeted `52/52`; Node disposable full `104/104` |
| Flutter/FastAPI Phase B ingress | DONE | Retired deep links/endpoints về fallback hoặc `404`; Flutter full chỉ còn 2 Home baseline failures |
| WP-05A | BLOCKED_ENV | Dart/Kotlin contracts và ML Kit `16.0.0` đạt; Android debug build chờ NDK `28.2.13676358` và accepted license |
| CLEAN-07 | IMPLEMENTATION_DONE | Fresh schema không tạo 7 bảng; disposable retirement `6/6`; không database thật nào đã drop |
| WP-01A | DONE | Tooling `20/20`, no-copy locator, explicit asset binding, exact coverage/provenance/report gates |
| WP-01B/C | PENDING_PREFLIGHT | Chờ approval bind đúng manifest, privacy approval, debug-retention deadline và clean `a6810a3` worktree |

Không ghi CPU/GPU baseline metrics trước khi hai run WP-01 được preflight phê duyệt. Chi tiết và run registry nằm trong `09_BAO_CAO_KET_QUA.md`.
