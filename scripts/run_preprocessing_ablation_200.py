import glob
import json
import os
import cv2
from rxie.image_transforms import process_image_pipeline


def run_ablation_on_200():
    input_images = sorted(glob.glob("data/staging_200/**/*.*", recursive=True))
    input_images = [f for f in input_images if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))][:200]

    # Index all OCR JSON files by base filename (e.g. IMG_20260122_005140 -> path)
    json_index = {}
    for p in glob.glob("data/output/**/*.json", recursive=True):
        bname = os.path.splitext(os.path.basename(p))[0]
        json_index[bname] = p

    print(f"[*] Indexed {len(json_index)} RAW OCR JSON files.")
    print(f"[*] Starting Conditional Preprocessing Pipeline on {len(input_images)} demo images...")
    os.makedirs("data/rectified_200", exist_ok=True)

    summary = {
        "total_images": len(input_images),
        "raw_ocr_matched": 0,
        "orientation_rotated": 0,
        "document_rectified": 0,
        "deskew_applied": 0,
        "cropped": 0,
        "rotations_by_angle": {90: 0, 180: 0, 270: 0},
        "records": [],
    }

    for idx, img_path in enumerate(input_images):
        rel = os.path.relpath(img_path, "data/staging_200")
        base_name = os.path.splitext(os.path.basename(img_path))[0]

        raw_ocr_data = None
        if base_name in json_index:
            summary["raw_ocr_matched"] += 1
            with open(json_index[base_name], "r", encoding="utf-8") as f:
                raw_ocr_data = json.load(f)

        img = cv2.imread(img_path)
        if img is None:
            continue

        h, w = img.shape[:2]
        processed_img, meta = process_image_pipeline(img, ocr_raw_data=raw_ocr_data)

        # Save rectified image preserving subfolder relative path
        out_img_path = os.path.join("data/rectified_200", rel)
        os.makedirs(os.path.dirname(out_img_path), exist_ok=True)
        cv2.imwrite(out_img_path, processed_img)

        if meta.orientation_rotation != 0:
            summary["orientation_rotated"] += 1
            summary["rotations_by_angle"][meta.orientation_rotation] = (
                summary["rotations_by_angle"].get(meta.orientation_rotation, 0) + 1
            )
        if meta.perspective_applied:
            summary["document_rectified"] += 1
        if meta.deskew_applied:
            summary["deskew_applied"] += 1
        if meta.cropped:
            summary["cropped"] += 1

        rec = {
            "image_id": base_name,
            "relative_path": rel,
            "original_dims": [w, h],
            "rectified_dims": [processed_img.shape[1], processed_img.shape[0]],
            "preprocessing": {
                "orientation_rotation": meta.orientation_rotation,
                "document_detected": meta.document_detected,
                "document_confidence": round(meta.document_confidence, 3),
                "perspective_corrected": meta.perspective_applied,
                "deskew_angle": round(meta.skew_angle, 2),
                "deskew_applied": meta.deskew_applied,
                "cropped": meta.cropped,
            },
        }
        summary["records"].append(rec)

    # Save summary metadata JSON
    with open("data/rectified_200/preprocessing_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n=======================================================")
    print("   RxIE Conditional Preprocessing Execution Results (200 images)")
    print("=======================================================")
    print(f"   • Tổng số ảnh đã chạy qua Pipeline : {summary['total_images']}")
    print(f"   • Khớp với kết quả OCR RAW        : {summary['raw_ocr_matched']}/{summary['total_images']}")
    print(f"   • Xoay hướng (P1 Orientation)     : {summary['orientation_rotated']} ảnh ({summary['orientation_rotated']/len(input_images)*100:.1f}%)")
    print(f"     - 90° : {summary['rotations_by_angle'].get(90, 0)} ảnh")
    print(f"     - 180°: {summary['rotations_by_angle'].get(180, 0)} ảnh")
    print(f"     - 270°: {summary['rotations_by_angle'].get(270, 0)} ảnh")
    print(f"   • Nắn phối cảnh (P2 Perspective)   : {summary['document_rectified']} ảnh ({summary['document_rectified']/len(input_images)*100:.1f}%)")
    print(f"   • Chỉnh góc nghiêng (P3 Deskew)    : {summary['deskew_applied']} ảnh ({summary['deskew_applied']/len(input_images)*100:.1f}%)")
    print(f"   • Cắt biên tài liệu (P5 Crop)      : {summary['cropped']} ảnh ({summary['cropped']/len(input_images)*100:.1f}%)")
    print(f"   • Ảnh đã nắn thẳng lưu tại         : data/rectified_200/")
    print(f"   • Metadata tổng hợp lưu tại        : data/rectified_200/preprocessing_summary.json")
    print("=======================================================\n")


if __name__ == "__main__":
    run_ablation_on_200()
