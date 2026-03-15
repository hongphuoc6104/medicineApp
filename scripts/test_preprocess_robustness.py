import cv2
import numpy as np
import os
import sys
import logging
import time
from typing import Tuple

# Thêm project root vào path để import được core
sys.path.append(os.getcwd())

from core.phase_a.s2_preprocess.orientation import preprocess_image

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestPreprocessComplex")

def rotate_image(image, angle):
    """Xoay ảnh một góc bất kỳ và giữ nền trắng."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    # Tính toán kích thước mới để không bị mất góc (optional, ở đây ta giữ nguyên size)
    return cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

def create_complex_fake_data(image_path: str, output_dir: str) -> list:
    """Tạo bộ dữ liệu phức tạp: Xuôi + Lộn ngược kết hợp với nhiều góc nghiêng."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Không tìm thấy ảnh tại {image_path}")

    variants = []
    # Các góc nghiêng yêu cầu: 1, 2, 4, 7, 9, 15, 24, 30, 45
    skew_angles = [1, 2, 4, 7, 9, 15, 24, 30, 45]

    print(f"--- Đang tạo Group 1: Xuôi (0°) + Nghiêng ---")
    for ang in skew_angles:
        # Nghiêng dương
        img_skew = rotate_image(img, ang)
        fname = f"norm_skew_p{ang}.jpg"
        path = os.path.join(output_dir, fname)
        cv2.imwrite(path, img_skew)
        variants.append((path, f"Xuôi + {ang}°"))
        
        # Nghiêng âm
        img_skew_m = rotate_image(img, -ang)
        fname_m = f"norm_skew_m{ang}.jpg"
        path_m = os.path.join(output_dir, fname_m)
        cv2.imwrite(path_m, img_skew_m)
        variants.append((path_m, f"Xuôi - {ang}°"))

    print(f"--- Đang tạo Group 2: Lộn ngược (180°) + Nghiêng ---")
    img_180_base = cv2.rotate(img, cv2.ROTATE_180)
    for ang in skew_angles:
        # Nghiêng dương (so với ảnh đã lộn ngược)
        img_skew = rotate_image(img_180_base, ang)
        fname = f"rev_skew_p{ang}.jpg"
        path = os.path.join(output_dir, fname)
        cv2.imwrite(path, img_skew)
        variants.append((path, f"Ngược + {ang}°"))
        
        # Nghiêng âm
        img_skew_m = rotate_image(img_180_base, -ang)
        fname_m = f"rev_skew_m{ang}.jpg"
        path_m = os.path.join(output_dir, fname_m)
        cv2.imwrite(path_m, img_skew_m)
        variants.append((path_m, f"Ngược - {ang}°"))

    return variants

def run_test():
    input_img = "data/input/prescription_3/IMG_20260209_180505.jpg"
    base_out = "data/output/test_preprocess"
    test_cases_dir = os.path.join(base_out, "test_cases")
    results_dir = os.path.join(base_out, "results")
    
    # Dọn dẹp folder cũ
    if os.path.exists(test_cases_dir):
        import shutil
        shutil.rmtree(test_cases_dir)
    if os.path.exists(results_dir):
        import shutil
        shutil.rmtree(results_dir)
    
    os.makedirs(test_cases_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    print("\n" + "="*70)
    print("  TẠO DỮ LIỆU PHỨC TẠP: XUÔI/NGƯỢC + ĐA GÓC NGHIÊNG (1° -> 45°)")
    print("="*70)
    
    variants = create_complex_fake_data(input_img, test_cases_dir)
    print(f"✅ Đã tạo {len(variants)} ảnh test tại: {test_cases_dir}")

    print("\n" + "-"*100)
    print(f"{'Mô tả':<20} | {'File Test':<20} | {'Góc Deskew':<12} | {'Thời gian':<10} | {'AI Orientation'}")
    print("-"*100)

    success_count = 0
    total_time = 0.0
    for path, desc in variants:
        stem = os.path.basename(path).replace(".jpg", "")
        img = cv2.imread(path)
        
        # Chạy tiền xử lý
        start_time = time.time()
        processed, info = preprocess_image(
            img, 
            stem=stem, 
            save_dir=results_dir, 
            skip_ai_fix=False
        )
        end_time = time.time()
        
        duration = end_time - start_time
        total_time += duration
        
        angle = info.get("deskew_angle", 0)
        ai_status = info.get("ai_status", "N/A")
        
        # Đánh giá sơ bộ: nếu xuôi thì AI nên là "Giữ nguyên 0", nếu ngược thì "Xoay 180"
        is_success = False
        if "Xuôi" in desc and "Giữ nguyên 0" in ai_status: is_success = True
        if "Ngược" in desc and "Xoay 180" in ai_status: is_success = True
        
        status_icon = "✅" if is_success else "❌"
        if is_success: success_count += 1
        
        print(f"{desc:<20} | {os.path.basename(path):<20} | {angle:<12.1f} | {duration:<10.3f} | {ai_status} {status_icon}")

    print("-"*100)
    print(f"📊 KẾT QUẢ ĐÁNH GIÁ ORIENTATION: {success_count}/{len(variants)} thành công")
    if len(variants) > 0:
        print(f"⏱️ THỜI GIAN TRUNG BÌNH: {total_time/len(variants):.3f}s / ảnh (Tổng cộng: {total_time:.2f}s)")
    print(f"📂 Ảnh lỗi: {test_cases_dir}")
    print(f"📂 Kết quả: {results_dir}")
    print("="*70)

if __name__ == "__main__":
    run_test()
