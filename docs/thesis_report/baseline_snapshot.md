# Thesis Baseline Snapshot (2026-04-21)

## Scope

This snapshot locks the quantitative baseline used for the thesis update run.

- Evaluation run: `data/output/eval/run_20260421_103453`
- OCR metrics file: `data/output/eval/run_20260421_103453/ocr_metrics.json`
- Error analysis file: `data/output/eval/run_20260421_103453/error_analysis.json`
- Bootstrap confidence intervals: `data/output/eval/run_20260421_103453/bootstrap_ci.json`

## Core-labeled benchmark summary (50 images)

### Proposed (adaptive STT)

- TP/FP/FN: 220 / 5 / 18
- Micro precision: 0.978
- Micro recall: 0.924
- Micro F1: 0.950
- Exact-match rate: 37/50 (74.0%)
- Runtime (s): cold 15.25, warm mean 5.12, p50 5.06, p90 5.94

### Baseline without STT grouping

- TP/FP/FN: 220 / 6 / 18
- Micro precision: 0.973
- Micro recall: 0.924
- Micro F1: 0.948
- Exact-match rate: 36/50 (72.0%)

### Forced STT without fallback

- TP/FP/FN: 147 / 0 / 91
- Micro precision: 1.000
- Micro recall: 0.618
- Micro F1: 0.764
- Exact-match rate: 14/50 (28.0%)

## OCR reference summary (238 items)

- Matched references: 220/238 (92.44%)
- Average CER (penalizing misses): 0.077
- Average WER (penalizing misses): 0.088

## Error profile (proposed)

- Error images: 13/50 (26.0%)
- Error type distribution:
  - under-extraction: 8
  - over-extraction: 4
  - mixed: 1

## Bootstrap 95% confidence intervals

### Proposed (adaptive STT)

- Precision CI95: [0.957, 0.995]
- Recall CI95: [0.860, 0.971]
- F1 CI95: [0.914, 0.977]

### Baseline without STT grouping

- Precision CI95: [0.951, 0.991]
- Recall CI95: [0.864, 0.973]
- F1 CI95: [0.914, 0.975]

## Reproducibility note

The thesis document must cite this run id explicitly and avoid mixing values from previous runs.
