# MedicineApp — MASTER PLAN

> **Ngày tạo:** 2026-03-10  
> **Trạng thái:** Đang thực hiện  
> **Nguyên tắc:** Mỗi phần phải có xử lý ngoại lệ, bảo mật, và tests trước khi chuyển sang phần tiếp.

> **Nguồn plan active hiện tại:** `APP_ACTIVE_GENERAL_PLAN.md` và `APP_ACTIVE_DETAILED_PLAN.md` ở root.
> File này giữ bối cảnh kiến trúc và lịch sử triển khai ở mức hệ thống, không phải execution plan active.

> **Cập nhật 2026-03-14 (Adaptive Scan P0):**
> - Đã triển khai 2 YOLO trong Phase A: detect đơn thuốc lớn + detect bảng thuốc ROI trước OCR (optional fallback).
> - Đã thêm quality gate Python + precheck cục bộ Flutter trước upload.
> - Đã chuyển scan session state từ in-memory sang DB (`scan_sessions`).
> - Đã chuẩn hóa trạng thái medication: `confirmed` / `unmapped_candidate` / `rejected_noise`.
> - Đang ở bước validate benchmark lợi ích thực tế (accuracy/stability/time) trước khi chốt P1/P2.

---

## Mục lục
1. [Giai đoạn 1: Fix 7 Bug Phase A](#giai-đoạn-1-fix-7-bug-phase-a)
2. [Giai đoạn 2: Thu thập Dữ liệu Thuốc VN](#giai-đoạn-2-thu-thập-dữ-liệu-thuốc-vn)
3. [Giai đoạn 3: Node.js + Express Backend](#giai-đoạn-3-nodejs--express-backend)
4. [Giai đoạn 4: Flutter App MVP](#giai-đoạn-4-flutter-app-mvp)
5. [Giai đoạn 5: Phase B](#giai-đoạn-5-phase-b-future)

---

## Giai đoạn 1: Fix 7 Bug Phase A

**Thời gian:** ~1-2 ngày | **Trạng thái:** [✅] Hoàn thành (2026-03-10)

### 1.1 Danh sách bugs

| # | Bug | File | Ưu tiên |
|---|-----|------|---------|
| VĐ1 | `_crop_polygon()` dùng `boundingRect` → crop sai chữ nghiêng | `core/phase_a/s3_ocr/ocr_engine.py` | **P0** |
| VĐ2 | Pipeline trả error thay vì fallback khi YOLO fail | `core/pipeline.py` | **P0** |
| VĐ3 | Pipeline skip bước preprocess (deskew/orientation) | `core/pipeline.py` | **P0** |
| VĐ4 | NER trả key `box`, Pipeline đọc `bbox` → mất toạ độ | `core/phase_a/s5_classify/ner_extractor.py` + `core/pipeline.py` | **P1** |
| VĐ5 | Log ghi sai `beamsearch=True` (thực tế False) | `core/phase_a/s3_ocr/ocr_engine.py` | **P2** |
| VĐ6 | `CONF_THRESHOLD=0.90` quá cao → miss detect | `core/config.py` | **P1** |
| VĐ7 | Server không warm-up models → cold start 13s | `server/main.py` | **P1** |
| VĐ8 | `_crop_prescription` không unpack tuple `crop_by_mask` | `core/pipeline.py` | **P0** |

### 1.2 Chi tiết sửa + Error handling

**VĐ1 — Perspective Transform:**
```python
def _crop_polygon(image, poly_pts):
    try:
        pts = np.array(poly_pts, dtype=np.float32)
        if len(pts) != 4:
            # Fallback: dùng boundingRect nếu không đủ 4 điểm
            x, y, w, h = cv2.boundingRect(pts.astype(np.int32))
            return image[y:y+h, x:x+w]
        pts = _order_points(pts)
        width = int(max(np.linalg.norm(pts[1]-pts[0]), np.linalg.norm(pts[2]-pts[3])))
        height = int(max(np.linalg.norm(pts[3]-pts[0]), np.linalg.norm(pts[2]-pts[1])))
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid crop dimensions: {width}x{height}")
        dst = np.array([[0,0],[width,0],[width,height],[0,height]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(pts, dst)
        return cv2.warpPerspective(image, M, (width, height))
    except Exception as e:
        logger.warning(f"Perspective crop failed: {e}, falling back to boundingRect")
        x, y, w, h = cv2.boundingRect(np.array(poly_pts, dtype=np.int32))
        h = max(h, 1); w = max(w, 1)
        return image[y:y+h, x:x+w]
```

**VĐ2 — YOLO Fallback:**
```python
def scan_prescription(self, image, ...):
    try:
        cropped = self._crop_prescription(image)
        if cropped is not None:
            image = cropped
            logger.info("YOLO crop successful")
        else:
            logger.warning("YOLO detection failed, using full image as fallback")
    except Exception as e:
        logger.error(f"YOLO detection error: {e}, using full image")
    # Tiếp tục pipeline với image (đã crop hoặc gốc)
```

**VĐ3 — Thêm Preprocess:**
```python
from core.phase_a.s2_preprocess.orientation import preprocess_image

# Trong scan_prescription(), sau YOLO crop:
try:
    image, prep_info = preprocess_image(image, stem="api")
    logger.info(f"Preprocess: {prep_info}")
except Exception as e:
    logger.warning(f"Preprocess failed: {e}, continuing with original image")
```

**VĐ4 — Thống nhất key:** Đổi `ner_extractor.py` trả `"bbox"` thay vì `"box"`.

**VĐ5 — Sửa log:** Đổi `"beamsearch=True"` → `"beamsearch=False"`.

**VĐ6 — Hạ threshold:** Đổi `CONF_THRESHOLD = 0.50` trong `config.py`.

**VĐ7 — Warm-up & Giới hạn Đồng thời (Concurrency Limit):**
```python
import asyncio

# Khởi tạo Semaphore chỉ cho phép MAX_CONCURRENT_SCANS đồng thời
# Nếu RTX 3050 4GB: chỉ nên để 1 hoặc 2 để tránh GPU OOM (Out of memory)
scan_semaphore = asyncio.Semaphore(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _get_drug_service()
        pipeline = _get_pipeline()
        if pipeline:
            import numpy as np
            dummy = np.zeros((100, 100, 3), dtype=np.uint8)
            pipeline.scan_prescription(dummy, skip_yolo=True)
            logger.info("✅ Pipeline warmed up successfully")
    except Exception as e:
        logger.error(f"⚠️ Warm-up failed: {e} — pipeline will lazy-load")
    yield

@app.post("/scan")
async def scan_endpoint(...):
    async with scan_semaphore:
        # Code xử lý pipeline
        pass
```

### 1.3 Tests cho Giai đoạn 1

```
tests/
├── test_crop_polygon.py       # VĐ1: test perspective transform
│   ├── test_normal_rectangle
│   ├── test_rotated_text
│   ├── test_invalid_polygon (< 4 points)
│   ├── test_zero_area_polygon
│   └── test_large_image_performance
│
├── test_pipeline_fallback.py  # VĐ2+VĐ3: test YOLO fail + preprocess
│   ├── test_yolo_success → cropped image
│   ├── test_yolo_fail → full image fallback
│   ├── test_preprocess_applied
│   ├── test_preprocess_fail_graceful
│   └── test_end_to_end_with_real_image
│
├── test_ner_keys.py           # VĐ4: test key consistency
│   ├── test_ner_returns_bbox_key
│   ├── test_pipeline_reads_bbox
│   └── test_bbox_coordinates_valid
│
├── test_config.py             # VĐ6: test threshold
│   └── test_conf_threshold_is_reasonable
│
└── test_server_warmup.py      # VĐ7: test warm-up
    ├── test_lifespan_loads_models
    └── test_first_request_fast (< 3s)
```

### 1.4 Verification

```bash
# Chạy tests
pytest tests/ -v

# So sánh trước/sau trên 51 ảnh
python scripts/run_pipeline.py --all > data/output/before_fix.json  # TRƯỚC
# ...fix bugs...
python scripts/run_pipeline.py --all > data/output/after_fix.json   # SAU
# Số drugs detected phải tăng, đặc biệt IMG_180633

# Test API server 
python -m uvicorn server.main:app --host 0.0.0.0 --port 8100 &
curl -X POST http://localhost:8100/api/scan-prescription -F "file=@data/input/prescription_3/IMG_20260209_180505.jpg"
```

**✅ Tiêu chí hoàn thành:**
- [x] 7/7 bugs đã fix (+1 bug mới phát hiện khi chạy thực tế)
- [x] 9/9 unit tests pass
- [x] IMG_180633 detect 1 drug
- [x] API response có `bbox` coordinates
- [x] Pipeline warm: ~7s/ảnh
- [x] **Benchmark:** 50/50 ảnh thành công, 338 drugs, avg 6.8/ảnh, 0 errors

---

## Giai đoạn 2: Thu thập Dữ liệu Thuốc VN

**Thời gian:** ~1-2 ngày | **Trạng thái:** [✅] Hoàn thành (2026-03-10)

### 2.1 Thu thập từ ddi.lab.io.vn

**Nguồn:** API có 9,284 thuốc VN, 1,857 trang  
**Cách:** Viết script Python crawl toàn bộ qua API pagination, có tích hợp cơ chế chống Anti-bot.

```python
# scripts/crawl_drug_vn.py
# - Crawl /api/drugs/search-detailed?q=&page=1..1857&limit=20
# - Anti-bot: Rate limit + Random Jitter Delay (vd: sleep ngẫu nhiên 1.5 - 3.5s).
# - Xoay vòng mảng User-Agents để đánh lừa WAF.
# - Retry logic: 3 lần retry khi timeout/error
# - Lưu: data/drug_db_vn_full.json
# - Cronjob (Kế hoạch): Chạy file này 1 tháng/1 lần để giữ Database không lỗi thời.
```

**Error handling:**
- Timeout → retry 3 lần với exponential backoff
- HTTP 429 (rate limit) → chờ 30s rồi tiếp tục
- Dữ liệu thiếu field → ghi log, bỏ qua record
- Checkpoint mỗi 100 trang (nếu crash, crawl tiếp từ checkpoint)

**Output:** File JSON chứa 9,284 thuốc:
```json
{
  "tenThuoc": "PARACETAMOL 500 mg",
  "soDangKy": "VD-16834-12",
  "hoatChat": [{"tenHoatChat": "paracetamol", "nongDo": "500 mg"}],
  "phanLoai": "Thuốc kê đơn",
  "congTySx": "Công ty cổ phần Dược phẩm 3/2",
  "nuocSx": "Việt Nam",
  "baoChe": "Viên nén dài",
  "dongGoi": "Hộp 10 vỉ x 10 viên"
}
```

### 2.2 Tổng hợp nguồn hiện có

| Nguồn | Số thuốc | Dùng cho |
|-------|---------|---------|
| ddi.lab.io.vn crawl | 9,284 | Database chính |
| vaipe_drugs_kb.json | 107 | Mapping tên OCR → tên chuẩn |
| drug_db_vn.csv | 316 | Mapping tên thương mại |
| Google Drive (user) | ? | Giấy tờ đăng ký thuốc (bổ sung) |

### 2.3 Tests cho Giai đoạn 2

```
tests/
├── test_crawl_drug.py
│   ├── test_single_page_crawl
│   ├── test_retry_on_timeout
│   ├── test_checkpoint_resume
│   ├── test_data_schema_valid
│   └── test_no_duplicate_records
```

**✅ Tiêu chí hoàn thành:**
- [x] Crawl xong 9,284 thuốc
- [x] File JSON lưu tại `data/drug_db_vn_full.json`
- [x] Không có duplicate (6,584 unique tên thuốc)
- [x] Mỗi record có tối thiểu: tenThuoc, soDangKy, hoatChat

---

## Giai đoạn 3: Node.js + Express Backend

**Thời gian:** ~1 tuần | **Trạng thái:** [✅] Hoàn thành (2026-03-10)

### 3.1 Cấu trúc thư mục

```
server-node/
├── src/
│   ├── config/
│   │   ├── database.js          # PostgreSQL connection + pool
│   │   ├── env.js               # Environment variables validation
│   │   └── constants.js         # Magic numbers, limits
│   ├── middleware/
│   │   ├── auth.js              # JWT verify middleware
│   │   ├── rateLimiter.js       # Rate limiting (express-rate-limit)
│   │   ├── errorHandler.js      # Global error handler
│   │   ├── validator.js         # Input validation (Joi/Zod)
│   │   └── logger.js            # Request logging (morgan/winston)
│   ├── routes/
│   │   ├── auth.routes.js       # POST /register, /login, /refresh
│   │   ├── drug.routes.js       # GET /drugs/:name, /drugs/search
│   │   ├── scan.routes.js       # POST /scan (proxy → Python)
│   │   ├── plan.routes.js       # CRUD /plans
│   │   ├── history.routes.js    # GET /history
│   │   └── interaction.routes.js # GET /interactions/:drug
│   ├── services/
│   │   ├── auth.service.js      # JWT + bcrypt logic
│   │   ├── drug.service.js      # ddi.lab.io.vn (chính) + nguồn khác (future)
│   │   ├── scan.service.js      # Forward to Python FastAPI
│   │   ├── plan.service.js      # Medication plan CRUD
│   │   ├── interaction.service.js # Drug interaction check
│   │   └── cache.service.js     # PostgreSQL cache layer
│   ├── models/
│   │   ├── user.model.js        # Users table
│   │   ├── scan.model.js        # Scan history table
│   │   ├── drug.model.js        # Drug cache table
│   │   └── plan.model.js        # Medication plans table
│   ├── utils/
│   │   ├── apiClient.js         # Axios wrapper with retry + timeout
│   │   ├── hash.js              # Password hashing
│   │   └── response.js          # Standardized API responses
│   └── app.js                   # Express app setup
├── migrations/                  # PostgreSQL migrations
├── tests/
│   ├── unit/                    # Unit tests cho services
│   ├── integration/             # API endpoint tests
│   └── fixtures/                # Test data
├── .env.example
├── package.json
└── README.md
```

### 3.2 Bảo mật

| Mục | Giải pháp |
|-----|----------|
| **Authentication** | JWT (access + refresh token), bcrypt hash password |
| **Token Revocation** | Refresh token lưu DB, có thể thu hồi (logout-all-devices) |
| **Rate Limiting** | 100 req/15min (auth), 300 req/15min (general) |
| **Input Validation** | Zod schema validation trên mọi route |
| **SQL Injection** | Parameterized queries (pg library, KHÔNG string concat) |
| **XSS** | Helmet middleware, sanitize input |
| **CORS** | Whitelist Flutter app origin only |
| **File Upload** | Max 10MB, kiểm tra **Magic Bytes** (nội dung thực), không chỉ header |
| **Secrets** | `.env` file, KHÔNG commit git |
| **API Keys** | External API keys lưu env, rotate định kỳ |
| **Logging** | Winston — log requests, errors, KHÔNG log passwords/tokens |

**File Upload Magic Bytes check:**
```javascript
import { fileTypeFromBuffer } from 'file-type'; // npm install file-type
const detected = await fileTypeFromBuffer(req.file.buffer);
const ALLOWED = ['image/jpeg', 'image/png', 'image/webp'];
if (!detected || !ALLOWED.includes(detected.mime))
  throw new AppError('Invalid file type', 400, 'INVALID_FILE_TYPE');
```

**Circuit Breaker cho external API (ddi.lab.io.vn) — kế hoạch tăng cường:**
```javascript
// Đây là hướng triển khai production trong tương lai.
// Nếu ddi.lab.io.vn lỗi 3 lần liên tiếp → dừng gọi 60s → fallback PostgreSQL cache
// Thư viện đề xuất: 'opossum' (node circuit breaker)
const breaker = new CircuitBreaker(callDdiApi, {
  timeout: 5000, errorThresholdPercentage: 50, resetTimeout: 60000
});
breaker.fallback(() => getCachedDrugFromDB(drugName)); // Fallback về cache
```

### 3.3 Error Handling Pattern

```javascript
// Mọi route dùng asyncHandler wrapper
const asyncHandler = (fn) => (req, res, next) =>
  Promise.resolve(fn(req, res, next)).catch(next);

// Global error handler
app.use((err, req, res, next) => {
  const status = err.statusCode || 500;
  const message = status === 500 ? 'Internal Server Error' : err.message;
  logger.error({ err, req: { method: req.method, url: req.url } });
  res.status(status).json({
    success: false,
    error: { code: err.code || 'INTERNAL_ERROR', message }
  });
});

// Service errors
class AppError extends Error {
  constructor(message, statusCode, code) {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
  }
}
```

### 3.4 Database Schema (PostgreSQL)

```sql
-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(100),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bật mỏ rộng pg_trgm cho Fuzzy Search (Gõ sai chính tả từ OCR vẫn tìm ra thuốc)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Drug Cache (cache API responses)
CREATE TABLE drug_cache (
  id SERIAL PRIMARY KEY,
  drug_name VARCHAR(255) NOT NULL,
  source VARCHAR(50) NOT NULL,  -- 'ddi' (active), 'dailymed'/'openfda' (future)
  data JSONB NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
  UNIQUE(drug_name, source)
);
-- Index Fuzzy Search mạnh nhất
CREATE INDEX idx_drug_cache_name_trgm ON drug_cache USING GIN (drug_name gin_trgm_ops);

-- Scan History
CREATE TABLE scans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  image_url TEXT,
  -- Encryption at rest (AES-256) là mục tiêu bảo mật tương lai; hiện chưa bật mặc định trong codebase.
  result JSONB NOT NULL,
  drug_count INTEGER DEFAULT 0,
  scanned_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_scans_user ON scans(user_id, scanned_at DESC);

-- Medication Plans
CREATE TABLE medication_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  drug_name VARCHAR(255) NOT NULL,
  dosage VARCHAR(100),
  frequency VARCHAR(50) NOT NULL,       -- 'daily', 'twice_daily', 'weekly'
  times JSONB NOT NULL,                  -- ["08:00", "20:00"]
  pills_per_dose INTEGER DEFAULT 1,
  total_days INTEGER,
  start_date DATE NOT NULL,
  end_date DATE,
  is_active BOOLEAN DEFAULT true,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_plans_user ON medication_plans(user_id, is_active);

-- Medication Logs (đánh dấu đã uống)
CREATE TABLE medication_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID REFERENCES medication_plans(id) ON DELETE CASCADE,
  scheduled_time TIMESTAMPTZ NOT NULL,
  taken_at TIMESTAMPTZ,
  status VARCHAR(20) DEFAULT 'pending', -- 'taken', 'missed', 'skipped'
  note TEXT
);
CREATE INDEX idx_logs_plan ON medication_logs(plan_id, scheduled_time DESC);

-- Index bổ sung để tảng tốc query phổ biến
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_logs_status ON medication_logs(plan_id, status)
  WHERE status IN ('taken', 'missed');

-- Refresh Tokens (JWT Revocation)
CREATE TABLE refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(255) UNIQUE NOT NULL,
  device_info TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ  -- NULL = hợp lệ, NOT NULL = đã thu hồi
);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id, revoked_at);

### 3.5 Tests cho Giai đoạn 3

```
tests/
├── unit/
│   ├── auth.service.test.js
│   │   ├── test_register_success
│   │   ├── test_register_duplicate_email → 409
│   │   ├── test_register_weak_password → 400
│   │   ├── test_login_success → JWT token
│   │   ├── test_login_wrong_password → 401
│   │   └── test_token_refresh
│   │
│   ├── drug.service.test.js
│   │   ├── test_search_ddi_success
│   │   ├── test_search_ddi_timeout → graceful error
│   │   ├── test_cache_hit → no API call
│   │   ├── test_cache_expired → refresh
│   │   └── test_interaction_check
│   │
│   ├── scan.service.test.js
│   │   ├── test_forward_to_python_success
│   │   ├── test_python_server_down → 503
│   │   └── test_invalid_image → 400
│   │
│   └── plan.service.test.js
│       ├── test_create_plan
│       ├── test_get_user_plans
│       ├── test_update_plan
│       ├── test_delete_plan
│       └── test_log_medication_taken
│
├── integration/
│   ├── auth.routes.test.js      # Full HTTP request tests
│   ├── drug.routes.test.js
│   ├── scan.routes.test.js
│   ├── plan.routes.test.js
│   ├── rate-limit.test.js       # Verify rate limiting works
│   └── health.routes.test.js    # Verify /health endpoint
│
└── security/
    ├── sql-injection.test.js    # Verify parameterized queries
    ├── xss.test.js              # Verify input sanitization
    ├── auth-bypass.test.js      # Verify JWT required on protected routes
    ├── file-upload.test.js      # Verify magic bytes validation
    └── token-revocation.test.js # Verify logout-all-devices works
```

**✅ Tiêu chí hoàn thành:**
- [x] Tất cả API endpoints hoạt động (15+ endpoints)
- [x] Auth (register/login/refresh/logout-all-devices) pass tests
- [x] Drug lookup (ddi + crawled data + pg_trgm fuzzy search) pass tests
- [x] File upload kiểm tra Magic Bytes
- [x] Scan proxy to Python hoạt động
- [x] Plan CRUD pass tests, có pagination
- [x] Rate limiting hoạt động (300/15min, 20/15min auth)
- [x] SQL injection safe (parameterized queries)
- [x] `GET /health` trả trạng thái DB + uptime
- [x] **55/55 tests pass** (26 unit + 29 integration, 6 suites)

---

## Giai đoạn 4: Flutter App MVP

**Thời gian:** ~2-3 tuần | **Trạng thái:** [ ] Chưa bắt đầu

### 4.1 Màn hình

| # | Màn hình | Chức năng |
|---|---------|----------|
| 1 | **Login/Register** | Đăng nhập/đăng ký (JWT) |
| 2 | **Scan** | Chụp/chọn ảnh → gọi API → hiển thị kết quả |
| 3 | **Drug Detail** | Thông tin thuốc + tương tác |
| 4 | **Plan** | Lập/xem/sửa kế hoạch uống thuốc |
| 5 | **History** | Lịch sử quét + Log uống thuốc |
| 6 | **Settings** | Profile, notification preferences |

### 4.2 Bảo mật Flutter

- Lưu JWT token trong `flutter_secure_storage` (Keychain/Keystore)
- Certificate pinning cho API calls
- Biometric auth (optional)
- Không log sensitive data

### 4.3 Error handling & Kiến trúc Offline

- **Nhắc thuốc Mất mạng (Offline Alarm):**
  - **KHÔNG THỂ** phụ thuộc hoàn toàn vào Firebase Cloud Messaging (FCM) vì cần Internet. Bệnh nhân lúc ngủ / cúp wifi sẽ không đổ chuông.
  - **Giải pháp:** Sử dụng thư viện `flutter_local_notifications` để đăng ký báo thức cục bộ trên máy. Lưu trữ thông tin Kế hoạch hoàn toàn bằng **SQLite nội bộ** (`sqflite`). Đồng bộ với Backend API Node.js khi có mạng nền (Sync).
- Network error → hiện "Không có kết nối mạng, hiển thị dữ liệu Lưu cục bộ (Offline)"
- API 401 → auto refresh token, nếu fail → redirect login
- API 500 → hiện "Lỗi server, vui lòng thử lại sau"
- Cần áp dụng chuẩn **State Management chuyên sâu** như _Riverpod_, _BLoC_, _Provider_ không dùng `setState` truyền thống.

### 4.4 Tests Flutter

```
test/
├── unit/
│   ├── auth_service_test.dart
│   ├── drug_service_test.dart
│   └── plan_service_test.dart
├── widget/
│   ├── login_screen_test.dart
│   ├── scan_screen_test.dart
│   └── plan_screen_test.dart
└── integration/
    └── app_flow_test.dart   # Full flow: login → scan → view result
```

**✅ Tiêu chí hoàn thành:**
- [ ] 6 màn hình hoạt động
- [ ] Scan → hiển thị kết quả thuốc
- [ ] Plan + reminder notification
- [ ] Tương tác thuốc hiển thị cảnh báo
- [ ] Widget tests pass
- [ ] Chạy được trên Android emulator

---

## Giai đoạn 5: Phase B (Future)

**Trạng thái:** 🔒 Hold — Chỉ bắt đầu khi Phase A + App MVP hoàn thành.

- [ ] Contrastive matching Zero-PIMA
- [ ] Pill shape/color identification (tham khảo Medisafe)
- [ ] Scan viên thuốc + so sánh với đơn thuốc

---

## Giai đoạn 6: Docker & Deployment

**Thời gian:** ~1-2 ngày | **Thực hiện cuối cùng sau khi code xong**

### Môi trường

| Dịch vụ | Development | Production |
|---------|------------|----------|
| **Python FastAPI** | `localhost:8001` (GPU local) | RunPod / Lambda Labs GPU Cloud |
| **Node.js Express** | `localhost:3000` | Railway hoặc Render |
| **PostgreSQL** | Docker container | Supabase (Free 500MB) |
| **Flutter** | Android Emulator | APK / TestFlight |

### `docker-compose.yml` (Development)
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: medicineapp
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports: ["55432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  node-api:
    build: ./server-node
    ports: ["3101:3000"]
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@postgres:5432/medicineapp_experimental
      PYTHON_API_URL: http://host.docker.internal:8100
    depends_on: [postgres]
```

### Health Check Endpoint
```javascript
// routes/health.routes.js
GET /health →  { status: 'OK', db: 'connected', python: 'reachable', timestamp }
GET /health/ready → 503 nếu DB hoặc Python chưa sẵn sàng
```

---

## Nguồn Dữ liệu Tham khảo

| Nguồn | URL | Ghi chú |
|-------|-----|---------|
| ddi.lab.io.vn | https://ddi.lab.io.vn/drugs | API thuốc VN (9,284 thuốc + tương tác) |
| DailyMed | https://dailymed.nlm.nih.gov/ | Nguồn tham khảo mở rộng (future) |
| OpenFDA | https://api.fda.gov/ | Nguồn tham khảo mở rộng (future) |
| RxNorm | https://rxnav.nlm.nih.gov/ | Chuẩn hóa tên thuốc quốc tế |
| go.drugbank.com | https://go.drugbank.com/ | Database quốc tế (academic download) |
| drugs.com | https://www.drugs.com/imprints.php | Pill Identifier |
| Google Drive (user) | Link riêng | Giấy tờ đăng ký thuốc VN |
