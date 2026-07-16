# Active General Plan

## Initiative active

`ML Kit Document Scanner and Progressive Spatial OCR foundation`

## Active execution wave

All worker branches start from `7c66dc5`. Workers do not edit shared progress, ADR, or run-log documents; the coordinator updates them after integration.

| Lane | Branch | Scope | State |
|---|---|---|---|
| A | `work/wp03b-drug-resolution` | WP-03B brand/ingredient/strength safety | DONE |
| B | `work/wp05a-mlkit-bridge` | Dormant native ML Kit bridge, no production UI switch | BLOCKED_ENV |
| C | `work/cleanup-mobile-phase-b` | Retire Flutter Phase B features and deep links | DONE |
| D | `work/cleanup-fastapi-phase-b` | Retire FastAPI Phase B endpoints | DONE |
| E | `work/clean07-schema-retirement` | Fresh-schema cleanup and safe retirement tooling | IMPLEMENTATION_DONE |
| F | `work/wp01-baseline-tooling` | Asset locator, harness and provenance | TOOLING_DONE_PREFLIGHT_BLOCKED |

`APP_ACTIVE_DETAILED_PLAN.md` records WP-03B closure. WP-03C is now dependency-ready but has not been activated.

## Locked decisions

- Implementation baseline: `main@a6810a392c97593f073a9c5e2b8dfc47027c1911`.
- Foundation branch: `feature/mlkit-progressive-ocr-foundation`.
- Keep YOLO, deskew, orientation, and CameraX until ML Kit benchmark evidence exists.
- Mobile uses an app-owned Android ML Kit bridge with a one-page JPEG in `SCANNER_MODE_FULL`.
- AI remains server-side and moves to CPU-only only after correctness equivalence.
- Phase B is not part of the product flow.
- WP-01 covers all 170 approved images: 50 labeled images for correctness and 120 operational images for success/error/empty/timing only.
- Approved-main is run twice at exactly `a6810a3`: one GPU process and one CPU-forced process, using the same manifest, evaluator, seed and thread policy.
- Inputs and models are referenced read-only through a locator; they are not copied or symlinked into the clean worktree.
- Full debug may exist only in an ignored local directory and must never be committed.

## Dependencies and merge order

1. WP-03B is complete; WP-03C and Python core Phase B cleanup may now start in isolated slices because they share `core/pipeline.py`.
2. Merge WP-05A before WP-05B; keep CameraX production flow unchanged in WP-05A.
3. Flutter and FastAPI Phase B cleanup can merge independently after their retired-route tests pass.
4. Merge CLEAN-07 implementation only after disposable PostgreSQL verification; production drop remains blocked on backup and restore testing.
5. Merge WP-01 tooling before recording the two approved-main runs. Safe full OCR remains blocked on WP-03B and WP-03C.

WP-06 waits for all of WP-05. WP-08 and WP-12 wait for WP-03B/C.

## WP-01 preflight gates

- Confirm that all 170 images are approved for this evaluation and do not expose real patient information in tracked artifacts.
- Record SHA-256 hashes for the input manifest and every model before execution.
- Select and record a local full-debug retention deadline. Recommended policy: delete full debug after aggregate report approval.
- Do not start either baseline until approval, privacy and asset preflight all pass.

## Completed foundation slices

- WP-03A: explicit Python/Node failure contract; no mock medication or failure persistence.
- WP-03D: unmatched evaluator predictions count as false positives.
- WP-03B: conservative brand/ingredient/strength resolution with stable product identity and raw candidate preservation.
- WP-04: pure-Dart prescription image acquisition contract with fake tests.
- WP-02 partial: Node, Flutter and FastAPI Phase B ingress retired; Python core and dependency cleanup remain.
- CLEAN-07 implementation: fresh schema no longer creates seven Phase B tables; guarded retirement CLI passed disposable verification. Production retirement remains pending.

## Definition of done

- Safe full-OCR baseline has full provenance.
- Python, Node, and mobile have one explicit scan error/result contract.
- Drug mapping never confirms an unsafe generic or strength mismatch.
- Progressive OCR is introduced through shadow, exhaustive, then guarded modes with tests and benchmarks.
