"""
setup_vaipe_data.py — Download VAIPE pill images từ Kaggle
và setup cấu trúc data cho Zero-PIMA.

Cần: ~/.kaggle/kaggle.json (API key từ kaggle.com/settings)

Chạy:
  python scripts/setup_vaipe_data.py
"""

import os
import sys
import json
import shutil
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PILLS_DIR = os.path.join(DATA, "pills")


def download_dataset():
    """Download VAIPE pills dataset từ Kaggle."""
    import kagglehub
    print("📦 Downloading pills-detection-dataset từ Kaggle...")
    path = kagglehub.dataset_download(
        "alexanderyotann/pills-detection-dataset"
    )
    print(f"✅ Downloaded to: {path}")
    return path


def setup_structure(raw_path):
    """
    Organize raw data → data/pills/{train,test}/{imgs,labels}/
    
    VAIPE dataset structure:
      raw_path/
        train/
          images/   ← pill photos (.jpg)
          labels/   ← bounding box annotations (.json)
        test/
          images/
          labels/
    """
    for split in ["train", "test"]:
        for subdir in ["imgs", "labels"]:
            os.makedirs(
                os.path.join(PILLS_DIR, split, subdir),
                exist_ok=True
            )

    # Find actual data directories
    # Dataset might have nested structure
    for split in ["train", "test"]:
        # Try common structures
        img_candidates = [
            os.path.join(raw_path, split, "images"),
            os.path.join(raw_path, split, "imgs"),
            os.path.join(raw_path, "images", split),
            os.path.join(raw_path, split),
        ]
        label_candidates = [
            os.path.join(raw_path, split, "labels"),
            os.path.join(raw_path, split, "annotations"),
            os.path.join(raw_path, "labels", split),
        ]

        # Find images
        img_src = None
        for c in img_candidates:
            if os.path.isdir(c):
                jpgs = glob.glob(os.path.join(c, "*.jpg"))
                pngs = glob.glob(os.path.join(c, "*.png"))
                if jpgs or pngs:
                    img_src = c
                    break

        # Find labels
        lbl_src = None
        for c in label_candidates:
            if os.path.isdir(c):
                jsons = glob.glob(os.path.join(c, "*.json"))
                if jsons:
                    lbl_src = c
                    break

        if img_src:
            imgs = sorted(
                glob.glob(os.path.join(img_src, "*.jpg"))
                + glob.glob(os.path.join(img_src, "*.png"))
            )
            dst = os.path.join(PILLS_DIR, split, "imgs")
            print(f"  {split}/imgs: {len(imgs)} images from {img_src}")
            for f in imgs:
                shutil.copy2(f, dst)
        else:
            print(f"  ⚠️ {split}/imgs: no images found!")

        if lbl_src:
            labels = sorted(
                glob.glob(os.path.join(lbl_src, "*.json"))
            )
            dst = os.path.join(PILLS_DIR, split, "labels")
            print(f"  {split}/labels: {len(labels)} labels from {lbl_src}")
            for f in labels:
                shutil.copy2(f, dst)
        else:
            print(f"  ⚠️ {split}/labels: no labels found!")


def verify():
    """Kiểm tra data sau khi setup."""
    print("\n=== Verification ===")
    for split in ["train", "test"]:
        imgs = len(glob.glob(
            os.path.join(PILLS_DIR, split, "imgs", "*")
        ))
        labels = len(glob.glob(
            os.path.join(PILLS_DIR, split, "labels", "*.json")
        ))
        pres = len(glob.glob(
            os.path.join(DATA, "pres", split, "*.json")
        ))
        print(
            f"  {split}: {imgs} pill images, "
            f"{labels} labels, {pres} prescriptions"
        )

    if imgs == 0:
        print("\n⚠️ Không tìm thấy ảnh! Kiểm tra cấu trúc raw data:")
        raw_path = input("Nhập path tới raw data: ").strip()
        if raw_path and os.path.isdir(raw_path):
            print("Cấu trúc raw data:")
            for root, dirs, files in os.walk(raw_path):
                level = root.replace(raw_path, '').count(os.sep)
                indent = '  ' * level
                print(f"{indent}{os.path.basename(root)}/")
                if level < 3:
                    for f in sorted(files)[:3]:
                        print(f"{indent}  {f}")
                    if len(files) > 3:
                        print(f"{indent}  ... ({len(files)} files)")


def main():
    print("=" * 50)
    print("  VAIPE Pill Dataset Setup")
    print("=" * 50)

    # Step 1: Download
    raw_path = download_dataset()

    # Step 2: Explore raw structure
    print(f"\n📂 Raw data structure at: {raw_path}")
    for root, dirs, files in os.walk(raw_path):
        level = root.replace(raw_path, '').count(os.sep)
        indent = '  ' * level
        print(f"{indent}{os.path.basename(root)}/")
        if level < 3:
            for f in sorted(files)[:3]:
                print(f"{indent}  {f}")
            if len(files) > 3:
                print(f"{indent}  ... ({len(files)} files)")

    # Step 3: Setup structure
    print("\n📋 Setting up data/pills/ structure...")
    setup_structure(raw_path)

    # Step 4: Verify
    verify()
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
