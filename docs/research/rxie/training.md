# Token-Classification Baseline

Install training dependencies:

```bash
pip install -e '.[train,dev]'
```

Convert the historical DRUG-only data without treating it as ten-class truth:

```bash
rxie-convert-legacy data/legacy/drug_only/train.json artifacts/legacy-train.jsonl
```

Create a validation JSONL from training-source documents using a documented group
split. Do not use `data/legacy/drug_only/test.json` for checkpoint selection.

Train a baseline with a verified local path or model-hub identifier:

```bash
rxie-train \
  --base-model <verified-model-id-or-path> \
  --train-file <train.rxie.jsonl> \
  --validation-file <validation.rxie.jsonl> \
  --output-dir artifacts/e1-token-baseline \
  --seed 42
```

Training writes `experiment_manifest.json` with input hashes, labels, seed, base
model, schema version, and source commit. A run is ten-class only when all ten
classes exist in versioned train and validation annotations.
