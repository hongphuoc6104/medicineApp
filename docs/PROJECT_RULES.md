# Project Rules - Medicine App

Đây là bản tóm tắt quy tắc dự án. File đầy đủ: `.gemini/GEMINI.md`

## Quy tắc chính

### Naming Conventions
| Loại | Quy tắc | Ví dụ |
|------|---------|-------|
| Variable | `camelCase` | `userName`, `isLoading` |
| Class | `PascalCase` | `YOLOSegmentation` |
| Function | `camelCase` | `getUserById()` |
| Constant | `SCREAMING_CASE` | `MAX_RETRY` |
| File | `snake_case` | `yolo_segmentation.py` |

### Công nghệ sử dụng
- **Models/AI**: Python + YOLO
- **Backend**: Node.js (planned)
- **Mobile**: Flutter (planned)
- **Database**: MongoDB (planned)

### Cấu trúc thư mục
```
medicineApp/
├── models/         # YOLO models
├── inference/      # Inference scripts
├── data/           # Input/output data
├── tests/          # Unit tests
├── docs/           # Documentation
└── scripts/        # Utility scripts
```
