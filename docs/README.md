# Docs — Tài Liệu

Tài liệu dự án được cấu trúc hóa để tách biệt các hướng dẫn đang thi hành (Active), tài liệu module, và lịch sử nghiên cứu (Archive).

## 1. Nguồn Active Hiện Tại (Core)

Các tài liệu chính cần đọc trước và thường xuyên đối chiếu khi lập trình hoặc phát triển hệ thống:

| File | Vai trò |
|------|---------|
| `../AGENTS.md` | Bối cảnh repo, guardrails kỹ thuật, rules bắt buộc cho Agents. Luôn đọc đầu tiên. |
| `../APP_ACTIVE_GENERAL_PLAN.md` | Kế hoạch phát triển chung mức tổng quan (Product roadmap). |
| `../APP_ACTIVE_DETAILED_PLAN.md` | Quy tắc thực thi chi tiết, workstreams, thiết lập Release Gates. |
| `../PIPELINE_STATUS.md` | Trạng thái kỹ thuật cụ thể của OCR AI Pipeline. |
| `UONG_THUOC_FULL_TEST_PLAN.md` | Kịch bản test E2E và release gate cho luồng chính của user. |
| `project_status.md` | Tiến độ hệ thống: what's done, blockers, trạng thái phase. |
| `phase_a_debug_runbook.md` | Runbook/Hướng dẫn debug chi tiết khi gặp lỗi với pipeline scan. |
| `MASTER_PLAN.md` | Kiến trúc hệ thống và luồng thiết kế ban đầu. (Là kiến trúc nền tảng, không phải active execution plan). |

## 2. Tài Liệu Theo Modules (Module Docs)

Mỗi module sẽ có README riêng để hướng dẫn chạy cục bộ và document api/features của module đó.
- `../mobile/README.md` - Lệnh chạy test, run app Flutter, architecture client.
- `../server-node/README.md` - Node.js Backend routes (`/api/auth`, `/api/medication-plans`,...), DB schemas.
- `../server/README.md` - FastAPI AI bridge routes và ports.
- `../core/phase_a/README.md` - Core logic của pipeline 5 bước trích xuất JSON.
- `../data/README.md` - Dataset và databases (`drug_db_vn_full.json`).
- `../scripts/README.md` - Hướng dẫn dùng script để chạy test rời pipeline.

## 3. Agent-Only Docs

Tài liệu được thiết kế chỉ cho AI Assistant đọc, người không cần xem trực tiếp.
- `../.agent/agent_kit_medicineapp.md`
- `../.agent/agent_kit_rollout.md`

## 4. History / Reports / Training (Archive)

Các file nghiên cứu cũ, plan cũ, bản báo cáo hoàn thành batch tính năng, đồ án tốt nghiệp hiện tại đã được dời vào folder `../archive/`. Chúng chỉ dùng để tham chiếu lịch sử:
- `../archive/docs/master_plan.md` *(Superseded by MASTER_PLAN.md)*
- `../archive/docs/phase_b_mvp_lite_plan.md` *(Superseded/Hold)*
- `../archive/docs/phase_b_dose_verification_completed.md` *(Phase B Hold)*
- `../archive/docs/SYSTEM_EVALUATION.md` *(Các điểm cần thiết đã được đưa vào project_status.md)*
- `../archive/docs/COLAB_SETUP.md` & `../archive/docs/resume_on_new_account.md` *(Đào tạo Zero-PIMA)*

*Lưu ý: Không dùng các plan nằm trong `archive/` làm cơ sở logic cho tính năng bạn đang viết trừ khi hệ thống có conflict liên quan đến luồng thiết kế cũ.*
