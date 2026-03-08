# ════════════════════════════════════════════════════════════════════
# Zero-PIMA Training Notebook — Paste từng cell vào Colab
# ════════════════════════════════════════════════════════════════════

# ══ Cell 1: Install Dependencies ══════════════════════════════════
"""
!pip install -q torch torchvision
!pip install -q torch_geometric
!pip install -q sentence-transformers
!pip install -q objdetecteval
!pip install -q wandb
!pip install -q kagglehub
!pip install -q networkx
"""

# ══ Cell 2: Download VAIPE Dataset ════════════════════════════════
"""
import kagglehub
import os

# Download full VAIPE dataset
path = kagglehub.dataset_download("kusnguyen/full-vaipe")
print("Path to dataset files:", path)
print("Contents:", os.listdir(path))

# Kiểm tra cấu trúc
for root, dirs, files in os.walk(path):
    level = root.replace(path, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    if level < 2:
        for f in files[:5]:
            print(f'{indent}  {f}')
        if len(files) > 5:
            print(f'{indent}  ... ({len(files)} files total)')
"""

# ══ Cell 3: Clone Zero-PIMA code ═════════════════════════════════
"""
# Option A: Upload Zero-PIMA folder từ local
# → Zip folder Zero-PIMA, upload lên Colab, unzip

# Option B: Clone từ GitHub (nếu bạn push code lên)
# !git clone https://github.com/YOUR_REPO/Zero-PIMA.git

# Option C: Upload trực tiếp từ Google Drive
from google.colab import drive
drive.mount('/content/drive')

import shutil
ZERO_PIMA_LOCAL = '/content/drive/MyDrive/Zero-PIMA'  # ← sửa path
ZERO_PIMA_DIR = '/content/Zero-PIMA'

if os.path.exists(ZERO_PIMA_LOCAL):
    shutil.copytree(ZERO_PIMA_LOCAL, ZERO_PIMA_DIR, dirs_exist_ok=True)
    print(f"✅ Copied Zero-PIMA to {ZERO_PIMA_DIR}")
else:
    print(f"⚠ {ZERO_PIMA_LOCAL} not found. Please upload Zero-PIMA folder.")
"""

# ══ Cell 4: Setup Data Structure ═════════════════════════════════
"""
import os, shutil, glob

# Path từ kagglehub download
VAIPE_PATH = path  # từ Cell 2
ZERO_PIMA_DIR = '/content/Zero-PIMA'
DATA_DIR = os.path.join(ZERO_PIMA_DIR, 'data')

# Liệt kê nội dung VAIPE để xác định cấu trúc
print("=== VAIPE Dataset Structure ===")
for item in sorted(os.listdir(VAIPE_PATH)):
    full_path = os.path.join(VAIPE_PATH, item)
    if os.path.isdir(full_path):
        n_files = len(os.listdir(full_path))
        print(f"  📁 {item}/ ({n_files} items)")
    else:
        size = os.path.getsize(full_path) / 1024
        print(f"  📄 {item} ({size:.1f} KB)")

# Zero-PIMA expects:
# data/pills/train/imgs/  ← pill images
# data/pills/train/labels/ ← pill labels (JSON: {boxes: [{x,y,w,h,label}]})
# data/pills/test/imgs/
# data/pills/test/labels/
# data/pres/train/         ← prescription JSON [{text, label, box, mapping}]
# data/pres/test/
# data/pill_information.csv

# ⚠ BẠN CẦN SỬA PHẦN DƯỚI CHO ĐÚNG CẤU TRÚC TƯƠNG ỨNG
# Sau khi chạy phần trên, xem output rồi sửa mapping dưới đây

# Ví dụ mapping (sửa cho đúng):
# os.makedirs(f'{DATA_DIR}/pills/train/imgs', exist_ok=True)
# os.makedirs(f'{DATA_DIR}/pills/train/labels', exist_ok=True)
# os.makedirs(f'{DATA_DIR}/pills/test/imgs', exist_ok=True)
# os.makedirs(f'{DATA_DIR}/pills/test/labels', exist_ok=True)
# os.makedirs(f'{DATA_DIR}/pres/train', exist_ok=True)
# os.makedirs(f'{DATA_DIR}/pres/test', exist_ok=True)

# Copy hoặc symlink data vào đúng vị trí
# Ví dụ:
# !ln -s {VAIPE_PATH}/pills_images/train {DATA_DIR}/pills/train/imgs
# !ln -s {VAIPE_PATH}/pills_labels/train {DATA_DIR}/pills/train/labels
# !ln -s {VAIPE_PATH}/prescriptions/train {DATA_DIR}/pres/train
"""

