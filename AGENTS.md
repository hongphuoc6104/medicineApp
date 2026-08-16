# RxIE Working Rules

- Scope is Android ML Kit OCR, OCR JSON contracts, and ten-class entity extraction.
- Do not restore Node, PostgreSQL, server-side OCR, Phase B, or medication-plan code.
- Do not open or enumerate prescription binaries under `data/input/` unless the user
  explicitly requests a privacy-reviewed data operation.
- Never commit raw prescriptions, OCR dumps from real patients, model checkpoints,
  training runs, or secrets.
- Production inference must fail with `503` when no model is available; never return
  mock entities or medications.
- Keep mobile and Python contracts covered by tests before changing field names.
- Treat `data/legacy/` as DRUG-only baseline data, not ten-class ground truth.
- Whenever dataset annotations, ground truth, or alignment logic change, do not reuse previous release version names; increment the release version (e.g., `rxie-dataset-v1.0` -> `rxie-dataset-v1.0.1`) and record new SHA256 checksums in `release_manifest.json`.
- Every gitignored artifact/data directory (`artifacts/`, `checkpoints/`, `runs/`, `experiments/`, `data/input/`, `data/output/`, `data/private/`) must maintain a `README.md` documenting its structure, lifecycle, and exclusion policy.
- Before committing and pushing to remote git branches, verify all test suites pass (`pytest tests/`) and no untracked binaries or checkpoints are staged.
