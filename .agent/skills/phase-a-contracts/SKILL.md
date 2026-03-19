# Skill: Phase A Contracts

## Canonical Response Concepts

- `qualityState`
- `rejectReason`
- `guidance`
- `drugs` / `mergedDrugs`
- `mappingStatus`
- `converged`
- `occurrenceId`

## Contract Mapping Targets

- Python API may expose snake_case fields
- Node should normalize fields for mobile
- mobile models should tolerate both snake_case and camelCase when necessary

## Audit Checklist

- same semantic meaning at all 3 layers
- no placeholder field that the UI depends on accidentally
- scan session endpoints return enough state to drive the UI without guessing
