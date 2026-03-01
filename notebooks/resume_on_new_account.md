# 🧬 Hướng Dẫn Train Zero-PIMA trên Colab Pro (Tài Khoản Mới)

## Files cần có trên máy

| File | Kích thước | Vị trí trên máy | Bắt buộc? |
|------|-----------|-----------------|-----------|
| `Zero-PIMA.zip` | 35KB | `Desktop/medicineApp/Zero-PIMA.zip` | ✅ Bắt buộc |
| `localization_best.pth` | 73MB | `Desktop/medicineApp/localization_best.pth` | ✅ FRCNN pretrained |
| `zero_pima_checkpoint.pth` | ~685MB | Từ Colab cũ (Cell 9) | ⚡ Nếu resume |

## Setup Colab

1. **Tạo notebook mới** trên Colab Pro
2. **Runtime → Change runtime type → L4 GPU (hoặc T4)**
3. **Runtime → Enable High-RAM** (nếu có option)
4. **Upload** file [resume_zero_pima_pro.ipynb](file:///home/hongphuoc/Desktop/medicineApp/notebooks/resume_zero_pima_pro.ipynb)

## Chạy theo thứ tự

| Cell | Làm gì | Thời gian |
|------|--------|-----------|
| **1** | Install packages + keep-alive | ~1 phút |
| **2** | JS keep-alive | 1 giây |
| **3** | Upload `Zero-PIMA.zip` + `.pth` files | ~2 phút |
| **4** | Download VAIPE | ~4-17 phút |
| **5** | Setup data | ~1 phút |
| **6** | Load models + resume checkpoint | ~30 giây |
| **7** | Fix gt_feature (monkey-patch) | ~5 giây |
| **8** | **TRAIN** | ~6 giờ (50 epoch) |
| **9** | Download checkpoint về máy | Khi muốn |

## Kết quả mong đợi

**Train từ đầu (có FRCNN pretrained):**
- Epoch 1 Loss: ~6-7 (tốt hơn không có FRCNN)
- Epoch 5: ~3-4
- Epoch 50: ~1-2

**Resume từ checkpoint:**
```
⏩ Resumed epoch X, best=Y.YYYY
```

## Lưu ý quan trọng

- **Trước khi đi ngủ:** Đảm bảo Cell 8 đang chạy, keep-alive đã ON
- **Sau khi train:** Chạy Cell 9 để download checkpoint về máy ngay
- **Nếu Colab ngắt:** Upload lại checkpoint → chạy lại từ Cell 1
