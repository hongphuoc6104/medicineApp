import glob
import os
import shutil
import subprocess

ADB = "/home/hongphuoc/Android/Sdk/platform-tools/adb"
DEVICE_ID = "192.168.1.65:36973"
PACKAGE = "com.medicineapp.medicine_app"
STAGING_DIR = "data/staging_200"

def main():
    all_files = sorted(glob.glob("data/input/**/*.*", recursive=True))
    images = [f for f in all_files if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    selected = images[:200]
    print(f"[*] Total found: {len(images)}, Selected 200 demo images.")

    if os.path.exists(STAGING_DIR):
        shutil.rmtree(STAGING_DIR)
    os.makedirs(STAGING_DIR, exist_ok=True)

    print("[*] Staging 200 images...")
    for img_path in selected:
        rel = os.path.relpath(img_path, "data/input")
        dst = os.path.join(STAGING_DIR, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(img_path, dst)

    print(f"[*] Staged 200 images into {STAGING_DIR}.")

    # Clean and push to /data/local/tmp
    print("[*] Pushing to Android device /data/local/tmp/staging_200...")
    subprocess.run([ADB, "-s", DEVICE_ID, "shell", "rm -rf /data/local/tmp/staging_200 && mkdir -p /data/local/tmp/staging_200"], check=True)
    subprocess.run([ADB, "-s", DEVICE_ID, "push", f"{STAGING_DIR}/.", "/data/local/tmp/staging_200/"], check=True)

    print("[*] Copying into app sandbox /data/data/.../files/input/...")
    cmd = (
        f"run-as {PACKAGE} mkdir -p files/input && "
        f"run-as {PACKAGE} mkdir -p files/output && "
        f"run-as {PACKAGE} cp -r /data/local/tmp/staging_200/* /data/data/{PACKAGE}/files/input/ && "
        f"rm -rf /data/local/tmp/staging_200"
    )
    subprocess.run([ADB, "-s", DEVICE_ID, "shell", cmd], check=True)
    print("[+] Successfully pushed 200 images into device app sandbox!")

if __name__ == "__main__":
    main()
