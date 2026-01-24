"""
Prediction script cho YOLO Segmentation

Usage:
    python inference/predict.py --image path/to/image.jpg
    python inference/predict.py --folder path/to/images/
"""

import argparse
import sys
from pathlib import Path

# Thêm root directory vào path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from models.yolo_segmentation import YOLOSegmentation


def run_inference(
    source: str,
    model_path: str = None,
    output_dir: str = "data/output",
    conf: float = 0.25,
    save: bool = True,
    show: bool = False
):
    """
    Chạy inference trên ảnh hoặc thư mục ảnh.
    
    Args:
        source: Đường dẫn tới ảnh hoặc thư mục.
        model_path: Đường dẫn tới custom model (.pt). None = pretrained.
        output_dir: Thư mục lưu kết quả.
        conf: Ngưỡng confidence.
        save: Lưu kết quả visualization.
        show: Hiển thị kết quả.
    
    Returns:
        results: Kết quả prediction.
    """
    # Khởi tạo model
    if model_path:
        model = YOLOSegmentation(model_path=model_path)
    else:
        model = YOLOSegmentation(model_size="nano")
    
    print(f"\n📷 Source: {source}")
    print(f"📁 Output: {output_dir}")
    print(f"🎯 Confidence threshold: {conf}")
    print("-" * 50)
    
    # Chạy prediction
    results = model.predict(
        source=source,
        conf=conf,
        save=save,
        save_dir=output_dir,
        show=show
    )
    
    # In kết quả
    for i, result in enumerate(results):
        print(f"\n🖼️  Image {i + 1}:")
        if result.boxes is not None:
            num_objects = len(result.boxes)
            print(f"   Detected: {num_objects} object(s)")
            
            # In class và confidence
            for j, box in enumerate(result.boxes):
                cls_id = int(box.cls[0])
                cls_name = model.get_class_names()[cls_id]
                conf_score = float(box.conf[0])
                print(f"   - {cls_name}: {conf_score:.2%}")
        else:
            print("   No objects detected")
        
        if result.masks is not None:
            print(f"   Masks: {len(result.masks)} segment(s)")
    
    print("\n" + "=" * 50)
    print("✅ Inference completed!")
    if save:
        print(f"📁 Results saved to: {output_dir}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="YOLO Segmentation Inference")
    parser.add_argument(
        "--image", "-i",
        type=str,
        help="Đường dẫn tới ảnh đầu vào"
    )
    parser.add_argument(
        "--folder", "-f",
        type=str,
        help="Đường dẫn tới thư mục chứa ảnh"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Đường dẫn tới custom model (.pt)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="data/output",
        help="Thư mục lưu kết quả (default: data/output)"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Ngưỡng confidence (default: 0.25)"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Hiển thị kết quả trên màn hình"
    )
    
    args = parser.parse_args()
    
    # Xác định source
    if args.image:
        source = args.image
    elif args.folder:
        source = args.folder
    else:
        print("❌ Cần chỉ định --image hoặc --folder")
        parser.print_help()
        sys.exit(1)
    
    # Chạy inference
    run_inference(
        source=source,
        model_path=args.model,
        output_dir=args.output,
        conf=args.conf,
        save=True,
        show=args.show
    )


if __name__ == "__main__":
    main()
