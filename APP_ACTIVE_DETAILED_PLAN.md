# Active Detailed Plan

## Current Slice: WP-03B (DONE)

`Safe brand, ingredient, and strength resolution`

## Objective

Prevent ingredient-only or strength-incompatible OCR text from being silently converted into a confirmed trade product while preserving the raw OCR candidate for user review.

## In scope

- `core/phase_a/s6_drug_search/drug_lookup.py`
- `core/pipeline.py`, limited to medication resolution output
- `server-node/src/services/scan.service.js`, limited to additive mapped/raw fields
- `scripts/tests/test_drug_lookup_resolution_safety.py`
- `tests/test_phase_a_scan_lookup_regression.py`

## Out of scope

- `scripts/run_pipeline.py`
- OCR grouping and row ownership
- ML Kit, Progressive OCR, Phase B cleanup and database migrations
- Broad canonical response migration or mobile UI changes

## Test-first cases

1. Exact brand with compatible strength may be confirmed.
2. Brand with incompatible strength must not be confirmed.
3. Query strength present but candidate strength absent must not be confirmed.
4. Ingredient shared by multiple brands remains an ingredient/unmapped candidate.
5. Ingredient plus unique strength must not silently become a brand.
6. Combination products require complete compatible strength evidence.
7. Parenthetical explicit brand remains supported.
8. `drug_name_raw` and `ocr_text` are preserved.
9. Existing lookup keys remain backward compatible.
10. Selected `medication_candidates`, including rejected items, remain observable.

## Implementation rules

- Return additive evidence such as `match_basis`, ambiguity, strength state and resolution reason.
- Treat strength as `compatible`, `mismatch`, `unknown_query` or `unknown_candidate` rather than a ranking-only boolean.
- Ingredient-only, ambiguous and strength-mismatch results cannot be `confirmed`.
- Keep plausible unsafe mappings as `unmapped_candidate` for review rather than dropping them.
- Do not change protected CLI behavior or remove existing lookup return keys.

## Acceptance criteria

- New safety test passes without loading OCR/NER models.
- Existing scan lookup regression passes, including `drug_name_raw`.
- WP-03A Python/Node contract tests remain green.
- No new confirmation path relies only on fuzzy score.

## Verification

```bash
python -m pytest scripts/tests/test_drug_lookup_resolution_safety.py -q
python -m pytest tests/test_phase_a_scan_lookup_regression.py tests/test_drug_database.py -q
cd server-node && npm test -- pythonScanContract.test.js scan.service.test.js
```

## Stop conditions

Stop if the change requires rewriting `scripts/run_pipeline.py`, removing current response fields, or combining row-ownership semantics into this slice.

## Completion evidence

- Safety fixture suite: `16/16` pass without loading OCR/NER models.
- Integrated targeted Python wave: `52/52` pass.
- Node full suite on disposable PostgreSQL: `104/104` pass; same-brand registrations with different strength remain distinct.
- Ingredient-only, ambiguous, missing/contradictory strength and strength mismatch cannot become `confirmed`.
- `drug_name_raw`, `ocr_text`, rejected candidates, registration and normalized strength evidence remain observable.
- `scripts/run_pipeline.py` is unchanged.

WP-03C is the next permitted core slice, but it is not started in this wave.