# ══ Cell 5: Patch roi_heads.py ═══════════════════════════════════
"""
import torchvision, shutil

# Tìm roi_heads.py trong torchvision
tv_path = os.path.dirname(torchvision.__file__)
roi_heads_dst = os.path.join(tv_path, 'models', 'detection', 'roi_heads.py')
roi_heads_src = os.path.join(ZERO_PIMA_DIR, 'roi_heads.py')

# Backup original
backup = roi_heads_dst + '.backup'
if not os.path.exists(backup):
    shutil.copy(roi_heads_dst, backup)
    print(f"✅ Backup: {backup}")

# Patch
shutil.copy(roi_heads_src, roi_heads_dst)
print(f"✅ Patched roi_heads.py")
print(f"   src: {roi_heads_src}")
print(f"   dst: {roi_heads_dst}")
"""

# ══ Cell 6: Verify Data ══════════════════════════════════════════
"""
import json, os

DATA_DIR = '/content/Zero-PIMA/data'

# Check pres files
pres_train = os.path.join(DATA_DIR, 'pres', 'train')
pres_test = os.path.join(DATA_DIR, 'pres', 'test')

if os.path.exists(pres_train):
    pres_files = os.listdir(pres_train)
    print(f"✅ Prescriptions train: {len(pres_files)} files")
    # Xem 1 file sample
    sample = os.path.join(pres_train, pres_files[0])
    with open(sample) as f:
        data = json.load(f)
    print(f"   Sample: {pres_files[0]}")
    if isinstance(data, list):
        print(f"   Entries: {len(data)}")
        print(f"   Keys: {data[0].keys() if data else 'empty'}")
        if data:
            print(f"   First: {data[0]}")
else:
    print(f"❌ {pres_train} not found!")

# Check pill images
pills_train_imgs = os.path.join(DATA_DIR, 'pills', 'train', 'imgs')
pills_train_labels = os.path.join(DATA_DIR, 'pills', 'train', 'labels')

if os.path.exists(pills_train_imgs):
    n_imgs = len(os.listdir(pills_train_imgs))
    print(f"✅ Pill train images: {n_imgs}")
else:
    print(f"❌ {pills_train_imgs} not found!")

if os.path.exists(pills_train_labels):
    label_files = os.listdir(pills_train_labels)
    print(f"✅ Pill train labels: {len(label_files)}")
    sample_label = os.path.join(pills_train_labels, label_files[0])
    with open(sample_label) as f:
        data = json.load(f)
    print(f"   Sample: {label_files[0]}")
    print(f"   Keys: {data.keys()}")
    if 'boxes' in data:
        print(f"   Boxes: {len(data['boxes'])}")
        print(f"   First box: {data['boxes'][0]}")
else:
    print(f"❌ {pills_train_labels} not found!")

# Check pill_information.csv  
pill_csv = os.path.join(DATA_DIR, 'pill_information.csv')
if os.path.exists(pill_csv):
    import pandas as pd
    df = pd.read_csv(pill_csv)
    print(f"✅ pill_information.csv: {len(df)} pills")
    print(f"   Columns: {list(df.columns)}")
    print(df.head())
else:
    print(f"❌ {pill_csv} not found!")
"""

# ══ Cell 7: Train Zero-PIMA ═════════════════════════════════════
"""
import os
os.chdir('/content/Zero-PIMA')

# Login wandb (optional — để tracking)
# import wandb
# wandb.login()

# Train command
!python train.py \
    --data-path data/ \
    --train-batch-size 2 \
    --val-batch-size 1 \
    --epochs 50 \
    --lr 1e-5 \
    --run-name "zero-pima-vaipe" \
    --run-group "vaipe-training" \
    --num-workers 2
"""

