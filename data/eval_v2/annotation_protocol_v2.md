# Phase A Evaluation Protocol v2

## 1) Dataset composition

- Core labeled benchmark: `50` images from `data/input/prescription_1..7`
- Extended unlabeled pool sample: `120` images sampled from `data/input/Data-20260420T154328Z-3-001/Data`

## 2) Evaluation tracks

### Track A — Extraction accuracy (labeled)

- Uses only split `core_labeled`
- Metrics: micro precision/recall/F1, FP/FN, exact-match, CER/WER
- Purpose: assess extraction correctness against canonical ground truth

### Track B — Operational stress test (unlabeled)

- Uses split `extended_unlabeled`
- Metrics: runtime distribution, non-empty output rate, OCR-empty error rate
- Purpose: assess pipeline robustness under wider capture variability

## 3) Reporting rules

- Track A and Track B must never be merged into one aggregate accuracy claim.
- Non-empty output rate is an operational metric, not a correctness metric.
- Any conclusion on extraction accuracy must reference Track A only.
