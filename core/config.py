# path
INPUT_DIR = "data/input"
OUTPUT_DIR = "data/output"

# Model weights
YOLO_WEIGHTS = 'models/yolo/best.pt'
MODEL_PATH = YOLO_WEIGHTS  # backward compat
ZERO_PIMA_WEIGHTS = 'models/zero_pima/zero_pima_best.pth'

# YOLO — VĐ6: hạ từ 0.90 xuống 0.50 để giảm miss detect
CONF_THRESHOLD = 0.50

# camera
CAMERA_INDEX = 0

# crop
CROP_PADDING = 20
