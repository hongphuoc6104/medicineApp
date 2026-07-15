# Active General Plan

## Initiative active

`ML Kit Document Scanner and Progressive Spatial OCR foundation`

## Current priority

1. WP-01: create a reproducible approved-main full-OCR baseline.
2. WP-03B: make brand/ingredient/strength resolution safe.
3. WP-03C: establish medication row ownership and source-region provenance.
4. WP-02: continue Python/FastAPI/mobile Phase B cleanup in isolated change sets.
5. WP-05: implement the native ML Kit bridge after the completed WP-04 contract.

## Locked decisions

- Implementation baseline: `main@a6810a392c97593f073a9c5e2b8dfc47027c1911`.
- Foundation branch: `feature/mlkit-progressive-ocr-foundation`.
- Keep YOLO, deskew, orientation, and CameraX until ML Kit benchmark evidence exists.
- Mobile uses an app-owned Android ML Kit bridge with a one-page JPEG in `SCANNER_MODE_FULL`.
- AI remains server-side and moves to CPU-only only after correctness equivalence.
- Phase B is not part of the product flow.

## Blocker

WP-01 cannot run in the clean worktree yet: model weights and approved test images are untracked and absent. Provision them from a versioned manifest or approved read-only asset location, then record their SHA-256 hashes before running the baseline.

## Completed foundation slices

- WP-03A: explicit Python/Node failure contract; no mock medication or failure persistence.
- WP-03D: unmatched evaluator predictions count as false positives.
- WP-04: pure-Dart prescription image acquisition contract with fake tests.
- WP-02 partial: Node Phase B ingress, orphan gitlink and legacy `drug_mapper` retired.

## Definition of done

- Safe full-OCR baseline has full provenance.
- Python, Node, and mobile have one explicit scan error/result contract.
- Drug mapping never confirms an unsafe generic or strength mismatch.
- Progressive OCR is introduced through shadow, exhaustive, then guarded modes with tests and benchmarks.
