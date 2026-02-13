import sys
from pathlib import Path

# Add project root to path so we can import modules if needed
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ ERROR: Chưa cài đặt ultralytics. Vui lòng chạy: pip install ultralytics")
    sys.exit(1)

def demo_yolov11_custom(model_path="models/weights/best.pt", image_path="data/input/test.jpg"):
    """
    Demo script để chạy YOLOv11n-seg custom model.
    """
    print("="*50)
    print("🚀 YOLOv11 Custom Model Demo")
    print("="*50)

    # 1. Kiểm tra file model
    model_file = Path(model_path)
    if not model_file.exists():
        print(f"⚠️  CẢNH BÁO: Không tìm thấy file model tại '{model_path}'")
        print(f"👉 Vui lòng copy file 'best.pt' của bạn vào thư mục 'models/weights/'")
        print(f"   Hoặc chỉnh sửa đường dẫn trong script này.")
        return

    # 2. Load model
    print(f"🔄 Đang load model từ: {model_path}...")
    try:
        model = YOLO(model_path)
        print("✅ Model loaded thành công!")
        print(f"   - Classes: {model.names}")
    except Exception as e:
        print(f"❌ Lỗi khi load model: {e}")
        return

    # 3. Kiểm tra ảnh test
    img_file = Path(image_path)
    if not img_file.exists():
        print(f"⚠️  Không tìm thấy ảnh test tại '{image_path}'")
        print("👉 Vui lòng thêm ảnh vào thư mục 'data/input/' để test.")
        # Thử download ảnh mẫu nếu không có
        try:
            print("⬇️  Đang tải ảnh mẫu từ internet...")
            import urllib.request
            img_url = "https://ultralytics.com/images/bus.jpg"
            img_file.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(img_url, str(img_file))
            print(f"✅ Đã tải ảnh mẫu về: {image_path}")
        except Exception as e:
            print(f"❌ Không thể tải ảnh mẫu: {e}")
            return

    # 4. Run Inference
    print(f"\nrunning inference trên: {image_path}...")
    results = model.predict(
        source=str(img_file),
        save=True,
        project="data/output",
        name="demo_yolov11",
        exist_ok=True,
        conf=0.25
    )

    # 5. Show results
    print("\n📊 KẾT QUẢ:")
    for result in results:
        boxes = result.boxes
        masks = result.masks
        if boxes is not None:
             print(f"   - Phát hiện: {len(boxes)} đối tượng")
        if masks is not None:
             print(f"   - Segmentation masks: {len(masks)} masks")
        
        # Save path
        save_dir = result.save_dir
        print(f"\n💾 Kết quả đã lưu tại: {save_dir}")

if __name__ == "__main__":
    # Bạn có thể sửa đường dẫn model ở đây
    # Ví dụ: model_path = "/path/to/your/best.pt"
    demo_yolov11_custom()
