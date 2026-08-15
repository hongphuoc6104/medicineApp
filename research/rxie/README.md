# RxIE Research

This package isolates research for noise-robust, layout-invariant prescription
information extraction from the production MedicineApp pipeline.

## Current Scope

- Schema version: `rxie.v0.1`
- OCR blocks preserve raw text, confidence, bounding boxes, reading order, and
  source-region provenance.
- Parent assignment is explicit and supports `NULL` through `drug_id=None`.
- Baseline metrics cover strict entity F1, relation F1, parent accuracy, and
  medication-record exact match.

The research blueprint is stored at
`docs/research/rxie/RxIE_Blueprint_Mo_hinh_OCR_Don_thuoc.docx`.

No code in this package is imported by `core/pipeline.py` or
`scripts/run_pipeline.py`. Production integration will happen only after the
ablation gates are met.

## Verify

```bash
python -m unittest discover -s tests/rxie -v
```
