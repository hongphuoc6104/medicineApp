# Model Checkpoints Directory (`checkpoints/`)

## Mục đích và Mô tả
Thư mục này dùng để lưu trữ các điểm kiểm tra trạng thái trọng số mô hình (model checkpoints) trong quá trình huấn luyện:
- PyTorch state dictionaries (`*.pt`, `*.pth`, `*.ckpt`).
- Hugging Face Transformers model weights (`model.safetensors`, `pytorch_model.bin`).
- Tokenizer vocabularies và optimizer states (`optimizer.pt`, `scheduler.pt`).

## Lý do bị Gitignore
1. **Dung lượng tệp lớn:** Mỗi checkpoint transformer (PhoBERT, BamiBERT, ViPubmedDeBERTa) có kích thước từ 400MB đến 1.5GB mỗi epoch.
2. **Quy tắc phát triển an toàn:** Không đưa các tệp nhị phân sinh ra từ quá trình train vào Git tree để duy trì tốc độ clone và fetch repository.

## Hướng dẫn sử dụng
- Khi huấn luyện các baseline E0 - E6, checkpoint tốt nhất (best validation F1) sẽ tự động được lưu vào thư mục này:
  ```bash
  checkpoints/
  ├── e0_phobert_base/
  │   ├── best_model/
  │   └── checkpoint-epoch-10/
  ├── e1_bamibert/
  └── e6_span_pointer/
  ```
- Để tải checkpoint mô hình đã huấn luyện sẵn phục vụ tái lập nghiên cứu, vui lòng tham khảo liên kết lưu trữ trên Google Drive / Hugging Face Release trong tài liệu `PROJECT.md`.
