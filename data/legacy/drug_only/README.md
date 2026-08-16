# Legacy DRUG-Only Baseline

This dataset contains token sequences with only `O`, `B-DRUG`, and `I-DRUG` labels:

- Train: 938 samples.
- Test: 118 samples.

It does not annotate strength, dosage, frequency, quantity, duration, route,
instruction, form, or note. It is retained only to reproduce a historical
DRUG-only baseline. Its test split must not be used for model selection.
