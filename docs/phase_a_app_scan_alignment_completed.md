# Phase A App Scan Alignment - Completed Record

This document archives the completed plan that aligned the mobile app scan path with a safer API contract.

It is kept in `docs/` because the plan has already been executed and should no longer be the active handoff file in the project root.

## Completed objective

The completed work focused on making the app scan path safer than before by:

- adding a dedicated app/API scan path in `core/pipeline.py`
- introducing grouped OCR before NER in the API path
- returning explicit scan semantics like:
  - `ocr_text`
  - `drug_name_raw`
  - `matched_drug_name`
  - `mapping_status`
  - `match_score`
- preventing low-confidence fuzzy matches from being displayed as if they were confirmed final names
- updating Node normalization so unresolved items stay unresolved

## Files involved in the completed alignment work

- `core/pipeline.py`
- `server/main.py`
- `server-node/src/services/scan.service.js`
- `server-node/tests/integration/scan.routes.test.js`
- `scripts/tests/test_phase_a_api_alignment.py`

## Important note

That completed alignment work should be treated as the baseline for the next active task.

The next active task is no longer "API alignment". The next active task is:

- in-app camera preview for prescription scan
- scan UX clarity
- disable mandatory DB matching for prescription scan display

The active root handoff plan has therefore been replaced.
