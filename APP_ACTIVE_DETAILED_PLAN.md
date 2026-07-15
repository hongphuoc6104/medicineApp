# Active Detailed Plan

## Current Slice: WP-03A

`Failure contract and mock-medication removal`

## Objective

Ensure a Python pipeline failure is an explicit non-2xx error through Node, is never normalized as a successful empty or mock scan, and is not persisted as a completed scan.

## In scope

- `server/main.py` and the Python scan endpoint/pipeline boundary it calls.
- `server-node/src/services/scan.service.js`.
- `server-node/src/routes/scan.routes.js` only if required to preserve an HTTP status/code.
- `scripts/tests/test_pipeline_failure_contract.py`.
- `server-node/tests/integration/pythonScanContract.test.js`.

## Out of scope

- `scripts/run_pipeline.py`.
- ML Kit, Progressive OCR, mobile UI, database migration, Phase B cleanup.
- Drug matching logic and row ownership; these are later WP-03 slices.

## Required reading order

1. `AGENTS.md`
2. `docs/mlkit_progressive_ocr/README.md`
3. `server/main.py`
4. The full Python scan handler and its pipeline invocation
5. `server-node/src/services/scan.service.js`
6. `server-node/src/routes/scan.routes.js`
7. Current Python and Node scan tests

## Implementation rules

1. Write both new contract tests before integration changes.
2. Preserve a machine-readable failure code and appropriate HTTP status from Python through Node.
3. Do not fabricate medications, quality `GOOD`, or a successful scan ID after failure.
4. Do not insert a scan-history row after the pipeline failure.
5. Keep the normal successful response backward-compatible until a later, separately approved canonical contract migration.
6. Stop and report if preserving the Python HTTP response requires a broad public API redesign.

## Acceptance criteria

- A Python exception produces a non-2xx API response with an explicit error code.
- Node preserves the failure semantics instead of returning success or mock medication.
- No successful scan persistence occurs for that request.
- Existing successful scan tests continue to pass.

## Verification

```bash
python scripts/tests/test_pipeline_failure_contract.py
cd server-node && npm test -- pythonScanContract.test.js
```

Run the relevant existing Python and Node scan tests after the two targeted tests pass.

## Next slices

1. WP-03B: safe brand/ingredient/strength resolution with `test_drug_lookup_resolution_safety.py`.
2. WP-03C: medication row ownership with `test_medication_row_ownership.py`.
3. WP-03D: evaluator counts out-of-alias predictions as false positives.
