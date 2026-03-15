# path
INPUT_DIR = "data/input"
OUTPUT_DIR = "data/output"

# Model weights
YOLO_WEIGHTS = 'models/yolo/best.pt'
MODEL_PATH = YOLO_WEIGHTS  # backward compat
ZERO_PIMA_WEIGHTS = 'models/zero_pima/zero_pima_best.pth'

# YOLO — VĐ6: hạ từ 0.90 xuống 0.50 để giảm miss detect
CONF_THRESHOLD = 0.50

# Optional second YOLO for table region OCR ROI.
# If weights do not exist, pipeline automatically falls back to full-image OCR.
TABLE_YOLO_WEIGHTS = 'models/yolo/table_best.pt'
TABLE_CONF_THRESHOLD = 0.35

# camera
CAMERA_INDEX = 0

# crop
CROP_PADDING = 20
