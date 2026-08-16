import os
import subprocess

ADB = "/home/hongphuoc/Android/Sdk/platform-tools/adb"
DEVICE_ID = "192.168.1.65:36973"
PACKAGE = "com.medicineapp.medicine_app"
RECTIFIED_DIR = "data/rectified_200"

def main():
    print("[*] Preparing device for OCR_RECTIFIED batch...")
    
    # 1. Clean device tmp & app input/output folders
    print("[*] Cleaning device app directories...")
    cmd_clean = (
        f"rm -rf /data/local/tmp/staging_rectified && "
        f"mkdir -p /data/local/tmp/staging_rectified && "
        f"run-as {PACKAGE} rm -rf files/input files/output && "
        f"run-as {PACKAGE} mkdir -p files/input files/output"
    )
    subprocess.run([ADB, "-s", DEVICE_ID, "shell", cmd_clean], check=True)

    # 2. Push rectified images to /data/local/tmp/staging_rectified
    print("[*] Pushing 200 rectified images to Android device...")
    subprocess.run([ADB, "-s", DEVICE_ID, "push", f"{RECTIFIED_DIR}/.", "/data/local/tmp/staging_rectified/"], check=True)

    # 3. Copy to app sandbox
    print("[*] Copying into app sandbox...")
    cmd_copy = (
        f"run-as {PACKAGE} cp -r /data/local/tmp/staging_rectified/* /data/data/{PACKAGE}/files/input/ && "
        f"rm -rf /data/local/tmp/staging_rectified"
    )
    subprocess.run([ADB, "-s", DEVICE_ID, "shell", cmd_copy], check=True)

    # 4. Restart batch OCR app
    print("[*] Restarting Batch OCR App on device...")
    cmd_launch = f"am force-stop {PACKAGE} && monkey -p {PACKAGE} -c android.intent.category.LAUNCHER 1"
    subprocess.run([ADB, "-s", DEVICE_ID, "shell", cmd_launch], check=True)

    print("[+] Successfully deployed and launched OCR_RECTIFIED batch on device!")

if __name__ == "__main__":
    main()
