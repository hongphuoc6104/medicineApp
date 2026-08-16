# RxIE Prescription Entity Extraction

This branch contains one vertical slice only:

```text
Android ML Kit scanner -> OCR JSON -> FastAPI -> entity classifier -> result UI
```

The server never receives the prescription image. Google ML Kit performs document
scanning and OCR on the Android device, then sends text regions with bounding boxes
and reading order to `POST /entities`.

## Entity Types

`DRUG`, `STRENGTH`, `DOSAGE`, `FREQUENCY`, `QUANTITY`, `DURATION`, `ROUTE`,
`INSTRUCTION`, `FORM`, and `NOTE`.

Parent assignment, relations, drug lookup, medication plans, authentication, and
server-side OCR are intentionally out of scope.

## Python API

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
RXIE_MODEL_PATH=/absolute/path/to/model rxie-api
```

Endpoints:

- `GET /health`
- `GET /model-info`
- `POST /entities`

The API returns `503` when `RXIE_MODEL_PATH` is missing or invalid. It never returns
mock medication data.

## Android Client

```bash
cd mobile
flutter pub get
flutter run --dart-define=RXIE_API_URL=http://10.0.2.2:8000
```

Use the host machine IP instead of `10.0.2.2` when testing on a physical device.

## Verification

```bash
python -m pytest tests/rxie -q
ruff check src/rxie tests/rxie
ruff format --check src/rxie tests/rxie
cd mobile && flutter analyze && flutter test
```

## Data

`data/input/` contains a local, ignored 2.14 GB collection of 489 real prescription
images from one layout family. It may contain protected health information. Do not
commit, upload, or inspect it automatically. See `data/input/README.md`.

The tracked `data/legacy/` dataset is a DRUG-only baseline and is not valid evidence
for the ten-class RxIE model.
