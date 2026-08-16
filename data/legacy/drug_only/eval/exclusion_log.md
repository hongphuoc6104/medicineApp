# Phase A Evaluation Exclusion Log

- Evaluation date: 2026-04-21 10:55:15
- Manifest file: `data/eval/phase_a_manifest.csv`
- Policy: only finalized image files (`.jpg`, `.jpeg`, `.png`) under `data/input/prescription_1..7` are included.

## Excluded artifacts

1. `data/input/Unconfirmed 823414.crdownload`
   - Reason: incomplete browser download artifact, not a valid image file.
   - Impact: no impact on 50-image benchmark because file is outside prescription folders and unreadable by pipeline.

2. `data/input/Phase_B /...`
   - Reason: Phase B pill-verification assets, outside Phase A prescription extraction scope.
   - Impact: intentionally excluded from this thesis evaluation chapter.
