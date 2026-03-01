# Colab Setup — Tài khoản mới, không cần Drive cũ

## Yêu cầu
- Tài khoản Google mới
- Kaggle account (lấy API key tại kaggle.com → Settings → API)
- File `zero_pima_training.ipynb` đã upload lên Colab

---

## Bước 1 — Mở notebook trên Colab mới

1. Vào [colab.research.google.com](https://colab.research.google.com)
2. **File → Upload notebook** → chọn `Zero-PIMA/zero_pima_training.ipynb`
3. **Runtime → Change runtime type → T4 GPU**
4. Mount Drive: chạy cell đầu tiên

---

## Bước 2 — Upload Kaggle API key (1 lần duy nhất)

```python
# Chạy cell này đầu tiên
import os
from google.colab import files

# Upload file kaggle.json từ máy tính
# (tải tại: kaggle.com → Settings → API → Create New Token)
files.upload()  # chọn kaggle.json

os.makedirs(os.path.expanduser("~/.kaggle"), exist_ok=True)
os.rename("kaggle.json", os.path.expanduser("~/.kaggle/kaggle.json"))
os.chmod(os.path.expanduser("~/.kaggle/kaggle.json"), 0o600)
print("✅ Kaggle API key configured")
```

---

## Bước 3 — Download và setup data

```python
import os, zipfile, glob

SAVE_DIR = '/content/drive/MyDrive/medicine_models'
DATA_DIR = '/content/data'
os.makedirs(SAVE_DIR, exist_ok=True)

# Download pill dataset từ Kaggle
print("Downloading pill dataset...")
os.system("kaggle datasets download -d alexanderyotann/pills-detection-dataset -p /content/")

# Extract
print("Extracting...")
with zipfile.ZipFile('/content/pills-detection-dataset.zip', 'r') as z:
    z.extractall('/content/raw_data/')

# Kiểm tra cấu trúc
print("Files:", glob.glob('/content/raw_data/**', recursive=True)[:10])
```

> Sau khi extract xong, chạy cell **Setup Data Directories** trong notebook
> để copy vào đúng cấu trúc `/content/data/pills/train|test/imgs|labels`

---

## Bước 4 — Backup data lên Drive ngay (QUAN TRỌNG)

```python
# Chạy ngay sau khi setup data xong, TRƯỚC KHI train
import shutil

BACKUP = '/content/drive/MyDrive/medicine_data_backup'
if not os.path.exists(BACKUP):
    print("Backing up data to Drive (chỉ cần chạy 1 lần)...")
    shutil.copytree('/content/data', BACKUP)
    print(f"✅ Backed up to {BACKUP}")
else:
    print("✅ Backup existed")
```

---

## Bước 5 — Chạy training

Chạy cell **Step 6 (Train Faster R-CNN)** trong notebook.

Training đã tích hợp:
- ✅ **Checkpoint save** sau mỗi epoch → `medicine_models/checkpoint_last.pth`
- ✅ **Resume tự động** nếu bị ngắt kết nối
- ✅ **Best model** → `medicine_models/localization_best.pth`

---

## Khi Colab bị reset (lần sau)

Chạy cell restore data:
```python
import shutil, os
BACKUP = '/content/drive/MyDrive/medicine_data_backup'
if os.path.exists(BACKUP):
    shutil.copytree(BACKUP, '/content/data', dirs_exist_ok=True)
    print("✅ Data restored")
```

Rồi chạy lại training cell → tự resume từ epoch bị dừng.

---

## Cấu hình training (Step 6)

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| EPOCHS | 30 | Tăng lên 50 nếu muốn tốt hơn |
| BATCH_SIZE | 8 | Giảm xuống 4 nếu OOM |
| LR | 1e-4 | Giữ nguyên |
| MAX_TRAIN | None | Dùng toàn bộ ~10,159 ảnh |

Expected loss progression:
- Epoch 1-3: ~0.38-0.42
- Epoch 5-10: ~0.28-0.32
- Epoch 15-20: ~0.22-0.26
- Epoch 25-30: ~0.18-0.22
