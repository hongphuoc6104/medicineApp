# E2E Test Infra: RxIE Sprint A

## Test Philosophy
- **Opaque-box & Requirement-driven**: Derived directly from `ORIGINAL_REQUEST.md`, `PROJECT.md`, and clinical prescription information extraction requirements.
- **Zero Internal Coupling**: Exercises public APIs (`rxie.ingestion`, `rxie.canonical_gt`, `rxie.alignment_engine`, `rxie.dataset_generator`, `rxie.sampler`, `rxie.evaluation`, `rxie.schemas`, `rxie.text`), CLI commands, and REST endpoints.
- **Methodology**: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Simulation.

## Feature Inventory & Coverage Matrix
| # | Feature | Requirement Source | Tier 1 (Target ≥5) | Tier 2 (Target ≥5) | Tier 3 (Pairwise) | Tier 4 (Workflows) |
|---|---------|-------------------|:------------------:|:------------------:|:-----------------:|:------------------:|
| 1 | ML Kit Parser & BBox Clamping | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 2 | Canonical Text Offset Reconstruction | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 3 | Ingestion CLI & Batch Parsing | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 4 | Canonical GT Schema Atomic Fields | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 5 | Instruction Decomposition Engine | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 6 | Annotation Policy Locking | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 7 | GT Batch Validation Script | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 8 | Fuzzy Alignment Engine | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 9 | Match State Taxonomy | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 10 | Observation Audit Report Generator | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 11 | Schema Upgrade `rxie.annotation.v2` | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| 12 | Flat BIO PhoBERT Dataset Export | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| 13 | Dataset Generator (19/4/4 Split Isolation) | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| 14 | Prescription-Balanced Samplers | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| 15 | Strict Entity Micro/Macro F1 | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |
| 16 | Parent Assignment & Relation PRF | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |
| 17 | Record Exact Match & Tuple F1 | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |
| 18 | Dual Level Aggregation (Micro/Macro) | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |
| 19 | End-to-End Pipeline Integration | Blueprint Architecture | 5 | 5 | ✓ | ✓ |
| 20 | Privacy Rules & Production 503 Semantics | Working Rules & Specs | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Runner**: `pytest tests/e2e -v`
- **Test Discovery & Structure**:
  - `tests/e2e/conftest.py`: Synthetic OCR generators, Canonical GT builders, Golden Annotation factories, and filesystem fixtures.
  - `tests/e2e/test_tier1_features.py`: >= 100 isolated feature tests across all 20 features.
  - `tests/e2e/test_tier2_boundaries.py`: >= 100 boundary, negative, and extreme-case tests across all 20 features.
  - `tests/e2e/test_tier3_interactions.py`: Pairwise integration tests connecting adjacent and multi-stage modules.
  - `tests/e2e/test_tier4_scenarios.py`: Full end-to-end clinical workflow scenarios.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Standard Multi-Medication Outpatient Prescription | F1, F2, F3, F4, F5, F6, F8, F9, F11, F15, F16, F17 | High |
| 2 | Highly Distorted / Noisy Low-Confidence Capture | F1, F2, F8, F9, F10, F11 | High |
| 3 | Pediatric Weight-Based / Drops Dosage Pipeline | F4, F5, F6, F8, F11, F16 | High |
| 4 | Chronic Disease Polypharmacy (10+ Meds) | F1, F4, F5, F8, F10, F11, F17 | Extreme |
| 5 | Full Train/Val/Test Split & PhoBERT BIO Generation | F11, F12, F13, F14 | High |
| 6 | Complete Benchmark Evaluation (Perfect, Partial, Noisy Preds) | F15, F16, F17, F18 | High |
| 7 | Production API Ingestion & Missing Model 503 Guard | F3, F20 | Medium |

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥ 100 tests (≥ 5 per feature across 20 features)
- **Tier 2 (Boundary & Corner)**: ≥ 100 tests (≥ 5 per feature across 20 features)
- **Tier 3 (Cross-Feature Combinations)**: ≥ 20 tests (covering pairwise pipeline interactions)
- **Tier 4 (Real-World Scenarios)**: ≥ 10 scenario tests (realistic clinical and dataset workflows)
- **Total Minimum Target**: ≥ 230 E2E tests
