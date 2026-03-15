
import os
import cv2
import sys
import torch
import numpy as np
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from core.phase_a.s1_detect.detector import PrescriptionDetector
from core.phase_a.s1_detect.segmentation import crop_by_mask

def process_and_save(detector, img_path, out_dir):
    try:
        print(f"Processing: {img_path}")
        image = cv2.imread(img_path)
        if image is None:
            print(f"  [Error] Cannot read image: {img_path}")
            return
            
        # 1. Detect
        results = detector.predict(image)
        if not results or results[0].boxes is None or len(results[0].boxes) == 0:
            print(f"  [Warning] No prescription detected in: {img_path}")
            return
            
        # 2. Crop (uses the new Convex Hull logic I just updated)
        cropped, offset = crop_by_mask(image, results[0])
        
        if cropped is not None:
            name = os.path.basename(img_path)
            # Use original extension or .jpg
            stem = os.path.splitext(name)[0]
            save_path = os.path.join(out_dir, f"{stem}_crop.jpg")
            cv2.imwrite(save_path, cropped)
            print(f"  [OK] Saved to: {save_path}")
        else:
            print(f"  [Warning] Crop failed for: {img_path}")
            
    except Exception as e:
        print(f"  [Error] {str(e)}")

def main():
    # Load Detector once
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading YOLOv8 Detector on {device}...")
    detector = PrescriptionDetector()
    
    # Setup Output dirs
    base_out = os.path.join(root_dir, "data/output/phase_a/test_crop")
    dirs = {
        "real": os.path.join(base_out, "dataset_real"),
        "pasted": os.path.join(base_out, "dataset_pasted"),
        "synthetic": os.path.join(base_out, "dataset_synthetic")
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
        
    # --- 1. Real Images (data/input) ---
    real_input = os.path.join(root_dir, "data/input")
    for subdir in ["prescription_1"]: # Process a known folder
        dpath = os.path.join(real_input, subdir)
        if os.path.exists(dpath):
            for f in os.listdir(dpath):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    process_and_save(detector, os.path.join(dpath, f), dirs["real"])

    # --- 2. Pasted image ---
    pasted_path = os.path.join(root_dir, "data/createPrescription/Pasted image.png")
    if os.path.exists(pasted_path):
        process_and_save(detector, pasted_path, dirs["pasted"])
        
    # --- 3. Synthetic (data/synthetic_train/pres_images/train) ---
    syn_input = os.path.join(root_dir, "data/synthetic_train/pres_images/train")
    if os.path.exists(syn_input):
        syn_files = sorted([f for f in os.listdir(syn_input) if f.endswith('.png')])
        for f in syn_files[:10]: # Take 10 samples
            process_and_save(detector, os.path.join(syn_input, f), dirs["synthetic"])

    print("\nDone! Check results in data/output/phase_a/test_crop/")

if __name__ == "__main__":
    main()
