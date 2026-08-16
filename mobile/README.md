# RxIE Android scanner

Minimal Flutter Android client that scans prescriptions, performs on-device OCR,
and posts OCR JSON to `POST /entities`. It never uploads image bytes.

```bash
flutter run --dart-define RXIE_API_URL=http://10.0.2.2:8000
```
