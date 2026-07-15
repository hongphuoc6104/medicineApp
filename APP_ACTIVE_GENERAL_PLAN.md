# Active General Plan

## Initiative active

`ML Kit Document Scanner and Progressive Spatial OCR foundation`

## Current priority

1. WP-01: create a reproducible approved-main full-OCR baseline.
2. WP-02: continue Phase B cleanup only in isolated change sets.
3. WP-03: make the scan failure, API, and drug-resolution contract safe before any progressive stopping policy.

## Locked decisions

- Implementation baseline: `main@a6810a392c97593f073a9c5e2b8dfc47027c1911`.
- Foundation branch: `feature/mlkit-progressive-ocr-foundation`.
- Keep YOLO, deskew, orientation, and CameraX until ML Kit benchmark evidence exists.
- Mobile uses an app-owned Android ML Kit bridge with a one-page JPEG in `SCANNER_MODE_FULL`.
- AI remains server-side and moves to CPU-only only after correctness equivalence.
- Phase B is not part of the product flow.

## Blocker

WP-01 cannot run in the clean worktree yet: model weights and approved test images are untracked and absent. Provision them from a versioned manifest or approved read-only asset location, then record their SHA-256 hashes before running the baseline.

## Definition of done

- Safe full-OCR baseline has full provenance.
- Python, Node, and mobile have one explicit scan error/result contract.
- Drug mapping never confirms an unsafe generic or strength mismatch.
- Progressive OCR is introduced through shadow, exhaustive, then guarded modes with tests and benchmarks.
