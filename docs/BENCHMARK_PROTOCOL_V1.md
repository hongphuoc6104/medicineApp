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

## 2. Active E0 / E1 / E2 Entity Classes & BIO Schema

All Token NER models are trained and evaluated on the 6 active trainable clinical entity classes (13 BIO labels):
- `DRUG`, `STRENGTH`, `DOSAGE`, `FREQUENCY`, `ROUTE`, `INSTRUCTION`
- Inactive classes (`QUANTITY`, `FORM`, `DURATION`, `NOTE`) are mapped to `O` during flat token classification.
- **Active Entity Macro F1:** Computed exclusively as the unweighted mean across the 6 active classes.

---

## 3. Model Capacity & Token Sliding Window Policy

Due to architectural positional embedding constraints:
- **PhoBERT Base v2 (`vinai/phobert-base-v2`):** Effective window size = `256 tokens`, stride = `64 tokens`.
- **BamiBERT (`Qualcomm-AI-Research/BamiBERT`):** Effective window size = `512 tokens`, stride = `64 tokens`.
- **ViPubmedDeBERTa (`manhtt-079/vipubmed-deberta-base`):** Effective window size = `512 tokens`, stride = `64 tokens`.

**Fair Training Loss Policy:**
- For multi-window documents during training, boundary overlap tokens are masked to `-100` (`mask_overlap_for_training=True`) so every token in the document receives gradient backpropagation exactly once.
- During validation / test inference, predictions across all windows are merged and deduplicated back to document character spans.

---

## 4. Standardized Experiment Seeds & Search Grid

All candidate backbones share the same search space:
- **Seeds:** `[42, 3407, 2026]`
- **Optimizer:** `AdamW`
- **Learning Rates:** `[1e-5, 2e-5, 3e-5, 5e-5]`
- **Warmup Ratio:** `0.1`
- **Weight Decay:** `0.01`
- **Max Epochs:** `20`
- **Batch Size:** `8`
- **Early Stopping:** Patience of `3` evaluation epochs based on validation Prescription Macro Entity F1.

---

## 5. Checkpoint Selection & Anti-Leakage Promotion Protocol

To strictly prevent test set data leakage:
1. **Hyperparameter Tuning Phase:**
   Run all learning rates across seeds in isolated tuning directories:
   `experiments/<model>/tuning/lr_<lr>_seed_<seed>/`
   Tuning checkpoints are marked with `selected_on_validation: false, eligible_for_final_test: false`.
2. **Promotion Phase:**
   Run `scripts/select_best_benchmark_checkpoint.py --model <model> --promote`.
   Selects the best learning rate based on validation `prescription_macro_entity_f1` and copies to `experiments/<model>/final/seed_<seed>/` with `selected_on_validation: true, eligible_for_final_test: true`.
3. **Final Test Evaluation:**
   `scripts/evaluate_final_test.py --checkpoint-dir experiments/<model>/final/seed_<seed>/`
   Executes real model inference on the sealed test set. Any attempt to run on tuning or smoke checkpoints is strictly blocked with `PermissionError`.

---

## 6. Standardized Experiment Directory Layout

```text
experiments/
  E0_phobert/
    tuning/
      lr_1.0e-05_seed_42/
      lr_2.0e-05_seed_42/
      ...
    final/
      seed_42/
        best_checkpoint/
        checkpoint_manifest.json
        environment.json
        training_log.json
        metrics_val.json
        predictions_val.jsonl
        metrics_test.json
        predictions_test.jsonl
      seed_3407/
      seed_2026/
```

---

## 7. Mandatory Evaluation Metrics

1. **Strict Entity Micro & Macro:** Precision, Recall, F1 for exact `(type, start, end)` spans across the 6 active classes.
2. **Per-Class Metrics:** P, R, F1, and Gold Support for each individual class (`DRUG`, `STRENGTH`, `DOSAGE`, `ROUTE`, `FREQUENCY`, `INSTRUCTION`).
3. **Prescription-Level Macro Summary:** Mean Macro Entity F1 computed across prescriptions to evaluate robustness across diverse prescription formats.
4. **Relational Metrics:** Parent Assignment Accuracy, Relation PRF, Drug Record Exact Match.

---
*Protocol locked on: 2026-08-16. Version: 1.1.0-final.*
