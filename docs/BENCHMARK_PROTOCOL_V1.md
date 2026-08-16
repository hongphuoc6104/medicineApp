# RxIE Benchmark Protocol V1

This document specifies the frozen benchmark protocol for all token classification experiments (E0: PhoBERT, E1: BamiBERT, E2: ViPubmedDeBERTa).

---

## 1. Dataset & Split Isolation

- **Dataset Release Version:** `rxie-dataset-v1.0.1`
- **Schema Contracts:**
  - Relational V2: `rxie.annotation.v2` (`train.jsonl`, `val.jsonl`, `test.jsonl`)
  - Flat BIO V1: `rxie.annotation.v1` (`bio_train.jsonl`, `bio_val.jsonl`, `bio_test.jsonl`)
- **Split Roles:**
  - **Train Split:** 19 Prescriptions (279 documents). Role: Model training.
  - **Validation Split:** 4 Prescriptions (115 documents). Role: Checkpoint selection and hyperparameter tuning.
  - **Test Split (SEALED):** 4 Prescriptions (35 documents). Role: Final evaluation only. **No hyperparameter tuning or checkpoint selection permitted on Test.**

---

## 2. Standardized Experiment Seeds

All candidate backbones must be evaluated on the exact same fixed set of random seeds:
- Seed 1: `42`
- Seed 2: `3407`
- Seed 3: `2026`

Mean and standard deviation across the 3 runs must be reported for all metrics.

---

## 3. Checkpoint Selection & Early Stopping

- **Primary Criterion:** Prescription-level Macro Entity F1 on the Validation split.
- **Secondary Criterion:** Strict Entity Micro F1 on the Validation split.
- **Early Stopping:** Patience of `3` evaluation epochs based on the primary validation metric.
- **Anti-Leakage Gate:** The final test evaluator (`scripts/evaluate_final_test.py`) will strictly refuse to evaluate any checkpoint that has not been flagged with `"selected_on_validation": true` in `checkpoint_manifest.json`.

---

## 4. Hyperparameter Search Grid

All models share the same fixed search space:
- **Optimizer:** `AdamW`
- **Learning Rates:** `[1e-5, 2e-5, 3e-5, 5e-5]`
- **Warmup Ratio:** `0.1`
- **Weight Decay:** `0.01`
- **Max Epochs:** `20`
- **Batch Size:** `8` (with gradient accumulation if required for memory constraints)
- **Max Sequence Length:** `512` (with sliding window `stride = 64` for longer sequences)

---

## 5. Standardized Experiment Directory Layout

Every experiment run must conform to the following directory hierarchy:

```text
experiments/
  E0_phobert/
    config.yaml
    environment.json
    seed_42/
      predictions_val.jsonl
      metrics_val.json
      training_log.json
      checkpoint_manifest.json
    seed_3407/
      ...
    seed_2026/
      ...
```

---

## 6. Mandatory Evaluation Metrics

1. **Strict Entity Micro & Macro:** Precision, Recall, F1 for exact `(type, start, end)` spans.
2. **Per-Class Metrics:** P, R, F1, and Gold Support for each individual class (`DRUG`, `STRENGTH`, `DOSAGE`, `ROUTE`, `FREQUENCY`, `INSTRUCTION`, `FORM`, `QUANTITY`).
3. **Prescription-Level Macro Summary:** Mean Macro Entity F1 computed across prescriptions to evaluate fairness against over-represented capture clusters.
4. **Relational Metrics (Post-Sprint B):** Parent Assignment Accuracy, Relation PRF, Drug Record Exact Match.

---
*Protocol locked on: 2026-08-16. Version: 1.0.0-final.*
