# OCR Input Contract

The Android client sends `rxie.ocr.v1` JSON directly to `POST /entities`.

- Regions are ML Kit text lines, with text blocks as fallback.
- `reading_order` is unique within each page.
- Bounding boxes use four pixel coordinates and must remain within page dimensions.
- `confidence` is nullable because ML Kit does not guarantee it for every region.
- Regions are joined with `\n`, ordered by page index then reading order.
- Entity offsets refer to this deterministic joined string.
- Prescription images are never sent to the API.

See `data/samples/ocr_document.json` for a complete synthetic example.
