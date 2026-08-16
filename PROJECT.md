# Project: RxIE Sprint A (Information Extraction from Prescription OCR)

## Architecture
- **Ingestion (`rxie.ocr.v1`)**: Deterministic ingestion of Android ML Kit OCR JSONs (`blocks` -> `lines` -> `elements` -> `symbols`) into canonical `OcrDocument` with line-level `OcrRegion`, coordinate clamping, reading order, and exact text offset reconstruction via `build_document_text`.
- **Atomic Ground Truth (`rxie.canonical_gt`)**: Decomposition of composite `instruction_raw` into atomic fields (`dosage_raw`, `frequency_raw`, `duration_raw`, `route_raw`, `instruction_raw`, `form_raw`) across all 27 canonical prescriptions (85 medication records). Locked annotation policies: `DRUG` excludes `STRENGTH`, `QUANTITY` includes unit, non-overlapping flat spans.
- **Alignment Engine & Auditing (`rxie.alignment_engine`)**: Fuzzy character alignment mapping 27 Canonical GT prescriptions onto 437 `OcrDocument` captures. Taxonomy: `MATCHED`, `AMBIGUOUS`, `UNRESOLVED`. Generates structured observation audit matrices.
- **Relational Schema & Dataset Generator (`rxie.annotation.v2`, `rxie.dataset_generator`, `rxie.sampler`)**: Span + Pointer annotations with `entity_id`, `medication_id`, `parent_entity_id`, `source_region_ids`, and 8 clinical relation types. Generates `train.jsonl`, `val.jsonl`, `test.jsonl` under `data/ner_dataset/` with strict 19/4/4 prescription split isolation and flat BIO PhoBERT export. Prescription-balanced sampling utility countering sample count imbalance.
- **Structured Multi-Metric Evaluator (`rxie.evaluation`)**: Full Blueprint evaluator suite covering Strict Entity Micro/Macro F1 (10 classes), Parent Assignment Accuracy, Relation Micro/Macro PRF (8 types), Record Exact Match, Record Tuple F1, Document EM, and dual Capture-level Micro vs Prescription-level Macro aggregation.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | ML Kit Parser & Coordinate Clamping | Deterministic parsing of 437 raw ML Kit JSON files into `OcrDocument` with bbox clamping to `[0.0, page_dim]` | M0 (A0) | Survey Explorer 1 / R1 |
| 2 | Canonical Text Offset Reconstruction | `build_document_text` matches 100% of OCR `fullText` with zero offset error | M0 (A0) | Survey Explorer 1 / R1 |
| 3 | Ingestion CLI / Module | `load_mlkit_ocr_document` / `rxie.ingestion` module with batch parsing utility | M0 (A0) | Survey Explorer 1 / R1 |
| 4 | Canonical GT Schema Atomic Fields | Update `CanonicalMedication` and validation for atomic fields | M1 (A1-A2) | Survey Explorer 2 / R2 |
| 5 | Instruction Decomposition Engine | Deterministic decomposition of 32 unique instruction patterns across 85 medication records | M1 (A1-A2) | Survey Explorer 2 / R2 |
| 6 | Annotation Policy Locking | Enforce `DRUG` without `STRENGTH`, `QUANTITY` with unit, non-overlapping flat spans | M1 (A1-A2) | Survey Explorer 2 / R2 |
| 7 | GT Batch Validation Script | Automated validation and review of all 27 canonical GT JSON files | M1 (A1-A2) | Survey Explorer 2 / R2 |
| 8 | Fuzzy Alignment Engine | Map 27 GT prescriptions to 437 `OcrDocument` captures | M2 (A3-A5) | Survey Explorer 2 / R3 |
| 9 | Match State Taxonomy | Classify spans into `MATCHED`, `AMBIGUOUS`, `UNRESOLVED` | M2 (A3-A5) | Survey Explorer 2 / R3 |
| 10 | Observation Audit Report Generator | Generate JSON/CSV alignment audit matrix logging spans, confidence, regions, status | M2 (A3-A5) | Survey Explorer 2 / R3 |
| 11 | Schema Upgrade `rxie.annotation.v2` | `GoldEntityV2`, `EntityRelation`, `RelationType`, `AnnotationDocumentV2` models & validation | M3 (A6-A7) | Survey Explorer 3 / R4 |
| 12 | Flat BIO PhoBERT Dataset Export | Convert `AnnotationDocumentV2` to flat BIO tokens compatible with fast tokenizers | M3 (A6-A7) | Survey Explorer 3 / R4 |
| 13 | Dataset Generator (19/4/4 Split) | Generate `train.jsonl`, `val.jsonl`, `test.jsonl` under `data/ner_dataset/` with zero cross-split leakage | M3 (A6-A7) | Survey Explorer 3 / R4 |
| 14 | Prescription-Balanced Samplers | `PrescriptionWeightedRandomSampler` ($w_i = 1/N_{p(i)}$) & `HierarchicalPrescriptionSampler` | M3 (A6-A7) | Survey Explorer 3 / R4 |
| 15 | Strict Entity Micro/Macro F1 | Exact `(type, start, end)` evaluation for 10 clinical entity classes | M4 (A8) | Survey Explorer 3 / R5 |
| 16 | Parent Assignment & Relation PRF | Parent accuracy & 8 relation type PRF (`HAS_STRENGTH`, `HAS_DOSAGE`, etc.) | M4 (A8) | Survey Explorer 3 / R5 |
| 17 | Record Exact Match & Tuple F1 | Drug record EM and slot tuple F1 evaluation | M4 (A8) | Survey Explorer 3 / R5 |
| 18 | Dual Level Aggregation | Capture-level Micro metrics & Prescription-level Macro metrics | M4 (A8) | Survey Explorer 3 / R5 |
| 19 | E2E Testing Suite (Tiers 1-4) | Comprehensive opaque-box test suite covering all features with >= 5 tests per feature | Test Track | Dual Track |
| 20 | Adversarial Coverage Hardening (Tier 5) | White-box adversarial testing and edge case verification | Final Milestone | Dual Track |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | ML Kit Ingestion (A0) | Ingestion module, coordinate clamping, 437 OCR documents validation, unit tests | None | DONE |
| M1 | GT Decomposition (A1-A2) | Schema update, 32 instruction rules, 85 med records decomposition, policy locking | None | PLANNED |
| M2 | Alignment Engine (A3-A5) | Fuzzy alignment across 437 captures, match states, observation auditing | M0, M1 | PLANNED |
| M3 | Dataset Generator & Sampler (A6-A7) | `rxie.annotation.v2`, 19/4/4 split generator, flat BIO export, balanced samplers | M2 | PLANNED |
| M4 | Multi-Metric Evaluator (A8) | Strict NER F1, Parent Accuracy, Relation F1, Record EM, Tuple F1, Dual Aggregation | M3 | PLANNED |
| M5 | Final E2E Pass & Hardening | 100% E2E test suite pass (Tiers 1-4) + Adversarial hardening (Tier 5) | M0-M4, Test Track | PLANNED |

