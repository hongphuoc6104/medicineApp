import os
import subprocess
import json

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_dir = os.path.join(root_dir, "data", "output", "phase_a")

test_images = [
    "data/input/prescription_1/IMG_20260209_180410.jpg",
    "data/createPrescription/Pasted image.png",
    "data/synthetic_train/pres_images/train/VAIPE_P_TRAIN_100.jpg"
]

for img_path in test_images:
    print(f"\n{'='*80}")
    print(f"RUNNING TEST ON: {img_path}")
    print(f"{'='*80}")
    
    # Chạy pipeline, tự động nó sẽ ghi ra output/phase_a/
    subprocess.run(["venv/bin/python", "scripts/run_pipeline.py", "--image", img_path], cwd=root_dir, check=True)
    
    # Lấy tên folder output (ví dụ: IMG_20260209_180410)
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    json_path = os.path.join(out_dir, base_name, "step-3.json")
    
    # Đọc json in ra
    print(f"\n[RESULTS] Group by STT for {base_name}:")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            for i, item in enumerate(data):
                print(f"  Line {i+1}: {item['text']}")
                
    except Exception as e:
        print(f"Can't read output: {e}")
