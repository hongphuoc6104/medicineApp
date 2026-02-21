import cv2
import os
import numpy as np
from datetime import datetime
from core.config import CAMERA_INDEX, OUTPUT_DIR, DEBUG_DIR
from core.detector import PrescriptionDetector
from core.segmentation import crop_by_mask, crop_by_bbox, extract_polygon
from core.visualizer import draw_bbox, draw_mask_overlay, draw_polygon_points


def open_camera(start_index: int = CAMERA_INDEX) -> cv2.VideoCapture:
    """
    Try to open webcam. Auto-fallback to next index if failed.
    Args:
        start_index: Starting camera index to try.
    Returns:
        An opened VideoCapture object.
    Raises:
        RuntimeError: If no camera found after trying 3 indices.
    """

    for index in range(start_index, start_index + 3):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            print(f"Camera opened at index {index}")
            return cap
    raise RuntimeError("No camera found. Check your connection.")



def save_result(frame: np.ndarray, result,save_debug: str) -> None:
    """
    Save cropped mask image and polygon points to files.
    Args:
        frame: Original BGR frame.
        result: A single YOLO Results object.
        save_dir: Directory to save output files.
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Prepare crops
    crop_bbox_img = crop_by_bbox(frame, result)
    crop_mask_img = crop_by_mask(frame, result)

    # Save images into subfolders: (subfolder_name, filename, image)
    image_items = [
        ("original", f"original_{timestamp}.png", frame),
        ("bbox",     f"bbox_{timestamp}.png",     crop_bbox_img),
        ("mask",     f"mask_{timestamp}.png",     crop_mask_img),
    ]
    for subfolder, filename, image in image_items:
        folder = os.path.join(save_debug, subfolder)
        os.makedirs(folder, exist_ok=True)
        cv2.imwrite(os.path.join(folder, filename), image)

    # Save polygon .txt
    txt_folder = os.path.join(save_debug, "polygon")
    txt_path = os.path.join(txt_folder, f"polygon_{timestamp}.txt")
    os.makedirs(txt_folder, exist_ok=True)
    with open(txt_path, "w") as f:
        f.write(" ".join(map(str, extract_polygon(result))))

    print(f"Saved 4 folders → {save_debug} [{timestamp}]")


def main() -> None:
    """Main loop: open camera, detect, display, save on keypress."""
    os.makedirs(DEBUG_DIR, exist_ok=True)
    detector = PrescriptionDetector()
    cap = open_camera()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = detector.predict(frame)
        display = frame.copy()

        if results and results[0].masks is not None:
            result = results[0]
            display = draw_bbox(display, result)
            display = draw_mask_overlay(display, result)
            display = draw_polygon_points(display, result)

        cv2.namedWindow("Prescription Detector", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Prescription Detector", 960, 540)

        cv2.imshow("Prescription Detector", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s') and results and results[0].masks is not None:
            save_result(frame, results[0], DEBUG_DIR)
            print("saved!")
            pass
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()