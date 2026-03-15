import os
import shutil
import subprocess

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_dir = os.path.join(root_dir, "data", "output", "phase_a")
test_out_dir = os.path.join(out_dir, "test_full")

tasks = [
    {
        "cmd": ["venv/bin/python", "scripts/run_pipeline.py", "--dir", "data/input/prescription_1"],
        "target": "dataset_real"
    },
    {
        "cmd": ["venv/bin/python", "scripts/run_pipeline.py", "--image", "data/createPrescription/Pasted image.png"],
        "target": "dataset_pasted"
    },
    {
        "cmd": ["venv/bin/python", "scripts/run_pipeline.py", "--dir", "data/synthetic_train/pres_images/train", "--limit", "10"],
        "target": "dataset_synthetic"
    }
]

for task in tasks:
    print(f"\n{'='*50}\nRunning Phase A pipeline for: {task['target']}\n{'='*50}")
    try:
        subprocess.run(task['cmd'], cwd=root_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running pipeline for {task['target']}")
        continue
    
    # Organize outputs
    target_dir = os.path.join(test_out_dir, task["target"])
    os.makedirs(target_dir, exist_ok=True)
    
    # Move every newly created folder in out_dir (except our test output folders)
    if os.path.exists(out_dir):
        for item in os.listdir(out_dir):
            if item in ["test_full", "test_crop"]:
                continue
            item_path = os.path.join(out_dir, item)
            if os.path.isdir(item_path):
                dst = os.path.join(target_dir, item)
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.move(item_path, target_dir)
            
print(f"\n>>> Done! Check all full pipeline outputs in: {test_out_dir}")
