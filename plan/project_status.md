# MedicineApp — Project Status (Updated 2026-03-01)

## 🔄 Đang chạy
- **Zero-PIMA fine-tune BVĐK format**: Epoch 51→100, Colab Pro T4
  - Notebook: `resume_zero_pima_bvdk.ipynb`
  - Checkpoint auto-save: HuggingFace `PhuocHong/zero-pima-checkpoints`
  - Drive backup: https://drive.google.com/drive/folders/1wScCChhfnkgZ_bAZ7Mll0OX3VbLPL0wz

## ✅ Đã hoàn thành

| Việc | File chính |
|------|-----------|
| YOLO11-seg detection model | `models/weights/best.pt` |
| PaddleOCR pipeline (VN) | `core/ocr/` |
| OCR→Zero-PIMA converter | `core/converter/ocr_to_pima.py` |
| Drug mapper (fuzzy match) | `core/converter/drug_mapper.py` |
| VAIPE dataset (21.9GB) | Kaggle `kusnguyen/full-vaipe` |
| BVĐK dataset: 938 train đơn thuốc | `data/synthetic_train/` |
| Zero-PIMA train 50 epoch (VAIPE) | best_loss=1.6923 |
| Colab notebook (BVĐK fine-tune) | `resume_zero_pima_bvdk.ipynb` |
| HuggingFace checkpoint storage | `PhuocHong/zero-pima-checkpoints` |
| PDF in thử (20 mẫu) | `data/synthetic_train/print_20_samples.pdf` |
| BVĐK test dataset (118 đơn, 286 thuốc) | `data/synthetic_train/pres/test/` |
| Evaluation script | `scripts/evaluate.py` |

## ❌ Chưa làm (theo ưu tiên)

| # | Việc | Ưu tiên |
|---|------|---------|
| 1 | Inference pipeline (load model → match) | 🔴 Cao |
| 2 | BVĐK test dataset (118 đơn) | 🔴 Cao |
| 3 | End-to-end test (In → Chụp → Pipeline) | 🟡 TB |
| 4 | Data augmentation | 🟡 TB |
| 5 | FastAPI server | 🟡 TB |
| 6 | Flutter App | 🟢 Thấp |

## Thông tin kỹ thuật

- **Checkpoint format best**: `{model_loc, model_match, epoch, loss}`
- **Checkpoint format full**: `{epoch, model_loc, model_match, opt_loc, opt_match, best_loss, history}`
- **Training config**: LR=1e-6, batch=1 (bắt buộc), FRCNN MobileNetV3 + GCN + SBERT
- **Known issue**: Cell 5b (gt_feature patch) KHÔNG chạy 2 lần → RecursionError
