# RxIE Benchmark Protocol v1.2.0

This protocol is frozen for E0 PhoBERT, E1 BamiBERT, and E2 ViPubmedDeBERTa Token NER.

## Dataset and labels

- Release: `rxie-dataset-v1.0.1`.
- Train: 19 prescriptions, 279 captures.
- Validation: 4 prescriptions, 115 captures.
- Sealed Test: 4 prescriptions, 35 captures.
- Active classes, in fixed order: `DRUG`, `STRENGTH`, `DOSAGE`, `FREQUENCY`, `ROUTE`, `INSTRUCTION`.
- The head has `O + 2 * 6 = 13` BIO labels. `QUANTITY`, `FORM`, `DURATION`, and `NOTE` map to `O`.
- Training, tuning, gates, and smoke tests do not parse the sealed Test split. Test is opened only after official cohort authorization and checksum verification.

## Tokenization and windows

- Tokenization first returns content IDs and character offsets without model special tokens.
- `max_input_tokens = 256` means total model input IDs including special tokens for all three benchmark backbones.
- `content_capacity = max_input_tokens - tokenizer.num_special_tokens_to_add(False)`.
- `content_overlap = 64`; step is `content_capacity - content_overlap`.
- Every window independently receives the tokenizer's valid BOS/CLS and EOS/SEP envelope.
- Special tokens have offset `(0, 0)`, no global token index, and label `-100`.
- Every final input must have `len(input_ids) <= 256`.
- Native 512-token BamiBERT/DeBERTa runs are outside the main benchmark and may be reported only as a separately named ablation.

## Loss ownership and batching

- The training dataset consists of token windows, and DataLoader shuffles those windows with a seed-controlled generator.
- The policy name is `Shuffled Token-Window Batching with Single-Loss Ownership`.
- Every original content token has exactly one window with label other than `-100`.
- Every active gold entity is assigned to one window that contains its complete token range. All entity tokens, including its `B-*`, share that owner.
- This prevents duplicate overlap loss and orphan `I-*` supervision.

## Inference merge

- Each window returns logits associated with global content-token indices.
- For duplicate overlap tokens, logits from the window where the token is farthest from a content edge win. Ties use the lower deterministic window index.
- Argmax is applied after constructing one global logit sequence.
- The global BIO sequence is decoded exactly once into document spans.
- Token NER outputs `parent_entity_id = null` and `relations = []`. Parent, relation, and record metrics are `N/A` (`null`) for E0/E1/E2.

## Metrics

- Entity identity is `(document_id, type, start, end)`.
- Entity Micro F1 is strict exact-span F1 over all active entities.
- Active Macro F1 is the arithmetic mean of the six fixed per-class F1 values. Inactive classes never affect it.
- For each prescription, active entities are pooled across captures while retaining `document_id`, then strict active-entity micro F1 is calculated.
- Primary `prescription_macro_entity_f1` is the equal mean of those per-prescription micro F1 values over prescriptions with at least one active gold entity.
- Empty-gold prescriptions are excluded from the primary metric; they never receive an artificial F1 of 1.
- Empty-gold document and prescription false-positive rates are reported separately.
- Validation currently has 3 prescriptions with active gold. This limitation must be disclosed with results; grouped cross-validation is reserved for a separately versioned protocol and must not be mixed with v1.2 results.

## Tuning and global LR selection

- Seeds: `42`, `3407`, `2026`.
- Learning rates: `1e-5`, `2e-5`, `3e-5`, `5e-5`.
- Tuning requires the complete Cartesian grid: 4 LR x 3 seeds = 12 runs.
- For each LR, report mean and sample standard deviation across the three validation seeds for primary Prescription Macro F1 and secondary Entity Micro F1.
- Select exactly one LR per backbone using: highest primary mean, highest secondary mean, lowest primary standard deviation, then smallest LR.
- The selector writes an immutable `selection_manifest.json`; it does not copy or promote any tuning checkpoint. Selection validation reopens and hashes all 12 tuning manifests and metric files before official authorization. A hash over benchmark-critical code/config/protocol files must remain identical from tuning selection through official training.

## Protocol-B official runs

- The training CLI exposes only `smoke`, `tuning`, and `official`; `final` is not a run type.
- `official` requires a valid selector-produced selection manifest and cannot accept a caller-supplied LR.
- After LR freeze, seeds `42`, `3407`, and `2026` each initialize a fresh model from the pinned pretrained backbone revision.
- Official outputs are `experiments/<model>/official/seed_<seed>/` and are never tuning checkpoint copies.
- Existing run, selection, prediction, or metric outputs are immutable and cause failure rather than overwrite.

## Test sealing

- The official evaluator has no `--force` and no caller-selectable Test file.
- The evaluator requires a clean worktree at the exact official training commit and revalidates checkpoint, environment, implementation, and cohort hashes before Test access.
- Smoke, tuning, old final, self-certified, incomplete-cohort, wrong-LR, wrong-selection-hash, or wrong-path checkpoints fail before Test access.
- All three official seeds must exist and share model, selected LR, protocol, and selection-manifest hash before Test is opened.
- Test checksum must match the frozen release manifest.
- Test inference is run once; existing Test outputs cause failure.

## Provenance and determinism

- Config pins immutable backbone and tokenizer revisions.
- Manifests record source commit, dataset version/checksums, revisions, seed, LR, batch size, epochs, warmup, weight decay, steps, window policy, package versions, CUDA/cuDNN, and deterministic flags.
- Python, NumPy, Torch, CUDA, and DataLoader generator receive the run seed.
- cuDNN deterministic mode is enabled, benchmark mode is disabled, CUBLAS deterministic workspace is configured, and unsupported nondeterministic operations fail instead of warning.
- Reproducibility is expected under the pinned software/hardware contract; cross-platform bitwise identity is not claimed.

Protocol locked: 2026-08-17. Version: `1.2.0-final`.
