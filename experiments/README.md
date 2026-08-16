# RxIE Experiments Directory

This directory stores experiment outputs for model training and evaluation (E0: PhoBERT, E1: BamiBERT, E2: ViPubmedDeBERTa).

## Directory Structure
```text
experiments/
  E0_phobert/
    smoke/seed_42/...
    tuning/
      lr_1.0e-05_seed_42/...
      lr_2.0e-05_seed_42/...
    official/
      seed_42/...
      seed_3407/...
      seed_2026/...
```

## Git Policy
- Model weights (`*.safetensors`, `*.bin`, `*.pt`), large optimizer states, and raw predictions are ignored by `.gitignore`.
- Benchmark evaluation summaries and metrics logs are committed to `reports/`.
- Tuning artifacts select one global LR but are never copied into `official/`.
- Official directories and Test outputs are immutable; reruns require a newly versioned protocol or run identity.
