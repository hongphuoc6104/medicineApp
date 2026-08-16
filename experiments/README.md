# RxIE Experiments Directory

This directory stores experiment outputs for model training and evaluation (E0: PhoBERT, E1: BamiBERT, E2: ViPubmedDeBERTa).

## Directory Structure
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

## Git Policy
- Model weights (`*.safetensors`, `*.bin`, `*.pt`), large optimizer states, and raw predictions are ignored by `.gitignore`.
- Benchmark evaluation summaries and metrics logs are committed to `reports/`.
