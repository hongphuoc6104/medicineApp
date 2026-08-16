import glob
import json
import os
import cv2
from rxie.image_transforms import (
    detect_dominant_orientation_from_ocr,
    detect_skew_angle_from_ocr,
    deskew_affine,
    detect_document_quad,
    perspective_rectify,
    rotate_orthogonal,
)


def generate_all_ablation_branches():
    input_images = sorted(glob.glob("data/staging_200/**/*.*", recursive=True))
    input_images = [f for f in input_images if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))][:200]

    # Index RAW OCR JSON files
    raw_json_index = {}
    for p in glob.glob("data/output/**/*.json", recursive=True):
        bname = os.path.splitext(os.path.basename(p))[0]
        raw_json_index[bname] = p

    print(f"[*] Preparing P1, P2, P3 branches for {len(input_images)} demo images...")
    
    os.makedirs("data/p1_rotation_200", exist_ok=True)
    os.makedirs("data/p2_perspective_200", exist_ok=True)
    os.makedirs("data/p3_deskew_200", exist_ok=True)

    metadata_tracking = {}

    for img_path in input_images:
        rel = os.path.relpath(img_path, "data/staging_200")
        base_name = os.path.splitext(os.path.basename(img_path))[0]

        raw_ocr_data = None
        if base_name in raw_json_index:
            with open(raw_json_index[base_name], "r", encoding="utf-8") as f:
                raw_ocr_data = json.load(f)

        img = cv2.imread(img_path)
        if img is None:
            continue

        h, w = img.shape[:2]

        # Calculate geometric signals
        orientation = detect_dominant_orientation_from_ocr(raw_ocr_data) if raw_ocr_data else 0
        skew_angle = detect_skew_angle_from_ocr(raw_ocr_data, orientation) if raw_ocr_data else 0.0
        
        # 1. P1: Rotation Only
        img_p1 = rotate_orthogonal(img.copy(), orientation) if orientation != 0 else img.copy()
        p1_out = os.path.join("data/p1_rotation_200", rel)
        os.makedirs(os.path.dirname(p1_out), exist_ok=True)
        cv2.imwrite(p1_out, img_p1)

        # 2. P2: Rotation + Perspective
        img_p2 = img_p1.copy()
        quad_pts, conf = detect_document_quad(img_p2)
        persp_applied = False
        if quad_pts is not None and conf >= 0.65:
            img_p2 = perspective_rectify(img_p2, quad_pts)
            persp_applied = True
        p2_out = os.path.join("data/p2_perspective_200", rel)
        os.makedirs(os.path.dirname(p2_out), exist_ok=True)
        cv2.imwrite(p2_out, img_p2)

        # 3. P3: Rotation + Deskew
        img_p3 = img_p1.copy()
        deskew_applied = False
        if 2.0 <= abs(skew_angle) <= 15.0:
            img_p3 = deskew_affine(img_p3, -skew_angle)
            deskew_applied = True
        p3_out = os.path.join("data/p3_deskew_200", rel)
        os.makedirs(os.path.dirname(p3_out), exist_ok=True)
        cv2.imwrite(p3_out, img_p3)

        metadata_tracking[base_name] = {
            "orientation_detected": orientation,
            "rotation_applied": orientation,
            "document_detected": quad_pts is not None,
            "document_confidence": round(conf, 3),
            "perspective_applied": persp_applied,
            "deskew_detected_angle": round(skew_angle, 2),
            "deskew_applied": deskew_applied,
            "crop_applied": False,
        }

    # Inject metadata into P4 JSON files in data/output_rectified
    rect_json_files = glob.glob("data/output_rectified/**/*.json", recursive=True)
    injected_count = 0
    for p in rect_json_files:
        bname = os.path.splitext(os.path.basename(p))[0]
        if bname in metadata_tracking:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["preprocessing"] = metadata_tracking[bname]
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            injected_count += 1

    # Save comprehensive metadata index
    with open("data/ablation_metadata_tracking.json", "w", encoding="utf-8") as f:
        json.dump(metadata_tracking, f, indent=2, ensure_ascii=False)

    print(f"[+] Successfully generated:")
    print(f"    - P1 (Rotation)    : {len(input_images)} images in data/p1_rotation_200/")
    print(f"    - P2 (Perspective) : {len(input_images)} images in data/p2_perspective_200/")
    print(f"    - P3 (Deskew)      : {len(input_images)} images in data/p3_deskew_200/")
    print(f"    - P4 (Full)        : Injected preprocessing metadata into {injected_count} JSONs in data/output_rectified/")
    print(f"    - Full Index       : data/ablation_metadata_tracking.json")


if __name__ == "__main__":
    generate_all_ablation_branches()
