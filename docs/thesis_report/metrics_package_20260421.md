# Metrics Package — Thesis Run `run_20260421_103453`

## 1) Source artifacts

- Main metrics: `data/output/eval/run_20260421_103453/phase_a_eval_metrics.json`
- Ablation CSV: `data/output/eval/run_20260421_103453/ablation_summary.csv`
- OCR metrics: `data/output/eval/run_20260421_103453/ocr_metrics.json`
- Error analysis: `data/output/eval/run_20260421_103453/error_analysis.json`
- Bootstrap CI: `data/output/eval/run_20260421_103453/bootstrap_ci.json`
- Track B operational metrics: `data/output/eval/run_20260421_103453/track_b_operational.json`

## 2) Extraction metrics (Track A: core labeled, n=50)

### Proposed (adaptive STT)

- TP/FP/FN: `220 / 5 / 18`
- Micro precision/recall/F1: `0.978 / 0.924 / 0.950`
- Exact-match rate: `37/50 = 74.0%`
- Latency (s): cold `15.25`, warm mean `5.12`, p50 `5.06`, p90 `5.94`

### Baseline without STT grouping

- TP/FP/FN: `220 / 6 / 18`
- Micro precision/recall/F1: `0.973 / 0.924 / 0.948`
- Exact-match rate: `36/50 = 72.0%`

### Forced STT without fallback

- TP/FP/FN: `147 / 0 / 91`
- Micro precision/recall/F1: `1.000 / 0.618 / 0.764`
- Exact-match rate: `14/50 = 28.0%`

### Additional ablations

- No lookup: TP/FP/FN `218 / 5 / 20`, micro F1 `0.946`
- No preprocess: TP/FP/FN `211 / 5 / 27`, micro F1 `0.930`

## 3) OCR metrics (Track A image-level reference set, n=238)

- Matched items: `220/238 = 92.44%`
- Average CER (miss-penalized): `0.077`
- Average WER (miss-penalized): `0.088`

## 4) Error profile (proposed)

- Error images: `13/50 = 26.0%`
- Distribution:
  - `under-extraction_fn`: 8
  - `over-extraction_fp`: 4
  - `mixed_fp_fn`: 1
- Highest-error group: `prescription_4` (`5` images)

## 5) Bootstrap 95% confidence intervals

### Proposed (adaptive STT)

- Precision CI95: `[0.957, 0.995]`
- Recall CI95: `[0.860, 0.971]`
- F1 CI95: `[0.914, 0.977]`
- Exact-match CI95: `[0.600, 0.860]`

### Baseline without STT grouping

- Precision CI95: `[0.951, 0.991]`
- Recall CI95: `[0.864, 0.973]`
- F1 CI95: `[0.914, 0.975]`
- Exact-match CI95: `[0.600, 0.840]`

### Paired delta: proposed minus baseline

- Precision delta CI95: `[0.000, 0.014]`
- Recall delta CI95: `[0.000, 0.000]`
- F1 delta CI95: `[0.000, 0.006]`
- Exact-match delta CI95: `[0.000, 0.060]`
- Mean latency delta CI95 (s): `[0.633, 1.142]`

## 6) Track B operational metrics (extended unlabeled, n=120)

- Non-empty output rate: `95.83%`
- OCR-empty error rate: `0.83%`
- Latency mean/p50/p90 (s): `4.79 / 4.98 / 7.21`
- Selection strategy distribution:
  - `raw_blocks`: 114
  - `stt_grouped`: 5
  - `unknown`: 1

## 7) Reporting constraints for thesis text

- Use `Track A` values for all correctness claims.
- Treat `Track B` as operational evidence only.
- State explicitly that adaptive STT is only marginally better than baseline on the current benchmark and much better than forced STT.
