import os
import subprocess
import sys
import time

ADB = "/home/hongphuoc/Android/Sdk/platform-tools/adb"
DEVICE_ID = "192.168.1.10:41729"
PACKAGE = "com.medicineapp.medicine_app"


def run_branch(branch_name: str, src_dir: str, dst_output_dir: str):
    print(f"\n=======================================================")
    print(f"   STARTING BATCH OCR FOR BRANCH: {branch_name}")
    print(f"   Source Folder: {src_dir}")
    print(f"   Destination  : {dst_output_dir}")
    print(f"=======================================================\n")

    # 1. Clean app sandbox and staging
    print(f"[*] [1/5] Cleaning device app directories...")
    cmd_clean = (
        f"rm -rf /data/local/tmp/staging_branch && "
        f"mkdir -p /data/local/tmp/staging_branch && "
        f"run-as {PACKAGE} rm -rf files/input files/output && "
        f"run-as {PACKAGE} mkdir -p files/input files/output"
    )
    subprocess.run([ADB, "-s", DEVICE_ID, "shell", cmd_clean], check=True)

    # 2. Push images
    print(f"[*] [2/5] Pushing {src_dir} to Android device...")
    subprocess.run([ADB, "-s", DEVICE_ID, "push", f"{src_dir}/.", "/data/local/tmp/staging_branch/"], check=True)

    # 3. Copy to app sandbox
    print(f"[*] [3/5] Moving into app sandbox...")
    cmd_copy = (
        f"run-as {PACKAGE} cp -r /data/local/tmp/staging_branch/* /data/data/{PACKAGE}/files/input/ && "
        f"rm -rf /data/local/tmp/staging_branch"
    )
    subprocess.run([ADB, "-s", DEVICE_ID, "shell", cmd_copy], check=True)

    # 4. Restart Batch App
    print(f"[*] [4/5] Launching Batch OCR App on device...")
    cmd_launch = f"am force-stop {PACKAGE} && monkey -p {PACKAGE} -c android.intent.category.LAUNCHER 1"
    subprocess.run([ADB, "-s", DEVICE_ID, "shell", cmd_launch], check=True)

    # 5. Monitor progress
    print(f"[*] [5/5] Monitoring Batch OCR progress on device...")
    start_time = time.time()
    last_count = 0
    while True:
        time.sleep(10)
        out = subprocess.check_output([
            ADB, "-s", DEVICE_ID, "shell",
            f"run-as {PACKAGE} find files/output -name '*.json' 2>/dev/null | wc -l"
        ]).decode().strip()
        try:
            count = int(out)
        except ValueError:
            count = 0

        if count != last_count:
            last_count = count
            elapsed = int(time.time() - start_time)
            print(f"    [{branch_name}] Progress: {count}/200 images ({elapsed}s elapsed)")

        if count >= 200:
            print(f"[+] [{branch_name}] Batch OCR completed 200/200!")
            break

    # 6. Pull results
    print(f"[*] Pulling results to {dst_output_dir}...")
    os.makedirs(dst_output_dir, exist_ok=True)
    pull_cmd = f"{ADB} -s {DEVICE_ID} exec-out \"run-as {PACKAGE} tar -czf - -C files/output .\" | tar -xzf - -C {dst_output_dir}/"
    subprocess.run(pull_cmd, shell=True, check=True)

    json_count = len([f for f in os.listdir(dst_output_dir) if f.endswith(".json") or os.path.isdir(os.path.join(dst_output_dir, f))])
    print(f"[+] Successfully pulled {branch_name} results into {dst_output_dir}!\n")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python run_branch_ocr.py <BRANCH_NAME> <SRC_DIR> <DST_OUTPUT_DIR>")
        sys.exit(1)
    run_branch(sys.argv[1], sys.argv[2], sys.argv[3])
