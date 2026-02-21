# Use for loop to read every .jpg/ ,png in data/input/, run the model, and save every thing blindly into data/output/.
import cv2
import os
from pathlib import Path
from core.config import INPUT_DIR, OUTPUT_DIR, CROP_PADDING
from core.detector import PrescriptionDetector
from core.segmentation import crop_by_mask, crop_by_bbox, extract_polygon


def save_outputs(image: "np.ndarray", result, stem: str) -> None:
    """
    Save 4 output files for one detected prescription.
    Args:
        image: Original BGR image.
        result: A single YOLO Results object.
        stem: Filename without extension (e.g. 'photo_001').
    """
    crop_bbox_img = crop_by_bbox(image, result)
    crop_mask_img = crop_by_mask(image, result)

    image_items = [
        ("original", f"{stem}_original.png", image),
        ("bbox",     f"{stem}_bbox.png",     crop_bbox_img),
        ("mask",     f"{stem}_mask.png",     crop_mask_img),
    ]
    for subfolder, filename, img in image_items:
        folder = os.path.join(OUTPUT_DIR, subfolder)
        os.makedirs(folder, exist_ok=True)
        cv2.imwrite(os.path.join(folder, filename), img)

    txt_folder = os.path.join(OUTPUT_DIR, "polygon")
    os.makedirs(txt_folder, exist_ok=True)
    with open(os.path.join(txt_folder, f"{stem}_polygon.txt"), "w") as f:
        f.write(" ".join(map(str, extract_polygon(result))))


def process_folder(detector: PrescriptionDetector) -> None:
    """Read images from INPUT_DIR, run YOLO, save results."""

    image_paths = list(Path(INPUT_DIR).glob("*.jpg")) + \
                list(Path(INPUT_DIR).glob("*.png"))

    if not image_paths:
        print("empty!")
        return 

    succes = 0
    total = len(image_paths)
    for image_path in image_paths:
        image = cv2.imread(str(image_path))

        results = detector.predict(image)

        if not results or results[0].masks is None:
            print(f"[WARNING] No detection: {image_path.name}")
            continue 
    # Step 4: print summary "X/Y images detected"
        stem = image_path.stem
        save_outputs(image, results[0], stem)
        succes +=1

    print(f"Done: {succes}/{total} images detected.")

def main() -> None:
    """Entry point."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    detector = PrescriptionDetector()
    process_folder(detector)


if __name__ == "__main__":
    main()