## Interface Contracts
### `rxie.ingestion` -> `OcrDocument` (`rxie.ocr.v1`)
- Function: `load_mlkit_ocr_document(path: Path | str) -> OcrDocument`
- Batch: `ingest_all_mlkit_captures(source_dir: Path | str) -> dict[str, OcrDocument]`
- Output: `OcrDocument` matching `schemas.py` with line-level `OcrRegion`, clamped coords, monotonic `reading_order`.

### `rxie.canonical_gt` -> `CanonicalPrescriptionGT`
- Decomposed fields: `dosage_raw`, `frequency_raw`, `duration_raw`, `route_raw`, `instruction_raw`, `form_raw`.
- Function: `decompose_instruction(instruction_raw: str) -> dict[str, str | None]`
- Validation: `validate_canonical_gt(prescription: CanonicalPrescriptionGT) -> bool`

### `rxie.alignment_engine` -> `AnnotationDocumentV2` & Audit Matrix
- Function: `align_prescription_to_ocr(prescription: CanonicalPrescriptionGT, ocr_doc: OcrDocument) -> tuple[AnnotationDocumentV2, list[AlignmentRecord]]`
- Taxonomy: `MatchStatus = "MATCHED" | "AMBIGUOUS" | "UNRESOLVED"`
- Audit Record: `(prescription_id, document_id, medication_id, entity_type, canonical_text, matched_text, start, end, confidence, region_ids, status)`

### `rxie.dataset_generator` & `rxie.sampler`
- Output: `data/ner_dataset/train.jsonl`, `val.jsonl`, `test.jsonl`
- Sampler: `PrescriptionWeightedRandomSampler(documents, num_samples, seed)`
- Sampler: `HierarchicalPrescriptionSampler(documents, seed)`

### `rxie.evaluation` -> `StructuredEvaluationReport`
- Function: `evaluate_structured_annotations(gold_docs: list[AnnotationDocumentV2], pred_docs: list[AnnotationDocumentV2]) -> StructuredEvaluationReport`
- Metrics: `entity_micro`, `entity_macro`, `parent_accuracy`, `relation_micro`, `relation_macro`, `record_exact_match`, `record_tuple_prf`, `prescription_macro_summary`.

## Code Layout
- `src/rxie/schemas.py`: Schema models (`OcrDocument`, `GoldEntityV2`, `AnnotationDocumentV2`, `RelationType`, `EntityRelation`).
- `src/rxie/text.py`: `DocumentText`, `build_document_text`, `RegionSpan`.
- `src/rxie/ingestion.py`: ML Kit OCR parser, coordinate clamping, batch ingestion.
- `src/rxie/canonical_gt.py`: Instruction decomposition rules, GT validation, GT update tooling.
- `src/rxie/alignment_engine.py`: Fuzzy alignment, match state classifier, observation audit matrix generator.
- `src/rxie/dataset_generator.py`: Dataset generation for 19/4/4 splits, split isolation check, PhoBERT flat BIO exporter.
- `src/rxie/sampler.py`: `PrescriptionWeightedRandomSampler`, `HierarchicalPrescriptionSampler`, dataloader utilities.
- `src/rxie/evaluation.py`: Structured multi-metric evaluator suite.
- `tests/rxie/`: Unit and integration tests covering all modules.