# ══ Cell 8: Train với checkpoint resume ══════════════════════════
"""
# Nếu cần resume, bạn phải sửa train.py để add checkpoint logic
# Tương tự code Faster R-CNN đã làm:

import torch, os, sys
sys.path.insert(0, '/content/Zero-PIMA')

from models.prescription_pill import PrescriptionPill
from utils.metrics import ContrastiveLoss
from utils.utils import build_loaders, get_model_instance_segmentation
from utils.option import option
import config as CFG

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
SAVE_DIR = '/content/drive/MyDrive/medicine_models'
os.makedirs(SAVE_DIR, exist_ok=True)

# Parse args
import sys
sys.argv = ['train.py',
    '--data-path', 'data/',
    '--train-batch-size', '2',
    '--val-batch-size', '1',
    '--epochs', '50',
    '--lr', '1e-5',
]
args = option()

# Build data
train_pres_list = os.listdir(args.data_path + 'pres/train/')
test_pres_list = os.listdir(args.data_path + 'pres/test/')
args.json_files_test = test_pres_list

train_loader = build_loaders(train_pres_list, mode="train",
    batch_size=args.train_batch_size, num_workers=2, shuffle=True, args=args)
val_loader = build_loaders(test_pres_list, mode="test",
    batch_size=args.val_batch_size, num_workers=2, args=args)

print(f"Train: {len(train_loader.dataset)}, Val: {len(val_loader.dataset)}")

# Build models
model_localization = get_model_instance_segmentation().to(device)
model_matching = PrescriptionPill(args).to(device)
matching_criterion = ContrastiveLoss()
graph_criterion = torch.nn.NLLLoss(
    weight=torch.FloatTensor(CFG.labels_weight).to(device))

optimizer_loc = torch.optim.AdamW(
    model_localization.parameters(), lr=args.lr, weight_decay=5e-4)
optimizer_match = torch.optim.AdamW(
    model_matching.parameters(), lr=args.lr, weight_decay=5e-4)

# Resume checkpoint
CHECKPOINT = f'{SAVE_DIR}/zero_pima_checkpoint.pth'
START_EPOCH = 1
best_loss = float('inf')

if os.path.exists(CHECKPOINT):
    print("⏩ Resuming from checkpoint...")
    ckpt = torch.load(CHECKPOINT, map_location=device)
    model_localization.load_state_dict(ckpt['model_loc'])
    model_matching.load_state_dict(ckpt['model_match'])
    optimizer_loc.load_state_dict(ckpt['opt_loc'])
    optimizer_match.load_state_dict(ckpt['opt_match'])
    START_EPOCH = ckpt['epoch'] + 1
    best_loss = ckpt['best_loss']
    print(f"   Epoch {START_EPOCH}, best_loss={best_loss:.4f}")
else:
    # Load pre-trained Faster R-CNN if available
    FRCNN_BEST = f'{SAVE_DIR}/localization_best.pth'
    if os.path.exists(FRCNN_BEST):
        state = torch.load(FRCNN_BEST, map_location=device)
        if isinstance(state, dict) and 'model_state_dict' in state:
            state = state['model_state_dict']
        model_localization.load_state_dict(state, strict=False)
        print(f"✅ Loaded pre-trained FRCNN: {FRCNN_BEST}")
    print("🆕 Fresh Zero-PIMA training")

# Training loop
from utils.utils import calculate_matching_cross_loss
from tqdm import tqdm

for epoch in range(START_EPOCH, args.epochs + 1):
    model_localization.train()
    model_matching.train()
    epoch_losses = []

    for data in tqdm(train_loader, desc=f'Epoch {epoch}/{args.epochs}'):
        data = data.to(device)
        optimizer_loc.zero_grad()
        optimizer_match.zero_grad()

        # Localization
        pill_image = [img.to(device) for img in data.pill_image]
        pill_label = [{k: v.to(device) for k, v in t[0].items()}
                      for t in data.pill_label_generate]
        loc_return = model_localization(pill_image, pill_label)

        loss_loc = sum(loc_return[k] for k in [
            'loss_classifier', 'loss_box_reg',
            'loss_objectness', 'loss_rpn_box_reg'])

        bbox_features = loc_return['gt_feature']

        # Matching
        (img_proj, sent_proj, sent_info_proj,
         sent_all_proj, sent_info_all_proj,
         graph_extract) = model_matching(data, bbox_features)

        graph_loss = graph_criterion(graph_extract, data.prescription_label)
        graph_pred = torch.nn.functional.softmax(graph_extract, dim=-1)
        graph_pred = graph_pred[:, 0].unsqueeze(1)
        sent_proj = graph_pred * sent_proj

        match_loss = calculate_matching_cross_loss(
            img_proj, sent_proj, sent_info_proj,
            sent_all_proj, sent_info_all_proj,
            data.pills_label_in_prescription, data.pill_image_label)

        total_loss = loss_loc + match_loss + graph_loss
        total_loss.backward()
        optimizer_loc.step()
        optimizer_match.step()
        epoch_losses.append(total_loss.item())

    avg_loss = sum(epoch_losses) / len(epoch_losses)
    print(f'Epoch {epoch}/{args.epochs} | Loss: {avg_loss:.4f}')

    if avg_loss < best_loss:
        best_loss = avg_loss
        torch.save({
            'model_loc': model_localization.state_dict(),
            'model_match': model_matching.state_dict(),
        }, f'{SAVE_DIR}/zero_pima_best.pth')
        print(f'  💾 Saved best (loss={best_loss:.4f})')

    # Save checkpoint every epoch
    torch.save({
        'epoch': epoch,
        'model_loc': model_localization.state_dict(),
        'model_match': model_matching.state_dict(),
        'opt_loc': optimizer_loc.state_dict(),
        'opt_match': optimizer_match.state_dict(),
        'best_loss': best_loss,
    }, CHECKPOINT)

print(f'✅ Done! Best loss: {best_loss:.4f}')
"""
