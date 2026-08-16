# Experiment Runs & Training Logs (`runs/`)

## Mục đích và Mô tả
Thư mục này lưu trữ nhật ký thực nghiệm (experiment telemetry) và metrics theo dõi quá trình huấn luyện:
- TensorBoard event logs (`events.out.tfevents.*`).
- Weights & Biases offline run files (`wandb/`).
- MLflow tracking metadata (`mlruns/`).
- Text log files ghi lại chi tiết loss, learning rate và metrics đánh giá qua từng epoch.

## Lý do bị Gitignore
1. **Dữ liệu động (Dynamic logs):** Được sinh ra liên tục theo từng bước gradient descent (step/epoch).
2. **Kích thước file log tăng nhanh:** Tránh làm ô nhiễm lịch sử commit Git.

## Hướng dẫn xem trực quan hóa Logs
- Khởi động TensorBoard để theo dõi trực quan loss curves và F1 curves:
  ```bash
  tensorboard --logdir runs/
  ```
- Mở trình duyệt tại `http://localhost:6006` để xem bảng điều khiển.
